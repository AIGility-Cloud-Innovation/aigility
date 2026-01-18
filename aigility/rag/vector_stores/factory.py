# vector_stores/factory.py
"""
向量库工厂 - 根据配置动态加载对应的向量库

支持的 provider:
- chroma: 轻量级本地向量库
- faiss: 高性能本地向量库
- milvus: 分布式向量数据库
"""

from typing import TYPE_CHECKING
from ..config import VectorStoreConfig

if TYPE_CHECKING:
    from langchain_core.vectorstores import VectorStore
    from langchain_core.embeddings import Embeddings


class VectorStoreFactory:
    """向量库工厂（核心：根据 provider 创建对应实例）"""

    @staticmethod
    def get_vector_store(config: VectorStoreConfig, embedding: "Embeddings") -> "VectorStore":
        """
        生产标准化 VectorStore 对象
        
        Args:
            config: 向量库配置
            embedding: 注入的 Embedding 模型实例
            
        Returns:
            标准化的 LangChain VectorStore 实例
        """
        # 1. 校验 Embedding 接口
        if not hasattr(embedding, "embed_documents") or not hasattr(embedding, "embed_query"):
            raise TypeError(
                f"注入的 Embedding [{type(embedding).__name__}] 未实现 LangChain 接口"
            )
        
        provider = config.provider
        
        # 2. 延迟加载对应的适配器
        if provider == "chroma":
            from .chroma import ChromaAdapter
            vector_store = ChromaAdapter.load(config, embedding)
            
        elif provider == "faiss":
            from .faiss import FAISSAdapter
            vector_store = FAISSAdapter.load(config, embedding)
            
        elif provider == "milvus":
            from .milvus import MilvusAdapter
            vector_store = MilvusAdapter.load(config, embedding)
            
        else:
            raise ValueError(
                f"不支持的向量库：{provider} | "
                f"支持的类型：['chroma', 'faiss', 'milvus']"
            )
        
        # 3. 校验 VectorStore 接口
        if not hasattr(vector_store, "add_documents") or not hasattr(vector_store, "similarity_search"):
            raise TypeError(f"{provider} 适配器未返回标准 VectorStore 对象")
        
        return vector_store


__all__ = ["VectorStoreFactory"]
