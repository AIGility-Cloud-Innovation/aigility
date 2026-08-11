"""Configuration shared by the provider-neutral memory module."""

import os
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

# Kept as an alias so existing imports remain valid while providers are now
# registered dynamically instead of being constrained to a fixed Literal.
MemoryProviderType = str


class MemoryProviderConfig(BaseModel):
    """Configuration passed to one concrete memory provider.

    ``kwargs`` contains provider-specific options.  It lets a new adapter add
    its own settings without changing AIGility's common configuration shape.
    """

    provider: MemoryProviderType = Field(
        default="timem",
        description="注册表中的提供商名称",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="提供商 API 密钥；TiMEM 也可从 TIMEM_API_KEY 读取",
    )
    base_url: Optional[str] = Field(
        default=None,
        description="提供商基础地址；TiMEM 也可从 TIMEM_BASE_URL 读取",
    )
    enabled: bool = Field(default=True, description="是否启用该提供商")
    timeout_seconds: float = Field(
        default=90.0,
        gt=0,
        description="单个提供商调用的超时提示",
    )
    max_retries: int = Field(
        default=0,
        ge=0,
        description="提供商 SDK 可使用的最大重试次数；默认关闭以避免重复写入",
    )
    kwargs: Dict[str, Any] = Field(
        default_factory=dict,
        description="提供商私有配置，例如 sdk_options",
    )

    def get_api_key(self) -> Optional[str]:
        """Resolve an API key without hard-coding other providers' env vars."""

        if self.api_key:
            return self.api_key

        env_key = self.kwargs.get("api_key_env")
        if isinstance(env_key, str) and env_key:
            return os.environ.get(env_key)
        if self.provider.lower() == "timem":
            return os.environ.get("TIMEM_API_KEY")
        return None

    def get_base_url(self) -> Optional[str]:
        """Resolve a base URL without imposing TiMEM defaults on other SDKs."""

        if self.base_url:
            return self.base_url

        env_key = self.kwargs.get("base_url_env")
        if isinstance(env_key, str) and env_key:
            return os.environ.get(env_key)
        if self.provider.lower() == "timem":
            return os.environ.get("TIMEM_BASE_URL", "https://api.timem.cloud")
        return None


class MemoryConfig(BaseModel):
    """Configuration of the common AIGility memory façade."""

    provider: MemoryProviderConfig = Field(
        default_factory=MemoryProviderConfig,
        description="Provider 配置",
    )
    failure_mode: Literal["degrade", "raise"] = Field(
        default="degrade",
        description="失败时返回状态化结果，或向调用方抛出异常",
    )


__all__ = ["MemoryConfig", "MemoryProviderConfig", "MemoryProviderType"]
