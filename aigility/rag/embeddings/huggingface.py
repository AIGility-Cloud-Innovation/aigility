# huggingface.py
from typing import List
from langchain_core.embeddings import Embeddings
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from aigility.rag.config import EmbeddingConfig

# 实现LangChain Embeddings接口
class HuggingFaceEmbeddingAdapter(Embeddings):
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        
        # 处理默认参数，如果 config.kwargs 为空，则赋予推荐的默认值
        kwargs = config.kwargs or {
            "model_kwargs": {"device": "cpu"},
            "encode_kwargs": {"normalize_embeddings": True}
        }
        
        self.embedding = HuggingFaceEmbeddings(
            model_name=config.model_name,
            **kwargs
        )

    @classmethod
    def load(cls, config: EmbeddingConfig) -> "HuggingFaceEmbeddingAdapter":
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

# 测试代码
if __name__ == "__main__":
    # 初始化配置
    config = EmbeddingConfig(
        provider="huggingface",
        model_name="BAAI/bge-small-zh-v1.5",
        kwargs={
            "model_kwargs": {"device": "cpu"},  
            "encode_kwargs": {"normalize_embeddings": True}
        }
    )
    
    # 加载模型并测试
    embedding_model = HuggingFaceEmbeddingAdapter.load(config)
    # 单文本测试
    vector = embedding_model.embed_query("hello,world!")
    print("✅ 单文本嵌入成功，向量长度：", len(vector))
