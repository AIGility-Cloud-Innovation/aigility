#!/usr/bin/env python3
"""
WorkflowBuilder 测试 — 验证 aigility.workflow 能独立读 YAML 并构建 LangGraph。

不依赖任何外部业务代码。
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
                    "output_keys": ["result"],
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

    # 模拟 seam_caller: 返回 RAG 标准格式 (results 列表 → 格式化为文本写入 output_keys)
    def mock_seam_caller(cap_ref, state):
        return {"results": [{"content": f"rag_result for {cap_ref}"}], "total": 1}

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


def test_capability_async_invoke():
    """测试: capability 节点异步 ainvoke 路径 (RunnableCallable.afunc)"""
    import asyncio
    import tempfile, yaml as yaml_lib

    config = {
        "workflow": {
            "name": "cap_async_test",
            "entry_point": "rag_node",
            "nodes": {
                "rag_node": {
                    "type": "capability_node",
                    "capability_ref": "@cognitive/rag-retrieval",
                    "output_keys": ["result"],
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

    async def mock_async_seam_caller(cap_ref, state):
        return {"results": [{"content": f"async_rag_result for {cap_ref}"}], "total": 1}

    engine = WorkflowEngine(config_path=config_path, state_schema=TestState)
    engine.set_seam_caller(mock_async_seam_caller)

    graph = engine.build()
    result = asyncio.run(graph.ainvoke({"value": 1}))
    assert "async_rag_result" in result["result"], \
        f"异步路径应调 async seam_caller, got {result}"
    print(f"  ✅ capability 异步 ainvoke: {result['result']}")

    os.unlink(config_path)


# ── save_yaml 读写闭环 ────────────────────────────────────────

def test_save_yaml_roundtrip():
    """测试: WorkflowConfig → save_yaml → safe_load → 回读校验 roundtrip"""
    import tempfile
    import yaml as yaml_lib
    from aigility.workflow import (
        WorkflowConfig, NodeConfig, EdgeConfig, FlowConfig, save_yaml,
    )

    config = WorkflowConfig(
        name="roundtrip_workflow",
        description="save_yaml 读写闭环测试",
        entry_point="start",
        nodes={
            "start": NodeConfig(
                type="function_node",
                description="起始节点",
                function_ref="start_node",
                output_keys=["value"],
            ),
        },
        flow=FlowConfig(
            edges=[EdgeConfig(**{"from": "start", "to": "__end__"})],
        ),
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        out_path = f.name

    try:
        save_yaml(config, out_path)

        with open(out_path, encoding="utf-8") as f:
            raw = yaml_lib.safe_load(f)

        # 边应使用别名形式 (from)，与 schema 读取格式一致
        assert raw["flow"]["edges"][0]["from"] == "start", \
            f"边应为别名形式 from, got {raw['flow']['edges'][0]}"
        # Optional 字段的 None 默认值应被清理
        assert "prompt_ref" not in raw["nodes"]["start"], "None 字段应被清理"
        assert "capability_ref" not in raw["nodes"]["start"], "None 字段应被清理"

        # 回读校验: 重新走 WorkflowConfig 校验, 与原对象等价
        restored = WorkflowConfig(**raw)
        assert restored == config, "roundtrip 后应与原 WorkflowConfig 相等"
        print("  ✅ schema → YAML → safe_load → 回读一致")

        # dict 输入: 原样写出
        dict_config = {"name": "dict_flow", "entry_point": "a",
                       "nodes": {"a": {"type": "llm_node"}}}
        save_yaml(dict_config, out_path)
        with open(out_path, encoding="utf-8") as f:
            assert yaml_lib.safe_load(f) == dict_config, "dict 输入应原样写出"
        print("  ✅ dict 输入原样写出")
    finally:
        os.unlink(out_path)


# ── run_yaml_workflow 一键运行 ────────────────────────────────

# 自包含 llm_node fixture: 无需函数注册/外部模块, LLM 不可用时降级为回退文本
_RUN_YAML_FIXTURE_YAML = """\
workflow:
  name: "run_yaml_fixture"
  description: "run_yaml_workflow 测试配置"
  entry_point: "start"
  nodes:
    start:
      type: "llm_node"
      description: "回显节点"
      prompt_ref: "你是回显测试节点，直接返回收到的内容。"
      output_keys: ["result"]
  flow:
    edges:
      - from: "start"
        to: "__end__"
"""

_RUN_YAML_NO_RESULT_YAML = """\
workflow:
  name: "run_yaml_fixture_no_result"
  description: "output_keys 不含 result 的回退分支测试"
  entry_point: "start"
  nodes:
    start:
      type: "llm_node"
      description: "自定义输出键"
      prompt_ref: "你是回显测试节点。"
      output_keys: ["answer"]
  flow:
    edges:
      - from: "start"
        to: "__end__"
