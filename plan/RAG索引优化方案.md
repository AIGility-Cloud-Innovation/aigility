# RAG 检索系统索引优化方案

> 技术优化方案 · 2025 | 现状诊断 · 解决方案 · 实施路线图 · 预期收益

---

## 一、现状与问题

当前 RAG 系统采用 MarkdownAST切分 + 向量化入 Qdrant + BM25/向量混合检索 + Rerank + Buffer上下文 的标准架构，整体流程合理，但存在以下核心问题：

| # | 问题 | 具体表现 | 严重性 |
|---|------|----------|--------|
| 1 | 固定大小切分 | 按 token 数截断，不考虑语义边界，句子/段落被切断 | 高 |
| 2 | 无 Payload Index | Qdrant 中 payload 字段默认无索引，带 filter 的检索走全扫描 | 高 |
| 3 | 单粒度检索 | 只有一种 chunk 粒度，无法同时应对章节级和句子级查询 | 高 |
| 4 | Buffer上下文有限 | 仅扩展250字符，前后文缺失，LLM难以生成完整答案 | 中 |
| 5 | 无结构感知 | 不知道 chunk 来自哪章节/文档类型，无法按结构过滤 | 中 |
| 6 | 单一内容向量 | 用户问法与文档写法差异大时，向量匹配失败 | 中 |

---

## 二、整体解决方案

本次优化围绕三个核心改造点展开：建立 Payload Index + 完善 Metadata、切换 Small-to-Big 分块策略替代Buffer机制，并将 HyDE 作为可选增强。

### 整体架构变化

| 环节 | 当前方案 | 优化方案 |
|------|----------|----------|
| 文档切分 | MarkdownAST切分（单粒度）+ Buffer(250字符) | Small-to-Big：父块 512 tok + 子块 128 tok |
| 向量化 | 仅 content_vector | 仅 content_vector（保持不变） |
| Metadata | 基础字段（file_hash, chunk_index等） | 增强字段：位置 / 结构 / 父子关联 / 语义 |
| Payload Index | 未建立（全扫描） | 对高频过滤字段显式建立索引 |
| 查询增强 | 原始 query 直接检索 | 默认：原始query；可选：HyDE |
| 检索对象 | 全量 chunk | 仅检索子块，取回父块给 LLM |
| 父块存储 | Buffer在metadata中 | 统一父块存储（SQLite通用 + Qdrant payload优化） |
| 效果评估 | 无 | RAGAS 框架量化三项指标 |

---

## 三、改造一：建立 Payload Index

### 问题说明

Qdrant 中 payload 字段默认没有索引。带 filter 的检索（如只查某类文档、某个时间范围）会扫描集合内所有向量点逐一比对，数据量达到百万级后，单次检索延迟可从毫秒级上升到秒级。

建立 Payload Index 后，Qdrant 会为该字段维护一个倒排结构，过滤时直接定位，速度提升通常在 10x 以上。

> **注意**：此操作对现有 collection 立即生效，无需重新入库，是成本最低、收益最直接的改造。

### 需要建立索引的字段（适配当前系统）

| 字段名 | 类型 | 用途 | 当前系统来源 |
|--------|------|------|-------------|
| `file_hash` | KEYWORD | 按文档精确过滤 | ✅ 已有 |
| `file_type` | KEYWORD | 按文档类型过滤 | ✅ 已有 |
| `chunk_index` | INTEGER | 按位置范围过滤 | ✅ 已有 |
| `is_deleted` | KEYWORD | 过滤已删除文档 | ✅ 已有 |
| `content_type` | KEYWORD | 按内容类型过滤（code/text/table） | 🆕 新增 |
| `heading` | KEYWORD | 按章节标题过滤 | 🆕 新增 |
| `parent_chunk_id` | KEYWORD | Small-to-Big 取父块 | 🆕 新增 |
| `level` | KEYWORD | 区分子块/父块，检索时只查子块 | 🆕 新增 |

### 实现代码

