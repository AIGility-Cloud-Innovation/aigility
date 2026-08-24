"""
ADK Workflow - 工作流引擎模块

基于 LangGraph 提供配置驱动的工作流编排能力。

核心组件:
  - WorkflowBuilder: 从 YAML 配置构建 LangGraph StateGraph
  - WorkflowEngine: 封装 WorkflowBuilder，提供 invoke/stream 接口
  - schema: 工作流配置的 Pydantic 模型

使用方式:
    from aigility.workflow import WorkflowEngine

    engine = WorkflowEngine(
        config_path="workflow_config.yaml",
        state_schema=MyState,
    )
    engine.register_node("my_node", my_func)
    result = engine.invoke(initial_state)
"""

from .engine import WorkflowEngine, create_workflow_engine
from .builder import WorkflowBuilder, WorkflowGraphBuilder
from .schema import (
    WorkflowConfig,
    NodeConfig,
    EdgeConfig,
    FlowConfig,
    ConditionalEdgeConfig,
    ConditionalEdgeBranch,
)

__all__ = [
    # 引擎
    "WorkflowEngine",
    "create_workflow_engine",
    # 构建器
    "WorkflowBuilder",
    "WorkflowGraphBuilder",
    # Schema
    "WorkflowConfig",
    "NodeConfig",
    "EdgeConfig",
    "FlowConfig",
    "ConditionalEdgeConfig",
    "ConditionalEdgeBranch",
]
