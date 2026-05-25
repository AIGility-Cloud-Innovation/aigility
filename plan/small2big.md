# Small2Big 实现计划

## Context

当前 RAG 系统使用 prev_buffer/next_buffer 机制在 chunk 边界拼接 250 字符上下文，信息窗口有限。Small2big 通过两层分块（小 child 用于检索、大 parent 用于返回 LLM）彻底解决跨 chunk 信息丢失问题，并替代 buffer 机制。

## 实现步骤（按依赖顺序）

### Step 1: config.py — 新增配置字段

**文件:** `aigility/rag/config.py`

- `IngestionConfig` 新增 4 个字段:
  - `enable_small2big: bool = True`
  - `parent_chunk_size: int = 1024`（约 512 tokens）
  - `child_chunk_size: int = 256`（约 128 tokens）
  - `child_chunk_overlap: int = 64`
- `PayloadIndexConfig` 默认字段新增:
  - `PayloadIndexField(field_name="metadata.parent_chunk_id", field_type="keyword")`

### Step 2: markdown_splitter.py — 核心两层分块

**文件:** `aigility/rag/markdown_splitter.py`

- `__init__` 新增参数: `enable_small2big`, `parent_chunk_size`, `child_chunk_size`, `child_chunk_overlap`
- 新增方法 `split_text_structured_small2big(text)`:
  - Phase 1: 复用 `_tokens_to_blocks` + `_merge_blocks`，但用 `parent_chunk_size` 作为上限生成 parent chunks
  - Phase 2: 每个 parent chunk 按 `child_chunk_size` 拆成 child chunks（句子边界切分，overlap 为 `child_chunk_overlap`）
  - 表格/代码块: 如果 `content_type` 是 table/code，不拆分，整个作为单个 child
  - 返回: 每个 child chunk dict 包含 `text`, `parent_text`, `parent_index`, `child_index`, `total_children_in_parent` 等
- 新增方法 `split_documents_small2big(documents)`:
  - 调用上面的方法，为每个 child 创建 Document 对象
  - metadata 包含 `parent_text`, `parent_chunk_id`(占位), `parent_index`, `child_index` 等
  - 不包含 `prev_buffer`/`next_buffer`

### Step 3: ingestion.py — 路由到 small2big

**文件:** `aigility/rag/ingestion.py`

- `__init__`: 向 `MarkdownASTSplitter` 传入新的 small2big 参数
- `process_documents` 第 393 行: 根据 `self.config.enable_small2big` 分支调用 `split_documents_small2big` 或 `split_documents`

### Step 4: service.py add_file — 注入 parent_chunk_id

**文件:** `aigility/rag/service.py`, `add_file` 方法

- 第 389-418 行替换为分支:
  - small2big 启用: 注入基础元数据 + `parent_chunk_id = f"{file_hash}_p{parent_idx:04d}"`，不再注入 prev/next_buffer
  - small2big 关闭: 保留原有 buffer 注入逻辑

### Step 5: service.py _format_search_results — 用 parent_text 替代 buffer

**文件:** `aigility/rag/service.py`, `_format_search_results` 方法

- 重写逻辑:
  - 遍历 docs，检查 `parent_text` 是否存在
  - 存在: 用 `parent_text` 作为返回内容，通过 `parent_chunk_id` 去重（同一 parent 只输出一次）
  - 不存在（旧文档）: 回退到 prev_buffer/next_buffer 标记逻辑
- 不再需要按 file_hash 分组 + chunk_index 排序 + 连续合并的逻辑

### Step 6: hybrid_search.py — 同步更新

**文件:** `aigility/rag/hybrid_search.py`, `enhanced_search_method` 函数

- 与 Step 5 相同的模式: 检查 parent_text，有则用 parent_text 并去重，无则回退 buffer

## 边界情况处理

| 情况 | 处理方式 |
|------|---------|
| 旧文档（无 parent_text） | 回退到 buffer 标记机制 |
| 极小文档（< child_chunk_size） | parent = child，parent_text == page_content |
| 表格/代码块 | 不拆分，整个作为单个 child |
| 多个 child 命中同一 parent | parent_chunk_id 去重，只输出一次 |

## 验证方式

1. 修改完成后，用测试文件调用 `add_file` 入库，检查 Qdrant 中 child chunk 的 metadata 是否包含 `parent_text` 和 `parent_chunk_id`
2. 调用 `search()` 验证返回的是 parent_text 而非 buffer 标记
3. 检查旧文档仍能正常检索（回退到 buffer 机制）
