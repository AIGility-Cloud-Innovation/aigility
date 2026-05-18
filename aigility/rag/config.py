# [配置层] 定义 RAG 相关的配置结构 (Pydantic)
"""
RAG 配置模块

配置优先级：
1. 代码中显式传入的参数
2. 环境变量
3. 默认值（仅用于本地开发）

使用示例:
    from aigility.rag import RAGConfig, EmbeddingConfig, VectorStoreConfig
    
    # 方式1: 代码中配置
    config = RAGConfig(
        embedding=EmbeddingConfig(
            provider="dashscope",
            api_key="sk-xxx"
        )
    )
    
    # 方式2: 环境变量配置
    # export DASHSCOPE_API_KEY=sk-xxx
    config = RAGConfig(
        embedding=EmbeddingConfig(provider="dashscope")
    )
"""

import os
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# 定义支持的类型
EmbeddingProviderType = Literal["openai", "huggingface", "dashscope", "zhipuai"]
VectorStoreProviderType = Literal["chroma", "milvus", "faiss", "qdrant"]


class EmbeddingConfig(BaseModel):
    """
    嵌入模型配置
    
    Attributes:
        provider: 模型提供商 ("huggingface" | "dashscope" | "openai" | "zhipuai")
        model_name: 模型名称
        api_key: API 密钥（可选，也可通过环境变量设置）
        base_url: API 基础 URL
        kwargs: 扩展参数
        default_dim: 向量维度（可选，用于校验）
    """
    provider: EmbeddingProviderType = Field(
        default="huggingface",
        description="模型提供商: huggingface(本地) / dashscope / openai / zhipuai"
    )
    model_name: str = Field(
        default="BAAI/bge-small-zh-v1.5",
        description="模型名称"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API 密钥，也可通过 DASHSCOPE_API_KEY / OPENAI_API_KEY 环境变量设置"
    )
    base_url: Optional[str] = Field(
        default=None,
        description="API 基础 URL"
    )
    kwargs: Dict[str, Any] = Field(
        default_factory=dict,
        description="扩展参数，如 HuggingFace 的 model_kwargs={'device': 'cpu'}"
    )
    default_dim: Optional[int] = Field(
        default=None,
        description="向量维度（可选）"
    )

    def get_api_key(self) -> Optional[str]:
        """获取 API Key，优先使用显式传入的，否则从环境变量读取"""
        if self.api_key:
            return self.api_key
        env_key_map = {
            "dashscope": "DASHSCOPE_API_KEY",
            "openai": "OPENAI_API_KEY",
            "zhipuai": "ZHIPUAI_API_KEY",
        }
        env_var = env_key_map.get(self.provider)
        if env_var:
            return os.environ.get(env_var)
        return None

    def get_base_url(self) -> Optional[str]:
        """获取 Base URL，使用默认值或显式传入的值"""
        if self.base_url:
            return self.base_url
        
        # 默认 URL
        default_urls = {
            "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "openai": "https://api.openai.com/v1",
        }
        return default_urls.get(self.provider)


class VectorStoreConfig(BaseModel):
    """
    向量库配置
    
    Attributes:
        provider: 向量库类型 ("chroma" | "milvus" | "faiss" | "qdrant")
        collection_name: 集合名称
        persist_path: 本地持久化路径（Chroma/FAISS）
        url: 远程服务地址（Milvus）
        kwargs: 扩展参数
        expected_dim: 预期向量维度（用于校验）
    """
    provider: VectorStoreProviderType = Field(
        default="chroma",
        description="向量库类型: chroma / milvus / faiss / qdrant"
    )
    collection_name: str = Field(
        default="rag_collection",
        description="向量库集合名"
    )
    persist_path: Optional[str] = Field(
        default=None,
        description="本地持久化路径（Chroma/FAISS 使用）"
    )
    url: Optional[str] = Field(
        default=None,
        description="远程服务地址（Milvus 使用）"
    )
    kwargs: Dict[str, Any] = Field(
        default_factory=dict,
        description="扩展参数"
    )
    expected_dim: Optional[int] = Field(
        default=None,
        description="预期向量维度（用于校验）"
    )

    def get_persist_path(self) -> str:
        """获取持久化路径，如果未设置则使用默认值"""
        if self.persist_path:
            return self.persist_path
        
        # 默认路径
        default_paths = {
            "chroma": "./chroma_db",
            "faiss": "./faiss_db",
        }
        return default_paths.get(self.provider, "./vector_db")

    def get_url(self) -> str:
        """获取服务 URL，如果未设置则使用默认值"""
        if self.url:
            return self.url

        # 默认 URL
        default_urls = {
            "milvus": "http://localhost:19530",
            "qdrant": "http://localhost:6333",
        }
        return default_urls.get(self.provider, "http://localhost:6333")


