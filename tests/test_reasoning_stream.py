"""CoT streaming (reasoning_content) 链路的单元测试。

使用 FakeReasoningChatModel mock LLM，不依赖真实 API，可进 CI。
覆盖：
1. _extract_stream_parts 对各家 provider 思维链格式的归一化提取
2. ChatFlow.invoke 路径：reasoning_content 透传到 flow 结果
3. ChatFlow.astream 路径：决策事件 + reasoning 增量先于正文增量
4. ChatService.process_chat 路径：reasoning_content 写入 ChatResponse
"""

from typing import Any, Iterator, List, Optional
from unittest import mock

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from aigility.chat.service import ChatService
from aigility.chat.schema import ChatRequest
from aigility.chatflow.flow import ChatFlow, _extract_stream_parts
from aigility.core.config import ADKConfig
from aigility.core.model_factory import ModelFactory


class FakeReasoningChatModel(BaseChatModel):
    """模拟推理模型：同步返回带 reasoning_content 的 AIMessage，
    流式时先吐 reasoning chunks 再吐 content chunks。"""

    reasoning: str = ""
    content: str = ""
    chunk_size: int = 4

    @property
    def _llm_type(self) -> str:
        return "fake-reasoning"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        message = AIMessage(content=self.content)
        if self.reasoning:
            message.additional_kwargs["reasoning_content"] = self.reasoning
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        for i in range(0, len(self.reasoning), self.chunk_size):
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content="",
                    additional_kwargs={
                        "reasoning_content": self.reasoning[i : i + self.chunk_size]
                    },
                )
            )
        for i in range(0, len(self.content), self.chunk_size):
            yield ChatGenerationChunk(
                message=AIMessageChunk(content=self.content[i : i + self.chunk_size])
            )


@pytest.fixture
def fake_llm():
    return FakeReasoningChatModel(
        reasoning="先分析问题，再给出结论。",
        content="最终回答：9.9 更大。",
    )


@pytest.fixture
def off_config():
    return ADKConfig(timem_enabled=False)


# ---------------------------------------------------------------------------
# 1. _extract_stream_parts 纯函数测试
# ---------------------------------------------------------------------------


class TestExtractStreamParts:
    def test_deepseek_style_reasoning_content(self):
        chunk = AIMessageChunk(
            content="", additional_kwargs={"reasoning_content": "思考中"}
        )
        reasoning, content = _extract_stream_parts(chunk)
        assert reasoning == "思考中"
        assert content == ""

    def test_plain_string_content(self):
        chunk = AIMessageChunk(content="正文增量")
        reasoning, content = _extract_stream_parts(chunk)
        assert reasoning == ""
        assert content == "正文增量"

    def test_content_blocks_reasoning_and_text(self):
        message = AIMessage(
            content=[
                {"type": "reasoning", "reasoning": "内部推理"},
                {"type": "text", "text": "最终回答"},
            ]
        )
        reasoning, content = _extract_stream_parts(message)
        assert reasoning == "内部推理"
        assert content == "最终回答"

    def test_openai_summary_style_reasoning(self):
        message = AIMessage(
            content=[
                {"type": "reasoning", "summary": [{"type": "text", "text": "摘要推理"}]},
                {"type": "text", "text": "回答"},
            ]
        )
        reasoning, content = _extract_stream_parts(message)
        assert reasoning == "摘要推理"
        assert content == "回答"

    def test_combined_additional_kwargs_and_content(self):
        chunk = AIMessageChunk(
            content="正文", additional_kwargs={"reasoning_content": "推理"}
        )
        reasoning, content = _extract_stream_parts(chunk)
        assert reasoning == "推理"
        assert content == "正文"


# ---------------------------------------------------------------------------
# 2. ChatFlow.invoke 路径
# ---------------------------------------------------------------------------


