#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
feedback_loop —— 用户反馈优化闭环（写入 timem 长期记忆）

职责：
  - 用户对「日报 / 对话」提意见（如「昨天的日报漏了测试结论」「优先级写反了」）
    → 把这个反馈封装成 MemoryWriteRequest，写入 timem 长期记忆。
  - 下次生成日报时，todo_memory_assistant 的 recall_todo_memory 会用同一
    identity 检索到这些反馈，从而「优化」后续输出（承接用户偏好 / 纠错）。

为什么能形成闭环？
  - 写入与检索使用相同的 MemoryIdentity(user_id, agent_id)，所以反馈会进入
    同一个记忆空间，次日日报的 retrieve 能命中。
  - 写入时打 metadata.kind="feedback" + report_date，便于后续针对性检索 /
    审计（timem 支持按 scope/metadata 过滤语义检索）。

降级：若 ADK client 未启用 timem（未配 TIMEM_API_KEY），write 静默跳过，
      返回 False，不阻断主流程。
"""

import sys
from typing import Optional

# 复用回环共享的身份常量，保持写入/检索一致（避免循环 import）
from constants import USER_ID, AGENT_ID, SESSION_ID


def memory_available(client) -> bool:
    return getattr(client, "memory", None) is not None


async def write_feedback(
    client,
    feedback_text: str,
    report_date: Optional[str] = None,
    trigger: str = "daily_report",
) -> bool:
    """把用户反馈写入 timem 长期记忆。

    返回 True 表示写入成功（或已降级跳过但配置允许），False 表示未配置记忆。
    """
    if not memory_available(client):
        print("  [feedback] 未启用 timem 记忆，反馈仅本地打印，不持久化。")
        return False

    # 延迟导入，避免在无 aigility 环境直接 import 时报错
    from aigility.memory.contracts import (
        MemoryIdentity,
        ConversationScope,
        MemoryWriteRequest,
    )

    scope = ConversationScope(
        identity=MemoryIdentity(user_id=USER_ID, agent_id=AGENT_ID),
        session_id=SESSION_ID,
    )
    req = MemoryWriteRequest(
        messages=[
            {
                "role": "user",
                "content": f"[用户反馈/{trigger}] {feedback_text}",
            }
        ],
        scope=scope,
        metadata={
            "kind": "feedback",
            "trigger": trigger,
            "report_date": report_date or "",
            "source": "todo_memory_assistant.feedback_loop",
        },
    )
    result = await client.memory.write(req)
    status = getattr(result, "status", None)
    status_val = getattr(status, "value", status)
    n = len(getattr(result, "records", []) or [])
    print(f"  [feedback.write] status={status_val} records={n}")
    return True


def collect_feedback_via_input(prompt: str = "请输入你对日报/对话的反馈（留空跳过）：") -> str:
    """CLI 模式：从 stdin 收集用户反馈。返回用户输入文本（可能为空）。"""
    try:
        text = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return ""
    return text


# ----------------------------------------------------------------------------
# CLI 自测：需先有 ADK client（依赖 LLM_API_KEY + 可选 TIMEM_API_KEY）
#   用法：python feedback_loop.py
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    # build_client 定义在主示例；单独运行 feedback_loop 时把 examples/ 加入 path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from todo_memory_assistant import build_client

    if not os.getenv("LLM_API_KEY"):
        print("✗ 缺少 LLM_API_KEY，无法构造 ADK client。请先 export LLM_API_KEY=...")
        sys.exit(1)

    async def _demo():
        client = build_client()
        fb = collect_feedback_via_input("试写一条反馈（如：日报要把优先级标红）：")
        if fb:
            await write_feedback(client, fb, report_date="2026-08-22")
        else:
            print("  （无反馈，跳过写入）")
        await client.close()

    import asyncio
    asyncio.run(_demo())
