"""Contract tests for the pluggable AIGility memory module."""

from typing import Any, Dict, Optional

import pytest

from aigility.client import ADKClientBuilder
from aigility.memory import (
    ConversationScope,
    Memory,
    MemoryCapabilities,
    MemoryConfig,
    MemoryError,
    MemoryIdentity,
    MemoryProviderConfig,
    MemoryProviderError,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryStatus,
    MemoryWriteRequest,
    MemoryWriteResult,
)
from aigility.memory.providers.base import BaseMemoryProvider
from aigility.memory.providers.factory import MemoryProviderFactory
from aigility.memory.providers.timem import TimemMemoryProvider


class FakeAsyncMemory:
    """A network-free stand-in for the TiMEM high-level SDK client."""

    last_instance: Optional["FakeAsyncMemory"] = None
    add_result: Any = {
        "success": True,
        "memory_id": "memory-1",
        "memory_ids": ["memory-1"],
        "memories": [
            {
                "id": "memory-1",
                "content": "用户偏好中文回答",
                "layer": "L1",
                "metadata": {"score": 0.91},
            }
        ],
    }
    search_result: Any = {
        "success": True,
        "results": [
            {
                "id": "memory-1",
                "content": "用户偏好中文回答",
                "layer": "L1",
                "metadata": {"score": 0.91},
            }
        ],
    }
    add_exception: Optional[Exception] = None

    def __init__(self, **kwargs: Any) -> None:
        self.init_kwargs = kwargs
        self.add_kwargs: Optional[Dict[str, Any]] = None
        self.search_kwargs: Optional[Dict[str, Any]] = None
        self.closed = False
        type(self).last_instance = self

    async def add(self, **kwargs: Any) -> Any:
        self.add_kwargs = kwargs
        if type(self).add_exception:
            raise type(self).add_exception
        return type(self).add_result

    async def search(self, **kwargs: Any) -> Any:
        self.search_kwargs = kwargs
        return type(self).search_result

    async def close(self) -> None:
        self.closed = True


class ProviderError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__("provider error")
        self.status_code = status_code


class ExampleProvider(BaseMemoryProvider):
    """Minimal third-party provider used to test the generic registry seam."""

    provider_name = "example"
    capabilities = MemoryCapabilities(
        conversation_write=True,
        semantic_search=True,
    )

    def __init__(self, config: Any) -> None:
        super().__init__(config)
        self.last_write: Optional[MemoryWriteRequest] = None

    async def write(self, request: MemoryWriteRequest) -> MemoryWriteResult:
        self.last_write = request
        return MemoryWriteResult(
            status=MemoryStatus.SUCCESS,
            provider=self.provider_name,
        )

    async def retrieve(self, request: MemorySearchRequest) -> MemorySearchResult:
        return MemorySearchResult(
            status=MemoryStatus.SUCCESS,
            provider=self.provider_name,
        )


def make_config() -> MemoryProviderConfig:
    return MemoryProviderConfig(
        provider="timem",
        api_key="test-key",
        base_url="https://example.invalid",
    )


def make_write_request() -> MemoryWriteRequest:
    return MemoryWriteRequest(
        messages=[{"role": "user", "content": "请记住我喜欢中文"}],
        scope=ConversationScope(
            identity=MemoryIdentity(user_id="user-1", agent_id="agent-1"),
            session_id="session-1",
        ),
        metadata={"source": "test"},
    )


@pytest.fixture(autouse=True)
def reset_fake_sdk() -> None:
    FakeAsyncMemory.last_instance = None
    FakeAsyncMemory.add_exception = None
    FakeAsyncMemory.add_result = {
        "success": True,
        "memory_id": "memory-1",
        "memory_ids": ["memory-1"],
        "memories": [
            {
                "id": "memory-1",
                "content": "用户偏好中文回答",
                "layer": "L1",
                "metadata": {"score": 0.91},
            }
        ],
    }
    FakeAsyncMemory.search_result = {
        "success": True,
        "results": [
            {
                "id": "memory-1",
                "content": "用户偏好中文回答",
                "layer": "L1",
                "metadata": {"score": 0.91},
            }
        ],
    }


@pytest.mark.asyncio
async def test_timem_provider_maps_generic_write_scope_to_sdk() -> None:
    provider = TimemMemoryProvider(make_config(), client_factory=FakeAsyncMemory)

    result = await provider.write(make_write_request())

    client = FakeAsyncMemory.last_instance
    assert client is not None
    assert client.add_kwargs == {
        "messages": [{"role": "user", "content": "请记住我喜欢中文"}],
        "user_id": "user-1",
        "character_id": "agent-1",
        "session_id": "session-1",
        "metadata": {"source": "test"},
    }
    assert result.status == MemoryStatus.SUCCESS
    assert result.records[0].content == "用户偏好中文回答"
    assert result.records[0].score == 0.91
    assert result.memory_id == "memory-1"
    assert client.init_kwargs["timeout"] == 90.0
    assert client.init_kwargs["max_retries"] == 0


