#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
todo_memory_assistant —— 记忆增强的 todo 对话 / 日报助手（最小可用示例）

把三件事串起来：
  1. 用 aigility 的 ChatAgent 做「todo 自然语言对话」（基于智谱 GLM-4-flash）。
  2. 用 aigility 的 Memory 模块（provider=timem）把每日 todo 进展写入长期记忆。
  3. 次日生成日报时，先 retrieve 历史记忆注入 prompt，做「引入 Memory 前后对比」。

运行方式（推荐用环境变量注入密钥，勿硬编码）：
    export LLM_API_KEY="你的智谱Key"
    export TIMEM_API_KEY="你的太忆Key"          # 可选；不设置则走无记忆基线
    export TIMEM_BASE_URL="https://memory.timem.cloud"   # 可选；默认取 TIMEM_BASE_URL
    python examples/todo_memory_assistant.py

设计说明：
  - LLM 部分强依赖智谱 Key，必跑。
  - Memory 部分做了优雅降级：没配 TIMEM_API_KEY 时，retrieve 返回空、write 静默跳过，
    整条 demo 仍可跑通「无记忆基线」；配了就走完整记忆增强闭环。
  - 这样示例既能本地一键验证 LLM 质量，又能在有 timem key 时展示记忆承接效果。
"""

import os
import sys
import asyncio
from typing import List, Dict, Any, Optional

# 让 examples/ 直接运行也能 import aigility
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from aigility import create_client
from aigility.memory.contracts import (
    MemoryIdentity,
    ConversationScope,
    MemoryWriteRequest,
    MemorySearchRequest,
)


# ============================== 配置 ==============================
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "glm-4-flash")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")

TIMEM_API_KEY = os.getenv("TIMEM_API_KEY", "")
TIMEM_BASE_URL = os.getenv("TIMEM_BASE_URL", "")

# 记忆身份（一个固定 user + agent，真实场景按登录用户区分）
USER_ID = os.getenv("TODO_USER_ID", "demo-user-001")
AGENT_ID = "todo_memory_assistant"
SESSION_ID = os.getenv("TODO_SESSION_ID", "session-2026-08-22")


# ============================== 客户端 ==============================
def build_client():
    """构造 ADK 客户端：LLM + （可选）timem 记忆。"""
    kwargs = dict(
        llm_provider="openai",   # 智谱兼容 OpenAI 协议
        llm_model=LLM_MODEL,
        llm_api_key=LLM_API_KEY,
        llm_base_url=LLM_BASE_URL,
    )
    if TIMEM_API_KEY:
        kwargs.update(
            memory_provider="timem",
            memory_api_key=TIMEM_API_KEY,
            memory_base_url=TIMEM_BASE_URL or None,
        )
    return create_client(**kwargs)


# ============================== 记忆封装 ==============================
def memory_available(client) -> bool:
    return bool(TIMEM_API_KEY) and client.memory is not None


async def save_todo_turn(client, user_text: str, assistant_text: str) -> None:
    """把一轮 todo 对话写入长期记忆。"""
    if not memory_available(client):
        return
    scope = ConversationScope(
        identity=MemoryIdentity(user_id=USER_ID, agent_id=AGENT_ID),
        session_id=SESSION_ID,
    )
    req = MemoryWriteRequest(
        messages=[
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ],
        scope=scope,
        metadata={"source": "todo_memory_assistant"},
    )
    result = await client.memory.write(req)
    print(f"  [memory.write] status={result.status.value} "
          f"records={len(result.records)}")


async def recall_todo_memory(client, query: str) -> str:
    """检索与当日相关的历史记忆，拼成上下文文本。"""
    if not memory_available(client):
        return ""
    identity = MemoryIdentity(user_id=USER_ID, agent_id=AGENT_ID)
    req = MemorySearchRequest(query=query, identity=identity, limit=5)
    result = await client.memory.retrieve(req)
    hits = getattr(result, "records", []) or []
    if not hits:
        return ""
    lines = [f"- {getattr(h, 'content', '')}" for h in hits]
    return "\n".join(lines)


# ============================== 日报生成 ==============================
def build_daily_report_prompt(today_text: str, memory_context: str) -> str:
    base = (
        "你是一位资深的项目日报生成助手。请基于今日工作信息生成 Markdown 日报，"
        "必须包含三节：\n"
        "## 一、今日完成任务\n## 二、遇到的问题\n## 三、明日计划\n"
        "无内容标注「无」。\n\n"
        f"【今日工作信息】\n{today_text}\n"
    )
    if memory_context:
        base += (
            "\n【历史记忆（来自太忆长期记忆，请承接昨日计划，"
            "检查是否已完成/仍在推进）】\n"
            f"{memory_context}\n"
            "请在日报中体现对昨日计划的承接与回顾。\n"
        )
    else:
        base += "\n（本次未引入历史记忆，作为无记忆基线对照。）\n"
    return base


async def main():
    if not LLM_API_KEY:
        print("✗ 缺少 LLM_API_KEY，无法运行。请先 export LLM_API_KEY=你的智谱Key")
        sys.exit(1)

    print("=" * 72)
    print("  todo_memory_assistant —— 记忆增强 todo 对话 / 日报助手")
    print("=" * 72)
    print(f"  LLM: {LLM_MODEL} @ {LLM_BASE_URL}")
    print(f"  Memory(timem): {'已启用' if TIMEM_API_KEY else '未配置（走无记忆基线）'}")
    print()

    client = build_client()
    agent = client.create_chat_agent(AGENT_ID)

    # ---------- 第 1 步：今日 todo 对话 ----------
    print("[1] 今日 todo 对话（写入记忆 + 对话）")
    todo_inputs = [
        "今天我部署了服务到 Kali 服务器 111.113.25.190:40041，并写了 README 初稿。",
        "还修了一个登录接口的 422 报错，原因是 Pydantic 类型没在运行时导入。",
    ]
    today_summary_parts: List[str] = []
    for text in todo_inputs:
        reply = agent.chat(text, rag_used="off")
        today_summary_parts.append(f"用户：{text}\n助手：{reply}")
        print(f"  用户：{text}")
        print(f"  助手：{reply[:120]}{'…' if len(reply) > 120 else ''}")
        # 异步写入记忆（不阻塞对话展示）
        await save_todo_turn(client, text, reply)
    print()

    # ---------- 第 2 步：无记忆基线日报 ----------
    print("[2] 生成「无记忆基线」日报")
    baseline_prompt = build_daily_report_prompt(
        today_text="\n".join(today_summary_parts), memory_context=""
    )
    baseline_report = agent.chat(baseline_prompt, rag_used="off")
    print(baseline_report)
    print()

    # ---------- 第 3 步：记忆增强日报 ----------
    print("[3] 生成「记忆增强」日报（先 retrieve 历史记忆）")
    memory_ctx = await recall_todo_memory(
        client, query="昨日计划与 todo 进展：Kali 部署、README、登录 422 修复"
    )
    enhanced_prompt = build_daily_report_prompt(
        today_text="\n".join(today_summary_parts), memory_context=memory_ctx
    )
    enhanced_report = agent.chat(enhanced_prompt, rag_used="off")
    print(enhanced_report)
    print()

    # ---------- 第 4 步：对比观察 ----------
    print("[4] 前后对比小结")
    if memory_ctx:
        print("  ✓ 已注入历史记忆，增强版日报应体现对昨日计划的承接。")
    else:
        print("  · 未配置 TIMEM_API_KEY，两步日报同为无记忆基线（用于演示结构）。")
        print("    配置 TIMEM_API_KEY 后重跑，即可看到记忆承接差异。")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
