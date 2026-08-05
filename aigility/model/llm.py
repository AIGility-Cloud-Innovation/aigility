"""
LLM 模型提供者

提供统一的 LLM 创建入口，内部转发到 ModelFactory。
"""

from typing import Optional, Any


def create_llm(
    provider: str = "openai",
    model: str = "gpt-4",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs
) -> Any:
    """
    创建 LLM 实例（便捷函数）

    内部构造 ADKConfig 并转发到 ModelFactory.create_llm()。

    Args:
        provider: 提供商名称 ("openai", "deepseek" 等)
        model: 模型名称
        api_key: API 密钥
        base_url: API Base URL
        **kwargs: 额外参数（temperature, max_tokens 等）

    Returns:
        LangChain LLM 实例（如 ChatOpenAI）
    """
    from ..core.config import ADKConfig
    from ..core.model_factory import ModelFactory

    config = ADKConfig(
        llm_provider=provider,
        llm_model=model,
        llm_api_key=api_key,
        llm_base_url=base_url,
        llm_temperature=kwargs.get("temperature", 0.7),
        llm_max_tokens=kwargs.get("max_tokens", 2000),
    )
    return ModelFactory.create_llm(config)

