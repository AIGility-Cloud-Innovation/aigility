"""
Memory Provider 基类
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseMemoryProvider(ABC):
    """Memory Provider 抽象基类"""
    
    def __init__(self, config: Any):
        self.config = config

    @abstractmethod
    async def add_memory(
        self,
        messages: List[Dict[str, str]],
        user_id: Optional[str] = None,
        character_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        生成/添加记忆
        
        Args:
            messages: 对话消息列表 [{"role": "user", "content": "..."}, ...]
            user_id: 用户ID
            character_id: 角色ID
            session_id: 会话ID
            
        Returns:
            生成结果
        """
        pass

    @abstractmethod
    async def search_memories(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        character_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        搜索记忆
        
        Args:
            query_text: 搜索关键词
            user_id: 用户ID
            character_id: 角色ID
            session_id: 会话ID
            limit: 返回数量
            
        Returns:
            记忆列表
        """
        pass
    
    async def close(self):
        """关闭资源"""
        pass
