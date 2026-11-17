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
    _bm25_bucket_key,
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


def _make_bm25_service(
    doc_meta: List[Optional[Dict[str, Any]]],
    scores: List[float],
    bucket_filters: Optional[List[Dict[str, Any]]] = None,
) -> RAGService:
    svc = _bare_service()
    from collections import OrderedDict
    import threading

    svc._bm25_built = True
    svc._bm25_index = _FakeBM25Index(scores)
    svc._bm25_doc_mapping = {
        idx: {"content": f"doc-{idx}", "metadata": meta or {}, "point_id": str(idx)}
        for idx, meta in enumerate(doc_meta)
    }
    svc._bm25_buckets = OrderedDict()
    svc._bm25_lock = threading.RLock()
    for raw_filter in bucket_filters or []:
        normalized = _normalize_filter_keys(raw_filter) or {}
        svc._bm25_buckets[_bm25_bucket_key(normalized)] = {
            "index": svc._bm25_index,
            "mapping": svc._bm25_doc_mapping,
            "corpus": [],
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
        bucket_filters=[{"metadata.user_id": "alice"}],
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
        bucket_filters=[{"metadata.user_id": "alice", "kb_id": "kb1"}],
    )
    results = svc._bm25_search("revenue report", top_k=3, filter={"metadata.user_id": "alice", "kb_id": "kb1"})
    assert len(results) == 1
    doc, _ = results[0]
    assert doc.metadata == {"user_id": "alice", "kb_id": "kb1"}


def test_bm25_search_tenant_without_hits_returns_empty():
    svc = _make_bm25_service(
        doc_meta=[{"user_id": "alice"}],
        scores=[1.0],
        bucket_filters=[{"metadata.user_id": "carol"}],
    )
    assert svc._bm25_search("revenue report", top_k=3, filter={"metadata.user_id": "carol"}) == []


def test_bm25_search_ignores_zero_score_docs():
    svc = _make_bm25_service(
        doc_meta=[{"user_id": "alice"}, {"user_id": "alice"}],
        scores=[0.0, 2.0],
        bucket_filters=[{"metadata.user_id": "alice"}],
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


def test_bm25_search_with_filter_does_not_fall_back_to_global_index():
    svc = _make_bm25_service(
        doc_meta=[{"user_id": "bob"}],
        scores=[9.0],
    )
    assert svc._bm25_search("revenue report", top_k=2, filter={"metadata.user_id": "alice"}) == []


def test_invalidate_bm25_drops_only_the_matching_bucket():
    svc = _make_bm25_service(
        doc_meta=[{"user_id": "alice", "kb_id": "kb1"}],
        scores=[1.0],
        bucket_filters=[
            {"user_id": "alice", "kb_id": "kb1"},
            {"user_id": "bob", "kb_id": "kb2"},
        ],
    )
    svc._invalidate_bm25({"metadata.user_id": "alice", "metadata.kb_id": "kb1"})
    assert svc._bm25_search("revenue report", top_k=1, filter={"user_id": "alice", "kb_id": "kb1"}) == []
    assert _bm25_bucket_key(_normalize_filter_keys({"user_id": "bob", "kb_id": "kb2"})) in svc._bm25_buckets


def test_delete_document_scrolls_with_tenant_payload_path():
    from types import SimpleNamespace

    captured = {}

    class _Client:
        def scroll(self, **kwargs):
            captured["filter"] = kwargs["scroll_filter"]
            return [], None

        def overwrite_payload(self, **kwargs):
            raise AssertionError("没有命中点时不应写 payload")

    svc = _bare_service()
    svc.config = SimpleNamespace(
        vector_store=SimpleNamespace(provider="qdrant", collection_name="timem_knowledge")
    )
    svc.vector_store = SimpleNamespace(client=_Client(), collection_name="timem_knowledge")
    svc._bm25_buckets = {}
    svc._bm25_lock = __import__("threading").RLock()
    svc._bm25_built = False
    svc._bm25_index = None
    svc._bm25_doc_mapping = {}
    svc._bm25_corpus = []

    ok = svc.delete_document(
        file_hash="abc",
        filter={"metadata.user_id": "alice", "metadata.kb_id": "kb1"},
    )

    assert ok is False
    keys = [item.key for item in captured["filter"].must]
    assert "metadata.file_hash" in keys
    assert "metadata.user_id" in keys
    assert "metadata.kb_id" in keys


def test_hybrid_returns_bm25_when_semantic_is_empty():
    from langchain_core.documents import Document

    svc = _make_bm25_service(
        doc_meta=[{"user_id": "alice", "kb_id": "kb1"}],
        scores=[2.0],
        bucket_filters=[{"metadata.user_id": "alice", "metadata.kb_id": "kb1"}],
    )
    svc.config = SimpleNamespace(search_top_k=5)
    svc._embedding_wrapper = SimpleNamespace(last_usage=None, reset_usage=lambda: None)
    hit = Document(page_content="doc-0", metadata={"user_id": "alice", "kb_id": "kb1"})

    def _no_semantic(query, k=5, filter=None):
        return []

    svc._search_with_filter = _no_semantic
    svc._format_search_results = lambda docs, expand: docs[0].page_content
    svc.build_bm25_index = lambda *args, **kwargs: None

    result = svc.search_bm25_hybrid(
        "revenue report",
        filter={"metadata.user_id": "alice", "metadata.kb_id": "kb1"},
    )

    assert result.documents
    assert result.documents[0].page_content == hit.page_content
    assert result.metadata.get("bm25_only") is True
