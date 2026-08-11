# CoT Streaming 增量说明：模型原生思维链流式输出

> **对应版本：** 基于 2.0.0 的功能增量（分支 `feat/shb/0810/CoT_streaming`，提交 `6cd7c31`）
> **维护方：** AIGility Cloud Innovation
>
> 本文是《Aigility SDK (ADK) 使用文档》的**增量补充**，只讲本次「reasoning 模式模型原生 CoT 流式输出」相对之前的变化，以及 SDK 使用者需要注意的事项。基础用法请仍以主文档为准。

---

## 1. 本次变更概览

| 文件 | 变更 |
| --- | --- |
| `aigility/core/config.py` | `ADKConfig` 新增 `llm_reasoning`、`llm_reasoning_effort` 两个配置项 |
| `aigility/core/model_factory.py` | 按 `llm_reasoning` 开关透传 DeepSeek `thinking` / OpenAI `reasoning_effort` 参数 |
| `aigility/chatflow/flow.py` | 新增 `_extract_stream_parts()` 归一化提取思维链；`astream` 推送 reasoning 增量事件；invoke 路径拆分并返回 `reasoning_content`；DEBUG 日志改为 `debug` 开关控制；新增 `_explain_llm_error()` 错配友好报错 |
| `aigility/chat/schema.py` | `ChatResponse` 新增 `reasoning_content` 字段 |
| `aigility/chat/service.py` | `process_chat` 透传 `reasoning_content`；流式事件契约补充注释 |
| `aigility/chat/agent.py` | `ChatAgent.invoke()` 的 `AgentResponse.metadata` 补传 `reasoning_content`（修复遗漏入口） |
| `tests/test_reasoning_stream.py` | 新增 16 个 mock 单元测试（不进真实 API，可进 CI） |
| `test_reasoning_stream.py`（根目录） | 真实 API 手动验证脚本 |
| `examples/reasoning_demo.py` | 彩色双流演示 demo（思维链暗灰斜体 / 正文亮色） |

---

## 2. 新增能力

### 2.1 配置开关（默认关闭，向后兼容）

```python
from aigility.core.config import ADKConfig

config = ADKConfig(
    llm_provider="deepseek",
    llm_model="deepseek-v4-flash",
    llm_api_key="...",
    llm_reasoning=True,                    # 新增：开启模型原生思维链，默认 False
    # llm_reasoning_effort="medium",       # 新增：仅 OpenAI o 系列使用 "low"|"medium"|"high"
)
```

- **DeepSeek**：`llm_reasoning` 会显式映射为 `extra_body={"thinking": {"type": "enabled"/"disabled"}}`
- **OpenAI o 系列**：`llm_reasoning=True` 且设置了 `llm_reasoning_effort` 时，透传 `reasoning_effort` 参数
- 其他 OpenAI 兼容 provider：不开开关则完全不带推理参数，行为与之前一致

### 2.2 `ChatResponse` 新增字段

```python
resp = service.process_chat(request)
resp.reasoning_content   # 新增：模型原生思维链（Optional[str]，未开启/不支持时为 None）
resp.thought_process     # 原有：Agent 决策轨迹（不变）
```

### 2.3 思维链输出与开关绑定：全入口覆盖

设计原则：`llm_reasoning=True` 即**必然输出**思维链，无额外配置。各入口的消费位置：

| 入口 | 思维链位置 |
| --- | --- |
| `ChatService.process_chat` | `ChatResponse.reasoning_content` |
| `ChatService.process_chat_stream` / `ChatFlow.astream` | 流式 reasoning 增量事件 |
| `ChatFlow.invoke` | 返回 dict 的 `reasoning_content` 键 |
| `ChatAgent.invoke` | `AgentResponse.metadata["reasoning_content"]`（本次修复的遗漏入口） |

注：`ChatAgent.chat()` 是只返回 `str` 正文的最简便捷接口，有意不带思维链；需要时请用上表任一入口。

### 2.4 流式事件契约新增 reasoning 增量

`process_chat_stream` / `ChatFlow.astream` 的事件序列变为三类：

```python
async for event in service.process_chat_stream(request):
    if "agent_decision" in event:
        ...                                  # ① 决策事件（一次性）：Agent 层 thought
        continue
    chunk = event["stream_response"]["messages"][0]
    rc = chunk.additional_kwargs.get("reasoning_content")
    if rc:
        ...                                  # ② 思维链增量（0~N 次，新增）
    elif chunk.content:
        ...                                  # ③ 正文增量（0~N 次）
```

开启 reasoning 后，事件顺序保证为 **决策事件 → 思维链增量 → 正文增量**。

完整可运行示例见 `examples/reasoning_demo.py`（支持 `--ask` 单问单答、`--off` 关思维链对比）。

---

## 3. 两个"思维链"不要混淆

| | `thought_process`（原有） | `reasoning_content`（新增） |
| --- | --- | --- |
| 层级 | Agent / 应用层 | 模型 / API 层 |
| 来源 | chatflow 决策节点 + CoT prompt | 推理模型原生返回 |
| 内容 | "我决定调用 xx 工具" | 模型解题的内部推理过程 |
| 产生条件 | 任何模型、任何模式 | 需 `llm_reasoning=True` 且模型支持 |
| 流式载体 | `agent_decision` 事件（一次性） | chunk 的 `additional_kwargs["reasoning_content"]` |

