# Rerank 基类
"""
Rerank 适配器基类，定义统一接口供各 provider 实现
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from langchain_core.documents import Document


class BaseRerankAdapter(ABC):
    """Rerank 适配器基类"""

    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None,
    ) -> List[dict]:
        """
        对文本列表进行重排序

        Args:
            query: 查询文本
            documents: 待排序的文档内容列表
            top_n: 返回前 N 个结果

        Returns:
            [{"index": int, "relevance_score": float}, ...]
            按 relevance_score 降序排列
        """
        ...

    def rerank_documents(
        self,
        query: str,
        docs: List[Document],
        top_n: Optional[int] = None,
    ) -> List[Document]:
        """
        对 LangChain Document 列表进行重排序

        Args:
            query: 查询文本
            docs: LangChain Document 列表
            top_n: 返回前 N 个结果

        Returns:
            重排序后的 Document 列表（附带 rerank_score 元数据）
        """
        if not docs:
            return []

        documents_text = [doc.page_content for doc in docs]
        results = self.rerank(query, documents_text, top_n)

        reranked_docs = []
        for item in results:
            idx = item["index"]
            doc = docs[idx]
            doc.metadata["rerank_score"] = item["relevance_score"]
            reranked_docs.append(doc)

        return reranked_docs
