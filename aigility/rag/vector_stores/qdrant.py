# vector_stores/qdrant.py
"""
Qdrant 向量库适配器

使用前需要安装: pip install qdrant-client langchain-community

本地运行 Qdrant:
    docker pull qdrant/qdrant
    docker run -p 6333:6333 -p 6334:6334 \
        -v "$(pwd)/qdrant_storage:/qdrant/storage:z" \
        qdrant/qdrant
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.vectorstores import VectorStore
    from ..config import VectorStoreConfig

class QdrantAdapter:
    """Qdrant 向量库适配器"""

    @staticmethod
    def load(config: "VectorStoreConfig", embedding: "Embeddings") -> "VectorStore":
        """
        加载 Qdrant 向量库（支持本地和远程模式）

        Args:
            config: 向量库配置
            embedding: 嵌入模型实例

        Returns:
            LangChain VectorStore 实例
        """
        # 延迟导入
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
        except ImportError:
            raise ImportError(
                "使用 Qdrant 向量库需要安装: "
                "pip install qdrant-client"
            )

        # 1. 获取连接配置
        url = config.get_url() if hasattr(config, 'get_url') else (
            config.url or "http://localhost:6333"
        )

        # 2. 检测 Embedding 模型的实际维度
        test_vector = embedding.embed_query("维度测试")
        actual_dim = len(test_vector)

        # 3. 创建 Qdrant 客户端（带兼容性包装）
        try:
            # 从 kwargs 中提取额外的客户端配置
            client_kwargs = config.kwargs.get("client_kwargs", {})

            # 如果配置中指定了 api_key，则使用云端模式
            if config.kwargs.get("api_key"):
                client = QdrantClient(
                    url=url,
                    api_key=config.kwargs.get("api_key"),
                    **client_kwargs
                )
            else:
                # 本地模式
                client = QdrantClient(
                    url=url,
                    **client_kwargs
                )

            # 测试连接
            client.get_collections()
            print(f"✅ Qdrant 连接成功：{url}")

            # 为客户端添加兼容的 search 方法（如果不存在）
            if not hasattr(client, 'search'):
                from types import MethodType

                class SearchResults:
                    """模拟旧版 search 方法的返回结果"""
                    def __init__(self, query_response):
                        self._response = query_response

                    def __iter__(self):
                        # 使结果可迭代
                        for point in self._response.points:
                            yield point

                def _search_method(self, collection_name, query_vector, limit=10, with_payload=True, **kwargs):
                    """兼容旧 API：将 search 映射到 query_points"""
                    # 调用新版 API
                    result = self.query_points(
                        collection_name=collection_name,
                        query=query_vector,
                        limit=limit,
                        with_payload=with_payload,
                        **kwargs
                    )
                    # 返回兼容的结果对象
                    return SearchResults(result)

                # 动态添加 search 方法
                client.search = MethodType(_search_method, client)

        except Exception as e:
            raise ConnectionError(f"Qdrant 连接失败：{str(e)}") from e

        # 4. 检查集合是否存在，不存在则创建
        collections = client.get_collections().collections
        collection_names = [col.name for col in collections]

        if config.collection_name not in collection_names:
            print(f"📦 创建新集合：{config.collection_name}")
            client.create_collection(
                collection_name=config.collection_name,
                vectors_config=VectorParams(
                    size=actual_dim,
                    distance=Distance.COSINE
                )
            )
            print(f"✅ 集合创建成功，向量维度：{actual_dim}")

            # 新建集合时自动创建 Payload Index
            if config.payload_index.enabled and config.payload_index.auto_create:
                QdrantAdapter._create_payload_indexes(client, config)

        # 5. 创建向量存储 - 优先使用 langchain_community
        try:
            from langchain_community.vectorstores import Qdrant
            print("✓ 使用 langchain_community.vectorstores.Qdrant")

            vector_store = Qdrant(
                client=client,
                collection_name=config.collection_name,
                embeddings=embedding,  # 注意：这里使用 embeddings（复数）
                **config.kwargs.get("vectorstore_kwargs", {})
            )

            # 验证返回的对象是 VectorStore 而不是 QdrantClient
            print(f"   DEBUG: vector_store type = {type(vector_store)}")
            print(f"   DEBUG: has similarity_search = {hasattr(vector_store, 'similarity_search')}")
            print(f"   DEBUG: has add_documents = {hasattr(vector_store, 'add_documents')}")

            return vector_store
        except ImportError:
            raise ImportError(
                "使用 Qdrant 向量库需要安装: "
                "pip install langchain-community qdrant-client"
            )


    @staticmethod
    def ensure_payload_indexes(client, config: "VectorStoreConfig"):
        """
        确保 Payload Index 已创建（对外接口）

        可在服务启动时或手动调用，为已有 collection 补建索引。
        对已存在的索引幂等，可重复调用。

        Args:
            client: QdrantClient 实例
            config: VectorStoreConfig 配置
        """
        QdrantAdapter._create_payload_indexes(client, config)

    @staticmethod
    def _create_payload_indexes(client, config: "VectorStoreConfig"):
        """
        为 collection 创建 Payload Index

        对已有字段建立倒排索引，加速带 filter 的检索操作。
        create_payload_index 对已存在的索引幂等，不会报错。

        Args:
            client: QdrantClient 实例
            config: VectorStoreConfig 配置
        """
        try:
            from qdrant_client.models import PayloadSchemaType
        except ImportError:
            return

        index_config = config.payload_index
        if not index_config.enabled:
            return

        field_schema_map = index_config.get_field_schema_map()
        created = 0

        for field_name, field_schema in field_schema_map.items():
            try:
                client.create_payload_index(
                    collection_name=config.collection_name,
                    field_name=field_name,
                    field_schema=field_schema,
                )
                created += 1
            except Exception as e:
                # 索引已存在时 Qdrant 会抛异常，忽略即可
                logging.debug(f"Payload index '{field_name}' skip: {e}")

        if created > 0:
            print(f"✅ Payload Index 已创建：{created}/{len(field_schema_map)} 个字段")


__all__ = ["QdrantAdapter"]

