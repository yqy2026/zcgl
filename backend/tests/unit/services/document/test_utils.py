"""
测试 PDF 处理公共工具模块
"""

from datetime import datetime

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


# ============================================================================
# Test Date Utilities
# ============================================================================
class TestParseContractDate:
    """测试日期解析"""

    def test_parse_iso_date(self):
        """测试解析ISO格式日期"""
        result = parse_contract_date("2024-01-15")
        assert result == datetime(2024, 1, 15)

    def test_parse_slash_date(self):
        """测试解析斜杠分隔日期"""
        result = parse_contract_date("2024/01/15")
        assert result == datetime(2024, 1, 15)

    def test_parse_dot_date(self):
        """测试解析点分隔日期"""
        result = parse_contract_date("2024.01.15")
        assert result == datetime(2024, 1, 15)

    def test_parse_chinese_date(self):
        """测试解析中文日期"""
        result = parse_contract_date("2024年01月15日")
        assert result == datetime(2024, 1, 15)

    def test_parse_compact_date(self):
        """测试解析紧凑日期"""
        result = parse_contract_date("20240115")
        assert result == datetime(2024, 1, 15)

    def test_parse_reversed_date(self):
        """测试解析反向日期"""
        result = parse_contract_date("15/01/2024")
        assert result == datetime(2024, 1, 15)

    def test_parse_with_prefix(self):
        """测试带前缀的日期"""
        result = parse_contract_date("日期2024-01-15")
        assert result == datetime(2024, 1, 15)

    def test_parse_datetime_object(self):
        """测试直接传入datetime对象"""
        dt = datetime(2024, 5, 20)
        result = parse_contract_date(dt)
        assert result == dt

    def test_parse_none(self):
        """测试解析None"""
        result = parse_contract_date(None)
        assert result is None

    def test_parse_empty_string(self):
        """测试解析空字符串"""
        result = parse_contract_date("")
        assert result is None

    def test_parse_invalid_date(self):
        """测试解析无效日期"""
        result = parse_contract_date("invalid-date")
        assert result is None


class TestFormatDate:
    """测试日期格式化"""

    def test_format_date_basic(self):
        """测试基本日期格式化"""
        date = datetime(2024, 1, 15)
        result = format_date(date)
        assert result == "2024-01-15"

    def test_format_date_custom_format(self):
        """测试自定义日期格式"""
        date = datetime(2024, 1, 15)
        result = format_date(date, "%Y/%m/%d")
        assert result == "2024/01/15"

    def test_format_date_none(self):
        """测试格式化None日期"""
        result = format_date(None)
        assert result == ""


class TestValidateDateRange:
    """测试日期范围验证"""

    def test_valid_date_range(self):
        """测试有效日期范围"""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        result = validate_date_range(start, end)
        assert result is True

    def test_invalid_date_range(self):
        """测试无效日期范围"""
        start = datetime(2024, 12, 31)
        end = datetime(2024, 1, 1)
        result = validate_date_range(start, end)
        assert result is False

    def test_equal_dates(self):
        """测试相同日期"""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 1)
        result = validate_date_range(start, end)
        assert result is True

    def test_none_start_date(self):
        """测试None开始日期"""
        result = validate_date_range(None, datetime(2024, 12, 31))
        assert result is True

    def test_none_end_date(self):
        """测试None结束日期"""
        result = validate_date_range(datetime(2024, 1, 1), None)
        assert result is True

    def test_both_none(self):
        """测试两个日期都为None"""
        result = validate_date_range(None, None)
        assert result is True


# ============================================================================
# Test Amount Utilities
# ============================================================================
class TestParseAmount:
    """测试金额解析"""

    def test_parse_simple_amount(self):
        """测试解析简单金额"""
        result = parse_amount("5000元")
        assert result == 5000.0

    def test_parse_yuan_symbol(self):
        """测试解析带人民币符号的金额"""
        result = parse_amount("￥5000")
        assert result == 5000.0

    def test_parse_wan_unit(self):
        """测试解析万元单位"""
        result = parse_amount("5.5万")
        assert result == 55000.0

    def test_parse_qian_unit(self):
        """测试解析千元单位"""
        result = parse_amount("5千")
        assert result == 5000.0

    def test_parse_bai_unit(self):
        """测试解析百元单位"""
        result = parse_amount("5百")
        assert result == 500.0

    def test_parse_with_commas(self):
        """测试解析带逗号的金额"""
        result = parse_amount("5,000.50元")
        assert result == 5000.5

    def test_parse_float(self):
        """测试解析浮点数金额"""
        result = parse_amount(5000.50)
        assert result == 5000.50

    def test_parse_int(self):
        """测试解析整数金额"""
        result = parse_amount(5000)
        assert result == 5000.0

    def test_parse_none(self):
        """测试解析None"""
        result = parse_amount(None)
        assert result is None

    def test_parse_empty_string(self):
        """测试解析空字符串"""
        result = parse_amount("")
        assert result is None

    def test_parse_invalid_amount(self):
        """测试解析无效金额"""
        result = parse_amount("invalid")
        assert result is None


