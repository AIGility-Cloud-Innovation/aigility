"""
ADK 配置管理

提供全局配置、智能体配置、工具配置等。
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


@dataclass
class ADKConfig:
    """ADK 全局配置"""
    # LLM 配置
    llm_provider: str = "openai"  # openai, anthropic, etc.
    llm_model: str = "gpt-4"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2000

    # Reasoning (思维链) 配置
    # 注意: 开关需与模型能力匹配。普通模型开启可能被 API 拒绝(400)；
    # 纯推理模型(deepseek-reasoner/o1 等)关闭无效, 思考由模型侧强制执行。
    llm_reasoning: bool = False  # 是否启用推理模型的思维链模式(如 deepseek-v4 系列 / OpenAI o 系列)
    llm_reasoning_effort: Optional[str] = None  # OpenAI o 系列专用: "low" | "medium" | "high"
    
    # Memory 配置
    memory_enabled: bool = True
    memory_api_key: Optional[str] = None
    memory_base_url: Optional[str] = None
    
    # Knowledge 配置
    knowledge_enabled: bool = True
    knowledge_store_type: str = "vector"  # vector, graph, hybrid

    # 太忆 (TimeM) RAG 云服务配置
    timem_api_key: Optional[str] = None  # 太忆API Key
    timem_base_url: Optional[str] = None  # 太忆API基础URL
    timem_enabled: bool = False  # 是否启用太忆RAG服务

    # 工作流配置
    workflow_timeout: float = 300.0
    workflow_max_steps: int = 50
    
    # HTTP 配置
    http_timeout: float = 60.0
    http_max_retries: int = 3
    http_verify_ssl: bool = False
    
    # 其他配置
    debug: bool = False
    log_level: str = "INFO"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith("_")
        }


@dataclass
class AgentConfig:
    """智能体配置"""
    name: str
    description: str
    prompt_template: Optional[str] = None
    tools: List[str] = field(default_factory=list)
    memory_enabled: bool = True
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolConfig:
    """工具配置"""
    name: str
    description: str
    schema: Dict[str, Any]
    enabled: bool = True
    timeout: float = 30.0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

