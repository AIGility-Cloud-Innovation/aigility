"""CoT streaming 直观演示：思维链(暗灰斜体)与正文(亮色)双流实时输出。

用法:
    python examples/reasoning_demo.py                # 交互式多轮对话
    python examples/reasoning_demo.py --ask "9.11和9.9哪个大?"   # 单问单答
    python examples/reasoning_demo.py --off          # 关闭思维链(对比用)

从 .env 读取 DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL。
"""
import argparse
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from aigility.core.config import ADKConfig
from aigility.chat.service import ChatService
from aigility.chat.schema import ChatRequest

# ANSI 颜色
GRAY_ITALIC = "\033[90m\033[3m"   # 暗灰 + 斜体: 思维链
BRIGHT = "\033[97m\033[1m"        # 亮白加粗: 正文
CYAN = "\033[36m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def make_service(reasoning: bool) -> ChatService:
    config = ADKConfig(
        llm_provider="deepseek",
        llm_model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        llm_api_key=os.getenv("DEEPSEEK_API_KEY"),
        llm_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        llm_reasoning=reasoning,
        timem_enabled=False,
    )
    return ChatService(adk_config=config)


async def chat_once(service: ChatService, question: str, session_id: str):
    request = ChatRequest(user_input=question, session_id=session_id, rag_used="off")

    print(f"\n{CYAN}🧑 你:{RESET} {question}\n")

    in_reasoning = False
    in_content = False
    n_reasoning = n_content = 0
    t0 = time.perf_counter()
    t_first_reasoning = t_first_content = None

    async for event in service.process_chat_stream(request):
        if "agent_decision" in event:
            thought = event["agent_decision"].get("thought")
            print(f"{YELLOW}⚙ 决策: {thought}{RESET}")
            continue

        chunk = event["stream_response"]["messages"][0]
        rc = chunk.additional_kwargs.get("reasoning_content")
        if rc:
            if not in_reasoning:
                print(f"{GRAY_ITALIC}💭 思考中...\n{RESET}{GRAY_ITALIC}", end="")
                in_reasoning = True
                t_first_reasoning = time.perf_counter() - t0
            n_reasoning += 1
            print(rc, end="", flush=True)
        elif chunk.content:
            if in_reasoning:
                print(f"{RESET}")  # 结束思维链的灰色
                in_reasoning = False
            if not in_content:
                print(f"{BRIGHT}🤖 回答:\n{RESET}{BRIGHT}", end="")
                in_content = True
                t_first_content = time.perf_counter() - t0
            n_content += 1
            print(chunk.content, end="", flush=True)

    print(RESET)
    total = time.perf_counter() - t0
    stats = [f"{n_reasoning} 思考 chunks", f"{n_content} 正文 chunks", f"总耗时 {total:.1f}s"]
    if t_first_reasoning is not None:
        stats.append(f"首个思考 chunk {t_first_reasoning:.1f}s")
    if t_first_content is not None:
        stats.append(f"首个正文 chunk {t_first_content:.1f}s")
    print(f"{CYAN}── {' | '.join(stats)} ──{RESET}")


async def main():
    parser = argparse.ArgumentParser(description="CoT streaming 直观演示")
    parser.add_argument("--ask", help="单问单答模式")
    parser.add_argument("--off", action="store_true", help="关闭思维链(对比用)")
    args = parser.parse_args()

    reasoning = not args.off
    service = make_service(reasoning)
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    print(f"{CYAN}model={model} | 思维链={'开 ✅' if reasoning else '关 ❌'} "
          f"| 输入 quit 退出{RESET}")

    if args.ask:
        await chat_once(service, args.ask, session_id="demo-oneshot")
        return

    session_id = f"demo-{int(time.time())}"
    while True:
        try:
            question = input(f"\n{CYAN}>{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in ("quit", "exit", ""):
            break
        await chat_once(service, question, session_id)


if __name__ == "__main__":
    asyncio.run(main())
