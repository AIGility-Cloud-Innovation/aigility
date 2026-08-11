"""The provider seam for all memory backends."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..contracts import (
    ConversationScope,
    MemoryCapabilities,
    MemoryIdentity,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryWriteRequest,
    MemoryWriteResult,
)


class BaseMemoryProvider(ABC):
    """Provider-independent memory interface.

    New adapters implement :meth:`write` and :meth:`retrieve`.  The historical
    ``add_memory`` and ``search_memories`` helpers remain as compatibility
    wrappers for callers that still use the original AIGility API.
    """

    provider_name = "base"
    capabilities = MemoryCapabilities(
        conversation_write=False,
        semantic_search=False,
    )

    def __init__(self, config: Any):
        self.config = config

    @abstractmethod
    async def write(self, request: MemoryWriteRequest) -> MemoryWriteResult:
        """Persist a conversation using the normalized write contract."""

    @abstractmethod
    async def retrieve(self, request: MemorySearchRequest) -> MemorySearchResult:
        """Retrieve memories using the normalized retrieval contract."""

    async def add_memory(
        self,
        messages: List[Dict[str, str]],
        user_id: Optional[str] = None,
        character_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Backward-compatible wrapper around :meth:`write`.

        This legacy method intentionally keeps the historical ``None`` failure
        shape.  New callers should use :meth:`write` to distinguish an empty
        result from a provider failure.
        """

        if user_id is None or character_id is None or session_id is None:
            return None

        request = MemoryWriteRequest(
            messages=messages,
            scope=ConversationScope(
                identity=MemoryIdentity(
                    user_id=str(user_id),
                    agent_id=str(character_id),
                ),
                session_id=str(session_id),
            ),
        )
        result = await self.write(request)
        return result.to_dict() if result.success else None

    async def search_memories(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        character_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Backward-compatible wrapper around :meth:`retrieve`."""

        if user_id is None or character_id is None:
            return []

        request = MemorySearchRequest(
            query=query_text,
            identity=MemoryIdentity(
                user_id=str(user_id),
                agent_id=str(character_id),
            ),
            session_id=session_id,
            limit=limit,
        )
        result = await self.retrieve(request)
        return [record.to_dict() for record in result.records] if result.success else []

    async def close(self) -> None:
        """Release provider-owned resources when an adapter needs it."""


__all__ = ["BaseMemoryProvider"]
