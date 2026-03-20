"""Shared string utilities."""

from typing import Any


def normalize_optional_str(value: Any) -> str | None:
    """将空字符串归一为 None，非空字符串去首尾空格。"""
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped if stripped else None
