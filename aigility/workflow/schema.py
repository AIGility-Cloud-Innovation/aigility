# -*- coding: utf-8 -*-
"""
工作流配置 Schema — Pydantic 模型，用于验证 workflow_config.yaml。

从 reachAI 实践经验提炼，去掉场景特定字段，保留通用工作流配置模型。
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class NodeConfig(BaseModel):
    """节点配置模型"""
    type: str = Field(description="节点类型: llm_node / function_node / capability_node")
    description: Optional[str] = Field(default="", description="节点描述")
    prompt_ref: Optional[str] = Field(default=None, description="提示词引用，格式: module.prompt_name")
    function_ref: Optional[str] = Field(default=None, description="函数引用名")
    capability_ref: Optional[str] = Field(default=None, description="Seam 能力 ID，如 @cognitive/rag-retrieval")
    output_keys: List[str] = Field(default_factory=list, description="输出键列表")


class EdgeConfig(BaseModel):
    """边配置模型"""
    model_config = ConfigDict(populate_by_name=True)

    from_node: str = Field(alias="from", description="起始节点 ID")
    to: str = Field(description="目标节点 ID，__end__ 表示结束")


class ConditionalEdgeBranch(BaseModel):
    """条件边分支配置"""
    condition: str = Field(description="分支条件表达式")
    to: str = Field(description="目标节点 ID")
    description: Optional[str] = Field(default="", description="分支描述")


class ConditionalEdgeConfig(BaseModel):
    """条件边配置模型"""
    model_config = ConfigDict(populate_by_name=True)

    from_node: str = Field(alias="from", description="起始节点 ID")
    condition: str = Field(description="条件函数名")
    description: Optional[str] = Field(default="", description="条件描述")
    branches: List[ConditionalEdgeBranch] = Field(description="分支列表")


class FlowConfig(BaseModel):
    """流程配置模型"""
    edges: List[EdgeConfig] = Field(default_factory=list, description="普通边列表")
    conditional_edges: List[ConditionalEdgeConfig] = Field(default_factory=list, description="条件边列表")


class WorkflowConfig(BaseModel):
    """工作流配置模型"""
    name: str = Field(description="工作流名称")
    description: Optional[str] = Field(default="", description="工作流描述")
    entry_point: str = Field(description="入口节点 ID")
    nodes: Dict[str, NodeConfig] = Field(description="节点配置字典")
    flow: FlowConfig = Field(default_factory=FlowConfig, description="流程配置")
