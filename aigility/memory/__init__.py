"""
ADK Memory - 记忆管理模块

提供记忆的添加、搜索、管理等功能。
基于 Provider 架构实现。

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

from .memory import Memory
from .config import MemoryConfig, MemoryProviderConfig
from .providers.timem import TimemMemoryProvider
from .providers.base import BaseMemoryProvider
from .providers.factory import MemoryProviderFactory

__all__ = [
    "Memory",
    "MemoryConfig",
    "MemoryProviderConfig",
    "TimemMemoryProvider",
    "BaseMemoryProvider",
    "MemoryProviderFactory",
]

