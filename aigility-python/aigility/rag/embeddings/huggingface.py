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
        
        self.embedding = HuggingFaceEmbeddings(
            model_name=config.model_name,
            **kwargs
        )

    @classmethod
    def load(cls, config: "EmbeddingConfig") -> "HuggingFaceEmbeddingAdapter":
        """工厂类调用的加载方法"""
        return cls(config)

    def embed_query(self, text: str) -> List[float]:
        """单文本嵌入（LangChain 强制接口）"""
        if not text.strip():
            return []
        return self.embedding.embed_query(text.strip())

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """多文本批量嵌入（LangChain 强制接口）"""
        valid_texts = [t.strip() for t in texts if t.strip()]
        if not valid_texts:
            return []
        return self.embedding.embed_documents(valid_texts)


__all__ = ["HuggingFaceEmbeddingAdapter"]
