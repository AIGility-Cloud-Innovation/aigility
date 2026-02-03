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
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        发送 HTTP 请求

        Args:
            method: HTTP 方法
            endpoint: 端点路径
            data: 请求体数据 (JSON)
            params: URL 查询参数
            headers: 额外的请求头
            files: 文件上传数据
        """
        # 使用熔断器和重试机制
        async with self.circuit_breaker():
            return await self.retry_handler.execute(
                self._do_request,
                method=method,
                endpoint=endpoint,
                data=data,
                params=params,
                headers=headers,
                files=files,
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

            if self.api_key and "X-API-Key" not in request_headers:
                request_headers["X-API-Key"] = self.api_key

            # 调试日志
            import logging
            logger = logging.getLogger(__name__)
            full_url = f"{self.base_url}{endpoint}"
            logger.warning(f"🔍 ADP Stream Request: {method} {full_url}")
            logger.warning(f"   Base URL: {self.base_url}")
            logger.warning(f"   Endpoint: {endpoint}")
            logger.warning(f"   Request data: {data}")

            try:
                async with client.stream(
                    method=method,
                    url=endpoint,
                    json=data,
                    params=params,
                    headers=request_headers,
                    timeout=self.timeout,
                ) as response:
                    logger.warning(f"✅ ADP Response Status: {response.status_code}")
                    logger.warning(f"   Response headers: {dict(response.headers)}")

                    response.raise_for_status()

                    line_count = 0
                    async for line in response.aiter_lines():
                        if line:
                            line_count += 1
                            logger.warning(f"   📨 Line {line_count}: {line[:100]}...")
                            yield line

                    logger.warning(f"🏁 Stream ended. Total lines: {line_count}")

            except httpx.HTTPStatusError as e:
                logger.error(f"❌ HTTP Status Error: {e.response.status_code}")
                logger.error(f"   Response: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"❌ Stream request error: {type(e).__name__}: {e}")
                raise

    async def _do_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        执行实际请求

        Args:
            method: HTTP 方法
            endpoint: 端点路径
            data: 请求体数据 (JSON)
            params: URL 查询参数
            headers: 额外的请求头
            files: 文件上传数据
        """
        # 使用连接池
        async with self.connection_pool.get_client() as client:
            # 合并客户端级别和请求级别的 headers
            request_headers = {}
            request_headers.update(self.headers)
            if headers:
                request_headers.update(headers)

            # 如果 self.api_key 存在，且 X-API-Key 头未被显式设置，则添加 X-API-Key 头
            if self.api_key and "X-API-Key" not in request_headers:
                request_headers["X-API-Key"] = self.api_key

            # 只有在没有文件上传时才设置 Content-Type 为 application/json
            # httpx 会自动为文件上传设置正确的 Content-Type 和 boundary
            if not files and "Content-Type" not in request_headers:
                request_headers["Content-Type"] = "application/json"

            # 准备请求参数
            request_kwargs = {
                "method": method,
                "url": endpoint,
                "params": params,
                "headers": request_headers,
                "timeout": self.timeout,
            }

            # 根据是否有文件上传选择不同的数据传递方式
            if files:
                # 文件上传：使用 data 和 files
                request_kwargs["data"] = data
                request_kwargs["files"] = files
            else:
                # 普通 JSON 请求：使用 json
                request_kwargs["json"] = data

            response = await client.request(**request_kwargs)

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

