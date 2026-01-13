#!/usr/bin/env python3
"""
PDF 处理公共工具模块
提供日期解析、字段验证等常用功能
"""

import json
import logging
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# 日期解析工具
# ============================================================================

# 支持的日期格式（按优先级排序）
DATE_FORMATS = [
    "%Y-%m-%d",  # 2024-01-15
    "%Y/%m/%d",  # 2024/01/15
    "%Y.%m.%d",  # 2024.01.15
    "%Y年%m月%d日",  # 2024年01月15日
    "%Y年%m月%d",  # 2024年1月15日
    "%d/%m/%Y",  # 15/01/2024
    "%m/%d/%Y",  # 01/15/2024
    "%d.%m.%Y",  # 15.01.2024
    "%d-%m-%Y",  # 15-01-2024
    "%Y%m%d",  # 20240115
]


def parse_contract_date(date_str: str | None) -> datetime | None:
    """
    解析合同日期字符串

    支持多种中文和英文日期格式

    Args:
        date_str: 日期字符串

    Returns:
        datetime 对象，解析失败返回 None

    Examples:
        >>> parse_contract_date("2024-01-15")
        datetime(2024, 1, 15, 0, 0)
        >>> parse_contract_date("2024年01月15日")
        datetime(2024, 1, 15, 0, 0)
        >>> parse_contract_date("invalid")
        None
    """
    if not date_str:
        return None

    if isinstance(date_str, datetime):
        return date_str

    date_str = str(date_str).strip()

    # 移除常见的日期前缀
    for prefix in ["日期", "签订日期", "签约日期", "时间:", "日期:"]:
        if date_str.startswith(prefix):
            date_str = date_str[len(prefix) :].strip()

    # 尝试各种格式
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    logger.warning(f"Failed to parse date: {date_str}")
    return None


def format_date(date: datetime | None, output_format: str = "%Y-%m-%d") -> str:
    """
    格式化日期

    Args:
        date: datetime 对象
        output_format: 输出格式

    Returns:
        格式化后的日期字符串，空日期返回空字符串
    """
    if not date:
        return ""
    return date.strftime(output_format)


def validate_date_range(start_date: datetime | None, end_date: datetime | None) -> bool:
    """
    验证日期范围有效性

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        bool: 日期范围是否有效
    """
    if not start_date or not end_date:
        return True

    return start_date <= end_date


# ============================================================================
# 金额解析工具
# ============================================================================


def parse_amount(amount_str: str | None) -> float | None:
    """
    解析金额字符串

    支持中文金额表达（如 "5000元", "5千元"）

    Args:
        amount_str: 金额字符串

    Returns:
        float: 金额值，解析失败返回 None

    Examples:
        >>> parse_amount("5000元")
        5000.0
        >>> parse_amount("5千元")
        5000.0
        >>> parse_amount("5.5万")
        55000.0
        >>> parse_amount("invalid")
        None
    """
    if not amount_str:
        return None

    if isinstance(amount_str, int | float):
        return float(amount_str)

    amount_str = str(amount_str).strip()

    # 移除常见的前缀和后缀
    amount_str = amount_str.replace("元", "").replace("￥", "").replace("¥", "")
    amount_str = amount_str.replace(",", "").strip()

    try:
        # 处理中文单位
        if "万" in amount_str:
            number = float(amount_str.replace("万", ""))
            return number * 10000
        elif "千" in amount_str:
            number = float(amount_str.replace("千", ""))
            return number * 1000
        elif "百" in amount_str:
            number = float(amount_str.replace("百", ""))
            return number * 100
        else:
            return float(amount_str)
    except (ValueError, InvalidOperation):
        logger.warning(f"Failed to parse amount: {amount_str}")
        return None


