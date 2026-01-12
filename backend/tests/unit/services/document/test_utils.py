#!/usr/bin/env python3
"""
Unit tests for document processing utils
文档处理公共工具单元测试
"""

from datetime import datetime

import pytest

from src.services.document.utils import (
    clean_text,
    compact_list,
    extract_json_from_response,
    filter_none_values,
    format_amount,
    format_date,
    log_dict,
    merge_dicts,
    normalize_whitespace,
    parse_amount,
    parse_contract_date,
    safe_parse_json,
    to_bool,
    to_float,
    to_int,
    truncate_for_log,
    validate_date_range,
    validate_field_value,
)


class TestDateParsing:
    """日期解析测试"""

    def test_parse_iso_format(self):
        """测试解析 ISO 格式日期"""
        result = parse_contract_date("2024-01-15")
        assert result == datetime(2024, 1, 15)

    def test_parse_slash_format(self):
        """测试解析斜杠分隔日期"""
        result = parse_contract_date("2024/01/15")
        assert result == datetime(2024, 1, 15)

    def test_parse_chinese_format(self):
        """测试解析中文日期"""
        result = parse_contract_date("2024年01月15日")
        assert result == datetime(2024, 1, 15)

    def test_parse_compact_format(self):
        """测试解析紧凑格式"""
        result = parse_contract_date("20240115")
        assert result == datetime(2024, 1, 15)

    def test_parse_invalid_date(self):
        """测试解析无效日期"""
        result = parse_contract_date("invalid-date")
        assert result is None

    def test_parse_none_returns_none(self):
        """测试解析 None 返回 None"""
        result = parse_contract_date(None)
        assert result is None

    def test_parse_datetime_input(self):
        """测试解析 datetime 输入"""
        dt = datetime(2024, 6, 15)
        result = parse_contract_date(dt)
        assert result == dt

    def test_format_date(self):
        """测试格式化日期"""
        dt = datetime(2024, 6, 15)
        result = format_date(dt)
        assert result == "2024-06-15"

    def test_format_date_none(self):
        """测试格式化 None 日期"""
        result = format_date(None)
        assert result == ""

    def test_validate_date_range_valid(self):
        """测试有效日期范围"""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        assert validate_date_range(start, end) is True

    def test_validate_date_range_invalid(self):
        """测试无效日期范围"""
        start = datetime(2024, 12, 31)
        end = datetime(2024, 1, 1)
        assert validate_date_range(start, end) is False

    def test_validate_date_range_with_none(self):
        """测试包含 None 的日期范围"""
        assert validate_date_range(None, datetime(2024, 1, 1)) is True
        assert validate_date_range(datetime(2024, 1, 1), None) is True


class TestAmountParsing:
    """金额解析测试"""

    def test_parse_simple_amount(self):
        """测试解析简单金额"""
        assert parse_amount("5000") == 5000.0
        assert parse_amount("5000.50") == 5000.50

    def test_parse_amount_with_unit(self):
        """测试解析带单位的金额"""
        assert parse_amount("5000元") == 5000.0
        assert parse_amount("5千元") == 5000.0
        assert parse_amount("5百元") == 500.0

    def test_parse_amount_with_wan(self):
        """测试解析万元"""
        assert parse_amount("5万") == 50000.0
        assert parse_amount("5.5万") == 55000.0

    def test_parse_amount_with_yuan_symbol(self):
        """测试解析带货币符号的金额"""
        assert parse_amount("¥5000") == 5000.0
        assert parse_amount("￥5000") == 5000.0

    def test_parse_amount_with_commas(self):
        """测试解析带千分位的金额"""
        assert parse_amount("5,000.50") == 5000.50

    def test_parse_amount_float_input(self):
        """测试解析浮点数输入"""
        assert parse_amount(5000.0) == 5000.0
        assert parse_amount(5000) == 5000.0

    def test_parse_amount_invalid(self):
        """测试解析无效金额"""
        assert parse_amount("invalid") is None
        assert parse_amount(None) is None

    def test_format_amount(self):
        """测试格式化金额"""
        assert format_amount(5000) == "5000元"
        assert format_amount(5000.50) == "5000.50元"
        assert format_amount(5000.0) == "5000元"

    def test_format_amount_none(self):
        """测试格式化 None 金额"""
        assert format_amount(None) == ""


class TestFieldValidation:
    """字段验证测试"""

    def test_validate_contract_number_valid(self):
        """测试有效合同编号"""
        is_valid, error = validate_field_value("contract_number", "HT2024001")
        assert is_valid is True
        assert error is None

    def test_validate_contract_number_invalid(self):
        """测试无效合同编号"""
        is_valid, error = validate_field_value("contract_number", "AB")
        assert is_valid is False
        assert "长度" in error

    def test_validate_party_name_valid(self):
        """测试有效当事人名称"""
        is_valid, error = validate_field_value("party_a", "张三")
        assert is_valid is True

    def test_validate_party_name_invalid(self):
        """测试无效当事人名称"""
        is_valid, error = validate_field_value("party_a", "张")
        assert is_valid is False

    def test_validate_phone_valid(self):
        """测试有效手机号"""
        is_valid, error = validate_field_value("phone", "13800138000")
        assert is_valid is True

    def test_validate_phone_with_format(self):
        """测试带格式的手机号"""
        is_valid, error = validate_field_value("phone", "138-0013-8000")
        assert is_valid is True

    def test_validate_phone_invalid(self):
        """测试无效手机号"""
        is_valid, error = validate_field_value("phone", "123")
        assert is_valid is False

    def test_validate_rent_amount_valid(self):
        """测试有效租金"""
        is_valid, error = validate_field_value("rent_amount", "5000元")
        assert is_valid is True

    def test_validate_rent_amount_invalid_format(self):
        """测试无效租金格式"""
        is_valid, error = validate_field_value("rent_amount", "invalid")
        assert is_valid is False

    def test_validate_rent_amount_too_large(self):
        """测试租金超出范围"""
        is_valid, error = validate_field_value("rent_amount", "100000000元")
        assert is_valid is False


