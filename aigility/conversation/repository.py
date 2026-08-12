"""Storage seam for canonical conversation sessions."""

from dataclasses import replace
from datetime import datetime
from threading import RLock
from typing import Dict, Optional, Protocol, Tuple

from .contracts import ConversationSession, ConversationSessionConflictError


class ConversationSessionRepository(Protocol):
    """Persistence contract; applications can supply a database-backed adapter."""

    def create(self, session: ConversationSession) -> ConversationSession:
        """Persist a newly generated session or return an idempotent existing one."""

    def get(self, session_id: str) -> Optional[ConversationSession]:
        """Look up a session by its canonical identifier."""

    def find_by_idempotency_key(
        self, user_id: str, idempotency_key: str
    ) -> Optional[ConversationSession]:
        """Find a session created by a retried create request."""

    def touch(self, session_id: str, updated_at: datetime) -> ConversationSession:
        """Record activity for an existing session."""


class InMemoryConversationSessionRepository:
    """Thread-safe process-local repository for SDK and test use.

    Production applications should inject a durable implementation of
    :class:`ConversationSessionRepository`; this adapter intentionally makes no
    claim of surviving a process restart.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: Dict[str, ConversationSession] = {}
        self._idempotency_index: Dict[Tuple[str, str], str] = {}

    def create(self, session: ConversationSession) -> ConversationSession:
        with self._lock:
            if session.idempotency_key:
                key = (session.user_id, session.idempotency_key)
                existing_id = self._idempotency_index.get(key)
                if existing_id:
                    return self._sessions[existing_id]

            if session.session_id in self._sessions:
                raise ConversationSessionConflictError(
                    "session_id 已存在，无法创建重复会话"
                )

            self._sessions[session.session_id] = session
            if session.idempotency_key:
                self._idempotency_index[(session.user_id, session.idempotency_key)] = (
                    session.session_id
                )
            return session

    def get(self, session_id: str) -> Optional[ConversationSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def find_by_idempotency_key(
        self, user_id: str, idempotency_key: str
    ) -> Optional[ConversationSession]:
        with self._lock:
            session_id = self._idempotency_index.get((user_id, idempotency_key))
            return self._sessions.get(session_id) if session_id else None

    def touch(self, session_id: str, updated_at: datetime) -> ConversationSession:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise ConversationSessionConflictError("会话不存在，无法更新活动时间")
            updated = replace(session, updated_at=updated_at)
            self._sessions[session_id] = updated
            return updated