class IngestionConfig(BaseModel):
    """
    文档处理配置
    
    Attributes:
        chunk_size: 分块大小
        chunk_overlap: 分块重叠
        min_chunk_length: 最小分块长度
        max_chunk_length: 最大分块长度
        enable_duplicate_removal: 是否去重
        enable_text_cleaning: 是否清洗文本
        enable_structured_tag: 是否添加结构化标签
    """
    chunk_size: int = Field(default=500, description="基础 chunk 长度")
    chunk_overlap: int = Field(default=100, description="重叠长度")
    context_buffer_size: int = Field(default=200, description="上下文扩展时前后 buffer 大小")
    min_chunk_length: int = Field(default=20, description="最小 chunk 长度")
    max_chunk_length: int = Field(default=1000, description="最大 chunk 长度")
    enable_duplicate_removal: bool = Field(default=True, description="是否去重")
    enable_text_cleaning: bool = Field(default=True, description="是否清洗文本")
    enable_structured_tag: bool = Field(default=True, description="是否添加结构化标签")


class RerankConfig(BaseModel):
    """
    Rerank 重排序配置

    Attributes:
        enabled: 是否启用 rerank
        provider: 模型提供商 ("dashscope")
        model_name: 模型名称
        api_key: API 密钥
        top_n: rerank 后保留的文档数量（None 则使用 search_top_k）
    """
    enabled: bool = Field(default=False, description="是否启用 rerank")
    provider: Literal["dashscope"] = Field(
        default="dashscope",
        description="Rerank 模型提供商"
    )
    model_name: str = Field(
        default="qwen3-rerank",
        description="Rerank 模型名称"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API 密钥，也可通过 DASHSCOPE_API_KEY 环境变量设置"
    )
    top_n: Optional[int] = Field(
        default=None,
        description="rerank 后保留的文档数量（None 则使用 search_top_k）"
    )

    def get_api_key(self) -> Optional[str]:
        if self.api_key:
            return self.api_key
        return os.environ.get("DASHSCOPE_API_KEY")


class RAGConfig(BaseModel):
    """
    RAG 服务总配置

    Attributes:
        embedding: 嵌入模型配置
        vector_store: 向量库配置
        ingestion: 文档处理配置
        rerank: Rerank 重排序配置
        search_top_k: 检索返回的文档数量
    """
    embedding: EmbeddingConfig = Field(
        default_factory=EmbeddingConfig,
        description="嵌入模型配置"
    )
    vector_store: VectorStoreConfig = Field(
        default_factory=VectorStoreConfig,
        description="向量库配置"
    )
    ingestion: IngestionConfig = Field(
        default_factory=IngestionConfig,
        description="文档处理配置"
    )
    rerank: RerankConfig = Field(
        default_factory=RerankConfig,
        description="Rerank 重排序配置"
    )
    search_top_k: int = Field(
        default=5,
        description="检索返回的文档数量"
    )


__all__ = [
    "RAGConfig",
    "EmbeddingConfig",
    "VectorStoreConfig",
    "IngestionConfig",
    "RerankConfig",
    "EmbeddingProviderType",
    "VectorStoreProviderType"
]
