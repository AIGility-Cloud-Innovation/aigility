# huggingface.py
"""
HuggingFace 嵌入模型适配器

使用前需要安装: pip install sentence-transformers langchain-huggingface
"""

import os
from typing import List, Optional, TYPE_CHECKING

from ..._optional import import_optional

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from aigility.rag.config import EmbeddingConfig

from ..usage_tracking import TokenUsage


class HuggingFaceEmbeddingAdapter:
    """HuggingFace 嵌入模型适配器（实现 LangChain Embeddings 接口）"""

    def __init__(self, config: "EmbeddingConfig"):
        embeddings = import_optional(
            "langchain_huggingface.embeddings",
            feature="HuggingFace embeddings",
            extra="embedding-huggingface",
            dependency="langchain-huggingface",
        )
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

        self.config = config

        # 处理默认参数
        kwargs = config.kwargs or {
            "model_kwargs": {"device": "cpu"},
            "encode_kwargs": {"normalize_embeddings": True}
        }

        # 直接返回 LangChain 的原生 Embeddings 对象，而不是包装它
        self._embedding = embeddings.HuggingFaceEmbeddings(
            model_name=config.model_name,
            **kwargs
        )
        self._last_usage: Optional[TokenUsage] = None

    @classmethod
    def load(cls, config: "EmbeddingConfig"):
        """工厂类调用的加载方法 - 直接返回 LangChain 原生对象"""
        embeddings = import_optional(
            "langchain_huggingface.embeddings",
            feature="HuggingFace embeddings",
            extra="embedding-huggingface",
            dependency="langchain-huggingface",
        )
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

        # 处理默认参数
        kwargs = config.kwargs or {
            "model_kwargs": {"device": "cpu"},
            "encode_kwargs": {"normalize_embeddings": True}
        }

        # 直接返回 LangChain 原生对象，不包装
        return embeddings.HuggingFaceEmbeddings(
            model_name=config.model_name,
            **kwargs
        )

    def embed_query(self, text: str) -> List[float]:
        """单文本嵌入（LangChain 强制接口）"""
        if not text.strip():
            return []
        result = self._embedding.embed_query(text.strip())
        total_chars = len(text.strip())
        estimated_tokens = total_chars // 2
        self._last_usage = TokenUsage(
            input_tokens=estimated_tokens,
            total_tokens=estimated_tokens,
            model=self.config.model_name,
        )
        return result

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """多文本批量嵌入（LangChain 强制接口）"""
        valid_texts = [t.strip() for t in texts if t.strip()]
        if not valid_texts:
            return []
        result = self._embedding.embed_documents(valid_texts)
        total_chars = sum(len(t) for t in valid_texts)
        estimated_tokens = total_chars // 2
        self._last_usage = TokenUsage(
            input_tokens=estimated_tokens,
            total_tokens=estimated_tokens,
            model=self.config.model_name,
        )
        return result

    def get_last_usage(self) -> Optional[TokenUsage]:
        return self._last_usage

    def reset_usage(self):
        self._last_usage = None

    def __call__(self, text: str) -> List[float]:
        """
        使适配器对象可调用，用于兼容 Qdrant 等需要直接调用 embedding 对象的场景

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        return self.embed_query(text)


__all__ = ["HuggingFaceEmbeddingAdapter"]
