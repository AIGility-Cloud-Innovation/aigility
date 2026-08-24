# -*- coding: utf-8 -*-
"""
WorkflowEngine — 基于 LangGraph 的工作流引擎。

WorkflowEngine 封装了 WorkflowBuilder，提供更高级的 invoke/stream 接口。
它是 aigility 的通用编排工具，不包含任何业务逻辑。

使用方式:
    engine = WorkflowEngine(
        config_path="workflow_config.yaml",
        state_schema=MyState,
    )
    engine.register_node("my_node", my_func)
    graph = engine.build()
    result = graph.invoke(initial_state)
"""

import logging
from typing import Optional, Dict, Any, Type, Callable

from .builder import WorkflowBuilder

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """工作流引擎 — 封装 WorkflowBuilder，提供编排能力。"""

    def __init__(
        self,
        name: str = "workflow",
        config_path: Optional[str] = None,
        state_schema: Optional[Type] = None,
        node_registry: Optional[Dict[str, Callable]] = None,
        condition_registry: Optional[Dict[str, Callable]] = None,
        node_module: Optional[str] = None,
        condition_module: Optional[str] = None,
    ):
        self.name = name
        self.builder = WorkflowBuilder(
            config_path=config_path,
            state_schema=state_schema,
            node_registry=node_registry,
            condition_registry=condition_registry,
            node_module=node_module,
            condition_module=condition_module,
        )
        self._graph: Optional[Any] = None

    # ── 注册代理 ──────────────────────────────────────────────

    def register_node(self, node_id: str, node_function: Callable) -> None:
        self.builder.register_node(node_id, node_function)

    def register_nodes(self, nodes: Dict[str, Callable]) -> None:
        self.builder.register_nodes(nodes)

    def register_condition(self, name: str, func: Callable) -> None:
        self.builder.register_condition(name, func)

    def register_conditions(self, conditions: Dict[str, Callable]) -> None:
        self.builder.register_conditions(conditions)

    def set_seam_caller(self, seam_caller: Callable) -> None:
        """注入 Seam 调用器 (harness 集成用)"""
        self.builder.set_seam_caller(seam_caller)

    # ── 构建与执行 ──────────────────────────────────────────────

    def build(self, fallback_graph: Optional[Any] = None) -> Any:
        """构建并编译工作流图"""
        self._graph = self.builder.build(fallback_graph=fallback_graph)
        return self._graph

    def invoke(self, state: Any, config: Optional[Dict] = None,
               node_registry: Optional[Dict[str, Callable]] = None,
               condition_registry: Optional[Dict[str, Callable]] = None) -> Any:
        """
        执行工作流。

        Args:
            state: 初始状态
            config: LangGraph 运行配置 (可选)
            node_registry: 运行时注入节点函数 (可选, 在构建前注册)
            condition_registry: 运行时注入条件函数 (可选)

        Returns:
            最终状态
        """
        if node_registry:
            self.builder.register_nodes(node_registry)
        if condition_registry:
            self.builder.register_conditions(condition_registry)
        if self._graph is None:
            self.build()
        return self._graph.invoke(state, config=config)

    async def ainvoke(self, state: Any, config: Optional[Dict] = None) -> Any:
        """异步执行工作流"""
        if self._graph is None:
            self.build()
        return await self._graph.ainvoke(state, config=config)

    async def astream(self, state: Any, config: Optional[Dict] = None):
        """流式执行工作流"""
        if self._graph is None:
            self.build()
        async for chunk in self._graph.astream(state, config=config):
            yield chunk


def create_workflow_engine(
    name: str = "workflow",
    config_path: Optional[str] = None,
    state_schema: Optional[Type] = None,
    **kwargs,
) -> WorkflowEngine:
    """创建工作流引擎"""
    return WorkflowEngine(
        name=name,
        config_path=config_path,
        state_schema=state_schema,
        **kwargs,
    )
