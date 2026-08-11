import uuid
import yaml
import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, AnyMessage, AIMessageChunk
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from ..core.config import ADKConfig
from ..core.model_factory import ModelFactory
from ..rag.client import create_timem_rag_client
from .schema import ChatFlowState, ToolCall, ToolResult, get_tool_descriptions, get_tool_names, get_tool_schema_map


def _extract_stream_parts(message: Any) -> Tuple[str, str]:
    """从 LLM 消息/chunk 中提取 (reasoning, content)，provider 无关。

    兼容两种思维链承载方式:
    - DeepSeek 风格(deepseek-reasoner 等): additional_kwargs["reasoning_content"]
    - 标准 content blocks(OpenAI o 系列等): content 为 list 时,
      type == "reasoning" 的块 -> reasoning; type == "text" 的块 -> content
    """
    reasoning = ""
    content = ""

    additional_kwargs = getattr(message, "additional_kwargs", None) or {}
    rc = additional_kwargs.get("reasoning_content")
    if isinstance(rc, str):
        reasoning += rc

    raw_content = getattr(message, "content", message)
    if isinstance(raw_content, str):
        content += raw_content
    elif isinstance(raw_content, list):
        for block in raw_content:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if block_type == "reasoning":
                text = block.get("reasoning") or block.get("text") or ""
                if not text and isinstance(block.get("summary"), list):
                    # OpenAI responses API: 推理摘要放在 summary 列表里
                    text = "".join(
                        s.get("text", "") for s in block["summary"] if isinstance(s, dict)
                    )
                reasoning += text
            elif block_type == "text":
                content += block.get("text", "")
    return reasoning, content

def _explain_llm_error(error: Exception) -> str:
    """为 LLM 调用异常补充排障提示。

    识别"模型不支持思维链参数"类 400 错误（llm_reasoning 开关与模型能力错配），
    在原始错误信息后追加针对性提示；其他错误原样返回字符串。
    """
    message = str(error)
    status = getattr(error, "status_code", None)
    lowered = message.lower()
    looks_like_400 = status == 400 or "400" in message
    mentions_reasoning = any(
        keyword in lowered
        for keyword in ("thinking", "reasoning_effort", "reasoning_content", "reasoning")
    )
    if looks_like_400 and mentions_reasoning:
        message += (
            "（提示：该错误可能与思维链参数有关——请检查 ADKConfig.llm_reasoning "
            "与模型能力是否匹配：普通模型请设 llm_reasoning=False；"
            "纯推理模型（deepseek-reasoner/o1 等）的思考无法关闭）"
        )
    return message


