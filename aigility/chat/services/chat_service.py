import uuid
from typing import List, Dict, Any
from aigility.chat.schema import ChatRequest, ChatResponse
from aigility.chat_flow import ChatFlowService, ChatFlowState

class ChatService:
    """
    Chat 模块的服务层，负责处理聊天请求，并调用 ChatFlowService。
    """
    def __init__(self):
        # 初始化 ChatFlowService
        # 注意：由于没有实现 CheckpointSaver，每次调用都是无状态的，
        # 历史记录需要由调用方（如 API 层）传入。
        self.chat_flow_service = ChatFlowService()

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
        
        # 调用 ChatFlowService
        flow_result = self.chat_flow_service.invoke(
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
                tool_results_list.append({
                    "tool_name": tr.tool_name,
                    "result": tr.result
                })

        # 构建 ChatResponse
        response = ChatResponse(
            response=flow_result["response"],
            session_id=session_id,
            session_title=flow_result.get("session_title"),
            reply_suggestions=reply_suggestions,
            thought_process=flow_result.get("thought_process"),
            tool_results=tool_results_list
        )
        
        return response

# --- 辅助函数：生成会话标题和回复建议的接口 ---

    def generate_session_title(self, user_input: str, ai_response: str) -> str:
        """
        生成会话标题的接口（通过调用 ChatFlowService 的逻辑实现）。
        """
        # 实际应用中，可以调用一个简化的 LLM 链或复用 ChatFlowService 中的逻辑
        # 由于 ChatFlowService.invoke 已经返回了 session_title，这里可以简化
        # 但为了模拟一个独立的接口，我们可以在 ChatFlowService 中添加一个专门的链
        # 考虑到通用性，我们直接使用 ChatFlowService.invoke 的结果
        
        # 模拟一个简化的调用，只关注标题生成
        # 实际生产中，会有一个专门的、更轻量的 LLM 调用
        
        # 再次调用 ChatFlowService (效率较低，仅为演示接口存在)
        flow_result = self.chat_flow_service.invoke(user_input=user_input)
        return flow_result.get("session_title", "新会话")

    def generate_reply_suggestions(self, ai_response: str) -> List[str]:
        """
        生成回复建议的接口（通过调用 ChatFlowService 的逻辑实现）。
        """
        # 再次调用 ChatFlowService (效率较低，仅为演示接口存在)
        # 实际生产中，会有一个专门的、更轻量的 LLM 调用
        
        # 模拟一个简化的调用，只关注建议生成
        flow_result = self.chat_flow_service.invoke(user_input="请根据以下回复生成3个后续问题建议：" + ai_response)
        
        reply_suggestions = []
        if flow_result.get("reply_suggestions"):
            reply_suggestions = [s.strip() for s in flow_result["reply_suggestions"].split(',') if s.strip()]
            
        return reply_suggestions
