"""
重试机制

提供请求重试功能。
"""

import asyncio
from typing import Optional, Callable, Any
from dataclasses import dataclass


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    retry_delay: float = 1.0
    exponential_backoff: bool = True
    retryable_exceptions: tuple = (Exception,)


class RetryHandler:
    """重试处理器"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """执行函数，带重试"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except self.config.retryable_exceptions as e:
                last_exception = e
                
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay
                    if self.config.exponential_backoff:
                        delay *= (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    raise last_exception
        
        raise last_exception

