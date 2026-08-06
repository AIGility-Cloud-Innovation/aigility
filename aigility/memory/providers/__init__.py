from importlib import import_module
from typing import TYPE_CHECKING

from .base import BaseMemoryProvider
from .factory import MemoryProviderFactory

if TYPE_CHECKING:
    from .timem import TimemMemoryProvider


def __getattr__(name: str):
    if name != "TimemMemoryProvider":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(".timem", __name__), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))

__all__ = [
    "BaseMemoryProvider",
    "TimemMemoryProvider",
    "MemoryProviderFactory"
]
