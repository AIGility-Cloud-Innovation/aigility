# RAG 索引优化方案 v2a — 实施进度

> 版本：v2a | 日期：2026-05-19 | 分支：qyd/feat_0518
> 基于 v1.0 方案，记录已完成与待实施内容

---

## 一、整体进度总览

| 改造项 | 状态 | 说明 |
|--------|------|------|
| Payload Index | 已完成 | 6 个字段已建立索引，自动生效 |
| Metadata 完善 | 已完成 | 结构化元数据已入链路，Qdrant 中已验证 |
| Small-to-Big 分块 | 待实施 | 替代 Buffer 机制，父块存储 |
| HyDE 查询增强 | 待实施 | 可选增强，按需启用 |
| RAGAS 效果评估 | 待实施 | 量化各项指标提升 |

---

## 二、已完成：Payload Index

### 实施内容

在 Qdrant 中为高频过滤字段建立倒排索引，加速带 filter 的检索。

### 修改文件

| 文件 | 改动 |
|------|------|
| `aigility/rag/config.py` | 新增 `PayloadIndexConfig`、`PayloadIndexField` 配置类 |
| `aigility/rag/vector_stores/qdrant.py` | 新增 `_create_payload_indexes`、`ensure_payload_indexes` 方法 |
| `aigility/rag/service.py` | 初始化时自动调用 `ensure_payload_indexes` 补建索引 |

### 索引字段（6 个）

| 字段 | 类型 | 用途 |
|------|------|------|
| `metadata.file_hash` | keyword | 按文档精确过滤 |
| `metadata.file_type` | keyword | 按文档类型过滤 |
| `metadata.chunk_index` | integer | 按位置范围过滤 |
| `metadata.is_deleted` | keyword | 过滤已删除文档 |
| `metadata.content_type` | keyword | 按内容类型过滤（text/table/code） |
| `metadata.heading` | keyword | 按章节标题过滤 |

### 验证结果

```
✅ Payload Index 已建立，共 6 个字段：
   - metadata.file_hash: keyword
   - metadata.file_type: keyword
   - metadata.chunk_index: integer
   - metadata.is_deleted: keyword
   - metadata.content_type: keyword
   - metadata.heading: keyword
```

### 预期效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| Filter 检索延迟（10万级） | 50-200ms | 5-15ms |
| Filter 检索延迟（100万级） | 500ms-2s | 10-50ms |
| 存储开销 | 无额外 | +5%-10% |
| Token 消耗 | 不变 | 不变 |

---

## 三、已完成：Metadata 完善

### 实施内容

为每个 chunk 附加结构化元数据，包括内容类型、所属标题、面包屑路径、唯一 ID、时间戳等。

### 修改文件

| 文件 | 改动 |
|------|------|
| `aigility/rag/markdown_splitter.py` | `_merge_blocks` 返回结构化数据；新增 `split_text_structured`；`split_documents` 输出新字段 |
| `aigility/rag/service.py` | `add_file` 中新增 `chunk_id`、`created_at`、`source_file` 元数据 |
| `aigility/rag/config.py` | Payload Index 默认新增 `content_type` 和 `heading` 索引 |

### 新增元数据字段

| 字段 | 来源 | 示例值 |
|------|------|--------|
| `content_type` | AST splitter 分析 block 类型 | `"text"` / `"table"` / `"code"` |
| `heading` | AST splitter 标题层级追踪 | `"七、产品线总览"` |
| `section_path` | AST splitter 面包屑路径 | `"八、主推产品型号 > 8.2 CD-K2..."` |
| `chunk_id` | add_file 生成 | `"3a380f07..._c0008"` |
| `created_at` | add_file 生成 | `"2026-05-19T10:26:29.985571+00:00"` |
| `source_file` | add_file 生成 | `"test.docx"` |

### 验证结果

Qdrant 中 chunk 的 metadata 示例：

```json
{
  "content_type": "table",
  "heading": "8.2 CD-K2 1250/2500kg (220V Variable Frequency)",
  "section_path": "八、主推产品型号及规格参数 > 8.2 CD-K2...",
  "chunk_id": "3a380f07..._c0013",
  "source_file": "test.docx",
  "created_at": "2026-05-19T10:26:29.985571+00:00"
}
```

