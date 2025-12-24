# RAG module initialization
"""
RAG (Retrieval-Augmented Generation) 模块

使用方式:
    from aigility.rag import RAGService, RAGConfig, EmbeddingConfig, VectorStoreConfig
    
    config = RAGConfig(
        embedding=EmbeddingConfig(provider="dashscope", api_key="your-key"),
        vector_store=VectorStoreConfig(provider="chroma", persist_path="./my_db")
    )
    service = RAGService(config=config)
"""

from .service import RAGService
from .config import (
    RAGConfig,
    EmbeddingConfig,
    VectorStoreConfig,
    IngestionConfig,
)

__all__ = [
    "RAGService",
    "RAGConfig",
    "EmbeddingConfig",
    "VectorStoreConfig",
    "IngestionConfig",
]
