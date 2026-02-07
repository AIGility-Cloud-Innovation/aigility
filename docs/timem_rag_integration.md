# 太忆 (TimeM) RAG 集成指南

本文档介绍如何在 aigility 项目中使用太忆云 RAG 服务。

## 配置说明

### 1. 环境变量配置

在 `.env` 文件或环境变量中设置以下配置：

```bash
# 太忆 RAG 云服务配置
TIMEM_ENABLED=true                    # 启用太忆 RAG 服务
TIMEM_BASE_URL=https://api.timem.cloud  # 太忆 API 基础 URL
TIMEM_API_KEY=your-api-key-here       # 太忆 API Key
```

### 2. 代码配置

```python
from aigility.core.config import ADKConfig
from aigility.chat.service import ChatService

# 方式 1: 通过环境变量配置
config = ADKConfig(
    timem_enabled=True,
    timem_base_url="https://api.timem.cloud",
    timem_api_key="your-api-key-here"
)

# 方式 2: 直接从环境变量读取（推荐）
# 只要设置了 TIMEM_ENABLED、TIMEM_BASE_URL 和 TIMEM_API_KEY 环境变量
# ADKConfig 会自动读取
config = ADKConfig()

# 创建 ChatService
chat_service = ChatService(adk_config=config)

# 使用聊天服务
response = chat_service.process_chat(
    ChatRequest(
        user_input="查询已上传文档中的信息",
        session_id="session-123"
    )
)

print(response.response)
```

## 工作原理

### 架构流程

1. **ChatFlow** 接收用户输入
2. **Agent Decision** 节点使用 LLM 判断是否需要调用 RAG 工具
3. 如果需要，**Tool Executor** 节点调用 `TimeMRAGClient`
4. **TimeMRAGClient** 通过 HTTP API 调用太忆云服务
5. 返回搜索结果并整合到最终回复中

### 状态图

```
用户输入
    ↓
Agent Decision (LLM 判断是否需要工具)
    ↓
    ├─→ 需要工具 → Tool Executor (调用太忆 RAG)
    │                  ↓
    └─→ 不需要工具 → Prepare for Generation
                          ↓
                   Stream Response (生成最终回复)
                          ↓
                       END
```

## 工具说明

### TimeMRAGTool

- **工具名**: `TimeMRAGTool`
- **用途**: 搜索太忆云服务中的知识库文档
- **参数**:
  - `query` (str): 搜索查询语句

### 使用示例

```python
from aigility.chatflow.schema import TimeMRAGTool

tool = TimeMRAGTool(
    query="人工智能的发展历史"
)
```

## API 接口

太忆 RAG 客户端实现了以下接口：

### 1. 搜索知识库

```python
from aigility.rag import create_timem_rag_client

client = create_timem_rag_client(
    base_url="https://api.timem.cloud",
    api_key="your-api-key"
)

# 异步搜索（需要指定知识库 kb_id）
result = await client.search(query="搜索内容", kb_id="kb_xxx")

# 同步搜索（需要指定知识库 kb_id）
result = client.search_sync(query="搜索内容", kb_id="kb_xxx")
```

### 2. 健康检查

```python
is_healthy = await client.health_check()
```

### 3. 获取统计信息

```python
stats = await client.get_stats()
```

### 4. 清空知识库

```python
result = await client.clear_knowledge_base()
```

## 文件结构

```
aigility/
├── core/
│   └── config.py          # ADKConfig 配置（包含 timem_* 配置项）
├── chatflow/
│   ├── flow.py            # ChatFlow 实现（集成 TimeMRAGClient）
│   ├── schema.py          # TimeMRAGTool 工具定义
│   └── prompts/
│       └── assistant.yaml  # Prompt 配置
├── rag/
│   └── client.py          # TimeMRAGClient 实现
└── chat/
    └── service.py         # ChatService (使用 ChatFlow)
```

## 禁用 RAG 服务

如果不需要使用太忆 RAG 服务，可以设置：

```python
config = ADKConfig(timem_enabled=False)
```

或者不设置 `timem_base_url` 和 `timem_api_key`，系统会自动跳过工具调用。

## 故障排查

### 1. 工具未被调用

- 检查 `timem_enabled` 是否为 `True`
- 检查 `timem_base_url` 和 `timem_api_key` 是否正确设置
- 查看日志中的 `[ADK]` 标记，确认 Agent Decision 是否正常工作

### 2. API 调用失败

- 确认网络连接正常
- 检查 API Key 是否有效
- 使用 `client.health_check()` 测试服务可用性

### 3. 搜索结果为空

- 确认已上传文档到太忆知识库
- 尝试使用不同的查询语句
- 检查搜索日志确认 API 请求是否成功

## 扩展

### 添加新的工具

如果需要添加其他 RAG 工具，可以参考 `TimeMRAGTool` 的实现：

1. 在 `schema.py` 中定义新的工具类
2. 在 `flow.py` 的 `_tool_executor` 中添加处理逻辑
3. 在 `assistant.yaml` 中添加工具说明

### 自定义 Prompt

修改 `assistant.yaml` 中的 prompt 来自定义 Agent 的行为：

- `agent_decision_prompt`: 控制 Agent 如何决策是否调用工具
- `final_response_prompt`: 控制最终回复的生成方式
