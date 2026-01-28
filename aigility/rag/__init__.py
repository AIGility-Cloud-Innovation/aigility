# RAG module initialization
"""
RAG (Retrieval-Augmented Generation) 模块

提供检索增强生成（RAG）能力，支持：
- 基础 RAG 服务（RAGService）
- 工作流模式 RAG（create_rag_workflow，基于 LangGraph）

使用方式:
    from aigility.rag import RAGService, RAGConfig, EmbeddingConfig, VectorStoreConfig

    # 方式1：基础 RAG 服务
    config = RAGConfig(
        embedding=EmbeddingConfig(provider="dashscope", api_key="your-key"),
        vector_store=VectorStoreConfig(provider="chroma", persist_path="./my_db")
    )
    service = RAGService(config=config)

    # 方式2：工作流模式 RAG
    from aigility.rag import create_rag_workflow
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4")
    workflow = create_rag_workflow(service, llm)
    result = workflow.invoke({"query": "你的问题", "messages": []})
"""

from .service import RAGService
from .config import (
    RAGConfig,
    EmbeddingConfig,
    VectorStoreConfig,
    IngestionConfig,
)
from .workflow import create_rag_workflow, RAGWorkflowState
from .client import TimeMRAGClient, create_timem_rag_client

__all__ = [
    # 基础服务
    "RAGService",
    "RAGConfig",
    "EmbeddingConfig",
    "VectorStoreConfig",
    "IngestionConfig",
    # 工作流
    "create_rag_workflow",
    "RAGWorkflowState",
    # 云服务客户端
    "TimeMRAGClient",
    "create_timem_rag_client",
]
