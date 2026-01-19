"""
ADK 主客户端

提供统一的客户端接口，使用 Builder 模式。
"""

from typing import Optional, Dict, Any
from .core.config import ADKConfig
from .memory import Memory
from .chat import ChatAgent
from .chatflow import ChatFlow
from .workflow import WorkflowEngine


class ADKClient:
    """
    ADK 主客户端
    
    提供统一的接口访问所有 ADK 功能模块。
    """
    
    def __init__(self, config: Optional[ADKConfig] = None):
        """
        初始化 ADK 客户端
        
        Args:
            config: ADK 配置
        """
        self.config = config or ADKConfig()

        # 初始化各模块
        self._memory: Optional[Memory] = None
    
    @property
    def memory(self) -> Memory:
        """获取记忆模块"""
        if self._memory is None and self.config.memory_enabled:
            self._memory = Memory(
                api_key=self.config.memory_api_key,
                base_url=self.config.memory_base_url,
            )
        return self._memory
    
    def create_chat_agent(
        self,
        name: str,
        **kwargs
    ) -> ChatAgent:
        """创建对话智能体"""
        from .chat import create_chat_agent
        return create_chat_agent(name=name, **kwargs)
    
    def create_chatflow(
        self,
        name: str,
        **kwargs
    ) -> ChatFlow:
        """创建对话流"""
        from .chatflow import create_chatflow
        return create_chatflow(name=name, **kwargs)
    
    def create_workflow(
        self,
        name: str,
        **kwargs
    ) -> WorkflowEngine:
        """创建工作流"""
        from .workflow import create_workflow_engine
        return create_workflow_engine(name=name, **kwargs)
    
    def create_adp_client(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        **kwargs
    ) -> "ADPClient":
        """
        创建远程 ADP 服务客户端
        
        Args:
            base_url: ADP 服务地址
            api_key: API Key
            **kwargs: 其他配置
        """
        from .adp import ADPClient
        return ADPClient(base_url=base_url, api_key=api_key, **kwargs)

    async def close(self):
        """关闭客户端"""
        if self._memory:
            await self._memory.close()


class ADKClientBuilder:
    """ADK 客户端构建器"""
    
    def __init__(self):
        self.config = ADKConfig()
    
    def with_llm(
        self,
        provider: str = "openai",
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs
    ) -> "ADKClientBuilder":
        """配置 LLM"""
        self.config.llm_provider = provider
        self.config.llm_model = model
        self.config.llm_api_key = api_key
        self.config.llm_base_url = base_url
        return self
    
    def with_memory(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        enabled: bool = True
    ) -> "ADKClientBuilder":
        """配置记忆"""
        self.config.memory_enabled = enabled
        self.config.memory_api_key = api_key
        self.config.memory_base_url = base_url
        return self

    def with_http(
        self,
        timeout: float = 60.0,
        max_retries: int = 3,
        verify_ssl: bool = False
    ) -> "ADKClientBuilder":
        """配置 HTTP"""
        self.config.http_timeout = timeout
        self.config.http_max_retries = max_retries
        self.config.http_verify_ssl = verify_ssl
        return self
    
    def with_debug(self, enabled: bool = True) -> "ADKClientBuilder":
        """配置调试模式"""
        self.config.debug = enabled
        self.config.log_level = "DEBUG" if enabled else "INFO"
        return self
    
    def build(self) -> ADKClient:
        """构建客户端"""
        return ADKClient(config=self.config)


def create_client(**kwargs) -> ADKClient:
    """
    创建 ADK 客户端（快捷方式）

    Args:
        **kwargs: 配置参数

    Returns:
        ADK 客户端实例
    """
    builder = ADKClientBuilder()

    if "llm_provider" in kwargs:
        builder.with_llm(**{k.replace("llm_", ""): v for k, v in kwargs.items() if k.startswith("llm_")})

    if "memory_api_key" in kwargs:
        builder.with_memory(**{k.replace("memory_", ""): v for k, v in kwargs.items() if k.startswith("memory_")})

    return builder.build()

