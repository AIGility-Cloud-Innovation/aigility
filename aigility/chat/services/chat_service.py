import uuid
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel as LangchainBaseModel, Field as LangchainField
from aigility.chat.schema import ChatRequest, ChatResponse
from aigility.chat_flow import ChatFlowService, LLMConfig

class ChatService:
    """
    Chat 模块的服务层，负责处理聊天请求，并调用 ChatFlowService。
    """
    def __init__(self, llm_config: LLMConfig = LLMConfig()):
        # 初始化 LLM 配置
        self.llm_config = llm_config
        self.llm = self.llm_config.get_client()
        
        # 初始化 ChatFlowService，注入 LLM 配置
        self.chat_flow_service = ChatFlowService(llm_config=self.llm_config)

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
        if flow_result.get("tool_result        # 格式化工具结果
        tool_results_list = []
        if flow_result.get("tool_results"):
            for tr in flow_result["tool_results"]:
                tool_results_list.append({
                    "tool_name": tr.tool_name,
                    "result": tr.result
                })
        
        # 独立调用标题和建议生成方法
        session_title = self.generate_session_title(request.user_input, flow_result["response"])
        reply_suggestions = self.generate_reply_suggestions(flow_result["response"])

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
