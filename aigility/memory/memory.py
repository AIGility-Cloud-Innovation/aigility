"""Public façade for provider-neutral long-term memory operations."""

import logging
from typing import Any, Dict, List, Mapping, Optional, TypeVar, Union

from .config import MemoryConfig
from .contracts import (
    ConversationScope,
    MemoryCapabilities,
    MemoryError,
    MemoryIdentity,
    MemoryProviderError,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryStatus,
    MemoryWriteRequest,
    MemoryWriteResult,
)
from .providers.base import BaseMemoryProvider
from .providers.factory import MemoryProviderFactory

logger = logging.getLogger(__name__)

MemoryOperationResult = TypeVar(
    "MemoryOperationResult", MemoryWriteResult, MemorySearchResult
)


class Memory:
    """A stable memory façade over a pluggable provider registry.

    New integrations should use :meth:`write` and :meth:`retrieve` with the
    contracts in ``aigility.memory.contracts``.  ``add`` and ``search`` stay as
    compatibility helpers and return dictionaries for existing callers.
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        if config is not None and not isinstance(config, MemoryConfig):
            raise TypeError(
                "config 必须是 MemoryConfig 类型，" f"获取到: {type(config)}"
            )

        self.config = config or MemoryConfig()
        self._provider: Optional[BaseMemoryProvider] = None
        self._initialization_error: Optional[MemoryError] = None
        self._initialize_provider()

    @property
    def provider_name(self) -> str:
        return self.config.provider.provider

    @property
    def capabilities(self) -> MemoryCapabilities:
        if self._provider:
            return self._provider.capabilities
        return MemoryCapabilities(
            conversation_write=False,
            semantic_search=False,
        )

    def _initialize_provider(self) -> None:
        if not self.config.provider.enabled:
            self._initialization_error = MemoryError(
                code="provider_disabled",
                message="Memory provider 未启用",
            )
            return

        self._provider = MemoryProviderFactory.create_provider(self.config.provider)
        logger.info(
            "Memory provider initialized: provider=%s",
            self.config.provider.provider,
        )

    async def write(self, request: MemoryWriteRequest) -> MemoryWriteResult:
        """Persist memory through the configured provider."""

        if not self._provider:
            result = MemoryWriteResult(
                status=(
                    MemoryStatus.DISABLED
                    if not self.config.provider.enabled
                    else MemoryStatus.FAILED
                ),
                provider=self.provider_name,
                error=self._initialization_error
                or MemoryError(
                    code="provider_unavailable",
                    message="Memory provider 不可用",
                ),
            )
            return self._apply_failure_mode(result)

        result = await self._provider.write(request)
        return self._apply_failure_mode(result)

    async def retrieve(self, request: MemorySearchRequest) -> MemorySearchResult:
        """Retrieve memory through the configured provider."""

        if not self._provider:
            result = MemorySearchResult(
                status=(
                    MemoryStatus.DISABLED
                    if not self.config.provider.enabled
                    else MemoryStatus.FAILED
                ),
                provider=self.provider_name,
                error=self._initialization_error
                or MemoryError(
                    code="provider_unavailable",
                    message="Memory provider 不可用",
                ),
            )
            return self._apply_failure_mode(result)

        result = await self._provider.retrieve(request)
        return self._apply_failure_mode(result)

    def _apply_failure_mode(
        self, result: MemoryOperationResult
    ) -> MemoryOperationResult:
        if not result.success and self.config.failure_mode == "raise":
            raise MemoryProviderError(result)
        return result

    async def add(
        self,
        messages: List[Dict[str, str]],
        user_id: Optional[Union[str, int]] = None,
        character_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        provider_options: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Backward-compatible dictionary wrapper around :meth:`write`.

        ``character_id`` remains an alias for ``agent_id`` for compatibility
        with TiMEM callers.  A write always requires a real session identifier;
        the façade never invents one from a user identifier.
        """

        identity = self._build_identity(user_id, agent_id, character_id)
        if session_id is None:
            raise ValueError("session_id 必须提供")

        result = await self.write(
            MemoryWriteRequest(
                messages=messages,
                scope=ConversationScope(identity=identity, session_id=session_id),
                metadata=metadata or {},
                provider_options=provider_options or {},
            )
        )
        return result.to_dict()

    async def search(
        self,
        query: str,
        user_id: Optional[Union[str, int]] = None,
        limit: int = 10,
        character_id: Optional[str] = None,
        include_context: bool = False,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        filters: Optional[Mapping[str, Any]] = None,
        provider_options: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Backward-compatible dictionary wrapper around :meth:`retrieve`."""

        identity = self._build_identity(user_id, agent_id, character_id)
        result = await self.retrieve(
            MemorySearchRequest(
                query=query,
                identity=identity,
                limit=limit,
                session_id=session_id,
                filters=filters or {},
                include_context=include_context,
                provider_options=provider_options or {},
            )
        )
        return result.to_dict(query=query)

    @staticmethod
    def _build_identity(
        user_id: Optional[Union[str, int]],
        agent_id: Optional[str],
        character_id: Optional[str],
    ) -> MemoryIdentity:
        if agent_id and character_id and agent_id != character_id:
            raise ValueError("agent_id 与 character_id 必须一致")
        resolved_agent_id = agent_id or character_id
        if user_id is None:
            raise ValueError("user_id 必须提供")
        if not resolved_agent_id:
            raise ValueError("agent_id 必须提供（character_id 可作为兼容别名）")
        return MemoryIdentity(user_id=str(user_id), agent_id=resolved_agent_id)

    async def close(self) -> None:
        """Release the configured provider's resources."""

        if self._provider:
            await self._provider.close()

    async def __aenter__(self) -> "Memory":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()


__all__ = ["Memory"]
