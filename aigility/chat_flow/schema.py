from typing import List, Annotated, TypedDict, Optional
from langgraph.graph.message import AnyMessage, add_messages
from pydantic import BaseModel, Field, PrivateAttr

# --- 1. 工具定义 ---
class ToolCall(BaseModel):
    """Represents a tool call request."""
    tool_name: str = Field(..., description="The name of the tool to call (e.g., 'rag_search', 'web_search').")
    query: str = Field(..., description="The search query or input for the tool.")

class ToolResult(BaseModel):
    """Represents the result of a tool call."""
    tool_name: str = Field(..., description="The name of the tool that was called.")
    result: str = Field(..., description="The output or result from the tool.")

# --- 2. Graph State 定义 ---
# --- 4. LLM 配置模型 ---
class LLMConfig(BaseModel):
    """LLM Configuration for ChatFlow and related services."""
    model_name: str = Field("gpt-4.1-mini", description="The name of the LLM model to use.")
    base_url: Optional[str] = Field(None, description="The base URL for the OpenAI-compatible API.")
    api_key: Optional[str] = Field(None, description="The API key for the OpenAI-compatible API.")
    temperature: float = Field(0.0, description="The sampling temperature for the LLM.")
    
    # Private attribute to store the initialized ChatOpenAI client
    _client: Any = PrivateAttr()

    def get_client(self):
        """Initializes and returns the ChatOpenAI client."""
        from langchain_openai import ChatOpenAI
        if not hasattr(self, "_client") or self._client is None:
            # Use environment variables if base_url and api_key are not provided
            # Note: In the sandbox, OPENAI_API_KEY is pre-configured.
            self._client = ChatOpenAI(
                model=self.model_name,
                openai_api_base=self.base_url,
                openai_api_key=self.api_key,
                temperature=self.temperature
            )
        return self._client

# --- 5. Graph State 定义 ---
class ChatFlowState(TypedDict):
    """
    Represents the state of the LangGraph chat flow.
    """
    # 历史消息，用于保持对话上下文
    messages: Annotated[List[AnyMessage], add_messages]
    
    # CoT 思考过程，用于记录 Agent 的决策和推理
    thought: Optional[str]
    
    # Agent 决定调用的工具列表
    tool_calls: List[ToolCall]
    
    # 工具执行结果列表
    tool_results: List[ToolResult]
    
    # 最终回复建议（用于生成回复建议接口）
    reply_suggestion: Optional[str]
    
    # 会话标题建议（用于生成会话标题接口）
    session_title_suggestion: Optional[str]

# --- 3. 核心工具定义（模拟） ---
# 实际应用中，这些会是真实的 RAG 和 Web Search 函数
class RAGTool(BaseModel):
    """Tool for retrieving information from internal knowledge base (RAG)."""
    query: str = Field(description="The query to search the internal knowledge base.")

class WebSearchTool(BaseModel):
    """Tool for searching the web for up-to-date information."""
    query: str = Field(description="The query to search the internet.")

AVAILABLE_TOOLS = [RAGTool, WebSearchTool]
TOOL_MAP = {
    "rag_search": RAGTool,
    "web_search": WebSearchTool,
}

# --- 4. 辅助函数 ---
def get_tool_schema_map():
    """Returns a map of tool names to their Pydantic schemas."""
    return {tool.__name__: tool for tool in AVAILABLE_TOOLS}

def get_tool_names():
    """Returns a list of available tool names."""
    return [tool.__name__ for tool in AVAILABLE_TOOLS]

def get_tool_descriptions():
    """Returns a list of tool descriptions for the LLM."""
    descriptions = []
    for tool in AVAILABLE_TOOLS:
        descriptions.append(f"Tool Name: {tool.__name__}\nDescription: {tool.__doc__}\nSchema: {tool.schema_json(indent=2)}")
    return "\n\n".join(descriptions)
