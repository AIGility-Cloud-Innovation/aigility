// EXPORTS: DOC_NAV, DOC_CONTENT

export interface DocNavItem {
  id: string;
  title: string;
  children?: DocNavItem[];
}

export interface DocSearchResult {
  id: string;
  title: string;
  section: string;
  snippet: string;
}

export const DOC_NAV: DocNavItem[] = [
  {
    id: 'overview',
    title: 'SDK 概述',
  },
  {
    id: 'quick-start',
    title: '快速开始',
    children: [
      { id: 'quick-start-simple', title: '最简示例' },
      { id: 'quick-start-stream', title: '流式对话' },
      { id: 'quick-start-builder', title: 'Builder 模式' },
    ],
  },
  {
    id: 'structure',
    title: '包结构与实现状态',
  },
  {
    id: 'config',
    title: '核心配置：ADKConfig',
    children: [
      { id: 'config-fields', title: '完整字段说明' },
      { id: 'config-provider', title: 'LLM 提供商兼容性' },
      { id: 'config-examples', title: '各提供商配置示例' },
      { id: 'config-env', title: '配置与环境变量' },
    ],
  },
  {
    id: 'client',
    title: 'ADKClient：统一客户端入口',
  },
  {
    id: 'chat',
    title: 'Chat 模块',
    children: [
      { id: 'chat-service', title: 'ChatService' },
      { id: 'chat-agent', title: 'ChatAgent' },
      { id: 'chat-schema', title: '数据模型' },
      { id: 'chat-rag', title: 'RAG 模式详解' },
    ],
  },
  {
    id: 'chatflow',
    title: 'ChatFlow 模块',
  },
  {
    id: 'rag',
    title: 'RAG 模块',
  },
  {
    id: 'memory',
    title: 'Memory 模块',
  },
  {
    id: 'workflow',
    title: 'Workflow 模块',
  },
  {
    id: 'adp',
    title: 'ADP 模块',
  },
  {
    id: 'http',
    title: 'HTTP 基础设施',
  },
  {
    id: 'modelfactory',
    title: 'ModelFactory：LLM 实例化',
  },
  {
    id: 'tools',
    title: '工具系统与扩展点',
  },
  {
    id: 'roadmap',
    title: '已知限制与路线图',
  },
  {
    id: 'appendix-a',
    title: '附录 A：导入路径速查',
  },
  {
    id: 'appendix-b',
    title: '附录 B：完整示例',
  },
];