```python
from qdrant_client.models import PayloadSchemaType

# 对以下字段逐一建立 Payload Index
fields_to_index = [
    # 已有字段
    ("file_hash",        PayloadSchemaType.KEYWORD),
    ("file_type",        PayloadSchemaType.KEYWORD),
    ("chunk_index",      PayloadSchemaType.INTEGER),
    ("is_deleted",       PayloadSchemaType.KEYWORD),
    # 新增字段
    ("content_type",     PayloadSchemaType.KEYWORD),
    ("heading",          PayloadSchemaType.KEYWORD),
    ("parent_chunk_id",  PayloadSchemaType.KEYWORD),
    ("level",            PayloadSchemaType.KEYWORD),
]

for field, schema in fields_to_index:
    client.create_payload_index(
        collection_name=config.collection_name,
        field_name=field,
        field_schema=schema,
    )
```

---

## 四、改造二：完善 Metadata

### 字段来源策略

核心原则：**能规则提取的绝不用 LLM，只对 parent 块调用一次，子块复用父块的结果。**

| 来源 | 字段示例 | 成本 | 说明 |
|------|----------|------|------|
| 文件系统 | file_name / file_hash / created_at | 零 | os.stat() 直接获取 |
| 文档解析 | page_number / total_pages | 极低 | pdfplumber/python-docx 解析 |
| 切分时生成 | chunk_id / chunk_index / level | 零 | 切分逻辑中自动赋值 |
| 规则提取 | heading / section_path / content_type | 极低 | MarkdownAST解析 + 正则匹配 |
| LLM 生成（可选） | summary / keywords / doc_type | 低 | 仅对 parent 块，可选开启 |

### 完整字段清单

**位置与溯源字段**

```python
"file_hash":     "a1b2c3d4...",              # 文档唯一ID（已有）
"chunk_id":      "a1b2c3d4_c023",            # chunk唯一ID（新增）
"chunk_index":   23,                          # 第几个chunk（已有）
"source_file":   "2024_annual_report.pdf",   # 原始文件名（已有）
```

**结构与语义字段**

```python
"heading":        "第三章 财务分析",           # 所属标题（新增）
"section_path":   "年报 > 财务分析 > 营收",   # 面包屑路径（新增）
"content_type":   "text",                     # 内容类型：text/code/table（新增）
"file_type":      "pdf",                      # 文件类型（已有）
```

**父子关联字段（Small-to-Big 所需）**

```python
"level":            "child",      # child 或 parent（新增）
"parent_chunk_id":  "..._p007",   # 子块指向父块（新增）
"prev_chunk_id":    "..._c022",   # 前一个chunk（新增）
"next_chunk_id":    "..._c024",   # 后一个chunk（新增）
```

**时间与权重字段**

```python
"created_at":       "2024-10-01T00:00:00",  # 创建时间（新增）
"is_deleted":       False,                   # 软删除标记（已有）
```

### 规则提取 Metadata 代码

```python
import re
from typing import List, Dict

def extract_metadata_from_chunk(
    chunk_text: str,
    chunk_index: int,
    total_chunks: int,
    file_info: Dict
) -> Dict:
    """
    从chunk文本中提取结构化metadata（无需LLM）
    """
    metadata = {
        # 已有字段
        "file_hash": file_info["file_hash"],
        "file_name": file_info["file_name"],
        "file_type": file_info["file_type"],
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        "is_deleted": False,

        # 新增字段
        "chunk_id": f"{file_info['file_hash']}_c{chunk_index:04d}",
        "content_type": detect_content_type(chunk_text),
        "heading": extract_heading(chunk_text),
        "section_path": extract_section_path(chunk_text),
    }
    return metadata


def detect_content_type(text: str) -> str:
    """检测内容类型"""
    if re.search(r'```[\s\S]*?```', text):
        return "code"
    if '|' in text and text.count('|') > 3:
        return "table"
    return "text"


def extract_heading(text: str) -> str:
    """提取chunk所属标题"""
    # 优先从MarkdownAST获取，否则用正则
    match = re.search(r'^#+\s+(.+)$', text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return ""


def extract_section_path(text: str) -> str:
    """提取面包屑路径（从MarkdownAST获取更准确）"""
    # 需要结合MarkdownASTSplitter的token信息
    # 这里简化处理，实际应从splitter返回
    return ""
```

