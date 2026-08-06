"""
AIGility ADK - Agent Development Kit

基于 LangGraph/LangChain 的智能体开发框架，提供：
- chat: 基础对话能力
- chatflow: 对话流管理
- workflow: 工作流引擎
- rag: RAG 检索增强生成
- memory: 记忆管理
"""

from importlib import import_module
from typing import TYPE_CHECKING

__version__ = "0.1.3"
__author__ = "AIGility Cloud Innovation"
__email__ = "contact@aigility.com"
__description__ = "Agent Development Kit - 智能体开发框架"

if TYPE_CHECKING:
    from . import chat, chatflow, memory, rag, workflow
    from .client import ADKClient, ADKClientBuilder, create_client


_LAZY_EXPORTS = {
    "ADKClient": (".client", "ADKClient"),
    "create_client": (".client", "create_client"),
    "memory": (".memory", None),
    "chat": (".chat", None),
    "chatflow": (".chatflow", None),
    "workflow": (".workflow", None),
    "rag": (".rag", None),
}


def __getattr__(name: str):
    try:
        module_name, attribute = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = import_module(module_name, __name__)
    value = module if attribute is None else getattr(module, attribute)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))

__all__ = [
    # 主客户端
    "ADKClient",
    "ADKClientBuilder",
    "create_client",

    # 模块
    "memory",
    "chat",
    "chatflow",
    "workflow",
    "rag",

    # 元信息
    "__version__",
    "__author__",
    "__email__",
    "__description__",
]
