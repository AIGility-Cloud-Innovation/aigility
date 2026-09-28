"""租户过滤（多租户单全局 collection）单元测试。

覆盖 fe7d4d50 引入的 tenant filter 的两个关键语义:
  1. langchain 向量库 dict filter 的键相对 payload.metadata（内部自动补
     metadata. 前缀），对外 payload 路径风格键（metadata.user_id）必须归一化,
     否则生成 metadata.metadata.user_id 条件导致语义检索恒为空;
  2. BM25 语料在单全局 collection 下包含所有租户 chunk, _bm25_search 必须
     在 top_k 截断之前应用租户过滤, 且与语义侧过滤语义一致。

均使用 RAGService.__new__ 白盒构造, 不连接真实向量库。
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

import pytest

from aigility.rag.service import (
    RAGService,
    _matches_metadata_filter,
    _normalize_filter_keys,
)


def _bare_service() -> RAGService:
    """绕过 __init__（不连接向量库/不加载 Embedding），仅装配检索所需字段"""
    return RAGService.__new__(RAGService)


class _FakeBM25Index:
    """固定打分的 BM25 替身: get_scores 返回预设分数"""

    def __init__(self, scores: List[float]):
        self._scores = scores

    def get_scores(self, tokens):
        assert tokens, "查询分词不应为空"
        return list(self._scores)


def _make_bm25_service(doc_meta: List[Optional[Dict[str, Any]]], scores: List[float]) -> RAGService:
    svc = _bare_service()
    svc._bm25_built = True
    svc._bm25_index = _FakeBM25Index(scores)
    svc._bm25_doc_mapping = {
        idx: {"content": f"doc-{idx}", "metadata": meta or {}, "point_id": str(idx)}
        for idx, meta in enumerate(doc_meta)
    }
    return svc


class _CapturingVectorStore:
    """记录 similarity_search 收到的 filter 参数"""

    def __init__(self, docs=None):
        self.captured_filters = []
        self._docs = docs or []

    def similarity_search(self, query, k=4, filter=None, **kwargs):
        self.captured_filters.append(filter)
        return self._docs[:k]


# ── 键归一化 ─────────────────────────────────────────────────────


def test_normalize_filter_keys_strips_metadata_prefix():
    assert _normalize_filter_keys({"metadata.user_id": "u1", "metadata.kb_id": "kb1"}) == {
        "user_id": "u1",
        "kb_id": "kb1",
    }


def test_normalize_filter_keys_keeps_plain_keys():
    # 兼容直接传 metadata 顶层键（如 is_deleted）的写法
    assert _normalize_filter_keys({"user_id": "u1", "is_deleted": False}) == {
        "user_id": "u1",
        "is_deleted": False,
    }


def test_normalize_filter_keys_passthrough_for_empty():
    assert _normalize_filter_keys(None) is None
    assert _normalize_filter_keys({}) == {}


def test_matches_metadata_filter_requires_all_keys():
    meta = {"user_id": "u1", "kb_id": "kb1"}
    assert _matches_metadata_filter(meta, {"user_id": "u1"})
    assert _matches_metadata_filter(meta, {"user_id": "u1", "kb_id": "kb1"})
    assert not _matches_metadata_filter(meta, {"user_id": "u2"})
    assert not _matches_metadata_filter(meta, {"user_id": "u1", "kb_id": "kb2"})
    assert not _matches_metadata_filter(meta, {"user_id": None})


# ── BM25 侧租户过滤 ──────────────────────────────────────────────


def test_bm25_search_without_filter_returns_top_k():
    # 行为不变: 无 filter 时按分数取 top_k
    svc = _make_bm25_service(
        doc_meta=[{"user_id": "alice"}, {"user_id": "bob"}, {"user_id": "alice"}],
        scores=[0.2, 5.0, 3.0],
    )
    results = svc._bm25_search("revenue report", top_k=2)
    assert [doc.metadata["user_id"] for doc, _ in results] == ["bob", "alice"]


def test_bm25_search_filters_by_tenant_before_top_k():
    # 核心场景: bob 的分数更高, 但 filter 限定 alice → 必须返回 alice 的最高分文档,
    # 而不是被其他租户挤占名额
    svc = _make_bm25_service(
        doc_meta=[{"user_id": "alice"}, {"user_id": "bob"}, {"user_id": "alice"}, {"user_id": "bob"}],
        scores=[0.2, 5.0, 3.0, 4.0],
    )
    results = svc._bm25_search("revenue report", top_k=2, filter={"metadata.user_id": "alice"})
    assert [doc.metadata["user_id"] for doc, _ in results] == ["alice", "alice"]
    assert [score for _, score in results] == [3.0, 0.2]


def test_bm25_search_multi_key_filter():
    svc = _make_bm25_service(
        doc_meta=[
            {"user_id": "alice", "kb_id": "kb1"},
            {"user_id": "alice", "kb_id": "kb2"},
            {"user_id": "bob", "kb_id": "kb1"},
        ],
        scores=[1.0, 2.0, 3.0],
    )
    results = svc._bm25_search("revenue report", top_k=3, filter={"metadata.user_id": "alice", "kb_id": "kb1"})
    assert len(results) == 1
    doc, _ = results[0]
    assert doc.metadata == {"user_id": "alice", "kb_id": "kb1"}


def test_bm25_search_tenant_without_hits_returns_empty():
    svc = _make_bm25_service(
        doc_meta=[{"user_id": "alice"}],
        scores=[1.0],
    )
    assert svc._bm25_search("revenue report", top_k=3, filter={"metadata.user_id": "carol"}) == []


def test_bm25_search_ignores_zero_score_docs():
    svc = _make_bm25_service(
        doc_meta=[{"user_id": "alice"}, {"user_id": "alice"}],
        scores=[0.0, 2.0],
    )
    results = svc._bm25_search("revenue report", top_k=2, filter={"metadata.user_id": "alice"})
    assert len(results) == 1  # score<=0 的候选不进入结果


# ── 语义侧 filter 键传递（归一化生效） ────────────────────────────


def test_search_with_filter_normalizes_qdrant_filter_keys():
    # langchain_community 的 Qdrant 会把 dict filter 的键补上 metadata. 前缀,
    # 因此服务层必须传顶层键; 传 metadata.user_id 会生成 metadata.metadata.user_id
    svc = _bare_service()
    svc.config = SimpleNamespace(vector_store=SimpleNamespace(provider="qdrant"))
    fake_vs = _CapturingVectorStore()
    svc.vector_store = fake_vs

    svc._search_with_filter("revenue report", k=5, filter={"metadata.user_id": "u1", "metadata.kb_id": "kb1"})

    assert fake_vs.captured_filters == [
        {"is_deleted": False, "user_id": "u1", "kb_id": "kb1"}
    ]


def test_search_with_filter_without_tenant_keeps_default():
    svc = _bare_service()
    svc.config = SimpleNamespace(vector_store=SimpleNamespace(provider="qdrant"))
    fake_vs = _CapturingVectorStore()
    svc.vector_store = fake_vs

    svc._search_with_filter("revenue report", k=5)

    assert fake_vs.captured_filters == [{"is_deleted": False}]


def test_search_with_filter_fallback_branch_applies_tenant():
    # 非 chroma/qdrant 的手动过滤分支也要隔离租户
    from langchain_core.documents import Document

    docs = [
        Document(page_content="a", metadata={"user_id": "alice", "is_deleted": False}),
        Document(page_content="b", metadata={"user_id": "bob", "is_deleted": False}),
        Document(page_content="c", metadata={"user_id": "alice", "is_deleted": True}),
    ]
    svc = _bare_service()
    svc.config = SimpleNamespace(vector_store=SimpleNamespace(provider="faiss"))
    svc.vector_store = _CapturingVectorStore(docs)

    results = svc._search_with_filter("revenue report", k=3, filter={"metadata.user_id": "alice"})

    assert [doc.page_content for doc in results] == ["a"]
