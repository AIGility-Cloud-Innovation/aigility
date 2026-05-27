# Embedding Wrapper
"""
Embedding model wrapper with usage tracking and pre-computation support.

Wraps any LangChain Embeddings instance to:
1. Track token usage via adapter's get_last_usage() if available
2. Support pre-computed embeddings to prevent double embedding in vector stores
"""

from contextlib import contextmanager
from typing import Dict, List, Optional

from langchain_core.embeddings import Embeddings

from ..usage_tracking import TokenUsage


class EmbeddingWrapper(Embeddings):
    """Wraps an Embeddings instance with usage tracking and pre-computation cache."""

    def __init__(self, embedding: Embeddings):
        self._embedding = embedding
        self._last_usage: Optional[TokenUsage] = None
        self._precomputed: Optional[Dict[str, List[float]]] = None

    def embed_query(self, text: str) -> List[float]:
        if self._precomputed and text in self._precomputed:
            return self._precomputed[text]
        result = self._embedding.embed_query(text)
        self._extract_usage([text])
        return result

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if self._precomputed:
            return [
                self._precomputed.get(t, self._embedding.embed_query(t))
                for t in texts
            ]
        result = self._embedding.embed_documents(texts)
        self._extract_usage(texts)
        return result

    def _extract_usage(self, texts: List[str]):
        if hasattr(self._embedding, "get_last_usage"):
            self._last_usage = self._embedding.get_last_usage()
        else:
            total_chars = sum(len(t) for t in texts)
            estimated = total_chars // 2
            self._last_usage = TokenUsage(
                input_tokens=estimated,
                total_tokens=estimated,
            )

    @property
    def last_usage(self) -> Optional[TokenUsage]:
        return self._last_usage

    def reset_usage(self):
        self._last_usage = None

    @contextmanager
    def use_precomputed(self, texts: List[str], embeddings: List[List[float]]):
        """Context manager to serve pre-computed embeddings during vector store add."""
        self._precomputed = dict(zip(texts, embeddings))
        try:
            yield
        finally:
            self._precomputed = None


__all__ = ["EmbeddingWrapper"]
