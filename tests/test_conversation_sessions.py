import pytest

from aigility.conversation import (
    ConversationContext,
    ConversationSessionNotFoundError,
    ConversationSessionOwnershipError,
    ConversationSessionService,
)
from aigility.memory.contracts import ConversationScope, MemoryIdentity


def test_session_id_is_globally_unique_and_does_not_embed_user_identity():
    service = ConversationSessionService()

    first = service.create("user-a")
    second = service.create("user-a")

    assert first.session_id.startswith("sess_")
    assert first.session_id != second.session_id
    assert "user-a" not in first.session_id
    assert "user-a" not in second.session_id


def test_existing_session_is_resolved_by_its_own_id():
    service = ConversationSessionService()
    created = service.create("user-a")

    resolved = service.resolve_or_create("user-a", session_id=created.session_id)

    assert resolved == created


def test_session_owner_is_checked_without_becoming_part_of_the_id():
    service = ConversationSessionService()
    created = service.create("user-a")

    with pytest.raises(ConversationSessionOwnershipError):
        service.resolve(created.session_id, "user-b")


def test_client_cannot_invent_an_unknown_session_id():
    service = ConversationSessionService()

    with pytest.raises(ConversationSessionNotFoundError):
        service.resolve_or_create("user-a", session_id="sess_client_supplied")


def test_create_is_idempotent_without_making_the_key_the_session_id():
    service = ConversationSessionService()

    first = service.create("user-a", idempotency_key="create-001")
    retried = service.create("user-a", idempotency_key="create-001")

    assert retried.session_id == first.session_id
    assert retried.session_id != "create-001"


def test_conversation_context_keeps_agent_out_of_session_identity():
    context = ConversationContext(user_id="user-a", agent_id="assistant-a")
    session = ConversationSessionService().create(context.user_id)

    assert session.user_id == context.user_id
    assert context.agent_id not in session.session_id


def test_canonical_session_id_passes_to_memory_scope_without_rewriting():
    context = ConversationContext(user_id="user-a", agent_id="assistant-a")
    session = ConversationSessionService().create(context.user_id)

    scope = ConversationScope(
        identity=MemoryIdentity(
            user_id=context.user_id,
            agent_id=context.agent_id,
        ),
        session_id=session.session_id,
    )

    assert scope.session_id == session.session_id
    assert scope.identity.user_id == context.user_id
    assert scope.identity.agent_id == context.agent_id
