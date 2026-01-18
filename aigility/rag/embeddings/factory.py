# [核心] 嵌入模型工厂
"""
嵌入模型工厂 - 根据配置动态加载对应的嵌入模型

支持的 provider:
- huggingface: 本地 HuggingFace 模型
- dashscope: 阿里云 DashScope 服务
- openai: OpenAI API
"""

from typing import TYPE_CHECKING
from ..config import EmbeddingConfig

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings


class EmbeddingFactory:
    """嵌入模型工厂（核心：根据 provider 创建对应实例）"""

    @staticmethod
    def get_embedding_model(config: EmbeddingConfig) -> "Embeddings":
        """
        工厂核心方法：根据配置的 provider 返回对应嵌入模型实例
        
        Args:
            config: 嵌入模型配置
            
        Returns:
            标准化的 LangChain Embeddings 实例
        """
        provider = config.provider
        
        if provider == "huggingface":
            from .huggingface import HuggingFaceEmbeddingAdapter
            embedding_model = HuggingFaceEmbeddingAdapter.load(config)
            
        elif provider == "dashscope":
            from .dashscope import DashScopeEmbeddingAdapter
            embedding_model = DashScopeEmbeddingAdapter.load(config)
            
        elif provider == "openai":
            # OpenAI 使用 LangChain 官方适配器
            try:
                from langchain_openai import OpenAIEmbeddings
            except ImportError:
                raise ImportError(
                    "使用 OpenAI 嵌入模型需要安装 langchain-openai: "
                    "pip install langchain-openai"
                )
            embedding_model = OpenAIEmbeddings(
                model=config.model_name,
                openai_api_key=config.get_api_key(),
                openai_api_base=config.get_base_url(),
            )
        else:
            raise ValueError(
                f"不支持的嵌入模型：{provider} | "
                f"支持的类型：['huggingface', 'dashscope', 'openai']"
            )
        
        # 校验接口
        if not hasattr(embedding_model, "embed_query") or not hasattr(embedding_model, "embed_documents"):
            raise RuntimeError(f"{provider} 适配器未实现 LangChain Embeddings 核心接口")
        
        return embedding_model


__all__ = ["EmbeddingFactory"]
