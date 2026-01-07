"""
数值工具函数模块

提供安全的数值转换和处理函数
"""

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


def to_float(value: Any) -> float:
    """
    将可能为 None/Decimal/str 的值安全转换为 float

    Args:
        value: 任意值（可能是 None、Decimal、str、int、float 等）

    Returns:
        float: 转换后的浮点数，如果无法转换则返回 0.0
    """
    if value is None:
        return 0.0

    try:
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
    except (ValueError, TypeError) as e:
        logger.warning(f"数值转换失败: {value} -> {e}")
        return 0.0


def to_decimal(value: Any, default: Decimal | None = None) -> Decimal:
    """
    将值安全转换为 Decimal

    Args:
        value: 任意值
        default: 转换失败时的默认值，默认为 None（会转为 Decimal("0")）

    Returns:
        Decimal: 转换后的 Decimal 值
    """
    if default is None:
        default = Decimal("0")

    if value is None:
        return default

    try:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
    except (ValueError, TypeError) as e:
        logger.warning(f"Decimal转换失败: {value} -> {e}")
        return default


def safe_divide(
    numerator: float | Decimal,
    denominator: float | Decimal,
    default: float = 0.0,
) -> float:
    """
    安全除法，避免除以零错误

    Args:
        numerator: 分子
        denominator: 分母
        default: 除以零时的默认返回值

    Returns:
        float: 除法结果
    """
    try:
        if denominator == 0:
            return default
        return float(numerator / denominator)
    except (ValueError, TypeError, ZeroDivisionError):
        return default


def calculate_percentage(
    part: float | Decimal,
    whole: float | Decimal,
    decimal_places: int = 2,
) -> float:
    """
    计算百分比

    Args:
        part: 部分值
        whole: 整体值
        decimal_places: 小数位数

    Returns:
        float: 百分比值（0-100）
    """
    if whole == 0:
        return 0.0
    result = safe_divide(part, whole) * 100
    return round(result, decimal_places)
