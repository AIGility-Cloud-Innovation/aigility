"""
ADK 基础抽象类

定义智能体、工具、记忆等核心组件的抽象接口。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from .types import State, Message, AgentResponse


class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
    
    @abstractmethod
    async def invoke(self, state: State) -> AgentResponse:
        """
        执行智能体逻辑
        
        Args:
            state: 当前状态
            
        Returns:
            智能体响应
        """
        pass
    
    @abstractmethod
    def get_prompt(self) -> str:
        """获取智能体的提示词"""
        pass


class BaseTool(ABC):
    """工具基类"""
    
    def __init__(self, name: str, description: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.config = config or {}
    
    @abstractmethod
    async def invoke(self, **kwargs) -> Any:
        """
        执行工具逻辑
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            工具执行结果
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """获取工具的 JSON Schema"""
        pass


class BaseMemory(ABC):
    """记忆基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    @abstractmethod
    async def add(self, messages: List[Message], **kwargs) -> Dict[str, Any]:
        """添加记忆"""
        pass
    
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """搜索记忆"""
        pass
    
    @abstractmethod
    async def get(self, memory_id: str) -> Dict[str, Any]:
        """获取记忆"""
        pass