"""


def _write_yaml_fixture(content: str) -> str:
    """写 fixture YAML 到临时文件, 返回路径 (调用方负责 unlink)"""
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        return f.name


def test_run_yaml_workflow_happy_path():
    """测试: 自包含 YAML 一键运行, 返回 result 键的 JSON 安全值"""
    import json
    from aigility.workflow import run_yaml_workflow

    path = _write_yaml_fixture(_RUN_YAML_FIXTURE_YAML)
    try:
        result = run_yaml_workflow(path, user_input="你好")
        # LLM 成功或降级都返回 str; 只锁类型与 JSON 可序列化, 不锁具体文本
        assert isinstance(result, str), f"result 应为 str, got {type(result)}"
        json.dumps(result, ensure_ascii=False)
        print(f"  ✅ happy path: result={result[:40]!r}")
    finally:
        os.unlink(path)


def test_run_yaml_workflow_no_result_fallback():
    """测试: output_keys 不含 result 时, 回退返回整个最终 state (JSON 安全 dict)"""
    import json
    from aigility.workflow import run_yaml_workflow

    path = _write_yaml_fixture(_RUN_YAML_NO_RESULT_YAML)
    try:
        result = run_yaml_workflow(path, user_input="测试")
        assert isinstance(result, dict), f"回退应返回整个 state dict, got {type(result)}"
        assert "answer" in result, f"应含 output_key 'answer', got {list(result.keys())}"
        assert "result" not in result, "不应含 result 键"
        json.dumps(result, ensure_ascii=False)
        print(f"  ✅ 回退分支: state keys={list(result.keys())}")
    finally:
        os.unlink(path)


def test_run_yaml_workflow_error_propagation():
    """测试: 配置文件不存在 → RuntimeError 上抛 (worker 报错策略)"""
    from aigility.workflow import run_yaml_workflow

    try:
        run_yaml_workflow("/nonexistent/path/config.yaml", user_input="x")
        raise AssertionError("应上抛 RuntimeError")
    except RuntimeError as e:
        assert "工作流配置未加载" in str(e), f"消息应含'工作流配置未加载', got {e}"
        print("  ✅ 错误上抛: RuntimeError(工作流配置未加载...)")


def test_json_safe():
    """测试: _json_safe 序列化策略 (default=str 降级 + 中文原样 + 无损 roundtrip)"""
    import datetime
    from aigility.workflow.runtime import _json_safe

    plain = {"中文": "你好", "n": [1, 2.5, True, None, {"k": "v"}]}
    assert _json_safe(plain) == plain, "可序列化对象应无损 roundtrip"

    dt = datetime.datetime(2026, 9, 27, 10, 0, 0)
    out = _json_safe({"t": dt, "s": {1, 2}})
    assert isinstance(out["t"], str) and "2026" in out["t"], "datetime 应降级为 str"
    assert isinstance(out["s"], str), "set 应降级为 str (default=str 语义)"

    cn = _json_safe({"msg": "中文不转义"})
    assert cn["msg"] == "中文不转义", "ensure_ascii=False 应保留中文"
    print("  ✅ _json_safe: 无损 roundtrip + default=str 降级 + 中文原样")


def test_arun_yaml_workflow_smoke():
    """测试: 异步入口冒烟, 与同步版行为一致"""
    import asyncio
    from aigility.workflow import arun_yaml_workflow

    path = _write_yaml_fixture(_RUN_YAML_FIXTURE_YAML)
    try:
        result = asyncio.run(arun_yaml_workflow(path, user_input="异步"))
        assert isinstance(result, str), f"异步 result 应为 str, got {type(result)}"
        print("  ✅ 异步冒烟: 与同步版一致返回 JSON 安全 str")
    finally:
        os.unlink(path)


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

    print("\n5. save_yaml 读写闭环")
    test_save_yaml_roundtrip()

    print("\n6. run_yaml_workflow happy path")
    test_run_yaml_workflow_happy_path()

    print("\n7. run_yaml_workflow 无 result 回退")
    test_run_yaml_workflow_no_result_fallback()

    print("\n8. run_yaml_workflow 错误上抛")
    test_run_yaml_workflow_error_propagation()

    print("\n9. _json_safe 序列化策略")
    test_json_safe()

    print("\n10. arun_yaml_workflow 异步冒烟")
    test_arun_yaml_workflow_smoke()

    print("\n11. capability 异步 ainvoke")
    test_capability_async_invoke()

    print("\n=== 全部通过 ===")
