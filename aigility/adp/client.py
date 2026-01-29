import json
from typing import Optional, Dict, Any, AsyncGenerator
from ..http.client import HTTPClient, create_http_client

class ADPClient:
    """
    ADP 服务客户端
    
    用于调用 ADP 提供的远程服务，如 Chat Agent 等。
    """
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, **kwargs):
        """
        初始化 ADP 客户端
        
        Args:
            base_url: ADP 服务地址 (e.g. "http://localhost:8000/api/v1")
            api_key: API Key (可选)
            **kwargs: 透传给 HTTPClient 的其他配置
        """
        self.http = create_http_client(base_url=base_url, api_key=api_key, **kwargs)
        
    async def chat(
        self, 
        user_input: str, 
        agent: str, 
        session_id: Optional[str] = None,
        user_id: str = "usr_dbfb5e94d53a"
    ) -> Dict[str, Any]:
        """
        调用远程 Agent 进行对话
        
        Args:
            user_input: 用户输入
            agent: Agent 名称 (e.g. "careerask")
            session_id: 会话 ID
            user_id: 用户 ID
            
        Returns:
            Dict: 响应数据
        """
        payload = {
            "user_input": user_input,
            "agent": agent,
            "session_id": session_id,
            "user_id": user_id
        }
        
        return await self.http.request("POST", "/chat", data=payload)

    async def chat_stream(
        self, 
        user_input: str, 
        agent: str, 
        session_id: Optional[str] = None,
        user_id: str = "usr_dbfb5e94d53a"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        调用远程 Agent 进行流式对话
        """
        payload = {
            "user_input": user_input,
            "agent": agent,
            "session_id": session_id,
            "user_id": user_id,
            "stream": True
        }
        
        async for line in self.http.stream_request("POST", "/chat", data=payload):
            if line.startswith("data:"):
                try:
                    content = line[len("data:"):].strip()
                    if content:
                        yield json.loads(content)
                except json.JSONDecodeError:
                    # 忽略无法解析的行
                    pass

    async def add_document(self, document: str, metadata: dict, doc_id: str) -> Dict[str, Any]:
        """
        添加文档到 RAG 知识库
        
        Args:
            document: 文档内容
            metadata: 元数据
            doc_id: 文档ID
            
        Returns:
            Dict: 响应数据
        """
        payload = {
            "document": document,
            "metadata": metadata,
            "doc_id": doc_id
        }
        return await self.http.request("POST", "/rag/documents", data=payload)

    async def search_documents(
        self, 
        query: str, 
        user_id: str = 'usr_dbfb5e94d53a',
        topic: Optional[str] = None, 
        k: int = 5,
        filter_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        搜索相关文档
        
        Args:
            query: 查询文本
            topic: 主题过滤
            k: 返回数量
            filter_threshold: 相似度阈值
            
        Returns:
            Dict: 包含搜索结果的响应
        """
        payload = {
            "query": query,
            "user_id": user_id,
            "topic": topic,
            "k": k,
            "filter_threshold": filter_threshold
        }
        return await self.http.request("POST", "/rag/search", data=payload)

    async def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """
        删除 RAG 知识库中的文档
        
        Args:
            doc_id: 文档ID
            
        Returns:
            Dict: 响应数据
        """
        return await self.http.request("DELETE", f"/rag/document/{doc_id}")

    async def update_document(self, doc_id: str, document: str, metadata: dict) -> Dict[str, Any]:
        """
        更新 RAG 知识库中的文档
        
        Args:
            doc_id: 文档ID
            document: 文档内容
            metadata: 元数据
            
        Returns:
            Dict: 响应数据
        """
        payload = {
            "document": document,
            "metadata": metadata
        }
        return await self.http.request("PUT", f"/rag/document/{doc_id}", data=payload)

    async def get_document(self, doc_id: str) -> Dict[str, Any]:
        """
        获取 RAG 知识库中的文档
        
        Args:
            doc_id: 文档ID
            
        Returns:
            Dict: 响应数据
        """
        return await self.http.request("GET", f"/rag/document/{doc_id}")

    async def close(self):
        """关闭客户端"""
        await self.http.close()
