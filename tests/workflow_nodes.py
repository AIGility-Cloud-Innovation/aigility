"""
测试用节点函数模块 — WorkflowEngine 通过 node_module 自动导入这些函数。
"""
from typing import Any, Dict


def start_node(state: Any) -> Dict:
    v = state.get("value", 0)
    return {"value": v}


def double_node(state: Any) -> Dict:
    return {"value": state.get("value", 0) * 2}


def finish_node(state: Any) -> Dict:
    return {"result": f"final value = {state.get('value', 0)}"}


def check_value(state: Any) -> str:
    if state.get("value", 0) > 0:
        return "positive"
    return "zero_or_negative"