### 搜索输出改进

搜索结果现在展示章节和类型信息：

```
--- [来源: test.docx (片段 1) | 章节: 七、产品线总览 | 类型: table] ---
```

### 预期效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 检索精度（Context Recall） | 基准 | ↑ 5%-10% |
| 按结构过滤能力 | 无 | 支持 heading/content_type/section_path 过滤 |
| 结果可溯源性 | 仅文件名 | 文件名 + 章节 + 面包屑路径 |
| 入库时间 | 基准 | ↑ 5%-10% |

---

## 四、待实施：Small-to-Big 分块策略

### 目标

用小块（子块，128 tok）做向量检索，返回给 LLM 时扩展到父块（512 tok），替代现有 Buffer 机制。

### 需要修改的文件

| 文件 | 改动 |
|------|------|
| `aigility/rag/markdown_splitter.py` | 实现父子块切分逻辑 |
| `aigility/rag/service.py` | 检索时查子块、取父块；父块存储管理 |
| `aigility/rag/config.py` | 新增 `SmallToBigConfig` 配置 |

### 关键设计

- 父块：512 tok，语义完整的上下文单元
- 子块：128 tok，用于向量检索，精度高
- 父块存储：SQLite 通用方案 + Qdrant payload 可选
- 通过 `parent_chunk_id` 关联父子块

### 预期效果

| 指标 | Buffer 方案 | Small-to-Big |
|------|------------|--------------|
| 检索精度 | 基准 | ↑ 10%-20% |
| 上下文完整性 | 250 字符 buffer | 512 tok 完整父块 |
| 答案质量（Faithfulness） | 基准 | ↑ 10%-15% |
| 检索延迟 | 基准 | ↑ 5-15ms（额外查父块） |
| 存储开销 | 基准 | ↑ 20%-40% |

---

## 五、待实施：HyDE 查询增强（可选）

### 目标

用户问法与文档表述差异大时，先让 LLM 生成假设性答案，用假设答案的向量去检索。

### 需要修改的文件

| 文件 | 改动 |
|------|------|
| `aigility/rag/service.py` | 新增 HyDE 增强检索器 |
| `aigility/rag/config.py` | 新增 `HyDEConfig` 配置 |

### 预期效果

| 指标 | 不启用 | 启用 |
|------|--------|------|
| Answer Relevancy | 基准 | ↑ 10%-20% |
| 检索延迟 | 基准 | ↑ 200-500ms |
| Token 消耗（检索） | 0 | ↑ 200-500 tokens |

---

## 六、待实施：RAGAS 效果评估

### 目标

用 RAGAS 框架量化每步改造的实际增量收益。

### 评估指标

| 指标 | 含义 | 优化目标 |
|------|------|---------|
| Faithfulness | 答案是否基于检索上下文 | > 0.85 |
| Answer Relevancy | 答案与问题的相关度 | > 0.80 |
| Context Recall | 检索覆盖回答所需信息的程度 | > 0.75 |

### A/B 对比阶段

| 阶段 | 改造内容 | 对比基准 |
|------|---------|---------|
| Baseline | 固定切分 + Buffer | — |
| Stage 1 | + Payload Index + Metadata | vs Baseline |
| Stage 2 | + Small-to-Big 分块 | vs Stage 1 |
| Stage 3 | + HyDE 查询增强 | vs Stage 2 |

---

## 七、分层定价参考

基于已实现和待实施的优化方案：

| 套餐 | 检索策略 | Metadata | HyDE | 适用场景 |
|------|---------|---------|------|---------|
| **基础版** | 固定切分 + Buffer | 基础字段 | 不启用 | 简单文档查询 |
| **专业版** | Small-to-Big | 完整字段 | 可选启用 | 复杂知识问答 |
| **企业版** | Small-to-Big + HyDE | 完整字段 + 自定义 | 自动启用 | 跨领域/推理类问答 |

---

## 八、变更记录

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-05-19 | v1.0 | 初始方案文档 |
| 2026-05-19 | v2a | 标记 Payload Index 和 Metadata 为已完成，记录验证结果 |