class TestJSONUtils:
    """JSON 工具测试"""

    def test_safe_parse_json_valid(self):
        """测试解析有效 JSON"""
        result = safe_parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_safe_parse_json_invalid(self):
        """测试解析无效 JSON"""
        result = safe_parse_json("not json")
        assert result is None

    def test_safe_parse_json_empty(self):
        """测试解析空字符串"""
        result = safe_parse_json("")
        assert result is None

    def test_extract_json_from_response(self):
        """测试从响应中提取 JSON"""
        response = 'Some text {"key": "value"} more text'
        result = extract_json_from_response(response)
        assert result == {"key": "value"}

    def test_extract_json_no_json(self):
        """测试无 JSON 的响应"""
        result = extract_json_from_response("just plain text")
        assert result is None


class TestTextCleaning:
    """文本清理测试"""

    def test_clean_text_basic(self):
        """测试基本清理"""
        assert clean_text("  hello  world  ") == "hello world"

    def test_clean_text_removes_fullwidth_space(self):
        """测试移除全角空格"""
        assert clean_text("hello\u3000world") == "helloworld"

    def test_clean_text_none(self):
        """测试清理 None"""
        assert clean_text(None) == ""

    def test_normalize_whitespace(self):
        """测试标准化空白字符"""
        assert normalize_whitespace("hello   \t\n  world") == "hello world"

    def test_normalize_whitespace_fullwidth(self):
        """测试标准化全角空格"""
        assert normalize_whitespace("hello\u3000world") == "hello world"


class TestTypeConversion:
    """类型转换测试"""

    def test_to_bool_true_values(self):
        """测试转换为 True"""
        assert to_bool("true") is True
        assert to_bool("1") is True
        assert to_bool("yes") is True
        assert to_bool("Y") is True
        assert to_bool(1) is True
        assert to_bool(True) is True

    def test_to_bool_false_values(self):
        """测试转换为 False"""
        assert to_bool("false") is False
        assert to_bool("0") is False
        assert to_bool("no") is False
        assert to_bool(0) is False
        assert to_bool(False) is False

    def test_to_int_valid(self):
        """测试转换为整数"""
        assert to_int("123") == 123
        assert to_int("123.45") == 123
        assert to_int("1,234") == 1234

    def test_to_int_invalid(self):
        """测试无效值转换整数"""
        assert to_int("invalid") == 0
        assert to_int("invalid", default=10) == 10

    def test_to_float_valid(self):
        """测试转换为浮点数"""
        assert to_float("123.45") == 123.45
        assert to_float("123") == 123.0
        assert to_float("1,234.56") == 1234.56

    def test_to_float_invalid(self):
        """测试无效值转换浮点数"""
        assert to_float("invalid") == 0.0
        assert to_float("invalid", default=10.0) == 10.0


class TestListUtils:
    """列表工具测试"""

    def test_merge_dicts(self):
        """测试合并字典"""
        result = merge_dicts({"a": 1}, {"b": 2}, {"a": 3})
        assert result == {"a": 3, "b": 2}

    def test_merge_dicts_empty(self):
        """测试合并空字典"""
        result = merge_dicts()
        assert result == {}

    def test_filter_none_values(self):
        """测试过滤 None 值"""
        result = filter_none_values({"a": 1, "b": None, "c": ""})
        assert result == {"a": 1, "c": ""}

    def test_compact_list(self):
        """测试压缩列表"""
        result = compact_list([1, None, "", 2, None, 3])
        assert result == [1, 2, 3]


class TestDebugUtils:
    """调试工具测试"""

    def test_truncate_for_log_short_text(self):
        """测试截断短文本"""
        text = "short text"
        result = truncate_for_log(text, 100)
        assert result == text

    def test_truncate_for_log_long_text(self):
        """测试截断长文本"""
        text = "a" * 300
        result = truncate_for_log(text, 100)
        assert len(result) < 150
        assert "..." in result
        assert "300 chars" in result

    def test_log_dict(self):
        """测试日志记录字典"""
        d = {"key1": "value1", "key2": "a" * 200}
        result = log_dict(d, max_value_length=50)
        assert "key1=" in result
        assert "key2=" in result
        assert "..." in result


class TestUtilitiesIntegration:
    """工具集成测试"""

    def test_parse_and_format_date_cycle(self):
        """测试日期解析和格式化循环"""
        original = "2024-06-15"
        parsed = parse_contract_date(original)
        formatted = format_date(parsed)
        assert formatted == original

    def test_parse_and_format_amount_cycle(self):
        """测试金额解析和格式化循环"""
        original = "5000元"
        parsed = parse_amount(original)
        formatted = format_amount(parsed)
        assert "5000" in formatted

    def test_validate_field_with_custom_rules(self):
        """测试使用自定义规则验证字段"""
        custom_rules = {
            "custom_field": lambda x: (len(x) > 5, "长度不足")
        }

        is_valid, error = validate_field_value(
            "custom_field",
            "123",
            rules=custom_rules
        )
        assert is_valid is False
        assert error == "长度不足"
