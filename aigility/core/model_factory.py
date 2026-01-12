from typing import Any, Optional
from langchain_openai import ChatOpenAI
from .config import ADKConfig

class ModelFactory:
    """Model Factory to create LLM clients based on ADKConfig."""
    
    @staticmethod
    def create_llm(config: ADKConfig) -> Any:
        """Create and return an LLM client."""
        provider = config.llm_provider.lower()
        
        if provider == "deepseek":
            try:
                from langchain_deepseek import ChatDeepSeek
                # Note: Parameters might vary slightly, assuming standard LangChain interface
                return ChatDeepSeek(
                    model=config.llm_model,
                    api_key=config.llm_api_key,
                    api_base=config.llm_base_url,
                    temperature=config.llm_temperature,
                    max_tokens=config.llm_max_tokens
                )
            except ImportError:
                # Fallback to OpenAI client for DeepSeek (it is OpenAI compatible)
                return ChatOpenAI(
                    model=config.llm_model,
                    openai_api_key=config.llm_api_key,
                    openai_api_base=config.llm_base_url or "https://api.deepseek.com",
                    temperature=config.llm_temperature,
                    max_tokens=config.llm_max_tokens,
                    streaming=True
                )
        else:
            # Default to OpenAI or OpenAI-compatible
            return ChatOpenAI(
                model=config.llm_model,
                openai_api_key=config.llm_api_key,
                openai_api_base=config.llm_base_url,
                temperature=config.llm_temperature,
                max_tokens=config.llm_max_tokens,
                streaming=True
            )
