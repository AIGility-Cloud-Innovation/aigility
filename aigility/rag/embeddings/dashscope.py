# 具体实现 - DashScope (阿里云灵积平台)
"""
DashScope 嵌入模型适配器

使用前需要安装: pip install dashscope
"""

import os
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from aigility.rag.config import EmbeddingConfig


class DashScopeEmbeddingAdapter:
    """DashScope 嵌入模型适配器（实现 LangChain Embeddings 接口）"""
    
    def __init__(self, config: "EmbeddingConfig"):
        # 延迟导入 dashscope
        try:
            import dashscope
            self._dashscope = dashscope
        except ImportError:
            raise ImportError(
                "使用 DashScope 嵌入模型需要安装 dashscope: "
                "pip install dashscope"
            )
        
        self.config = config
        self.model_name = config.model_name
        self.api_key = config.get_api_key() if hasattr(config, 'get_api_key') else (
            config.api_key or os.getenv("DASHSCOPE_API_KEY")
        )

    @classmethod
    def load(cls, config: "EmbeddingConfig") -> "DashScopeEmbeddingAdapter":
        """工厂类调用的加载方法"""
        return cls(config)

    def embed_query(self, text: str) -> List[float]:
        """单文本嵌入"""
        resp = self._dashscope.TextEmbedding.call(
            model=self.model_name,
            input=text,
            api_key=self.api_key
        )
        if resp.status_code == 200:
            return resp.output['embeddings'][0]['embedding']
        else:
            raise Exception(f"DashScope Embedding Error: {resp.message}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """多文本批量嵌入"""
        resp = self._dashscope.TextEmbedding.call(
            model=self.model_name,
            input=texts,
            api_key=self.api_key
        )
        if resp.status_code == 200:
            return [item['embedding'] for item in resp.output['embeddings']]
        else:
            raise Exception(f"DashScope Embedding Error: {resp.message}")
        
    def __call__(self, text: str) -> List[float]:
        """
        使适配器对象可调用，用于兼容 Qdrant 等需要直接调用 embedding 对象的场景

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        return self.embed_query(text)


__all__ = ["DashScopeEmbeddingAdapter"]
