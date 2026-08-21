# todo_memory_assistant —— 记忆增强的 todo 对话 / 日报助手

最小可用示例，演示如何用 **aigility（ADK）** 把三件事串起来：

1. **todo 自然语言对话**：基于智谱 GLM-4-flash 的 `ChatAgent`，用自然语言记录当天工作。
2. **长期记忆写入**：用 aigility 的 `Memory` 模块（provider=`timem`）把每轮 todo 对话沉淀为长期记忆。
3. **记忆增强日报**：次日生成日报前，先 `retrieve` 历史记忆注入 prompt，做「引入 Memory 前后对比」。

## 依赖

```bash
pip install aigility[timem]
# 或已验证可装的独立环境：
pip install aigility timem
```

## 配置（环境变量，勿硬编码进 PR）

| 变量 | 说明 | 必填 |
|------|------|------|
| `LLM_API_KEY` | 智谱 GLM API Key | ✅ |
| `LLM_MODEL` | 默认 `glm-4-flash` | ❌ |
| `LLM_BASE_URL` | 默认 `https://open.bigmodel.cn/api/paas/v4/` | ❌ |
| `TIMEM_API_KEY` | 太忆记忆 API Key | ❌（不填走无记忆基线） |
| `TIMEM_BASE_URL` | 太忆服务地址 | ❌ |
| `TODO_USER_ID` / `TODO_SESSION_ID` | 记忆身份隔离 | ❌ |

## 运行

```bash
export LLM_API_KEY="你的智谱Key"
# 可选：开启记忆增强
export TIMEM_API_KEY="你的太忆Key"
export TIMEM_BASE_URL="https://memory.timem.cloud"

python examples/todo_memory_assistant.py
```

## 行为说明

- **LLM 部分强依赖智谱 Key**，缺失直接退出。
- **Memory 部分优雅降级**：未设置 `TIMEM_API_KEY` 时，`retrieve` 返回空、`write` 静默跳过，
  示例仍可跑通「无记忆基线」，便于本地一键验证 LLM 质量。
- 配置了 timem key 后，第 3 步的「记忆增强日报」会注入历史记忆，可在输出中观察对昨日计划的承接。

## 接入真实业务的扩展点

- 把 `agent.chat(...)` 换成你自己的 todo 服务调用（FastAPI `/daily-report` 等）。
- 用户反馈 → `client.memory.write(...)` 写入 timem，下次生成更贴合（动态 prompt 优化）。
- 多用户：用登录用户 id 作为 `USER_ID`，天然隔离记忆。
