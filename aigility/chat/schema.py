from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    """用户发送的聊天请求模型"""
    user_input: str = Field(..., description="用户输入的文本内容")
    session_id: Optional[str] = Field(None, description="会话ID，用于恢复历史记录（当前版本暂不实现存储）")
    
class ChatResponse(BaseModel):
    """聊天回复模型"""
    response: str = Field(..., description="AI生成的最终回复")
    session_id: str = Field(..., description="当前会话ID")
    session_title: Optional[str] = Field(None, description="会话标题建议")
    reply_suggestions: List[str] = Field(..., description="后续回复建议列表")
    thought_process: Optional[str] = Field(None, description="Agent的思维链(CoT)过程，用于调试和监控")
    tool_results: Optional[List[dict]] = Field(None, description="工具调用结果列表，用于调试和监控")