export const DOC_CONTENT: string = `# Aigility SDK (ADK) 使用文档

> **当前开发分支包版本：** 2.0.1 | **维护方：** AIGility Cloud Innovation
>
> 本文档面向 SDK 使用者，详细说明 \`aigility\` 包的架构设计、各模块功能、使用方式及当前实现状态。
>
> **2026-08-12 增量更新：** 已同步 TiMEM（太忆）可插拔记忆接口、服务端唯一会话、\`kb_id\` 校验与模型原生推理内容（CoT）输出。

***

## 1. SDK 概述 {#overview}

\`aigility\`（AIGility ADK - Agent Development Kit）是基于 **LangGraph / LangChain** 的智能体开发框架，提供从对话、RAG 检索到工作流编排的全链路能力。

### 设计理念

- **即插即用**：\`ChatService\` / \`ChatFlow\` 开箱可用，内置 CoT 决策 + RAG 工具调用
- **配置驱动**：通过 \`ADKConfig\` 统一管理 LLM、记忆、RAG 等服务的连接
- **会话安全**：服务端签发不携带用户信息的唯一 \`session_id\`，认证上下文负责所有权校验
- **可扩展**：支持自定义 prompt、工具、工作流节点，以及通过统一契约接入其他 Memory Provider

### 核心依赖

| 依赖 | 用途 |
| --- | --- |
| \`langgraph\` | 状态机编排（ChatFlow 内部） |
| \`langchain-core\` | Prompt、OutputParser、消息模型 |
| \`langchain-openai\` | OpenAI 兼容的 LLM 客户端 |
| \`pydantic\` | 数据校验和 Schema 定义 |
| \`httpx\` | 异步 HTTP 客户端 |
| \`timem-ai\`（可选） | TiMEM 云端记忆 Provider；通过 \`pip install "aigility[timem]"\` 安装 |

***

## 2. 快速开始 {#quick-start}

### 2.1 最简示例：带 RAG 的受认证会话 {#quick-start-simple}

\`\`\`python
from aigility.chat.service import ChatService
from aigility.chat.schema import ChatRequest
from aigility.conversation import ConversationContext
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
    timem_kb_id="kb_store",              # 默认知识库；请求可按次覆盖
)

# 2. 创建服务
service = ChatService(adk_config=config)

# 3. 对话
request = ChatRequest(
    user_input="你们的最小起订量是多少？",
    rag_used="auto",          # auto / on / off
)

# 应由认证中间件构造；不要把请求体内的 user_id 直接作为可信上下文。
context = ConversationContext(user_id="authenticated-user-123", agent_id="sales-agent")
response = service.process_chat(request, context=context)

print(response.response)          # AI 回复
print(response.session_id)         # 服务端签发的唯一会话 ID
print(response.thought_process)    # Agent 决策过程
print(response.reasoning_content)  # 模型原生推理内容（模型支持时）
print(response.tool_results)      # RAG 检索结果
\`\`\`

> \`rag_used="auto"\` 或 \`"on"\` 时，必须在 \`ChatRequest.kb_id\` 或 \`ADKConfig.timem_kb_id\` 中提供知识库 ID；纯对话请显式使用 \`rag_used="off"\`。

### 2.2 流式对话 {#quick-start-stream}

\`\`\`python
import asyncio

async def main():
    # 回传已有 ID，标记为同一会话；当前消息历史由应用自行维护或加载。
    follow_up = ChatRequest(
        user_input="那最小起订量对应的交期呢？",
        session_id=response.session_id,
        rag_used="auto",
    )
    async for event in service.process_chat_stream(follow_up, context=context):
        # 首个事件先告知客户端本次会话的 canonical session_id。
        if "conversation" in event:
            print("session_id:", event["conversation"]["session_id"])
            continue

        if "stream_response" not in event:
            continue

        chunk = event["stream_response"]["messages"][0]
        reasoning = chunk.additional_kwargs.get("reasoning_content")
        if reasoning:
            print(reasoning, end="", flush=True)  # 按需展示或仅记录
        else:
            print(chunk.content, end="", flush=True)

asyncio.run(main())
\`\`\`

### 2.3 使用 Builder 模式创建客户端 {#quick-start-builder}

\`\`\`python
from aigility import ADKClientBuilder

client = (
    ADKClientBuilder()
    .with_llm(provider="deepseek", model="deepseek-chat", api_key="sk-xxx",
              base_url="https://api.deepseek.com")
    .with_memory(provider="timem", api_key="timem-xxx", timeout_seconds=90,
                 max_retries=0)
    .with_rag(api_key="timem-xxx", kb_id="kb_store")
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
# Memory 是显式调用的门面；ChatAgent / ChatService 不会自动写入或检索。
# 使用 response.session_id 构造请求，详见第 9.2 节。
\`\`\`

***

## 3. 包结构与实现状态 {#structure}

\`\`\`
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
├── conversation/
│   ├── contracts.py         # ✅ 会话、认证上下文与所有权错误契约
│   ├── id_generator.py      # ✅ UUID4 唯一 session_id 生成器（可替换）
│   ├── repository.py        # ✅ 会话持久化接口与内存实现
│   └── service.py           # ✅ 会话创建、幂等与所有权校验
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
│   ├── contracts.py         # ✅ Provider 无关的请求、结果、能力与错误契约
│   └── providers/
│       ├── factory.py       # ✅ Provider 工厂
│       ├── base.py          # ✅ Provider 扩展基类
│       └── timem.py         # ✅ TiMEM（太忆）Provider
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
\`\`\`

**图例：** ✅ 可用 | ⚠️ 部分可用 / 框架已有但核心方法未实现 | ❌ 未实现

***

## 4. 核心配置：ADKConfig {#config}

\`ADKConfig\` 是贯穿整个 SDK 的配置中枢，定义在 \`aigility.core.config\` 中。

### 4.1 完整字段说明 {#config-fields}

\`\`\`python
from aigility.core.config import ADKConfig

config = ADKConfig(
    # ===== LLM 配置 =====
    llm_provider="openai",          # "openai"（默认，兼容所有 OpenAI 兼容提供商）、"deepseek"
    llm_model="gpt-4",              # 模型名称
    llm_api_key="sk-xxx",           # API Key
    llm_base_url=None,              # API Base URL（留空则用 provider 默认值）
    llm_temperature=0.7,            # 温度
    llm_max_tokens=2000,            # 最大输出 token
    llm_reasoning=False,             # 是否请求模型返回原生推理内容（需模型支持）
    llm_reasoning_effort=None,       # OpenAI o 系列可选："low" / "medium" / "high"

    # ===== Memory 配置 =====
    memory_enabled=True,            # 是否启用记忆模块
    memory_provider="timem",        # Provider 注册名；可替换为应用注册的其他服务
    memory_api_key=None,            # 记忆服务 API Key
    memory_base_url=None,           # 记忆服务 Base URL
    memory_options={},               # Provider 私有项；可含 timeout_seconds、max_retries、sdk_options

    # ===== Knowledge 配置 =====
    knowledge_enabled=True,         # 是否启用知识库
    knowledge_store_type="vector",  # 存储类型: "vector", "graph", "hybrid"

    # ===== TimeM RAG 云服务配置 =====
    timem_enabled=False,            # 是否启用 TimeM RAG
    timem_api_key=None,             # TimeM API Key
    timem_base_url=None,            # TimeM Base URL
    timem_kb_id=None,               # 默认知识库 ID；每次请求可通过 kb_id 覆盖

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
\`\`\`

### 4.1.1 本次新增配置的使用边界

- \`memory_*\` 配置的是 **Memory Provider**；\`timem_*\` 配置的是 **TiMEM RAG**。两者可以共用同一份凭据，但用途和初始化链路独立。
- \`memory_options\` 中的 \`timeout_seconds\` 默认 \`90\`，\`max_retries\` 默认 \`0\`，后者默认关闭以避免写入请求因重试而重复入库。其余参数以 Provider 私有配置传入，例如 \`sdk_options\`。
- \`llm_reasoning=True\` 仅应配合支持思维链的模型使用。普通模型可能拒绝该参数；\`llm_reasoning_effort\` 仅在 OpenAI o 系列等兼容模型上生效。

### 4.2 LLM 提供商兼容性 {#config-provider}

SDK 的 \`ModelFactory\` 内部使用 LangChain 的 \`ChatOpenAI\`，因此**所有兼容 OpenAI API 格式的提供商均可直接使用**。

| \`llm_provider\` | 实际创建的类 | 说明 |
| --- | --- | --- |
| \`"openai"\` | \`ChatOpenAI\` | 默认分支，兼容所有 OpenAI API 格式的提供商 |
| \`"deepseek"\` | \`ChatDeepSeek\` 或 \`ChatOpenAI\` | 优先尝试 langchain-deepseek，失败则回退 |

### 4.3 各提供商配置示例 {#config-examples}

#### DeepSeek

\`\`\`python
config = ADKConfig(
    llm_provider="deepseek",
    llm_model="deepseek-chat",               # 或 deepseek-coder
    llm_api_key="sk-xxx",
    llm_base_url="https://api.deepseek.com",
)
\`\`\`

#### 智谱 AI（GLM）

\`\`\`python
config = ADKConfig(
    llm_provider="openai",                    # 智谱兼容 OpenAI 接口
    llm_model="glm-4-flash",                  # glm-4、glm-4-flash 等
    llm_api_key="xxx.xxx",
    llm_base_url="https://open.bigmodel.cn/api/paas/v4",
)
\`\`\`

#### 阿里云百炼（通义千问）

\`\`\`python
config = ADKConfig(
    llm_provider="openai",
    llm_model="qwen-plus",                    # qwen-turbo、qwen-max 等
    llm_api_key="sk-xxx",
    llm_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
\`\`\`

#### Moonshot（Kimi）

\`\`\`python
config = ADKConfig(
    llm_provider="openai",
    llm_model="moonshot-v1-8k",               # moonshot-v1-32k 等
    llm_api_key="sk-xxx",
    llm_base_url="https://api.moonshot.cn/v1",
)
\`\`\`

#### 豆包（火山引擎）

\`\`\`python
config = ADKConfig(
    llm_provider="openai",
    llm_model="doubao-pro-4k",                # 模型端点 ID
    llm_api_key="xxx",
    llm_base_url="https://ark.cn-beijing.volces.com/api/v3",
)
\`\`\`

#### OpenAI（官方）

\`\`\`python
config = ADKConfig(
    llm_provider="openai",
    llm_model="gpt-4o",                       # gpt-4、gpt-3.5-turbo 等
    llm_api_key="sk-xxx",
    # llm_base_url 留空，使用 OpenAI 官方地址
)
\`\`\`

#### 通过 Builder 模式配置

\`\`\`python
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
\`\`\`

#### 通过 create_llm() 快捷函数

\`\`\`python
from aigility.model import create_llm

llm = create_llm(
    provider="deepseek",
    model="deepseek-chat",
    api_key="sk-xxx",
    base_url="https://api.deepseek.com",
    temperature=0.7,
    max_tokens=2000,
)
\`\`\`

> **规则总结：**
>
> - DeepSeek → \`llm_provider="deepseek"\`
> - 其他所有 OpenAI 兼容提供商 → \`llm_provider="openai"\` + 对应的 \`llm_base_url\`
> - SDK 会自动将 \`llm_temperature\` 和 \`llm_max_tokens\` 传递给模型

### 4.4 配置与环境变量 {#config-env}

SDK 的 Memory Provider 支持从环境变量自动读取：

| 环境变量 | 对应配置 |
| --- | --- |
| \`TIMEM_API_KEY\` | \`MemoryProviderConfig(provider="timem")\` 未显式传入 \`api_key\` 时的回退值 |
| \`TIMEM_BASE_URL\` | \`MemoryProviderConfig(provider="timem")\` 未显式传入 \`base_url\` 时的回退值（默认 \`https://api.timem.cloud\`） |
| \`DEEPSEEK_API_KEY\` | \`llm_api_key\`（需手动传入） |

> \`ADKConfig.timem_api_key\` / \`timem_base_url\` 用于 RAG 客户端；RAG 凭据请显式在 \`ADKConfig\` 或 \`ADKClientBuilder.with_rag()\` 中设置，不依赖上述 Memory Provider 的环境变量回退。

***

## 5. ADKClient：统一客户端入口 {#client}

\`ADKClient\` 是 SDK 的顶层门面，提供统一的模块访问入口。

### 5.1 创建方式

\`\`\`python
from aigility import ADKClient, ADKClientBuilder, create_client

# 方式1: 直接传入 config
client = ADKClient(config=ADKConfig(...))

# 方式2: Builder 模式（推荐）
client = (
    ADKClientBuilder()
    .with_llm(provider="openai", model="gpt-4", api_key="sk-xxx")
    .with_memory(provider="timem", api_key="timem-xxx")
    .with_rag(api_key="timem-xxx", kb_id="kb_store")
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
\`\`\`

### 5.2 可用方法

\`\`\`python
# 创建对话智能体（推荐入口）
agent = client.create_chat_agent("my_agent")

# 同步纯对话（最简用法）
response = agent.chat("你好", rag_used="off")
print(response)  # AI 回复文本

# 对话 + RAG（kb_id 可在调用时覆盖 Builder 中的默认值）
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
print(mem.provider_name, mem.capabilities)
# ChatAgent / ChatService 不会自动执行记忆读写；业务层应显式调用 mem.write()/retrieve()。

# 关闭客户端
await client.close()
\`\`\`

***

## 6. Chat 模块 {#chat}

### 6.1 ChatService {#chat-service}

\`ChatService\` 是 SDK 的对话服务主类，内部封装了 \`ChatFlow\`（LangGraph 状态机）。

\`\`\`python
from aigility.chat.service import ChatService
from aigility.chat.schema import ChatRequest
from aigility.conversation import ConversationContext
from aigility.core.config import ADKConfig

config = ADKConfig(
    llm_provider="deepseek",
    llm_model="deepseek-chat",
    llm_api_key="sk-xxx",
    llm_base_url="https://api.deepseek.com",
    timem_enabled=True,
    timem_api_key="your-timem-api-key",
    timem_base_url="https://api.timem.cloud",
    timem_kb_id="kb_xxx",
)
service = ChatService(adk_config=config)

# 同步对话
request = ChatRequest(
    user_input="你们支持哪些支付方式？",
    rag_used="auto",
)

# 认证层负责生成可信 context；不要让调用方在请求体中伪造 user_id。
context = ConversationContext(user_id="user-001", agent_id="sales-agent")
response = service.process_chat(request, context=context)
print(response.response)
print(response.session_id)
\`\`\`

**构造参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| \`adk_config\` | \`ADKConfig\` | 否 | 全局配置，默认使用 \`ADKConfig()\` |
| \`flow_config\` | \`Dict[str, Any]\` | 否 | 对话流配置，不传则使用内置默认配置 |
| \`session_service\` | \`ConversationSessionService\` | 否 | 会话生命周期服务；默认使用进程内实现 |

**可用方法：**

| 方法 | 类型 | 返回值 | 说明 |
| --- | --- | --- | --- |
| \`process_chat(request, context=None)\` | 同步 | \`ChatResponse\` | 完整对话处理；生产环境传入认证后的 \`ConversationContext\` |
| \`process_chat_stream(request, context=None)\` | 异步生成器 | \`Dict\` 事件 | 流式对话；首个事件含服务端会话 ID |
| \`generate_session_title(user_input, ai_response)\` | 同步 | \`str\` | 生成会话标题 |
| \`generate_reply_suggestions(ai_response)\` | 同步 | \`List[str]\` | 生成回复建议 |

### 6.1.1 服务端唯一会话与所有权

\`session_id\` 是一个全局唯一、不可从中推导用户或 Agent 信息的 opaque ID，默认格式为 \`sess_<uuid4-hex>\`。它只标识**一次会话**，不再采用 \`user_id-session_id\` 的拼接方式。

- 新会话：请求不带 \`session_id\`，由 \`ConversationSessionService\` 签发；可带 \`idempotency_key\`，重试同一创建请求会返回同一会话，但该键不会参与 ID 生成。
- 续聊：请求带上之前响应中的 \`session_id\`。服务会基于 \`ConversationContext.user_id\` 校验归属，错误用户不能复用他人的会话。
- 认证边界：\`ConversationContext(user_id, agent_id)\` 必须由鉴权后的服务端创建，而非直接反序列化用户请求。
- 持久化：默认仓库 \`InMemoryConversationSessionRepository\` 仅适合 SDK/测试，进程重启后会丢失。生产环境应向 \`ChatService(session_service=...)\` 注入实现了 \`ConversationSessionRepository\` 的数据库适配器。
- 消息历史：当前 \`ChatService\` 不会仅凭 \`session_id\` 自动加载历史消息；会话仓库负责 ID 生命周期和所有权，消息历史应由应用的消息存储自行维护或在调用 ChatFlow 时显式提供。
- 兼容模式：不传 \`context\` 仍可调用旧版直连接口，但 \`session_id\` 不会被持久化或授权校验；不要用于多用户服务。

需要写入或检索记忆时，使用响应返回的同一个 \`session_id\` 作为 \`ConversationScope.session_id\` 或 \`MemorySearchRequest.session_id\`，保证会话与记忆的关联一致。

### 6.2 ChatAgent {#chat-agent}

\`ChatAgent\` 是 SDK 的对话智能体入口，内部委托 \`ChatFlow\` 执行对话，对外提供简化的 Agent 接口。

\`\`\`python
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
        timem_kb_id="kb_xxx",
    ),
)

# 方式1：同步便捷方法（推荐）
response = agent.chat("你好", rag_used="off")
print(response)  # AI 回复文本

# 方式2：通过 ADKClient 创建
from aigility import ADKClientBuilder

client = (
    ADKClientBuilder()
    .with_llm(provider="deepseek", model="deepseek-chat", api_key="sk-xxx")
    .with_rag(api_key="timem-xxx", kb_id="kb_xxx")
    .build()
)
agent = client.create_chat_agent("my_agent")
response = agent.chat("你好", rag_used="auto")
\`\`\`

**构造参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| \`name\` | \`str\` | 是 | 智能体名称 |
| \`adk_config\` | \`ADKConfig\` | 否 | 全局配置，默认使用 \`ADKConfig()\` |
| \`config\` | \`AgentConfig\` | 否 | 智能体配置（prompt 模板等） |

**可用方法：**

| 方法 | 类型 | 返回值 | 说明 |
| --- | --- | --- | --- |
| \`chat(user_input, rag_used="auto", kb_id=None)\` | 同步 | \`str\` | 便捷对话，非 \`off\` 时必须有调用参数或默认 \`kb_id\` |
| \`invoke(state)\` | 异步 | \`AgentResponse\` | 实现 BaseAgent 接口；从 \`state.metadata["kb_id"]\` 或默认配置取知识库 |

> \`ChatAgent\` 是简化的单次对话入口，不承担 \`ChatService\` 的会话所有权校验。无 RAG 的最简调用应写为 \`agent.chat("你好", rag_used="off")\`；\`"auto"\` / \`"on"\` 必须配置 \`kb_id\`。

### 6.3 数据模型 {#chat-schema}

\`\`\`python
from aigility.chat.schema import ChatRequest, ChatResponse

# 请求
class ChatRequest(BaseModel):
    user_input: str                          # 用户输入（必填）
    session_id: Optional[str] = None         # 服务端签发的会话 ID；缺失时创建新会话
    idempotency_key: Optional[str] = None     # 新建会话重试用；不参与 session_id 生成
    kb_id: Optional[str] = None               # 知识库 ID（非 off 的 RAG 必需，可由默认配置提供）
    rag_used: Literal["auto", "on", "off"] = "auto"

# 响应
class ChatResponse(BaseModel):
    response: str                            # AI 回复
    session_id: str                          # 会话 ID
    session_title: Optional[str] = None      # 会话标题
    reply_suggestions: List[str]             # 回复建议列表
    thought_process: Optional[str] = None    # Agent 决策过程
    reasoning_content: Optional[str] = None  # 模型原生推理内容（模型支持时）
    tool_results: Optional[List[dict]] = None # 工具调用结果
\`\`\`

### 6.4 RAG 模式详解 {#chat-rag}

\`rag_used\` 参数控制 RAG 行为，是 ChatService 最核心的配置之一：

| 模式 | 行为 | 适用场景 |
| --- | --- | --- |
| \`"auto"\` | LLM 自主决定是否调用 RAG 工具 | 通用场景，LLM 会根据问题判断是否需要检索 |
| \`"on"\` | 强制调用 RAG，跳过决策节点 | 确定需要检索的场景 |
| \`"off"\` | 强制关闭 RAG，纯对话模式 | 闲聊、创意写作等不需要知识库的场景 |

\`"auto"\` 与 \`"on"\` 都会校验知识库：优先用请求的 \`kb_id\`，其次用 \`ADKConfig.timem_kb_id\`；两者都没有时抛出 \`ValueError\`，以避免意外落到不确定的知识库。\`"off"\` 不要求 \`kb_id\`。

***

## 7. ChatFlow 模块 {#chatflow}

\`ChatFlow\` 是 SDK 的核心引擎，实现了一个完整的 **LangGraph 状态机**，包含 CoT 决策、工具执行和回复生成。

### 7.1 状态图结构

\`\`\`
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
\`\`\`

### 7.2 节点详解

#### \`agent_decision\` — 决策节点

- 使用 LLM + CoT Prompt 分析用户输入
- 输出 JSON：\`{"thought": "...", "tool_calls": [{"tool_name": "TimeMRAGTool", "query": "..."}]}\`
- 支持从用户输入中提取特殊检索标记：

    - \`【用于检索的关键词】xxx\` → 优先使用 \`xxx\` 作为 RAG query
    - \`【RAG_QUERY】xxx【/RAG_QUERY】\` → 同上

- 如果未检测到特殊标记，使用 LLM 决策的 query

#### \`tool_executor\` — 工具执行节点

- 遍历 \`tool_calls\`，根据 \`tool_name\` 分发执行
- \`TimeMRAGTool\` → 调用 \`timem_rag_client.search_sync(query, kb_id)\`
- \`WebSearchTool\` → 占位实现（返回模拟结果）
- 执行结果通过 \`ToolMessage\` 追加到消息历史

#### \`prepare_for_generation\` — 准备节点

- 从消息历史中提取用户输入、历史对话、工具结果
- 构建最终回复的 Prompt Template
- 创建保留原始消息对象的 \`prompt | llm\` Chain，使推理模型的 \`reasoning_content\` 不会在解析阶段丢失

#### \`stream_response\` — 生成节点

- 同步调用：直接 \`chain.invoke(prompt_input)\`
- 流式调用：通过 \`chain.astream(prompt_input)\` 逐 chunk 输出

### 7.3 调用方式

\`\`\`python
from aigility.chatflow.flow import ChatFlow
from langchain_core.runnables import RunnableConfig

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
    config=RunnableConfig(configurable={"timem_kb_id": "kb_xxx"}),
    rag_used="auto",
)
# result = {
#     "response": "...",
#     "reasoning_content": "...",      # 模型支持时返回
#     "thought_process": "...",
#     "tool_results": [ToolResult(...)],
#     "full_history": [...],
# }

# 异步流式调用
async for event in flow.astream(
    user_input="你们的产品有哪些认证？",
    config=RunnableConfig(configurable={"timem_kb_id": "kb_xxx"}),
    rag_used="auto",
):
    if "stream_response" not in event:
        continue
    chunk = event["stream_response"]["messages"][0]
    reasoning = chunk.additional_kwargs.get("reasoning_content")
    print(reasoning or chunk.content, end="", flush=True)
\`\`\`

### 7.4 内置 Prompt 配置

ChatFlow 的默认 prompt 从 \`chatflow/prompts/chat.yaml\` 加载，包含两个核心 prompt：

1. **\`agent_decision_prompt\`** — 指导 LLM 判断是否需要调用 RAG 工具
2. **\`final_response_prompt\`** — 指导 LLM 基于工具结果生成最终回复

可通过 \`flow_config\` 参数覆盖：

\`\`\`python
flow = ChatFlow(adk_config=config, flow_config={
    "agent_decision_prompt": "你是一个智能助手，请根据用户问题决定是否需要搜索知识库...",
    "final_response_prompt": "请根据以下信息回答用户问题...\\n{tool_results}\\n用户问：{input}",
})
\`\`\`

### 7.5 kb_id 传递机制

知识库 ID 通过 LangGraph 的 \`RunnableConfig\` 传递：

\`\`\`python
from langchain_core.runnables import RunnableConfig

config = RunnableConfig(configurable={"timem_kb_id": "kb_xxx"})
result = flow.invoke(user_input="...", config=config, rag_used="on")
\`\`\`

\`ChatFlow.invoke()\` / \`astream()\` 在 \`rag_used != "off"\` 时同样会校验该配置；纯对话可以传 \`rag_used="off"\`，不需要 \`RunnableConfig\`。

### 7.6 模型原生 CoT（推理内容）

SDK 将模型原生推理内容和 ChatFlow 的工具决策过程分开返回：\`thought_process\` 是 Agent 的决策文本，\`reasoning_content\` 是模型在 reasoning 模式下输出的原生内容。

\`\`\`python
config = ADKConfig(
    llm_provider="deepseek",
    llm_model="deepseek-reasoner",  # 需替换为实际支持 reasoning 的模型
    llm_api_key="sk-xxx",
    llm_reasoning=True,
)

result = ChatFlow(adk_config=config).invoke("比较两种方案", rag_used="off")
print(result["response"])
print(result["reasoning_content"])  # 可能为 None，取决于模型和提供商
\`\`\`

流式模式会先后产生两类 \`stream_response\` 事件：\`chunk.additional_kwargs["reasoning_content"]\` 为推理增量，\`chunk.content\` 为正文增量。推理内容可能包含不适合直接对终端用户展示的信息，建议按产品安全策略仅记录在受控日志或明确的调试视图中。

***

## 8. RAG 模块 {#rag}

RAG 模块提供两种使用方式：**TimeM 云服务** 和 **本地 RAGService**。

### 8.1 TimeM 云服务客户端

\`TimeMRAGClient\` 封装了对太忆 RAG API 的调用，是 \`ChatFlow\` 内部使用的 RAG 引擎。

\`\`\`python
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
\`\`\`

也可通过 \`create_timem_rag_client\` 快捷函数创建：

\`\`\`python
from aigility.rag import create_timem_rag_client

client = create_timem_rag_client(
    base_url="https://api.timem.cloud",
    api_key="your-api-key",
)
\`\`\`

### 8.2 本地 RAGService

\`RAGService\` 提供完整的本地 RAG 能力，包括文档入库、向量检索和混合搜索。

\`\`\`python
from aigility.rag.service import RAGService
from aigility.rag.config import RAGConfig

config = RAGConfig(...)
service = RAGService(config=config)
\`\`\`

**支持的向量数据库：**

| 数据库 | 文件 | 说明 |
| --- | --- | --- |
| Chroma | \`vector_stores/chroma.py\` | 轻量级，适合开发 |
| FAISS | \`vector_stores/faiss.py\` | Facebook 向量检索 |
| Qdrant | \`vector_stores/qdrant.py\` | 生产级向量数据库 |
| Milvus | \`vector_stores/milvus.py\` | 分布式向量数据库 |

**支持的 Embedding 模型：**

| 模型 | 文件 | 说明 |
| --- | --- | --- |
| HuggingFace | \`embeddings/huggingface.py\` | 本地模型 |
| DashScope | \`embeddings/dashscope.py\` | 阿里云 |
| ZAI | \`embeddings/zai.py\` | 智谱 |

**其他能力：**

- \`IngestionManager\` — 文档入库管理
- \`hybrid_search.py\` — BM25 + 向量混合搜索
- \`markdown_splitter.py\` — Markdown 文档切分

***

## 9. Memory 模块 {#memory}

### 9.1 设计与安装

\`aigility.memory\` 采用 Provider Registry + 供应商无关契约：应用只依赖统一的身份、会话、请求和结果类型；TiMEM（太忆）是内置的 \`timem\` Provider，其他记忆服务可在应用启动时注册，而不需要修改 SDK 的公共门面。

> **调用边界：** 配置 \`memory_*\` 或访问 \`ADKClient.memory\` 只会创建 Memory 门面。当前 \`ChatService\` / \`ChatAgent\` 不会自动写入或检索记忆；业务层应在完成对话、组装 Prompt 等合适位置，显式调用 \`Memory.write()\` / \`retrieve()\`，并使用聊天响应返回的 canonical \`session_id\`。

安装 TiMEM 适配器：

\`\`\`bash
pip install "aigility[timem]"
\`\`\`

TiMEM 的 API Key 可显式传入，或在创建 \`Memory()\` 前设置 \`TIMEM_API_KEY\`。未安装可选依赖或未提供密钥时，启用 TiMEM Provider 会在初始化时失败；这能尽早暴露配置错误。

\`\`\`python
from aigility.memory import Memory, MemoryConfig, MemoryProviderConfig

memory = Memory(
    config=MemoryConfig(
        provider=MemoryProviderConfig(
            provider="timem",
            api_key="timem-api-key",          # 或使用环境变量 TIMEM_API_KEY
            base_url="https://api.timem.cloud",
            timeout_seconds=90,
            max_retries=0,                     # 默认不重试，避免重复写入
        ),
        failure_mode="degrade",               # "degrade"（默认）或 "raise"
    )
)
\`\`\`

通过 \`ADKClientBuilder\` 配置时，\`with_memory()\` 的未知关键字会作为 Provider 私有选项保留：

\`\`\`python
client = (
    ADKClientBuilder()
    .with_memory(
        provider="timem",
        api_key="timem-api-key",
        timeout_seconds=90,
        max_retries=0,
        sdk_options={"your_provider_option": "value"},
    )
    .build()
)
memory = client.memory  # 首次访问时创建 Provider
\`\`\`

### 9.2 推荐接口：类型化写入与检索

新接入应使用 \`write()\` / \`retrieve()\`。这两个方法使用稳定的通用契约，并始终返回带有 \`status\`、\`provider\`、记录和错误信息的结果对象。

\`\`\`python
from aigility.memory import (
    ConversationScope,
    Memory,
    MemoryConfig,
    MemoryIdentity,
    MemoryProviderConfig,
    MemorySearchRequest,
    MemoryWriteRequest,
)

async def save_and_search(session_id: str) -> None:
    memory = Memory(
        MemoryConfig(
            provider=MemoryProviderConfig(provider="timem", api_key="timem-api-key")
        )
    )
    identity = MemoryIdentity(user_id="user-001", agent_id="sales-agent")

    write_result = await memory.write(
        MemoryWriteRequest(
            messages=[
                {"role": "user", "content": "我偏好月度结算。"},
                {"role": "assistant", "content": "已记录你的结算偏好。"},
            ],
            scope=ConversationScope(identity=identity, session_id=session_id),
            metadata={"source": "chat"},
            # 仅传入当前 Provider 支持的私有调用选项。
            provider_options={"domain": "sales"},
        )
    )
    if not write_result.success:
        print(write_result.status, write_result.error)
        return

    search_result = await memory.retrieve(
        MemorySearchRequest(
            query="用户喜欢怎样结算？",
            identity=identity,
            session_id=session_id,             # 省略则按身份跨会话检索
            limit=5,
            include_context=True,
        )
    )
    for record in search_result.records:
        print(record.content, record.score)

    await memory.close()
\`\`\`

身份与会话约束如下：

| 类型 | 必填字段 | 语义 |
| --- | --- | --- |
| \`MemoryIdentity\` | \`user_id\`、\`agent_id\` | 记忆的稳定用户和 Agent 作用域 |
| \`ConversationScope\` | \`identity\`、\`session_id\` | 一次写入所属的唯一会话 |
| \`MemoryWriteRequest\` | \`messages\`、\`scope\` | 消息中的每一项必须有非空的 \`role\` 和 \`content\` |
| \`MemorySearchRequest\` | \`query\`、\`identity\` | \`session_id\` 可选；不传时可检索该身份下的跨会话记忆 |

\`session_id\` 应复用 \`ChatService\` 响应返回的服务端会话 ID；Memory 模块不会从 \`user_id\` 推导或拼接一个会话 ID。

### 9.3 结果、能力与失败策略

\`MemoryWriteResult\` 和 \`MemorySearchResult\` 都提供 \`.success\` 与 \`.is_degraded\`。失败不会被伪装成空结果，状态统一为：\`success\`、\`disabled\`、\`blocked\`、\`unauthorized\`、\`invalid_request\`、\`rate_limited\`、\`unavailable\` 或 \`failed\`。

- 默认 \`failure_mode="degrade"\`：返回带错误信息的结果对象，适合把记忆作为可降级能力的在线对话。
- \`failure_mode="raise"\`：失败时抛出 \`MemoryProviderError\`，适合要求记忆写入必须成功的工作流。
- \`memory.capabilities\` 返回当前 Provider 的能力声明；避免在业务代码中按 Provider 名称分支。内置 TiMEM 适配器声明支持会话写入和语义检索。

\`\`\`python
strict_memory = Memory(
    MemoryConfig(
        provider=MemoryProviderConfig(provider="timem", api_key="timem-api-key"),
        failure_mode="raise",
    )
)
print(strict_memory.provider_name)
print(strict_memory.capabilities.to_dict())
\`\`\`

### 9.4 旧接口兼容层

历史的 \`add()\` / \`search()\` 仍可用，并返回字典格式的标准化结果。新代码优先使用上一节的类型化接口。

\`\`\`python
# character_id 是 agent_id 的兼容别名；二者同时传入时必须相同。
write_result = await memory.add(
    messages=[{"role": "user", "content": "请记住我的偏好"}],
    user_id="user-001",
    agent_id="sales-agent",
    session_id="sess_...",             # 写入时必填
)

search_result = await memory.search(
    query="用户的偏好",
    user_id="user-001",
    character_id="sales-agent",
    session_id="sess_...",             # 可省略以跨会话搜索
    limit=10,
)
\`\`\`

兼容层不会再以 \`user_id\` 生成会话 ID：\`add()\` 缺少 \`session_id\` 会直接抛出 \`ValueError\`。也不要把旧的 \`BaseMemory.get()\` 当作新的 Provider 通用能力；当前跨 Provider 的稳定表面仅包含写入与检索，扩展能力应先通过 \`capabilities\` 协商。

### 9.5 接入其他记忆服务

自定义适配器实现 \`BaseMemoryProvider.write()\` 与 \`BaseMemoryProvider.retrieve()\`，将服务商 SDK 的参数和响应映射到 AIGility 的契约，再在应用启动时注册。Provider 名称不受固定枚举限制。

\`\`\`python
from aigility.memory import (
    BaseMemoryProvider,
    MemoryCapabilities,
    MemoryProviderFactory,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryStatus,
    MemoryWriteRequest,
    MemoryWriteResult,
)

class MyMemoryProvider(BaseMemoryProvider):
    provider_name = "my-memory"
    capabilities = MemoryCapabilities(
        conversation_write=True,
        semantic_search=True,
    )

    async def write(self, request: MemoryWriteRequest) -> MemoryWriteResult:
        # 在此把 request 映射到第三方 SDK；省略实际网络调用。
        return MemoryWriteResult(status=MemoryStatus.SUCCESS, provider=self.provider_name)

    async def retrieve(self, request: MemorySearchRequest) -> MemorySearchResult:
        # 在此把第三方响应归一化为 MemoryRecord 列表。
        return MemorySearchResult(status=MemoryStatus.SUCCESS, provider=self.provider_name)

# 可直接注册类（构造函数接收 MemoryProviderConfig），也可注册自定义 builder。
MemoryProviderFactory.register("my-memory", MyMemoryProvider)

memory = Memory(
    MemoryConfig(
        provider=MemoryProviderConfig(
            provider="my-memory",
            api_key="provider-api-key",
            kwargs={"region": "cn"},
        )
    )
)
\`\`\`

\`MemoryProviderFactory.available_providers()\` 可查看已注册名称；重复注册默认会报错，如需替换应显式传 \`overwrite=True\`。Provider 私有的配置放在 \`MemoryProviderConfig.kwargs\`，单次调用的私有选项放在请求的 \`provider_options\`，避免污染跨 Provider 的通用接口。

***

## 10. Workflow 模块 {#workflow}

### 10.1 当前状态

> **⚠️ 未实现：** \`WorkflowEngine\` 和 \`WorkflowGraphBuilder\` 的核心方法均抛出 \`NotImplementedError\`。

### 10.2 WorkflowEngine（框架）

\`\`\`python
from aigility.workflow.engine import WorkflowEngine

# 已定义但 invoke()/stream() 未实现
engine = WorkflowEngine(name="my_workflow", nodes={...})
# await engine.invoke(state)   → NotImplementedError
# await engine.stream(state)   → NotImplementedError
\`\`\`

### 10.3 WorkflowGraphBuilder（框架）

\`\`\`python
from aigility.workflow.builder import WorkflowGraphBuilder

builder = WorkflowGraphBuilder()
builder.add_node("step1", my_func)
builder.add_edge("step1", "step2")
builder.set_start("step1")
# builder.build()  → NotImplementedError
\`\`\`

### 10.4 设计意图

Workflow 模块的定位是提供一个比 ChatFlow 更通用的工作流编排能力，但目前仍处于框架阶段。**实际使用中，建议直接使用 LangGraph 构建自定义工作流**（如 ChatFlow 内部所做的那样）。

***

## 11. ADP 模块 {#adp}

\`ADPClient\` 用于调用远程 Agent Deployment Platform (ADP) 服务。

\`\`\`python
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
\`\`\`

**接口说明：**

| 方法 | 说明 |
| --- | --- |
| \`chat(user_input, agent, session_id)\` | 调用远程 Agent 进行对话 |
| \`chat_stream(user_input, agent, session_id)\` | 流式对话，yield JSON 事件 |
| \`close()\` | 关闭 HTTP 连接 |

> **注意：** \`user_id\` 通过 API Key 由服务端自动获取，无需手动传递。

***

## 12. HTTP 基础设施 {#http}

SDK 内置了一套完整的 HTTP 客户端基础设施，供各模块使用。

### 12.1 HTTPClient

\`\`\`python
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
\`\`\`

### 12.2 内置组件

| 组件 | 文件 | 说明 |
| --- | --- | --- |
| \`ConnectionPool\` | \`pool.py\` | httpx 连接池管理 |
| \`CircuitBreaker\` | \`circuit_breaker.py\` | 熔断器（防止雪崩） |
| \`RetryHandler\` | \`retry.py\` | 指数退避重试策略 |

### 12.3 配置

通过 \`ADKConfig\` 的 HTTP 字段控制：

\`\`\`python
config = ADKConfig(
    http_timeout=60.0,      # 请求超时
    http_max_retries=3,      # 最大重试次数
    http_verify_ssl=False,   # SSL 验证
)
\`\`\`

***

## 13. ModelFactory：LLM 实例化 {#modelfactory}

\`ModelFactory\` 根据 \`ADKConfig\` 创建 LangChain LLM 实例，是 SDK 内部 LLM 统一管理的核心。

若所选模型支持原生推理，可在 \`ADKConfig\` 上配置 \`llm_reasoning=True\`；OpenAI o 系列还可设置 \`llm_reasoning_effort="low" | "medium" | "high"\`。DeepSeek 路径会根据该开关传入 thinking 配置，并将流式返回的推理内容归一化到 \`reasoning_content\`。模型不支持时请关闭该开关。

\`\`\`python
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
\`\`\`

**Provider 路由逻辑：**

\`\`\`
llm_provider
├── "deepseek"
│   ├── 尝试 ChatDeepSeek (langchain-deepseek)
│   └── 回退 ChatOpenAI (base_url=deepseek)
└── 其他（包括 "openai"）
    └── ChatOpenAI
\`\`\`

***

## 14. 工具系统与扩展点 {#tools}

### 14.1 内置工具

SDK 在 ChatFlow 中内置了以下工具：

| 工具名 | 类 | 功能 | 状态 |
| --- | --- | --- | --- |
| \`TimeMRAGTool\` | - | TimeM 云服务 RAG 检索 | ✅ 已实现 |
| \`WebSearchTool\` | - | 互联网搜索 | ⚠️ 占位实现 |

### 14.2 工具数据模型

\`\`\`python
# aigility.chatflow.schema

class ToolCall(BaseModel):
    tool_name: str   # 工具名称
    query: str       # 检索查询

class ToolResult(BaseModel):
    tool_name: str   # 工具名称
    result: str      # 执行结果
\`\`\`

### 14.3 扩展工具

ChatFlow 的 \`tool_executor\` 节点通过 \`tool_name\` 分发，可以在 \`flow_config\` 中自定义决策 prompt 来引导 LLM 调用新工具。但目前 SDK 尚未提供标准化的工具注册机制，扩展需要修改 \`_tool_executor\` 方法或在外层自行编排。

### 14.4 抽象基类

SDK 定义了 \`BaseAgent\`、\`BaseTool\`、\`BaseMemory\` 三个历史抽象基类（\`aigility.core.base\`），可用于自定义实现：

\`\`\`python
from aigility.core.base import BaseTool

class MyCustomTool(BaseTool):
    def __init__(self):
        super().__init__(name="my_tool", description="自定义工具")

    async def invoke(self, **kwargs) -> Any:
        return {"result": "..."}

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {...}}
\`\`\`

> 如需扩展新的云端记忆服务，请使用第 9.5 节的 \`BaseMemoryProvider\` 和 \`MemoryProviderFactory\`；它们是当前 Memory 模块的稳定 Provider 扩展点。

***

## 15. 已知限制与路线图 {#roadmap}

### 15.1 当前限制

| 模块 | 限制 | 影响 |
| --- | --- | --- |
| \`workflow\` | \`WorkflowEngine.invoke()\` / \`stream()\` 未实现 | 无法使用 SDK 的通用工作流引擎 |
| \`workflow\` | \`WorkflowGraphBuilder.build()\` 无法运行 | 只能直接使用 LangGraph API |
| \`chatflow\` | 工具系统无注册机制 | 扩展工具需修改源码 |
| \`chatflow\` | \`WebSearchTool\` 为占位实现 | 互联网搜索不可用 |
| \`chatflow\` | \`astream\` 使用 updates 模式手动拼接 | 流式输出粒度为节点级，非 token 级 |
| \`rag\` | 本地 RAGService 依赖 sklearn/jieba/rank_bm25 | 需额外安装依赖 |
| \`conversation\` | 默认会话仓库仅在内存中保存 | 生产环境须注入数据库等持久化 \`ConversationSessionRepository\` |
| \`chat\` | \`session_id\` 当前不自动恢复消息历史 | 应用需单独维护消息历史，或在低层 \`ChatFlow\` 调用时显式传入 \`history\` |
| \`memory\` | 内置适配器目前为 TiMEM；其他服务需要应用侧注册适配器 | 业务应只依赖 \`write/retrieve\` 与 \`capabilities\`，不要耦合供应商 SDK |
| \`memory\` | \`timem-ai\` 是可选依赖且需要有效凭据 | 使用 TiMEM 前安装 \`aigility[timem]\` 并配置密钥 |
| \`http\` | 连接池/熔断器的具体策略不可配置 | 使用默认策略 |

### 15.2 推荐的使用方式

| 需求 | 推荐方案 |
| --- | --- |
| 简单对话 + RAG | ✅ 直接使用 \`ChatService\` 或 \`ChatAgent\` |
| Agent 对话入口 | ✅ 使用 \`ChatAgent.chat()\` 或通过 \`ADKClient.create_chat_agent()\` |
| 自定义工作流 | ✅ 直接使用 LangGraph（参考 ChatFlow 源码） |
| 远程 Agent 调用 | ✅ 使用 \`ADPClient\` |
| 本地 RAG | ✅ 使用 \`RAGService\` |
| 记忆管理 | ✅ 使用 \`Memory\` |
| 通用工作流引擎 | ❌ SDK 尚未就绪，建议自行基于 LangGraph 实现 |

### 15.3 路线图

未来可能实现：

- \`WorkflowEngine\` 的 LangGraph StateGraph 封装
- \`WorkflowGraphBuilder\` 的图构建和编译
- 更多内置工具（Web Search、SQL 查询等）
- 工具注册和发现机制

***

## 附录 A：导入路径速查 {#appendix-a}

\`\`\`python
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

# ===== Conversation =====
from aigility.conversation import (
    ConversationContext, ConversationSession, ConversationSessionService,
    ConversationSessionRepository, InMemoryConversationSessionRepository,
    SessionIdGenerator, UUID4SessionIdGenerator,
)

# ===== Memory =====
from aigility.memory import (
    Memory, MemoryConfig, MemoryProviderConfig,
    MemoryIdentity, ConversationScope,
    MemoryWriteRequest, MemoryWriteResult,
    MemorySearchRequest, MemorySearchResult,
    MemoryStatus, MemoryProviderError, MemoryCapabilities,
    BaseMemoryProvider, MemoryProviderFactory,
)

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
\`\`\`

***

## 附录 B：完整示例 {#appendix-b}

### B.1 带 RAG 的完整对话流程

\`\`\`python
import asyncio
from aigility.core.config import ADKConfig
from aigility.chat.service import ChatService
from aigility.chat.schema import ChatRequest
from aigility.conversation import ConversationContext

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
        timem_kb_id="kb_my_store",      # 默认知识库；也可只在请求中传 kb_id
        llm_reasoning=False,              # 仅在所选模型支持时开启
        debug=True,
    )

    # 创建服务
    service = ChatService(adk_config=config)

    # 对话
    request = ChatRequest(
        user_input="你们支持哪些支付方式？",
        rag_used="auto",
    )
    context = ConversationContext(user_id="user-001", agent_id="sales-agent")

    # 同步调用
    response = service.process_chat(request, context=context)
    print(f"回复: {response.response}")
    print(f"会话: {response.session_id}")  # 保存它以便下次作为 request.session_id 传回
    print(f"决策: {response.thought_process}")
    print(f"原生推理: {response.reasoning_content}")
    print(f"工具: {response.tool_results}")

    # 流式续聊：回传服务端签发的 session_id。
    follow_up = ChatRequest(
        user_input="请再说明一下退款规则。",
        session_id=response.session_id,
        rag_used="auto",
    )
    async for event in service.process_chat_stream(follow_up, context=context):
        if "conversation" in event:
            print("stream session:", event["conversation"]["session_id"])
        elif "stream_response" in event:
            msg = event["stream_response"]["messages"][0]
            print(msg.additional_kwargs.get("reasoning_content") or msg.content,
                  end="", flush=True)

asyncio.run(main())
\`\`\`

### B.1.1 通过 ChatAgent 对话（更简洁）

\`\`\`python
from aigility import ADKClientBuilder

client = (
    ADKClientBuilder()
    .with_llm(
        provider="deepseek",
        model="deepseek-chat",
        api_key="sk-xxx",
        base_url="https://api.deepseek.com",
    )
    .with_rag(api_key="timem-xxx", kb_id="kb_my_store")
    .build()
)

agent = client.create_chat_agent("my_agent")

# 纯对话
response = agent.chat("你好", rag_used="off")
print(response)

# 带 RAG 的对话
response = agent.chat("你们的最小起订量是多少？", rag_used="auto")
print(response)
\`\`\`

### B.2 自定义 flow_config

\`\`\`python
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
\`\`\`
`;
