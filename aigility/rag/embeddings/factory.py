# [核心] 嵌入模型工厂

from langchain_core.embeddings import Embeddings
from ..config import EmbeddingConfig
from .dashscope import DashScopeEmbeddingAdapter
from .huggingface import HuggingFaceEmbeddingAdapter

class EmbeddingFactory:
    """嵌入模型工厂（核心：根据provider创建对应实例）"""
    # 注册表：新增模型只需在这里加映射，无需改其他代码
    _EMBEDDING_ADAPTERS = {
        "dashscope": DashScopeEmbeddingAdapter,
        "huggingface": HuggingFaceEmbeddingAdapter
    }

    @staticmethod
    def get_embedding_model(config: EmbeddingConfig) -> Embeddings:
        """
        工厂核心方法：根据配置的provider返回对应嵌入模型实例
        :param config: 嵌入模型配置
        :return: 标准化的LangChain Embeddings实例
        """
        # 1. 校验provider是否支持
        if config.provider not in EmbeddingFactory._EMBEDDING_ADAPTERS:
            raise ValueError(
                f"不支持的嵌入模型：{config.provider} | 支持的类型：{list(EmbeddingFactory._EMBEDDING_ADAPTERS.keys())}"
            )
        
        # 2. 创建适配器实例（所有适配器都实现LangChain Embeddings接口）
        adapter_cls = EmbeddingFactory._EMBEDDING_ADAPTERS[config.provider]
        embedding_model = adapter_cls.load(config)
        
        # 3. 校验接口（确保适配器实现了核心方法）
        if not hasattr(embedding_model, "embed_query") or not hasattr(embedding_model, "embed_documents"):
            raise RuntimeError(f"{config.provider}适配器未实现LangChain Embeddings核心接口")
        
        return embedding_model

# SDK 对外暴露工厂类
__all__ = ["EmbeddingFactory"]