两者可同时存在，互不干扰；消费方按需取用。

---

## 4. 与之前相比，使用注意事项

### ⚠️ 4.1 DeepSeek 混合推理模型的行为变化（最重要）

之前版本**不传** `thinking` 参数，DeepSeek V3.2+/V4 这类混合推理模型按 API 侧默认值走（部分模型默认开启思考）。

本版本起，`llm_reasoning=False` 会**显式传 `thinking: disabled`**：

- 升级后如果**没有**显式设置 `llm_reasoning=True`，之前"默认带思维链"的模型将**不再返回**思维链
- 想要思维链，必须显式开启 `llm_reasoning=True`

这是有意为之（保证行为与配置一致），但属于可感知的行为变化，升级后请确认。

### 4.2 模型名限制

DeepSeek API 目前只接受 `deepseek-v4-pro` / `deepseek-v4-flash`，带日期后缀的别名（如 `deepseek-v4-flash-0731`）会被 400 拒绝。如遇 `invalid_request_error` 报模型名，先检查这一项。

### 4.3 移除 StrOutputParser 的影响（仅影响深度定制用户）

`_prepare_for_generation` 构建的 chain 不再接 `StrOutputParser`（parser 会把流式 chunk 压成纯字符串，导致 `reasoning_content` 丢失）。现在 chain 直接返回 `AIMessage` / `AIMessageChunk`。

对标准用法（`ChatService` / `ChatFlow` 公开接口）**无影响**；但如果你之前自行消费过 state 中的 `chain` 并假设输出是 `str`，需要改为从 `.content` / `.additional_kwargs` 取值。

### 4.4 开关与模型能力必须匹配

SDK **不做**模型能力校验，`llm_reasoning` 与模型能力错配时由 API 侧报错或产生非预期行为：

| 模型类型 | `llm_reasoning=True` | `llm_reasoning=False`（默认） |
| --- | --- | --- |
| 混合推理模型（`deepseek-v4-flash` / `deepseek-v4-pro`） | ✅ 思考 + 回答双流输出 | ✅ 显式禁用思考，纯回答 |
| 普通模型（`gpt-4o`、GLM、通义等） | ⚠️ 可能 400：API 不识别推理参数（DeepSeek 系下发 `thinking`；OpenAI 系在设了 `llm_reasoning_effort` 时下发 `reasoning_effort`） | ✅ 正常（DeepSeek 系仍会下发 `disabled`） |
| 纯推理模型（`deepseek-reasoner`、o1 等） | ✅ 正常 | ⚠️ 思考关不掉：模型侧强制思考，仍返回 `reasoning_content`，**计费含思考 token** |

排障指引：遇到 `400 invalid_request_error` / `unsupported parameter` 类报错，首先检查开关与模型是否匹配。**SDK 已内置识别**：`_explain_llm_error()` 会识别思维链参数相关的 400 错误，自动在报错信息后追加排障提示（覆盖 `_agent_decision` / `_stream_response` / `astream` 三处 LLM 调用入口），无需用户自行对照矩阵排查。

### 4.5 DEBUG 流式日志需要显式开启

`ChatFlow.astream` 里的 `DEBUG [astream]` 系列日志（节点完成、逐 chunk 内容等）从无条件输出改为 `ADKConfig(debug=True)` 时才打印。升级后如果觉得"流式过程变安静了"，是正常的；需要排查时传 `debug=True` 即可恢复。错误信息（`LLM streaming error` / `Graph error`）不受开关影响，始终输出。

### 4.6 Provider 思维链格式支持矩阵

`_extract_stream_parts()` 已归一化以下三种承载方式，消费方无需关心差异：

| Provider 风格 | 承载方式 | 示例 |
| --- | --- | --- |
| DeepSeek | `additional_kwargs["reasoning_content"]` | deepseek-reasoner / v4 系列 |
| 标准 content blocks | `content` 列表中 `type=="reasoning"` 的块 | Claude extended thinking 等 |
| OpenAI responses API | reasoning 块的 `summary` 列表 | o 系列 |

未列出的 provider：只要走 LangChain 标准消息格式返回思维链，一般也能被接住；否则 `reasoning_content` 为空，不影响正文。

### 4.7 兼容性总结

- `llm_reasoning` 默认 `False`，`reasoning_content` 为 `Optional[str]`（默认 `None`）——**不开开关，一切行为与之前一致**（除 4.1 的 DeepSeek 显式 disabled）
- `ChatResponse` 只新增字段，未改动/删除任何既有字段，反序列化旧数据不受影响
- 流式契约只新增事件类型，既有 `agent_decision` / 正文 chunk 事件的格式不变

---

## 5. 验证方式

```bash
# 单元测试（mock LLM，可进 CI，16 个用例）
python -m pytest tests/test_reasoning_stream.py -q

# 真实 API 手动验证（需 .env 配置 DEEPSEEK_API_KEY）
python test_reasoning_stream.py

# 直观演示（彩色双流对比）
python examples/reasoning_demo.py --ask "9.11 和 9.9 哪个大?"
python examples/reasoning_demo.py --ask "9.11 和 9.9 哪个大?" --off   # 关思维链对比
```

本次交付前已验证：16 个单元测试全过；真实 API 下思维链开（91 reasoning chunks 先于正文）/ 关（无思考环节）行为均符合预期。
