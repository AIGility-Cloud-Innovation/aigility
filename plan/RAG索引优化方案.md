# RAG 索引优化方案

> 版本：v1.0 | 日期：2026-05-19 | 分支：qyd/feat_0518

---

## 一、现状与问题

当前 RAG 系统采用 **MarkdownAST 切分 + 向量化入 Qdrant + BM25/向量混合检索 + Rerank + Buffer 上下文** 的标准架构，整体流程合理，但存在以下核心问题：

| # | 问题 | 具体表现 | 严重性 |
|:---:|------|---------|:------:|
| 1 | 固定大小切分 | 按 token 数截断，不考虑语义边界，句子/段落被切断 | 高 |
| 2 | 无 Payload Index | Qdrant 中 payload 字段默认无索引，带 filter 的检索走全扫描 | 高 |
| 3 | 单粒度检索 | 只有一种 chunk 粒度，无法同时应对章节级和句子级查询 | 高 |
| 4 | Buffer 上下文有限 | 仅扩展 250 字符，前后文缺失，LLM 难以生成完整答案 | 中 |
| 5 | 无结构感知 | 不知道 chunk 来自哪个章节/文档类型，无法按结构过滤 | 中 |
| 6 | 单一内容向量 | 用户问法与文档写法差异大时，向量匹配失败 | 中 |

---

## 二、整体解决方案

本次优化围绕三个核心改造点展开：

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG 优化路线图                             │
├─────────────────────────────────────────────────────────────┤
│  Stage 1: Payload Index + Metadata 完善                      │
│    ↓                                                        │
│  Stage 2: Small-to-Big 分块策略（替代 Buffer）                │
│    ↓                                                        │
│  Stage 3: HyDE 查询增强（可选）                               │
│    ↓                                                        │
│  评估: RAGAS 框架量化各项指标                                  │
└─────────────────────────────────────────────────────────────┘
```

### 架构变化总览

| 环节 | 当前方案 | 优化方案 |
|------|---------|---------|
| 文档切分 | MarkdownAST 切分（单粒度）+ Buffer(250 字符) | Small-to-Big：父块 512 tok + 子块 128 tok |
| Metadata | 基础字段（file_hash, chunk_index 等） | 增强字段：位置 / 结构 / 父子关联 / 语义 |
| Payload Index | 未建立（全扫描） | 对高频过滤字段显式建立索引 |
| 查询增强 | 原始 query 直接检索 | 默认：原始 query；可选：HyDE |
| 检索对象 | 全量 chunk | 仅检索子块，取回父块给 LLM |
| 父块存储 | Buffer 在 metadata 中 | 统一父块存储（SQLite 通用 + Qdrant payload 优化） |
| 效果评估 | 无 | RAGAS 框架量化三项指标 |

---

## 三、改造一：建立 Payload Index

### 3.1 问题说明

Qdrant 中 payload 字段默认没有索引。带 filter 的检索（如只查某类文档、某个时间范围）会扫描集合内所有向量点逐一比对，数据量达到百万级后，单次检索延迟可从毫秒级上升到秒级。

建立 Payload Index 后，Qdrant 会为该字段维护一个**倒排结构**，过滤时直接定位，速度显著提升。

> **注意：** 此操作对现有 collection 立即生效，无需重新入库，是成本最低、收益最直接的改造。

### 3.2 需要建立索引的字段

| 字段名 | 类型 | 用途 | 来源 |
|--------|------|------|------|
| `file_hash` | KEYWORD | 按文档精确过滤 | 已有 |
| `file_type` | KEYWORD | 按文档类型过滤 | 已有 |
| `chunk_index` | INTEGER | 按位置范围过滤 | 已有 |
| `is_deleted` | KEYWORD | 过滤已删除文档 | 已有 |
| `content_type` | KEYWORD | 按内容类型过滤（code/text/table） | **新增** |
| `heading` | KEYWORD | 按章节标题过滤 | **新增** |
| `parent_chunk_id` | KEYWORD | Small-to-Big 取父块 | **新增** |
| `level` | KEYWORD | 区分子块/父块，检索时只查子块 | **新增** |

### 3.3 实施步骤

1. **编写索引创建脚本**：对 8 个字段逐一调用 `create_payload_index`
2. **验证索引生效**：通过 Qdrant REST API `GET /collections/{name}/index/{field}` 确认
3. **性能对比测试**：使用 filter 查询对比索引前后的延迟差异

### 3.4 实现代码

```python
from qdrant_client.models import PayloadSchemaType