def format_amount(amount: float | None, unit: str = "元") -> str:
    """
    格式化金额

    Args:
        amount: 金额
        unit: 单位

    Returns:
        格式化后的金额字符串
    """
    if amount is None:
        return ""

    # 使用 Decimal 避免浮点精度问题
    decimal_amount = Decimal(str(amount))

    # 格式化为两位小数
    formatted = f"{decimal_amount:.2f}"

    # 移除不必要的 .00
    if formatted.endswith(".00"):
        formatted = formatted[:-3]

    return f"{formatted}{unit}"


# ============================================================================
# 字段验证工具
# ============================================================================


def validate_field_value(
    field_name: str, value: Any, rules: dict[str, Any] | None = None
) -> tuple[bool, str | None]:
    """
    验证字段值

    Args:
        field_name: 字段名称
        value: 字段值
        rules: 自定义验证规则

    Returns:
        (is_valid, error_message): 验证结果和错误消息

    Examples:
        >>> validate_field_value("contract_number", "HT2024001")
        (True, None)
        >>> validate_field_value("contract_number", "")
        (False, "合同编号不能为空")
    """
    if value is None:
        return False, f"{field_name} 不能为空"

    value_str = str(value).strip()

    # 内置验证规则
    validators = {
        "contract_number": _validate_contract_number,
        "party_a": _validate_party_name,
        "party_b": _validate_party_name,
        "landlord_name": _validate_party_name,
        "tenant_name": _validate_party_name,
        "property_address": _validate_address,
        "id_number": _validate_id_number,
        "phone": _validate_phone,
        "rent_amount": _validate_rent_amount,
    }

    # 使用自定义规则或内置规则
    if rules:
        is_valid = rules.get(field_name, lambda x: (True, None))(value)
        return is_valid if isinstance(is_valid, tuple) else (is_valid, None)

    validator = validators.get(field_name)
    if validator:
        return validator(value_str)

    # 默认通过
    return True, None


def _validate_contract_number(value: str) -> tuple[bool, str | None]:
    """验证合同编号"""
    if len(value) < 3:
        return False, "合同编号长度不能少于3个字符"
    return True, None


def _validate_party_name(value: str) -> tuple[bool, str | None]:
    """验证当事人名称"""
    if len(value) < 2:
        return False, "名称长度不能少于2个字符"
    return True, None


def _validate_address(value: str) -> tuple[bool, str | None]:
    """验证地址"""
    if len(value) < 5:
        return False, "地址长度不能少于5个字符"
    return True, None


def _validate_id_number(value: str) -> tuple[bool, str | None]:
    """验证身份证号或统一社会信用代码"""
    # 18位身份证
    if len(value) == 18 and value.isdigit():
        return True, None

    # 统一社会信用代码（18位）
    if len(value) == 18:
        return True, None

    return False, "证件号格式不正确"


def _validate_phone(value: str) -> tuple[bool, str | None]:
    """验证电话号码"""
    # 移除所有非数字字符
    digits = re.sub(r"\D", "", value)

    if len(digits) == 11 and digits.startswith("1"):
        return True, None

    if len(digits) >= 7:  # 座机号码至少7位
        return True, None

    return False, "电话号码格式不正确"


def _validate_rent_amount(value: str) -> tuple[bool, str | None]:
    """验证租金金额"""
    amount = parse_amount(value)
    if amount is None:
        return False, "租金金额格式不正确"

    if amount <= 0:
        return False, "租金金额必须大于0"

    if amount > 10000000:  # 1000万
        return False, "租金金额超出合理范围"

    return True, None


# ============================================================================
# JSON 工具
# ============================================================================


def safe_parse_json(json_str: str) -> dict[str, Any] | None:
    """
    安全解析 JSON

    Args:
        json_str: JSON 字符串

    Returns:
        解析后的字典，失败返回 None
    """
    if not json_str:
        return None

    try:
        from typing import cast

        return cast(dict[str, Any], json.loads(json_str))
    except json.JSONDecodeError:
        # 尝试提取 JSON 片段
        match = re.search(r"\{.*\}", json_str, re.DOTALL)
        if match:
            try:
                from typing import cast

                return cast(dict[str, Any], json.loads(match.group(0)))
            except json.JSONDecodeError:
                pass
        return None


