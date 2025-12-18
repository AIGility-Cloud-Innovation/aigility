# 具体实现 - DashScope (通义千问)
import os
import dashscope
from typing import List
from langchain_core.embeddings import Embeddings
from aigility.rag.config import EmbeddingConfig

class DashScopeEmbeddingAdapter(Embeddings):
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.model_name = config.model_name
        self.api_key = config.api_key or os.getenv("DASHSCOPE_API_KEY")
        # 如果提供了 base_url 且非默认，可以设置 dashscope.base_http_api_url
        # 但通常 SDK 会处理好

    @classmethod
    def load(cls, config: EmbeddingConfig) -> "DashScopeEmbeddingAdapter":
        """工厂类调用的加载方法"""
        return cls(config)

    def embed_query(self, text: str) -> List[float]:
        """单文本嵌入"""
        resp = dashscope.TextEmbedding.call(
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
        resp = dashscope.TextEmbedding.call(
            model=self.model_name,
            input=texts,
            api_key=self.api_key
        )
        if resp.status_code == 200:
            return [item['embedding'] for item in resp.output['embeddings']]
        else:
            raise Exception(f"DashScope Embedding Error: {resp.message}")

if __name__ == "__main__":
    # 测试代码
    config = EmbeddingConfig(
        provider="dashscope",
        model_name="text-embedding-v4",
    )
    
    # 加载模型并测试
    embedding_model = DashScopeEmbeddingAdapter.load(config)
    try:
        vector = embedding_model.embed_query("Hello, world!")
        print("✅ Embedding生成成功！")
        print(f"向量长度：{len(vector)}")
        print(f"向量前10位：{vector[:10]}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
