"""Registry-backed construction of pluggable memory providers."""

from typing import Any, Callable, Dict, List

from .base import BaseMemoryProvider

ProviderBuilder = Callable[[Any], BaseMemoryProvider]


class MemoryProviderFactory:
    """A registry rather than a provider-specific ``if`` chain.

    Third-party integrations can register a provider at application startup:

    ``MemoryProviderFactory.register("mem0", Mem0MemoryProvider)``.
    """

    _registry: Dict[str, ProviderBuilder] = {}

    @classmethod
    def register(
        cls,
        provider_name: str,
        builder: ProviderBuilder,
        *,
        overwrite: bool = False,
    ) -> None:
        normalized_name = cls._normalize_name(provider_name)
        if normalized_name in cls._registry and not overwrite:
            raise ValueError(f"Memory provider 已注册: {normalized_name}")
        cls._registry[normalized_name] = builder

    @classmethod
    def unregister(cls, provider_name: str) -> None:
        """Remove a registered provider, primarily useful in isolated tests."""

        cls._registry.pop(cls._normalize_name(provider_name), None)

    @classmethod
    def available_providers(cls) -> List[str]:
        return sorted(cls._registry)

    @classmethod
    def create_provider(cls, config: Any) -> BaseMemoryProvider:
        provider_name = cls._normalize_name(getattr(config, "provider", ""))
        builder = cls._registry.get(provider_name)
        if builder is None:
            available = ", ".join(cls.available_providers()) or "无"
            raise ValueError(
                f"不支持的 memory provider: {provider_name or '<empty>'}。"
                f"已注册: {available}"
            )
        return builder(config)

    @staticmethod
    def _normalize_name(provider_name: str) -> str:
        normalized_name = str(provider_name).strip().lower()
        if not normalized_name:
            raise ValueError("provider 名称不能为空")
        return normalized_name


# The bundled adapter is registered lazily so importing aigility.memory does
# not require the optional TiMEM SDK. Other integrations can register their
# own builder without editing this module or the Memory façade.
def _build_timem_provider(config: Any) -> BaseMemoryProvider:
    from .timem import TimemMemoryProvider

    return TimemMemoryProvider(config)


MemoryProviderFactory.register("timem", _build_timem_provider)


__all__ = ["MemoryProviderFactory", "ProviderBuilder"]
