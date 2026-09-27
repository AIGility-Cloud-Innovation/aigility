# -*- coding: utf-8 -*-
"""
run_yaml_workflow — 自包含 YAML 工作流的一键运行入口。

无需构建 WorkflowBuilder/WorkflowEngine、无需注册节点函数:

    result = run_yaml_workflow("workflow_config.yaml", user_input="你好")

前置约束:
  - 仅支持自包含 YAML: function_node 的函数解析依赖 YAML 内 node_module
    (配合 node_registry 映射) 动态导入; 本入口无函数注册参数。
  - llm_node 无需外部函数 (prompt_ref/内联提示词; LLM 服务不可用时
    降级为确定性回退文本)。
  - capability_node 可运行, 但本入口无 seam_caller 注入参数: 未集成 harness
    时该类节点仅透传状态 (warning); 需注入请直接用 WorkflowEngine +
    set_seam_caller。

结果提取:
  最终 state 含 "result" 键 → 返回该值的 JSON 安全化;
  否则 → 返回整个最终 state 的 JSON 安全化。
  JSON 安全化 = json.loads(json.dumps(value, ensure_ascii=False, default=str)),
  datetime/set/Path 等不可序列化对象降级为字符串。

异常策略: 不做任何捕获, 配置/构建/运行/序列化错误全部上抛, 由 worker 报错。
配置文件缺失或格式错误时, builder 会吞掉原始异常记日志, 最终以
RuntimeError("工作流配置未加载...") 冒泡。
"""

import json
from typing import Any

from .engine import WorkflowEngine


def _json_safe(value: Any) -> Any:
    """将任意对象转为 JSON 安全结构 (不可序列化对象经 default=str 降级)"""
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _extract_result(final_state: Any) -> Any:
    """提取结果: 有 result 键取该值, 否则取整个最终 state, 统一 JSON 安全化"""
    if isinstance(final_state, dict) and "result" in final_state:
        return _json_safe(final_state["result"])
    return _json_safe(final_state)


def run_yaml_workflow(config_path: str, **state) -> Any:
    """从 YAML 配置一键运行工作流, 返回 JSON 安全的结果。

    Args:
        config_path: 自包含的工作流 YAML 配置路径。
        **state: 初始状态字段 (如 user_input="...")。

    Returns:
        最终 state 的 "result" 键值 (不存在时为整个最终 state), 经 JSON 安全化。

    Raises:
        RuntimeError: 配置文件缺失或格式错误 (原始 YAML 错误在日志中)。
        Exception: 节点运行期异常、序列化 TypeError 原样上抛。
    """
    engine = WorkflowEngine(config_path=config_path)
    return _extract_result(engine.invoke(dict(state)))


async def arun_yaml_workflow(config_path: str, **state) -> Any:
    """异步版 run_yaml_workflow, 行为一致 (走 engine.ainvoke)。"""
    engine = WorkflowEngine(config_path=config_path)
    return _extract_result(await engine.ainvoke(dict(state)))