# 对以下字段逐一建立 Payload Index
fields_to_index = [
    # 已有字段
    ("file_hash",       PayloadSchemaType.KEYWORD),
    ("file_type",       PayloadSchemaType.KEYWORD),
    ("chunk_index",     PayloadSchemaType.INTEGER),
    ("is_deleted",      PayloadSchemaType.KEYWORD),
    # 新增字段
    ("content_type",    PayloadSchemaType.KEYWORD),
    ("heading",         PayloadSchemaType.KEYWORD),
    ("parent_chunk_id", PayloadSchemaType.KEYWORD),
    ("level",           PayloadSchemaType.KEYWORD),
]

for field, schema in fields_to_index:
    client.create_payload_index(
        collection_name=config.collection_name,
        field_name=field,
        field_schema=schema,
    )
```

### 3.5 接口可选配置字段

```json
{
  "payload_index": {
    "enabled": true,
    "fields": ["file_hash", "file_type", "heading", "level"],
    "auto_create": true
  }
}
```

### 3.6 预期效果与性能影响

| 指标 | 优化前 | 优化后 | 变化 |
|------|--------|--------|------|
| Filter 检索延迟（10万级） | 50-200ms | 5-15ms | **↓ 70%-90%** |
| Filter 检索延迟（100万级） | 500ms-2s | 10-50ms | **↓ 90%-95%** |
| 存储开销 | 无额外开销 | 增加 5%-10% | 可接受 |
| 入库时间 | 基准 | 增加 10%-15% | 一次性成本 |
| Token 消耗 | 不变 | 不变 | 无影响 |

**适用场景：** 所有需要带 filter 的检索场景（按文档类型、按标题、按状态过滤等）

---

## 四、改造二：完善 Metadata

### 4.1 字段来源策略

核心原则：**能规则提取的绝不用 LLM**，只对 parent 块调用一次，子块复用父块的结果。

| 来源 | 字段示例 | 成本 | 说明 |
|------|---------|------|------|
| 文件系统 | `file_name` / `file_hash` / `created_at` | 零 | `os.stat()` 直接获取 |
| 文档解析 | `page_number` / `total_pages` | 极低 | pdfplumber/python-docx 解析 |
| 切分时生成 | `chunk_id` / `chunk_index` / `level` | 零 | 切分逻辑中自动赋值 |
| 规则提取 | `heading` / `section_path` / `content_type` | 极低 | MarkdownAST 解析 + 正则匹配 |
| LLM 生成（可选） | `summary` / `keywords` / `doc_type` | 低 | 仅对 parent 块，可选开启 |

### 4.2 完整字段清单

#### 位置与溯源字段

```json
{
  "file_hash":     "a1b2c3d4...",              // 文档唯一 ID（已有）
  "chunk_id":      "a1b2c3d4_c023",            // chunk 唯一 ID（新增）
  "chunk_index":   23,                          // 第几个 chunk（已有）
  "source_file":   "2024_annual_report.pdf"    // 原始文件名（已有）
}
```

#### 结构与语义字段

```json
{
  "heading":        "第三章 财务分析",           // 所属标题（新增）
  "section_path":   "年报 > 财务分析 > 营收",   // 面包屑路径（新增）
  "content_type":   "text",                     // 内容类型：text/code/table（新增）
  "file_type":      "pdf"                       // 文件类型（已有）
}
```

#### 父子关联字段（Small-to-Big 所需）

```json
{
  "level":            "child",      // child 或 parent（新增）
  "parent_chunk_id":  "..._p007",   // 子块指向父块（新增）
  "prev_chunk_id":    "..._c022",   // 前一个 chunk（新增）
  "next_chunk_id":    "..._c024"    // 后一个 chunk（新增）
}
```

#### 时间与权重字段

```json
{
  "created_at":       "2024-10-01T00:00:00",  // 创建时间（新增）
  "is_deleted":       false                    // 软删除标记（已有）
}
```

### 4.3 实施步骤

1. **定义 Metadata schema**：在 `IngestionConfig` 中新增 metadata 相关配置字段
2. **修改切分逻辑**：在 `MarkdownASTSplitter` 中生成完整的 metadata 信息
3. **修改入库逻辑**：将 metadata 写入 Qdrant payload
4. **向后兼容处理**：旧数据自动填充默认值，无需重新入库

### 4.4 接口可选配置字段

```json
{
  "metadata": {
    "enable_structural": true,
    "enable_parent_child": true,
    "enable_llm_summary": false,
    "llm_summary_model": "qwen-turbo",
    "custom_fields": ["doc_type", "department"]
  }
}
```

### 4.5 预期效果与性能影响

| 指标 | 优化前 | 优化后 | 变化 |
|------|--------|--------|------|
| 检索精度（Context Recall） | 基准 | ↑ 5%-10% | 结构过滤提升召回 |
| 入库时间 | 基准 | ↑ 5%-10% | metadata 生成开销 |
| 存储开销 | 基准 | ↑ 8%-15% | metadata 字段存储 |
| Token 消耗 | 不变 | 不变 | 无影响 |

**适用场景：** 所有需要按文档结构、类型过滤的检索场景

---

## 五、改造三：Small-to-Big 分块策略

### 5.1 核心思路

Small-to-Big 将**切分和检索解耦**：用小块（子块，128 tok）做向量检索，精度高；返回给 LLM 时扩展到父块（512 tok），上下文完整。两者通过 `parent_chunk_id` 关联。

替代现有 Buffer 机制：当前的 `prev_buffer`/`next_buffer`（250 字符）上下文太小，Small-to-Big 直接返回完整父块，效果更好。

### 5.2 方案对比

| 维度 | 当前方案（Buffer） | 优化方案（Small-to-Big） |
|------|-------------------|------------------------|
| 上下文扩展 | metadata 中存 250 字符 buffer | 独立存储 512 tok 父块 |
| 上下文质量 | 可能截断，不够完整 | 完整父块，语义完整 |
| 存储开销 | 无额外存储 | 需要父块存储 |
| 检索开销 | 无额外查询 | 需要查父块存储 |

### 5.3 父块存储策略：通用抽象 + 多后端支持

考虑到不同向量库的 payload 能力不同，设计统一的父块存储抽象：

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

#### 后端实现对比

| 后端 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| SQLite | 单机部署，通用方案 | 零依赖，跨平台，ACID | 并发写入受限 |
| Qdrant Payload | 已用 Qdrant，数据量 <10 万 | 无额外存储，查询快 | 依赖特定向量库 |
| Redis | 已有 Redis，高并发 | 毫秒级延迟，支持 TTL | 需要额外组件 |
| 内存 | 测试/小数据量 | 最快 | 重启丢失 |

### 5.4 实施步骤

1. **设计父块存储接口**：定义 `ParentChunkStore` 抽象基类
2. **实现 SQLite 后端**：通用方案，适用于单机部署
3. **修改切分逻辑**：实现 Small-to-Big 切分，生成父块和子块
4. **修改检索逻辑**：检索时只查子块，结果扩展到父块
5. **迁移现有数据**：编写迁移脚本，将现有 chunk 重新切分

### 5.5 接口可选配置字段

```json
{
  "chunking": {
    "strategy": "small_to_big",
    "parent_chunk_size": 512,
    "child_chunk_size": 128,
    "overlap": 32,
    "parent_store": {
      "backend": "sqlite",
      "path": "./parent_chunks.db",
      "enable_cache": true,
      "cache_ttl": 3600
    }
  }
}
```

### 5.6 预期效果与性能影响

| 指标 | 优化前（Buffer） | 优化后（Small-to-Big） | 变化 |
|------|-----------------|----------------------|------|
| 检索精度 | 基准 | ↑ 10%-20% | 小块检索更精准 |
| 上下文完整性 | 250 字符 buffer | 512 tok 完整父块 | **显著提升** |
| 答案质量（Faithfulness） | 基准 | ↑ 10%-15% | 完整上下文减少幻觉 |
| 检索延迟 | 基准 | ↑ 5-15ms | 额外查父块存储 |
| 存储开销 | 基准 | ↑ 20%-40% | 父块独立存储 |
| Token 消耗（LLM） | 基准 | ↑ 15%-25% | 更长上下文 |

**适用场景：** 需要完整上下文才能准确回答的复杂问题（如文档问答、知识问答）

---

## 六、改造四：HyDE 查询增强（可选）

### 6.1 原理

HyDE（Hypothetical Document Embeddings）的核心思路：用户的问题和文档的写法往往风格不一致，直接用问题向量检索效果差。HyDE 先让 LLM 生成一个「假设性答案」，用假设答案的向量去检索，因为假设答案的语言风格更接近文档语料，匹配效果更好。

### 6.2 适用场景

| 场景 | 是否启用 HyDE | 原因 |
|------|:------------:|------|
| 精确事实查询 | 不启用 | 关键词检索更准 |
| 复杂推理问题 | **启用** | 假设答案更接近文档表述 |
| 跨领域查询 | **启用** | 风格差异大，HyDE 有效 |
| 生产环境默认 | 不启用 | 增加延迟和成本 |

### 6.3 实施步骤

1. **设计 HyDE 提示词模板**：引导 LLM 生成假设性答案
2. **实现 HyDE 增强检索器**：在检索前增加一步 LLM 调用
3. **配置开关**：支持按查询类型自动判断是否启用
4. **性能调优**：优化提示词，控制假设答案长度

### 6.4 接口可选配置字段

```json
{
  "query_enhancement": {
    "hyde": {
      "enabled": false,
      "model": "qwen-turbo",
      "max_tokens": 200,
      "auto_enable": true,
      "auto_enable_threshold": 0.3
    }
  }
}
```

### 6.5 预期效果与性能影响

| 指标 | 不启用 HyDE | 启用 HyDE | 变化 |
|------|------------|----------|------|
| 检索精度（Answer Relevancy） | 基准 | ↑ 10%-20% | 假设答案更匹配 |
| 检索延迟 | 基准 | ↑ 200-500ms | 额外 LLM 调用 |
| Token 消耗（检索） | 0 | ↑ 200-500 tokens | 生成假设答案 |
| Token 消耗（LLM 生成） | 基准 | 不变 | — |
| 适用场景 | 简单查询 | 复杂查询 | 按需启用 |

**适用场景：** 用户问法与文档表述差异大的复杂查询（如跨领域问答、推理类问题）

---

## 七、效果评估：RAGAS 框架

### 7.1 核心评估指标

| 指标 | 含义 | 优化目标 |
|------|------|---------|
| **Faithfulness**（忠实度） | LLM 生成的答案是否完全基于检索到的上下文，不捏造 | > 0.85 |
| **Answer Relevancy**（答案相关性） | 生成的答案与用户问题的相关程度 | > 0.80 |
| **Context Recall**（上下文召回率） | 检索到的上下文是否覆盖了回答问题所需的关键信息 | > 0.75 |

### 7.2 A/B 对比方法

按以下四个阶段分别跑 RAGAS 评估，对比每步改造的实际增量收益：

| 阶段 | 改造内容 | 对比基准 |
|------|---------|---------|
| Baseline | 当前方案（固定切分 + Buffer） | — |
| Stage 1 | + Payload Index + Metadata | vs Baseline |
| Stage 2 | + Small-to-Big 分块 | vs Stage 1 |
| Stage 3 | + HyDE 查询增强（可选） | vs Stage 2 |

---

## 八、分层定价参考

基于以上优化方案的性能影响分析，建议按以下维度进行分层定价：

### 8.1 定价维度

| 定价维度 | 说明 | 影响因素 |
|---------|------|---------|
| 存储费 | 按存储量计费 | Metadata 丰富度、父块存储 |
| 检索费 | 按检索次数计费 | Payload Index、HyDE 增强 |
| Token 费 | 按 LLM 消耗计费 | 上下文长度、HyDE 生成 |

### 8.2 推荐套餐

| 套餐 | 检索策略 | Metadata | HyDE | 月费参考 |
|------|---------|---------|------|---------|
| **基础版** | 固定切分 + Buffer | 基础字段 | 不启用 | ¥XX |
| **专业版** | Small-to-Big | 完整字段 | 可选启用 | ¥XX |
| **企业版** | Small-to-Big + HyDE | 完整字段 + 自定义 | 自动启用 | ¥XX |

### 8.3 成本估算

| 指标 | 基础版 | 专业版 | 企业版 |
|------|--------|--------|--------|
| 存储开销（10万 chunk） | 基准 | +30% | +30% |
| 检索延迟 | 基准 | +5-15ms | +200-500ms |
| Token 消耗/次 | 基准 | +15%-25% | +200-500 tokens |
| 答案质量 | 基准 | ↑ 15% | ↑ 25% |

---

## 九、实施计划

| 阶段 | 任务 | 预计工时 | 依赖 |
|------|------|---------|------|
| Phase 1 | Payload Index 建立 | 1 天 | 无 |
| Phase 2 | Metadata 完善 | 2 天 | Phase 1 |
| Phase 3 | Small-to-Big 分块 | 3 天 | Phase 2 |
| Phase 4 | HyDE 查询增强 | 2 天 | Phase 3 |
| Phase 5 | RAGAS 评估 | 2 天 | Phase 3 |
| **总计** | | **10 天** | |

---

## 十、风险与注意事项

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 索引字段选择不当 | 性能提升不明显 | 基于实际查询 pattern 选择 |
| Small-to-Big 切分不合理 | 语义完整性受损 | A/B 测试调优参数 |
| HyDE 生成质量差 | 检索效果反降 | 增加过滤条件，控制质量 |
| 存储成本上升 | 费用增加 | 按需启用，提供套餐选择 |
| 迁移过程服务中断 | 用户体验受影响 | 灰度发布，逐步迁移 |
