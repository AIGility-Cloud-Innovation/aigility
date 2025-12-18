# /aigility/rag/vector_stores/faiss.py
import os
import pickle
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from ..config import VectorStoreConfig

class FAISSAdapter:
    @staticmethod
    def load(config: VectorStoreConfig, embedding: Embeddings) -> VectorStore:
        """加载FAISS向量库（极简，无任何外部依赖）"""
        # 1. 定义FAISS持久化路径（默认：./storage/faiss）
        faiss_path = config.persist_path or "./storage/faiss"
        os.makedirs(faiss_path, exist_ok=True)
        index_path = os.path.join(faiss_path, f"{config.collection_name}.index")

        # 2. 加载/创建FAISS索引
        if os.path.exists(index_path):
            # 加载已有索引
            faiss_db = FAISS.load_local(
                folder_path=faiss_path,
                embeddings=embedding,
                index_name=config.collection_name,
                allow_dangerous_deserialization=True  # 本地使用可开启
            )
            print(f"✅ 加载已有FAISS索引：{index_path}")
        else:
            # 创建新索引（空初始化）
            faiss_db = FAISS.from_texts(
                texts=["初始化FAISS索引"],
                embedding=embedding
            )
            # 保存索引到本地
            faiss_db.save_local(
                folder_path=faiss_path,
                index_name=config.collection_name
            )
            print(f"✅ 创建新FAISS索引：{index_path}")

        return faiss_db