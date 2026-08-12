"""AIGility ADK.

Top-level imports are deliberately lazy so an optional subsystem such as RAG
does not prevent a standalone subsystem such as ``aigility.memory`` from being
used or tested.
"""

from importlib import import_module
from typing import TYPE_CHECKING

__version__ = "2.0.1"
__author__ = "AIGility Cloud Innovation"
__email__ = "contact@aigility.com"
__description__ = "Agent Development Kit - 智能体开发框架"

if TYPE_CHECKING:
    from . import chat, chatflow, conversation, memory, rag, workflow
    from .client import ADKClient, ADKClientBuilder, create_client


_LAZY_EXPORTS = {
    "ADKClient": (".client", "ADKClient"),
    "ADKClientBuilder": (".client", "ADKClientBuilder"),
    "create_client": (".client", "create_client"),
    "memory": (".memory", None),
    "conversation": (".conversation", None),
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
    "ADKClient",
    "ADKClientBuilder",
    "create_client",
    "memory",
    "conversation",
    "chat",
    "chatflow",
    "workflow",
    "rag",
    "__version__",
    "__author__",
    "__email__",
    "__description__",
]
