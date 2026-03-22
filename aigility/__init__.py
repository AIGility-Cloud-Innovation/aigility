"""
AIGility ADK - Agent Development Kit

基于 LangGraph/LangChain 的智能体开发框架，提供：
- chat: 基础对话能力
- chatflow: 对话流管理
- workflow: 工作流引擎
- rag: RAG 检索增强生成
- memory: 记忆管理
"""

__version__ = "0.0.7"
__author__ = "AIGility Cloud Innovation"
__email__ = "contact@aigility.com"
__description__ = "Agent Development Kit - 智能体开发框架"

# 导入主客户端
from .client import ADKClient, create_client

# 导入各模块
from . import memory
from . import chat
from . import chatflow
from . import workflow
from . import rag

__all__ = [
    # 主客户端
    "ADKClient",
    "create_client",

    # 模块
    "memory",
    "chat",
    "chatflow",
    "workflow",
    "rag",

    # 元信息
    "__version__",
    "__author__",
    "__email__",
    "__description__",
]

