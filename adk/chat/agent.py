"""
Chat Agent

基于 LangChain 的对话智能体。
"""

from typing import Optional, List, Dict, Any
from ..core.base import BaseAgent
from ..core.types import State, Message, AgentResponse
from ..core.config import AgentConfig


class ChatAgent(BaseAgent):
    """对话智能体"""
    
    def __init__(
        self,
        name: str,
        config: Optional[AgentConfig] = None,
        llm: Optional[Any] = None,  # LangChain LLM
        tools: Optional[List[Any]] = None,  # LangChain Tools
        memory: Optional[Any] = None,  # LangChain Memory
    ):
        super().__init__(name, config)
        self.config = config or AgentConfig(name=name, description="")
        self.llm = llm
        self.tools = tools or []
        self.memory = memory
        
        # TODO: 初始化 LangChain Agent
        # 这里需要使用 LangChain 的 Agent 类
        self._agent = None
    
    async def invoke(self, state: State) -> AgentResponse:
        """
        执行对话
        
        Args:
            state: 当前状态
            
        Returns:
            智能体响应
        """
        # TODO: 实现 LangChain Agent 调用
        # 这里需要调用 LangChain 的 Agent
        raise NotImplementedError("ChatAgent.invoke not yet implemented")
    
    def get_prompt(self) -> str:
        """获取提示词"""
        return self.config.prompt_template or ""


def create_chat_agent(
    name: str,
    config: Optional[AgentConfig] = None,
    **kwargs
) -> ChatAgent:
    """创建对话智能体"""
    return ChatAgent(name=name, config=config, **kwargs)

