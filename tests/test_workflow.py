#!/usr/bin/env python3
"""
WorkflowBuilder 测试 — 验证 aigility.workflow 能独立读 YAML 并构建 LangGraph。

不依赖 reachAI 任何代码。
"""
import sys
import os

# 确保用 aigility 的 venv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import TypedDict, Annotated
from operator import add

from aigility.workflow import WorkflowBuilder, WorkflowEngine


# ── 测试用 State ──────────────────────────────────────────────

class TestState(TypedDict, total=False):
    value: int
    result: str


# ── 测试用节点函数 ────────────────────────────────────────────

def start_node(state: TestState) -> dict:
    """起始节点: 初始化 value"""
    v = state.get("value", 0)
    return {"value": v}

def double_node(state: TestState) -> dict:
    """翻倍节点"""
    return {"value": state.get("value", 0) * 2}

def finish_node(state: TestState) -> dict:
    """结束节点"""
    return {"result": f"final value = {state.get('value', 0)}"}


# ── 测试用条件函数 ────────────────────────────────────────────

def check_value(state: TestState) -> str:
    """值大于0返回 positive，否则 zero_or_negative"""
    if state.get("value", 0) > 0:
        return "positive"
    return "zero_or_negative"


# ── 测试 ──────────────────────────────────────────────────────

def test_build_and_invoke():
    """测试: 构建图并执行"""
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "workflow_test_config.yaml"
    )

    builder = WorkflowBuilder(
        config_path=config_path,
        state_schema=TestState,
    )
    builder.register_nodes({
        "start_node": start_node,
        "double_node": double_node,
        "finish_node": finish_node,
    })
    builder.register_conditions({
        "check_value": check_value,
    })

    graph = builder.build()
    assert graph is not None, "graph 不应为 None"

    # 测试 1: 正值 → 翻倍 → 结束
    result = graph.invoke({"value": 5})
    assert result["value"] == 10, f"正值应翻倍,7, got {result['value']}"
    assert "final" in result["result"], f"应有 result, got {result}"
    print(f"  ✅ 正值路径: value=5 → {result['value']}, result='{result['result']}'")

    # 测试 2: 零值 → 直接结束
    result = graph.invoke({"value": 0})
    assert result["value"] == 0, f"零值不应翻倍, got {result['value']}"
    print(f"  ✅ 零值路径: value=0 → {result['value']}, result='{result['result']}'")

    # 测试 3: 负值 → 直接结束
    result = graph.invoke({"value": -3})
    assert result["value"] == -3, f"负值不应翻倍, got {result['value']}"
    print(f"  ✅ 负值路径: value=-3 → {result['value']}, result='{result['result']}'")


def test_engine_invoke():
    """测试: WorkflowEngine 封装"""
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "workflow_test_config.yaml"
    )

    engine = WorkflowEngine(
        name="test",
        config_path=config_path,
        state_schema=TestState,
        node_registry={
            "start_node": start_node,
            "double_node": double_node,
            "finish_node": finish_node,
        },
        condition_registry={
            "check_value": check_value,
        },
    )

    result = engine.invoke({"value": 7})
    assert result["value"] == 14, f"7 应翻倍为 14, got {result['value']}"
    print(f"  ✅ Engine: value=7 → {result['value']}, result='{result['result']}'")


def test_capability_ref():
    """测试: capability_ref 节点 (无 seam_caller 时返回空)"""
    import tempfile, yaml as yaml_lib

    config = {
        "workflow": {
            "name": "cap_test",
            "entry_point": "cap_node",
            "nodes": {
                "cap_node": {
                    "type": "capability_node",
                    "capability_ref": "@cognitive/rag-retrieval",
                }
            },
            "flow": {
                "edges": [],
                "conditional_edges": []
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml_lib.dump(config, f)
        config_path = f.name

    builder = WorkflowBuilder(config_path=config_path, state_schema=TestState)
    builder.register_node("cap_node", builder._make_capability_wrapper("@cognitive/rag-retrieval"))

    graph = builder.build()
    result = graph.invoke({"value": 1})
    # 无 seam_caller, 节点返回 {}, value 保持不变
    assert result["value"] == 1, f"无 seam_caller 应不改变 state, got {result}"
    print(f"  ✅ capability_ref 无 seam_caller: 返回空, state 不变")

    os.unlink(config_path)


def test_seam_caller():
    """测试: 注入 seam_caller 后 capability_ref 能调外部能力"""
    import tempfile, yaml as yaml_lib

    config = {
        "workflow": {
            "name": "seam_test",
            "entry_point": "rag_node",
            "nodes": {
                "rag_node": {
                    "type": "capability_node",
                    "capability_ref": "@cognitive/rag-retrieval",
                }
            },
            "flow": {
                "edges": [],
                "conditional_edges": []
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml_lib.dump(config, f)
        config_path = f.name

    # 模拟 seam_caller
    def mock_seam_caller(cap_ref, state):
        return {"result": f"rag_result for {cap_ref}"}

    engine = WorkflowEngine(
        config_path=config_path,
        state_schema=TestState,
    )
    engine.set_seam_caller(mock_seam_caller)

    graph = engine.build()
    result = graph.invoke({"value": 1})
    assert "rag_result" in result["result"], f"应调 seam_caller, got {result}"
    print(f"  ✅ seam_caller 注入: {result['result']}")

    os.unlink(config_path)


if __name__ == "__main__":
    print("=== aigility WorkflowBuilder 测试 ===\n")

    print("1. 构建图并执行 (正值/零值/负值路径)")
    test_build_and_invoke()

    print("\n2. WorkflowEngine 封装")
    test_engine_invoke()

    print("\n3. capability_ref 节点 (无 seam_caller)")
    test_capability_ref()

    print("\n4. seam_caller 注入")
    test_seam_caller()

    print("\n=== 全部通过 ===")