# --- 1. 辅助函数：加载配置 ---
def load_default_config() -> Dict[str, Any]:
    """Load the chat flow configuration from the YAML file."""
    config_path = os.path.join(os.path.dirname(__file__), "prompts", "chat.yaml")
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
        node_start = time.perf_counter()

        # 检查 rag_used 模式
        rag_used = state.get("rag_used", "auto")

        # 如果不是 auto 模式，直接返回预设的状态
        if rag_used == "on":
            print("--- [ADK] 🚀 RAG 模式已开启，跳过决策节点，直接使用 RAG ---")
            # on 模式下，tool_calls 应该已经在 invoke 中预设好了
            if state.get("tool_calls"):
                return {"thought": state.get("thought", "RAG 模式已开启")}
            else:
                # 如果没有预设 tool_calls，说明 RAG 客户端未配置
                return {"thought": state.get("thought", "RAG 服务未配置"), "tool_calls": []}

        elif rag_used == "off":
            print("--- [ADK] 🔒 RAG 模式已关闭，跳过决策节点 ---")
            return {"thought": state.get("thought", "RAG 模式已关闭"), "tool_calls": []}

        # auto 模式：执行决策节点
        print("--- [ADK] 🔍 执行 Agent Decision 节点 (auto 模式) ---")

        # 如果太忆 RAG 未启用，跳过工具调用
        if not self.timem_rag_client:
            print("--- [ADK] TimeM RAG client not configured, skipping tool calling ---")
            return {"thought": "太忆 RAG 服务未配置，直接生成回复。", "tool_calls": []}

        # 获取历史消息和用户输入
        history = "\n".join([f"{m.type.capitalize()}: {m.content}" for m in state["messages"][:-1]])
        user_input = state["messages"][-1].content

        # ✅ 智能提取 RAG 检索关键词（支持特殊标记格式）
        # 如果 user_input 包含特殊标记，提取标记内的内容优先作为 RAG query
        extracted_rag_query = None
        import re
        # 格式1: 【用于检索的关键词】{content}
        match1 = re.search(r'【用于检索的关键词】\s*(.*?)(?:\n【|【|$)', user_input, re.DOTALL)
        # 格式2: 【RAG_QUERY】{content}【/RAG_QUERY】
        match2 = re.search(r'【RAG_QUERY】(.*?)【/RAG_QUERY】', user_input, re.DOTALL)

        if match1:
            extracted_rag_query = match1.group(1).strip()
            print(f"--- [ADK] 🔍 提取到RAG检索关键词（格式1）: {extracted_rag_query[:100]}... ---")
        elif match2:
            extracted_rag_query = match2.group(1).strip()
            print(f"--- [ADK] 🔍 提取到RAG检索关键词（格式2）: {extracted_rag_query[:100]}... ---")
        else:
            print(f"--- [ADK] ℹ️ 未检测到特殊检索标记，将使用LLM决策的query ---")

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
                        # 智能选择 RAG query
                        query = tc['query']
                        if tc['tool_name'] == 'TimeMRAGTool':
                            if extracted_rag_query:
                                # 优先使用提取的关键词
                                query = extracted_rag_query
                                print(f"--- [ADK] 🔧 使用提取的关键词作为 RAG query: {query[:100]}... ---")
                            else:
                                # 使用 LLM 决定的 query
                                query = tc['query']
                                print(f"--- [ADK] 🔧 使用LLM决策的query作为 RAG query: {query[:100]}... ---")
                        tool_calls.append(ToolCall(
                            tool_name=tc['tool_name'],
                            query=query
                        ))
                thought = f"决定调用工具: {', '.join([tc.tool_name for tc in tool_calls])}"

            elif isinstance(parsed, dict):
                if 'tool_calls' in parsed:
                    # 标准格式: {"thought": "...", "tool_calls": [...]}
                    thought = parsed.get('thought', '思考过程未生成')
                    for tc in parsed.get('tool_calls', []):
                        # 智能选择 RAG query
                        query = tc['query']
                        if tc['tool_name'] == 'TimeMRAGTool':
                            if extracted_rag_query:
                                # 优先使用提取的关键词
                                query = extracted_rag_query
                                print(f"--- [ADK] 🔧 使用提取的关键词作为 RAG query: {query[:100]}... ---")
                            else:
                                # 使用 LLM 决定的 query
                                query = tc['query']
                                print(f"--- [ADK] 🔧 使用LLM决策的query作为 RAG query: {query[:100]}... ---")
                        tool_calls.append(ToolCall(
                            tool_name=tc['tool_name'],
                            query=query
                        ))
                elif 'tool_name' in parsed and 'query' in parsed:
                    # 单个工具: {'tool_name': 'TimeMRAGTool', 'query': '...'}
                    query = parsed['query']
                    if parsed['tool_name'] == 'TimeMRAGTool':
                        if extracted_rag_query:
                            # 优先使用提取的关键词
                            query = extracted_rag_query
                            print(f"--- [ADK] 🔧 使用提取的关键词作为 RAG query: {query[:100]}... ---")
                        else:
                            # 使用 LLM 决定的 query
                            query = parsed['query']
                            print(f"--- [ADK] 🔧 使用LLM决策的query作为 RAG query: {query[:100]}... ---")
                    tool_calls.append(ToolCall(
                        tool_name=parsed['tool_name'],
                        query=query
                    ))
                    thought = f"决定调用工具: {parsed['tool_name']}"

            if self.adk_config.debug:
                print(f"--- [ADK] Agent Decision: thought={thought}, tool_calls={len(tool_calls)} ---")

            node_elapsed = (time.perf_counter() - node_start) * 1
            print(f"⏱️ [ADK性能] Agent Decision 节点耗时: {node_elapsed:.2f}s")

            return {
                "thought": thought,
                "tool_calls": tool_calls
            }

        except Exception as e:
            import traceback
            explained = _explain_llm_error(e)
            print(f"--- [ADK] Agent decision failed: {explained} ---")
            if self.adk_config.debug:
                print(f"--- [ADK] Traceback: {traceback.format_exc()} ---")
            node_elapsed = (time.perf_counter() - node_start) * 1
            print(f"⏱️ [ADK性能] Agent Decision 节点耗时(失败): {node_elapsed:.2f}s")
            return {"thought": f"决策过程出错: {explained}", "tool_calls": []}

    def _should_continue(self, state: ChatFlowState) -> str:
        """
        Conditional Edge: 根据是否有工具调用决定下一步。
        """
        if state.get("tool_calls"):
            return "continue"
        return "end"

    def _tool_executor(self, state: ChatFlowState,config: RunnableConfig) -> Dict[str, Any]:
        """
        Node 2: 工具执行节点。
        模拟执行 RAG 和 Web Search 工具。
        """
        node_start = time.perf_counter()
        # print("--- Executing Tool Executor Node ---")
        tool_calls: List[ToolCall] = state["tool_calls"]
        tool_results: List[ToolResult] = []
        target_kb_id = config.get("configurable", {}).get("timem_kb_id")
        print(f"--- 🔧 [ADK] Tool Executor: Received {len(tool_calls)} tool calls, using kb_id={target_kb_id} ---")

        for tc in tool_calls:
            tool_name = tc.tool_name
            query = tc.query

            # 根据工具名称执行不同的操作
            if tool_name == "TimeMRAGTool":
                # 使用太忆 RAG 云服务
                rag_start = time.perf_counter()
                if self.timem_rag_client:
                    result = self.timem_rag_client.search_sync(query=query, kb_id=target_kb_id)
                    rag_elapsed = (time.perf_counter() - rag_start) * 1

                    # 根据结果判断是否成功，避免误导性的成功提示
                    is_success = not result.startswith("搜索出错") and not result.startswith("搜索失败")
                    status_icon = "✅" if is_success else "❌"
                    print(f"{status_icon}调用太忆RAG服务：--- [ADK] TimeM RAG search for '{query}' (耗时: {rag_elapsed:.2f}s): {result} ---")
                else:
                    result = f"❌错误：太忆 RAG 服务未配置。现在的配置：url：{self.adk_config.timem_base_url},apikey：{self.adk_config.timem_api_key}"
            elif tool_name == "WebSearchTool":
                result = f"Web Search Result for '{query}': 找到关于 {query} 的最新互联网信息。"
            else:
                result = f"Error: Tool '{tool_name}' not found."

            tool_results.append(ToolResult(tool_name=tool_name, result=result))

            # 将工具结果添加到消息历史中，以便 LLM 在下一步使用
            state["messages"].append(ToolMessage(content=result, tool_call_id=tool_name))

        node_elapsed = (time.perf_counter() - node_start) * 1
        print(f"⏱️ [ADK性能] Tool Executor 节点总耗时: {node_elapsed:.2f}s")

        return {
            "tool_results": tool_results,
            "messages": state["messages"] # 更新后的消息列表
        }

    def _prepare_for_generation(self, state: ChatFlowState) -> Dict[str, Any]:
        """Node 3: 准备最终回复生成的 Prompt 和 Chain。"""
        node_start = time.perf_counter()
        print("--- [ADK] 📝 准备最终回复生成节点 ---")

        response_prompt = self.config.get("final_response_prompt", "")

        # 正确获取用户输入：找到最后一条 HumanMessage
        user_input = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                user_input = msg.content
                break

        if not user_input:
            user_input = state["messages"][-1].content  # 降级方案

        # 获取历史消息（排除最后一条 HumanMessage 之后的所有消息）
        human_messages = [i for i, msg in enumerate(state["messages"]) if isinstance(msg, HumanMessage)]
        if human_messages:
            last_human_idx = human_messages[-1]
            history = "\n".join([f"{m.type.capitalize()}: {m.content}" for m in state["messages"][:last_human_idx]])
        else:
            history = "\n".join([f"{m.type.capitalize()}: {m.content}" for m in state["messages"][:-1]])

        thought = state.get("thought", "无")
        tool_results_str = "\n".join([f"[{tr.tool_name}]: {tr.result}" for tr in state.get("tool_results", [])])
        if not tool_results_str:
            tool_results_str = "无工具调用结果。"

        # 不再使用 StrOutputParser: parser 会把 chunk 压成纯字符串,
        # 导致推理模型的 reasoning_content 在流式传输中丢失。
        # 统一由消费端(_stream_response / astream)通过 _extract_stream_parts 归一化。
        response_prompt_template = response_prompt

        prompt = ChatPromptTemplate.from_template(
            response_prompt_template
        )

        chain = prompt | self.llm

        node_elapsed = (time.perf_counter() - node_start) * 1
        print(f"⏱️ [ADK性能] Prepare for Generation 节点耗时: {node_elapsed:.2f}s")

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
        node_start = time.perf_counter()
        print("--- [ADK] 💬 生成最终回复节点 ---")
        chain = state.get("chain")
        prompt_input = state.get("prompt_input")
        
        if not chain or not prompt_input:
            return {"messages": [AIMessage(content="无法生成回复")]}
        
        # 同步调用 LLM(chain 直接返回 AIMessage, 正文与思维链在此拆分)
        try:
            llm_start = time.perf_counter()
            response = chain.invoke(prompt_input)
            llm_elapsed = (time.perf_counter() - llm_start) * 1
            print(f"⏱️ [ADK性能] LLM invoke 耗时: {llm_elapsed:.2f}s")

            node_elapsed = (time.perf_counter() - node_start) * 1
            print(f"⏱️ [ADK性能] Stream Response 节点总耗时: {node_elapsed:.2f}s")

            reasoning, content = _extract_stream_parts(response)
            message = AIMessage(content=content)
            if reasoning:
                message.additional_kwargs["reasoning_content"] = reasoning
            return {"messages": [message]}
        except Exception as e:
            node_elapsed = (time.perf_counter() - node_start) * 1
            print(f"⏱️ [ADK性能] Stream Response 节点耗时(失败): {node_elapsed:.2f}s")
            explained = _explain_llm_error(e)
            print(f"Response generation failed: {explained}")
            return {"messages": [AIMessage(content=f"抱歉，生成回复时发生错误: {explained}")]}

    def invoke(self, user_input: str, history: List[AnyMessage] = None, config: RunnableConfig = None, rag_used: str = "auto") -> Dict[str, Any]:
        """
        调用 ChatFlow，执行一次完整的对话流程。

        Args:
            user_input: 用户输入
            history: 对话历史
            config: 可选的配置对象，包含运行时配置（如timem_kb_id）
            rag_used: RAG使用模式 ("auto", "on", "off")
                - auto: 启动决策节点，由AI决定是否使用RAG
                - on: 默认打开RAG，跳过决策节点
                - off: 默认关闭RAG，跳过决策节点

        Returns:
            包含响应、思考过程、工具结果的字典
        """
        invoke_start = time.perf_counter()

        if history is None:
            history = []

        # 添加最新的用户消息
        history.append(HumanMessage(content=user_input))

        # 验证 kb_id：RAG 模式下必传
        target_kb_id = None
        if config:
            target_kb_id = config.get("configurable", {}).get("timem_kb_id")
        if rag_used != "off" and not target_kb_id:
            raise ValueError(
                f"rag_used='{rag_used}' 但未提供 kb_id 知识库 ID。"
                f"请通过 ChatAgent.chat(kb_id='your_kb_id') 传入，"
                f"或通过 ChatFlow.invoke(config=RunnableConfig(configurable={{'timem_kb_id': 'your_kb_id'}})) 传入。"
            )

        initial_state = ChatFlowState(
            messages=history,
            thought=None,
            tool_calls=[],
            tool_results=[],
            reply_suggestion=None,
            session_title_suggestion=None,
            rag_used=rag_used
        )

        # 添加调试信息
        print(f"--- [ADK] 📥 Invoke: rag_used={rag_used}, user_input={user_input[:50]}... ---")

        # 根据 rag_used 参数决定是否预先设置工具调用
        if rag_used == "on":
            # 强制使用 RAG，跳过决策节点，直接设置工具调用
            if self.timem_rag_client:
                initial_state["tool_calls"] = [ToolCall(tool_name="TimeMRAGTool", query=user_input)]
                initial_state["thought"] = "RAG模式已开启，强制调用RAG工具"
                print(f"--- [ADK] ✅ RAG ON 模式: 已预设 tool_call for query: {user_input[:50]}... ---")
            else:
                initial_state["thought"] = "RAG模式已开启，但太忆RAG服务未配置"
                print(f"--- [ADK] ❌ RAG ON 模式: 但 RAG 客户端未配置 ---")
        elif rag_used == "off":
            # 强制关闭 RAG，跳过决策节点
            initial_state["thought"] = "RAG模式已关闭，不调用任何工具"
            print(f"--- [ADK] 🔒 RAG OFF 模式: 禁用工具调用 ---")
        # rag_used == "auto" 时，保持默认行为，让决策节点决定
        else:
            print(f"--- [ADK] 🤖 RAG AUTO 模式: 将由决策节点决定 ---")

        # 运行 Graph，传递config
        if config:
            final_state = self.graph.invoke(initial_state, config)
        else:
            final_state = self.graph.invoke(initial_state)

        # 提取最终结果
        final_message_obj = final_state["messages"][-1]
        final_message = final_message_obj.content
        if not isinstance(final_message, str):
            final_message = str(final_message)
        reasoning_content = None
        if hasattr(final_message_obj, "additional_kwargs"):
            reasoning_content = final_message_obj.additional_kwargs.get("reasoning_content")

        invoke_elapsed = (time.perf_counter() - invoke_start) * 1
        print(f"\n{'='*60}")
        print(f"⏱️ [ADK性能] ChatFlow.invoke 总耗时: {invoke_elapsed:.2f}s")
        print(f"{'='*60}\n")

        return {
            "response": final_message,
            "reasoning_content": reasoning_content,
            "thought_process": final_state.get("thought"),
            "tool_results": final_state.get("tool_results"),
            "full_history": final_state["messages"]
        }

    async def astream(self, user_input: str, history: List[AnyMessage] = None, config: RunnableConfig = None, rag_used: str = "auto"):
        """
        异步流式调用 ChatFlow。

        由于旧版 LangGraph 不支持 get_stream_writer，
        我们使用 updates 模式运行图到 prepare_for_generation 节点，
        然后手动执行流式 LLM 调用。

        流式事件契约(均为 LangGraph updates 风格的 dict):
        1. 决策事件(auto/on/off 模式下均会在决策节点完成后推送一次)::
            {"agent_decision": {"thought": "...", "tool_calls": [{"tool_name": ..., "query": ...}]}}
        2. 思维链增量(reasoning 模型专有, 0~N 次)::
            {"stream_response": {"messages": [AIMessageChunk(content="", additional_kwargs={"reasoning_content": "..."})]}}
        3. 正文增量(0~N 次)::
            {"stream_response": {"messages": [AIMessageChunk(content="...")]}}

        Args:
            user_input: 用户输入
            history: 对话历史
            config: 可选的配置对象，包含运行时配置（如timem_kb_id）
            rag_used: RAG使用模式 ("auto", "on", "off")
                - auto: 启动决策节点，由AI决定是否使用RAG
                - on: 默认打开RAG，跳过决策节点
                - off: 默认关闭RAG，跳过决策节点
        """
        if history is None:
            history = []

        # 添加最新的用户消息
        history.append(HumanMessage(content=user_input))

        # 验证 kb_id：RAG 模式下必传
        target_kb_id = None
        if config:
            target_kb_id = config.get("configurable", {}).get("timem_kb_id")
        if rag_used != "off" and not target_kb_id:
            raise ValueError(
                f"rag_used='{rag_used}' 但未提供 kb_id 知识库 ID。"
                f"请通过 ChatAgent.chat(kb_id='your_kb_id') 传入，"
                f"或通过 ChatFlow.astream(config=RunnableConfig(configurable={{'timem_kb_id': 'your_kb_id'}})) 传入。"
            )

        initial_state = ChatFlowState(
            messages=history,
            thought=None,
            tool_calls=[],
            tool_results=[],
            reply_suggestion=None,
            session_title_suggestion=None,
            rag_used=rag_used
        )

        # 添加调试信息
        print(f"--- [ADK] 📥 Invoke: rag_used={rag_used}, user_input={user_input[:50]}... ---")

        # 根据 rag_used 参数决定是否预先设置工具调用
        if rag_used == "on":
            # 强制使用 RAG，跳过决策节点，直接设置工具调用
            if self.timem_rag_client:
                initial_state["tool_calls"] = [ToolCall(tool_name="TimeMRAGTool", query=user_input)]
                initial_state["thought"] = "RAG模式已开启，强制调用RAG工具"
                print(f"--- [ADK] ✅ RAG ON 模式: 已预设 tool_call for query: {user_input[:50]}... ---")
            else:
                initial_state["thought"] = "RAG模式已开启，但太忆RAG服务未配置"
                print(f"--- [ADK] ❌ RAG ON 模式: 但 RAG 客户端未配置 ---")
        elif rag_used == "off":
            # 强制关闭 RAG，跳过决策节点
            initial_state["thought"] = "RAG模式已关闭，不调用任何工具"
            print(f"--- [ADK] 🔒 RAG OFF 模式: 禁用工具调用 ---")
        # rag_used == "auto" 时，保持默认行为，让决策节点决定
        else:
            print(f"--- [ADK] 🤖 RAG AUTO 模式: 将由决策节点决定 ---")

        if self.adk_config.debug:
            print(f"DEBUG [astream]: Starting with stream_mode='updates'...")
        chain = None
        prompt_input = None

        # 使用 updates 模式运行图，传递config
        try:
            if config:
                stream_iter = self.graph.astream(initial_state, stream_mode="updates", config=config)
            else:
                stream_iter = self.graph.astream(initial_state, stream_mode="updates")

            async for event in stream_iter:
                node_name = list(event.keys())[0] if event else None
                if self.adk_config.debug:
                    print(f"DEBUG [astream]: Node completed: {node_name}")

                if node_name == "agent_decision":
                    # 推送决策 thought 事件(一次性, 调用方可选消费)
                    node_output = event.get("agent_decision", {})
                    yield {
                        "agent_decision": {
                            "thought": node_output.get("thought"),
                            "tool_calls": [
                                tc.model_dump() if hasattr(tc, "model_dump") else tc
                                for tc in node_output.get("tool_calls", [])
                            ]
                        }
                    }

                if node_name == "prepare_for_generation":
                    # 捕获 chain 和 prompt_input
                    node_output = event.get("prepare_for_generation", {})
                    chain = node_output.get("chain")
                    prompt_input = node_output.get("prompt_input")
                    if self.adk_config.debug:
                        print(f"DEBUG [astream]: Got chain={chain is not None}, prompt_input={prompt_input is not None}")

                    # 现在手动执行流式 LLM 调用
                    if chain and prompt_input:
                        if self.adk_config.debug:
                            print("DEBUG [astream]: Starting manual LLM streaming...")
                        chunk_count = 0
                        try:
                            async for chunk in chain.astream(prompt_input):
                                chunk_count += 1
                                # 拆分思维链增量与正文增量, 分别推送
                                reasoning_delta, content_delta = _extract_stream_parts(chunk)

                                if reasoning_delta:
                                    yield {
                                        "stream_response": {
                                            "messages": [AIMessageChunk(
                                                content="",
                                                additional_kwargs={"reasoning_content": reasoning_delta},
                                                id="stream"
                                            )]
                                        }
                                    }
                                if content_delta:
                                    if self.adk_config.debug:
                                        print(f"DEBUG [astream]: Chunk #{chunk_count}: {content_delta!r}")
                                    yield {
                                        "stream_response": {
                                            "messages": [AIMessageChunk(content=content_delta, id="stream")]
                                        }
                                    }
                            if self.adk_config.debug:
                                print(f"DEBUG [astream]: LLM streaming finished. Total chunks: {chunk_count}")
                        except Exception as e:
                            print(f"--- [ADK] LLM streaming error: {_explain_llm_error(e)} ---")
                            if self.adk_config.debug:
                                import traceback
                                traceback.print_exc()

                    # 不再继续执行 stream_response 节点，因为我们已经手动处理了
                    break
                    
        except Exception as e:
            print(f"--- [ADK] Graph error: {e} ---")
            if self.adk_config.debug:
                import traceback
                traceback.print_exc()

def create_chatflow(
    name: str,
    adk_config: Optional[ADKConfig] = None,
    **kwargs
) -> ChatFlow:
    """创建对话流"""
    return ChatFlow(name=name, adk_config=adk_config, **kwargs)
