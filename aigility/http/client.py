"""
ADK HTTP 客户端

提供统一的 HTTP 请求接口，支持连接池、重试、熔断等功能。
"""

import httpx
from typing import Optional, Dict, Any, AsyncGenerator
from .pool import ConnectionPool, ConnectionConfig
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from .retry import RetryConfig, RetryHandler


class HTTPClient:
    """HTTP 客户端"""
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 60.0,
        verify_ssl: bool = False,
        connection_config: Optional[ConnectionConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = headers or {}
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
    
    async def stream_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> AsyncGenerator[str, None]:
        """发送流式 HTTP 请求"""
        async with self.connection_pool.get_client() as client:
            request_headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
            request_headers.update(self.headers)
            if headers:
                request_headers.update(headers)

            if self.api_key and "Authorization" not in request_headers and "X-API-Key" not in request_headers:
                request_headers["Authorization"] = f"Bearer {self.api_key}"

            async with client.stream(
                method=method,
                url=endpoint,
                json=data,
                params=params,
                headers=request_headers,
                timeout=self.timeout,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        yield line

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
            # 合并客户端级别和请求级别的 headers
            request_headers = {"Content-Type": "application/json"}
            request_headers.update(self.headers)
            if headers:
                request_headers.update(headers)

            # 如果 self.api_key 存在，且 Authorization 或 X-API-Key 头未被显式设置，则添加默认的 Authorization 头
            if self.api_key and "Authorization" not in request_headers and "X-API-Key" not in request_headers:
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

