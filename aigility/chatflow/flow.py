import uuid
import yaml
import os
import json
from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, AnyMessage, AIMessageChunk
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from ..core.config import ADKConfig
from ..core.model_factory import ModelFactory
from ..rag import create_timem_rag_client
from .schema import ChatFlowState, ToolCall, ToolResult, get_tool_descriptions, get_tool_names, get_tool_schema_map

# --- 1. 辅助函数：加载配置 ---
def load_default_config() -> Dict[str, Any]:
    """Load the chat flow configuration from the YAML file."""
    config_path = os.path.join(os.path.dirname(__file__), "prompts", "assistant.yaml")
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

        # 初始化太忆 RAG 客户端（如果配置了）
        self.timem_rag_client = None
        if self.adk_config.timem_enabled and self.adk_config.timem_api_key and self.adk_config.timem_base_url:
            self.timem_rag_client = create_timem_rag_client(
                base_url=self.adk_config.timem_base_url,
                api_key=self.adk_config.timem_api_key,
            )

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

        # 如果太忆 RAG 未启用，跳过工具调用
        if not self.timem_rag_client:
            print("--- [ADK] TimeM RAG client not configured, skipping tool calling ---")
            return {"thought": "太忆 RAG 服务未配置，直接生成回复。", "tool_calls": []}

        # 获取历史消息和用户输入
        history = "\n".join([f"{m.type.capitalize()}: {m.content}" for m in state["messages"][:-1]])
        user_input = state["messages"][-1].content

        # 构建决策 prompt
        agent_decision_prompt = self.config.get("agent_decision_prompt", "")
        tool_descriptions = get_tool_descriptions()

        # 添加 JSON 格式说明到 prompt 中（注意：花括号需要转义为双花括号）
        json_format_instruction = """
**重要输出格式要求：**
你必须严格按照以下 JSON 格式输出，不要添加任何其他文本、标记或说明：

```json
{{
  "thought": "你的思考过程描述（必须填写）",
  "tool_calls": [
    {{
      "tool_name": "TimeMRAGTool",
      "query": "搜索查询语句"
    }}
  ]
}}
```

如果不需要调用工具，tool_calls 必须是空数组：[]
只输出 JSON 对象，不要输出其他任何内容！
"""
        enhanced_prompt = agent_decision_prompt + "\n\n" + json_format_instruction

        prompt = ChatPromptTemplate.from_template(enhanced_prompt)

        # 直接使用手动解析 JSON（兼容性更好，适用于所有 LLM）
        chain = prompt | self.llm

        try:
            response = chain.invoke({
                "history": history,
                "input": user_input,
                "tool_descriptions": tool_descriptions
            })

            # 获取原始输出
            if hasattr(response, 'content'):
                raw_output = response.content
            else:
                raw_output = str(response)

            if self.adk_config.debug:
                print(f"--- [ADK] DEBUG: Raw LLM output (first 500 chars): {raw_output[:500]} ---")

            # 尝试从输出中提取 JSON
            import re
            json_pattern = r'```json\s*(.*?)\s*```'
            json_match = re.search(json_pattern, raw_output, re.DOTALL)

            if json_match:
                json_str = json_match.group(1)
                if self.adk_config.debug:
                    print(f"--- [ADK] DEBUG: Extracted JSON from code block ---")
            else:
                # 尝试直接找到 JSON 对象
                json_pattern2 = r'\{.*\}'
                json_match2 = re.search(json_pattern2, raw_output, re.DOTALL)
                if json_match2:
                    json_str = json_match2.group(0)
                    if self.adk_config.debug:
                        print(f"--- [ADK] DEBUG: Extracted JSON directly ---")
                else:
                    # 尝试查找数组格式
                    json_pattern3 = r'\[.*\]'
                    json_match3 = re.search(json_pattern3, raw_output, re.DOTALL)
                    if json_match3:
                        json_str = json_match3.group(0)
                        if self.adk_config.debug:
                            print(f"--- [ADK] DEBUG: Extracted JSON array ---")
                    else:
                        raise ValueError("无法从 LLM 输出中提取 JSON")

            # 解析 JSON
            parsed = json.loads(json_str)

            # 处理不同的返回格式
            thought = "思考过程未生成"
            tool_calls = []

            if isinstance(parsed, list):
                # 格式: [{'tool_name': 'TimeMRAGTool', 'query': '...'}]
                for tc in parsed:
                    if isinstance(tc, dict) and 'tool_name' in tc and 'query' in tc:
                        tool_calls.append(ToolCall(
                            tool_name=tc['tool_name'],
                            query=tc['query']
                        ))
                thought = f"决定调用工具: {', '.join([tc.tool_name for tc in tool_calls])}"

            elif isinstance(parsed, dict):
                if 'tool_calls' in parsed:
                    # 标准格式: {"thought": "...", "tool_calls": [...]}
                    thought = parsed.get('thought', '思考过程未生成')
                    for tc in parsed.get('tool_calls', []):
                        tool_calls.append(ToolCall(
                            tool_name=tc['tool_name'],
                            query=tc['query']
                        ))
                elif 'tool_name' in parsed and 'query' in parsed:
                    # 单个工具: {'tool_name': 'TimeMRAGTool', 'query': '...'}
                    tool_calls.append(ToolCall(
                        tool_name=parsed['tool_name'],
                        query=parsed['query']
                    ))
                    thought = f"决定调用工具: {parsed['tool_name']}"

            if self.adk_config.debug:
                print(f"--- [ADK] Agent Decision: thought={thought}, tool_calls={len(tool_calls)} ---")

            return {
                "thought": thought,
                "tool_calls": tool_calls
            }

        except Exception as e:
            import traceback
            print(f"--- [ADK] Agent decision failed: {e} ---")
            if self.adk_config.debug:
                print(f"--- [ADK] Traceback: {traceback.format_exc()} ---")
            return {"thought": f"决策过程出错: {str(e)}", "tool_calls": []}

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

            # 根据工具名称执行不同的操作
            if tool_name == "TimeMRAGTool":
                # 使用太忆 RAG 云服务
                if self.timem_rag_client:
                    result = self.timem_rag_client.search_sync(query)
                    print(f"✅成功调用太忆RAG服务：--- [ADK] TimeM RAG search for '{query}': {result} ---")
                else:
                    result = f"❌错误：太忆 RAG 服务未配置。现在的配置：url：{self.adk_config.timem_base_url},apikey：{self.adk_config.timem_api_key}"
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
