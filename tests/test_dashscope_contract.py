"""No-network contracts for the DashScope embedding and rerank extras."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.optional_dashscope


def test_embedding_dashscope_extra_initializes_the_public_factory_boundary():
    """The embedding extra must install the SDK used by the public factory."""
    import dashscope

    from aigility.rag import EmbeddingConfig
    from aigility.rag.embeddings import EmbeddingFactory

    assert hasattr(dashscope, "TextEmbedding")

    embedding = EmbeddingFactory.get_embedding_model(
        EmbeddingConfig(
            provider="dashscope",
            model_name="text-embedding-v3",
            api_key="test-key",
        )
    )

    assert callable(embedding.embed_query)
    assert callable(embedding.embed_documents)


def test_rerank_dashscope_extra_initializes_the_public_factory_boundary():
    """The rerank extra must install the SDK used by the public factory."""
    import dashscope

    from aigility.rag import RerankConfig, RerankFactory
    from aigility.rag.rerank import BaseRerankAdapter

    assert hasattr(dashscope, "TextReRank")

    reranker = RerankFactory.get_reranker(
        RerankConfig(
            enabled=True,
            provider="dashscope",
            model_name="qwen3-rerank",
            api_key="test-key",
        )
    )

    assert isinstance(reranker, BaseRerankAdapter)
    assert callable(reranker.rerank)
