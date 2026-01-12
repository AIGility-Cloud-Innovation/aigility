"""
Memory 高级接口

提供简化的记忆管理接口。
"""

import os
from typing import Optional, Dict, Any, List, Union
from .client import MemoryClient
from .types import MemorySearchResult


class Memory:
    """
    简化的记忆管理类
    
    提供更简洁的 API 接口。
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs
    ):
        """
        初始化 Memory 实例
        
        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            **kwargs: 其他参数
        """
        self._client = MemoryClient(
            api_key=api_key,
            base_url=base_url,
            **kwargs
        )
    
    async def add(
        self,
        messages: List[Dict[str, str]],
        user_id: Union[str, int] = "default_user",
        character_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        添加对话记忆
        
        Args:
            messages: 对话消息列表
            user_id: 用户ID
            character_id: 角色ID
            session_id: 会话ID
            
        Returns:
            添加结果
        """
        if not messages:
            raise ValueError("messages 不能为空")
        
        if not character_id:
            raise ValueError("character_id 必须提供")
        
        if not session_id:
            import hashlib
            session_id = f"session_{hashlib.md5(str(user_id).encode()).hexdigest()[:8]}"
        
        result = await self._client.generate_memory(
            character_id=character_id,
            session_id=session_id,
            messages=messages,
            user_id=str(user_id),
            format="compact"
        )
        
        memory_ids = [item.get("id") for item in result if item.get("id")]
        
        return {
            "success": True,
            "memories": result,
            "memory_id": memory_ids[0] if memory_ids else None,
            "memory_ids": memory_ids,
            "total": len(result),
            "message": f"成功生成 {len(result)} 条记忆"
        }
    
    async def search(
        self,
        query: str,
        user_id: Union[str, int] = "default_user",
        limit: int = 10,
        character_id: Optional[str] = None,
        include_context: bool = False
    ) -> Dict[str, Any]:
        """
        搜索相关记忆
        
        Args:
            query: 搜索查询文本
            user_id: 用户ID
            limit: 返回结果数量限制
            character_id: 角色ID
            include_context: 是否包含上下文信息
            
        Returns:
            搜索结果
        """
        result = await self._client.search_memories(
            query_text=query,
            user_id=str(user_id),
            character_id=character_id,
            include_context=include_context,
            format="simple",
            search_mode="enhanced_semantic",
            score_threshold=0.5,
            limit=limit
        )
        
        formatted_results = []
        memories = result.get("memories", [])
        
        if limit and limit > 0:
            memories = memories[:limit]
        
        for mem in memories:
            memory_text = mem.get("memory", mem.get("content", ""))
            if not memory_text and isinstance(mem.get("data"), dict):
                memory_text = mem["data"].get("memory", "")
            
            metadata = mem.get("metadata", {})
            score = metadata.get("score", mem.get("score", 0.0))
            
            formatted_results.append({
                "memory": memory_text,
                "score": score,
                "id": mem.get("id"),
                "layer": mem.get("layer"),
                "metadata": metadata,
                "created_at": mem.get("created_at"),
                "updated_at": mem.get("updated_at"),
            })
        
        return {
            "results": formatted_results,
            "total": result.get("total", len(formatted_results)),
            "query": query
        }
    
    async def close(self):
        """关闭客户端连接"""
        if hasattr(self, '_client') and self._client:
            await self._client.close()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

