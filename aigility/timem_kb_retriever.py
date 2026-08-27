# -*- coding: utf-8 -*-
"""
TiMEM Space 只读检索器 (BM25 keyword retrieval)

仅提供检索能力（读文件/索引 → 返回相关片段）。绝不写入、修改、删除任何数据。
用于 aigility-harness 客服工作流的 retrieve 节点:
    index_knowledge_base(source_dir, index_path)  # 一次性建索引
    search_docs(query, index_path, top_k)         # 查询
"""
import os
import re
import json
import hashlib
from typing import List, Dict, Any

# ── 文档分块 ─────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    """中英文分词: 英文按词, 中文按二元组(char bigram), 保留数字."""
    text = text.lower()
    # 英文词 + 数字
    words = re.findall(r"[a-z0-9_]+", text)
    # 中文字符
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    # 中文二元组
    bigrams = [cjk[i] + cjk[i+1] for i in range(len(cjk)-1)]
    # 中文字符本身 (增强召回)
    return words + bigrams + cjk

def _chunk_text(text: str, max_chars: int = 1500, overlap: int = 150) -> List[Dict[str, Any]]:
    """按字符切块, 带重叠."""
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end]
        if chunk.strip():
            chunks.append({
                "text": chunk,
                "start": start,
                "end": end,
            })
        if end >= len(text):
            break
        start = end - overlap
    return chunks

# ── BM25 索引 ─────────────────────────────────────────────

def _bm25_score(
    query_terms: List[str],
    doc_tf: Dict[str, int],
    doc_len: int,
    df: Dict[str, int],
    total_docs: int,
    avg_len: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """经典 BM25 打分"""
    score = 0.0
    for term in set(query_terms):
        tf = doc_tf.get(term, 0)
        if tf == 0:
            continue
        idf = max(0.0, float(total_docs - df.get(term, 0) + 0.5) /
                  (df.get(term, 0) + 0.5))
        denom = tf + k1 * (1 - b + b * doc_len / max(avg_len, 1e-9))
        score += idf * (tf * (k1 + 1)) / max(denom, 1e-9)
    return score

def build_index(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """docs: [{'file': path, 'text': content}] → BM25 索引结构"""
    chunks: List[Dict[str, Any]] = []
    for doc in docs:
        for chunk in _chunk_text(doc.get("text", "")):
            chunks.append({
                "file": doc["file"],
                "text": chunk["text"],
            })

    # 文档频率 + 每 chunk 词频
    df: Dict[str, int] = {}
    chunk_data: List[Dict[str, Any]] = []
    for c in chunks:
        terms = _tokenize(c["text"])
        tf: Dict[str, int] = {}
        for t in terms:
            tf[t] = tf.get(t, 0) + 1
        # 全局 df
        for t in set(terms):
            df[t] = df.get(t, 0) + 1
        chunk_data.append({"file": c["file"], "text": c["text"], "tf": tf, "len": len(terms)})

    total_len = sum(c["len"] for c in chunk_data)
    avg_len = total_len / max(len(chunk_data), 1)

    return {
        "chunks": chunk_data,
        "df": df,
        "total_docs": len(chunk_data),
        "avg_len": avg_len,
    }

def search_index(index: Dict[str, Any], query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """查询 BM25 索引, 返回最相关片段 (只读, 不修改索引)"""
    query_terms = _tokenize(query)
    if not query_terms:
        return []
    scored = []
    for c in index["chunks"]:
        score = _bm25_score(
            query_terms, c["tf"], c["len"],
            index["df"], index["total_docs"], index["avg_len"],
        )
        if score > 0:
            scored.append({"score": round(score, 4), "file": c["file"], "text": c["text"]})
    scored.sort(key=lambda x: -x["score"])
    return scored[:top_k]

# ── 持久化 (只读工具集的索引文件) ─────────────────────────

def save_index(index: Dict[str, Any], path: str) -> None:
    """序列化索引到磁盘 (仅本工具使用)"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)

def load_index(path: str) -> Dict[str, Any]:
    """加载磁盘索引"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def index_directory(source_dir: str, index_path: str, extensions=(".py", ".md")) -> Dict[str, Any]:
    """扫描目录建索引 (只读扫描)"""
    docs = []
    for root, dirs, files in os.walk(source_dir):
        # 跳过无关目录
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next")]
        for fn in files:
            if fn.endswith(extensions):
                fp = os.path.join(root, fn)
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        docs.append({"file": fp, "text": f.read()})
                except (UnicodeDecodeError, OSError):
                    continue
    index = build_index(docs)
    save_index(index, index_path)
    return index


# ── workflow 节点函数 (供 py-bridge node_module 调用) ──────

_DEFAULT_INDEX = "/home/johnny/AI/aigility/config/timem_kb_index.json"
_SOURCE_DIR = "/home/johnny/AI/timem/TiMEM-Space"

def retrieve_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """workflow retrieve 节点: 用 user_input 检索知识库, 结果放 context.

    只读: 绝不写回/修改知识库。
    """
    query = str(state.get("user_input", "") or "")
    top_k = int(state.get("top_k", 5))

    # 索引不存在则建 (首次调用)
    if not os.path.exists(_DEFAULT_INDEX):
        index_directory(_SOURCE_DIR, _DEFAULT_INDEX)

    index = load_index(_DEFAULT_INDEX)
    hits = search_index(index, query, top_k=top_k)

    # 组装检索上下文 (限长)
    ctx_parts = []
    for i, h in enumerate(hits, 1):
        rel = os.path.relpath(h["file"], _SOURCE_DIR)
        snippet = h["text"][:600].strip()
        ctx_parts.append(f"[知识片段{i}] ({rel})\n{snippet}")

    context = "\n\n".join(ctx_parts) if ctx_parts else "（知识库未检索到相关内容）"
    return {
        "retrieved_context": context,
        "retrieved_count": len(hits),
        **state,
    }