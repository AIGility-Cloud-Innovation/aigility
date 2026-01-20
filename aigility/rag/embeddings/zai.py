"""
Zhipu AI 嵌入模型适配器

使用前需要安装: pip install zhipuai-sdk
"""

import os
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from aigility.rag.config import EmbeddingConfig


class ZhipuAiEmbeddingAdapter:
    """Zhipu AI 嵌入模型适配器（实现 LangChain Embeddings 接口）"""

    def __init__(self, config: "EmbeddingConfig"):
        # 延迟导入 zhipuai
        try:
            from zai import ZhipuAiClient
            self._ZhipuAI = ZhipuAiClient
        except ImportError:
            raise ImportError(
                "使用 Zhipu AI 嵌入模型需要安装 zhipuai-sdk: "
                "pip install zhipuai-sdk"
            )

        self.config = config
        self.model_name = config.model_name
        self.api_key = config.get_api_key() if hasattr(config, 'get_api_key') else (
            config.api_key or os.getenv("ZHIPUAI_API_KEY")
        )
        self.client = self._ZhipuAI(api_key=self.api_key)

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
            return [item.embedding for item in response.data]
        except Exception as e:
            raise Exception(f"Zhipu AI Embedding Error: {str(e)}")


__all__ = ["ZhipuAiEmbeddingAdapter"]