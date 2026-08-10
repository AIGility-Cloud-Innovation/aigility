from typing import Any, Optional
from langchain_openai import ChatOpenAI
from .config import ADKConfig

class ModelFactory:
    """Model Factory to create LLM clients based on ADKConfig."""
    
    @staticmethod
    def create_llm(config: ADKConfig) -> Any:
        """Create and return an LLM client.

        当 config.llm_reasoning=True 时:
        - OpenAI o 系列: 透传 reasoning_effort
        - DeepSeek(deepseek-reasoner 等): 无需额外参数, reasoning_content 随流式 chunk 自动返回
        """
        provider = config.llm_provider.lower()

        # OpenAI o 系列推理参数(仅对支持的模型生效)
        reasoning_kwargs = {}
        if config.llm_reasoning and config.llm_reasoning_effort:
            reasoning_kwargs["reasoning_effort"] = config.llm_reasoning_effort

        # DeepSeek 思维链开关(V3.2+/V4 混合推理模型, 部分模型默认开启思考):
        # 显式传 thinking enabled/disabled, 保证行为与 llm_reasoning 配置一致。
        # 开启时思维链随流式 chunk 的 reasoning_content 字段返回。
        deepseek_thinking_kwargs = {
            "extra_body": {"thinking": {"type": "enabled" if config.llm_reasoning else "disabled"}}
        }

        if provider == "deepseek":
            try:
                from langchain_deepseek import ChatDeepSeek
                # Note: Parameters might vary slightly, assuming standard LangChain interface
                return ChatDeepSeek(
                    model=config.llm_model,
                    api_key=config.llm_api_key,
                    api_base=config.llm_base_url,
                    temperature=config.llm_temperature,
                    max_tokens=config.llm_max_tokens,
                    streaming=True,
                    **deepseek_thinking_kwargs
                )
            except ImportError:
                # Fallback to OpenAI client for DeepSeek (it is OpenAI compatible)
                return ChatOpenAI(
                    model=config.llm_model,
                    openai_api_key=config.llm_api_key,
                    openai_api_base=config.llm_base_url or "https://api.deepseek.com",
                    temperature=config.llm_temperature,
                    max_tokens=config.llm_max_tokens,
                    streaming=True,
                    **deepseek_thinking_kwargs
                )
        else:
            # Default to OpenAI or OpenAI-compatible
            return ChatOpenAI(
                model=config.llm_model,
                openai_api_key=config.llm_api_key,
                openai_api_base=config.llm_base_url,
                temperature=config.llm_temperature,
                max_tokens=config.llm_max_tokens,
                streaming=True,
                **reasoning_kwargs
            )
