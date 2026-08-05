# Aigility SDK (ADK) 使用文档

> **版本：** 0.1.3 | **维护方：** AIGility Cloud Innovation
>
> 本文档面向 SDK 使用者，详细说明 `aigility` 包的架构设计、各模块功能、使用方式及当前实现状态。

---

## 目录

1. [SDK 概述](#1-sdk-概述)
2. [快速开始](#2-快速开始)
3. [包结构与实现状态](#3-包结构与实现状态)
4. [核心配置：ADKConfig](#4-核心配置adkconfig)
5. [ADKClient：统一客户端入口](#5-adkclient统一客户端入口)
6. [Chat 模块](#6-chat-模块)
7. [ChatFlow 模块](#7-chatflow-模块)
8. [RAG 模块](#8-rag-模块)
9. [Memory 模块](#9-memory-模块)
10. [Workflow 模块](#10-workflow-模块)
11. [ADP 模块](#11-adp-模块)
12. [HTTP 基础设施](#12-http-基础设施)
13. [ModelFactory：LLM 实例化](#13-modelfactoryllm-实例化)
14. [工具系统与扩展点](#14-工具系统与扩展点)
15. [已知限制与路线图](#15-已知限制与路线图)

---

## 1. SDK 概述

`aigility`（AIGility ADK - Agent Development Kit）是基于 **LangGraph / LangChain** 的智能体开发框架，提供从对话、RAG 检索到工作流编排的全链路能力。

### 设计理念

- **即插即用**：`ChatService` / `ChatFlow` 开箱可用，内置 CoT 决策 + RAG 工具调用
- **配置驱动**：通过 `ADKConfig` 统一管理 LLM、记忆、RAG 等服务的连接
- **可扩展**：支持自定义 prompt、工具、工作流节点

### 核心依赖

| 依赖 | 用途 |
|------|------|
| `langgraph` | 状态机编排（ChatFlow 内部） |
| `langchain-core` | Prompt、OutputParser、消息模型 |
| `langchain-openai` | OpenAI 兼容的 LLM 客户端 |
| `pydantic` | 数据校验和 Schema 定义 |
| `httpx` | 异步 HTTP 客户端 |

---

## 2. 快速开始

### 2.1 最简示例：3 行代码完成一次 RAG 对话

```python
from aigility.chat.service import ChatService
from aigility.chat.schema import ChatRequest
from aigility.core.config import ADKConfig

# 1. 配置
config = ADKConfig(
    llm_provider="openai",
    llm_model="gpt-4",
    llm_api_key="sk-xxx",
    llm_base_url="https://api.openai.com/v1",
    timem_enabled=True,                   # 启用 RAG
    timem_api_key="your-timem-api-key",
    timem_base_url="https://api.timem.cloud",
)

# 2. 创建服务
service = ChatService(adk_config=config)

# 3. 对话
request = ChatRequest(
    user_input="你们的最小起订量是多少？",
    kb_id="kb_xxx",           # 知识库 ID
    rag_used="auto",          # auto / on / off
)
response = service.process_chat(request)

print(response.response)          # AI 回复
print(response.thought_process)   # 思考过程
print(response.tool_results)      # RAG 检索结果
```

### 2.2 流式对话

```python
import asyncio

async def main():
    async for event in service.process_chat_stream(request):
        # event 为 LangGraph 的 stream 事件
        node_name = list(event.keys())[0]
        print(f"[{node_name}]", event)

asyncio.run(main())
```

### 2.3 使用 Builder 模式创建客户端

```python
from aigility import ADKClientBuilder

client = (
    ADKClientBuilder()
    .with_llm(provider="deepseek", model="deepseek-chat", api_key="sk-xxx",
              base_url="https://api.deepseek.com")
    .with_memory(api_key="timem-xxx")
    .with_debug(enabled=True)
    .build()
)

# 通过 ChatAgent 进行对话（推荐）
agent = client.create_chat_agent("my_agent")
response = agent.chat("你好", rag_used="off")
print(response)  # AI 回复文本

# 也可以通过 ChatFlow 进行对话
chatflow = client.create_chatflow("my_flow")
result = chatflow.invoke(user_input="你好", rag_used="off")
print(result["response"])

# 访问 Memory（懒加载）
memory = client.memory
```

---

## 3. 包结构与实现状态

```
aigility/
├── __init__.py
├── client.py                # ADKClient 主客户端
│
├── core/
│   ├── config.py            # ✅ ADKConfig, AgentConfig, ToolConfig
│   ├── model_factory.py     # ✅ ModelFactory - LLM 实例化工厂
│   ├── base.py              # ✅ BaseAgent, BaseTool, BaseMemory 抽象类
│   └── types.py             # ✅ State, Message, AgentResponse 类型定义
│
├── chat/
│   ├── service.py           # ✅ ChatService - 对话服务主类
│   ├── schema.py            # ✅ ChatRequest, ChatResponse
│   └── agent.py             # ✅ ChatAgent - 委托 ChatFlow 实现对话
│
├── chatflow/
│   ├── flow.py              # ✅ ChatFlow - LangGraph 对话流引擎（核心可用）
│   └── schema.py            # ✅ ChatFlowState, ToolCall, ToolResult
│
├── rag/
│   ├── service.py           # ✅ RAGService - 本地 RAG（文档入库 + 检索）
│   ├── client.py            # ✅ TimeMRAGClient - TimeM 云服务客户端
│   ├── config.py            # ✅ RAGConfig
│   ├── ingestion.py         # ✅ 文档入库管理
│   ├── hybrid_search.py     # ✅ 混合搜索（BM25 + 向量）
│   ├── workflow.py          # ✅ RAG 工作流
│   ├── markdown_splitter.py # ✅ Markdown 文档切分
│   ├── embeddings/          # ✅ Embedding 模型工厂
│   │   ├── factory.py
│   │   ├── huggingface.py
│   │   ├── dashscope.py
│   │   └── zai.py
│   └── vector_stores/       # ✅ 向量数据库工厂
│       ├── factory.py
│       ├── chroma.py
│       ├── faiss.py
│       ├── qdrant.py
│       └── milvus.py
│
├── memory/
│   ├── memory.py            # ✅ Memory 高级接口
│   ├── config.py            # ✅ MemoryConfig, MemoryProviderConfig
│   └── providers/
│       ├── factory.py       # ✅ Provider 工厂
│       ├── base.py          # ✅ 基类
│       └── timem.py         # ✅ TimeM Provider
│
├── workflow/
│   ├── builder.py           # ❌ WorkflowGraphBuilder - build() 未实现
│   └── engine.py            # ❌ WorkflowEngine - invoke()/stream() 未实现
│
├── adp/
│   └── client.py            # ✅ ADPClient - 远程 Agent 调用客户端
│
├── http/
│   ├── client.py            # ✅ HTTPClient - 统一 HTTP 接口
│   ├── retry.py             # ✅ 重试策略
│   ├── circuit_breaker.py   # ✅ 熔断器
│   └── pool.py              # ✅ 连接池
│
├── model/
│   └── llm.py               # ✅ create_llm() 便捷入口（转发到 ModelFactory）
│
└── utils/
    ├── logger.py            # ✅ 日志工具
    └── workflow.py          # ✅ 工作流工具
```

**图例：** ✅ 可用 | ⚠️ 部分可用 / 框架已有但核心方法未实现 | ❌ 未实现

---

## 4. 核心配置：ADKConfig

`ADKConfig` 是贯穿整个 SDK 的配置中枢，定义在 `aigility.core.config` 中。

### 4.1 完整字段说明

```python
from aigility.core.config import ADKConfig

config = ADKConfig(
    # ===== LLM 配置 =====
    llm_provider="openai",          # "openai"（默认，兼容所有 OpenAI 兼容提供商）、"deepseek"
    llm_model="gpt-4",              # 模型名称
    llm_api_key="sk-xxx",           # API Key
    llm_base_url=None,              # API Base URL（留空则用 provider 默认值）
    llm_temperature=0.7,            # 温度
    llm_max_tokens=2000,            # 最大输出 token

    # ===== Memory 配置 =====
    memory_enabled=True,            # 是否启用记忆模块
    memory_api_key=None,            # 记忆服务 API Key
    memory_base_url=None,           # 记忆服务 Base URL

    # ===== Knowledge 配置 =====
    knowledge_enabled=True,         # 是否启用知识库
    knowledge_store_type="vector",  # 存储类型: "vector", "graph", "hybrid"

    # ===== TimeM RAG 云服务配置 =====
    timem_enabled=False,            # 是否启用 TimeM RAG
    timem_api_key=None,             # TimeM API Key
    timem_base_url=None,            # TimeM Base URL

    # ===== 工作流配置 =====
    workflow_timeout=300.0,         # 工作流超时（秒）
    workflow_max_steps=50,          # 最大执行步数

    # ===== HTTP 配置 =====
    http_timeout=60.0,              # HTTP 请求超时（秒）
    http_max_retries=3,             # 最大重试次数
    http_verify_ssl=False,          # 是否验证 SSL 证书

    # ===== 调试 =====
    debug=False,                    # 调试模式
    log_level="INFO",               # 日志级别
)
```

### 4.2 LLM 提供商兼容性

SDK 的 `ModelFactory` 内部使用 LangChain 的 `ChatOpenAI`，因此**所有兼容 OpenAI API 格式的提供商均可直接使用**。

| `llm_provider` | 实际创建的类 | 说明 |
|----------------|-------------|------|
| `"openai"` | `ChatOpenAI` | 默认分支，兼容所有 OpenAI API 格式的提供商 |
| `"deepseek"` | `ChatDeepSeek` 或 `ChatOpenAI` | 优先尝试 langchain-deepseek，失败则回退 |

### 4.3 各提供商配置示例

#### DeepSeek

```python
config = ADKConfig(
    llm_provider="deepseek",
    llm_model="deepseek-chat",               # 或 deepseek-coder
    llm_api_key="sk-xxx",
    llm_base_url="https://api.deepseek.com",
)
```

#### 智谱 AI（GLM）

```python
config = ADKConfig(
    llm_provider="openai",                    # 智谱兼容 OpenAI 接口
    llm_model="glm-4-flash",                  # glm-4、glm-4-flash 等
    llm_api_key="xxx.xxx",
    llm_base_url="https://open.bigmodel.cn/api/paas/v4",
)
```

#### 阿里云百炼（通义千问）

```python
config = ADKConfig(
    llm_provider="openai",
    llm_model="qwen-plus",                    # qwen-turbo、qwen-max 等
    llm_api_key="sk-xxx",
    llm_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
```

#### Moonshot（Kimi）

```python
config = ADKConfig(
    llm_provider="openai",
    llm_model="moonshot-v1-8k",               # moonshot-v1-32k 等
    llm_api_key="sk-xxx",
    llm_base_url="https://api.moonshot.cn/v1",
)
```

#### 豆包（火山引擎）

```python
config = ADKConfig(
    llm_provider="openai",
    llm_model="doubao-pro-4k",                # 模型端点 ID
    llm_api_key="xxx",
    llm_base_url="https://ark.cn-beijing.volces.com/api/v3",
)
```

#### OpenAI（官方）

```python
config = ADKConfig(
    llm_provider="openai",
    llm_model="gpt-4o",                       # gpt-4、gpt-3.5-turbo 等
    llm_api_key="sk-xxx",
    # llm_base_url 留空，使用 OpenAI 官方地址
)
```

#### 通过 Builder 模式配置

```python
client = (
    ADKClientBuilder()
    .with_llm(
        provider="deepseek",                  # 或 "openai"
        model="deepseek-chat",
        api_key="sk-xxx",
        base_url="https://api.deepseek.com",
    )
    .build()
)
```

#### 通过 create_llm() 快捷函数

```python
from aigility.model import create_llm

llm = create_llm(
    provider="deepseek",
    model="deepseek-chat",
    api_key="sk-xxx",
    base_url="https://api.deepseek.com",
    temperature=0.7,
    max_tokens=2000,
)
```

> **规则总结：**
> - DeepSeek → `llm_provider="deepseek"`
> - 其他所有 OpenAI 兼容提供商 → `llm_provider="openai"` + 对应的 `llm_base_url`
> - SDK 会自动将 `llm_temperature` 和 `llm_max_tokens` 传递给模型

### 4.4 配置与环境变量

SDK 的 Memory Provider 支持从环境变量自动读取：

| 环境变量 | 对应配置 |
|----------|---------|
| `TIMEM_API_KEY` | `timem_api_key` / `memory_provider.api_key` |
| `TIMEM_BASE_URL` | `timem_base_url` / `memory_provider.base_url` |
| `DEEPSEEK_API_KEY` | `llm_api_key`（需手动传入） |

---

## 5. ADKClient：统一客户端入口

`ADKClient` 是 SDK 的顶层门面，提供统一的模块访问入口。

### 5.1 创建方式

```python
from aigility import ADKClient, ADKClientBuilder, create_client

# 方式1: 直接传入 config
client = ADKClient(config=ADKConfig(...))

# 方式2: Builder 模式（推荐）
client = (
    ADKClientBuilder()
    .with_llm(provider="openai", model="gpt-4", api_key="sk-xxx")
    .with_memory(api_key="timem-xxx")
    .with_http(timeout=30.0, max_retries=5)
    .with_debug(enabled=True)
    .build()
)

# 方式3: 快捷函数
client = create_client(
    llm_provider="openai",
    llm_api_key="sk-xxx",
    llm_model="gpt-4",
)
```

### 5.2 可用方法

```python
# 创建对话智能体（推荐入口）
agent = client.create_chat_agent("my_agent")

# 同步对话（最简用法）
response = agent.chat("你好")
print(response)  # AI 回复文本

# 对话 + RAG
response = agent.chat("你们的最小起订量是多少？", rag_used="auto")

# 通过 ChatFlow 对话（更底层的控制）
chatflow = client.create_chatflow("my_chat")
result = chatflow.invoke(user_input="你好", rag_used="off")
print(result["response"])           # AI 回复
print(result["thought_process"])    # 思考过程
print(result["tool_results"])       # RAG 检索结果

# 创建 ADP 远程客户端
adp = client.create_adp_client(base_url="http://...", api_key="xxx")

# 访问 Memory（懒加载）
mem = client.memory

# 关闭客户端
await client.close()
```

---

## 6. Chat 模块

### 6.1 ChatService

`ChatService` 是 SDK 的对话服务主类，内部封装了 `ChatFlow`（LangGraph 状态机）。

```python
from aigility.chat.service import ChatService
from aigility.chat.schema import ChatRequest
from aigility.core.config import ADKConfig

config = ADKConfig(
    llm_provider="deepseek",
    llm_model="deepseek-chat",
    llm_api_key="sk-xxx",
    llm_base_url="https://api.deepseek.com",
    timem_enabled=True,
    timem_api_key="your-timem-api-key",
    timem_base_url="https://api.timem.cloud",
)
service = ChatService(adk_config=config)

# 同步对话
request = ChatRequest(
    user_input="你们支持哪些支付方式？",
    kb_id="kb_xxx",
    rag_used="auto",
)
response = service.process_chat(request)
print(response.response)
```

**构造参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `adk_config` | `ADKConfig` | 否 | 全局配置，默认使用 `ADKConfig()` |
| `flow_config` | `Dict[str, Any]` | 否 | 对话流配置，不传则使用内置默认配置 |

**可用方法：**

| 方法 | 类型 | 返回值 | 说明 |
|------|------|--------|------|
| `process_chat(request)` | 同步 | `ChatResponse` | 完整对话处理 |
| `process_chat_stream(request)` | 异步生成器 | `Dict` 事件 | 流式对话 |
| `generate_session_title(user_input, ai_response)` | 同步 | `str` | 生成会话标题 |
| `generate_reply_suggestions(ai_response)` | 同步 | `List[str]` | 生成回复建议 |

### 6.2 ChatAgent

`ChatAgent` 是 SDK 的对话智能体入口，内部委托 `ChatFlow` 执行对话，对外提供简化的 Agent 接口。

```python
from aigility.chat.agent import ChatAgent
from aigility.core.config import ADKConfig

agent = ChatAgent(
    name="my_agent",
    adk_config=ADKConfig(
        llm_provider="openai",
        llm_model="gpt-4",
        llm_api_key="sk-xxx",
        timem_enabled=True,
        timem_api_key="timem-xxx",
    ),
)

# 方式1：同步便捷方法（推荐）
response = agent.chat("你好")
print(response)  # AI 回复文本

# 方式2：通过 ADKClient 创建
from aigility import ADKClientBuilder

client = (
    ADKClientBuilder()
    .with_llm(provider="deepseek", model="deepseek-chat", api_key="sk-xxx")
    .build()
)
agent = client.create_chat_agent("my_agent")
response = agent.chat("你好", rag_used="auto")
```

**构造参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | `str` | 是 | 智能体名称 |
| `adk_config` | `ADKConfig` | 否 | 全局配置，默认使用 `ADKConfig()` |
| `config` | `AgentConfig` | 否 | 智能体配置（prompt 模板等） |

**可用方法：**

| 方法 | 类型 | 返回值 | 说明 |
|------|------|--------|------|
| `chat(user_input, rag_used)` | 同步 | `str` | 便捷对话，返回 AI 回复文本 |
| `invoke(state)` | 异步 | `AgentResponse` | 实现 BaseAgent 接口，接受 State 对象 |

### 6.3 数据模型

```python
from aigility.chat.schema import ChatRequest, ChatResponse

# 请求
class ChatRequest(BaseModel):
    user_input: str                          # 用户输入（必填）
    session_id: Optional[str] = None         # 会话 ID
    kb_id: Optional[str] = None              # 知识库 ID（RAG 必需）
    rag_used: Literal["auto", "on", "off"]   # RAG 模式，默认 "auto"

# 响应
class ChatResponse(BaseModel):
    response: str                            # AI 回复
    session_id: str                          # 会话 ID
    session_title: Optional[str] = None      # 会话标题
    reply_suggestions: List[str]             # 回复建议列表
    thought_process: Optional[str] = None    # CoT 思考过程
    tool_results: Optional[List[dict]] = None # 工具调用结果
```

### 6.4 RAG 模式详解

`rag_used` 参数控制 RAG 行为，是 ChatService 最核心的配置之一：

| 模式 | 行为 | 适用场景 |
|------|------|---------|
| `"auto"` | LLM 自主决定是否调用 RAG 工具 | 通用场景，LLM 会根据问题判断是否需要检索 |
| `"on"` | 强制调用 RAG，跳过决策节点 | 确定需要检索的场景 |
| `"off"` | 强制关闭 RAG，纯对话模式 | 闲聊、创意写作等不需要知识库的场景 |

---

## 7. ChatFlow 模块

`ChatFlow` 是 SDK 的核心引擎，实现了一个完整的 **LangGraph 状态机**，包含 CoT 决策、工具执行和回复生成。

### 7.1 状态图结构

```
                    ┌──────────────────┐
                    │  agent_decision   │  ← LLM 决策：是否需要工具？
                    └────────┬─────────┘
                             │
                    ┌────────┴─────────┐
                    │                  │
              有工具调用            无工具调用
                    │                  │
                    ▼                  │
           ┌────────────────┐         │
           │  tool_executor  │         │
           │  (RAG / Search) │         │
           └────────┬───────┘         │
                    │                  │
                    ▼                  ▼
           ┌─────────────────────────────┐
           │  prepare_for_generation      │  ← 构建 Prompt + Chain
           └─────────────┬───────────────┘
                         │
                         ▼
           ┌─────────────────────────────┐
           │  stream_response             │  ← LLM 生成最终回复
           └─────────────┬───────────────┘
                         │
                         ▼
                        END
```

### 7.2 节点详解

#### `agent_decision` — 决策节点

- 使用 LLM + CoT Prompt 分析用户输入
- 输出 JSON：`{"thought": "...", "tool_calls": [{"tool_name": "TimeMRAGTool", "query": "..."}]}`
- 支持从用户输入中提取特殊检索标记：
  - `【用于检索的关键词】xxx` → 优先使用 `xxx` 作为 RAG query
  - `【RAG_QUERY】xxx【/RAG_QUERY】` → 同上
- 如果未检测到特殊标记，使用 LLM 决策的 query

#### `tool_executor` — 工具执行节点

- 遍历 `tool_calls`，根据 `tool_name` 分发执行
- `TimeMRAGTool` → 调用 `timem_rag_client.search_sync(query, kb_id)`
- `WebSearchTool` → 占位实现（返回模拟结果）
- 执行结果通过 `ToolMessage` 追加到消息历史

#### `prepare_for_generation` — 准备节点

- 从消息历史中提取用户输入、历史对话、工具结果
- 构建最终回复的 Prompt Template
- 创建 `prompt | llm | StrOutputParser` Chain

#### `stream_response` — 生成节点

- 同步调用：直接 `chain.invoke(prompt_input)`
- 流式调用：通过 `chain.astream(prompt_input)` 逐 chunk 输出

### 7.3 调用方式

```python
from aigility.chatflow.flow import ChatFlow

flow = ChatFlow(
    adk_config=config,
    flow_config={                          # 可选，覆盖默认 prompt
        "agent_decision_prompt": "...",
        "final_response_prompt": "...",
    },
)

# 同步调用
result = flow.invoke(
    user_input="你们的产品有哪些认证？",
    history=[],                           # 可选：历史消息列表
    config=None,                          # 可选：RunnableConfig（如 kb_id）
    rag_used="auto",
)
# result = {
#     "response": "...",
#     "thought_process": "...",
#     "tool_results": [ToolResult(...)],
#     "full_history": [...],
# }

# 异步流式调用
async for event in flow.astream(
    user_input="你们的产品有哪些认证？",
    rag_used="auto",
):
    # event: {"stream_response": {"messages": [AIMessageChunk(...)]}}
    chunk = list(event.values())[0]["messages"][0].content
    print(chunk, end="", flush=True)
```

### 7.4 内置 Prompt 配置

ChatFlow 的默认 prompt 从 `chatflow/prompts/chat.yaml` 加载，包含两个核心 prompt：

1. **`agent_decision_prompt`** — 指导 LLM 判断是否需要调用 RAG 工具
2. **`final_response_prompt`** — 指导 LLM 基于工具结果生成最终回复

可通过 `flow_config` 参数覆盖：

```python
flow = ChatFlow(adk_config=config, flow_config={
    "agent_decision_prompt": "你是一个智能助手，请根据用户问题决定是否需要搜索知识库...",
    "final_response_prompt": "请根据以下信息回答用户问题...\n{tool_results}\n用户问：{input}",
})
```

### 7.5 kb_id 传递机制

知识库 ID 通过 LangGraph 的 `RunnableConfig` 传递：

```python
from langchain_core.runnables import RunnableConfig

config = RunnableConfig(configurable={"timem_kb_id": "kb_xxx"})
result = flow.invoke(user_input="...", config=config, rag_used="on")
```

---

## 8. RAG 模块

RAG 模块提供两种使用方式：**TimeM 云服务** 和 **本地 RAGService**。

### 8.1 TimeM 云服务客户端

`TimeMRAGClient` 封装了对太忆 RAG API 的调用，是 `ChatFlow` 内部使用的 RAG 引擎。

```python
from aigility.rag.client import TimeMRAGClient

client = TimeMRAGClient(
    base_url="https://api.timem.cloud",
    api_key="your-api-key",
    timeout=30.0,
)

# 搜索知识库
result = await client.search(query="MOQ是多少", kb_id="kb_xxx")
# result: str（格式化的搜索结果）

# 同步搜索（ChatFlow 内部使用）
result = client.search_sync(query="MOQ是多少", kb_id="kb_xxx")
```

也可通过 `create_timem_rag_client` 快捷函数创建：

```python
from aigility.rag import create_timem_rag_client

client = create_timem_rag_client(
    base_url="https://api.timem.cloud",
    api_key="your-api-key",
)
```

### 8.2 本地 RAGService

`RAGService` 提供完整的本地 RAG 能力，包括文档入库、向量检索和混合搜索。

```python
from aigility.rag.service import RAGService
from aigility.rag.config import RAGConfig

config = RAGConfig(...)
service = RAGService(config=config)
```

**支持的向量数据库：**

| 数据库 | 文件 | 说明 |
|--------|------|------|
| Chroma | `vector_stores/chroma.py` | 轻量级，适合开发 |
| FAISS | `vector_stores/faiss.py` | Facebook 向量检索 |
| Qdrant | `vector_stores/qdrant.py` | 生产级向量数据库 |
| Milvus | `vector_stores/milvus.py` | 分布式向量数据库 |

**支持的 Embedding 模型：**

| 模型 | 文件 | 说明 |
|------|------|------|
| HuggingFace | `embeddings/huggingface.py` | 本地模型 |
| DashScope | `embeddings/dashscope.py` | 阿里云 |
| ZAI | `embeddings/zai.py` | 智谱 |

**其他能力：**
- `IngestionManager` — 文档入库管理
- `hybrid_search.py` — BM25 + 向量混合搜索
- `markdown_splitter.py` — Markdown 文档切分

---

## 9. Memory 模块

### 9.1 Memory 类

`Memory` 提供简化的记忆管理接口，内部使用 Provider 架构。

```python
from aigility.memory import Memory, MemoryConfig, MemoryProviderConfig

# 方式1: 默认配置（从环境变量 TIMEM_API_KEY 读取）
memory = Memory()

# 方式2: 显式配置
config = MemoryConfig(
    provider=MemoryProviderConfig(
        provider="timem",
        api_key="sk-xxx",
        base_url="https://api.timem.cloud",
    )
)
memory = Memory(config=config)
```

### 9.2 Provider 架构

| Provider | 文件 | 说明 |
|----------|------|------|
| `timem` | `providers/timem.py` | 太忆 TimeM 云服务 |
| `custom` | - | 自定义 Provider（需实现 `BaseMemoryProvider`） |

### 9.3 BaseMemory 抽象接口

`aigility.core.base.BaseMemory` 定义了记忆的标准接口：

```python
class BaseMemory(ABC):
    async def add(self, messages: List[Message], **kwargs) -> Dict[str, Any]:
        """添加记忆"""
        ...

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """搜索记忆"""
        ...

    async def get(self, memory_id: str) -> Dict[str, Any]:
        """获取单条记忆"""
        ...
```

---

## 10. Workflow 模块

### 10.1 当前状态

> **⚠️ 未实现：** `WorkflowEngine` 和 `WorkflowGraphBuilder` 的核心方法均抛出 `NotImplementedError`。

### 10.2 WorkflowEngine（框架）

```python
from aigility.workflow.engine import WorkflowEngine

# 已定义但 invoke()/stream() 未实现
engine = WorkflowEngine(name="my_workflow", nodes={...})
# await engine.invoke(state)   → NotImplementedError
# await engine.stream(state)   → NotImplementedError
```

### 10.3 WorkflowGraphBuilder（框架）

```python
from aigility.workflow.builder import WorkflowGraphBuilder

builder = WorkflowGraphBuilder()
builder.add_node("step1", my_func)
builder.add_edge("step1", "step2")
builder.set_start("step1")
# builder.build()  → NotImplementedError
```

### 10.4 设计意图

Workflow 模块的定位是提供一个比 ChatFlow 更通用的工作流编排能力，但目前仍处于框架阶段。**实际使用中，建议直接使用 LangGraph 构建自定义工作流**（如 ChatFlow 内部所做的那样）。

---

## 11. ADP 模块

`ADPClient` 用于调用远程 Agent Deployment Platform (ADP) 服务。

```python
from aigility.adp.client import ADPClient

client = ADPClient(
    base_url="http://localhost:8000/api/v1",
    api_key="your-api-key",
)

# 同步对话
response = await client.chat(
    user_input="你好",
    agent="careerask",
    session_id="session-001",
)

# 流式对话
async for chunk in client.chat_stream(
    user_input="你好",
    agent="careerask",
):
    print(chunk)
```

**接口说明：**

| 方法 | 说明 |
|------|------|
| `chat(user_input, agent, session_id)` | 调用远程 Agent 进行对话 |
| `chat_stream(user_input, agent, session_id)` | 流式对话，yield JSON 事件 |
| `close()` | 关闭 HTTP 连接 |

> **注意：** `user_id` 通过 API Key 由服务端自动获取，无需手动传递。

---

## 12. HTTP 基础设施

SDK 内置了一套完整的 HTTP 客户端基础设施，供各模块使用。

### 12.1 HTTPClient

```python
from aigility.http.client import HTTPClient

http = HTTPClient(
    base_url="https://api.example.com",
    api_key="xxx",
    timeout=60.0,
    verify_ssl=False,
)

# 普通请求
result = await http.request("POST", "/chat", data={"input": "hello"})

# 流式请求
async for line in http.stream_request("POST", "/chat", data={"stream": True}):
    print(line)
```

### 12.2 内置组件

| 组件 | 文件 | 说明 |
|------|------|------|
| `ConnectionPool` | `pool.py` | httpx 连接池管理 |
| `CircuitBreaker` | `circuit_breaker.py` | 熔断器（防止雪崩） |
| `RetryHandler` | `retry.py` | 指数退避重试策略 |

### 12.3 配置

通过 `ADKConfig` 的 HTTP 字段控制：

```python
config = ADKConfig(
    http_timeout=60.0,      # 请求超时
    http_max_retries=3,      # 最大重试次数
    http_verify_ssl=False,   # SSL 验证
)
```

---

## 13. ModelFactory：LLM 实例化

`ModelFactory` 根据 `ADKConfig` 创建 LangChain LLM 实例，是 SDK 内部 LLM 统一管理的核心。

```python
from aigility.core.model_factory import ModelFactory
from aigility.core.config import ADKConfig

# 方式1: 通过 ADKConfig
config = ADKConfig(
    llm_provider="deepseek",
    llm_model="deepseek-chat",
    llm_api_key="sk-xxx",
    llm_base_url="https://api.deepseek.com",
    llm_temperature=0.7,
    llm_max_tokens=2000,
)
llm = ModelFactory.create_llm(config)
# 返回 ChatOpenAI 实例，streaming=True

# 方式2: 通过 create_llm() 快捷函数（推荐）
from aigility.model import create_llm

llm = create_llm(
    provider="deepseek",
    model="deepseek-chat",
    api_key="sk-xxx",
    base_url="https://api.deepseek.com",
    temperature=0.7,
    max_tokens=2000,
)

# 直接使用 LangChain 调用
from langchain_core.messages import HumanMessage
response = llm.invoke([HumanMessage(content="你好")])
print(response.content)
```

**Provider 路由逻辑：**

```
llm_provider
├── "deepseek"
│   ├── 尝试 ChatDeepSeek (langchain-deepseek)
│   └── 回退 ChatOpenAI (base_url=deepseek)
└── 其他（包括 "openai"）
    └── ChatOpenAI
```

---

## 14. 工具系统与扩展点

### 14.1 内置工具

SDK 在 ChatFlow 中内置了以下工具：

| 工具名 | 类 | 功能 | 状态 |
|--------|-----|------|------|
| `TimeMRAGTool` | - | TimeM 云服务 RAG 检索 | ✅ 已实现 |
| `WebSearchTool` | - | 互联网搜索 | ⚠️ 占位实现 |

### 14.2 工具数据模型

```python
# aigility.chatflow.schema

class ToolCall(BaseModel):
    tool_name: str   # 工具名称
    query: str       # 检索查询

class ToolResult(BaseModel):
    tool_name: str   # 工具名称
    result: str      # 执行结果
```

### 14.3 扩展工具

ChatFlow 的 `tool_executor` 节点通过 `tool_name` 分发，可以在 `flow_config` 中自定义决策 prompt 来引导 LLM 调用新工具。但目前 SDK 尚未提供标准化的工具注册机制，扩展需要修改 `_tool_executor` 方法或在外层自行编排。

### 14.4 抽象基类

SDK 定义了 `BaseAgent`、`BaseTool`、`BaseMemory` 三个抽象基类（`aigility.core.base`），可用于自定义实现：

```python
from aigility.core.base import BaseTool

class MyCustomTool(BaseTool):
    def __init__(self):
        super().__init__(name="my_tool", description="自定义工具")

    async def invoke(self, **kwargs) -> Any:
        return {"result": "..."}

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {...}}
```

---

## 15. 已知限制与路线图

### 15.1 当前限制

| 模块 | 限制 | 影响 |
|------|------|------|
| `workflow` | `WorkflowEngine.invoke()` / `stream()` 未实现 | 无法使用 SDK 的通用工作流引擎 |
| `workflow` | `WorkflowGraphBuilder.build()` 无法运行 | 只能直接使用 LangGraph API |
| `chatflow` | 工具系统无注册机制 | 扩展工具需修改源码 |
| `chatflow` | `WebSearchTool` 为占位实现 | 互联网搜索不可用 |
| `chatflow` | `astream` 使用 updates 模式手动拼接 | 流式输出粒度为节点级，非 token 级 |
| `rag` | 本地 RAGService 依赖 sklearn/jieba/rank_bm25 | 需额外安装依赖 |
| `http` | 连接池/熔断器的具体策略不可配置 | 使用默认策略 |

### 15.2 推荐的使用方式

| 需求 | 推荐方案 |
|------|---------|
| 简单对话 + RAG | ✅ 直接使用 `ChatService` 或 `ChatAgent` |
| Agent 对话入口 | ✅ 使用 `ChatAgent.chat()` 或通过 `ADKClient.create_chat_agent()` |
| 自定义工作流 | ✅ 直接使用 LangGraph（参考 ChatFlow 源码） |
| 远程 Agent 调用 | ✅ 使用 `ADPClient` |
| 本地 RAG | ✅ 使用 `RAGService` |
| 记忆管理 | ✅ 使用 `Memory` |
| 通用工作流引擎 | ❌ SDK 尚未就绪，建议自行基于 LangGraph 实现 |

### 15.3 路线图

未来可能实现：

- `WorkflowEngine` 的 LangGraph StateGraph 封装
- `WorkflowGraphBuilder` 的图构建和编译
- 更多内置工具（Web Search、SQL 查询等）
- 工具注册和发现机制

---

## 附录 A：导入路径速查

```python
# ===== 核心 =====
from aigility import ADKClient, ADKClientBuilder, create_client
from aigility.core.config import ADKConfig, AgentConfig, ToolConfig
from aigility.core.model_factory import ModelFactory
from aigility.core.types import State, Message, AgentResponse, MessageRole
from aigility.core.base import BaseAgent, BaseTool, BaseMemory

# ===== Chat =====
from aigility.chat.service import ChatService
from aigility.chat.schema import ChatRequest, ChatResponse
from aigility.chat.agent import ChatAgent, create_chat_agent

# ===== ChatFlow =====
from aigility.chatflow.flow import ChatFlow, create_chatflow
from aigility.chatflow.schema import ChatFlowState, ToolCall, ToolResult

# ===== Model =====
from aigility.model import create_llm

# ===== RAG =====
from aigility.rag.service import RAGService
from aigility.rag.client import TimeMRAGClient
from aigility.rag import create_timem_rag_client
from aigility.rag.config import RAGConfig

# ===== Memory =====
from aigility.memory import Memory, MemoryConfig, MemoryProviderConfig

# ===== Workflow =====
from aigility.workflow.engine import WorkflowEngine      # ⚠️ 未实现
from aigility.workflow.builder import WorkflowGraphBuilder  # ⚠️ 未实现

# ===== ADP =====
from aigility.adp.client import ADPClient

# ===== HTTP =====
from aigility.http.client import HTTPClient
from aigility.http.retry import RetryConfig
from aigility.http.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from aigility.http.pool import ConnectionPool, ConnectionConfig
```

---

## 附录 B：完整示例

### B.1 带 RAG 的完整对话流程

```python
import asyncio
from aigility.core.config import ADKConfig
from aigility.chat.service import ChatService
from aigility.chat.schema import ChatRequest

async def main():
    # 配置（以 DeepSeek 为例，其他提供商同理）
    config = ADKConfig(
        llm_provider="deepseek",
        llm_model="deepseek-chat",
        llm_api_key="sk-xxx",
        llm_base_url="https://api.deepseek.com",
        llm_temperature=0.7,
        llm_max_tokens=2000,
        timem_enabled=True,
        timem_api_key="timem-xxx",
        timem_base_url="https://api.timem.cloud",
        debug=True,
    )

    # 创建服务
    service = ChatService(adk_config=config)

    # 对话
    request = ChatRequest(
        user_input="你们支持哪些支付方式？",
        kb_id="kb_my_store",
        rag_used="auto",
    )

    # 同步调用
    response = service.process_chat(request)
    print(f"回复: {response.response}")
    print(f"思考: {response.thought_process}")
    print(f"工具: {response.tool_results}")

    # 流式调用
    async for event in service.process_chat_stream(request):
        node = list(event.keys())[0]
        if node == "stream_response":
            msg = event[node]["messages"][0]
            print(msg.content, end="", flush=True)

asyncio.run(main())
```

### B.1.1 通过 ChatAgent 对话（更简洁）

```python
from aigility import ADKClientBuilder

client = (
    ADKClientBuilder()
    .with_llm(
        provider="deepseek",
        model="deepseek-chat",
        api_key="sk-xxx",
        base_url="https://api.deepseek.com",
    )
    .build()
)

agent = client.create_chat_agent("my_agent")

# 纯对话
response = agent.chat("你好", rag_used="off")
print(response)

# 带 RAG 的对话
response = agent.chat("你们的最小起订量是多少？", rag_used="auto")
print(response)
```

### B.2 自定义 flow_config

```python
custom_config = {
    "agent_decision_prompt": """你是一个智能客服助手。
根据用户的问题，决定是否需要搜索知识库。

可用工具：
{tool_descriptions}

历史对话：
{history}

用户问题：{input}

请以 JSON 格式输出你的决策。""",

    "final_response_prompt": """你是专业的销售顾问。请根据以下信息回答用户问题。

参考信息：
{tool_results}

历史对话：
{history}

用户问题：{input}

请直接回答，不要包含分析过程。""",
}

service = ChatService(adk_config=config, flow_config=custom_config)
```
