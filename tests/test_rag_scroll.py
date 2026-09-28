"""Qdrant scroll 翻页单元测试。

不连接真实向量库。覆盖游标翻页、单页、偏移不前进，以及 BM25
构建失败时不替换已有语料。
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List, Optional, Tuple

import pytest

from aigility.rag.service import (
    RAGService,
    SCROLL_PAGE_SIZE,
    QdrantScrollError,
    scroll_all_points,
)


def _bare_service() -> RAGService:
    return RAGService.__new__(RAGService)


def _point(point_id: str, content: str, is_deleted: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        id=point_id,
        payload={
            "page_content": content,
            "metadata": {"is_deleted": is_deleted, "file_name": content},
        },
    )


class _PagingClient:
    """按预设页依次返回 (points, next_offset)。"""

    def __init__(self, pages: List[Tuple[List[Any], Optional[Any]]]):
        self._pages = list(pages)
        self.calls: List[dict] = []

    def scroll(self, **kwargs):
        self.calls.append(kwargs)
        if not self._pages:
            raise AssertionError("scroll 调用次数超过预设页数")
        return self._pages.pop(0)


class _FakeBM25:
    def __init__(self, corpus, k1=1.5, b=0.75, epsilon=0.25):
        self.corpus = corpus


def test_scroll_all_points_follows_offset_across_pages():
    client = _PagingClient([
        ([_point("a", "one")], "cursor-1"),
        ([_point("b", "two")], "cursor-2"),
        ([_point("c", "three")], None),
    ])

    points = scroll_all_points(client, "kb")

    assert [point.id for point in points] == ["a", "b", "c"]
    assert [call["offset"] for call in client.calls] == [None, "cursor-1", "cursor-2"]
    assert all(call["limit"] == SCROLL_PAGE_SIZE for call in client.calls)
    assert all(call["with_vectors"] is False for call in client.calls)
    assert all(call["with_payload"] is True for call in client.calls)


def test_scroll_all_points_single_page_calls_once():
    client = _PagingClient([
        ([_point("a", "only")], None),
    ])

    points = scroll_all_points(client, "kb")

    assert [point.id for point in points] == ["a"]
    assert len(client.calls) == 1
    assert client.calls[0]["offset"] is None


def test_scroll_all_points_raises_when_offset_does_not_advance():
    client = _PagingClient([
        ([_point("a", "one")], "stuck"),
        ([_point("b", "two")], "stuck"),
    ])

    with pytest.raises(QdrantScrollError):
        scroll_all_points(client, "kb")

    assert [call["offset"] for call in client.calls] == [None, "stuck"]


def test_build_bm25_index_includes_points_after_first_page(monkeypatch):
    kept_later = _point("later", "second-page")
    deleted = _point("gone", "deleted-doc", is_deleted=True)
    kept_first = _point("early", "first-page")
    client = _PagingClient([
        ([deleted, kept_first], "next"),
        ([kept_later], None),
    ])

    svc = _bare_service()
    svc.vector_store = SimpleNamespace(client=client, collection_name="kb")
    svc._bm25_built = False
    svc._bm25_corpus = []
    svc._bm25_doc_mapping = {}
    svc._bm25_index = None
    svc._tokenize_for_bm25 = lambda text: [text]
    monkeypatch.setattr("aigility.rag.service._load_rank_bm25", lambda: _FakeBM25)

    svc.build_bm25_index()

    assert svc._bm25_corpus == [["first-page"], ["second-page"]]
    assert [item["content"] for item in svc._bm25_doc_mapping.values()] == [
        "first-page",
        "second-page",
    ]
    assert svc._bm25_built is True
    assert client.calls[0]["scroll_filter"] is not None
    excluded = client.calls[0]["scroll_filter"].must_not
    assert excluded[0].key == "metadata.is_deleted"
    assert excluded[0].match.value is True


def test_build_bm25_index_keeps_existing_index_when_scroll_fails():
    client = _PagingClient([])

    def _fail_scroll(**kwargs):
        raise QdrantScrollError("offset stuck")

    client.scroll = _fail_scroll

    svc = _bare_service()
    svc.vector_store = SimpleNamespace(client=client, collection_name="kb")
    svc._bm25_built = True
    svc._bm25_corpus = [["old"]]
    svc._bm25_doc_mapping = {0: {"content": "old", "metadata": {}, "point_id": "old"}}
    svc._bm25_index = "old-index"
    svc._tokenize_for_bm25 = lambda text: [text]

    svc.build_bm25_index(force_rebuild=True)

    assert svc._bm25_built is True
    assert svc._bm25_corpus == [["old"]]
    assert svc._bm25_index == "old-index"
    assert svc._bm25_doc_mapping[0]["content"] == "old"


def test_build_bm25_index_with_filter_scrolls_payload_path_and_skips_global_index(monkeypatch):
    alice = _point("a", "alice-doc")
    alice.payload["metadata"]["user_id"] = "alice"
    alice.payload["metadata"]["kb_id"] = "kb1"
    client = _PagingClient([
        ([alice], None),
    ])

    svc = _bare_service()
    svc.vector_store = SimpleNamespace(client=client, collection_name="timem_knowledge")
    svc._bm25_built = True
    svc._bm25_corpus = [["old-global"]]
    svc._bm25_doc_mapping = {0: {"content": "old-global", "metadata": {}, "point_id": "old"}}
    svc._bm25_index = "old-index"
    svc._tokenize_for_bm25 = lambda text: [text]
    monkeypatch.setattr("aigility.rag.service._load_rank_bm25", lambda: _FakeBM25)

    svc.build_bm25_index(filter={"metadata.user_id": "alice", "metadata.kb_id": "kb1"})

    must = client.calls[0]["scroll_filter"].must
    assert {item.key for item in must} == {"metadata.user_id", "metadata.kb_id"}
    assert svc._bm25_index == "old-index"
    assert svc._bm25_corpus == [["old-global"]]
    assert len(svc._bm25_buckets) == 1
    bucket = next(iter(svc._bm25_buckets.values()))
    assert bucket["corpus"] == [["alice-doc"]]
