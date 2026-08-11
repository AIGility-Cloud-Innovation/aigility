"""Provider-independent contracts for the AIGility memory module.

The public models in this module intentionally do not expose a vendor's
terminology.  A provider maps these models to its own SDK at the adapter seam.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence


class MemoryStatus(str, Enum):
    """A normalized outcome for every memory operation."""

    SUCCESS = "success"
    DISABLED = "disabled"
    BLOCKED = "blocked"
    UNAUTHORIZED = "unauthorized"
    INVALID_REQUEST = "invalid_request"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(frozen=True)
class MemoryError:
    """A safe, provider-neutral description of a failed operation."""

    code: str
    message: str
    retryable: bool = False
    provider_status_code: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "provider_status_code": self.provider_status_code,
        }


@dataclass(frozen=True)
class MemoryIdentity:
    """The stable user and agent scope shared by writes and retrievals."""

    user_id: str
    agent_id: str

    def __post_init__(self) -> None:
        user_id = str(self.user_id).strip()
        agent_id = str(self.agent_id).strip()
        if not user_id:
            raise ValueError("user_id 必须提供")
        if not agent_id:
            raise ValueError("agent_id 必须提供")
        object.__setattr__(self, "user_id", user_id)
        object.__setattr__(self, "agent_id", agent_id)


@dataclass(frozen=True)
class ConversationScope:
    """The stable identity plus a concrete conversation for a write."""

    identity: MemoryIdentity
    session_id: str

    def __post_init__(self) -> None:
        session_id = str(self.session_id).strip()
        if not session_id:
            raise ValueError("session_id 必须提供")
        object.__setattr__(self, "session_id", session_id)


@dataclass(frozen=True)
class MemoryWriteRequest:
    """A vendor-neutral request to persist one conversation turn or batch."""

    messages: Sequence[Mapping[str, Any]]
    scope: ConversationScope
    metadata: Mapping[str, Any] = field(default_factory=dict)
    provider_options: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError("messages 不能为空")

        normalized_messages: List[Dict[str, str]] = []
        for message in self.messages:
            if not isinstance(message, Mapping):
                raise ValueError("messages 中的每条消息必须是映射类型")
            role = message.get("role")
            content = message.get("content")
            if not isinstance(role, str) or not role.strip():
                raise ValueError("messages 中的 role 必须是非空字符串")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("messages 中的 content 必须是非空字符串")
            normalized_messages.append({"role": role, "content": content})

        object.__setattr__(self, "messages", normalized_messages)
        object.__setattr__(self, "metadata", dict(self.metadata))
        object.__setattr__(self, "provider_options", dict(self.provider_options))


@dataclass(frozen=True)
class MemorySearchRequest:
    """A vendor-neutral semantic memory retrieval request."""

    query: str
    identity: MemoryIdentity
    limit: int = 10
    session_id: Optional[str] = None
    filters: Mapping[str, Any] = field(default_factory=dict)
    include_context: bool = False
    provider_options: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        query = str(self.query).strip()
        if not query:
            raise ValueError("query 不能为空")
        if self.limit < 1:
            raise ValueError("limit 必须大于 0")

        session_id = self.session_id
        if session_id is not None:
            session_id = str(session_id).strip()
            if not session_id:
                raise ValueError("session_id 不能为空字符串")

        object.__setattr__(self, "query", query)
        object.__setattr__(self, "session_id", session_id)
        object.__setattr__(self, "filters", dict(self.filters))
        object.__setattr__(self, "provider_options", dict(self.provider_options))


@dataclass(frozen=True)
class MemoryRecord:
    """A normalized memory record returned by any provider."""

    content: str
    id: Optional[str] = None
    score: Optional[float] = None
    layer: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "memory": self.content,
            "content": self.content,
            "score": self.score,
            "layer": self.layer,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class MemoryCapabilities:
    """Capabilities used for feature negotiation without vendor type checks."""

    conversation_write: bool = True
    semantic_search: bool = True
    read_by_id: bool = False
    deletion: bool = False
    structured_write: bool = False
    layered_memory: bool = False
    relationship_summary: bool = False
    policy_management: bool = False

    def to_dict(self) -> Dict[str, bool]:
        return {
            "conversation_write": self.conversation_write,
            "semantic_search": self.semantic_search,
            "read_by_id": self.read_by_id,
            "deletion": self.deletion,
            "structured_write": self.structured_write,
            "layered_memory": self.layered_memory,
            "relationship_summary": self.relationship_summary,
            "policy_management": self.policy_management,
        }


@dataclass(frozen=True)
class MemoryWriteResult:
    """The normalized result of a write operation."""

    status: MemoryStatus
    provider: str
    records: Sequence[MemoryRecord] = field(default_factory=list)
    memory_id: Optional[str] = None
    memory_ids: Sequence[str] = field(default_factory=list)
    task_id: Optional[str] = None
    message: str = ""
    error: Optional[MemoryError] = None

    @property
    def success(self) -> bool:
        return self.status == MemoryStatus.SUCCESS

    @property
    def is_degraded(self) -> bool:
        return not self.success

    def to_dict(self) -> Dict[str, Any]:
        memory_ids = list(self.memory_ids)
        if not memory_ids:
            memory_ids = [record.id for record in self.records if record.id]
        memory_id = self.memory_id or (memory_ids[0] if memory_ids else None)
        return {
            "success": self.success,
            "status": self.status.value,
            "is_degraded": self.is_degraded,
            "provider": self.provider,
            "memories": [record.to_dict() for record in self.records],
            "memory_id": memory_id,
            "memory_ids": memory_ids,
            "task_id": self.task_id,
            "total": len(self.records),
            "message": self.message,
            "error": self.error.to_dict() if self.error else None,
        }


@dataclass(frozen=True)
class MemorySearchResult:
    """The normalized result of a retrieval operation."""

    status: MemoryStatus
    provider: str
    records: Sequence[MemoryRecord] = field(default_factory=list)
    error: Optional[MemoryError] = None

    @property
    def success(self) -> bool:
        return self.status == MemoryStatus.SUCCESS

    @property
    def is_degraded(self) -> bool:
        return not self.success

    def to_dict(self, query: str) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status.value,
            "is_degraded": self.is_degraded,
            "provider": self.provider,
            "results": [record.to_dict() for record in self.records],
            "total": len(self.records),
            "query": query,
            "error": self.error.to_dict() if self.error else None,
        }


class MemoryProviderError(RuntimeError):
    """Raised only when a caller selects strict memory failure handling."""

    def __init__(self, result: Any):
        error = getattr(result, "error", None)
        message = error.message if error else "Memory provider operation failed"
        super().__init__(message)
        self.result = result


__all__ = [
    "ConversationScope",
    "MemoryCapabilities",
    "MemoryError",
    "MemoryIdentity",
    "MemoryProviderError",
    "MemoryRecord",
    "MemorySearchRequest",
    "MemorySearchResult",
    "MemoryStatus",
    "MemoryWriteRequest",
    "MemoryWriteResult",
]
