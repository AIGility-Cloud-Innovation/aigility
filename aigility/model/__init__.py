"""
ADK Model - 模型层

提供 LLM 创建便捷入口。
"""

from .llm import create_llm
from .embeddings import EmbeddingProvider, create_embeddings

__all__ = [
    "create_llm",
    "EmbeddingProvider",
    "create_embeddings",
]