---

## 五、改造三：Small-to-Big 分块策略

### 核心思路

Small-to-Big 将切分和检索解耦：用小块（子块，128 tok）做向量检索，精度高；返回给 LLM 时扩展到父块（512 tok），上下文完整。两者通过 `parent_chunk_id` 关联。

**替代现有Buffer机制**：当前的 `prev_buffer`/`next_buffer`（250字符）上下文太小，Small-to-Big 直接返回完整父块，效果更好。

| 维度 | 当前方案（Buffer） | 优化方案（Small-to-Big） |
|------|-------------------|-------------------------|
| 上下文扩展 | metadata中存250字符buffer | 独立存储512 tok父块 |
| 上下文质量 | 可能截断，不够完整 | 完整父块，语义完整 |
| 存储开销 | 无额外存储 | 需要父块存储 |
| 检索开销 | 无额外查询 | 需要查父块存储 |

### 父块存储策略：通用抽象 + 多后端支持

考虑到不同向量库的payload能力不同，设计**统一的父块存储抽象**：

```python
from abc import ABC, abstractmethod
from typing import Optional

class ParentChunkStore(ABC):
    """父块存储抽象基类"""

    @abstractmethod
    def put(self, chunk_id: str, text: str, metadata: dict = None):
        """存储父块"""
        pass

    @abstractmethod
    def get(self, chunk_id: str) -> Optional[str]:
        """获取父块文本"""
        pass

    @abstractmethod
    def delete(self, chunk_id: str):
        """删除父块"""
        pass

    @abstractmethod
    def batch_get(self, chunk_ids: list) -> dict:
        """批量获取父块"""
        pass
```

### 后端实现

| 后端 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **SQLite** | 单机部署，通用方案 | 零依赖，跨平台，ACID | 并发写入受限 |
| **Qdrant Payload** | 已用Qdrant，数据量<10万 | 无额外存储，查询快 | 依赖特定向量库 |
| **Redis** | 已有Redis，高并发 | 毫秒级延迟，支持TTL | 需要额外组件 |
| **内存** | 测试/小数据量 | 最快 | 重启丢失 |

#### SQLite实现（默认推荐）

```python
import sqlite3
import json
from typing import Optional, Dict

class SQLiteParentChunkStore(ParentChunkStore):
    """SQLite父块存储（通用方案）"""

    def __init__(self, db_path: str = "parent_chunks.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_table()

    def _init_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS parent_chunks (
                chunk_id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def put(self, chunk_id: str, text: str, metadata: dict = None):
        self.conn.execute(
            "INSERT OR REPLACE INTO parent_chunks (chunk_id, text, metadata) VALUES (?, ?, ?)",
            (chunk_id, text, json.dumps(metadata or {}))
        )
        self.conn.commit()

    def get(self, chunk_id: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT text FROM parent_chunks WHERE chunk_id=?", (chunk_id,)
        ).fetchone()
        return row[0] if row else None

    def batch_get(self, chunk_ids: list) -> Dict[str, str]:
        if not chunk_ids:
            return {}
        placeholders = ",".join(["?"] * len(chunk_ids))
        rows = self.conn.execute(
            f"SELECT chunk_id, text FROM parent_chunks WHERE chunk_id IN ({placeholders})",
            chunk_ids
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    def delete(self, chunk_id: str):
        self.conn.execute("DELETE FROM parent_chunks WHERE chunk_id=?", (chunk_id,))
        self.conn.commit()
```

#### Qdrant Payload实现（优化方案）

```python
class QdrantParentChunkStore(ParentChunkStore):
    """Qdrant Payload父块存储（依赖Qdrant，但无需额外存储）"""

    def __init__(self, client, collection_name: str):
        self.client = client
        self.collection_name = collection_name

    def put(self, chunk_id: str, text: str, metadata: dict = None):
        # 父块存在单独的collection中，或存在child point的payload里
        # 这里选择：为每个child点的payload添加parent_chunk_text字段
        pass

    def get(self, chunk_id: str) -> Optional[str]:
        # 根据chunk_id查询
        pass

    def batch_get(self, chunk_ids: list) -> Dict[str, str]:
        # 批量查询
        pass
```

