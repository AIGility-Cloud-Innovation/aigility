# vector_stores/milvus.py
"""
Milvus 向量库适配器

使用前需要安装: pip install pymilvus langchain-community
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.vectorstores import VectorStore
    from ..config import VectorStoreConfig


class MilvusAdapter:
    """Milvus 向量库适配器"""
    
    @staticmethod
    def load(config: "VectorStoreConfig", embedding: "Embeddings") -> "VectorStore":
        """
        加载 Milvus 向量库（分布式，需提前启动 Milvus 服务）
        """
        # 延迟导入
        try:
            from langchain_community.vectorstores import Milvus
            from pymilvus import connections, Collection, utility
        except ImportError:
            raise ImportError(
                "使用 Milvus 向量库需要安装: "
                "pip install pymilvus langchain-community"
            )
        
        # 1. 获取连接 URL
        url = config.get_url() if hasattr(config, 'get_url') else (
            config.url or "http://localhost:19530"
        )
        
        # 2. 校验 Milvus 连接
        try:
            connections.connect(
                alias="default",
                uri=url,
                **config.kwargs.get("connection_args", {})
            )
        except Exception as e:
            raise ConnectionError(f"Milvus 连接失败：{str(e)}") from e
        
        # 3. 向量维度校验
        test_vector = embedding.embed_query("维度测试")
        dim = len(test_vector)
        if config.expected_dim and dim != config.expected_dim:
            raise ValueError(
                f"Milvus 适配失败：Embedding 维度 {dim} ≠ 预期 {config.expected_dim}"
            )
        
        # 4. 自动创建集合（若不存在）
        if not utility.has_collection(config.collection_name):
            from pymilvus import FieldSchema, CollectionSchema, DataType, IndexType
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512)
            ]
            schema = CollectionSchema(fields, description="RAG 知识库")
            collection = Collection(config.collection_name, schema)
            index_params = {
                "index_type": IndexType.IVF_FLAT,
                "metric_type": "L2",
                "params": {"nlist": 128}
            }
            collection.create_index("embedding", index_params)
            collection.load()
        
        # 5. 返回 Milvus VectorStore 实例
        return Milvus(
            embedding_function=embedding,
            collection_name=config.collection_name,
            connection_args={"uri": url},
            index_params=config.kwargs.get("index_params", {"nlist": 128}),
            **config.kwargs
        )


__all__ = ["MilvusAdapter"]
