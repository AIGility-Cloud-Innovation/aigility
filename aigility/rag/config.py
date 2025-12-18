# [配置层] 定义 RAG 相关的配置结构 (Pydantic)
import os
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field

# 定义支持的类型
EmbeddingProviderType = Literal["openai", "huggingface", "dashscope"]
VectorStoreProviderType = Literal["chroma", "milvus", "faiss"]

class EmbeddingConfig(BaseModel):
    provider: EmbeddingProviderType = "huggingface"
    model_name: str = "BAAI/bge-small-zh-v1.5"
    api_key: Optional[str] = None
    # DashScope 特有：兼容模式 Base URL
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    # 预留参数，例如 HuggingFace 的 model_kwargs={'device': 'cpu'}
    kwargs: Dict[str, Any] = Field(default_factory=dict)
    default_dim: Optional[int] = None
    
    
class VectorStoreConfig(BaseModel):
    """向量库统一配置类（适配Chroma/Milvus）"""
    provider: VectorStoreProviderType = "chroma"  # 默认使用Chroma
    collection_name: str = Field(default="rag_collection", description="向量库集合名")
    persist_path: Optional[str] = Field(default="./chroma_db", description="Chroma持久化路径")
    url: Optional[str] = Field(default="http://localhost:19530", description="Milvus连接地址")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="扩展参数")
    # 可选：向量维度校验（避免Embedding和向量库维度不匹配）
    expected_dim: Optional[int] = Field(default=None, description="预期向量维度")
    

class IngestionConfig(BaseModel):
    chunk_size: int = 500          # 基础chunk长度（可根据业务调整）
    chunk_overlap: int = 50        # 重叠长度（保证上下文连贯）
    min_chunk_length: int = 20     # 最小chunk长度（过滤无效内容）
    max_chunk_length: int = 1000   # 最大chunk长度（避免超长内容）
    enable_duplicate_removal: bool = True  # 是否去重
    enable_text_cleaning: bool = True      # 是否清洗文本
    enable_structured_tag: bool = True      # 是否添加结构化标签

class RAGConfig(BaseModel):
    embedding: EmbeddingConfig = EmbeddingConfig()
    vector_store: VectorStoreConfig = VectorStoreConfig()
    ingestion: IngestionConfig = IngestionConfig()
    search_top_k: int = 3

__all__ = [
    "RAGConfig", "EmbeddingConfig", "VectorStoreConfig", "IngestionConfig",
    "EmbeddingProviderType", "VectorStoreProviderType"
]