#### 工厂方法

```python
class ParentChunkStoreFactory:
    """父块存储工厂"""

    @staticmethod
    def create(store_type: str = "sqlite", **kwargs) -> ParentChunkStore:
        if store_type == "sqlite":
            return SQLiteParentChunkStore(
                db_path=kwargs.get("db_path", "parent_chunks.db")
            )
        elif store_type == "qdrant":
            return QdrantParentChunkStore(
                client=kwargs["client"],
                collection_name=kwargs["collection_name"]
            )
        elif store_type == "redis":
            # TODO: Redis实现
            raise NotImplementedError
        elif store_type == "memory":
            return InMemoryParentChunkStore()
        else:
            raise ValueError(f"Unknown store type: {store_type}")
```

### 入库流程

```python
def process_document(file_path: str, store: ParentChunkStore):
    """处理文档，生成父子chunk并存储"""

    # 1. 解析和切分（使用现有IngestionManager）
    chunks = ingestion_manager.process_documents(file_path)

    # 2. 构建父子关系
    parent_child_chunks = build_parent_child_chunks(chunks)

    # 3. 分别存储
    for chunk in parent_child_chunks:
        if chunk["level"] == "parent":
            # 父块存入KV存储
            store.put(
                chunk_id=chunk["chunk_id"],
                text=chunk["text"],
                metadata=chunk["metadata"]
            )
        else:  # child
            # 子块存入Qdrant（附带parent_chunk_id）
            payload = {
                **chunk["metadata"],
                "level": "child",
                "parent_chunk_id": chunk["parent_chunk_id"],
            }
            vector_store.add_texts(
                texts=[chunk["text"]],
                metadatas=[payload]
            )


def build_parent_child_chunks(chunks: list) -> list:
    """
    将chunk构建为父子结构

    策略：
    - 每N个子块组成一个父块（按语义边界划分）
    - 父块大小约512 token
    - 子块大小约128 token
    """
    parent_chunks = []
    child_chunks = []

    # 按现有切分结果，重新组织为父子结构
    # 简化实现：每4个chunk为一组，第1个为parent，其余为child
    group_size = 4
    for i in range(0, len(chunks), group_size):
        group = chunks[i:i+group_size]

        # 第一个chunk作为parent
        parent_chunk = group[0]
        parent_id = f"{parent_chunk.metadata['file_hash']}_p{i//group_size:04d}"
        parent_chunk.metadata["chunk_id"] = parent_id
        parent_chunk.metadata["level"] = "parent"
        parent_chunks.append(parent_chunk)

        # 其余chunk作为child
        for j, child in enumerate(group[1:]):
            child_id = f"{child.metadata['file_hash']}_c{i+j:04d}"
            child.metadata["chunk_id"] = child_id
            child.metadata["level"] = "child"
            child.metadata["parent_chunk_id"] = parent_id
            child_chunks.append(child)

    return parent_chunks + child_chunks
```

### 检索流程

```python
def search_with_parent(query: str, top_k: int = 5) -> list:
    """Small-to-Big检索：查子块，返回父块"""

    # 1. 只检索子块（level=child）
    results = vector_store.similarity_search(
        query=query,
        k=top_k,
        filter={"level": "child"}  # Qdrant filter
    )

    # 2. 获取对应的parent_chunk_ids
    parent_ids = [r.metadata["parent_chunk_id"] for r in results]

    # 3. 从KV存储批量获取父块
    parent_texts = parent_chunk_store.batch_get(parent_ids)

    # 4. 返回父块内容给LLM
    contexts = []
    for r in results:
        pid = r.metadata["parent_chunk_id"]
        if pid in parent_texts:
            contexts.append({
                "parent_text": parent_texts[pid],
                "child_text": r.page_content,
                "metadata": r.metadata,
                "score": r.metadata.get("score", 0)
            })

    return contexts
```

---

## 六、改造四：HyDE 查询增强（可选）

### 原理

HyDE（Hypothetical Document Embeddings）的核心思路：用户的问题和文档的写法往往风格不一致，直接用问题向量检索效果差。HyDE 先让 LLM 生成一个「假设性答案」，用假设答案的向量去检索，因为假设答案的语言风格更接近文档语料，匹配效果更好。

