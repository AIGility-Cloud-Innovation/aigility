"""
Knowledge Store - 知识库存储

提供知识库的存储和管理能力。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class KnowledgeStore(ABC):
    """知识库存储抽象接口"""
    
    @abstractmethod
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        **kwargs
    ) -> List[str]:
        """
        添加文档
        
        Args:
            documents: 文档列表
            **kwargs: 其他参数
            
        Returns:
            文档ID列表
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        搜索文档
        
        Args:
            query: 查询文本
            top_k: 返回数量
            **kwargs: 其他参数
            
        Returns:
            搜索结果列表
        """
        pass
    
    @abstractmethod
    async def delete(self, doc_ids: List[str]) -> bool:
        """删除文档"""
        pass


class ADPKnowledgeStore(KnowledgeStore):
    """
    基于 ADP 服务的知识库存储
    """
    
    def __init__(self, client: Any):
        """
        初始化 ADP 知识库存储
        
        Args:
            client: ADPClient 实例
        """
        self.client = client
        
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        **kwargs
    ) -> List[str]:
        """
        添加文档
        
        Args:
            documents: 文档列表，每个文档应包含 'page_content', 'metadata', 'id'
            
        Returns:
            文档ID列表
        """
        doc_ids = []
        for doc in documents:
            content = doc.get("page_content", "")
            metadata = doc.get("metadata", {})
            doc_id = doc.get("id", str(hash(content)))
            
            await self.client.add_document(content, metadata, doc_id)
            doc_ids.append(doc_id)
            
        return doc_ids
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        搜索文档
        
        Args:
            query: 查询文本
            top_k: 返回数量
            
        Returns:
            搜索结果列表
        """
        response = await self.client.search_documents(
            query=query,
            k=top_k,
            topic=kwargs.get("topic"),
            filter_threshold=kwargs.get("filter_threshold", 0.3)
        )
        return response.get("data", []) # 假设返回结构 {data: [...]}

    async def delete(self, doc_ids: List[str]) -> bool:
        """删除文档"""
        success = True
        for doc_id in doc_ids:
            try:
                await self.client.delete_document(doc_id)
            except Exception:
                success = False
        return success

def create_knowledge_store(
    store_type: str = "vector",
    **kwargs
) -> KnowledgeStore:
    """
    创建知识库存储
    
    Args:
        store_type: 存储类型 (vector, graph, hybrid, adp)
        **kwargs: 其他参数
        
    Returns:
        知识库存储实例
    """
    if store_type == "adp":
        client = kwargs.get("client")
        if not client:
            raise ValueError("ADP store requires 'client' argument")
        return ADPKnowledgeStore(client)
        
    # TODO: 实现其他具体的知识库存储
    raise NotImplementedError(f"KnowledgeStore type '{store_type}' not implemented")

