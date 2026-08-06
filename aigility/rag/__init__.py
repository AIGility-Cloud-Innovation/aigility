# RAG module initialization
"""
RAG (Retrieval-Augmented Generation) 模块

提供检索增强生成（RAG）能力，支持：
- 基础 RAG 服务（RAGService）
- BM25 混合检索（语义检索 + 关键词检索）
- 工作流模式 RAG（create_rag_workflow，基于 LangGraph）

## 使用方式

### 1. 基础 RAG 服务
```python
from aigility.rag import RAGService, RAGConfig, EmbeddingConfig, VectorStoreConfig

config = RAGConfig(
    embedding=EmbeddingConfig(provider="zhipuai", api_key="your-key"),
    vector_store=VectorStoreConfig(provider="qdrant", url="http://localhost:6333")
)
service = RAGService(config=config)

# 添加文档
service.add_file("path/to/document.pdf")

# 检索（使用默认的语义检索）
result = service.search("你的查询")
```

### 2. BM25 混合检索（推荐）
```python
# 构建BM25索引（首次使用前必须）
service.build_bm25_index()

# 使用混合检索（结合语义理解和关键词匹配）
result = service.search_bm25_hybrid("你的查询")

# 对于精确查询，可以增加BM25权重
result = service.search_bm25_hybrid(
    "目标市场",
    semantic_weight=0.4,  # 语义检索权重
    bm25_weight=0.6       # BM25关键词权重
)
```

### 3. 工作流模式 RAG
```python
from aigility.rag import create_rag_workflow
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")
workflow = create_rag_workflow(service, llm)
result = workflow.invoke({"query": "你的问题", "messages": []})
```

## 检索方法对比

| 方法 | 适用场景 | 特点 |
|------|---------|------|
| `search()` | 语义查询 | 理解查询意图，适合复杂问题 |
| `search_bm25_hybrid()` | 精确查询 | 结合语义和关键词，确保关键信息不遗漏 |

## 优化建议

1. **首次使用时构建BM25索引**：
   ```python
   service.build_bm25_index()
   ```

2. **根据查询类型选择检索方法**：
   - 语义查询（"产品定位策略"）→ `search()`
   - 精确查询（"目标市场"）→ `search_bm25_hybrid()`

3. **添加/删除文档后重建索引**：
   ```python
   service.add_file("new_doc.pdf")
   service.build_bm25_index(force_rebuild=True)
   ```
"""

from importlib import import_module
from typing import TYPE_CHECKING

from .config import (
    RAGConfig,
    EmbeddingConfig,
    VectorStoreConfig,
    IngestionConfig,
    RerankConfig,
)
from .client import TimeMRAGClient, create_timem_rag_client
from .usage_tracking import TokenUsage, UsageStats, SearchResult, AddFileResult

if TYPE_CHECKING:
    from .embeddings.wrapper import EmbeddingWrapper
    from .ingestion import IngestionManager
    from .rerank import BaseRerankAdapter, RerankFactory
    from .service import RAGService
    from .workflow import RAGWorkflowState, create_rag_workflow


_LAZY_EXPORTS = {
    "RAGService": (".service", "RAGService"),
    "IngestionManager": (".ingestion", "IngestionManager"),
    "RerankFactory": (".rerank", "RerankFactory"),
    "BaseRerankAdapter": (".rerank", "BaseRerankAdapter"),
    "EmbeddingWrapper": (".embeddings.wrapper", "EmbeddingWrapper"),
    "create_rag_workflow": (".workflow", "create_rag_workflow"),
    "RAGWorkflowState": (".workflow", "RAGWorkflowState"),
}


def __getattr__(name: str):
    try:
        module_name, attribute = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))

__all__ = [
    # 基础服务
    "RAGService",
    "RAGConfig",
    "EmbeddingConfig",
    "VectorStoreConfig",
    "IngestionConfig",
    "RerankConfig",
    "IngestionManager",
    # Rerank
    "RerankFactory",
    "BaseRerankAdapter",
    # Usage Tracking
    "TokenUsage",
    "UsageStats",
    "SearchResult",
    "AddFileResult",
    "EmbeddingWrapper",
    # 工作流
    "create_rag_workflow",
    "RAGWorkflowState",
    # 云服务客户端
    "TimeMRAGClient",
    "create_timem_rag_client",
]