class TestFormatAmount:
    """测试金额格式化"""

    def test_format_amount_basic(self):
        """测试基本金额格式化"""
        result = format_amount(5000.50)
        assert result == "5000.50元"

    def test_format_amount_no_decimals(self):
        """测试无小数金额格式化"""
        result = format_amount(5000.0)
        assert result == "5000元"

    def test_format_amount_custom_unit(self):
        """测试自定义单位格式化"""
        result = format_amount(5000, "万")
        assert result == "5000万"

    def test_format_amount_none(self):
        """测试格式化None金额"""
        result = format_amount(None)
        assert result == ""


# ============================================================================
# Test Field Validation
# ============================================================================
class TestValidateFieldValue:
    """测试字段值验证"""

    def test_validate_contract_number_valid(self):
        """测试有效合同编号"""
        is_valid, error = validate_field_value("contract_number", "HT202401001")
        assert is_valid is True
        assert error is None

    def test_validate_contract_number_invalid(self):
        """测试无效合同编号"""
        is_valid, error = validate_field_value("contract_number", "AB")
        assert is_valid is False
        assert error is not None

    def test_validate_party_name_valid(self):
        """测试有效当事人名称"""
        is_valid, error = validate_field_value("party_a", "张三")
        assert is_valid is True
        assert error is None

    def test_validate_party_name_too_short(self):
        """测试过短当事人名称"""
        is_valid, error = validate_field_value("party_a", "张")
        assert is_valid is False

    def test_validate_address_valid(self):
        """测试有效地址"""
        is_valid, error = validate_field_value("property_address", "北京市朝阳区XXX号")
        assert is_valid is True
        assert error is None

    def test_validate_address_too_short(self):
        """测试过短地址"""
        is_valid, error = validate_field_value("property_address", "北京")
        assert is_valid is False

    def test_validate_id_number_valid(self):
        """测试有效身份证号"""
        is_valid, error = validate_field_value("id_number", "110101199001011234")
        assert is_valid is True
        assert error is None

    def test_validate_id_number_invalid_length(self):
        """测试无效长度身份证号"""
        is_valid, error = validate_field_value("id_number", "12345")
        assert is_valid is False

    def test_validate_phone_valid(self):
        """测试有效手机号"""
        is_valid, error = validate_field_value("phone", "13800138000")
        assert is_valid is True
        assert error is None

    def test_validate_phone_invalid(self):
        """测试无效手机号"""
        is_valid, error = validate_field_value("phone", "12345")
        assert is_valid is False

    def test_validate_rent_amount_valid(self):
        """测试有效租金金额"""
        is_valid, error = validate_field_value("rent_amount", "5000元")
        assert is_valid is True
        assert error is None

    def test_validate_rent_amount_negative(self):
        """测试负数租金"""
        is_valid, error = validate_field_value("rent_amount", "-1000")
        assert is_valid is False

    def test_validate_unknown_field(self):
        """测试未知字段"""
        is_valid, error = validate_field_value("unknown_field", "any_value")
        assert is_valid is True  # 未知字段默认通过验证


# ============================================================================
# Test JSON Utilities
# ============================================================================
class TestSafeParseJson:
    """测试JSON解析"""

    def test_parse_valid_json(self):
        """测试解析有效JSON"""
        result = safe_parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_invalid_json(self):
        """测试解析无效JSON"""
        result = safe_parse_json('not a json')
        assert result is None

    def test_parse_empty_string(self):
        """测试解析空字符串"""
        result = safe_parse_json("")
        assert result is None

    def test_parse_none(self):
        """测试解析None"""
        result = safe_parse_json(None)
        assert result is None