### 适用场景

| 场景 | 是否启用 HyDE | 原因 |
|------|--------------|------|
| 精确事实查询 | ❌ 不启用 | 关键词检索更准 |
| 复杂推理问题 | ✅ 启用 | 假设答案更接近文档表述 |
| 跨领域查询 | ✅ 启用 | 风格差异大，HyDE有效 |
| 生产环境默认 | ❌ 不启用 | 增加延迟和成本 |

### 实现代码

```python
class HyDEEnhancer:
    """HyDE查询增强器（可选组件）"""

    def __init__(self, llm, embedding_model):
        self.llm = llm
        self.embedding = embedding_model

    def generate_hypothetical(self, query: str) -> str:
        """生成假设性答案"""
        prompt = f"""请假设你是领域专家，简要回答以下问题（约100字）：
问题：{query}"""
        return self.llm.generate(prompt)

    def enhance_query(self, query: str) -> str:
        """增强查询（返回假设答案用于检索）"""
        return self.generate_hypothetical(query)


class HybridSearchWithHyDE:
    """混合检索 + 可选HyDE"""

    def __init__(self, vector_store, parent_store, hyde_enhancer=None):
        self.vector_store = vector_store
        self.parent_store = parent_store
        self.hyde = hyde_enhancer

    def search(
        self,
        query: str,
        top_k: int = 5,
        use_hyde: bool = False,  # 默认不启用
        **kwargs
    ) -> list:
        """混合检索"""

        if use_hyde and self.hyde:
            # 1. 生成假设答案
            hypothetical = self.hyde.enhance_query(query)

            # 2. 用假设答案向量检索
            hyde_results = self._vector_search(hypothetical, top_k * 2)

            # 3. 用原始query向量检索
            plain_results = self._vector_search(query, top_k * 2)

            # 4. RRF融合
            results = self._rrf_fusion(hyde_results, plain_results, top_k)
        else:
            # 默认：直接向量检索
            results = self._vector_search(query, top_k)

        # 5. Small-to-Big：取父块
        return self._expand_to_parent(results)

    def _vector_search(self, query: str, top_k: int) -> list:
        """向量检索（只查child）"""
        return self.vector_store.similarity_search(
            query=query,
            k=top_k,
            filter={"level": "child"}
        )

    def _rrf_fusion(self, results_a, results_b, top_k, weight_a=0.6):
        """Reciprocal Rank Fusion"""
        fused = {}
        for rank, r in enumerate(results_a):
            key = r.metadata["chunk_id"]
            fused[key] = fused.get(key, 0) + weight_a / (1 + rank)

        for rank, r in enumerate(results_b):
            key = r.metadata["chunk_id"]
            fused[key] = f.get(key, 0) + (1 - weight_a) / (1 + rank)

        # 按分数排序
        sorted_keys = sorted(fused.keys(), key=lambda k: fused[k], reverse=True)
        # 返回top_k结果
        return [r for r in results_a + results_b if r.metadata["chunk_id"] in sorted_keys[:top_k]]

    def _expand_to_parent(self, results: list) -> list:
        """扩展到父块"""
        parent_ids = [r.metadata["parent_chunk_id"] for r in results]
        parent_texts = self.parent_store.batch_get(parent_ids)

        contexts = []
        for r in results:
            pid = r.metadata["parent_chunk_id"]
            if pid in parent_texts:
                contexts.append({
                    "parent_text": parent_texts[pid],
                    "child_text": r.page_content,
                    "metadata": r.metadata,
                })
        return contexts
```

### 使用方式

```python
# 默认检索（不使用HyDE）
results = search_engine.search("Q3营收增长", use_hyde=False)

# 启用HyDE（复杂问题）
results = search_engine.search("公司未来的战略方向是什么", use_hyde=True)
```

---

## 七、效果评估：RAGAS 框架

### 核心评估指标

