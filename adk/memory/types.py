"""
Memory 类型定义
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class MemoryResult:
    """记忆结果"""
    memory_id: str
    content: Dict[str, Any]
    layer: str = "L1"
    tags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemorySearchResult:
    """记忆搜索结果"""
    memory: str
    score: float
    id: str
    layer: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

