#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
todo_retriever —— 从 MySQL 召回「今日 todo / subtask」（真实 SQL 召回）

这是 todo_memory_assistant 回环的「数据源头」。它直接连 fastapi_todo_refactored
使用的同一个 MySQL 库（todo_db），按 created_at 落在当天召回 todos 及其 subtasks，
拼成可注入 LLM prompt 的纯文本。

为什么不复用 app 包的模型？
  - 本示例在 aigility 仓库里，不能把整个 fastapi_todo_refactored 后端当子依赖。
  - 这里用「同构轻量模型」映射同一套表（todos / subtasks），字段与
    fastapi_todo_refactored/app/models/{todo,subtask}.py 保持一致。
  - 源模型定义（权威）：
        fastapi_todo_refactored/app/models/todo.py    -> Todo(__tablename__="todos")
        fastapi_todo_refactored/app/models/subtask.py -> Subtask(__tablename__="subtasks")

连接配置（环境变量，优先级从高到低）：
    DATABASE_URL  完整 SQLAlchemy URL，如
                  mysql+pymysql://user:pass@host:3306/todo_db?charset=utf8mb4
    若未设置，回退到本地默认（与本机 fastapi_todo_refactored 一致）。

依赖：sqlalchemy + pymysql（pip install sqlalchemy pymysql）
"""

import os
from datetime import date, datetime, time
from typing import List, Dict, Any, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    create_engine,
    select,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# ----------------------------------------------------------------------------
# 同构轻量模型（与 fastapi_todo_refactored/app/models/{todo,subtask}.py 对齐）
#   说明：源模型 priority 用 SQLAlchemy Enum(Priority)，这里为与 MySQL 中
#        实际存储的枚举字符串（'high'/'medium'/'low'）对齐，直接用 String 读取，
#        避免 SQLAlchemy 2.x Enum 初始化差异。取值语义完全一致。
# ----------------------------------------------------------------------------
Base = declarative_base()


class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    completed = Column(Boolean, default=False)
    priority = Column(String(16), default="medium", nullable=False)
    created_at = Column(DateTime(timezone=True))


class Subtask(Base):
    __tablename__ = "subtasks"

    id = Column(Integer, primary_key=True, index=True)
    parent_task_id = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True))


# ----------------------------------------------------------------------------
# 连接
# ----------------------------------------------------------------------------
DEFAULT_DATABASE_URL = (
    "mysql+pymysql://root:S6%23rT%265m%2BG2%24@127.0.0.1:3306/todo_db?charset=utf8mb4"
)


def get_engine():
    """根据环境变量构造同步引擎（pymysql 驱动）。"""
    url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    connect_args = {"charset": "utf8mb4"} if url.startswith("mysql") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


def _today_range() -> tuple[datetime, datetime]:
    """返回今天 00:00:00 ~ 23:59:59.999999 的闭区间。"""
    today = date.today()
    start = datetime.combine(today, time.min)
    end = datetime.combine(today, time.max)
    return start, end


def retrieve_today_todos(
    engine=None, target_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """召回指定日期（默认今天）创建的 todos 及其 subtasks。

    返回结构（每个 todo 一项）：
        {
            "id": int,
            "title": str,
            "description": str | None,
            "completed": bool,
            "priority": str,
            "created_at": str,
            "subtasks": [ {"id", "title", "completed"}, ... ]
        }
    """
    if engine is None:
        engine = get_engine()

    if target_date is None:
        start, end = _today_range()
    else:
        start = datetime.combine(target_date, time.min)
        end = datetime.combine(target_date, time.max)

    Session = sessionmaker(bind=engine)
    out: List[Dict[str, Any]] = []
    with Session() as session:
        stmt = (
            select(Todo)
            .where(Todo.created_at >= start, Todo.created_at <= end)
            .order_by(Todo.created_at.asc())
        )
        todos = session.execute(stmt).scalars().all()
        for t in todos:
            sub_stmt = select(Subtask).where(
                Subtask.parent_task_id == t.id
            ).order_by(Subtask.id.asc())
            subs = session.execute(sub_stmt).scalars().all()
            out.append(
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "completed": bool(t.completed),
                    "priority": t.priority or "medium",
                    "created_at": t.created_at.isoformat() if t.created_at else "",
                    "subtasks": [
                        {
                            "id": s.id,
                            "title": s.title,
                            "completed": bool(s.completed),
                        }
                        for s in subs
                    ],
                }
            )
    return out


def format_todos_as_text(
    todos: List[Dict[str, Any]], target_date: Optional[date] = None
) -> str:
    """把召回结果拼成可注入 prompt 的文本。"""
    day_label = (target_date or date.today()).isoformat()
    if not todos:
        return f"（{day_label} 无新建 todo）"

    lines: List[str] = [f"【{day_label} 新建的 todo 清单】"]
    for t in todos:
        status = "✓已完成" if t["completed"] else "○未完成"
        lines.append(
            f"- [#{t['id']}] ({t['priority']}) {t['title']} —— {status}"
        )
        if t["description"]:
            lines.append(f"    描述：{t['description']}")
        if t["subtasks"]:
            for s in t["subtasks"]:
                s_status = "✓" if s["completed"] else "○"
                lines.append(f"    · [{s_status}] {s['title']}")
    return "\n".join(lines)


def retrieve_today_todos_as_text(
    engine=None, target_date: Optional[date] = None
) -> str:
    """一步到位：召回并格式化为文本（给主流程 / server 直接调用）。"""
    todos = retrieve_today_todos(engine=engine, target_date=target_date)
    return format_todos_as_text(todos, target_date=target_date)


# ----------------------------------------------------------------------------
# CLI 自测：python todo_retriever.py
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        eng = get_engine()
        text = retrieve_today_todos_as_text(engine=eng)
        print(text)
    except Exception as exc:  # noqa: BLE001
        print(f"✗ 召回失败：{exc}")
        print("  请确认 DATABASE_URL 指向的 MySQL 可达，且存在 todos/subtasks 表。")