class TestExtractJsonFromResponse:
    """测试从响应中提取JSON"""

    def test_extract_json_from_markdown(self):
        """测试从markdown中提取JSON"""
        response = '```json\n{"key": "value"}\n```'
        result = extract_json_from_response(response)
        assert result == {"key": "value"}

    def test_extract_json_from_text(self):
        """测试从文本中提取JSON"""
        response = 'Some text {"key": "value"} more text'
        result = extract_json_from_response(response)
        assert result == {"key": "value"}

    def test_extract_no_json(self):
        """测试没有JSON的响应"""
        response = 'This is just plain text'
        result = extract_json_from_response(response)
        assert result is None

    def test_extract_invalid_json(self):
        """测试无效JSON"""
        response = '{"incomplete": '
        result = extract_json_from_response(response)
        assert result is None


# ============================================================================
# Test Text Utilities
# ============================================================================
class TestCleanText:
    """测试文本清理"""

    def test_clean_text_basic(self):
        """测试基本文本清理"""
        result = clean_text("  Hello   World  ")
        assert result == "Hello World"

    def test_clean_text_newlines(self):
        """测试清理换行符"""
        result = clean_text("Line1\n\nLine2")
        assert result == "Line1 Line2"

    def test_clean_text_none(self):
        """测试清理None"""
        result = clean_text(None)
        assert result == ""

    def test_clean_text_keep_extra_spaces(self):
        """测试保留额外空格"""
        result = clean_text("  Hello   World  ", remove_extra_spaces=False)
        assert result == "Hello   World"


class TestNormalizeWhitespace:
    """测试空白字符标准化"""

    def test_normalize_spaces(self):
        """测试空格标准化"""
        result = normalize_whitespace("Hello    World")
        assert result == "Hello World"

    def test_normalize_tabs(self):
        """测试制表符标准化"""
        result = normalize_whitespace("Hello\t\tWorld")
        assert result == "Hello World"

    def test_normalize_mixed(self):
        """测试混合空白字符"""
        result = normalize_whitespace("Hello \t \n World")
        assert result == "Hello World"


# ============================================================================
# Test Type Conversion Utilities
# ============================================================================
class TestToBool:
    """测试布尔值转换"""

    def test_to_bool_from_true(self):
        """测试从True转换"""
        assert to_bool(True) is True

    def test_to_bool_from_false(self):
        """测试从False转换"""
        assert to_bool(False) is False

    def test_to_bool_from_string_true(self):
        """测试从字符串'true'转换"""
        assert to_bool("true") is True

    def test_to_bool_from_string_false(self):
        """测试从字符串'false'转换"""
        assert to_bool("false") is False

    def test_to_bool_from_yes(self):
        """测试从'yes'转换"""
        assert to_bool("yes") is True

    def test_to_bool_from_no(self):
        """测试从'no'转换"""
        assert to_bool("no") is False

    def test_to_bool_from_int(self):
        """测试从整数转换"""
        assert to_bool(1) is True
        assert to_bool(0) is False

    def test_to_bool_default_true(self):
        """测试未知值返回False"""
        assert to_bool("random") is False

    def test_to_bool_default_false(self):
        """测试None值返回False"""
        assert to_bool(None) is False


class TestToInt:
    """测试整数转换"""

    def test_to_int_from_int(self):
        """测试从整数转换"""
        assert to_int(42) == 42

    def test_to_int_from_float(self):
        """测试从浮点数转换"""
        assert to_int(42.9) == 42

    def test_to_int_from_string(self):
        """测试从字符串转换"""
        assert to_int("42") == 42

    def test_to_int_from_invalid_string(self):
        """测试从无效字符串转换"""
        assert to_int("invalid", default=0) == 0

    def test_to_int_with_custom_default(self):
        """测试自定义默认值"""
        assert to_int(None, default=-1) == -1


class TestToFloat:
    """测试浮点数转换"""

    def test_to_float_from_int(self):
        """测试从整数转换"""
        assert to_float(42) == 42.0

    def test_to_float_from_float(self):
        """测试从浮点数转换"""
        assert to_float(42.5) == 42.5

    def test_to_float_from_string(self):
        """测试从字符串转换"""
        assert to_float("42.5") == 42.5

    def test_to_float_from_invalid_string(self):
        """测试从无效字符串转换"""
        assert to_float("invalid", default=0.0) == 0.0

    def test_to_float_with_custom_default(self):
        """测试自定义默认值"""
        assert to_float(None, default=-1.0) == -1.0


