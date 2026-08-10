from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class ChatRequest(BaseModel):
    """用户发送的聊天请求模型"""
    user_input: str = Field(..., description="用户输入的文本内容")
    session_id: Optional[str] = Field(None, description="会话ID，用于恢复历史记录")
    kb_id: Optional[str] = Field(None, description="知识库ID，用于指定RAG检索的知识库")
    rag_used: Literal["auto", "on", "off"] = Field(
        default="auto",
        description="""RAG使用模式:
- auto: 启动决策节点，由AI决定是否使用RAG
- on: 默认打开RAG，跳过决策节点
- off: 默认关闭RAG，跳过决策节点"""
    )
    
class ChatResponse(BaseModel):
    """聊天回复模型"""
    response: str = Field(..., description="AI生成的最终回复")
    session_id: str = Field(..., description="当前会话ID")
    session_title: Optional[str] = Field(None, description="会话标题建议")
    reply_suggestions: List[str] = Field(..., description="后续回复建议列表")
    thought_process: Optional[str] = Field(None, description="Agent的思维链(CoT)过程，用于调试和监控")
    reasoning_content: Optional[str] = Field(None, description="推理模型(reasoning模式)生成的原生思维链内容")
    tool_results: Optional[List[dict]] = Field(None, description="工具调用结果列表，用于调试和监控")
