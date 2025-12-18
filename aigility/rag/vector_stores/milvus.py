# vector_stores/milvus.py
from langchain_community.vectorstores import Milvus
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from ..config import VectorStoreConfig
from pymilvus import connections, Collection, utility

class MilvusAdapter:
    @staticmethod
    def load(config: VectorStoreConfig, embedding: Embeddings) -> VectorStore:
        """
        加载Milvus向量库（分布式，需提前启动Milvus服务）
        :param config: 向量库配置
        :param embedding: Embedding模型（LangChain接口）
        :return: Milvus VectorStore对象
        """
        # 1. 校验Milvus连接
        try:
            connections.connect(
                alias="default",
                uri=config.url,  
                **config.kwargs.get("connection_args", {})
            )
        except Exception as e:
            raise ConnectionError(f"Milvus连接失败：{str(e)}") from e
        
        # 2. 向量维度校验
        test_vector = embedding.embed_query("维度测试")
        dim = len(test_vector)
        if config.expected_dim and dim != config.expected_dim:
            raise ValueError(
                f"Milvus适配失败：Embedding维度{dim} ≠ 预期{config.expected_dim}"
            )
        
        # 3. 自动创建集合（若不存在）
        if not utility.has_collection(config.collection_name):
            from pymilvus import FieldSchema, CollectionSchema, DataType, IndexType
            # 定义集合schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512)
            ]
            schema = CollectionSchema(fields, description="RAG知识库")
            collection = Collection(config.collection_name, schema)
            # 创建索引（提升检索速度）
            index_params = {
                "index_type": IndexType.IVF_FLAT,
                "metric_type": "L2",
                "params": {"nlist": 128}
            }
            collection.create_index("embedding", index_params)
            collection.load()
        
        # 4. 返回Milvus VectorStore实例
        return Milvus(
            embedding_function=embedding,
            collection_name=config.collection_name,
            connection_args={"uri": config.url},
            # 适配Milvus索引参数
            index_params=config.kwargs.get("index_params", {"nlist": 128}),
            **config.kwargs
        )