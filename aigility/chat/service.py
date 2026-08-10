import uuid
import time
from typing import List, Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel as LangchainBaseModel, Field as LangchainField
from langchain_core.runnables import RunnableConfig
from ..core.config import ADKConfig
from ..core.model_factory import ModelFactory
from ..chatflow.flow import ChatFlow
from .schema import ChatRequest, ChatResponse

class ChatService:
    """
    Chat 模块的服务层，负责处理聊天请求，并调用 ChatFlow。
    """
    def __init__(self, adk_config: Optional[ADKConfig] = None, flow_config: Optional[Dict[str, Any]] = None):
        # 初始化配置
        self.adk_config = adk_config or ADKConfig()
        self.llm = ModelFactory.create_llm(self.adk_config)
        
        # 初始化 ChatFlow
        self.chat_flow = ChatFlow(adk_config=self.adk_config, flow_config=flow_config)

    def process_chat(self, request: ChatRequest) -> ChatResponse:
        """
        处理聊天请求，调用 LangGraph ChatFlow。

        Args:
            request: 包含用户输入和会话ID的请求对象。

        Returns:
            包含 AI 回复、建议和流程信息的响应对象。
        """
        start_time = time.perf_counter()

        session_id = request.session_id if request.session_id else str(uuid.uuid4())
        # kb_id 必传校验（RAG 模式下）
        if request.rag_used != "off":
            timem_kb_id = request.kb_id or self.adk_config.timem_kb_id
            if not timem_kb_id:
                raise ValueError(
                    f"rag_used='{request.rag_used}' 但未提供 kb_id。"
                    f"请在 ChatRequest 中设置 kb_id，或在 ADKConfig.timem_kb_id 中设置默认值。"
                )
        else:
            timem_kb_id = request.kb_id or self.adk_config.timem_kb_id
        config = RunnableConfig(
        configurable={
            "timem_kb_id": timem_kb_id  # 优先用 request 中的 kb_id，否则用 adk_config 的默认值
        }
    )
        # 模拟历史记录的获取（当前版本简化为只处理当前请求）
        # 在实际应用中，这里会从数据库或缓存中加载历史消息
        history = []

        # 调用 ChatFlow
        flow_start = time.perf_counter()
        flow_result = self.chat_flow.invoke(
            user_input=request.user_input,
            history=history,
            config=config,
            rag_used=request.rag_used
        )
        flow_elapsed = (time.perf_counter() - flow_start) * 1

        print(f"\n{'─'*60}")
        print(f"⏱️ [ADK性能] ChatFlow.invoke 总耗时: {flow_elapsed:.2f}s")
        print(f"{'─'*60}\n")

        # 解析回复建议
        reply_suggestions = []
        if flow_result.get("reply_suggestions"):
            # 假设回复建议是逗号分隔的字符串
            reply_suggestions = [s.strip() for s in flow_result["reply_suggestions"].split(',') if s.strip()]
        
        # 格式化工具结果
        tool_results_list = []
        if flow_result.get("tool_results"):
            for tr in flow_result["tool_results"]:
                # tool_results might be a list of ToolResult objects or dicts depending on serialization
                if hasattr(tr, 'tool_name'):
                    tool_results_list.append({
                        "tool_name": tr.tool_name,
                        "result": tr.result
                    })
                elif isinstance(tr, dict):
                    tool_results_list.append(tr)
        
        # 独立调用标题和建议生成方法 (暂时禁用以提高性能)
        session_title = "新会话" # 使用默认值
        reply_suggestions = [] # 返回空列表

        # 构建 ChatResponse
        build_start = time.perf_counter()
        response = ChatResponse(
            response=flow_result["response"],
            session_id=session_id,
            session_title=session_title,
            reply_suggestions=reply_suggestions,
            thought_process=flow_result.get("thought_process"),
            tool_results=tool_results_list
        )
        build_elapsed = (time.perf_counter() - build_start) * 1
        total_elapsed = (time.perf_counter() - start_time) * 1

        print(f"⏱️ [ADK性能] 响应构建耗时: {build_elapsed:.2f}s")
        print(f"⏱️ [ADK性能] process_chat 总耗时: {total_elapsed:.2f}s\n")

        return response

    async def process_chat_stream(self, request: ChatRequest):
        """
        处理流式聊天请求。
        """
        session_id = request.session_id if request.session_id else str(uuid.uuid4())
        history = []
        # kb_id 必传校验（RAG 模式下）
        if request.rag_used != "off":
            timem_kb_id = request.kb_id or self.adk_config.timem_kb_id
            if not timem_kb_id:
                raise ValueError(
                    f"rag_used='{request.rag_used}' 但未提供 kb_id。"
                    f"请在 ChatRequest 中设置 kb_id，或在 ADKConfig.timem_kb_id 中设置默认值。"
                )
        else:
            timem_kb_id = request.kb_id or self.adk_config.timem_kb_id
        config = RunnableConfig(
        configurable={
            "timem_kb_id": timem_kb_id  # 优先用 request 中的 kb_id，否则用 adk_config 的默认值
        }
    )
        async for event in self.chat_flow.astream(
            user_input=request.user_input,
            history=history,
            config=config,
            rag_used=request.rag_used
        ):
            yield event

    # --- 独立服务：生成会话标题 ---

    def generate_session_title(self, user_input: str, ai_response: str) -> str:
        """
        即插即用的独立方法：根据对话内容生成会话标题。
        """
        class TitleOutput(LangchainBaseModel):
            title: str = LangchainField(description="A concise session title (max 15 characters).")

        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的标题生成器。请根据用户输入和AI回复，生成一个简洁的会话标题（不超过15个字）。"),
            ("human", f"用户输入: {user_input}\nAI回复: {ai_response}")
        ])
        
        chain = prompt | self.llm.with_structured_output(TitleOutput)
        
        try:
            result = chain.invoke({})
            return result.title
        except Exception as e:
            print(f"Title generation failed: {e}")
            return "新会话"

    # --- 独立服务：生成回复建议 ---

    def generate_reply_suggestions(self, ai_response: str) -> List[str]:
        """
        即插即用的独立方法：根据 AI 回复生成后续回复建议。
        """
        class SuggestionOutput(LangchainBaseModel):
            suggestions: List[str] = LangchainField(description="A list of 3 suggested follow-up questions or actions.")

        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的建议生成器。请根据AI的回复，生成3个用户可能感兴趣的后续问题或操作建议。"),
            ("human", f"AI回复: {ai_response}")
        ])
        
        chain = prompt | self.llm.with_structured_output(SuggestionOutput)
        
        try:
            result = chain.invoke({})
            return result.suggestions
        except Exception as e:
            print(f"Suggestion generation failed: {e}")
            return ["请重试", "报告错误"]