| 指标 | 含义 | 优化目标 |
|------|------|----------|
| Faithfulness（忠实度） | LLM 生成的答案是否完全基于检索到的上下文，不捏造 | > 0.85 |
| Answer Relevancy（答案相关性） | 生成的答案与用户问题的相关程度 | > 0.80 |
| Context Recall（上下文召回率） | 检索到的上下文是否覆盖了回答问题所需的关键信息 | > 0.75 |

### A/B 对比方法

按以下四个阶段分别跑 RAGAS 评估，对比每步改造的实际增量收益：

| 阶段 | 改造内容 | 对比基准 |
|------|----------|----------|
| Baseline | 当前方案（固定切分 + Buffer） | — |
| Stage 1 | + Payload Index + Metadata | vs Baseline |
| Stage 2 | + Small-to-Big 分块 | vs Stage 1 |
| Stage 3 | + HyDE 查询增强（可选） | vs Stage 2 |

---

## 八、实施路线图

| 阶段 | 时间 | 任务 | 预期收益 |
|------|------|------|----------|
| P0 立即 | 1-2 天 | 对现有 collection 建立 Payload Index；入库时补充 content_type / heading 等字段 | 带 filter 检索速度 10x |
| P1 本周 | 3-5 天 | 实现 Small-to-Big 切分（父块 512 tok / 子块 128 tok）；SQLite存储父块；检索时加 level=child 过滤；移除Buffer机制 | LLM 上下文质量 +50% |
| P2 下周 | 2-3 天 | 接入 HyDE 查询增强（可选）；完善 LLM metadata 提取（summary / keywords） | 复杂问题召回提升 |
| P3 后续 | 1 周 | 部署 RAGAS 评估 pipeline；对 Baseline / Stage1 / Stage2 分别跑评估 | 量化各阶段收益 |

---

## 九、优先级矩阵

| 优先级 | 改造项 | 改动成本 | 预期收益 | 建议时间 |
|--------|--------|----------|----------|----------|
| P0 🔴 | 建立 Payload Index | 极低（无需重新入库） | 检索性能 10x | 立即 |
| P0 🔴 | 补充基础 Metadata 字段 | 低 | 可过滤 / 可溯源 | 立即 |
| P1 🔴 | Small-to-Big 分块策略 | 中 | 上下文质量 +50% | 本周 |
| P1 🔴 | 父块 SQLite 存储 | 低 | 支撑 S2B 取回 | 本周 |
| P2 🟡 | HyDE 查询增强（可选） | 低 | 复杂问题召回提升 | 下周 |
| P3 🟢 | RAGAS 评估 Pipeline | 中 | 量化所有改造收益 | 后续 |

---

## 十、预期收益汇总

| 指标 | 当前 | 优化后（预估） | 主要来源 |
|------|------|---------------|----------|
| 带 Filter 检索速度 | 全扫描（秒级） | 10x 提升（毫秒级） | Payload Index |
| 召回率 | 基准 | +35% | Small-to-Big + HyDE(可选) |
| LLM 上下文质量 | Buffer(250字符) | +50% | Small-to-Big 父块返回 |
| Faithfulness | 未量化 | 目标 > 0.85 | RAGAS 评估 |
| Answer Relevancy | 未量化 | 目标 > 0.80 | RAGAS 评估 |
| Context Recall | 未量化 | 目标 > 0.75 | RAGAS 评估 |

---

## 十一、兼容性说明

### 向量库适配

| 向量库 | Payload能力 | 父块存储方案 |
|--------|------------|-------------|
| Qdrant | ✅ 支持 | SQLite（推荐）或 Qdrant Payload |
| Chroma | ✅ 支持metadata | SQLite（推荐） |
| FAISS | ❌ 不支持 | SQLite（必须） |
| Milvus | ✅ 支持JSON字段 | SQLite（推荐） |

**结论**：使用 SQLite 作为默认父块存储，可以适配所有向量库，不依赖特定向量库的 payload 能力。

### 迁移策略

1. **新文档**：直接使用新架构入库
2. **旧文档**：可选择重新入库，或继续使用 Buffer 机制（向后兼容）
3. **混合模式**：检索时同时支持两种模式，通过 `level` 字段区分

---

*优先执行 P0，预计 1-2 天完成，立即见效。整体改造两周内完成。*
