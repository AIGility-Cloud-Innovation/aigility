# -*- coding: utf-8 -*-
"""框架介绍员/TiMEM客服工作流 State — 允许 user_input/上下文 透传 LLM 节点"""

from typing import TypedDict, Optional


class HarnessGuideState(TypedDict, total=False):
    """客服工作流状态

    - user_input: 用户在企微/入口输入的问题
    - user_id / agent_id: 记忆归属 (按用户/agent 隔离)
    - recent_history: 最近对话上下文 (瞬时记忆)
    - retrieved_context: 知识库检索片段
    - memory_context: 用户历史记忆召回
    - result / save_result: llm 回答 / 记忆保存结果
    """

    user_input: str
    user_id: str
    agent_id: str
    recent_history: str
    retrieved_context: str
    memory_context: str
    result: Optional[str]
    save_result: Optional[str]