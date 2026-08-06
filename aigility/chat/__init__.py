"""
ADK Chat - 基础对话模块

基于 LangChain 提供基础对话能力。
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agent import ChatAgent, create_chat_agent
    from .schema import ChatRequest, ChatResponse
    from .service import ChatService


_LAZY_EXPORTS = {
    "ChatAgent": (".agent", "ChatAgent"),
    "create_chat_agent": (".agent", "create_chat_agent"),
    "ChatService": (".service", "ChatService"),
    "ChatRequest": (".schema", "ChatRequest"),
    "ChatResponse": (".schema", "ChatResponse"),
}


def __getattr__(name: str):
    try:
        module_name, attribute = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))

__all__ = [
    "ChatAgent",
    "create_chat_agent",
    "ChatService",
    "ChatRequest",
    "ChatResponse",
]
