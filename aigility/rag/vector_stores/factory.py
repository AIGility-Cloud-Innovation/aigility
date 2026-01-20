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

        elif provider == "qdrant":
            from .qdrant import QdrantAdapter
            vector_store = QdrantAdapter.load(config, embedding)

        else:
            raise ValueError(
                f"不支持的向量库：{provider} | "
                f"支持的类型：['chroma', 'faiss', 'milvus', 'qdrant']"
            )
        
        # 3. 校验 VectorStore 接口
        if not hasattr(vector_store, "add_documents") or not hasattr(vector_store, "similarity_search"):
            raise TypeError(f"{provider} 适配器未返回标准 VectorStore 对象")
        
        return vector_store


__all__ = ["VectorStoreFactory"]

# ====================== 测试代码 ======================
if __name__ == "__main__":
    import os
    import sys
    import warnings

    # 抑制第三方库的警告
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="runpy")

    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _package_dir = os.path.dirname(os.path.dirname(_current_dir))
    if _package_dir not in sys.path:
        sys.path.insert(0, _package_dir)

    from langchain_core.documents import Document
    from aigility.rag.config import EmbeddingConfig, VectorStoreConfig
    from aigility.rag.embeddings.factory import EmbeddingFactory

    print("=" * 60)
    print("向量库工厂测试")
    print("=" * 60)

    # ========== 配置 Embedding 模型 ==========
    print("\n【步骤 1】配置 Embedding 模型")
    print("-" * 60)

    # 使用 HuggingFace 本地模型进行测试（无需 API Key）
    embedding_config = EmbeddingConfig(
        provider="huggingface",
        model_name="BAAI/bge-small-zh-v1.5"
    )
    print(f"✓ Embedding Provider: {embedding_config.provider}")
    print(f"✓ 模型: {embedding_config.model_name}")

    try:
        embedding_model = EmbeddingFactory.get_embedding_model(embedding_config)
        print(f"✓ Embedding 模型加载成功")

        # 测试嵌入
        test_text = "这是一个测试文本"
        test_embedding = embedding_model.embed_query(test_text)
        print(f"✓ 嵌入维度: {len(test_embedding)}")
    except Exception as e:
        print(f"❌ Embedding 模型加载失败: {str(e)}")
        print("   提示：请安装 sentence-transformers: pip install sentence-transformers")
        sys.exit(1)

    # ========== 测试 Qdrant 向量库 ==========
    print("\n【测试 1】Qdrant 向量库")
    print("-" * 60)

    try:
        qdrant_config = VectorStoreConfig(
            provider="qdrant",
            collection_name="test_collection",
            url="http://localhost:6333"
        )
        print(f"✓ 配置: provider={qdrant_config.provider}")
        print(f"✓ 集合名称: {qdrant_config.collection_name}")
        print(f"✓ 服务地址: {qdrant_config.get_url()}")

        # 创建向量库
        qdrant_store = VectorStoreFactory.get_vector_store(qdrant_config, embedding_model)
        print(f"✓ 向量库类型: {type(qdrant_store).__name__}")

        # 准备测试文档
        test_documents = [
            Document(page_content="人工智能是计算机科学的一个分支", metadata={"id": 1}),
            Document(page_content="机器学习是人工智能的核心技术", metadata={"id": 2}),
            Document(page_content="深度学习基于神经网络算法", metadata={"id": 3}),
        ]
        print(f"\n📝 添加测试文档: {len(test_documents)} 个")

        # 添加文档
        qdrant_store.add_documents(test_documents)
        print(f"✓ 文档添加成功")

        # 相似性搜索
        query = "什么是神经网络"
        print(f"\n🔍 搜索查询: {query}")

        results = qdrant_store.similarity_search(query, k=2)
        print(f"✓ 找到 {len(results)} 个相关文档:")
        for i, doc in enumerate(results, 1):
            print(f"   {i}. {doc.page_content}")

        print("\n✅ Qdrant 测试通过！")

    except ConnectionError as e:
        print(f"⚠️  跳过 Qdrant 测试：无法连接到 Qdrant 服务")
        print(f"   错误: {str(e)}")
        print("   提示：请先启动 Qdrant 服务：")
        print("   docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant")
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("   请安装: pip install qdrant-client langchain-community")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n💡 提示：")
    print("   - 本地测试推荐使用 Chroma 或 FAISS")
    print("   - 生产环境推荐使用 Qdrant 或 Milvus")
    print("   - 如需测试 Qdrant，请先启动服务：")
    print("     docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant")

