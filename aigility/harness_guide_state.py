# -*- coding: utf-8 -*-
"""框架介绍员工作流 State — 允许 user_input 透传 LLM 节点"""

from typing import TypedDict, Optional


class HarnessGuideState(TypedDict, total=False):
    """框架介绍员工作流状态

    - user_input: 用户在企微/入口输入的问题
    - result: llm_node 生成的回答
    """

    user_input: str
    result: Optional[str]