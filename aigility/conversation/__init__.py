"""Canonical conversation-session lifecycle APIs."""

from .contracts import (
    ConversationContext,
    ConversationSession,
    ConversationSessionConflictError,
    ConversationSessionError,
    ConversationSessionNotFoundError,
    ConversationSessionOwnershipError,
)
from .id_generator import SessionIdGenerator, UUID4SessionIdGenerator
from .repository import (
    ConversationSessionRepository,
    InMemoryConversationSessionRepository,
)
from .service import ConversationSessionService

__all__ = [
    "ConversationContext",
    "ConversationSession",
    "ConversationSessionConflictError",
    "ConversationSessionError",
    "ConversationSessionNotFoundError",
    "ConversationSessionOwnershipError",
    "ConversationSessionRepository",
    "ConversationSessionService",
    "InMemoryConversationSessionRepository",
    "SessionIdGenerator",
    "UUID4SessionIdGenerator",
]
