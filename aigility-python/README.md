# Aigility Python SDK

模块化 AI 能力库，提供 RAG（检索增强生成）、Chat、ChatFlow 等能力。

## 安装

```bash
# 安装核心库
pip install aigility-python

# 安装 RAG 完整功能（推荐）
pip install aigility-python[rag-full]

# 按需安装
pip install aigility-python[rag,embedding-huggingface,vectorstore-chroma]
```

## 快速开始

### RAG 服务

```python
from aigility.rag import RAGService, RAGConfig, EmbeddingConfig, VectorStoreConfig

# 1. 配置（所有配置在业务项目中定义，不在 SDK 中）
config = RAGConfig(
    embedding=EmbeddingConfig(
        provider="huggingface",  # 或 "dashscope"
        model_name="BAAI/bge-small-zh-v1.5"
    ),
    vector_store=VectorStoreConfig(
        provider="chroma",
        persist_path="./my_knowledge_base"
    )
)

# 2. 初始化服务
service = RAGService(config=config)

# 3. 添加文档
service.add_file("/path/to/document.pdf")

# 4. 检索
result = service.search("我的问题")
print(result)
```

### 使用 DashScope 嵌入模型

```python
import os
from aigility.rag import RAGService, RAGConfig, EmbeddingConfig, VectorStoreConfig

config = RAGConfig(
    embedding=EmbeddingConfig(
        provider="dashscope",
        model_name="text-embedding-v4",
        api_key=os.getenv("DASHSCOPE_API_KEY")  # 或设置环境变量
    ),
    vector_store=VectorStoreConfig(
        provider="chroma",
        persist_path="./chroma_db"
    )
)

service = RAGService(config=config)
```

### 使用 Milvus 向量库

```python
from aigility.rag import RAGService, RAGConfig, EmbeddingConfig, VectorStoreConfig

config = RAGConfig(
    embedding=EmbeddingConfig(provider="huggingface"),
    vector_store=VectorStoreConfig(
        provider="milvus",
        url="http://localhost:19530",
        collection_name="my_collection"
    )
)

service = RAGService(config=config)
```

## 配置说明

### EmbeddingConfig

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `provider` | 模型提供商 | `"huggingface"` |
| `model_name` | 模型名称 | `"BAAI/bge-small-zh-v1.5"` |
| `api_key` | API 密钥 | `None`（可通过环境变量设置） |
| `base_url` | API 基础 URL | 各平台默认值 |

支持的 provider:
- `huggingface`: 本地运行，无需 API Key
- `dashscope`: 阿里云灵积平台
- `openai`: OpenAI API

### VectorStoreConfig

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `provider` | 向量库类型 | `"chroma"` |
| `collection_name` | 集合名称 | `"rag_collection"` |
| `persist_path` | 持久化路径 | `"./chroma_db"` |
| `url` | 远程服务地址 | `"http://localhost:19530"` |

支持的 provider:
- `chroma`: 本地轻量级向量库
- `faiss`: Facebook AI 相似性搜索
- `milvus`: 分布式向量数据库

## 开发

```bash
# 克隆项目
git clone https://github.com/AIGility-Cloud-Innovation/aigility-python.git
cd aigility-python

# 安装开发依赖
pip install -e ".[dev,rag-full]"

# 运行测试
pytest
```

## License

MIT License