class TestChatFlowInvoke:
    def test_invoke_returns_reasoning_content(self, fake_llm, off_config):
        with mock.patch.object(ModelFactory, "create_llm", return_value=fake_llm):
            flow = ChatFlow(adk_config=off_config)
            result = flow.invoke(user_input="9.11 和 9.9 哪个大?", rag_used="off")

        assert result["response"] == fake_llm.content
        assert result["reasoning_content"] == fake_llm.reasoning
        assert result["thought_process"] == "RAG模式已关闭，不调用任何工具"

    def test_invoke_without_reasoning_returns_none(self, off_config):
        plain_llm = FakeReasoningChatModel(reasoning="", content="普通回答")
        with mock.patch.object(ModelFactory, "create_llm", return_value=plain_llm):
            flow = ChatFlow(adk_config=off_config)
            result = flow.invoke(user_input="你好", rag_used="off")

        assert result["response"] == "普通回答"
        assert result["reasoning_content"] is None


# ---------------------------------------------------------------------------
# 3. ChatFlow.astream 路径
# ---------------------------------------------------------------------------


class TestChatFlowAstream:
    async def test_reasoning_streams_before_content(self, fake_llm, off_config):
        with mock.patch.object(ModelFactory, "create_llm", return_value=fake_llm):
            flow = ChatFlow(adk_config=off_config)
            events = [
                event
                async for event in flow.astream(user_input="哪个大?", rag_used="off")
            ]

        # 决策事件一次性推送
        decision_events = [e for e in events if "agent_decision" in e]
        assert len(decision_events) == 1
        assert decision_events[0]["agent_decision"]["thought"] == "RAG模式已关闭，不调用任何工具"

        # 收集流式增量
        reasoning_deltas, content_deltas = [], []
        first_reasoning_idx = first_content_idx = None
        for idx, event in enumerate(events):
            if "stream_response" not in event:
                continue
            chunk = event["stream_response"]["messages"][0]
            rc = chunk.additional_kwargs.get("reasoning_content")
            if rc:
                if first_reasoning_idx is None:
                    first_reasoning_idx = idx
                reasoning_deltas.append(rc)
            elif chunk.content:
                if first_content_idx is None:
                    first_content_idx = idx
                content_deltas.append(chunk.content)

        # reasoning 增量完整、先于正文出现，且拼接后等于完整思维链
        assert reasoning_deltas, "应收到 reasoning 增量"
        assert content_deltas, "应收到正文增量"
        assert first_reasoning_idx < first_content_idx
        assert "".join(reasoning_deltas) == fake_llm.reasoning
        assert "".join(content_deltas) == fake_llm.content


# ---------------------------------------------------------------------------
# 4. ChatService 路径
# ---------------------------------------------------------------------------


class TestChatService:
    def test_process_chat_populates_reasoning_content(self, fake_llm, off_config):
        with mock.patch.object(ModelFactory, "create_llm", return_value=fake_llm):
            service = ChatService(adk_config=off_config)
            resp = service.process_chat(
                ChatRequest(user_input="哪个大?", session_id="t1", rag_used="off")
            )

        assert resp.response == fake_llm.content
        assert resp.reasoning_content == fake_llm.reasoning
        assert resp.thought_process == "RAG模式已关闭，不调用任何工具"

    async def test_process_chat_stream_passthrough(self, fake_llm, off_config):
        with mock.patch.object(ModelFactory, "create_llm", return_value=fake_llm):
            service = ChatService(adk_config=off_config)
            events = [
                event
                async for event in service.process_chat_stream(
                    ChatRequest(user_input="哪个大?", session_id="t2", rag_used="off")
                )
            ]

        assert any("agent_decision" in e for e in events)
        reasoning_deltas = [
            e["stream_response"]["messages"][0].additional_kwargs["reasoning_content"]
            for e in events
            if "stream_response" in e
            and e["stream_response"]["messages"][0].additional_kwargs.get(
                "reasoning_content"
            )
        ]
        assert "".join(reasoning_deltas) == fake_llm.reasoning
