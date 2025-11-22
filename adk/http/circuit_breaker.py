"""
熔断器

提供熔断器功能，防止级联故障。
"""

import asyncio
import time
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3
    error_rate_threshold: float = 0.5


class CircuitBreaker:
    """熔断器"""
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback_func: Optional[Callable] = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.fallback_func = fallback_func
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()
    
    @asynccontextmanager
    async def __call__(self):
        """上下文管理器"""
        async with self._lock:
            # 检查状态
            if self.state == CircuitState.OPEN:
                if time.time() - (self.last_failure_time or 0) > self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise Exception("Circuit breaker is OPEN")
        
        try:
            yield
            # 成功
            async with self._lock:
                if self.state == CircuitState.HALF_OPEN:
                    self.success_count += 1
                    if self.success_count >= self.config.success_threshold:
                        self.state = CircuitState.CLOSED
                        self.failure_count = 0
                else:
                    self.failure_count = 0
        except Exception as e:
            # 失败
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                
                if self.fallback_func:
                    try:
                        result = await self.fallback_func()
                        return result
                    except:
                        pass
                raise

