"""测试用 State schema — 给 WorkflowEngine 的 LangGraph StateGraph 用。"""
from typing import TypedDict, Any, Optional


class TestState(TypedDict, total=False):
    """通用测试状态，不包含任何销售/客服特定字段。"""
    value: int
    result: str
