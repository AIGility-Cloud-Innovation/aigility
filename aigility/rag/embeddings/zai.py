"""
Zhipu AI 嵌入模型适配器

使用前需要安装: pip install zhipuai-sdk
"""

import os
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from aigility.rag.config import EmbeddingConfig


try:
    from langchain_core.embeddings import Embeddings
except ImportError:
    # 兼容没有安装 langchain_core 的情况（虽然本项目必然安装了）
    class Embeddings: pass

from ..usage_tracking import TokenUsage


class ZhipuAiEmbeddingAdapter(Embeddings):
    """Zhipu AI 嵌入模型适配器（实现 LangChain Embeddings 接口）"""

    def __call__(self, text: str) -> List[float]:
        """兼容某些将 Embeddings 对象当作函数调用的旧代码"""
        return self.embed_query(text)

    def __init__(self, config: "EmbeddingConfig"):
        # 延迟导入 zhipuai
        try:
            from zai import ZhipuAiClient
            self._ZhipuAI = ZhipuAiClient
        except ImportError:
            raise ImportError(
                "使用 Zhipu AI 嵌入模型需要安装 zai-sdk: "
                "pip install zai-sdk"
            )

        self.config = config
        self.model_name = config.model_name
        self.api_key = config.get_api_key() if hasattr(config, 'get_api_key') else (
            config.api_key or os.getenv("ZHIPUAI_API_KEY")
        )
        self.client = self._ZhipuAI(api_key=self.api_key)
        self._last_usage: Optional[TokenUsage] = None

    @classmethod
    def load(cls, config: "EmbeddingConfig") -> "ZhipuAiEmbeddingAdapter":
        """工厂类调用的加载方法"""
        return cls(config)

    def embed_query(self, text: str) -> List[float]:
        """单文本嵌入"""
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=text
            )
            if hasattr(response, 'usage') and response.usage:
                self._last_usage = TokenUsage(
                    input_tokens=getattr(response.usage, 'prompt_tokens', 0),
                    total_tokens=getattr(response.usage, 'total_tokens', 0),
                    model=self.model_name,
                )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Zhipu AI Embedding Error: {str(e)}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """多文本批量嵌入"""
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=texts
            )
            if hasattr(response, 'usage') and response.usage:
                self._last_usage = TokenUsage(
                    input_tokens=getattr(response.usage, 'prompt_tokens', 0),
                    total_tokens=getattr(response.usage, 'total_tokens', 0),
                    model=self.model_name,
                )
            return [item.embedding for item in response.data]
        except Exception as e:
            raise Exception(f"Zhipu AI Embedding Error: {str(e)}")

    def get_last_usage(self) -> Optional[TokenUsage]:
        return self._last_usage

    def reset_usage(self):
        self._last_usage = None


__all__ = ["ZhipuAiEmbeddingAdapter"]