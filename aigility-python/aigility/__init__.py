# aigility/__init__.py
"""
Aigility Python SDK

一个模块化的 AI 能力库，提供：
- RAG (检索增强生成)
- Chat (对话服务)
- ChatFlow (对话流程)

使用方式:
    from aigility.rag import RAGService, RAGConfig
    from aigility.chat import ChatService
    from aigility.chat_flow import ChatFlowService
"""

__version__ = "0.1.0"

# 延迟导入，避免强制依赖
def __getattr__(name):
    if name == "rag":
        from . import rag
        return rag
    if name == "chat":
        from . import chat
        return chat
    if name == "chat_flow":
        from . import chat_flow
        return chat_flow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["rag", "chat", "chat_flow", "__version__"]
