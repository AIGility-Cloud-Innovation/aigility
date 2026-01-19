# AIGility ADK - Agent Development Kit

基于 LangGraph/LangChain 的智能体开发框架，提供开箱即用的 RAG、记忆管理、对话流等能力。

## 特性

- **RAG 检索增强生成**
  - 基础 RAG 服务：文档摄取、向量化、语义检索
  - 工作流模式 RAG：基于 LangGraph 的可组合 RAG 工作流
  - 多 Embedding 支持：DashScope、HuggingFace 等
  - 多向量存储支持：Chroma、FAISS、Milvus 等

- **记忆管理**
  - 持久化对话历史
  - 语义记忆检索
  - 可扩展的记忆存储

- **对话流管理**
  - 基于 LangGraph 的对话流编排
  - 工具调用支持
  - 状态管理

- **工作流引擎**
  - 可视化工作流构建
  - 节点编排
  - 条件分支和循环

## 安装

```bash
pip install aigility
```

## 快速开始

### RAG 基础使用

```python
from aigility.rag import RAGService, RAGConfig, EmbeddingConfig, VectorStoreConfig

# 配置 RAG 服务
config = RAGConfig(
    embedding=EmbeddingConfig(provider="dashscope", api_key="your-api-key"),
    vector_store=VectorStoreConfig(provider="chroma", persist_path="./my_db")
)

# 初始化服务
rag_service = RAGService(config=config)

# 添加文档
rag_service.add_file("document.pdf")

# 检索相关内容
results = rag_service.search("什么是机器学习？")
print(results)
```

### RAG 工作流模式

```python
from aigility.rag import RAGService, create_rag_workflow
from langchain_openai import ChatOpenAI

# 初始化 RAG 服务和 LLM
rag_service = RAGService()
llm = ChatOpenAI(model="gpt-4")

# 创建工作流
workflow = create_rag_workflow(rag_service, llm)

# 执行查询
result = workflow.invoke({
    "query": "什么是机器学习？",
    "messages": []
})

print(result["answer"])
```

### 客户端使用

```python
from aigility import ADKClient, create_client

# 创建客户端
client = create_client(
    llm_provider="openai",
    llm_api_key="your-api-key",
    memory_api_key="your-memory-api-key",
)

# 使用记忆
memory = client.memory
await memory.add(
    messages=[{"role": "user", "content": "Hello"}],
    user_id="user123",
    character_id="assistant"
)

# 创建对话智能体
agent = client.create_chat_agent(name="my_agent")
```

## 文档

- [开发指南](DEVELOPMENT.md) - 详细的开发文档和架构说明
- [示例代码](examples/) - 各种使用场景的示例代码

## 项目结构

```
aigility/
├── core/           # 核心配置和类型
├── memory/         # 记忆管理
├── chat/           # 基础对话
├── chatflow/       # 对话流管理
├── workflow/       # 工作流引擎
├── rag/            # RAG 检索增强生成
│   ├── service.py  # RAG 服务
│   ├── workflow.py # RAG 工作流
│   ├── embeddings/ # Embedding 模型
│   ├── vector_stores/ # 向量存储
│   └── ingestion.py # 文档摄取
├── adp/            # ADP 服务客户端
└── client.py       # 主客户端
```

## 技术栈

- **LangChain**: 基础对话能力
- **LangGraph**: 对话流和工作流编排
- **Chroma/FAISS/Milvus**: 向量存储
- **DashScope/HuggingFace**: Embedding 模型

## 许可证

MIT License
