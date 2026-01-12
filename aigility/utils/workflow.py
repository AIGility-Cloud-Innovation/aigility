"""
工作流工具

提供工作流构建和管理功能。
"""

from typing import Any, Dict, Callable, Optional
from ..core.types import State


class WorkflowBuilder:
    """工作流构建器"""
    
    def __init__(self):
        self.nodes: Dict[str, Callable] = {}
        self.edges: Dict[str, list] = {}
        self.start_node: Optional[str] = None
    
    def add_node(self, name: str, func: Callable):
        """添加节点"""
        self.nodes[name] = func
        return self
    
    def add_edge(self, from_node: str, to_node: str):
        """添加边"""
        if from_node not in self.edges:
            self.edges[from_node] = []
        self.edges[from_node].append(to_node)
        return self
    
    def set_start(self, node_name: str):
        """设置起始节点"""
        self.start_node = node_name
        return self
    
    async def run(self, initial_state: State) -> State:
        """运行工作流"""
        if not self.start_node:
            raise ValueError("Start node not set")
        
        current_node = self.start_node
        state = initial_state
        
        while current_node:
            if current_node not in self.nodes:
                break
            
            func = self.nodes[current_node]
            result = await func(state)
            
            if isinstance(result, State):
                state = result
            elif isinstance(result, dict):
                state = state.update(**result)
            
            # 获取下一个节点
            next_nodes = self.edges.get(current_node, [])
            if next_nodes:
                current_node = next_nodes[0]  # 简单实现，只取第一个
            else:
                break
        
        return state


def create_workflow() -> WorkflowBuilder:
    """创建工作流构建器"""
    return WorkflowBuilder()