# --------------------
# 对聊天服务的测试
# --------------------
def print_test_header(title: str):
    """打印测试标题分隔符"""
    print("\n" + "=" * 80)
    print(f"  【测试】{title}")
    print("=" * 80 + "\n")


def print_rag_status(chat_response):
    """打印 RAG 使用情况"""
    print("\n【RAG 使用情况】")
    if chat_response.tool_results:
        print(f"✓ 使用了工具调用，共 {len(chat_response.tool_results)} 个工具被调用")

        rag_used = False
        for i, tool_result in enumerate(chat_response.tool_results, 1):
            tool_name = tool_result.get("tool_name", "unknown")
            print(f"\n工具 {i}: {tool_name}")

            if "rag" in tool_name.lower() or "retriev" in tool_name.lower() or "search" in tool_name.lower():
                rag_used = True
                print("  → 这是一个 RAG 相关工具")

            result = tool_result.get("result", "")
            if result:
                result_str = str(result)
                if len(result_str) > 500:
                    print(f"  结果预览: {result_str[:500]}...")
                else:
                    print(f"  结果: {result_str}")

        if rag_used:
            print("\n✓ 确认：本次对话使用了 RAG 检索增强功能")
        else:
            print("\n✗ 未检测到 RAG 工具调用")
    else:
        print("✗ 未使用任何工具调用（纯对话模式）")

    # 打印思考过程（如果有）
    if chat_response.thought_process:
        print("\n【思考过程】")
        print(chat_response.thought_process)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()  # 加载 .env 文件
    from aigility.core.config import ADKConfig
    from aigility.chat.service import ChatService
    from aigility.chat.schema import ChatRequest

    # 初始化配置（从环境变量读取 DeepSeek 配置）
    config = ADKConfig(
        llm_provider="deepseek",  # 使用 DeepSeek
        llm_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        llm_api_key=os.getenv("DEEPSEEK_API_KEY"),
        llm_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        timem_enabled=os.getenv("TIMEM_ENABLED", "true").lower() == "true",  # 启用太忆 RAG
        timem_api_key=os.getenv("TIMEM_API_KEY"),
        timem_base_url=os.getenv("TIMEM_BASE_URL")
    )

    # 创建聊天服务
    chat_service = ChatService(adk_config=config)

    # 测试用户输入
    test_query = "Mac的iCloud操作"
    test_kb_id = "kb_57220503e2eb"

    # ========== 测试 1: rag_used = "auto" ==========
    print_test_header("测试 1: rag_used = 'auto' (AI 自行决策)")

    chat_request_auto = ChatRequest(
        user_input=test_query,
        session_id="1",
        kb_id=test_kb_id,
        rag_used="auto"
    )

    chat_response_auto = chat_service.process_chat(chat_request_auto)

    print(f"\n📝 AI 回复: {chat_response_auto.response}")
    print(f"🆔 会话 ID: {chat_response_auto.session_id}")
    print_rag_status(chat_response_auto)

    # ========== 测试 2: rag_used = "on" ==========
    print_test_header("测试 2: rag_used = 'on' (强制使用 RAG)")

    chat_request_on = ChatRequest(
        user_input=test_query,
        session_id="2",
        kb_id=test_kb_id,
        rag_used="on"
    )

    chat_response_on = chat_service.process_chat(chat_request_on)

    print(f"\n📝 AI 回复: {chat_response_on.response}")
    print(f"🆔 会话 ID: {chat_response_on.session_id}")
    print_rag_status(chat_response_on)

    # ========== 测试 3: rag_used = "off" ==========
    print_test_header("测试 3: rag_used = 'off' (强制不使用 RAG)")

    chat_request_off = ChatRequest(
        user_input=test_query,
        session_id="3",
        kb_id=test_kb_id,
        rag_used="off"
    )

    chat_response_off = chat_service.process_chat(chat_request_off)

    print(f"\n📝 AI 回复: {chat_response_off.response}")
    print(f"🆔 会话 ID: {chat_response_off.session_id}")
    print_rag_status(chat_response_off)

    # ========== 测试对比总结 ==========
    print("\n" + "=" * 80)
    print("  【测试对比总结】")
    print("=" * 80)
    print(f"\n原始查询: {test_query}")
    print(f"知识库ID: {test_kb_id}\n")

    print("模式对比:")
    print(f"  1. auto 模式 - 工具调用数: {len(chat_response_auto.tool_results) if chat_response_auto.tool_results else 0}")
    print(f"  2. on   模式 - 工具调用数: {len(chat_response_on.tool_results) if chat_response_on.tool_results else 0}")
    print(f"  3. off  模式 - 工具调用数: {len(chat_response_off.tool_results) if chat_response_off.tool_results else 0}")
    print("\n" + "=" * 80)