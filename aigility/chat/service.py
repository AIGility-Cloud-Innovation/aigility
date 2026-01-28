import uuid
from typing import List, Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel as LangchainBaseModel, Field as LangchainField

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
        session_id = request.session_id if request.session_id else str(uuid.uuid4())
        
        # 模拟历史记录的获取（当前版本简化为只处理当前请求）
        # 在实际应用中，这里会从数据库或缓存中加载历史消息
        history = [] 
        
        # 调用 ChatFlow
        flow_result = self.chat_flow.invoke(
            user_input=request.user_input,
            history=history
        )
        
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
        response = ChatResponse(
            response=flow_result["response"],
            session_id=session_id,
            session_title=session_title,
            reply_suggestions=reply_suggestions,
            thought_process=flow_result.get("thought_process"),
            tool_results=tool_results_list
        )
        
        return response

    async def process_chat_stream(self, request: ChatRequest):
        """
        处理流式聊天请求。
        """
        session_id = request.session_id if request.session_id else str(uuid.uuid4())
        history = []
        
        async for event in self.chat_flow.astream(
            user_input=request.user_input,
            history=history
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
        timem_enabled=True,  # 启用太忆 RAG
        timem_api_key=os.getenv("TIMEM_API_KEY"),
        timem_base_url=os.getenv("TIMEM_BASE_URL")
    )

    # 创建聊天服务
    chat_service = ChatService(adk_config=config)

    # 构建聊天请求
    chat_request = ChatRequest(
        user_input="应届生毕业后档案有哪些去处？",
        session_id=None
    )

    # 处理聊天请求
    chat_response = chat_service.process_chat(chat_request)

    # 输出响应
    print("=" * 80)
    print("AI 回复:", chat_response.response)
    print("会话 ID:", chat_response.session_id)
    print("会话标题:", chat_response.session_title)
    print("回复建议:", chat_response.reply_suggestions)
    print("=" * 80)

    # 检查是否使用了 RAG
    print("\n【RAG 使用情况】")
    if chat_response.tool_results:
        print(f"✓ 使用了工具调用，共 {len(chat_response.tool_results)} 个工具被调用")

        # 检查是否有 RAG 相关的工具调用
        rag_used = False
        for i, tool_result in enumerate(chat_response.tool_results, 1):
            tool_name = tool_result.get("tool_name", "unknown")
            print(f"\n工具 {i}: {tool_name}")

            # 检查是否是 RAG 相关工具
            if "rag" in tool_name.lower() or "retriev" in tool_name.lower() or "search" in tool_name.lower():
                rag_used = True
                print("  → 这是一个 RAG 相关工具")

            # 打印工具结果（如果内容不太长）
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

    print("=" * 80)