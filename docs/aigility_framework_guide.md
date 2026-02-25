# Aigility ADK 框架使用与设计文档

## 目录

- [1. 框架概述](#1-框架概述)
- [2. 快速开始](#2-快速开始)
- [3. 核心架构设计](#3-核心架构设计)
- [4. RAG 模块详解](#4-rag-模块详解)
- [5. Memory 模块详解](#5-memory-模块详解)
- [6. Chat 与 ChatFlow 服务](#6-chat-与-chatflow-服务)
- [7. 配置管理](#7-配置管理)
- [8. 支持的服务](#8-支持的服务)
- [9. 设计模式与最佳实践](#9-设计模式与最佳实践)

---

## 1. 框架概述

### 1.1 背景

**Aigility ADK (Agent Development Kit)** 是一个基于 Python 的现代智能体开发框架，构建于 LangGraph 和 LangChain 之上。框架提供了一套完整的工具链，用于构建具有对话能力、知识检索、记忆管理和工作流编排的智能应用。

### 1.2 核心特性

| 特性 | 描述 |
|------|------|
| **RAG 检索增强** | 支持本地和云端 RAG 服务，智能文档处理，语义检索 |
| **记忆管理** | 持久化对话历史，语义记忆检索，多维度索引 |
| **对话流编排** | 基于 LangGraph 的状态机，支持 CoT 推理和工具调用 |
| **多 LLM 支持** | OpenAI、DeepSeek、智谱 AI、Anthropic 等 |
| **可扩展架构** | Provider 模式，易于添加新的向量存储、Embedding 模型 |
| **生产就绪** | 连接池、重试机制、熔断器、性能监控 |

### 1.3 技术栈

```
┌─────────────────────────────────────────────────────────┐
│                     Aigility ADK                        │
├─────────────────────────────────────────────────────────┤
│  ChatFlow  │  RAG  │  Memory  │  Workflow  │  HTTP     │
├─────────────────────────────────────────────────────────┤
│  LangGraph  │  LangChain  │  Pydantic  │  httpx       │
├─────────────────────────────────────────────────────────┤
│  Chroma  │  Qdrant  │  FAISS  │  HuggingFace          │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 快速开始

### 2.1 安装

#### 核心安装（推荐）

```bash
pip install aigility
```

#### 完整功能安装

```bash
# 本地 RAG (HuggingFace + Chroma)
pip install "aigility[rag-local]"

# Qdrant RAG
pip install "aigility[rag-qdrant]"

# 太忆 RAG 云服务
pip install "aigility[timem-rag]"

# 全功能
pip install "aigility[all]"
```

### 2.2 环境配置

创建 `.env` 文件：

```bash
# DeepSeek API 配置
DEEPSEEK_API_KEY=sk-your-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 智谱 AI 配置（用于 Embedding）
ZHIPUAI_API_KEY=your-api-key

# Qdrant 配置（本地向量存储）
QDRANT_URL=http://localhost:6333

# 太忆 RAG 配置（可选）
TIMEM_ENABLED=true
TIMEM_API_KEY=sk-your-timem-key
TIMEM_BASE_URL=http://localhost:8000
```

### 2.3 基础使用示例

#### Chat 服务

```python
from aigility.chat.service import ChatService
from aigility.chat.schema import ChatRequest
from aigility.core.config import ADKConfig
import os

# 初始化配置
config = ADKConfig(
    llm_provider="deepseek",
    llm_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
    llm_api_key=os.getenv("DEEPSEEK_API_KEY"),
    llm_base_url=os.getenv("DEEPSEEK_BASE_URL"),
    timem_enabled=os.getenv("TIMEM_ENABLED", "false").lower() == "true",
    timem_api_key=os.getenv("TIMEM_API_KEY"),
    timem_base_url=os.getenv("TIMEM_BASE_URL")
)

# 创建 Chat 服务
chat_service = ChatService(adk_config=config)

# 发起聊天请求
request = ChatRequest(
    user_input="Mac 的 iCloud 如何操作？",
    kb_id="kb_e61b976ff864"  # 太忆知识库 ID
)

response = chat_service.process_chat(request)
print(f"AI 回复: {response.response}")
print(f"思考过程: {response.thought_process}")
```

---

## 3. 核心架构设计

### 3.1 项目结构

```
aigility/
├── __init__.py              # 主包入口
├── core/                    # 核心抽象和配置
│   ├── config.py           # ADKConfig, AgentConfig, ToolConfig
│   ├── model_factory.py    # LLM 模型工厂
│   └── types.py            # 类型定义
├── chat/                    # 聊天服务
│   ├── service.py          # ChatService 主服务
│   └── schema.py           # ChatRequest, ChatResponse
├── chatflow/                # LangGraph 对话流
│   ├── flow.py             # ChatFlow 状态机
│   ├── schema.py           # State, ToolCall, ToolResult
│   └── prompts/            # Prompt 配置
│       └── chat_flow_config.yaml
├── rag/                     # RAG 检索增强
│   ├── service.py          # RAGService 主服务
│   ├── client.py           # TimeMRAGClient 云服务客户端
│   ├── config.py           # RAGConfig
│   ├── embeddings/         # Embedding 工厂
│   ├── vector_stores/      # 向量存储工厂
│   └── ingestion.py        # 文档处理
├── memory/                  # 记忆管理
│   ├── memory.py           # Memory 主类
│   ├── config.py           # MemoryConfig
│   └── providers/          # Provider 实现
│       ├── base.py         # BaseMemoryProvider
│       ├── timem.py        # TimemMemoryProvider
│       └── factory.py      # MemoryProviderFactory
├── http/                    # HTTP 客户端
│   └── client.py           # HTTPClient (连接池、重试、熔断)
├── workflow/                # 工作流引擎
└── utils/                   # 工具函数
```

### 3.2 架构原则

1. **分层架构**：Service → Flow → Core，清晰的职责分离
2. **Provider 模式**：可插拔的组件设计（Embedding、VectorStore、Memory）
3. **配置驱动**：环境变量 + 配置对象，灵活的配置管理
4. **异步优先**：全链路 async/await 支持
5. **类型安全**：Pydantic 模型验证

### 3.3 数据流

```
用户请求 → ChatService → ChatFlow → LangGraph
                              ↓
                    Agent Decision (是否调用工具)
                              ↓
                    Tool Executor (RAG / Web Search)
                              ↓
                    Prepare for Generation
                              ↓
                    Stream Response → 返回用户
```

---

## 4. RAG 模块详解

### 4.1 模块架构

RAG 模块采用三层架构：

```
┌────────────────────────────────────────┐
│          RAGService (服务层)            │
│  - add_file()                          │
│  - search()                            │
│  - clear_knowledge_base()              │
├────────────────────────────────────────┤
│   IngestionManager (数据处理层)         │
│  - PDF/Excel/Word/Text 解析            │
│  - 智能分块                             │
│  - 上下文缓冲                           │
├────────────────────────────────────────┤
│  Embedding + VectorStore (存储层)       │
│  - HuggingFace / DashScope / ZhipuAI   │
│  - Chroma / Qdrant / FAISS / Milvus    │
└────────────────────────────────────────┘
```

### 4.2 核心设计原理

#### 4.2.1 智能文档处理

RAG 模块针对不同文档类型采用专门的解析策略：

| 文档类型 | 解析器 | 处理方式 |
|---------|--------|----------|
| **PDF** | pdfplumber | 布局感知提取，保留表格结构 |
| **Excel** | pandas | 语义行序列化（键值对格式） |
| **Word** | python-docx | 保留表格/文本顺序的结构化解析 |
| **Text/MD** | 基础解析 | 元数据保留的基本分块 |

#### 4.2.2 上下文缓冲 (Context Buffering)

为解决分块导致的语义断裂问题，RAG 模块实现了**前后文缓冲机制**：

```python
# 在 metadata 中预存前后文
for i, chunk in enumerate(chunks):
    # 注入前文 (Look-behind)
    if i > 0:
        chunk.metadata["prev_buffer"] = chunks[i-1].page_content[-250:]

    # 注入后文 (Look-ahead)
    if i < total_chunks - 1:
        chunk.metadata["next_buffer"] = chunks[i+1].page_content[:250:]
```

**解决的问题**：
- 问题在页末，答案在下页
- 句子被物理切割导致语义不完整
- 跨页表格数据断裂

#### 4.2.3 智能结果融合

检索后的智能合并策略：

```python
# 按 (file_hash, chunk_index) 分组
for doc in docs:
    f_hash = doc.metadata.get("file_hash")
    grouped_docs[f_hash].append(doc)

# 检查连续性并合并
if current_index == last_index + 1:
    current_block.append(content)  # 连续，直接合并
else:
    merged_texts.append(current_block)  # 不连续，结算上一块
```

**效果**：将 `[Chunk 5, Chunk 6, Chunk 10]` 合并为 `[5-6合并内容]` 和 `[10内容]`

#### 4.2.4 去重机制

基于文件哈希的去重：

```python
file_hash = hashlib.md5(file_content).hexdigest()
existing = vector_store.get(where={"file_hash": file_hash})
if existing:
    return  # 跳过重复文件
```

### 4.3 RAG 配置

#### 4.3.1 基础配置

```python
from aigility.rag import RAGConfig, EmbeddingConfig, VectorStoreConfig

config = RAGConfig(
    # Embedding 配置
    embedding=EmbeddingConfig(
        provider="zhipuai",        # huggingface, dashscope, zhipuai
        model_name="embedding-3",
        api_key=os.getenv("ZHIPUAI_API_KEY")
    ),

    # 向量存储配置
    vector_store=VectorStoreConfig(
        provider="qdrant",         # chroma, faiss, milvus, qdrant
        collection_name="knowledge_base",
        url="http://localhost:6333"
    ),

    # 文档处理配置
    ingestion=IngestionConfig(
        chunk_size=500,
        chunk_overlap=50
    ),

    search_top_k=5
)
```

#### 4.3.2 支持的向量存储

| Provider | 安装命令 | 特点 |
|----------|---------|------|
| Chroma | `aigility[vectorstore-chroma]` | 本地持久化，简单易用 |
| Qdrant | `aigility[vectorstore-qdrant]` | 高性能，支持过滤 |
| FAISS | `aigility[vectorstore-faiss]` | 内存索引，极速检索 |
| Milvus | `aigility[vectorstore-milvus]` | 分布式，云原生 |

#### 4.3.3 支持的 Embedding

| Provider | 模型示例 | 特点 |
|----------|---------|------|
| HuggingFace | sentence-transformers | 本地部署，免费 |
| DashScope | text-embedding-v2 | 阿里云服务 |
| ZhipuAI | embedding-3 | 智谱 AI 服务 |

### 4.4 云端 RAG 服务 (TimeM)

#### 4.4.1 TimeMRAGClient

太忆 RAG 云服务客户端，提供开箱即用的知识库检索能力：

```python
from aigility.rag import create_timem_rag_client

client = create_timem_rag_client(
    base_url="http://localhost:8000",
    api_key="sk-your-key"
)

# 同步搜索
result = client.search_sync(
    query="应届生毕业后档案有哪些去处？",
    kb_id="kb_e61b976ff864"
)

# 异步搜索
result = await client.search(
    query="查询内容",
    kb_id="kb_xxx"
)
```

#### 4.4.2 在 ChatFlow 中集成

TimeM RAG 通过工具调用集成到 ChatFlow：

```python
# ChatFlow 中的工具调用
if tool_name == "TimeMRAGTool":
    result = self.timem_rag_client.search_sync(
        query=query,
        kb_id=target_kb_id
    )
```

---

## 5. Memory 模块详解

### 5.1 模块架构

Memory 模块采用 Provider 架构，支持多种存储后端：

```
┌────────────────────────────────────────┐
│           Memory (高级接口)             │
│  - add()                              │
│  - search()                           │
├────────────────────────────────────────┤
│      MemoryProviderFactory             │
│  - create_provider()                  │
├────────────────────────────────────────┤
│     BaseMemoryProvider (抽象)          │
│           ↓                            │
│  ┌────────────┬────────────┐          │
│  │   Timem    │   Custom   │          │
│  │  Provider  │  Provider  │          │
│  └────────────┴────────────┘          │
└────────────────────────────────────────┘
```

### 5.2 设计原理

#### 5.2.1 多维度索引

Memory 支持按以下维度组织记忆：

```python
await memory.add(
    messages=[{"role": "user", "content": "..."}],
    user_id="user123",           # 用户维度
    character_id="assistant",     # 角色/助手维度
    session_id="session_xxx"      # 会话维度
)
```

#### 5.2.2 语义检索

基于向量相似度的智能记忆检索：

```python
results = await memory.search(
    query="用户之前问过什么？",
    user_id="user123",
    limit=10,
    character_id="assistant"
)
```

### 5.3 Memory 配置

```python
from aigility.memory import Memory, MemoryConfig, MemoryProviderConfig

# 基础配置
config = MemoryConfig(
    provider=MemoryProviderConfig(
        provider="timem",
        api_key=os.getenv("TIMEM_API_KEY"),
        base_url=os.getenv("TIMEM_BASE_URL"),
        enabled=True
    )
)

memory = Memory(config=config)
```

### 5.4 Provider 扩展

实现自定义 Provider：

```python
from aigility.memory.providers.base import BaseMemoryProvider

class CustomMemoryProvider(BaseMemoryProvider):
    async def add_memory(self, messages, user_id, character_id, session_id):
        # 实现记忆添加逻辑
        pass

    async def search_memories(self, query_text, user_id, character_id, limit):
        # 实现记忆检索逻辑
        pass
```

---

## 6. Chat 与 ChatFlow 服务

### 6.1 Chat 服务

#### 6.1.1 服务架构

```
ChatService
    ↓
ChatFlow (LangGraph 状态机)
    ↓
Node 1: Agent Decision (工具决策)
    ↓
Node 2: Tool Executor (工具执行)
    ↓
Node 3: Prepare for Generation (准备生成)
    ↓
Node 4: Stream Response (流式响应)
```

#### 6.1.2 ChatRequest/Response Schema

```python
class ChatRequest(BaseModel):
    user_input: str              # 用户输入
    session_id: Optional[str]    # 会话 ID
    kb_id: Optional[str]         # 知识库 ID

class ChatResponse(BaseModel):
    response: str                # AI 回复
    session_id: str              # 会话 ID
    session_title: str           # 会话标题
    reply_suggestions: List[str] # 回复建议
    thought_process: Optional[str] # 思考过程
    tool_results: List[Dict]     # 工具执行结果
```

### 6.2 ChatFlow 详解

#### 6.2.1 四节点架构

| 节点 | 功能 | 输出 |
|------|------|------|
| **Agent Decision** | 使用 CoT Prompt 决定是否调用工具 | thought, tool_calls |
| **Tool Executor** | 执行 RAG 和 Web Search 工具 | tool_results |
| **Prepare for Generation** | 准备最终回复的 Prompt 和 Chain | chain, prompt_input |
| **Stream Response** | 生成并流式输出最终回复 | messages |

#### 6.2.2 条件路由

```python
workflow.add_conditional_edges(
    "agent_decision",
    self._should_continue,
    {
        "continue": "tool_executor",   # 有工具调用
        "end": "prepare_for_generation",  # 无工具调用
    }
)
```

#### 6.2.3 工具集成

支持的工具：

| 工具名称 | 功能 | 实现 |
|---------|------|------|
| TimeMRAGTool | 太忆 RAG 检索 | [client.py](aigility/rag/client.py:267) |
| WebSearchTool | 互联网搜索 | (占位符实现) |

工具调用格式：

```json
{
  "thought": "需要查询知识库",
  "tool_calls": [
    {
      "tool_name": "TimeMRAGTool",
      "query": "搜索查询语句"
    }
  ]
}
```

#### 6.2.4 Prompt 配置

Prompt 通过 YAML 配置文件管理：

```yaml
# chat_flow_config.yaml
agent_decision_prompt: |
  你是一个智能决策助手，需要分析用户请求并决定是否调用工具。

  **对话历史:**
  {history}

  **用户请求:**
  {input}

  **可用工具:**
  {tool_descriptions}

final_response_prompt: |
  你已经完成了思考和工具调用。

  **思考过程:**
  {thought}

  **工具调用结果:**
  {tool_results}
```

### 6.3 性能监控

ChatFlow 内置性能监控，输出每个节点的耗时：

```
⏱️ [ADK性能] Agent Decision 节点耗时: 1.23s
⏱️ [ADK性能] Tool Executor 节点总耗时: 2.45s
⏱️ [ADK性能] Prepare for Generation 节点耗时: 0.12s
⏱️ [ADK性能] LLM invoke 耗时: 3.56s
⏱️ [ADK性能] ChatFlow.invoke 总耗时: 7.89s
```

---

## 7. 配置管理

### 7.1 ADKConfig

全局配置类，支持环境变量和代码配置：

```python
@dataclass
class ADKConfig:
    # LLM 配置
    llm_provider: str = "openai"
    llm_model: str = "gpt-4"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_temperature: float = 0.7

    # Memory 配置
    memory_enabled: bool = True
    memory_api_key: Optional[str] = None
    memory_base_url: Optional[str] = None

    # 知识库配置
    knowledge_enabled: bool = True
    knowledge_store_type: str = "vector"

    # 太忆 RAG 配置
    timem_api_key: Optional[str] = None
    timem_base_url: Optional[str] = None
    timem_enabled: bool = False

    # 其他
    debug: bool = False
    log_level: str = "INFO"
```

### 7.2 环境变量优先级

配置读取优先级：

1. 代码中显式传入的参数
2. 环境变量
3. 默认值

### 7.3 配置示例

```python
# 完整配置示例
config = ADKConfig(
    # LLM 配置
    llm_provider="deepseek",
    llm_model="deepseek-chat",
    llm_api_key=os.getenv("DEEPSEEK_API_KEY"),
    llm_base_url=os.getenv("DEEPSEEK_BASE_URL"),

    # 太忆 RAG 配置
    timem_enabled=True,
    timem_api_key=os.getenv("TIMEM_API_KEY"),
    timem_base_url=os.getenv("TIMEM_BASE_URL"),

    # 调试模式
    debug=True
)
```

---

## 8. 支持的服务

### 8.1 LLM 服务

| Provider | 模型示例 | 配置前缀 |
|---------|---------|---------|
| OpenAI | gpt-4, gpt-3.5-turbo | `OPENAI_` |
| DeepSeek | deepseek-chat | `DEEPSEEK_` |
| 智谱 AI | glm-4 | `ZHIPUAI_` |
| Anthropic | claude-3-opus | `ANTHROPIC_` |

### 8.2 Embedding 服务

| Provider | 模型示例 | 特点 |
|---------|---------|------|
| HuggingFace | sentence-transformers | 本地部署 |
| DashScope | text-embedding-v2 | 阿里云 |
| ZhipuAI | embedding-3 | 智谱 AI |
| OpenAI | text-embedding-ada-002 | OpenAI |

### 8.3 向量存储服务

| Provider | 类型 | 部署方式 |
|---------|------|---------|
| Chroma | 本地/云 | Docker / 本地 |
| Qdrant | 本地/云 | Docker / 云服务 |
| FAISS | 内存 | 本地 |
| Milvus | 分布式 | Kubernetes |

### 8.4 RAG 云服务

| Provider | 功能 |
|---------|------|
| 太忆 (TimeM) | 文档上传、智能检索、知识库管理 |

---

## 9. 设计模式与最佳实践

### 9.1 设计模式

#### 9.1.1 工厂模式 (Factory)

用于创建可插拔的组件：

```python
# Embedding 工厂
class EmbeddingFactory:
    @staticmethod
    def get_embedding_model(config: EmbeddingConfig):
        if config.provider == "huggingface":
            return HuggingFaceEmbeddings(...)
        elif config.provider == "dashscope":
            return DashScopeEmbeddings(...)
```

#### 9.1.2 策略模式 (Strategy)

不同文档类型的解析策略：

```python
# IngestionManager
parsers = {
    ".pdf": PDFParser(),
    ".docx": DocxParser(),
    ".xlsx": ExcelParser(),
}
```

#### 9.1.3 服务层模式 (Service Layer)

清晰的业务逻辑分离：

```python
# ChatService 作为服务层
class ChatService:
    def process_chat(self, request: ChatRequest) -> ChatResponse:
        # 业务逻辑
        flow_result = self.chat_flow.invoke(...)
        return ChatResponse(...)
```

#### 9.1.4 状态机模式 (State Machine)

LangGraph 实现的对话流：

```python
workflow = StateGraph(ChatFlowState)
workflow.add_node("agent_decision", self._agent_decision)
workflow.add_conditional_edges("agent_decision", self._should_continue)
```

### 9.2 最佳实践

#### 9.2.1 错误处理

```python
try:
    result = await self._provider.add_memory(...)
except Exception as e:
    logger.error(f"Failed to add memory: {e}")
    return {"success": False, "error": str(e)}
```

#### 9.2.2 连接管理

```python
async def close(self):
    """关闭客户端连接"""
    if self._provider:
        await self._provider.close()

# 使用上下文管理器
async with Memory(config=config) as memory:
    await memory.add(...)
```

#### 9.2.3 性能优化

- 使用连接池（HTTPClient 内置）
- 批量处理文档
- 合理设置 chunk_size 和 overlap
- 启用向量索引

#### 9.2.4 调试技巧

```python
# 启用调试模式
config = ADKConfig(debug=True)

# 查看性能日志
chat_service.process_chat(request)
# 输出: ⏱️ [ADK性能] Agent Decision 节点耗时: 1.23s
```

---

## 附录

### A. 依赖管理

| 安装方式 | 大小 | 说明 |
|---------|-----|------|
| `pip install aigility` | ~50MB | 核心依赖 |
| `aigility[rag-local]` | ~500MB-2GB | 含 HuggingFace 模型 |
| `aigility[timem-rag]` | ~100MB | 含文档处理依赖 |

### B. 常见问题

**Q: 如何选择向量存储？**
- 本地开发：Chroma
- 生产环境：Qdrant
- 大规模检索：Milvus

**Q: chunk_size 如何设置？**
- 短文档：300-500
- 长文档：500-1000
- overlap 建议：10-20%

**Q: 如何调试 RAG 检索效果？**
```python
# 启用调试并查看检索结果
config.debug = True
result = rag_service.search("查询词", expand_context=True)
```

### C. 相关链接

- [GitHub 仓库](https://github.com/AIGility-Cloud-Innovation/aigility)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LangChain 文档](https://python.langchain.com/)

---

*文档版本: 0.0.2 | 更新日期: 2025-02-24*
