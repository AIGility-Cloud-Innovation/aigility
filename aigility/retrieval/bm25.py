# -*- coding: utf-8 -*-
"""
通用 BM25 关键词检索器 (只读).

纯检索能力: 建索引 + 查询。不写入/修改/删除任何外部数据。
可作为 workflow 的 function_node 检索节点使用:

    index_directory(source_dir, index_path, exts)   # 一次性建索引
    search_docs(query, index_path, top_k)           # 查询
    retrieve_node(state)                            # workflow 节点 (BM25)
    recall_node(state)                              # workflow 节点 (记忆召回, 经 seam_caller)
"""

import hashlib
import json
import os
import re
import pickle
import asyncio
from typing import Any, Dict, List, Optional

__all__ = [
    "index_directory",
    "search_docs",
    "retrieve_node",
]

# 中文/英文混合分词: 中文按字词切块, 英文按单词
_SPLIT_RE = re.compile(r"[\u4e00-\u9fff]|[\u4e00-\u9fff][\u4e00-\u9fff]|[a-zA-Z0-9_]{2,}")


def _tokenize(text: str) -> List[str]:
    """简单中英混合分词 (BM25 用)."""
    if not text:
        return []
    return [t.lower() for t in _SPLIT_RE.findall(text) if t.strip()]


def _load_index(index_path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(index_path):
        return None
    try:
        with open(index_path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def _save_index(index: Dict[str, Any], index_path: str) -> None:
    os.makedirs(os.path.dirname(index_path) or ".", exist_ok=True)
    with open(index_path, "wb") as f:
        pickle.dump(index, f)


def index_directory(
    source_dir: str,
    index_path: str,
    exts: Optional[List[str]] = None,
    chunk_size: int = 500,
) -> Dict[str, Any]:
    """扫描目录下源码/文档文件, 建 BM25 索引并持久化.

    Args:
        source_dir: 待索引目录
        index_path: 索引持久化路径 (.pkl)
        exts: 文件扩展名过滤, 默认 [".py", ".md", ".mdx", ".yaml", ".yml", ".json"]
        chunk_size: 单块字符数

    Returns:
        {"ok": True, "files": n, "chunks": m}
    """
    exts = exts or [".py", ".md", ".mdx", ".yaml", ".yml", ".json"]
    chunks: List[Dict[str, str]] = []
    files = 0

    for root, _dirs, names in os.walk(source_dir):
        # 跳过常见噪音目录
        if any(x in root for x in ("node_modules", ".git", ".venv", "venv", "__pycache__", "dist", "build")):
            continue
        for name in names:
            if not name.endswith(tuple(exts)):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if not text.strip():
                continue
            files += 1
            for i in range(0, max(1, len(text)), chunk_size):
                chunk = text[i : i + chunk_size]
                if chunk.strip():
                    chunks.append({"file": path, "text": chunk})

    # 构建倒排: term → {doc_idx: freq}
    doc_terms: List[Dict[str, int]] = []
    for c in chunks:
        freq: Dict[str, int] = {}
        for t in _tokenize(c["text"]):
            freq[t] = freq.get(t, 0) + 1
        doc_terms.append(freq)

    index = {
        "chunks": chunks,
        "doc_terms": doc_terms,
        "doc_count": len(chunks),
        "avg_len": sum(sum(d.values()) for d in doc_terms) / max(1, len(doc_terms)),
    }
    _save_index(index, index_path)
    return {"ok": True, "files": files, "chunks": len(chunks)}


def _bm25_score(query_tokens: List[str], doc_terms: Dict[str, int], doc_len: int, avg_len: float, N: int, k1: float = 1.5, b: float = 0.75) -> float:
    score = 0.0
    for t in query_tokens:
        tf = doc_terms.get(t, 0)
        if tf == 0:
            continue
        idf = max(0.0, (N - len([d for d in doc_terms if t in d]) + 0.5) / (len([d for d in doc_terms if t in d]) + 0.5) + 1)
        score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / max(1, avg_len)))
    return score


def search_docs(query: str, index_path: str, top_k: int = 5) -> List[Dict[str, str]]:
    """BM25 检索, 返回 top_k 片段列表."""
    index = _load_index(index_path)
    if not index:
        return []
    chunks = index["chunks"]
    doc_terms = index["doc_terms"]
    N = index.get("doc_count", len(chunks))
    avg_len = index.get("avg_len", 100.0)

    q_tokens = _tokenize(query)
    if not q_tokens:
        return []

    scored = [
        (i, _bm25_score(q_tokens, dt, sum(dt.values()), avg_len, N))
        for i, dt in enumerate(doc_terms)
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [
        {
            "content": chunks[i]["text"],
            "file": chunks[i]["file"],
            "score": round(s, 4),
        }
        for i, s in scored[:top_k]
        if s > 0
    ]


def retrieve_node(state: Any) -> Dict[str, Any]:
    """workflow function_node: 知识库 BM25 检索.

    state 需含: query (或 user_input), index_path (业务侧传入索引文件路径)
    若无索引文件, 平滑返回空上下文.
    """
    if isinstance(state, dict):
        query = str(state.get("query") or state.get("user_input") or "")
        index_path = str(state.get("index_path") or "kb_index.json")
        top_k = int(state.get("top_k") or 5)
    else:
        query = str(getattr(state, "query", "") or getattr(state, "user_input", "") or "")
        index_path = str(getattr(state, "index_path", "kb_index.json") or "kb_index.json")
        top_k = int(getattr(state, "top_k", 5) or 5)

    results = search_docs(query, index_path, top_k)
    # 平滑返回空上下文 (业务方决定如何提示)

    if not results:
        return {"retrieved_context": "", "retrieved_total": 0}

    parts = [f"[知识片段{i+1}] ({r['file']})\n{r['content']}" for i, r in enumerate(results)]
    return {"retrieved_context": "\n\n".join(parts), "retrieved_total": len(results)}