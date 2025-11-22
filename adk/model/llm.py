"""
LLM 模型提供者

提供统一的 LLM 接口，支持多种 LLM 提供商。
"""

from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """LLM 提供者基类"""
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ):
        """流式生成文本"""
        pass


def create_llm(
    provider: str = "openai",
    model: str = "gpt-4",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs
) -> LLMProvider:
    """
    创建 LLM 提供者
    
    Args:
        provider: 提供者名称 (openai, anthropic, etc.)
        model: 模型名称
        api_key: API 密钥
        base_url: API 基础 URL
        **kwargs: 其他参数
        
    Returns:
        LLM 提供者实例
    """
    # TODO: 实现具体的 LLM 提供者
    # 这里需要根据 provider 参数创建对应的实例
    # 可以使用 langchain 的 LLM 类
    raise NotImplementedError("LLM provider creation not yet implemented")

