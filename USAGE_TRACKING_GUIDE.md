# Aigility SDK - Token 用量追踪使用指南

## 快速开始

```python
from aigility.rag import RAGService, RAGConfig, EmbeddingConfig, VectorStoreConfig, RerankConfig

config = RAGConfig(
    embedding=EmbeddingConfig(provider="zhipuai", model_name="embedding-3"),
    vector_store=VectorStoreConfig(provider="qdrant", url="http://localhost:6333"),
    rerank=RerankConfig(enabled=True),
)
service = RAGService(config)
```

## 添加文件

```python
result = service.add_file("document.pdf")

# 返回 AddFileResult 对象
print(result.file_name)       # 文件名
print(result.file_hash)       # 文件哈希
print(result.usage.embedding.total_tokens)  # embedding 消耗的 token
```

`AddFileResult` 同时支持 dict 风格访问（向后兼容）：

```python
print(result["file_name"])
print(result["file_hash"])
```

## 搜索

```python
search_result = service.search("你的查询")

# 返回 SearchResult 对象
print(str(search_result))              # 格式化结果字符串（向后兼容）
print(search_result.content)           # 同上
print(search_result.documents)         # 原始 Document 列表
print(search_result.usage.embedding.total_tokens)  # 查询 embedding token
print(search_result.usage.rerank.total_tokens)     # rerank token
print(search_result.metadata)          # 检索元数据（权重、文档数等）
```

`SearchResult` 支持 `str()` 和 `bool()` 转换，可直接用于字符串上下文：

```python
if search_result:        # bool 检查
    print(str(search_result))  # 字符串输出
```

## 累计用量追踪

```python
# 查看累计用量
print(service.usage.total_tokens)       # 总 token
print(service.usage.embedding.total_tokens)  # 累计 embedding token
print(service.usage.rerank.total_tokens)     # 累计 rerank token

# 重置计数
service.reset_usage()
```

## 实时回调监控

```python
def on_usage(usage):
    print(f"本次调用: embedding={usage.embedding.total_tokens}, rerank={usage.rerank.total_tokens}")

service.on_usage(on_usage)

# 每次 add_file / search 后自动触发回调
service.add_file("doc.pdf")   # 回调触发
service.search("查询")        # 回调触发
```

## 完整示例

```python
from aigility.rag import RAGService, RAGConfig, EmbeddingConfig, VectorStoreConfig, RerankConfig

config = RAGConfig(
    embedding=EmbeddingConfig(provider="zhipuai", model_name="embedding-3"),
    vector_store=VectorStoreConfig(provider="qdrant", url="http://localhost:6333"),
    rerank=RerankConfig(enabled=True),
)
service = RAGService(config)

# 注册用量回调
service.on_usage(lambda u: print(f"[Token] embedding={u.embedding.total_tokens}, rerank={u.rerank.total_tokens}"))

# 添加文件
result = service.add_file("report.pdf")
print(f"文件: {result.file_name}, hash: {result.file_hash}")
print(f"本次 embedding token: {result.usage.embedding.total_tokens}")

# 搜索
sr = service.search("核心结论")
print(str(sr))
print(f"查询 embedding: {sr.usage.embedding.total_tokens}")
print(f"Rerank: {sr.usage.rerank.total_tokens}")

# 查看累计
print(f"累计总 token: {service.usage.total_tokens}")
```

## 数据类型说明

| 类型 | 字段 | 说明 |
|------|------|------|
| `TokenUsage` | `input_tokens` | 输入 token 数 |
| | `total_tokens` | 总 token 数 |
| | `model` | 模型名称 |
| `UsageStats` | `embedding` | embedding 消耗（TokenUsage） |
| | `rerank` | rerank 消耗（TokenUsage） |
| | `total_tokens` | 总消耗（property） |
| `SearchResult` | `content` | 格式化结果字符串 |
| | `documents` | 原始 Document 列表 |
| | `usage` | 本次搜索用量（UsageStats） |
| | `metadata` | 检索元数据 |
| `AddFileResult` | `file_hash` | 文件哈希 |
| | `file_name` | 文件名 |
| | `usage` | 本次入库用量（UsageStats） |
