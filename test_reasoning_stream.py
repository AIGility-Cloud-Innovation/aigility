"""真实 API 验证: DeepSeek V4 Flash reasoning 模式流式输出。

用法: python test_reasoning_stream.py
从 .env 读取 DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL。
"""
import asyncio
import os
import time
from dotenv import load_dotenv

load_dotenv()

from aigility.core.config import ADKConfig
from aigility.chat.service import ChatService
from aigility.chat.schema import ChatRequest

MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash-0731")

config = ADKConfig(
    llm_provider="deepseek",
    llm_model=MODEL,
    llm_api_key=os.getenv("DEEPSEEK_API_KEY"),
    llm_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    llm_reasoning=True,          # 启用 reasoning 模式
    timem_enabled=False,         # 无 TIMEM 配置, 关闭 RAG
)

service = ChatService(adk_config=config)


async def test_stream():
    print("=" * 70)
    print(f"【流式测试】model={MODEL}, llm_reasoning=True, rag_used=off")
    print("=" * 70)

    request = ChatRequest(
        user_input="9.11 和 9.9 哪个大?请仔细思考后回答。",
        session_id="reasoning-test-1",
        rag_used="off",
    )

    reasoning_chunks = 0
    content_chunks = 0
    thought_seen = False
    reasoning_buf, content_buf = [], []

    start = time.perf_counter()
    first_reasoning_at = None
    first_content_at = None

    async for event in service.process_chat_stream(request):
        if "agent_decision" in event:
            thought_seen = True
            print(f"\n[决策事件] thought={event['agent_decision'].get('thought')}")
            continue

        chunk = event["stream_response"]["messages"][0]
        rc = chunk.additional_kwargs.get("reasoning_content")
        if rc:
            if first_reasoning_at is None:
                first_reasoning_at = time.perf_counter() - start
            reasoning_chunks += 1
            reasoning_buf.append(rc)
            print(rc, end="", flush=True)
        elif chunk.content:
            if first_content_at is None:
                first_content_at = time.perf_counter() - start
                print("\n----- 正文开始 -----")
            content_chunks += 1
            content_buf.append(chunk.content)
            print(chunk.content, end="", flush=True)

    total = time.perf_counter() - start
    print("\n")
    print("-" * 70)
    print(f"决策 thought 事件: {'✅ 收到' if thought_seen else '❌ 未收到'}")
    print(f"reasoning chunks: {reasoning_chunks}  (首 chunk: {first_reasoning_at:.2f}s)" if first_reasoning_at else "reasoning chunks: 0")
    print(f"content   chunks: {content_chunks}  (首 chunk: {first_content_at:.2f}s)" if first_content_at else "content   chunks: 0")
    print(f"总耗时: {total:.2f}s")
    print(f"流式顺序: reasoning 先于正文 = {bool(first_reasoning_at and first_content_at and first_reasoning_at <= first_content_at)}")
    return thought_seen, reasoning_chunks, content_chunks


def test_invoke():
    print("\n" + "=" * 70)
    print("【非流式测试】invoke 路径 reasoning_content 字段")
    print("=" * 70)
    request = ChatRequest(
        user_input="1+1 等于几?",
        session_id="reasoning-test-2",
        rag_used="off",
    )
    resp = service.process_chat(request)
    print(f"response: {resp.response[:200]}")
    print(f"reasoning_content: {(resp.reasoning_content or 'None')[:300]}")
    print(f"thought_process: {resp.thought_process}")
    return resp.reasoning_content


async def main():
    thought_ok, n_reasoning, n_content = await test_stream()
    invoke_reasoning = test_invoke()

    print("\n" + "=" * 70)
    print("【结论】")
    print("=" * 70)
    print(f"1. 决策 thought 事件推送: {'✅' if thought_ok else '❌'}")
    print(f"2. 流式 reasoning_content: {'✅ 收到 ' + str(n_reasoning) + ' chunks' if n_reasoning else '⚠️ 模型未返回 reasoning_content(该模型可能不输出思维链)'}")
    print(f"3. 流式正文: {'✅ 收到 ' + str(n_content) + ' chunks' if n_content else '❌'}")
    print(f"4. invoke reasoning_content: {'✅' if invoke_reasoning else '⚠️ 无'}")


if __name__ == "__main__":
    asyncio.run(main())
