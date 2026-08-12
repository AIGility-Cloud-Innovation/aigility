from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Literal

class ChatRequest(BaseModel):
    """用户发送的聊天请求模型"""
    user_input: str = Field(..., description="用户输入的文本内容")
    session_id: Optional[str] = Field(
        None,
        description="服务端签发的会话 ID；缺失时创建新的唯一会话",
    )
    idempotency_key: Optional[str] = Field(
        None,
        description="创建新会话时的可选幂等键；不会影响 session_id 的生成",
    )
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
    # 供应商返回的 token 使用量。它是计费审计数据，不向最终用户展示正文以外的内容。
    usage_metadata: Optional[Dict[str, Any]] = Field(None, description="模型用量元数据，包含 output_tokens 等")
    # ``False`` 明确表示模型生成失败、response 仅为可展示的友好错误文本；
    # ``None`` 保留给旧版/第三方 ChatFlow，避免新增字段破坏既有调用方。
    generation_succeeded: Optional[bool] = Field(
        None,
        description="模型正文是否成功生成；失败时调用方不得将 response 作为可计费输出",
    )
