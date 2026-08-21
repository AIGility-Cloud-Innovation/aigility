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
# 让本目录下的子模块（todo_retriever / feedback_loop）可导入
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from aigility import create_client
from aigility.memory.contracts import (
    MemoryIdentity,
    ConversationScope,
    MemoryWriteRequest,
    MemorySearchRequest,
)

# 真实数据来源：MySQL 召回今日 todo；反馈闭环
from todo_retriever import retrieve_today_todos_as_text
from feedback_loop import write_feedback, collect_feedback_via_input
from constants import USER_ID, AGENT_ID, SESSION_ID  # 共享身份常量（单一来源）


# ============================== 配置 ==============================
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "glm-4-flash")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")

TIMEM_API_KEY = os.getenv("TIMEM_API_KEY", "")
TIMEM_BASE_URL = os.getenv("TIMEM_BASE_URL", "")


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
            "要求：请在日报中**显式引用**上述历史记忆的要点（例如"
            "「根据昨日计划/用户反馈，X 已完成 / Y 仍在推进」），"
            "体现对昨日计划的承接与回顾，不要泛泛而谈。\n"
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

    # ---------- 第 1 步：真实 MySQL 召回今日 todo ----------
    print("[1] 从 MySQL 召回今日 todo（真实 SQL 召回）")
    try:
        today_text = retrieve_today_todos_as_text()
        print(today_text)
    except Exception as exc:  # noqa: BLE001
        print(f"  ✗ MySQL 召回失败：{exc}")
        print("    请确认 DATABASE_URL 指向的 MySQL 可达且存在 todos/subtasks 表。")
        today_text = "（无法从 MySQL 召回今日 todo）"
    today_summary_parts: List[str] = [today_text]
    print()

    # ---------- 第 2 步：今日 todo 对话（写入记忆） ----------
    print("[2] 基于今日 todo 做一轮自然语言对话（写入记忆）")
    print("    可直接回车跳过；或输入一句话（如「把第1条标为已完成」）。")
    user_says = collect_feedback_via_input("  对话输入：")
    if user_says:
        reply = agent.chat(user_says, rag_used="off")
        today_summary_parts.append(f"用户：{user_says}\n助手：{reply}")
        print(f"  助手：{reply[:160]}{'…' if len(reply) > 160 else ''}")
        await save_todo_turn(client, user_says, reply)
    else:
        print("  （跳过对话）")
    print()

    # ---------- 第 3 步：记忆增强日报（先 retrieve 历史记忆） ----------
    print("[3] 生成「记忆增强」日报（先检索 timem 历史记忆注入 prompt）")
    memory_ctx = await recall_todo_memory(
        client, query="昨日计划与 todo 进展，以及用户对日报的反馈"
    )
    report_prompt = build_daily_report_prompt(
        today_text="\n".join(today_summary_parts), memory_context=memory_ctx
    )
    report = agent.chat(report_prompt, rag_used="off")
    print(report)
    print()

    # ---------- 第 4 步：用户反馈优化（写入 timem） ----------
    print("[4] 收集你对日报的反馈，写入 timem 长期记忆（形成优化闭环）")
    fb = collect_feedback_via_input("  反馈（如：日报要把优先级标红）：")
    if fb:
        await write_feedback(client, fb, report_date=__import__("datetime").date.today().isoformat())
        print("  ✓ 反馈已写入，下次日报的检索会命中并优化输出。")
    else:
        print("  （无反馈，跳过）")
    print()

    # ---------- 第 5 步：对比观察 ----------
    print("[5] 回环小结")
    if memory_ctx:
        print("  ✓ 已注入历史记忆，日报应体现对昨日计划的承接。")
    else:
        print("  · 本次 timem 未检索到历史记忆（首次运行或索引未就绪）。")
        print("    配置 TIMEM_API_KEY 且运行过一次后，次日日报即可看到记忆承接。")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
