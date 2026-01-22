"""
Memory Provider 工厂类

根据配置动态创建不同的 Provider 实例。
"""

import logging
from typing import Union

from .base import BaseMemoryProvider
from .timem import TimemMemoryProvider

logger = logging.getLogger(__name__)


class MemoryProviderFactory:
    """
    Memory Provider 工厂类

    根据配置动态创建不同的 Provider 实例。
    """

    @staticmethod
    def create_provider(config) -> BaseMemoryProvider:
        """
        根据 Provider 配置创建对应的 Provider 实例

        Args:
            config: MemoryProviderConfig 配置对象

        Returns:
            BaseMemoryProvider 实例

        Raises:
            ValueError: 不支持的 provider 类型
        """
        provider_type = config.provider

        if provider_type == "timem":
            return TimemMemoryProvider(config)
        elif provider_type == "custom":
            # 预留给用户自定义 Provider
            raise ValueError(
                "custom provider 需要用户自行实现。"
                "请继承 BaseMemoryProvider 并传入自定义 Provider 类。"
            )
        else:
            raise ValueError(
                f"不支持的 provider 类型: {provider_type}。"
                f"支持的类型: timem, custom"
            )


__all__ = ["MemoryProviderFactory"]
