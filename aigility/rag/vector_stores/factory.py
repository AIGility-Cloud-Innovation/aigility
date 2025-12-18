# vector_stores/factory.py
from langchain_core.vectorstores import VectorStore
from langchain_core.embeddings import Embeddings
from typing import List, Dict, Any, Optional
from ..config import VectorStoreConfig
from .chroma import ChromaAdapter
from .milvus import MilvusAdapter
from .faiss import FAISSAdapter
class VectorStoreFactory:
    """向量库工厂（核心：根据provider创建对应实例）"""
    
    # 注册表：新增向量库只需在这里加映射
    _VECTOR_STORE_ADAPTERS = {
        "chroma": ChromaAdapter,
        "milvus": MilvusAdapter,
        "faiss": FAISSAdapter
    }

    @staticmethod
    def get_vector_store(config: VectorStoreConfig, embedding: Embeddings) -> VectorStore:
        """
        生产标准化VectorStore对象（兼容所有LangChain Embeddings）
        :param config: 向量库配置
        :param embedding: 注入的Embedding模型实例
        :return: 标准化的LangChain VectorStore实例
        """
        # 1. 校验Embedding接口（前置拦截）
        if not hasattr(embedding, "embed_documents") or not hasattr(embedding, "embed_query"):
            raise TypeError(f"注入的Embedding [{type(embedding).__name__}] 未实现LangChain接口")
        
        # 2. 校验provider支持情况
        if config.provider not in VectorStoreFactory._VECTOR_STORE_ADAPTERS:
            raise ValueError(
                f"不支持的向量库：{config.provider} | 支持的类型：{list(VectorStoreFactory._VECTOR_STORE_ADAPTERS.keys())}"
            )
        
        # 3. 创建适配器实例
        adapter_cls = VectorStoreFactory._VECTOR_STORE_ADAPTERS[config.provider]
        vector_store = adapter_cls.load(config, embedding)
        
        # 4. 校验VectorStore接口（后置拦截）
        if not hasattr(vector_store, "add_documents") or not hasattr(vector_store, "similarity_search"):
            raise TypeError(f"{config.provider}适配器未返回标准VectorStore对象")
        
        return vector_store

# SDK 对外暴露工厂类
__all__ = ["VectorStoreFactory"]