import uuid
import yaml
import os
import json
from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, AnyMessage, AIMessageChunk
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

from ..core.config import ADKConfig
from ..core.model_factory import ModelFactory
from .schema import ChatFlowState, ToolCall, ToolResult, get_tool_descriptions, get_tool_names, get_tool_schema_map

# --- 1. 辅助函数：加载配置 ---
def load_default_config() -> Dict[str, Any]:
    """Load the chat flow configuration from the YAML file."""
    config_path = os.path.join(os.path.dirname(__file__), "prompts", "chat_flow_config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}

DEFAULT_CONFIG = load_default_config()

# --- 2. 核心 Node 定义 ---

class ChatFlow:
    """
    一个即插即用的 LangGraph ChatFlow 服务。
    实现了 CoT、RAG 和 Web Search 的交互逻辑。
    """
    def __init__(
        self,
        name: str = "ChatFlow",
        adk_config: Optional[ADKConfig] = None,
        flow_config: Optional[Dict[str, Any]] = None,
        checkpoint: Optional[BaseCheckpointSaver] = None
    ):
        self.name = name
        self.config = flow_config or DEFAULT_CONFIG
        self.adk_config = adk_config or ADKConfig()
        self.llm = ModelFactory.create_llm(self.adk_config)
        self.tools = get_tool_schema_map()
        self.graph = self._build_graph(checkpoint)

    def _build_graph(self, checkpoint: Optional[BaseCheckpointSaver]):
        """构建 LangGraph 状态机。"""
        workflow = StateGraph(ChatFlowState)

        # 1. 定义节点
        workflow.add_node("agent_decision", self._agent_decision)
        workflow.add_node("tool_executor", self._tool_executor)
        workflow.add_node("prepare_for_generation", self._prepare_for_generation)
        workflow.add_node("stream_response", self._stream_response)

        # 2. 定义入口和边
        workflow.set_entry_point("agent_decision")

        # Agent Decision -> Tool Executor 或 Generate Response
        workflow.add_conditional_edges(
            "agent_decision",
            self._should_continue,
            {
                "continue": "tool_executor",
                "end": "prepare_for_generation",
            },
        )

        # Tool Executor -> Prepare for Generation
        workflow.add_edge("tool_executor", "prepare_for_generation")

        # Prepare for Generation -> Stream Response
        workflow.add_edge("prepare_for_generation", "stream_response")

        # Stream Response -> END
        workflow.add_edge("stream_response", END)

        app = workflow.compile(checkpointer=checkpoint)
        return app

    # --- 3. Node 实现 ---

    def _agent_decision(self, state: ChatFlowState) -> Dict[str, Any]:
        """
        Node 1: Agent 决策节点。
        使用 LLM 和 CoT Prompt 决定是否调用工具。
        """
        print("--- [ADK] Executing Agent Decision Node ---")
        
        # Per user request, disable tool calling for now.
        # This will be changed back in the future.
        return {"thought": "Tool calling is disabled.", "tool_calls": []}

    def _should_continue(self, state: ChatFlowState) -> str:
        """
        Conditional Edge: 根据是否有工具调用决定下一步。
        """
        if state.get("tool_calls"):
            return "continue"
        return "end"

    def _tool_executor(self, state: ChatFlowState) -> Dict[str, Any]:
        """
        Node 2: 工具执行节点。
        模拟执行 RAG 和 Web Search 工具。
        """
        # print("--- Executing Tool Executor Node ---")
        tool_calls: List[ToolCall] = state["tool_calls"]
        tool_results: List[ToolResult] = []

        # 模拟工具执行
        for tc in tool_calls:
            tool_name = tc.tool_name
            query = tc.query
            
            # 实际应用中，这里会调用真实的 RAG 或 Web Search API
            if tool_name == "RAGTool":
                result = f"RAG Search Result for '{query}': 找到关于 {query} 的内部知识库片段。"
            elif tool_name == "WebSearchTool":
                result = f"Web Search Result for '{query}': 找到关于 {query} 的最新互联网信息。"
            else:
                result = f"Error: Tool '{tool_name}' not found."
            
            tool_results.append(ToolResult(tool_name=tool_name, result=result))
            
            # 将工具结果添加到消息历史中，以便 LLM 在下一步使用
            state["messages"].append(ToolMessage(content=result, tool_call_id=tool_name))

        return {
            "tool_results": tool_results,
            "messages": state["messages"] # 更新后的消息列表
        }

    def _prepare_for_generation(self, state: ChatFlowState) -> Dict[str, Any]:
        """Node 3: 准备最终回复生成的 Prompt 和 Chain。"""
        print("--- [ADK] Preparing for Final Response Generation ---")
        
        response_prompt = self.config.get("final_response_prompt", "")
        history = "\n".join([f"{m.type.capitalize()}: {m.content}" for m in state["messages"][:-1]])
        user_input = state["messages"][-1].content
        thought = state.get("thought", "无")
        tool_results_str = "\n".join([f"[{tr.tool_name}]: {tr.result}" for tr in state.get("tool_results", [])])
        if not tool_results_str:
            tool_results_str = "无工具调用结果。"

        # Use StrOutputParser for better streaming
        parser = StrOutputParser()
        
        # We don't need format instructions for raw text generation
        # response_prompt_template = response_prompt + "\n\n{format_instructions}"
        response_prompt_template = response_prompt

        prompt = ChatPromptTemplate.from_template(
            response_prompt_template
            # partial_variables={"format_instructions": format_instructions}
        )

        chain = prompt | self.llm | parser
        
        return {"chain": chain, "prompt_input": {
            "thought": thought,
            "tool_results": tool_results_str,
            "history": history,
            "input": user_input
        }}

    def _stream_response(self, state: ChatFlowState):
        """Node 4: 生成最终回复。
        
        同步版本用于 invoke() 调用。
        流式处理在 astream 方法中手动完成。
        """
        print("--- [ADK] Generating Final Response ---")
        chain = state.get("chain")
        prompt_input = state.get("prompt_input")
        
        if not chain or not prompt_input:
            return {"messages": [AIMessage(content="无法生成回复")]}
        
        # 同步调用 LLM
        try:
            response = chain.invoke(prompt_input)
            if isinstance(response, str):
                return {"messages": [AIMessage(content=response)]}
            else:
                return {"messages": [AIMessage(content=str(response))]}
        except Exception as e:
            print(f"Response generation failed: {e}")
            return {"messages": [AIMessage(content=f"抱歉，生成回复时发生错误: {e}")]}

    def invoke(self, user_input: str, history: List[AnyMessage] = None) -> Dict[str, Any]:
        """
        调用 ChatFlow，执行一次完整的对话流程。
        """
        if history is None:
            history = []
            
        # 添加最新的用户消息
        history.append(HumanMessage(content=user_input))
        
        initial_state = ChatFlowState(
            messages=history,
            thought=None,
            tool_calls=[],
            tool_results=[],
            reply_suggestion=None,
            session_title_suggestion=None
        )
        
        # 运行 Graph
        final_state = self.graph.invoke(initial_state)
        
        # 提取最终结果
        final_message = final_state["messages"][-1].content
        
        return {
            "response": final_message,
            "thought_process": final_state.get("thought"),
            "tool_results": final_state.get("tool_results"),
            "full_history": final_state["messages"]
        }

    async def astream(self, user_input: str, history: List[AnyMessage] = None):
        """
        异步流式调用 ChatFlow。
        
        由于旧版 LangGraph 不支持 get_stream_writer，
        我们使用 updates 模式运行图到 prepare_for_generation 节点，
        然后手动执行流式 LLM 调用。
        """
        if history is None:
            history = []
            
        # 添加最新的用户消息
        history.append(HumanMessage(content=user_input))
        
        initial_state = ChatFlowState(
            messages=history,
            thought=None,
            tool_calls=[],
            tool_results=[],
            reply_suggestion=None,
            session_title_suggestion=None
        )
        
        print(f"DEBUG [astream]: Starting with stream_mode='updates'...")
        chain = None
        prompt_input = None
        
        # 使用 updates 模式运行图
        try:
            async for event in self.graph.astream(initial_state, stream_mode="updates"):
                node_name = list(event.keys())[0] if event else None
                print(f"DEBUG [astream]: Node completed: {node_name}")
                
                if node_name == "prepare_for_generation":
                    # 捕获 chain 和 prompt_input
                    node_output = event.get("prepare_for_generation", {})
                    chain = node_output.get("chain")
                    prompt_input = node_output.get("prompt_input")
                    print(f"DEBUG [astream]: Got chain={chain is not None}, prompt_input={prompt_input is not None}")
                    
                    # 现在手动执行流式 LLM 调用
                    if chain and prompt_input:
                        print("DEBUG [astream]: Starting manual LLM streaming...")
                        chunk_count = 0
                        try:
                            async for chunk in chain.astream(prompt_input):
                                chunk_count += 1
                                # Normalize chunk to string
                                if isinstance(chunk, str):
                                    delta = chunk
                                elif isinstance(chunk, dict):
                                    delta = chunk.get('final_response', '')
                                else:
                                    delta = str(chunk)
                                
                                if delta:
                                    print(f"DEBUG [astream]: Chunk #{chunk_count}: {delta!r}")
                                    yield {
                                        "stream_response": {
                                            "messages": [AIMessageChunk(content=delta, id="stream")]
                                        }
                                    }
                            print(f"DEBUG [astream]: LLM streaming finished. Total chunks: {chunk_count}")
                        except Exception as e:
                            print(f"DEBUG [astream]: LLM streaming error: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    # 不再继续执行 stream_response 节点，因为我们已经手动处理了
                    break
                    
        except Exception as e:
            print(f"DEBUG [astream]: Graph error: {e}")
            import traceback
            traceback.print_exc()

def create_chatflow(
    name: str,
    adk_config: Optional[ADKConfig] = None,
    **kwargs
) -> ChatFlow:
    """创建对话流"""
    return ChatFlow(name=name, adk_config=adk_config, **kwargs)
