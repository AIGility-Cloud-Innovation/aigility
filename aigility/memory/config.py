# [配置层] 定义 Memory 相关的配置结构 (Pydantic)
"""
Memory 配置模块

配置优先级：
1. 代码中显式传入的参数
2. 环境变量
3. 默认值
"""

import os
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field

# 定义支持的类型
MemoryProviderType = Literal["timem", "custom"]


class MemoryProviderConfig(BaseModel):
    """
    Memory Provider 配置
    
    Attributes:
        provider: 提供商类型 ("timem")
        api_key: API 密钥
        base_url: API 基础 URL
        enabled: 是否启用
        kwargs: 扩展参数
    """
    provider: MemoryProviderType = Field(
        default="timem",
        description="提供商类型"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API 密钥，也可通过 TIMEM_API_KEY 环境变量设置"
    )
    base_url: Optional[str] = Field(
        default=None,
        description="API 基础 URL，也可通过 TIMEM_BASE_URL 环境变量设置"
    )
    enabled: bool = Field(
        default=True,
        description="是否启用"
    )
    kwargs: Dict[str, Any] = Field(
        default_factory=dict,
        description="扩展参数"
    )

    def get_api_key(self) -> Optional[str]:
        """获取 API Key，优先使用显式传入的，否则从环境变量读取"""
        if self.api_key:
            return self.api_key
        
        if self.provider == "timem":
            return os.environ.get("TIMEM_API_KEY")
        return None

    def get_base_url(self) -> Optional[str]:
        """获取 Base URL"""
        if self.base_url:
            return self.base_url
            
        if self.provider == "timem":
            return os.environ.get("TIMEM_BASE_URL", "https://api.timem.cloud")
        return "http://localhost:8000"


class MemoryConfig(BaseModel):
    """
    Memory 总配置
    
    Attributes:
        provider: Provider 配置
    """
    provider: MemoryProviderConfig = Field(
        default_factory=MemoryProviderConfig,
        description="Provider 配置"
    )


__all__ = [
    "MemoryConfig",
    "MemoryProviderConfig",
    "MemoryProviderType"
]
