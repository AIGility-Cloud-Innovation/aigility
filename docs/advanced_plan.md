# 中期补全 Plan：修复 SDK 公共 API 表面

## Context

SDK 存在"公共 API 表面"（`ChatAgent`、`create_llm()`、`ADKClient`）全是脚手架不能用，而"实际工作实现"（`ChatService` → `ChatFlow` → `ModelFactory`）完整可用但没通过 `ADKClient` 暴露的问题。外部项目当前直接使用 `ChatFlow`，补全后不影响现有用法。

## 目标

让 `ADKClient` 成为一个真正可用的统一入口，同时保持向后兼容（外部项目直接用 `ChatFlow` 的方式不受影响）。

---

## Step 1：实现 ChatAgent.invoke() — 委托 ChatFlow

**文件：** `aigility/chat/agent.py`

**改动：**
- `ChatAgent.__init__` 新增 `adk_config: ADKConfig` 参数
- 内部创建 `ChatFlow` 实例（懒加载或构造时创建）
- `invoke()` 方法接受简化的参数（`user_input: str`），内部调用 `ChatFlow.invoke()`
- 保持 `State` / `AgentResponse` 兼容：接受 `State` 时提取 `user_input`，返回时包装为 `AgentResponse`

**关键决策：** `invoke()` 签名设计
- 方案 A：保持抽象接口 `invoke(state: State) -> AgentResponse`，内部转换
- 方案 B：新增便捷方法 `chat(user_input: str) -> str`，原 `invoke()` 保留为内部实现

**选择方案 A**，原因：保持与 `BaseAgent` 抽象接口一致，`create_chat_agent()` 返回的实例可以统一调用。

```python
async def invoke(self, state: State) -> AgentResponse:
    # 从 State 中提取 user_input
    user_input = state.messages[-1].content if state.messages else ""
    result = self._chat_flow.invoke(user_input=user_input, rag_used="auto")
    return AgentResponse(
        content=result["response"],
        metadata={"thought_process": result.get("thought_process"), "tool_results": result.get("tool_results")}
    )
```

同时新增同步便捷方法：
```python
def chat(self, user_input: str, rag_used: str = "auto") -> str:
    result = self._chat_flow.invoke(user_input=user_input, rag_used=rag_used)
    return result["response"]
```

---

## Step 2：修复 ADKClient 配置传递

**文件：** `aigility/client.py`

**改动：**
- `create_chat_agent()` 将 `self.config`（`ADKConfig`）传给 `ChatAgent`
- `create_chatflow()` 将 `self.config` 传给 `ChatFlow`（当前已传 `name` 但没传 `adk_config`）

```python
def create_chat_agent(self, name: str, **kwargs) -> ChatAgent:
    from .chat import create_chat_agent
    return create_chat_agent(name=name, adk_config=self.config, **kwargs)

def create_chatflow(self, name: str, **kwargs) -> ChatFlow:
    from .chatflow import create_chatflow
    return create_chatflow(name=name, adk_config=self.config, **kwargs)
```

---

## Step 3：修复 create_llm() — 转发到 ModelFactory

**文件：** `aigility/model/llm.py`

**改动：**
- `create_llm()` 内部构造 `ADKConfig`，转发到 `ModelFactory.create_llm()`
- 保持原有函数签名不变（`provider`, `model`, `api_key`, `base_url`, `**kwargs`）
- 返回类型改为 `Any`（实际是 LangChain LLM 实例），不再返回 `LLMProvider`

```python
def create_llm(provider="openai", model="gpt-4", api_key=None, base_url=None, **kwargs):
    from ..core.config import ADKConfig
    from ..core.model_factory import ModelFactory
    config = ADKConfig(
        llm_provider=provider, llm_model=model,
        llm_api_key=api_key, llm_base_url=base_url,
        llm_temperature=kwargs.get("temperature", 0.7),
        llm_max_tokens=kwargs.get("max_tokens", 2000),
    )
    return ModelFactory.create_llm(config)
```

---

## Step 4：更新文档

**文件：** `docs/use_sdk.md`

**改动：**
- 更新 `ADKClient` 章节（第 5 节），新增 `ChatAgent` 可用的示例
- 更新 `ChatAgent` 章节（第 6 节），标注已实现
- 更新附录 A 导入路径，移除 `⚠️ 未实现` 标注
- 更新第 15 节已知限制，移除已修复的条目

---

## Step 5：更新 __init__.py 导出

**文件：** `aigility/__init__.py`

**改动：**
- 确认 `ADKClientBuilder` 已导出（当前只有 `ADKClient` 和 `create_client`）
- 确认 `create_llm` 从 `aigility.model` 可导入

---

## 不改动的部分（向后兼容保证）

- `ChatFlow` 的构造函数和调用签名**不变**
- `ChatService` 的构造函数和调用签名**不变**
- `ModelFactory.create_llm()` 的行为**不变**
- `ADKConfig` 的字段**不变**
- 外部项目直接用 `ChatFlow(adk_config=...)` 的方式**不受影响**

---

## 验证方式

1. **单元验证：** 写一个简单脚本，通过 `ADKClient` 创建 `ChatAgent`，调用 `chat("你好")`，验证能拿到模型响应
2. **向后兼容验证：** 外部项目现有的 `ChatFlow` 用法不报错
3. **配置传递验证：** 通过 `ADKClientBuilder` 设置 `temperature=0.1`，验证模型实际使用该值
