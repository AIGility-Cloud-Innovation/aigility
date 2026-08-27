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
import importlib
import yaml
from typing import Dict, Any, Optional, Callable, Type
from langgraph.graph import StateGraph, END

from .schema import WorkflowConfig

logger = logging.getLogger(__name__)


def _resolve_dotted_path(path: str) -> Any:
    """把 'module.sub.attr' 字符串解析为 Python 对象 (类/函数)。

    兼容点分路径引用风格: 'tests.workflow_state.TestState' → TestState 类。
    解析失败时原样返回字符串, 不抛异常 (调用方再决定如何处理)。
    """
    if not isinstance(path, str) or "." not in path:
        return path
    try:
        parts = path.split(".")
        for i in range(len(parts), 0, -1):
            try:
                mod = importlib.import_module(".".join(parts[:i]))
                obj = mod
                for attr in parts[i:]:
                    obj = getattr(obj, attr)
                return obj
            except (ImportError, AttributeError):
                continue
        return path
    except Exception:
        return path


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
        node_module: Optional[str] = None,
        condition_module: Optional[str] = None,
    ):
        self.config_path = config_path
        # state_schema 兼容两种传法: Type 类直接使用, 点分路径字符串自动解析为类
        self.state_schema = (
            _resolve_dotted_path(state_schema)
            if isinstance(state_schema, str)
            else state_schema
        )
        self.config: Optional[WorkflowConfig] = None
        self.raw_config: Dict[str, Any] = {}
        self.node_registry: Dict[str, Callable] = node_registry or {}
        self.condition_registry: Dict[str, Callable] = condition_registry or {}
        self.node_module: Optional[str] = node_module
        self.condition_module: Optional[str] = condition_module

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
        # 0. 按节点类型分发: llm_node → LLM 调用闭包
        node_cfg = self.raw_config.get("workflow", {}).get("nodes", {}).get(node_id, {})
        if isinstance(node_cfg, dict) and node_cfg.get("type") == "llm_node":
            return self._make_llm_node(node_id, node_cfg)

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
        从 node_module 导入节点函数。
        node_module 在 __init__ 时设置，指向包含节点函数的 Python 模块。
        """
        if self.node_module:
            try:
                import importlib
                mod = importlib.import_module(self.node_module)
                return getattr(mod, func_name, None)
            except (ImportError, AttributeError):
                return None
        return None

    def _make_llm_node(self, node_id: str, node_cfg: Dict[str, Any]) -> Callable:
        """
        创建 LLM 节点闭包。

        llm_node 通过 prompt_ref 引用提示词（格式: module.prompt_name 或
        直接文本），把 state 中的 user_input 传给 LLM，返回生成文本。

        LLM 端点配置 (环境变量):
          LITELLM_URL / LITELLM_KEY  — 兼容 OpenAI 协议的网关 (LiteLLM)
          LLM_MODEL                  — 模型名 (默认 deepseek-v4-pro)
        未配置时降级为确定性回退文本（不崩，便于原型链路验证）。
        """
        prompt_ref = node_cfg.get("prompt_ref")
        output_keys = node_cfg.get("output_keys") or ["result"]

        # 解析提示词: 支持 "module.prompt_name" 引用，或直接文本
        def _resolve_prompt() -> str:
            if not prompt_ref:
                return "你是 aigility 智能助手。"
            if "." not in prompt_ref:
                return prompt_ref  # 直接文本
            try:
                mod_name, prompt_name = prompt_ref.rsplit(".", 1)
                mod = importlib.import_module(mod_name)
                p = getattr(mod, prompt_name)
                return p if isinstance(p, str) else str(p)
            except (ImportError, AttributeError):
                logger.warning(f"prompt_ref '{prompt_ref}' 解析失败，使用默认提示词")
                return "你是 aigility 智能助手。"

        prompt = _resolve_prompt()

        def llm_node(state: Any) -> Dict[str, Any]:
            # 提取用户输入
            user_input = ""
            context = ""
            if isinstance(state, dict):
                user_input = str(state.get("user_input", state.get("input", "")) or "")
                context = str(state.get("retrieved_context", state.get("context", "")) or "")
            else:
                user_input = str(getattr(state, "user_input", "") or "")
                context = str(getattr(state, "retrieved_context", "") or "")
            logger.info(f"llm_node[{node_id}] state keys={list(state.keys()) if isinstance(state, dict) else type(state)} user_input='{user_input[:50]}'")

            try:
                base_url = os.environ.get("LITELLM_URL", "http://127.0.0.1:48724")
                api_key = os.environ.get("LITELLM_KEY", "sk-1234")
                model = os.environ.get("LLM_MODEL", "deepseek-v4-flash")

                # 用户消息: 附加上下文 (检索片段), LLM 基于真实知识回答
                user_msg = user_input
                if context:
                    user_msg = f"【知识库检索到的相关内容，请基于此回答，若无关联则如实说明】\n{context}\n\n【用户问题】\n{user_input}"

                content = self._call_llm(base_url, api_key, model, prompt, user_msg)
                logger.info(f"llm_node[{node_id}] model={model} len={len(content)}")

                # 写回输出键
                if len(output_keys) == 1:
                    return {output_keys[0]: content}
                return {**{k: content for k in output_keys}, "user_input": user_input}
            except Exception as e:
                logger.error(f"llm_node[{node_id}] LLM 调用失败: {e}")
                fallback = (
                    f"（llm_node 降级）无法连接 LLM 服务: {e}\n"
                    f"收到消息: {user_input}"
                )
                if len(output_keys) == 1:
                    return {output_keys[0]: fallback}
                return {**{k: fallback for k in output_keys}, "user_input": user_input}

        return llm_node

    def _call_llm(
        self,
        base_url: str,
        api_key: str,
        model: str,
        prompt: str,
        user_input: str,
    ) -> str:
        """调用 OpenAI 兼容协议 LLM 端点 (LiteLLM 网关)。"""
        # 优先尝试 litellm 库；不存在则用标准库 urllib 调 OpenAI 兼容 API
        try:
            from litellm import completion

            resp = completion(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_input},
                ],
                api_base=base_url,
                api_key=api_key,
                temperature=0.7,
            )
            return str(resp.choices[0].message.content or "").strip()
        except ImportError:
            pass

        # 标准库回退: urllib 调 /v1/chat/completions
        import json as _json
        import urllib.request

        body = _json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_input},
            ],
            "temperature": 0.7,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
        return str(data["choices"][0]["message"]["content"] or "").strip()

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
            logger.warning(f"capability_ref '{capability_ref}' 无 seam_caller, 透传当前状态")
            # LangGraph 要求至少写入一个 state key，这里透传原状态避免 InvalidUpdateError
            if hasattr(state, "items"):
                return dict(state)
            return {"_capability_fallback": True}

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
        从 condition_module 导入条件函数。
        """
        if self.condition_module:
            try:
                import importlib
                mod = importlib.import_module(self.condition_module)
                return getattr(mod, func_name, None)
            except (ImportError, AttributeError):
                return None
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
