#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
server —— FastAPI 服务，把完整回环暴露为 HTTP 端点

端点：
  GET  /health            健康检查（含 memory 启用状态）
  POST /chat              对话 / 生成日报
        body: {"text": str, "mode": "todo" | "report"}
          - mode="todo"  ：todo 自然语言对话，并把本轮写入 timem 记忆
          - mode="report"：先 MySQL 召回今日 todo + 检索 timem 历史记忆，
                           再生成「记忆增强」日报
  POST /feedback          用户反馈优化（写入 timem 长期记忆）
        body: {"feedback": str, "report_date"?: str}

运行：
    export LLM_API_KEY="智谱Key"
    export TIMEM_API_KEY="太忆Key"                 # 可选
    export DATABASE_URL="mysql+pymysql://..."     # 指向 todo_db
    python server.py
    # 或：uvicorn todo_memory_assistant.server:app --host 0.0.0.0 --port 8011

依赖：fastapi uvicorn aigility sqlalchemy pymysql timem-ai
"""

import os
import sys
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# 让本包内模块可互导，同时让 examples/ 下的 todo_memory_assistant.py 也可导入
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from todo_memory_assistant import (  # noqa: E402
    build_client,
    save_todo_turn,
    recall_todo_memory,
    build_daily_report_prompt,
)
from constants import AGENT_ID  # noqa: E402  共享身份常量
from todo_retriever import retrieve_today_todos_as_text  # noqa: E402
from feedback_loop import write_feedback  # noqa: E402


# ----------------------------------------------------------------------------
# 请求 / 响应模型
# ----------------------------------------------------------------------------
class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, description="用户输入文本")
    mode: str = Field("todo", description="todo=对话, report=日报")


class ChatResponse(BaseModel):
    reply: str
    mode: str
    memory_used: bool


class FeedbackRequest(BaseModel):
    feedback: str = Field(..., min_length=1, description="用户对日报/对话的反馈")
    report_date: Optional[str] = Field(None, description="关联日报日期 YYYY-MM-DD")


class FeedbackResponse(BaseModel):
    saved: bool
    message: str


# ----------------------------------------------------------------------------
# 应用 + 单例 client
# ----------------------------------------------------------------------------
app = FastAPI(
    title="todo_memory_assistant 回环服务",
    description="MySQL 召回 + timem 记忆 + 反馈优化的 todo 对话/日报服务",
    version="1.0.0",
)

_CLIENT = None
_AGENT = None


def get_client():
    """懒加载共享 ADK client（含 timem 记忆，若配置了 key）。"""
    global _CLIENT, _AGENT
    if _CLIENT is None:
        _CLIENT = build_client()
        _AGENT = _CLIENT.create_chat_agent(AGENT_ID)
    return _CLIENT, _AGENT


@app.on_event("shutdown")
async def _shutdown():
    global _CLIENT
    if _CLIENT is not None:
        await _CLIENT.close()
        _CLIENT = None


# ----------------------------------------------------------------------------
# 端点
# ----------------------------------------------------------------------------
@app.get("/health")
async def health():
    client, _ = get_client()
    mem = getattr(client, "memory", None) is not None
    return {
        "status": "ok",
        "memory_enabled": mem,
        "agent": AGENT_ID,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    client, agent = get_client()

    if req.mode == "report":
        # 1) MySQL 召回今日 todo
        try:
            today_text = retrieve_today_todos_as_text()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"MySQL 召回失败：{exc}")
        # 2) timem 检索历史记忆（注入 prompt）
        memory_ctx = await recall_todo_memory(
            client, query="昨日计划与 todo 进展，以及用户对日报的反馈"
        )
        prompt = build_daily_report_prompt(
            today_text=today_text, memory_context=memory_ctx
        )
        reply = agent.chat(prompt, rag_used="off")
        # memory_used 反映「是否真正检索到历史记忆内容」（而非仅配置启用）
        return ChatResponse(reply=reply, mode="report", memory_used=bool(memory_ctx))

    elif req.mode == "todo":
        reply = agent.chat(req.text, rag_used="off")
        # 异步写入记忆（不阻塞响应）
        await save_todo_turn(client, req.text, reply)
        mem_on = getattr(client, "memory", None) is not None
        return ChatResponse(reply=reply, mode="todo", memory_used=mem_on)

    raise HTTPException(status_code=400, detail="mode 仅支持 todo | report")


@app.post("/feedback", response_model=FeedbackResponse)
async def feedback(req: FeedbackRequest):
    client, _ = get_client()
    saved = await write_feedback(
        client, req.feedback, report_date=req.report_date or date.today().isoformat()
    )
    if saved:
        return FeedbackResponse(saved=True, message="反馈已写入 timem 长期记忆。")
    return FeedbackResponse(
        saved=False, message="未启用 timem 记忆（缺 TIMEM_API_KEY），反馈未持久化。"
    )


# ----------------------------------------------------------------------------
# 直接运行
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8011"))
    uvicorn.run(app, host="0.0.0.0", port=port)
