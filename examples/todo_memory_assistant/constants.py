#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回环共享常量（把身份隔离变量集中放这里，避免 todo_memory_assistant 与
feedback_loop 之间的循环 import）。
"""

import os

# 记忆身份（一个固定 user + agent，真实场景按登录用户区分）
USER_ID = os.getenv("TODO_USER_ID", "demo-user-001")
AGENT_ID = "todo_memory_assistant"
SESSION_ID = os.getenv("TODO_SESSION_ID", "session-2026-08-22")
