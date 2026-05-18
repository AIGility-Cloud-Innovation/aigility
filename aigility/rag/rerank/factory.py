# Rerank 工厂
"""
Rerank 工厂 - 根据配置动态加载对应的 rerank 适配器

支持的 provider:
- dashscope: 阿里云 DashScope (qwen3-rerank)
"""

from typing import TYPE_CHECKING

from .base import BaseRerankAdapter

if TYPE_CHECKING:
    from aigility.rag.config import RerankConfig


class RerankFactory:
    """Rerank 工厂（根据 provider 创建对应实例）"""

    @staticmethod
    def get_reranker(config: "RerankConfig") -> BaseRerankAdapter:
        """
        工厂核心方法：根据配置的 provider 返回对应 rerank 适配器实例

        Args:
            config: Rerank 配置

        Returns:
            BaseRerankAdapter 实例
        """
        provider = config.provider

        if provider == "dashscope":
            from .dashscope import DashScopeRerankAdapter
            reranker = DashScopeRerankAdapter.load(config)
        else:
            raise ValueError(
                f"不支持的 Rerank 提供商: {provider} | "
                f"支持的类型: ['dashscope']"
            )

        if not isinstance(reranker, BaseRerankAdapter):
            raise RuntimeError(f"{provider} 适配器未继承 BaseRerankAdapter")

        return reranker


__all__ = ["RerankFactory"]
