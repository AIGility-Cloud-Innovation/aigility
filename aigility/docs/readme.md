# AIGility Provider 使用文档 & 配置示例

本文件提供了 AIGility 中所有支持的 Provider（模型提供商、向量数据库、内存库）的详细使用文档和配置示例。

## 目录
- [1. LLM 模型提供商 (LLM Providers)](#1-llm-模型提供商-llm-providers)
- [2. 嵌入模型提供商 (Embedding Providers)](#2-嵌入模型提供商-embedding-providers)
- [3. 向量数据库 (Vector Databases - RAG)](#3-向量数据库-vector-databases---rag)
- [4. 内存提供商 (Memory Providers)](#4-内存提供商-memory-providers)

---

## 1. LLM 模型提供商 (LLM Providers)

AIGility 通过 `ModelFactory` 统一管理 LLM 实例，目前主要支持 OpenAI 和 DeepSeek（以及所有兼容 OpenAI 接口的提供商）。

### 配置参数 (ADKConfig)
| 参数名 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `llm_provider` | `str` | `"openai"` | 提供商名称 (`openai`, `deepseek`) |
| `llm_model` | `str` | `"gpt-4"` | 模型名称 |
| `llm_api_key` | `str` | `None` | API 密钥 |
| `llm_base_url` | `str` | `None` | API 基础 URL |
| `llm_temperature`| `float`| `0.7` | 采样温度 |

### 示例代码
```python
from aigility.core.config import ADKConfig
from aigility.core.model_factory import ModelFactory

# OpenAI 配置
config = ADKConfig(
    llm_provider="openai",
    llm_model="gpt-4",
    llm_api_key="sk-...",
)

# DeepSeek 配置
config_ds = ADKConfig(
    llm_provider="deepseek",
    llm_model="deepseek-chat",
    llm_api_key="sk-...",
    llm_base_url="https://api.deepseek.com"
)

llm = ModelFactory.create_llm(config)
```

---

## 2. 嵌入模型提供商 (Embedding Providers)

用于 RAG 流程中的文本向量化。支持本地模型和在线 API。

### 支持的 Provider
- `huggingface`: 本地运行，支持 `sentence-transformers` 模型。
- `dashscope`: 阿里云灵积平台。
- `zhipuai`: 智谱 AI。
- `openai`: OpenAI 嵌入模型。

### 配置方案
通过 `EmbeddingConfig` 类进行配置。

#### HuggingFace (本地)
```python
from aigility.rag.config import EmbeddingConfig

config = EmbeddingConfig(
    provider="huggingface",
    model_name="BAAI/bge-small-zh-v1.5",
    kwargs={"device": "cpu"} # 可选：'cuda', 'mps'
)
```

#### DashScope (阿里云)
```python
config = EmbeddingConfig(
    provider="dashscope",
    model_name="text-embedding-v2",
    api_key="sk-..." # 也可通过 DASHSCOPE_API_KEY 环境变量设置
)
```

#### Zhipu AI
```python
config = EmbeddingConfig(
    provider="zhipuai",
    model_name="embedding-2",
    api_key="sk-..." # 也可通过 ZHIPUAI_API_KEY 环境变量设置
)
```

---

## 3. 向量数据库 (Vector Databases - RAG)

支持多种向量存储方式，满足从本地开发到生产环境的不同需求。

### 支持的 Provider
- `chroma`: 轻量级本地数据库，适合快速原型。
- `faiss`: Meta 开发的高性能向量搜索库。
- `milvus`: 分布式向量数据库，适合大规模生产。
- `qdrant`: 高性能向量数据库，支持复杂过滤。

### 配置方案
通过 `VectorStoreConfig` 类进行配置。

#### Chroma (本地持久化)
```python
from aigility.rag.config import VectorStoreConfig

config = VectorStoreConfig(
    provider="chroma",
    collection_name="my_docs",
    persist_path="./chroma_db"
)
```

#### Qdrant (在线/远程)
```python
config = VectorStoreConfig(
    provider="qdrant",
    collection_name="my_docs",
    url="http://localhost:6333"
)
```

#### Milvus
```python
config = VectorStoreConfig(
    provider="milvus",
    collection_name="my_docs",
    url="http://localhost:19530"
)
```

---

## 4. 内存提供商 (Memory Providers)

用于管理 Agent 的长期和短期记忆。

### 支持的 Provider
- `timem`: 专为 AI Agent 设计的记忆存储服务。

### 配置方案
通过 `MemoryConfig` 进行配置（包含在 `ADKConfig` 中或独立配置）。

#### Timem 配置
```python
from aigility.memory.config import MemoryConfig, MemoryProviderConfig

config = MemoryConfig(
    provider=MemoryProviderConfig(
        provider="timem",
        api_key="your-timem-api-key",
        base_url="https://api.timem.cloud",
        enabled=True
    )
)
```

### 环境变量支持
多数 Provider 支持通过环境变量简化配置：
- `OPENAI_API_KEY`
- `DASHSCOPE_API_KEY`
- `ZHIPUAI_API_KEY`
- `TIMEM_API_KEY`
- `TIMEM_BASE_URL`
