# -*- coding: utf-8 -*-
"""
工作流配置 IO — WorkflowConfig/dict 与 YAML 文件的序列化。

与 schema.py 配套：save_yaml 写出的 YAML 可直接被 WorkflowConfig 校验
读回（边的 from/to 使用别名形式）。
"""

from pathlib import Path
from typing import Any, Dict, Union

import yaml

from .schema import WorkflowConfig


def _strip_none(obj: Any) -> Any:
    """递归剔除 dict/list 中的 None 值（Optional 字段 model_dump 后的默认值）"""
    if isinstance(obj, dict):
        return {k: _strip_none(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_strip_none(item) for item in obj]
    return obj


def save_yaml(config: Union[WorkflowConfig, Dict[str, Any]], path: Union[str, Path]) -> Path:
    """将工作流配置写入 YAML 文件。

    - WorkflowConfig: 先 model_dump(by_alias=True)（如 EdgeConfig 的
      from_node 输出为 from，与 schema 读取格式一致），再递归清理 None 字段。
    - dict: 视为已就绪的配置数据，原样写出。

    Args:
        config: WorkflowConfig 实例或配置 dict。
        path: 目标 YAML 文件路径（str 或 Path），父目录需已存在。

    Returns:
        写入的文件 Path。
    """
    if isinstance(config, WorkflowConfig):
        data = _strip_none(config.model_dump(by_alias=True))
    else:
        data = config

    path = Path(path)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path
