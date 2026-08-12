"""Vendor-neutral conversation identity and session contracts.

The session identifier is deliberately opaque and globally unique.  A user
owns a session, but the user identifier is never part of the session ID.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


def normalize_identifier(value: Any, field_name: str) -> str:
    """Return a required, normalized identifier."""

    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} 必须提供")
    return normalized


def normalize_optional_identifier(value: Optional[Any]) -> Optional[str]:
    """Return ``None`` or a normalized optional identifier."""

    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


@dataclass(frozen=True)
class ConversationContext:
    """Trusted caller context for one chat request.

    ``user_id`` must come from the authentication boundary instead of an
    untrusted request body.  ``agent_id`` scopes agent-specific capabilities
    such as memory, but it does not participate in session identity.
    """

    user_id: str
    agent_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "user_id", normalize_identifier(self.user_id, "user_id")
        )
        object.__setattr__(
            self, "agent_id", normalize_identifier(self.agent_id, "agent_id")
        )


@dataclass(frozen=True)
class ConversationSession:
    """A durable conversation record identified only by ``session_id``."""

    session_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    idempotency_key: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "session_id",
            normalize_identifier(self.session_id, "session_id"),
        )
        object.__setattr__(
            self, "user_id", normalize_identifier(self.user_id, "user_id")
        )
        object.__setattr__(
            self,
            "idempotency_key",
            normalize_optional_identifier(self.idempotency_key),
        )


class ConversationSessionError(RuntimeError):
    """Base error for conversation-session lifecycle failures."""


class ConversationSessionConflictError(ConversationSessionError):
    """Raised when a repository cannot persist a globally unique session ID."""


class ConversationSessionNotFoundError(ConversationSessionError):
    """Raised when a supplied canonical session ID does not exist."""


class ConversationSessionOwnershipError(ConversationSessionError):
    """Raised when a user attempts to access another user's session."""
