import pytest

from aigility.chat.schema import ChatRequest
from aigility.chat.service import ChatService
from aigility.conversation import (
    ConversationContext,
    ConversationSessionOwnershipError,
    ConversationSessionService,
)


class FakeChatFlow:
    def __init__(self):
        self.invoke_calls = []
        self.stream_calls = []

    def invoke(self, **kwargs):
        self.invoke_calls.append(kwargs)
        return {
            "response": "reply",
            "thought_process": None,
            "tool_results": [],
        }

    async def astream(self, **kwargs):
        self.stream_calls.append(kwargs)
        yield {"stream_response": {"delta": "reply"}}


def make_chat_service():
    service = ChatService.__new__(ChatService)
    service.chat_flow = FakeChatFlow()
    service.session_service = ConversationSessionService()
    return service


def test_chat_creates_one_canonical_session_and_passes_it_to_flow_config():
    service = make_chat_service()
    context = ConversationContext(user_id="user-a", agent_id="agent-a")

    response = service.process_chat(ChatRequest(user_input="hello"), context)

    call = service.chat_flow.invoke_calls[0]
    configurable = call["config"]["configurable"]
    assert response.session_id.startswith("sess_")
    assert configurable["session_id"] == response.session_id
    assert configurable["thread_id"] == response.session_id
    assert service.session_service.resolve(
        response.session_id, context.user_id
    ).session_id == (response.session_id)


def test_chat_reuses_session_only_for_its_owner():
    service = make_chat_service()
    owner = ConversationContext(user_id="user-a", agent_id="agent-a")
    other_user = ConversationContext(user_id="user-b", agent_id="agent-a")
    created = service.process_chat(ChatRequest(user_input="first"), owner)

    with pytest.raises(ConversationSessionOwnershipError):
        service.process_chat(
            ChatRequest(user_input="attempt", session_id=created.session_id),
            other_user,
        )

    assert len(service.chat_flow.invoke_calls) == 1


def test_chat_response_exposes_provider_output_token_usage():
    service = make_chat_service()
    service.chat_flow.invoke = lambda **kwargs: {
        "response": "reply",
        "thought_process": None,
        "tool_results": [],
        "usage_metadata": {"output_tokens": 731},
    }

    response = service.process_chat(ChatRequest(user_input="hello"))

    assert response.usage_metadata == {"output_tokens": 731}


def test_chat_response_exposes_generation_failure_status():
    service = make_chat_service()
    service.chat_flow.invoke = lambda **kwargs: {
        "response": "抱歉，生成回复时发生错误: provider 500",
        "thought_process": None,
        "tool_results": [],
        "generation_succeeded": False,
    }

    response = service.process_chat(ChatRequest(user_input="hello"))

    assert response.generation_succeeded is False


@pytest.mark.asyncio
async def test_stream_emits_the_canonical_session_before_content_events():
    service = make_chat_service()
    context = ConversationContext(user_id="user-a", agent_id="agent-a")

    events = [
        event
        async for event in service.process_chat_stream(
            ChatRequest(user_input="hello"), context
        )
    ]

    session_id = events[0]["conversation"]["session_id"]
    configurable = service.chat_flow.stream_calls[0]["config"]["configurable"]
    assert session_id.startswith("sess_")
    assert configurable["session_id"] == session_id
    assert events[1] == {"stream_response": {"delta": "reply"}}
