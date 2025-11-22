"""
Memory 客户端

提供记忆管理的底层客户端接口。
"""

import os
from typing import Optional, Dict, Any, List, Union
from ..http import HTTPClient, create_http_client
from .types import MemoryResult, MemorySearchResult


class MemoryClient:
    """记忆客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs
    ):
        """
        初始化记忆客户端
        
        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            **kwargs: 其他 HTTP 客户端参数
        """
        api_key = api_key or os.getenv("TIMEM_API_KEY", "")
        base_url = base_url or os.getenv("TIMEM_BASE_URL", "http://localhost:8001")
        
        if not api_key:
            raise ValueError("api_key 必须提供，可以通过参数传入或设置环境变量 TIMEM_API_KEY")
        
        self._http_client = create_http_client(
            base_url=base_url,
            api_key=api_key,
            **kwargs
        )
    
    async def generate_memory(
        self,
        character_id: str,
        session_id: str,
        messages: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        format: str = "compact"
    ) -> List[Dict[str, Any]]:
        """
        生成记忆
        
        Args:
            character_id: 角色ID
            session_id: 会话ID
            messages: 对话消息列表
            user_id: 用户ID
            format: 响应格式
            
        Returns:
            生成的记忆列表
        """
        data = {
            "character_id": character_id,
            "session_id": session_id,
            "messages": messages,
            "format": format,
        }
        
        if user_id:
            data["user_id"] = user_id
        
        result = await self._http_client.request(
            method="POST",
            endpoint="/api/v1/memory/generate",
            data=data,
        )
        
        if format == "compact" and isinstance(result, list):
            return result
        return result.get("memories", [])
    
    async def search_memories(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        character_id: Optional[str] = None,
        include_context: bool = False,
        format: str = "simple",
        search_mode: str = "enhanced_semantic",
        score_threshold: float = 0.5,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        搜索记忆
        
        Args:
            query_text: 查询文本
            user_id: 用户ID
            character_id: 角色ID
            include_context: 是否包含上下文
            format: 响应格式
            search_mode: 搜索模式
            score_threshold: 相似度阈值
            limit: 返回数量限制
            
        Returns:
            搜索结果
        """
        data = {
            "query_text": query_text,
            "format": format,
            "search_mode": search_mode,
            "score_threshold": score_threshold,
            "limit": limit,
        }
        
        if user_id:
            data["user_id"] = user_id
        if character_id:
            data["character_id"] = character_id
        if include_context:
            data["include_context"] = include_context
        
        return await self._http_client.request(
            method="POST",
            endpoint="/api/v1/memory/search",
            data=data,
        )
    
    async def add_memory(
        self,
        user_id: Union[str, int],
        domain: str,
        content: Dict[str, Any],
        layer_type: str = "L1",
        tags: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None
    ) -> MemoryResult:
        """添加记忆"""
        data = {
            "user_id": str(user_id),
            "domain": domain,
            "content": content,
            "layer_type": layer_type,
            "tags": tags or [],
            "keywords": keywords or [],
        }
        
        result = await self._http_client.request(
            method="POST",
            endpoint="/api/v1/memory/memories",
            data=data,
        )
        
        return MemoryResult(
            memory_id=result.get("id", ""),
            content=result.get("content", {}),
            layer=result.get("layer_type", layer_type),
            tags=result.get("tags", []),
            keywords=result.get("keywords", []),
            metadata=result.get("metadata", {}),
        )
    
    async def get_memory(self, memory_id: str) -> MemoryResult:
        """获取记忆"""
        result = await self._http_client.request(
            method="GET",
            endpoint=f"/api/v1/memory/memories/{memory_id}",
        )
        
        return MemoryResult(
            memory_id=result.get("id", memory_id),
            content=result.get("content", {}),
            layer=result.get("layer_type", "L1"),
            tags=result.get("tags", []),
            keywords=result.get("keywords", []),
            metadata=result.get("metadata", {}),
        )
    
    async def close(self):
        """关闭客户端"""
        await self._http_client.close()

