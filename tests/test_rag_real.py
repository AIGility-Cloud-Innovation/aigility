#!/usr/bin/env python3
"""真实 RAG 调用测试 — 使用 .env 中的 DeepSeek + 指定的 TimeM 凭据"""
import os
import sys

import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from aigility import ADKClientBuilder

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
TIMEM_API_KEY = os.getenv("TIMEM_API_KEY")
TIMEM_KB_ID = os.getenv("TIMEM_KB_ID")
QUERY = "箱包品类"

if not all((DEEPSEEK_API_KEY, TIMEM_API_KEY, TIMEM_KB_ID)):
    pytest.skip(
        "缺少 DEEPSEEK_API_KEY、TIMEM_API_KEY 或 TIMEM_KB_ID，跳过真实 RAG 调用测试",
        allow_module_level=True,
    )

client = (
    ADKClientBuilder()
    .with_llm(
        provider="deepseek",
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        api_key=DEEPSEEK_API_KEY,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    .with_rag(
        enabled=True,
        api_key=TIMEM_API_KEY,
        base_url="https://test.api.timem.cloud",
        kb_id=TIMEM_KB_ID,
    )
    .with_debug(enabled=True)
    .build()
)

agent = client.create_chat_agent("rag_test_agent")

# === 测试1: rag_used="auto"（使用 Builder 默认 kb_id） ===
print("=" * 80)
print("测试1: rag_used='auto', 使用 Builder 默认 kb_id")
print(f"问题: {QUERY}")
print(f"知识库: {TIMEM_KB_ID}")
print("=" * 80)
r1 = agent.chat(QUERY, rag_used="auto")
print(f"\n📝 AI 回复:\n{r1}")

# === 测试2: rag_used="on"（强制 RAG） ===
print("\n" + "=" * 80)
print("测试2: rag_used='on', 强制 RAG")
print(f"问题: {QUERY}")
print("=" * 80)
r2 = agent.chat(QUERY, rag_used="on", kb_id=TIMEM_KB_ID)
print(f"\n📝 AI 回复:\n{r2}")

# === 测试3: 不传 kb_id 应该报错 ===
print("\n" + "=" * 80)
print("测试3: rag_used='auto' 但不传 kb_id → 应抛出 ValueError")
print("=" * 80)
try:
    client2 = (
        ADKClientBuilder()
        .with_llm(
            provider="deepseek",
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            api_key=DEEPSEEK_API_KEY,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        .with_rag(enabled=True, api_key=TIMEM_API_KEY, base_url="https://api.timem.cloud")
        # 故意不设置 kb_id
        .build()
    )
    agent2 = client2.create_chat_agent("no_kb_agent")
    agent2.chat(QUERY, rag_used="auto")
    print("❌ 未抛出 ValueError — 这是 BUG！")
except ValueError as e:
    print(f"✅ 正确抛出 ValueError: {e}")

print("\n测试完成！")
