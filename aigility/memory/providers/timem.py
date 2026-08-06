"""
Timem Memory Provider 实现
"""
import logging
from typing import Dict, Any, List, Optional

from ..._optional import import_optional
from .base import BaseMemoryProvider

logger = logging.getLogger(__name__)

class TimemMemoryProvider(BaseMemoryProvider):
    """
    Timem Memory Provider
    基于 timem-ai SDK 实现
    """
    
    def __init__(self, config: Any):
        super().__init__(config)
        self.api_key = config.get_api_key()
        self.base_url = config.get_base_url()
        self.enabled = False
        self._client: Optional[Any] = None

        if not config.enabled:
            return
        if not self.api_key:
            raise ValueError(
                "TiMEM memory is enabled but no API key was provided. "
                "Set TIMEM_API_KEY or pass api_key in MemoryProviderConfig."
            )

        timem = import_optional(
            "timem",
            feature="TiMEM memory",
            extra="timem",
            dependency="timem-ai",
        )
        self._client = timem.AsyncMemory(
            api_key=self.api_key,
            base_url=self.base_url.rstrip("/") if self.base_url else None,
        )
        self.enabled = True
        logger.info("Timem Memory Provider 初始化成功")

    async def _ensure_client(self) -> bool:
        """确保客户端已初始化"""
        if not self.enabled or not self._client:
            return False
        return True

    async def add_memory(
        self,
        messages: List[Dict[str, str]],
        user_id: Optional[str] = None,
        character_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        生成记忆
        """
        if not await self._ensure_client():
            return None
            
        try:
            # 使用 SDK 的 add 方法
            result = await self._client.add(
                messages=messages,
                user_id=user_id,
                character_id=character_id,
                session_id=session_id
            )
            logger.info(f"Timem Memory 生成成功: session_id={session_id}")
            return result
        except Exception as e:
            logger.error(f"Timem Memory 生成失败: {str(e)}")
            return None

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
        """
        if not await self._ensure_client():
            return []
            
        try:
            # 使用 SDK 的 search 方法
            results = await self._client.search(
                query=query_text,
                user_id=user_id,
                character_id=character_id,
                session_id=session_id,
                limit=limit
            )
            
            # 提取记忆列表 (处理不同版本的返回结构)
            if isinstance(results, dict):
                memories = results.get("memories", results.get("results", []))
            elif isinstance(results, list):
                # 某些版本可能直接返回列表
                memories = results
            else:
                memories = []
                
            # 再次限制数量
            memories = memories[:limit] if memories else []
            
            logger.info(f"Timem Memory 搜索成功: found {len(memories)} items")
            return memories
            
        except Exception as e:
            logger.error(f"Timem Memory 搜索失败: {str(e)}")
            return []

    async def close(self):
        """关闭连接"""
        if self._client and hasattr(self._client, 'aclose'):
            try:
                await self._client.aclose()
            except Exception:
                pass
