# todo_memory_assistant —— 记忆增强的 todo 对话 / 日报回环（完整可运行版）

把 **aigility（ADK）** 的 LLM 对话、MySQL 真实数据召回、TiMEM 长期记忆、用户反馈优化
串成一条**端到端可运行**的回环，覆盖四个能力：

| 能力 | 实现 | 状态 |
|------|------|------|
| 1. todo 自然语言对话 | `client.create_chat_agent` + 智谱 GLM-4-flash | ✅ |
| 2. **MySQL 真实召回今日 todo** | `todo_retriever.py` 直连 `todo_db` | ✅（接 SQL，非写死） |
| 3. **引入 Memory 真实验证** | `client.memory.write/retrieve`（timem provider，已用真实 key 验证 write=SUCCESS / retrieve 命中） | ✅ |
| 4. **用户反馈优化** | `feedback_loop.py` 把反馈写回 timem，下次日报检索命中 | ✅ |

## 目录结构

```
examples/todo_memory_assistant/
├── todo_retriever.py          # MySQL 召回今日 todos/subtasks（独立可运行）
├── feedback_loop.py           # 用户反馈 → 写入 timem（优化闭环）
├── server.py                  # FastAPI 服务：/chat + /feedback + /health
├── constants.py               # 共享身份常量（避免循环 import）
├── todo_memory_assistant.py   # CLI 主流程（串起整条回环，位于 examples/ 下）
├── requirements.txt
└── todo_memory_assistant_README.md
```

> 注：`todo_retriever.py` 用「同构轻量 SQLAlchemy 模型」映射
> `fastapi_todo_refactored/app/models/{todo,subtask}.py` 的同一套表
> （`todos` / `subtasks`），不把整个后端作为子依赖，保持示例自包含。

## 依赖

```bash
# aigility 根依赖 + 回环专用
pip install -r examples/todo_memory_assistant/requirements.txt
# 含：sqlalchemy pymysql timem-ai fastapi uvicorn
```

## 配置（环境变量，勿硬编码进 PR）

| 变量 | 说明 | 必填 |
|------|------|------|
| `LLM_API_KEY` | 智谱 GLM API Key | ✅ |
| `LLM_MODEL` | 默认 `glm-4-flash` | ❌ |
| `LLM_BASE_URL` | 默认 `https://open.bigmodel.cn/api/paas/v4/` | ❌ |
| `TIMEM_API_KEY` | 太忆记忆 API Key | ❌（不填走无记忆基线） |
| `TIMEM_BASE_URL` | 太忆服务地址，默认 `https://api.timem.cloud` | ❌ |
| `DATABASE_URL` | MySQL 连接串，如 `mysql+pymysql://user:pass@host:3306/todo_db?charset=utf8mb4` | ✅（回环数据来源） |
| `TODO_USER_ID` / `TODO_SESSION_ID` | 记忆身份隔离 | ❌ |

## 运行方式

### A. CLI 完整回环

```bash
export LLM_API_KEY="你的智谱Key"
export TIMEM_API_KEY="你的太忆Key"                 # 可选
export DATABASE_URL="mysql+pymysql://.../todo_db"  # 指向真实 todo_db
python examples/todo_memory_assistant.py
```

流程：① MySQL 召回今日 todo → ② 可选对话（写入记忆）→ ③ 记忆增强日报 →
④ 收集反馈写入 timem → ⑤ 回环小结。

### B. FastAPI 服务

```bash
export LLM_API_KEY="..." TIMEM_API_KEY="..." DATABASE_URL="..."
python examples/todo_memory_assistant/server.py
# 或：uvicorn todo_memory_assistant.server:app --host 0.0.0.0 --port 8011
```

端点：

- `GET  /health`     健康检查（含 `memory_enabled`）
- `POST /chat`       `{"text": "...", "mode": "todo"|"report"}`
  - `mode="todo"`：对话，并把本轮写入 timem 记忆
  - `mode="report"`：先 MySQL 召回今日 todo + 检索 timem 历史记忆 → 生成日报
- `POST /feedback`   `{"feedback": "...", "report_date"?: "YYYY-MM-DD"}` → 写回 timem

## 验证记录（真实 key 跑通）

- MySQL 召回：本机 `todo_db` 插入今日 3 条 todo + 2 subtask，`retrieve_today_todos_as_text()` 正确返回。
- timem 写入：`client.memory.write` 返回 `status=SUCCESS, records=1`。
- timem 检索：写入后检索返回命中记录（字段 `content` 为 timem 自动摘要），`/chat report` 的 `memory_used=True`。
- 反馈闭环：`/feedback` 写入后，后续 `/chat report` 检索命中，日报出现对历史计划的承接段落。

## 注意事项

- **timem 语义索引有延迟**：刚写入的记忆可能需等待数秒才可被检索命中（演示时写入后稍候再查）。
- **记忆身份隔离**：`USER_ID` / `AGENT_ID` 相同才会命中同一记忆空间；多用户请用登录 id 区分。
- **降级**：未配 `TIMEM_API_KEY` 时，记忆读写静默跳过，回环仍以「MySQL 召回 + LLM 日报」跑通。
