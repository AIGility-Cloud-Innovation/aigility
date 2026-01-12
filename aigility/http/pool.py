"""
连接池管理

提供 HTTP 连接池功能。
"""

import httpx
from typing import Optional
from dataclasses import dataclass
from contextlib import asynccontextmanager


@dataclass
class ConnectionConfig:
    """连接配置"""
    max_connections: int = 20
    max_keepalive_connections: int = 10
    keepalive_expiry: float = 30.0
    connect_timeout: float = 10.0
    read_timeout: float = 60.0
    write_timeout: float = 60.0


class ConnectionPool:
    """连接池"""
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        config: Optional[ConnectionConfig] = None,
        verify_ssl: bool = False,
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.config = config or ConnectionConfig()
        self.verify_ssl = verify_ssl
        self._client: Optional[httpx.AsyncClient] = None
    
    @asynccontextmanager
    async def get_client(self):
        """获取客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(
                    connect=self.config.connect_timeout,
                    read=self.config.read_timeout,
                    write=self.config.write_timeout,
                    pool=self.config.connect_timeout,
                ),
                limits=httpx.Limits(
                    max_connections=self.config.max_connections,
                    max_keepalive_connections=self.config.max_keepalive_connections,
                ),
                verify=self.verify_ssl,
            )
        
        try:
            yield self._client
        finally:
            pass  # 保持连接池打开
    
    async def close(self):
        """关闭连接池"""
        if self._client:
            await self._client.aclose()
            self._client = None

