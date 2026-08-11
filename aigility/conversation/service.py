"""Conversation lifecycle service.

This is the single authority that creates canonical session IDs and verifies
ownership before chat or memory code can use them.
"""

from datetime import datetime, timezone
from typing import Callable, Optional

from .contracts import (
    ConversationSession,
    ConversationSessionConflictError,
    ConversationSessionNotFoundError,
    ConversationSessionOwnershipError,
    normalize_identifier,
    normalize_optional_identifier,
)
from .id_generator import SessionIdGenerator, UUID4SessionIdGenerator
from .repository import (
    ConversationSessionRepository,
    InMemoryConversationSessionRepository,
)


def utc_now() -> datetime:
    """Return an aware UTC timestamp for session lifecycle records."""

    return datetime.now(timezone.utc)


class ConversationSessionService:
    """Create, resolve, authorize, and touch canonical conversation sessions."""

    def __init__(
        self,
        repository: Optional[ConversationSessionRepository] = None,
        id_generator: Optional[SessionIdGenerator] = None,
        clock: Callable[[], datetime] = utc_now,
        max_id_generation_attempts: int = 3,
    ) -> None:
        if max_id_generation_attempts < 1:
            raise ValueError("max_id_generation_attempts 必须大于 0")

        self._repository = repository or InMemoryConversationSessionRepository()
        self._id_generator = id_generator or UUID4SessionIdGenerator()
        self._clock = clock
        self._max_id_generation_attempts = max_id_generation_attempts

    def create(
        self, user_id: str, idempotency_key: Optional[str] = None
    ) -> ConversationSession:
        """Create one server-issued session for a user.

        A client-provided idempotency key can safely repeat a create request,
        but it never controls the generated session identifier.
        """

        normalized_user_id = normalize_identifier(user_id, "user_id")
        normalized_key = normalize_optional_identifier(idempotency_key)

        if normalized_key:
            existing = self._repository.find_by_idempotency_key(
                normalized_user_id, normalized_key
            )
            if existing is not None:
                return existing

        for _ in range(self._max_id_generation_attempts):
            now = self._clock()
            session = ConversationSession(
                session_id=normalize_identifier(
                    self._id_generator.new_id(), "生成的 session_id"
                ),
                user_id=normalized_user_id,
                created_at=now,
                updated_at=now,
                idempotency_key=normalized_key,
            )
            try:
                return self._repository.create(session)
            except ConversationSessionConflictError:
                # A UUID collision is exceptionally unlikely, but a repository
                # may also use this signal for a concurrent insertion race.
                if normalized_key:
                    existing = self._repository.find_by_idempotency_key(
                        normalized_user_id, normalized_key
                    )
                    if existing is not None:
                        return existing

        raise ConversationSessionConflictError("无法生成未冲突的 session_id")

    def resolve(self, session_id: str, user_id: str) -> ConversationSession:
        """Resolve a canonical session and verify its owning user."""

        normalized_session_id = normalize_identifier(session_id, "session_id")
        normalized_user_id = normalize_identifier(user_id, "user_id")
        session = self._repository.get(normalized_session_id)
        if session is None:
            raise ConversationSessionNotFoundError("session_id 不存在")
        if session.user_id != normalized_user_id:
            raise ConversationSessionOwnershipError("当前用户无权访问该 session_id")
        return session

    def resolve_or_create(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> ConversationSession:
        """Resolve a supplied server-issued ID or create a new session."""

        if session_id is not None:
            return self.resolve(session_id=session_id, user_id=user_id)
        return self.create(user_id=user_id, idempotency_key=idempotency_key)

    def touch(self, session_id: str) -> ConversationSession:
        """Record successful activity without changing session identity."""

        normalized_session_id = normalize_identifier(session_id, "session_id")
        return self._repository.touch(normalized_session_id, self._clock())
