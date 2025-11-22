"""
ADK HTTP 客户端

提供统一的 HTTP 请求接口，支持连接池、重试、熔断等功能。
"""

import httpx
from typing import Optional, Dict, Any
from .pool import ConnectionPool, ConnectionConfig
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from .retry import RetryConfig, RetryHandler


class HTTPClient:
    """HTTP 客户端"""
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        verify_ssl: bool = False,
        connection_config: Optional[ConnectionConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        
        # 初始化组件
        self.connection_pool = ConnectionPool(
            base_url=base_url,
            api_key=api_key,
            config=connection_config,
            verify_ssl=verify_ssl,
        )
        
        self.circuit_breaker = CircuitBreaker(
            name="http_client",
            config=circuit_breaker_config,
        )
        
        self.retry_handler = RetryHandler(
            config=retry_config or RetryConfig(),
        )
    
    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        # 使用熔断器和重试机制
        async with self.circuit_breaker():
            return await self.retry_handler.execute(
                self._do_request,
                method=method,
                endpoint=endpoint,
                data=data,
                params=params,
                headers=headers,
            )
    
    async def _do_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """执行实际请求"""
        # 使用连接池
        async with self.connection_pool.get_client() as client:
            request_headers = {
                "Content-Type": "application/json",
                **(headers or {}),
            }
            
            if self.api_key:
                request_headers["Authorization"] = f"Bearer {self.api_key}"
            
            response = await client.request(
                method=method,
                url=endpoint,
                json=data,
                params=params,
                headers=request_headers,
                timeout=self.timeout,
            )
            
            response.raise_for_status()
            return response.json()
    
    async def close(self):
        """关闭客户端"""
        await self.connection_pool.close()


def create_http_client(
    base_url: str,
    api_key: Optional[str] = None,
    **kwargs
) -> HTTPClient:
    """创建 HTTP 客户端"""
    return HTTPClient(base_url=base_url, api_key=api_key, **kwargs)

