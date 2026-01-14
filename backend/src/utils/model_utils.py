from typing import Any

"""
通用工具函数模块
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Mapper, class_mapper

# Type alias for SQLAlchemy models
SQLAlchemyModel = Any


def model_to_dict(model: Any, include_relations: bool = False) -> dict[str, Any] | None:
    """
    通用的模型转字典工具函数

    Args:
        model: SQLAlchemy模型实例
        include_relations: 是否包含关联关系数据

    Returns:
        转换后的字典，如果model为None则返回None
    """
    if model is None:
        return None

    mapper: Mapper[Any] = class_mapper(model.__class__)
    columns = [c.key for c in mapper.columns]
    result: dict[str, Any] = {}

    for column in columns:
        value = getattr(model, column)

        # 处理特殊类型
        if isinstance(value, datetime | date):
            result[column] = value.isoformat()
        elif isinstance(value, Decimal):
            result[column] = float(value)
        else:
            result[column] = value

    # 处理关联关系
    if include_relations:
        for rel in mapper.relationships:
            rel_value = getattr(model, rel.key)
            if rel_value is not None:
                if rel.uselist:  # 一对多关系
                    # Type assertion: we know this is a list of models
                    result[rel.key] = [
                        item_dict
                        for item in rel_value
                        if item is not None
                        and (item_dict := model_to_dict(item)) is not None
                    ]
                else:  # 多对一或一对一关系
                    dict_result = model_to_dict(rel_value)
                    if dict_result is not None:
                        result[rel.key] = dict_result

    return result


def batch_to_dict(
    models: list[Any], include_relations: bool = False
) -> list[dict[str, Any]]:
    """
    批量转换模型为字典

    Args:
        models: SQLAlchemy模型实例列表
        include_relations: 是否包含关联关系数据

    Returns:
        转换后的字典列表
    """
    return [
        model_dict
        for model in models
        if (model_dict := model_to_dict(model, include_relations)) is not None
    ]


def generate_uuid() -> str:
    """
    生成UUID字符串

    Returns:
        UUID字符串
    """
    return str(uuid.uuid4())


def format_currency(amount: Decimal | None, decimal_places: int = 2) -> float:
    """
    格式化金额为浮点数

    Args:
        amount: 金额
        decimal_places: 保留小数位数

    Returns:
        格式化后的浮点数
    """
    if amount is None:
        return 0.0
    return round(float(amount), decimal_places)


def calculate_percentage(part: Decimal, total: Decimal) -> float:
    """
    计算百分比

    Args:
        part: 部分值
        total: 总值

    Returns:
        百分比值
    """
    if total == 0:
        return 0.0
    return round(float(part / total * 100), 2)


def validate_date_range(start_date: date, end_date: date) -> bool:
    """
    验证日期范围是否有效

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        是否有效
    """
    return start_date <= end_date


def generate_month_range(start_month: str, end_month: str) -> list[str]:
    """
    生成月份范围列表

    Args:
        start_month: 开始月份 (YYYY-MM)
        end_month: 结束月份 (YYYY-MM)

    Returns:
        月份列表
    """
    try:
        start_year, start_month_num = map(int, start_month.split("-"))
        end_year, end_month_num = map(int, end_month.split("-"))

        months = []
        current_year = start_year
        current_month = start_month_num

        while (current_year < end_year) or (
            current_year == end_year and current_month <= end_month_num
        ):
            months.append(f"{current_year}-{current_month:02d}")

            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        return months
    except ValueError:
        raise ValueError(f"无效的月份格式: {start_month}, {end_month}")


def safe_divide(
    numerator: Decimal | None, denominator: Decimal | None, default: float = 0.0
) -> float:
    """
    安全除法，避免除零错误

    Args:
        numerator: 分子
        denominator: 分母
        default: 默认值

    Returns:
        除法结果
    """
    if denominator is None or denominator == 0:
        return default
    if numerator is None:
        return default
    return float(numerator / denominator)


def format_phone_number(phone: str) -> str:
    """
    格式化电话号码

    Args:
        phone: 电话号码

    Returns:
        格式化后的电话号码
    """
    if not phone:
        return ""

    # 移除所有非数字字符
    digits = "".join(c for c in phone if c.isdigit())

    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    elif len(digits) == 8:
        return f"{digits[:4]}-{digits[4:]}"
    else:
        return phone


def truncate_string(text: str, max_length: int = 100) -> str:
    """
    截断字符串

    Args:
        text: 原始字符串
        max_length: 最大长度

    Returns:
        截断后的字符串
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[: max_length - 3] + "..."
