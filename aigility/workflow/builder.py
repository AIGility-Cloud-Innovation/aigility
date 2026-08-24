# -*- coding: utf-8 -*-
"""
WorkflowBuilder — 从 YAML 配置文件构建 LangGraph 工作流。

这是 aigility 的通用工作流编排工具：
  - 读 YAML 配置 → 解析节点和边 → 构建 LangGraph StateGraph → 编译执行
  - 支持普通边 + 条件边
  - 支持三种节点类型:
      function_node  — 从 node_registry 或模块导入的 Python 函数
      llm_node       — LLM 节点 (通过 prompt_ref 引用提示词)
      capability_node — 通过 Seam 能力 ID 调用底层能力 (harness 集成)
  - 配置加载失败时回退到 fallback graph

使用方式:
    builder = WorkflowBuilder("workflow_config.yaml")
    builder.register_node("my_node", my_node_func)
    builder.register_condition("my_cond", my_cond_func)
    graph = builder.build()
    result = graph.invoke(initial_state)
"""

import os
import logging
import yaml
from typing import Dict, Any, Optional, Callable, Type
from langgraph.graph import StateGraph, END

from .schema import WorkflowConfig

logger = logging.getLogger(__name__)


class WorkflowBuilder:
    """
    工作流构建器 — 从 YAML 配置构建 LangGraph StateGraph。

    Args:
        config_path: YAML 配置文件路径
        state_schema: LangGraph 状态的 Pydantic 模型类 (TypedDict 或 BaseModel)
        node_registry: 节点函数注册表 {node_id: node_function}
        condition_registry: 条件函数注册表 {condition_name: condition_function}
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        state_schema: Optional[Type] = None,
        node_registry: Optional[Dict[str, Callable]] = None,
        condition_registry: Optional[Dict[str, Callable]] = None,
    ):
        self.config_path = config_path
        self.state_schema = state_schema
        self.config: Optional[WorkflowConfig] = None
        self.raw_config: Dict[str, Any] = {}
        self.node_registry: Dict[str, Callable] = node_registry or {}
        self.condition_registry: Dict[str, Callable] = condition_registry or {}

        if config_path:
            self._load_config()

    # ── 配置加载 ──────────────────────────────────────────────

    def _load_config(self) -> None:
        """从 YAML 文件加载工作流配置"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"工作流配置文件不存在: {self.config_path}")
                return

            with open(self.config_path, "r", encoding="utf-8") as f:
                self.raw_config = yaml.safe_load(f) or {}

            workflow_data = self.raw_config.get("workflow", {})
            if not workflow_data:
                logger.warning(f"工作流配置文件格式错误: {self.config_path}")
                return

            self.config = WorkflowConfig(**workflow_data)
            logger.info(f"成功加载工作流配置: {self.config.name}")

        except Exception as e:
            logger.error(f"加载工作流配置失败: {e}")
            self.config = None

    # ── 注册接口 ──────────────────────────────────────────────

    def register_node(self, node_id: str, node_function: Callable) -> None:
        """注册节点函数"""
        self.node_registry[node_id] = node_function

    def register_nodes(self, nodes: Dict[str, Callable]) -> None:
        """批量注册节点函数"""
        self.node_registry.update(nodes)

    def register_condition(self, condition_name: str, condition_function: Callable) -> None:
        """注册条件函数"""
        self.condition_registry[condition_name] = condition_function

    def register_conditions(self, conditions: Dict[str, Callable]) -> None:
        """批量注册条件函数"""
        self.condition_registry.update(conditions)

    # ── 解析逻辑 ──────────────────────────────────────────────

    def _resolve_node_function(self, node_id: str) -> Optional[Callable]:
        """
        解析节点函数。优先级:
          1. 运行时注册表 (self.node_registry)
          2. 配置文件中的 node_registry 映射
          3. capability_ref → 返回 Seam 能力调用 wrapper
          4. 从 nodes 模块动态导入 (fallback)
        """
        # 1. 运行时注册表
        if node_id in self.node_registry:
            return self.node_registry[node_id]

        # 2. 配置文件 node_registry: node_id → func_name
        config_registry = self.raw_config.get("workflow", {}).get("node_registry", {})
        if node_id in config_registry:
            func_name = config_registry[node_id]
            # 先看运行时注册表里有没有这个 func_name
            if func_name in self.node_registry:
                return self.node_registry[func_name]
            # 再尝试动态导入
            node_func = self._import_node_function(func_name)
            if node_func:
                return node_func

        # 3. capability_ref (Seam 能力调用)
        node_cfg = self.raw_config.get("workflow", {}).get("nodes", {}).get(node_id, {})
        if isinstance(node_cfg, dict) and "capability_ref" in node_cfg:
            cap_ref = node_cfg["capability_ref"]
            return self._make_capability_wrapper(cap_ref)

        # 4. 按 node_id 直接查找 (e.g. "my_node" → "my_node_node")
        node_func = self._import_node_function(f"{node_id}_node")
        if node_func:
            return node_func

        logger.error(f"找不到节点函数: {node_id}")
        return None

    def _import_node_function(self, func_name: str) -> Optional[Callable]:
        """
        从已注册的模块中导入节点函数。
        子类可重写此方法来指定从哪个模块导入。
        默认返回 None — 依赖运行时注册或 capability_ref。
        """
        return None

    def _make_capability_wrapper(self, capability_ref: str) -> Callable:
        """
        创建 Seam 能力调用的 wrapper。

        当节点配置了 capability_ref 时，节点执行时调用 harness Seam 能力。
        实际的 Seam 调用由外部注入 (harness py-bridge)。

        如果没有注入 seam_caller，返回一个占位函数，记录警告。
        """
        def capability_node(state: Any) -> Dict[str, Any]:
            seam_caller = getattr(self, '_seam_caller', None)
            if seam_caller:
                return seam_caller(capability_ref, state)
            logger.warning(f"capability_ref '{capability_ref}' 无 seam_caller, 返回空状态")
            return {}

        return capability_node

    def set_seam_caller(self, seam_caller: Callable) -> None:
        """
        注入 Seam 调用器 (由 harness py-bridge 设置)。

        Args:
            seam_caller: (capability_ref: str, state: Any) -> Dict[str, Any]
        """
        self._seam_caller = seam_caller

    def _resolve_condition_function(self, condition_name: str) -> Optional[Callable]:
        """
        解析条件函数。优先级:
          1. 运行时注册表
          2. 配置文件 condition_registry
          3. 从 workflow 模块动态导入 (fallback)
        """
        # 1. 运行时注册表
        if condition_name in self.condition_registry:
            return self.condition_registry[condition_name]

        # 2. 配置文件 condition_registry
        config_registry = self.raw_config.get("workflow", {}).get("condition_registry", {})
        if condition_name in config_registry:
            func_name = config_registry[condition_name]
            if func_name in self.condition_registry:
                return self.condition_registry[func_name]
            cond_func = self._import_condition_function(func_name)
            if cond_func:
                return cond_func

        # 3. 直接查找
        cond_func = self._import_condition_function(condition_name)
        if cond_func:
            return cond_func

        logger.error(f"找不到条件函数: {condition_name}")
        return None

    def _import_condition_function(self, func_name: str) -> Optional[Callable]:
        """
        从已注册的模块中导入条件函数。
        子类可重写此方法。默认返回 None。
        """
        return None

    # ── 构建图 ────────────────────────────────────────────────

    def build(self, fallback_graph: Optional[Any] = None) -> Any:
        """
        构建工作流图。

        Args:
            fallback_graph: 配置加载失败时使用的回退图

        Returns:
            编译后的 LangGraph StateGraph (可 invoke)
        """
        if self.config is None:
            logger.warning("工作流配置未加载，使用回退图")
            if fallback_graph is not None:
                return fallback_graph
            if self.state_schema is not None:
                return StateGraph(self.state_schema).compile()
            raise RuntimeError("工作流配置未加载且无 fallback_graph 和 state_schema")

        try:
            graph = StateGraph(self.state_schema) if self.state_schema else StateGraph(dict)

            # 添加节点
            nodes_config = self.raw_config.get("workflow", {}).get("nodes", {})
            for node_id, node_cfg in nodes_config.items():
                node_func = self._resolve_node_function(node_id)
                if node_func is None:
                    logger.error(f"节点 {node_id} 的函数无法解析，跳过")
                    continue
                graph.add_node(node_id, node_func)
                logger.debug(f"添加节点: {node_id}")

            # 设置入口点
            entry_point = self.config.entry_point
            graph.set_entry_point(entry_point)
            logger.debug(f"设置入口点: {entry_point}")

            # 添加普通边
            edges_config = self.raw_config.get("workflow", {}).get("flow", {}).get("edges", [])
            for edge in edges_config:
                from_node = edge.get("from")
                to_node = edge.get("to")

                if to_node == "__end__":
                    graph.add_edge(from_node, END)
                else:
                    graph.add_edge(from_node, to_node)

                logger.debug(f"添加边: {from_node} -> {to_node}")

            # 添加条件边
            conditional_edges = self.raw_config.get("workflow", {}).get("flow", {}).get("conditional_edges", [])
            for cedge in conditional_edges:
                from_node = cedge.get("from")
                condition_name = cedge.get("condition")

                condition_func = self._resolve_condition_function(condition_name)
                if condition_func is None:
                    logger.error(f"条件函数 {condition_name} 无法解析，跳过")
                    continue

                # 构建分支映射
                branch_map = {}
                for branch in cedge.get("branches", []):
                    condition = branch.get("condition")
                    to_node = branch.get("to")

                    if to_node == "__end__":
                        branch_map[condition] = END
                    else:
                        branch_map[condition] = to_node

                graph.add_conditional_edges(
                    from_node,
                    condition_func,
                    branch_map,
                )
                logger.debug(f"添加条件边: {from_node} -> {list(branch_map.keys())}")

            compiled = graph.compile()
            logger.info(f"工作流图构建完成: {self.config.name}")
            return compiled

        except Exception as e:
            logger.exception(f"构建工作流图失败: {e}")
            if fallback_graph is not None:
                return fallback_graph
            raise


# ── 保留旧 API 向后兼容 ──────────────────────────────────────

class WorkflowGraphBuilder:
    """
    工作流图构建器 (旧 API，向后兼容)。

    推荐使用 WorkflowBuilder 代替。
    """

    def __init__(self):
        self.nodes: Dict[str, Callable] = {}
        self.edges: Dict[str, list] = {}
        self.start_node: Optional[str] = None
        self.end_node: Optional[str] = None

    def add_node(self, name: str, node_func: Callable):
        self.nodes[name] = node_func
        return self

    def add_edge(self, from_node: str, to_node: str):
        if from_node not in self.edges:
            self.edges[from_node] = []
        self.edges[from_node].append(to_node)
        return self

    def set_start(self, node_name: str):
        self.start_node = node_name
        return self

    def set_end(self, node_name: str):
        self.end_node = node_name
        return self

    def build(self):
        """构建工作流图 (需要 state_schema, 否则抛异常)"""
        raise NotImplementedError(
            "WorkflowGraphBuilder.build is deprecated. Use WorkflowBuilder instead."
        )
