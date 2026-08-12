"""
ADK Memory - 记忆管理模块

提供记忆写入、检索和 Provider 管理功能。
核心 contracts 与具体 Provider 实现分离，便于接入其他记忆服务。

使用示例:
    from aigility.memory import Memory, MemoryConfig, MemoryProviderConfig

    # 方式1: 使用默认配置（从环境变量读取）
    memory = Memory()

    # 方式2: 使用自定义配置
    config = MemoryConfig(
        provider=MemoryProviderConfig(
            provider="timem",
            api_key="sk-xxx"
        )
    )
    memory = Memory(config=config)
"""

from importlib import import_module
from typing import TYPE_CHECKING

from .memory import Memory
from .config import MemoryConfig, MemoryProviderConfig
from .contracts import (
    ConversationScope,
    MemoryCapabilities,
    MemoryError,
    MemoryIdentity,
    MemoryProviderError,
    MemoryRecord,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryStatus,
    MemoryWriteRequest,
    MemoryWriteResult,
)
from .providers.base import BaseMemoryProvider
from .providers.factory import MemoryProviderFactory

if TYPE_CHECKING:
    from .providers.timem import TimemMemoryProvider


def __getattr__(name: str):
    if name != "TimemMemoryProvider":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(".providers.timem", __name__), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))

__all__ = [
    "Memory",
    "MemoryCapabilities",
    "MemoryConfig",
    "MemoryError",
    "MemoryIdentity",
    "MemoryProviderError",
    "MemoryProviderConfig",
    "TimemMemoryProvider",
    "BaseMemoryProvider",
    "MemoryProviderFactory",
    "MemoryRecord",
    "MemorySearchRequest",
    "MemorySearchResult",
    "MemoryStatus",
    "MemoryWriteRequest",
    "MemoryWriteResult",
    "ConversationScope",
]
