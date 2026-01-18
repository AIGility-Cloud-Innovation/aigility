# vector_stores/chroma.py
"""
Chroma 向量库适配器

使用前需要安装: pip install chromadb langchain-chroma
"""

import os
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.vectorstores import VectorStore
    from ..config import VectorStoreConfig


class ChromaAdapter:
    """Chroma 向量库适配器"""
    
    @staticmethod
    def load(config: "VectorStoreConfig", embedding: "Embeddings") -> "VectorStore":
        """
        加载 Chroma 向量库（自动适配 Embedding 维度）
        """
        # 延迟导入
        try:
            from langchain_chroma import Chroma
        except ImportError:
            raise ImportError(
                "使用 Chroma 向量库需要安装: "
                "pip install chromadb langchain-chroma"
            )
        
        # 1. 获取持久化路径
        persist_path = config.get_persist_path() if hasattr(config, 'get_persist_path') else (
            config.persist_path or "./chroma_db"
        )
        
        # 2. 检测 Embedding 模型的实际维度
        test_vector = embedding.embed_query("维度测试")
        actual_dim = len(test_vector)
        print(f"🔍 检测到 Embedding 维度：{actual_dim}")

        # 3. 如果维度不匹配，删除旧的 Chroma 集合
        chroma_dir = os.path.join(persist_path, config.collection_name)
        if os.path.exists(chroma_dir):
            try:
                old_chroma = Chroma(
                    collection_name=config.collection_name,
                    embedding_function=embedding,
                    persist_directory=persist_path
                )
                old_chroma.get(limit=1)
            except Exception as e:
                if "dimension" in str(e).lower():
                    print(f"⚠️ 维度不匹配，删除旧集合")
                    shutil.rmtree(chroma_dir)
        
        # 4. 创建新的 Chroma 实例
        chroma = Chroma(
            collection_name=config.collection_name,
            embedding_function=embedding,
            persist_directory=persist_path,
            **config.kwargs
        )

        # 5. 更新配置的预期维度
        config.expected_dim = actual_dim

        return chroma


__all__ = ["ChromaAdapter"]
