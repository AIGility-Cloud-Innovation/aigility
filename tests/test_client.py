"""Compatibility checks for the TiMEM SDK surface used by AIGility."""

from __future__ import annotations

import inspect

import pytest


pytestmark = pytest.mark.optional_timem


def test_timem_sdk_exposes_the_async_memory_contract_used_by_aigility():
    """The declared TiMEM extra must provide AIGility's no-network API seam."""
    import timem

    assert hasattr(timem, "AsyncMemory")

    add_parameters = inspect.signature(timem.AsyncMemory.add).parameters
    search_parameters = inspect.signature(timem.AsyncMemory.search).parameters

    assert {"messages", "user_id", "character_id", "session_id"} <= set(
        add_parameters
    )
    assert {"query", "user_id", "character_id", "session_id", "limit"} <= set(
        search_parameters
    )


def test_timem_extra_initializes_aigility_provider_without_network_access():
    """Installing the extra is sufficient to cross the provider constructor seam."""
    from aigility.memory import MemoryProviderConfig, TimemMemoryProvider

    provider = TimemMemoryProvider(
        MemoryProviderConfig(
            api_key="test-key",
            base_url="https://memory.example.test/",
        )
    )

    assert provider.enabled is True