def extract_json_from_response(response: str) -> dict[str, Any] | None:
    """
    从 LLM 响应中提取 JSON

    Args:
        response: LLM 响应文本

    Returns:
        解析后的字典，失败返回 None
    """
    return safe_parse_json(response)


# ============================================================================
# 文本清理工具
# ============================================================================


def clean_text(text: str | None, remove_extra_spaces: bool = True) -> str:
    """
    清理文本

    Args:
        text: 输入文本
        remove_extra_spaces: 是否移除多余空格

    Returns:
        清理后的文本
    """
    if not text:
        return ""

    text = text.strip()
    text = re.sub(r"\u3000", "", text)  # 移除全角空格

    if remove_extra_spaces:
        text = re.sub(r"\s+", " ", text)

    return text


def normalize_whitespace(text: str) -> str:
    """
    标准化空白字符

    Args:
        text: 输入文本

    Returns:
        标准化后的文本
    """
    # 统一为空格
    text = re.sub(r"[\u3000\u00A0\t\n\r]+", " ", text)
    # 移除多余空格
    text = re.sub(r" +", " ", text)
    return text.strip()


# ============================================================================
# 类型转换工具
# ============================================================================


def to_bool(value: Any) -> bool:
    """
    转换为布尔值

    Args:
        value: 输入值

    Returns:
        bool: 转换结果

    Examples:
        >>> to_bool("true")
        True
        >>> to_bool("1")
        True
        >>> to_bool("0")
        False
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, int | float):
        return bool(value)

    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "y", "on")

    return False


def to_int(value: Any, default: int = 0) -> int:
    """
    转换为整数

    Args:
        value: 输入值
        default: 默认值

    Returns:
        int: 转换结果
    """
    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    if isinstance(value, str):
        value = value.strip().replace(",", "")
        try:
            return int(float(value))
        except ValueError:
            return default

    return default


def to_float(value: Any, default: float = 0.0) -> float:
    """
    转换为浮点数

    Args:
        value: 输入值
        default: 默认值

    Returns:
        float: 转换结果
    """
    if isinstance(value, int | float):
        return float(value)

    if isinstance(value, str):
        value = value.strip().replace(",", "")
        try:
            return float(value)
        except ValueError:
            return default

    return default


# ============================================================================
# 列表/数组工具
# ============================================================================


def merge_dicts(*dicts: dict[str, Any]) -> dict[str, Any]:
    """
    合并多个字典（后面的覆盖前面的）

    Args:
        *dicts: 要合并的字典

    Returns:
        合并后的字典
    """
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result


def filter_none_values(data: dict[str, Any]) -> dict[str, Any]:
    """
    过滤掉值为 None 的项

    Args:
        data: 输入字典

    Returns:
        过滤后的字典
    """
    return {k: v for k, v in data.items() if v is not None}


def compact_list(lst: list[Any]) -> list[Any]:
    """
    压缩列表（移除 None 和空字符串）

    Args:
        lst: 输入列表

    Returns:
        压缩后的列表
    """
    return [item for item in lst if item not in (None, "")]


# ============================================================================
# 调试工具
# ============================================================================


def truncate_for_log(text: str, max_length: int = 200) -> str:
    """
    截断文本用于日志输出

    Args:
        text: 输入文本
        max_length: 最大长度

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text

    return text[:max_length] + f"... ({len(text)} chars total)"


def log_dict(d: dict[str, Any], max_value_length: int = 100) -> str:
    """
    将字典转换为可日志记录的字符串

    Args:
        d: 输入字典
        max_value_length: 值的最大长度

    Returns:
        格式化后的字符串
    """
    result = []
    for key, value in d.items():
        value_str = str(value)
        if len(value_str) > max_value_length:
            value_str = value_str[:max_value_length] + "..."
        result.append(f"{key}={value_str}")
    return "{" + ", ".join(result) + "}"
