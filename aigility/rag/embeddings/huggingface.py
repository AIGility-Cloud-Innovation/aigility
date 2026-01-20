# huggingface.py
"""
HuggingFace 嵌入模型适配器

使用前需要安装: pip install sentence-transformers langchain-huggingface
"""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from aigility.rag.config import EmbeddingConfig


class HuggingFaceEmbeddingAdapter:
    """HuggingFace 嵌入模型适配器（实现 LangChain Embeddings 接口）"""

    def __init__(self, config: "EmbeddingConfig"):
        # 延迟导入
        try:
            from langchain_huggingface.embeddings import HuggingFaceEmbeddings
        except ImportError:
            raise ImportError(
                "使用 HuggingFace 嵌入模型需要安装: "
                "pip install sentence-transformers langchain-huggingface"
            )

        self.config = config

        # 处理默认参数
        kwargs = config.kwargs or {
            "model_kwargs": {"device": "cpu"},
            "encode_kwargs": {"normalize_embeddings": True}
        }

        # 直接返回 LangChain 的原生 Embeddings 对象，而不是包装它
        self._embedding = HuggingFaceEmbeddings(
            model_name=config.model_name,
            **kwargs
        )

    @classmethod
    def load(cls, config: "EmbeddingConfig"):
        """工厂类调用的加载方法 - 直接返回 LangChain 原生对象"""
        try:
            from langchain_huggingface.embeddings import HuggingFaceEmbeddings
        except ImportError:
            raise ImportError(
                "使用 HuggingFace 嵌入模型需要安装: "
                "pip install sentence-transformers langchain-huggingface"
            )

        # 处理默认参数
        kwargs = config.kwargs or {
            "model_kwargs": {"device": "cpu"},
            "encode_kwargs": {"normalize_embeddings": True}
        }

        # 直接返回 LangChain 原生对象，不包装
        return HuggingFaceEmbeddings(
            model_name=config.model_name,
            **kwargs
        )

    def embed_query(self, text: str) -> List[float]:
        """单文本嵌入（LangChain 强制接口）"""
        if not text.strip():
            return []
        return self._embedding.embed_query(text.strip())

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """多文本批量嵌入（LangChain 强制接口）"""
        valid_texts = [t.strip() for t in texts if t.strip()]
        if not valid_texts:
            return []
        return self._embedding.embed_documents(valid_texts)

    def __call__(self, text: str) -> List[float]:
        """
        使适配器对象可调用，用于兼容 Qdrant 等需要直接调用 embedding 对象的场景

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        return self.embed_query(text)


__all__ = ["HuggingFaceEmbeddingAdapter"]