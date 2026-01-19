# AIGility ADK 开发指南

## 项目结构

```
aigility/
├── core/           # 核心功能模块
│   ├── config.py   # 配置管理
│   └── types.py    # 类型定义
├── http/           # HTTP 传输层
│   └── client.py   # HTTP 客户端
├── model/          # 模型层
│   └── llm.py      # LLM 提供者
├── memory/         # 记忆管理
│   ├── client.py   # 记忆客户端
│   └── memory.py   # 记忆接口
├── chat/           # 基础对话（基于 LangChain）
│   └── agent.py    # 对话智能体
├── chatflow/       # 对话流管理（基于 LangGraph）
│   └── service.py  # 对话流服务
├── workflow/       # 工作流引擎（基于 LangGraph）
│   ├── engine.py   # 工作流引擎
│   └── builder.py  # 工作流构建器
├── rag/            # RAG 检索增强生成
│   ├── service.py  # RAG 服务
│   ├── workflow.py # RAG 工作流（基于 LangGraph）
│   ├── embeddings/ # Embedding 模型
│   ├── vector_stores/ # 向量存储
│   └── ingestion.py # 文档摄取
├── adp/            # ADP 服务客户端
│   └── client.py   # ADP 客户端
└── client.py       # 主客户端接口
```

## 技术栈

- **LangChain**: 用于基础对话能力（chat 模块）
- **LangGraph**: 用于对话流和工作流（chatflow, workflow 模块）
- **httpx**: HTTP 客户端
- **pydantic**: 数据验证

## 开发环境设置

1. 安装依赖：
```bash
make install-dev
```

2. 运行测试：
```bash
make test
```

3. 代码格式化：
```bash
make format
```

4. 代码检查：
```bash
make lint
```

## 模块说明

### Core 模块

提供基础抽象类和类型定义：
- `BaseAgent`: 智能体基类
- `BaseTool`: 工具基类
- `BaseMemory`: 记忆基类
- `State`: 状态对象
- `Message`: 消息对象

### HTTP 模块

提供 HTTP 传输层功能：
- 连接池管理
- 熔断器
- 重试机制

### Memory 模块

提供记忆管理功能：
- 添加记忆
- 搜索记忆
- 记忆管理

### Chat 模块

基于 LangChain 提供基础对话能力。

### ChatFlow 模块

基于 LangGraph 提供对话流管理。

### Workflow 模块

基于 LangGraph 提供工作流引擎。

### RAG 模块

提供 RAG（检索增强生成）能力，包含：
- **基础 RAG 服务**：文档摄取、向量化、语义检索
- **工作流模式 RAG**：基于 LangGraph 的可组合 RAG 工作流
- **多 Embedding 支持**：DashScope、HuggingFace 等
- **多向量存储支持**：Chroma、FAISS、Milvus 等

## 使用示例

### 基础使用

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
result = await memory.add(
    messages=[{"role": "user", "content": "Hello"}],
    user_id="user123",
    character_id="assistant"
)

# 创建对话智能体
agent = client.create_chat_agent(name="my_agent")
```

### RAG 使用

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

### 工作流使用

```python
from aigility.workflow import WorkflowEngine, WorkflowGraphBuilder

# 构建工作流
builder = WorkflowGraphBuilder()
builder.add_node("start", start_node_func)
builder.add_node("process", process_node_func)
builder.add_edge("start", "process")
builder.set_start("start")

# 创建引擎
engine = builder.build()
result = await engine.invoke(initial_state)
```

## 待实现功能

- [ ] LangChain Agent 集成
- [ ] LangGraph StateGraph 集成
- [ ] LLM 提供者实现（OpenAI, Anthropic 等）
- [ ] Embeddings 提供者实现
- [ ] 知识库存储实现（向量数据库）
- [ ] 完整的测试套件
- [ ] 文档完善

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License

