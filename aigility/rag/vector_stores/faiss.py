# vector_stores/faiss.py
"""
FAISS 向量库适配器

使用前需要安装: pip install faiss-cpu langchain-community
"""

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.vectorstores import VectorStore
    from ..config import VectorStoreConfig


class FAISSAdapter:
    """FAISS 向量库适配器"""
    
    @staticmethod
    def load(config: "VectorStoreConfig", embedding: "Embeddings") -> "VectorStore":
        """加载 FAISS 向量库"""
        # 延迟导入
        try:
            from langchain_community.vectorstores import FAISS
        except ImportError:
            raise ImportError(
                "使用 FAISS 向量库需要安装: "
                "pip install faiss-cpu langchain-community"
            )
        
        # 1. 获取持久化路径
        faiss_path = config.get_persist_path() if hasattr(config, 'get_persist_path') else (
            config.persist_path or "./faiss_db"
        )
        os.makedirs(faiss_path, exist_ok=True)
        index_path = os.path.join(faiss_path, f"{config.collection_name}.index")

        # 2. 加载/创建 FAISS 索引
        if os.path.exists(index_path):
            faiss_db = FAISS.load_local(
                folder_path=faiss_path,
                embeddings=embedding,
                index_name=config.collection_name,
                allow_dangerous_deserialization=True
            )
            print(f"✅ 加载已有 FAISS 索引：{index_path}")
        else:
            faiss_db = FAISS.from_texts(
                texts=["初始化 FAISS 索引"],
                embedding=embedding
            )
            faiss_db.save_local(
                folder_path=faiss_path,
                index_name=config.collection_name
            )
            print(f"✅ 创建新 FAISS 索引：{index_path}")

        return faiss_db


__all__ = ["FAISSAdapter"]