@pytest.mark.asyncio
async def test_timem_provider_search_keeps_session_filter_opt_in() -> None:
    provider = TimemMemoryProvider(make_config(), client_factory=FakeAsyncMemory)

    result = await provider.retrieve(
        MemorySearchRequest(
            query="用户语言偏好",
            identity=MemoryIdentity(user_id="user-1", agent_id="agent-1"),
            limit=3,
        )
    )

    client = FakeAsyncMemory.last_instance
    assert client is not None
    assert client.search_kwargs is not None
    assert "session_id" not in client.search_kwargs
    assert client.search_kwargs["character_id"] == "agent-1"
    assert result.success
    assert result.records[0].layer == "L1"


@pytest.mark.asyncio
async def test_timem_provider_distinguishes_empty_search_from_failure() -> None:
    FakeAsyncMemory.search_result = {"success": True, "memories": []}
    provider = TimemMemoryProvider(make_config(), client_factory=FakeAsyncMemory)

    result = await provider.retrieve(
        MemorySearchRequest(
            query="没有匹配项",
            identity=MemoryIdentity(user_id="user-1", agent_id="agent-1"),
        )
    )

    assert result.success
    assert not result.is_degraded
    assert result.records == []


@pytest.mark.asyncio
async def test_timem_provider_exposes_402_as_blocked_not_empty_success() -> None:
    FakeAsyncMemory.add_exception = ProviderError(402)
    provider = TimemMemoryProvider(make_config(), client_factory=FakeAsyncMemory)

    result = await provider.write(make_write_request())

    assert result.status == MemoryStatus.BLOCKED
    assert not result.success
    assert result.is_degraded
    assert result.error is not None
    assert result.error.provider_status_code == 402
    assert result.error.code == "provider_blocked"


@pytest.mark.asyncio
async def test_memory_facade_requires_real_identity_and_session() -> None:
    memory = Memory(
        MemoryConfig(provider=MemoryProviderConfig(provider="example", enabled=False))
    )
    memory._provider = ExampleProvider(memory.config.provider)

    with pytest.raises(ValueError, match="session_id"):
        await memory.add(
            messages=[{"role": "user", "content": "hello"}],
            user_id="user-1",
            agent_id="agent-1",
        )

    result = await memory.add(
        messages=[{"role": "user", "content": "hello"}],
        user_id="user-1",
        agent_id="agent-1",
        session_id="session-1",
    )
    assert result["success"]
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_registered_provider_can_be_used_without_memory_facade_changes() -> None:
    MemoryProviderFactory.register("example", ExampleProvider, overwrite=True)
    try:
        memory = Memory(
            MemoryConfig(
                provider=MemoryProviderConfig(provider="example", api_key="unused")
            )
        )
        result = await memory.write(make_write_request())

        assert result.provider == "example"
        assert result.success
        assert "example" in MemoryProviderFactory.available_providers()
    finally:
        MemoryProviderFactory.unregister("example")


def test_adk_client_builder_keeps_memory_provider_generic() -> None:
    MemoryProviderFactory.register("example", ExampleProvider, overwrite=True)
    try:
        client = (
            ADKClientBuilder()
            .with_memory(
                provider="example",
                enabled=True,
                api_key="unused",
                timeout_seconds=12,
            )
            .build()
        )

        memory = client.memory
        assert client.config.memory_provider == "example"
        assert client.config.memory_options["timeout_seconds"] == 12
        assert memory is not None
        assert memory.provider_name == "example"
    finally:
        MemoryProviderFactory.unregister("example")


@pytest.mark.asyncio
async def test_memory_degrade_mode_keeps_blocked_state_visible() -> None:
    class BlockedProvider(ExampleProvider):
        async def write(self, request: MemoryWriteRequest) -> MemoryWriteResult:
            return MemoryWriteResult(
                status=MemoryStatus.BLOCKED,
                provider=self.provider_name,
                error=MemoryError(
                    code="provider_blocked",
                    message="blocked",
                    provider_status_code=402,
                ),
            )

    memory = Memory(
        MemoryConfig(provider=MemoryProviderConfig(provider="example", enabled=False))
    )
    memory._provider = BlockedProvider(memory.config.provider)

    result = await memory.add(
        messages=[{"role": "user", "content": "hello"}],
        user_id="user-1",
        agent_id="agent-1",
        session_id="session-1",
    )

    assert not result["success"]
    assert result["status"] == "blocked"
    assert result["is_degraded"]
    assert result["error"]["provider_status_code"] == 402


@pytest.mark.asyncio
async def test_memory_strict_mode_raises_typed_provider_error() -> None:
    class BlockedProvider(ExampleProvider):
        async def write(self, request: MemoryWriteRequest) -> MemoryWriteResult:
            return MemoryWriteResult(
                status=MemoryStatus.BLOCKED,
                provider=self.provider_name,
                error=MemoryError(code="provider_blocked", message="blocked"),
            )

    memory = Memory(
        MemoryConfig(
            provider=MemoryProviderConfig(provider="example", enabled=False),
            failure_mode="raise",
        )
    )
    memory._provider = BlockedProvider(memory.config.provider)

    with pytest.raises(MemoryProviderError):
        await memory.add(
            messages=[{"role": "user", "content": "hello"}],
            user_id="user-1",
            agent_id="agent-1",
            session_id="session-1",
        )
