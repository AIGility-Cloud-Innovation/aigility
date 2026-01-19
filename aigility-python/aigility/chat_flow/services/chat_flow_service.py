from this import d, s
import yaml
import os
import sys
import json
from typing import List, Dict, Any, Optional,Literal

# --- 0. 路径补丁：确保直接运行脚本时能找到 aigility 包 ---
# 获取当前文件的父目录（aigility/chat_flow/services）
current_file_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录（aigility-master）
root_dir = os.path.abspath(os.path.join(current_file_dir, "..", "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from langgraph.graph import StateGraph, END
from langgraph.graph.message import AnyMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from aigility.rag.service import RAGService
from aigility.chat_flow.schema import ChatFlowState, ToolCall, ToolResult, get_tool_descriptions, get_tool_names, get_tool_schema_map, LLMConfig

# --- 1. 辅助函数：加载配置 ---

# --- 1. 辅助函数：加载配置 ---
def load_config() -> Dict[str, Any]:
    """Load the chat flow configuration from the YAML file."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "chat_flow_config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

CONFIG = load_config()

# --- 2. 核心 Node 定义 ---

class ChatFlowService:
    """
    一个即插即用的 LangGraph ChatFlow 服务。
    实现了 CoT、RAG 和 Web Search 的交互逻辑。
    """
    def __init__(self, 
                 use_rag: Literal["on", "off", "auto"] = "off",
                 rag_service: Optional[RAGService] = None,
                 llm_config: LLMConfig = LLMConfig( provider="dashscope", model_name="qwen3-max"), 
                 checkpoint: Optional[BaseCheckpointSaver] = None,
                 ):
        self.config = CONFIG
        self.use_rag = use_rag
        self.llm_config = llm_config
        self.llm = self.llm_config.get_client()
        self.rag_service = rag_service
        self.tools = get_tool_schema_map()
        self.graph = self._build_graph(checkpoint)
        
        

    def _build_graph(self, checkpoint: Optional[BaseCheckpointSaver]):
        """构建 LangGraph 状态机。"""
        workflow = StateGraph(ChatFlowState)
         # 根据模式决定入口点和边
        if self.use_rag == "on":
            # 模式1: 总是执行 RAG
            # entry → rag_retrieval → agent_decision → [tool_executor] → generate_response
            workflow.add_node("rag_retrieval", self._rag_retrieval)
            workflow.add_node("agent_decision", self._agent_decision)
            workflow.add_node("tool_executor", self._tool_executor)
            workflow.add_node("generate_response", self._generate_response)
            
            workflow.set_entry_point("rag_retrieval")
            workflow.add_edge("rag_retrieval", "agent_decision")
        
        elif self.use_rag == "auto":
            # 模式2: LLM 判断是否需要 RAG
            # entry → rag_decision → (条件) → agent_decision → ...
            workflow.add_node("rag_decision", self._rag_decision)
            workflow.add_node("rag_retrieval", self._rag_retrieval)
            workflow.add_node("agent_decision", self._agent_decision)
            workflow.add_node("tool_executor", self._tool_executor)
            workflow.add_node("generate_response", self._generate_response)
            
            workflow.set_entry_point("rag_decision")
            workflow.add_conditional_edges(
                "rag_decision",
                lambda s: "retrieve" if s.get("rag_needed") else "skip",
                {"retrieve": "rag_retrieval", "skip": "agent_decision"}
            )
            workflow.add_edge("rag_retrieval", "agent_decision")  
            
        else:  # "off"
        # 模式3: 不使用 RAG（保持原有逻辑）
            workflow.add_node("agent_decision", self._agent_decision)
            workflow.add_node("tool_executor", self._tool_executor)
            workflow.add_node("generate_response", self._generate_response)
            workflow.set_entry_point("agent_decision")   
        
        # 共同的边
        workflow.add_conditional_edges(
            "agent_decision", self._should_continue,
            {"continue": "tool_executor", "end": "generate_response"}
        )
        workflow.add_edge("tool_executor", "generate_response")
        workflow.add_edge("generate_response", END)    

        app = workflow.compile(checkpointer=checkpoint)
        return app

    # --- 3. Node 实现 ---
    def _agent_decision(self, state: ChatFlowState) -> Dict[str, Any]:
        """
        Node 1: Agent 决策节点。
        使用 LLM 和 CoT Prompt 决定是否调用工具。
        """
        print("--- Executing Agent Decision Node ---")
        
        # 1. 准备 Prompt
        tool_desc = get_tool_descriptions().replace("{", "{{").replace("}", "}}")
        system_prompt = self.config["system_prompt"].format(
            tool_descriptions=tool_desc
        )
        decision_prompt = self.config["agent_decision_prompt"]
        
        # 提取历史消息和最新用户输入
        history = "\n".join([f"{m.type.capitalize()}: {m.content}" for m in state["messages"][:-1]])
        user_input = state["messages"][-1].content
        
        # 2. 构造消息列表并创建 Prompt
        # 使用 template_format="mustache" 或类似方式可以避开解析，
        # 但最简单的做法是直接传入已经格式化好的字符串，并告诉 LangChain 不要再解析变量
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt.replace("{", "{{").replace("}", "}}")),
            ("human", decision_prompt.format(history=history, input=user_input).replace("{", "{{").replace("}", "}}"))
        ])

        # 2. 绑定工具和解析器
        # 使用 Pydantic 模型来强制 LLM 输出 JSON 格式的工具调用
        class DecisionOutput(BaseModel):
            thought: str = Field(description="The detailed Chinese thought process (CoT).")
            tool_call: List[ToolCall] = Field(description="A list of tool calls to make, or an empty list if no tool is needed.")

        chain = prompt | self.llm.with_structured_output(DecisionOutput)
        
        # 3. 调用 LLM
        try:
            response = chain.invoke({})
        except Exception as e:
            # 失败时，直接进入生成回复阶段，不调用工具
            print(f"Agent Decision failed: {e}. Skipping tool call.")
            return {"thought": f"Agent Decision failed: {e}. Proceeding to final response.", "tool_calls": []}

        # 4. 更新状态
        tool_calls = response.tool_call
        
        # 确保 tool_calls 中的 tool_name 是有效的
        valid_tool_calls = []
        for tc in tool_calls:
            if tc.tool_name in self.tools:
                valid_tool_calls.append(tc)
            else:
                print(f"Warning: Invalid tool name '{tc.tool_name}' in decision. Skipping.")

        return {
            "thought": response.thought,
            "tool_calls": valid_tool_calls,
        }

    def _should_continue(self, state: ChatFlowState) -> str:
        """
        Conditional Edge: 根据是否有工具调用决定下一步。
        """
        if state.get("tool_calls"):
            return "continue"
        return "end"

    def _rag_retrieval(self, state: ChatFlowState) -> Dict[str, Any]:
        """RAG 检索节点：执行知识库检索"""
        print("--- Executing RAG Retrieval Node ---")
        user_input = state["messages"][-1].content
        
        if self.rag_service:
            rag_result = self.rag_service.search(user_input)
            if rag_result:
                print(f"RAG 检索结果：{rag_result}")
                return {"rag_context": f"【知识库检索结果】\n{rag_result}"}
            else:
                return {"rag_context": "Error: RAGService 未初始化，无法检索知识库。"}

    def _rag_decision(self, state: ChatFlowState) -> Dict[str, Any]:
        """RAG 判断节点（仅 auto 模式）：让 LLM 判断是否需要检索知识库"""
        print("--- Executing RAG Decision Node ---")
        user_input = state["messages"][-1].content
        
        all_meta = self.rag_service.get_all_doc_meta()
        
        # 处理空元信息的情况
        if not all_meta:
            print("⚠️ 知识库元信息为空，默认执行 RAG 检索")
            return {"rag_needed": True}
        
        # 汇总所有文档的关键词和摘要
        all_keywords = []
        all_summaries = []
        for doc_name, meta in all_meta.items():
            all_keywords.extend(meta.get('keywords', []))
            all_summaries.append(f"【{doc_name}】{meta.get('summary', '')}")
        
        doc_keywords = ", ".join(set(all_keywords))  # 去重后拼接
        doc_summary = "\n".join(all_summaries)
        user_input = state["messages"][-1].content
        
        decision_prompt = self.config["rag_decision_prompt"].format(
            doc_keywords=doc_keywords, 
            doc_summary=doc_summary,
            input=user_input
        )
        
        # 修复：replace 应该对字符串调用，不是元组
        prompt = ChatPromptTemplate.from_messages([
            ("system", decision_prompt.replace("{", "{{").replace("}", "}}"))
        ])
        
        # 定义回答类型
        class RAGDecision(BaseModel):
            need_rag: bool = Field(description="是否需要检索内部知识库")
            reason: str = Field(description="判断理由")
        
        chain = prompt | self.llm.with_structured_output(RAGDecision)
        response = chain.invoke({})
        print(f"rag判断结果：{response.need_rag};判断理由：{response.reason}")
        return {"rag_needed": response.need_rag}

    def _tool_executor(self, state: ChatFlowState) -> Dict[str, Any]:
        """
        Node 2: 工具执行节点。
        """
        print("--- Executing Tool Executor Node ---")
        tool_calls: List[ToolCall] = state["tool_calls"]
        tool_results: List[ToolResult] = []

        # 工具执行
        for tc in tool_calls:
            tool_name = tc.tool_name
            query = tc.query
            # 模拟调用 web 搜索工具
            if tool_name == "WebSearchTool":
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

    def _generate_response(self, state: ChatFlowState) -> Dict[str, Any]:
        """
        Node 3: 最终回复生成节点。
        整合所有信息，生成最终回复、会话标题和回复建议。
        """
        print("--- Executing Generate Response Node ---")
        
        # 1. 准备 Prompt
        response_prompt = self.config["final_response_prompt"]
        
        # 提取历史消息、思考过程和工具结果
        history = "\n".join([f"{m.type.capitalize()}: {m.content}" for m in state["messages"][:-1]])
        user_input = state["messages"][-1].content
        thought = state.get("thought", "无")
        tool_results_str = "\n".join([f"[{tr.tool_name}]: {tr.result}" for tr in state.get("tool_results", [])])
        # 对工具结果进行转义，防止其中包含 JSON 导致解析失败
        tool_results_str = tool_results_str.replace("{", "{{").replace("}", "}}")
        if not tool_results_str:
            tool_results_str = "无工具调用结果。"
        # 获取rag检索内容
        rag_context = state.get("rag_context", "")
        # 将 RAG 上下文加入 prompt
        # 2. 绑定结构化输出
        class FinalOutput(BaseModel):
            final_response: str = Field(description="The final, comprehensive, and professional response to the user.")

        prompt = ChatPromptTemplate.from_messages([
            ("system", response_prompt.format(
                thought=thought,
                tool_results=tool_results_str,
                history=history,
                input=user_input,
                rag_context=rag_context
            ).replace("{", "{{").replace("}", "}}"))
        ])
        
        chain = prompt | self.llm.with_structured_output(FinalOutput)

        # 3. 调用 LLM
        try:
            response = chain.invoke({})
        except Exception as e:
            print(f"Final Response Generation failed: {e}")
            # 失败时，返回一个简单的错误信息
            final_response = f"抱歉，生成最终回复时发生错误: {e}"
            
            # 更新消息历史
            state["messages"].append(AIMessage(content=final_response))
            
            return {
                "messages": state["messages"],
            }

        # 4. 更新状态
        final_response = response.final_response
        
        # 更新消息历史
        state["messages"].append(AIMessage(content=final_response))

        return {
            "messages": state["messages"],
        }

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

# --- 4. 示例使用 ---
if __name__ == "__main__":
    # 示例 1: 需要 RAG 的问题
    rag_service = RAGService()
    # ------------------------------
    # 如果切换为 DashScope + FIASS
    # ------------------------------
    '''
    from aigility.rag.config import VectorStoreConfig
    from aigility.rag.config import EmbeddingConfig
    embedding_config = EmbeddingConfig(
        provider="dashscope",
        model_name="text-embedding-v4",
        api_key=os.getenv("DASHSCOPE_API_KEY")
    )
    vector_store_config = VectorStoreConfig(
        provider="faiss",
        path="./faiss_db"
    )
    config = RAGConfig(embedding=embedding_config, vector_store=vector_store_config)
    service = RAGService(config=config)
    service.add_file("./test.pdf")
    print(service.search("公司最新的休假政策是什么？"))
    '''
    #rag_service.clear_knowledge_base()
    rag_service.add_file("test.pdf")
    print("="*50)
    print("示例 1: 需要 RAG 的问题 (关于内部知识库)")
    print("="*50)
    flow_service = ChatFlowService(rag_service=rag_service,use_rag="auto")
    result1 = flow_service.invoke("无领导小组讨论”面试考察什么")
    print("\n--- 最终结果 ---")
    print(f"Response: {result1['response']}\n")
    print(f"Thought: {result1['thought_process']}")
    '''
    # 示例 2: 需要 Web Search 的问题
    print("\n\n"+"="*50)
    print("示例 2: 需要 Web Search 的问题 (关于最新信息)")
    print("="*50)
    result2 = flow_service.invoke("2025年诺贝尔物理学奖得主是谁？")
    print("\n--- 最终结果 ---")
    print(f"Response: {result2['response']}")
    print(f"Thought: {result2['thought_process']}")
    
    # 示例 3: 不需要工具的简单问题
    print("\n\n"+"="*50)
    print("示例 3: 不需要工具的简单问题")
    print("="*50)
    result3 = flow_service.invoke("你好，你叫什么名字？")
    print("\n--- 最终结果 ---")
    print(f"Response: {result3['response']}")
    print(f"Thought: {result3['thought_process']}")
'''