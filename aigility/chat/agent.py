"""
Chat Agent

基于 ChatFlow 的对话智能体，提供简化的 Agent 入口。
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from langchain_core.runnables import RunnableConfig
from ..core.base import BaseAgent
from ..core.types import State, Message, AgentResponse, MessageRole
from ..core.config import ADKConfig, AgentConfig

if TYPE_CHECKING:
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
    def chat_flow(self) -> "ChatFlow":
        """懒加载 ChatFlow 实例（延迟导入以保持可选依赖边界）"""
        if self._chat_flow is None:
            from ..chatflow.flow import ChatFlow

            self._chat_flow = ChatFlow(
                name=self.name,
                adk_config=self.adk_config,
            )
        return self._chat_flow

    def _resolve_kb_id(self, kb_id: Optional[str] = None) -> Optional[str]:
        """解析 kb_id：优先使用传入的值，否则使用 adk_config 中的默认值"""
        if kb_id:
            return kb_id
        return self.adk_config.timem_kb_id

    def _require_kb_id(self, kb_id: Optional[str], rag_used: str) -> Optional[str]:
        """
        验证并解析 kb_id。当 rag_used 不是 "off" 时，kb_id 为必传。

        Args:
            kb_id: 调用时传入的 kb_id
            rag_used: RAG 模式

        Returns:
            解析后的 kb_id，RAG 关闭时可为 None

        Raises:
            ValueError: RAG 模式下未提供 kb_id
        """
        if rag_used == "off":
            return None
        resolved = self._resolve_kb_id(kb_id)
        if not resolved:
            raise ValueError(
                f"rag_used='{rag_used}' 但未提供 kb_id 知识库 ID。"
                f"请通过 chat(kb_id='your_kb_id') 传入，"
                f"或在 ADKClientBuilder.with_rag(kb_id='your_kb_id') 中设置默认值。"
            )
        return resolved

    def _make_config(self, kb_id: Optional[str] = None, rag_used: str = "auto") -> Optional[RunnableConfig]:
        """根据 kb_id 和 rag_used 构造 RunnableConfig"""
        resolved_kb_id = self._require_kb_id(kb_id, rag_used)
        if resolved_kb_id:
            return RunnableConfig(configurable={"timem_kb_id": resolved_kb_id})
        return None

    def chat(
        self,
        user_input: str,
        rag_used: str = "auto",
        kb_id: Optional[str] = None,
    ) -> str:
        """
        同步对话（便捷方法）

        Args:
            user_input: 用户输入
            rag_used: RAG 模式 ("auto", "on", "off")。非 "off" 时 kb_id 必传。
            kb_id: 知识库 ID（RAG 模式下必传，优先于 adk_config.timem_kb_id）

        Returns:
            AI 回复文本

        Raises:
            ValueError: rag_used 非 "off" 但未提供 kb_id
        """
        config = self._make_config(kb_id, rag_used)
        result = self.chat_flow.invoke(
            user_input=user_input,
            rag_used=rag_used,
            config=config,
        )
        return result["response"]

    async def invoke(self, state: State) -> AgentResponse:
        """
        执行对话（实现 BaseAgent 抽象接口）

        Args:
            state: 当前状态，从 messages 中提取最后一条用户消息。
                  可通过 state.metadata["kb_id"] 传入知识库 ID（RAG 模式下必传）。

        Returns:
            智能体响应

        Raises:
            ValueError: 未提供 kb_id
        """
        # 从 State 中提取用户输入
        user_input = ""
        for msg in reversed(state.messages):
            if msg.role == MessageRole.USER:
                user_input = msg.content
                break
        if not user_input and state.messages:
            user_input = state.messages[-1].content

        # 从 state.metadata 中提取 kb_id（如有）
        kb_id = state.metadata.get("kb_id") if state.metadata else None
        config = self._make_config(kb_id, rag_used="auto")

        result = self.chat_flow.invoke(
            user_input=user_input,
            rag_used="auto",
            config=config,
        )

        return AgentResponse(
            content=result["response"],
            metadata={
                "thought_process": result.get("thought_process"),
                "reasoning_content": result.get("reasoning_content"),
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
