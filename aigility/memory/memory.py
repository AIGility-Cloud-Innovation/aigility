"""
Memory 高级接口

提供简化的记忆管理接口，基于 Provider 架构实现。

使用示例:
    from aigility.memory import Memory, MemoryConfig, MemoryProviderConfig

    # 方式1: 使用默认配置
    memory = Memory()

    # 方式2: 传入配置对象
    config = MemoryConfig(
        provider=MemoryProviderConfig(
            provider="timem",
            api_key="sk-xxx"
        )
    )
    memory = Memory(config=config)

    # 方式3: 环境变量配置
    # export TIMEM_API_KEY=sk-xxx
    config = MemoryConfig()
    memory = Memory(config=config)
"""

import logging
from typing import Optional, Dict, Any, List, Union
from .config import MemoryConfig
from .providers.factory import MemoryProviderFactory
from .providers.base import BaseMemoryProvider

logger = logging.getLogger(__name__)


class Memory:
    """
    记忆管理类

    提供简化的 API 接口，内部使用 Provider 架构。
    支持多种 Memory Provider（如 Timem）。

    设计模式参考 RAG 模块：
    - 外部传入 Config 对象
    - 如果不传则使用默认配置
    - 通过工厂模式创建 Provider
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        """
        初始化 Memory 实例

        Args:
            config: Memory 配置对象，不传时使用默认配置（从环境变量读取）

        Examples:
            >>> from aigility.memory import Memory, MemoryConfig
            >>>
            >>> # 使用默认配置（从环境变量读取 TIMEM_API_KEY）
            >>> config = MemoryConfig()
            >>> memory = Memory(config=config)
            >>>
            >>> # 使用自定义配置
            >>> config = MemoryConfig(
            ...     provider=MemoryProviderConfig(
            ...         provider="timem",
            ...         api_key="sk-xxx"
            ...     )
            ... )
            >>> memory = Memory(config=config)
        """
        if config is None:
            config = MemoryConfig()

        if not isinstance(config, MemoryConfig):
            raise TypeError(
                f"config 必须是 MemoryConfig 类型，获取到: {type(config)}"
            )

        self.config = config

        logger.info(
            f"Initializing Memory with: Provider={self.config.provider.provider}"
        )

        # 使用工厂模式创建 Provider
        self._provider: Union[BaseMemoryProvider, None] = None
        self._initialize_provider()

    def _initialize_provider(self):
        """初始化 Provider（使用工厂模式）"""
        if not self.config.provider.enabled:
            logger.info("Memory Provider is disabled")
            return

        try:
            self._provider = MemoryProviderFactory.create_provider(
                self.config.provider
            )
            logger.info(f"Memory Provider initialized: {self.config.provider.provider}")
        except Exception as e:
            logger.error(f"Failed to initialize Memory Provider: {e}")
            self._provider = None
    
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
        if not self._provider:
            return {
                "success": False,
                "error": "Provider 未启用或初始化失败",
                "memories": [],
                "total": 0
            }

        if not messages:
            raise ValueError("messages 不能为空")

        if not character_id:
            raise ValueError("character_id 必须提供")

        if not session_id:
            import hashlib
            session_id = f"session_{hashlib.md5(str(user_id).encode()).hexdigest()[:8]}"

        # 调用 Provider 的 add_memory 方法
        result = await self._provider.add_memory(
            messages=messages,
            user_id=str(user_id),
            character_id=character_id,
            session_id=session_id
        )

        if result is None:
            return {
                "success": False,
                "error": "添加记忆失败",
                "memories": [],
                "total": 0
            }

        # 解析返回结果
        memories = result.get("memories", [])
        memory_ids = result.get("memory_ids", [])

        return {
            "success": result.get("success", True),
            "memories": memories,
            "memory_id": result.get("memory_id"),
            "memory_ids": memory_ids,
            "total": result.get("total", len(memories)),
            "message": result.get("message", "")
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
        if not self._provider:
            return {
                "results": [],
                "total": 0,
                "query": query,
                "error": "Provider 未启用或初始化失败"
            }

        # 调用 Provider 的 search_memories 方法
        memories = await self._provider.search_memories(
            query_text=query,
            user_id=str(user_id),
            character_id=character_id,
            limit=limit
        )

        # 格式化结果
        formatted_results = []
        for mem in memories[:limit] if limit else memories:
            # 从不同结构中提取记忆文本
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
            "total": len(formatted_results),
            "query": query
        }
    
    async def close(self):
        """关闭客户端连接"""
        if self._provider:
            await self._provider.close()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

