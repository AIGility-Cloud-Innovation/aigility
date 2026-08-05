"""
Chat Agent

基于 ChatFlow 的对话智能体，提供简化的 Agent 入口。
"""

from typing import Optional, List, Dict, Any
from ..core.base import BaseAgent
from ..core.types import State, Message, AgentResponse, MessageRole
from ..core.config import ADKConfig, AgentConfig
from ..chatflow.flow import ChatFlow


class ChatAgent(BaseAgent):
    """
    对话智能体

    内部委托 ChatFlow（LangGraph 状态机）执行对话，
    对外提供简化的 Agent 接口。
    """

    def __init__(
        self,
        name: str,
        config: Optional[AgentConfig] = None,
        adk_config: Optional[ADKConfig] = None,
        llm: Optional[Any] = None,
        tools: Optional[List[Any]] = None,
        memory: Optional[Any] = None,
    ):
        super().__init__(name, config)
        self.agent_config = config or AgentConfig(name=name, description="")
        self.adk_config = adk_config or ADKConfig()
        self.llm = llm
        self.tools = tools or []
        self.memory = memory
        self._chat_flow: Optional[ChatFlow] = None

    @property
    def chat_flow(self) -> ChatFlow:
        """懒加载 ChatFlow 实例"""
        if self._chat_flow is None:
            self._chat_flow = ChatFlow(
                name=self.name,
                adk_config=self.adk_config,
            )
        return self._chat_flow

    def chat(self, user_input: str, rag_used: str = "auto") -> str:
        """
        同步对话（便捷方法）

        Args:
            user_input: 用户输入
            rag_used: RAG 模式 ("auto", "on", "off")

        Returns:
            AI 回复文本
        """
        result = self.chat_flow.invoke(user_input=user_input, rag_used=rag_used)
        return result["response"]

    async def invoke(self, state: State) -> AgentResponse:
        """
        执行对话（实现 BaseAgent 抽象接口）

        Args:
            state: 当前状态，从 messages 中提取最后一条用户消息

        Returns:
            智能体响应
        """
        # 从 State 中提取用户输入
        user_input = ""
        for msg in reversed(state.messages):
            if msg.role == MessageRole.USER:
                user_input = msg.content
                break
        if not user_input and state.messages:
            user_input = state.messages[-1].content

        result = self.chat_flow.invoke(user_input=user_input, rag_used="auto")

        return AgentResponse(
            content=result["response"],
            metadata={
                "thought_process": result.get("thought_process"),
                "tool_results": [
                    {"tool_name": tr.tool_name, "result": tr.result}
                    for tr in (result.get("tool_results") or [])
                ],
            },
        )

    def get_prompt(self) -> str:
        """获取提示词"""
        return self.agent_config.prompt_template or ""


def create_chat_agent(
    name: str,
    config: Optional[AgentConfig] = None,
    adk_config: Optional[ADKConfig] = None,
    **kwargs
) -> ChatAgent:
    """创建对话智能体"""
    return ChatAgent(name=name, config=config, adk_config=adk_config, **kwargs)