# ============================================================================
# Test Data Utilities
# ============================================================================
class TestMergeDicts:
    """测试字典合并"""

    def test_merge_two_dicts(self):
        """测试合并两个字典"""
        result = merge_dicts({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_merge_overlapping_keys(self):
        """测试合并重叠键字典"""
        result = merge_dicts({"a": 1}, {"a": 2, "b": 3})
        assert result == {"a": 2, "b": 3}

    def test_merge_three_dicts(self):
        """测试合并三个字典"""
        result = merge_dicts({"a": 1}, {"b": 2}, {"c": 3})
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_merge_empty_dicts(self):
        """测试合并空字典"""
        result = merge_dicts({}, {})
        assert result == {}


class TestFilterNoneValues:
    """测试过滤None值"""

    def test_filter_none_values_basic(self):
        """测试基本None值过滤"""
        result = filter_none_values({"a": 1, "b": None, "c": 3})
        assert result == {"a": 1, "c": 3}

    def test_filter_none_values_all_none(self):
        """测试全部为None"""
        result = filter_none_values({"a": None, "b": None})
        assert result == {}

    def test_filter_none_values_empty_dict(self):
        """测试空字典"""
        result = filter_none_values({})
        assert result == {}


class TestCompactList:
    """测试列表压缩"""

    def test_compact_list_basic(self):
        """测试基本列表压缩"""
        result = compact_list([1, None, 2, None, 3])
        assert result == [1, 2, 3]

    def test_compact_list_all_none(self):
        """测试全部为None的列表"""
        result = compact_list([None, None, None])
        assert result == []

    def test_compact_list_empty(self):
        """测试空列表"""
        result = compact_list([])
        assert result == []


class TestTruncateForLog:
    """测试日志截断"""

    def test_truncate_short_text(self):
        """测试短文本截断"""
        text = "Short text"
        result = truncate_for_log(text, max_length=100)
        assert result == "Short text"

    def test_truncate_long_text(self):
        """测试长文本截断"""
        text = "A" * 300
        result = truncate_for_log(text, max_length=100)
        assert len(result) == 121  # 100 + "... (300 chars total)"
        assert "(300 chars total)" in result

    def test_truncate_custom_length(self):
        """测试自定义截断长度"""
        text = "A" * 50
        result = truncate_for_log(text, max_length=20)
        assert len(result) == 40  # 20 + "... (50 chars total)"
        assert "(50 chars total)" in result


class TestLogDict:
    """测试字典日志"""

    def test_log_dict_basic(self):
        """测试基本字典日志"""
        result = log_dict({"a": 1, "b": 2})
        assert "a" in result
        assert "b" in result

    def test_log_dict_truncate_long_values(self):
        """测试截断长值"""
        result = log_dict({"key": "A" * 200}, max_value_length=50)
        assert "..." in result

    def test_log_dict_empty(self):
        """测试空字典日志"""
        result = log_dict({})
        assert result == "{}"


# ============================================================================
# Test Summary
# ============================================================================
"""
总计：60+个测试

测试分类：
1. TestParseContractDate: 11个测试
2. TestFormatDate: 3个测试
3. TestValidateDateRange: 7个测试
4. TestParseAmount: 11个测试
5. TestFormatAmount: 4个测试
6. TestValidateFieldValue: 14个测试
7. TestSafeParseJson: 4个测试
8. TestExtractJsonFromResponse: 4个测试
9. TestCleanText: 4个测试
10. TestNormalizeWhitespace: 3个测试
11. TestToBool: 9个测试
12. TestToInt: 5个测试
13. TestToFloat: 5个测试
14. TestMergeDicts: 4个测试
15. TestFilterNoneValues: 3个测试
16. TestCompactList: 3个测试
17. TestTruncateForLog: 3个测试
18. TestLogDict: 3个测试

覆盖范围：
✓ 日期解析（多种格式、前缀、None处理）
✓ 金额解析（中文单位、符号、小数）
✓ 字段验证（合同编号、当事人、地址、身份证、手机号、租金）
✓ JSON解析和提取
✓ 文本清理和标准化
✓ 类型转换（布尔、整数、浮点数）
✓ 数据操作（字典合并、过滤、列表压缩）
✓ 日志工具（截断、格式化）

预期覆盖率：90%+
"""
