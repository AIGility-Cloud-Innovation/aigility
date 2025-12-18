# vector_stores/chroma.py
import os
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from ..config import VectorStoreConfig

import shutil
# 向量库类型枚举



class ChromaAdapter:
    @staticmethod
    def load(config: VectorStoreConfig, embedding: Embeddings) -> VectorStore:
        """
        加载Chroma向量库（自动适配Embedding维度）
        """
        # 1. 检测Embedding模型的实际维度
        test_vector = embedding.embed_query("维度测试")
        actual_dim = len(test_vector)
        print(f"🔍 检测到Embedding维度：{actual_dim}")

        # 2. 如果维度不匹配，删除旧的Chroma集合（核心修复）
        chroma_dir = os.path.join(config.persist_path, config.collection_name)
        if os.path.exists(chroma_dir):
            # 检查现有集合的维度（读取Chroma的元数据）
            try:
                # 尝试加载旧集合，检测维度
                old_chroma = Chroma(
                    collection_name=config.collection_name,
                    embedding_function=embedding,
                    persist_directory=config.persist_path
                )
                # 触发维度检测（查询一条数据）
                old_chroma.get(limit=1)
            except Exception as e:
                if "dimension" in str(e).lower():
                    print(f"⚠️ 维度不匹配（旧：{config.expected_dim or '未知'}，新：{actual_dim}），删除旧集合")
                    # 删除旧集合目录，重建
                    shutil.rmtree(chroma_dir)
        
        # 3. 创建新的Chroma实例（自动使用当前Embedding的维度）
        chroma = Chroma(
            collection_name=config.collection_name,
            embedding_function=embedding,
            persist_directory=config.persist_path,
            **config.kwargs
        )

        # 4. 更新配置的预期维度（便于后续校验）
        config.expected_dim = actual_dim

        return chroma