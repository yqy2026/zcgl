"""
模型工具函数单元测试

测试 src.utils.model_utils 模块的工具函数
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

from src.utils.model_utils import (
    batch_to_dict,
    calculate_percentage,
    format_currency,
    format_phone_number,
    generate_month_range,
    generate_uuid,
    model_to_dict,
    safe_divide,
    truncate_string,
    validate_date_range,
)


# ============================================================================
# Mock SQLAlchemy Model for testing
# ============================================================================
class MockColumn:
    """模拟 SQLAlchemy 列"""

    def __init__(self, key):
        self.key = key


class MockMapper:
    """模拟 SQLAlchemy Mapper"""

    def __init__(self, columns=None, relationships=None):
        self.columns = columns or []
        self.relationships = relationships or []


class MockModel:
    """模拟 SQLAlchemy 模型"""

    __tablename__ = "mock_model"

    def __init__(self, data: dict | None = None):
        if data:
            for key, value in data.items():
                setattr(self, key, value)


# Mock SQLAlchemy mapper configuration
class MockRelationship:
    """模拟 SQLAlchemy 关系"""

    def __init__(self, key, uselist=False):
        self.key = key
        self.uselist = uselist


# ============================================================================
# model_to_dict 测试
# ============================================================================
class TestModelToDict:
    """测试模型转字典"""

    @patch("src.utils.model_utils.class_mapper")
    def test_simple_model(self, mock_class_mapper):
        """测试简单模型转换"""
        # 设置 mock mapper
        mock_mapper = MockMapper(
            columns=[
                MockColumn("id"),
                MockColumn("name"),
                MockColumn("value"),
            ]
        )
        mock_class_mapper.return_value = mock_mapper

        model = MockModel({"id": 1, "name": "Test", "value": 100})
        result = model_to_dict(model)

        assert result == {"id": 1, "name": "Test", "value": 100}

    @patch("src.utils.model_utils.class_mapper")
    def test_model_with_datetime(self, mock_class_mapper):
        """测试包含 datetime 的模型"""
        now = datetime.now()
        mock_mapper = MockMapper(
            columns=[MockColumn("id"), MockColumn("created_at")]
        )
        mock_class_mapper.return_value = mock_mapper

        model = MockModel({"id": 1, "created_at": now})
        result = model_to_dict(model)

        assert result["id"] == 1
        assert result["created_at"] == now.isoformat()

    @patch("src.utils.model_utils.class_mapper")
    def test_model_with_date(self, mock_class_mapper):
        """测试包含 date 的模型"""
        today = date.today()
        mock_mapper = MockMapper(
            columns=[MockColumn("id"), MockColumn("start_date")]
        )
        mock_class_mapper.return_value = mock_mapper

        model = MockModel({"id": 1, "start_date": today})
        result = model_to_dict(model)

        assert result["id"] == 1
        assert result["start_date"] == today.isoformat()

    @patch("src.utils.model_utils.class_mapper")
    def test_model_with_decimal(self, mock_class_mapper):
        """测试包含 Decimal 的模型"""
        mock_mapper = MockMapper(
            columns=[MockColumn("id"), MockColumn("price")]
        )
        mock_class_mapper.return_value = mock_mapper

        model = MockModel({"id": 1, "price": Decimal("99.99")})
        result = model_to_dict(model)

        assert result["id"] == 1
        assert result["price"] == 99.99

    def test_none_model(self):
        """测试 None 模型"""
        result = model_to_dict(None)
        assert result is None

    @patch("src.utils.model_utils.class_mapper")
    def test_model_with_none_values(self, mock_class_mapper):
        """测试包含 None 值的模型"""
        mock_mapper = MockMapper(
            columns=[
                MockColumn("id"),
                MockColumn("name"),
                MockColumn("value"),
            ]
        )
        mock_class_mapper.return_value = mock_mapper

        model = MockModel({"id": 1, "name": None, "value": 0})
        result = model_to_dict(model)

        assert result == {"id": 1, "name": None, "value": 0}


# ============================================================================
# batch_to_dict 测试
# ============================================================================
class TestBatchToDict:
    """测试批量模型转字典"""

    def test_empty_list(self):
        """测试空列表"""
        result = batch_to_dict([])
        assert result == []

    @patch("src.utils.model_utils.class_mapper")
    def test_multiple_models(self, mock_class_mapper):
        """测试多个模型"""
        mock_mapper = MockMapper(
            columns=[MockColumn("id"), MockColumn("name")]
        )
        mock_class_mapper.return_value = mock_mapper

        model1 = MockModel({"id": 1, "name": "First"})
        model2 = MockModel({"id": 2, "name": "Second"})

        result = batch_to_dict([model1, model2])

        assert len(result) == 2
        assert result[0] == {"id": 1, "name": "First"}
        assert result[1] == {"id": 2, "name": "Second"}

    @patch("src.utils.model_utils.class_mapper")
    def test_filters_none_models(self, mock_class_mapper):
        """测试过滤 None 模型"""
        mock_mapper = MockMapper(
            columns=[MockColumn("id"), MockColumn("name")]
        )
        mock_class_mapper.return_value = mock_mapper

        model1 = MockModel({"id": 1, "name": "First"})

        result = batch_to_dict([model1, None])

        assert len(result) == 1
        assert result[0] == {"id": 1, "name": "First"}


# ============================================================================
# generate_uuid 测试
# ============================================================================
class TestGenerateUUID:
    """测试 UUID 生成"""

    def test_generates_valid_uuid(self):
        """测试生成有效的 UUID"""
        uuid_str = generate_uuid()

        # UUID 格式: 8-4-4-4-12
        assert len(uuid_str) == 36
        assert uuid_str.count("-") == 4

    def test_generates_unique_uuids(self):
        """测试生成唯一 UUID"""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()

        assert uuid1 != uuid2

    def test_uuid_format(self):
        """测试 UUID 格式"""
        uuid_str = generate_uuid()
        parts = uuid_str.split("-")

        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12


# ============================================================================
# format_currency 测试
# ============================================================================
class TestFormatCurrency:
    """测试金额格式化"""

    def test_normal_amount(self):
        """测试正常金额"""
        result = format_currency(Decimal("99.999"))
        assert result == 100.0

    def test_none_amount(self):
        """测试 None 金额"""
        result = format_currency(None)
        assert result == 0.0

    def test_custom_decimal_places(self):
        """测试自定义小数位数"""
        result = format_currency(Decimal("99.999"), decimal_places=3)
        assert result == 99.999

    def test_zero_amount(self):
        """测试零金额"""
        result = format_currency(Decimal("0"))
        assert result == 0.0

    def test_negative_amount(self):
        """测试负金额"""
        result = format_currency(Decimal("-50.5"))
        assert result == -50.5

    def test_rounding(self):
        """测试四舍五入"""
        result = format_currency(Decimal("99.995"), decimal_places=2)
        assert result == 100.0


# ============================================================================
# calculate_percentage 测试
# ============================================================================
class TestCalculatePercentage:
    """测试百分比计算"""

    def test_normal_percentage(self):
        """测试正常百分比"""
        result = calculate_percentage(Decimal("50"), Decimal("100"))
        assert result == 50.0

    def test_zero_total(self):
        """测试总值为零"""
        result = calculate_percentage(Decimal("50"), Decimal("0"))
        assert result == 0.0

    def test_zero_part(self):
        """测试部分值为零"""
        result = calculate_percentage(Decimal("0"), Decimal("100"))
        assert result == 0.0

    def test_both_zero(self):
        """测试两者都为零"""
        result = calculate_percentage(Decimal("0"), Decimal("0"))
        assert result == 0.0

    def test_over_100_percent(self):
        """测试超过100%"""
        result = calculate_percentage(Decimal("150"), Decimal("100"))
        assert result == 150.0

    def test_small_percentage(self):
        """测试小百分比"""
        result = calculate_percentage(Decimal("1"), Decimal("1000"))
        assert result == 0.1

    def test_rounding(self):
        """测试四舍五入"""
        # 1/3 = 33.333...%
        result = calculate_percentage(Decimal("1"), Decimal("3"))
        assert result == 33.33


# ============================================================================
# validate_date_range 测试
# ============================================================================
class TestValidateDateRange:
    """测试日期范围验证"""

    def test_valid_range(self):
        """测试有效范围"""
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)
        assert validate_date_range(start, end) is True

    def test_same_date(self):
        """测试相同日期"""
        day = date(2024, 6, 15)
        assert validate_date_range(day, day) is True

    def test_invalid_range(self):
        """测试无效范围（开始晚于结束）"""
        start = date(2024, 12, 31)
        end = date(2024, 1, 1)
        assert validate_date_range(start, end) is False


# ============================================================================
# generate_month_range 测试
# ============================================================================
class TestGenerateMonthRange:
    """测试月份范围生成"""

    def test_single_month(self):
        """测试单个月份"""
        result = generate_month_range("2024-01", "2024-01")
        assert result == ["2024-01"]

    def test_multiple_months_same_year(self):
        """测试同一年多个月份"""
        result = generate_month_range("2024-01", "2024-03")
        assert result == ["2024-01", "2024-02", "2024-03"]

    def test_cross_year(self):
        """测试跨年"""
        result = generate_month_range("2023-11", "2024-02")
        assert result == ["2023-11", "2023-12", "2024-01", "2024-02"]

    def test_full_year(self):
        """测试全年"""
        result = generate_month_range("2024-01", "2024-12")
        assert len(result) == 12
        assert result[0] == "2024-01"
        assert result[-1] == "2024-12"

    def test_invalid_format(self):
        """测试无效格式"""
        with pytest.raises(ValueError, match="无效的月份格式"):
            generate_month_range("2024/01", "2024-03")

    def test_reversed_range(self):
        """测试反转范围（开始晚于结束）"""
        result = generate_month_range("2024-06", "2024-03")
        assert result == []  # 或者可能返回空列表


# ============================================================================
# safe_divide 测试
# ============================================================================
class TestSafeDivideModelUtils:
    """测试安全除法"""

    def test_normal_division(self):
        """测试正常除法"""
        result = safe_divide(Decimal("10"), Decimal("2"))
        assert result == 5.0

    def test_divide_by_zero(self):
        """测试除以零"""
        result = safe_divide(Decimal("10"), Decimal("0"))
        assert result == 0.0

    def test_none_numerator(self):
        """测试分子为 None"""
        result = safe_divide(None, Decimal("10"))
        assert result == 0.0

    def test_none_denominator(self):
        """测试分母为 None"""
        result = safe_divide(Decimal("10"), None)
        assert result == 0.0

    def test_both_none(self):
        """测试两者都为 None"""
        result = safe_divide(None, None)
        assert result == 0.0

    def test_custom_default(self):
        """测试自定义默认值"""
        result = safe_divide(Decimal("10"), Decimal("0"), default=-1.0)
        assert result == -1.0

    def test_fractional_result(self):
        """测试小数结果"""
        result = safe_divide(Decimal("1"), Decimal("3"))
        assert abs(result - 0.33) < 0.01  # 允许小的误差


# ============================================================================
# format_phone_number 测试
# ============================================================================
class TestFormatPhoneNumber:
    """测试电话号码格式化"""

    def test_mobile_11_digits(self):
        """测试11位手机号"""
        result = format_phone_number("13800138000")
        assert result == "138-0013-8000"

    def test_landline_8_digits(self):
        """测试8位座机号"""
        result = format_phone_number("12345678")
        assert result == "1234-5678"

    def test_already_formatted(self):
        """测试已格式化的号码"""
        result = format_phone_number("138-0013-8000")
        assert result == "138-0013-8000"

    def test_with_special_chars(self):
        """测试包含特殊字符"""
        # Extracts digits: 13800138000123 (15 digits) - not 11 or 8, so returns original
        result = format_phone_number("138-0013-8000 ext.123")
        assert result == "138-0013-8000 ext.123"

    def test_empty_string(self):
        """测试空字符串"""
        result = format_phone_number("")
        assert result == ""

    def test_none_input(self):
        """测试 None 输入"""
        result = format_phone_number(None)
        assert result == ""

    def test_short_number(self):
        """测试短号码（不标准格式）"""
        result = format_phone_number("12345")
        assert result == "12345"  # 返回原值

    def test_long_number(self):
        """测试长号码（不标准格式）"""
        result = format_phone_number("12345678901234")
        assert result == "12345678901234"  # 返回原值


# ============================================================================
# truncate_string 测试
# ============================================================================
class TestTruncateString:
    """测试字符串截断"""

    def test_short_string(self):
        """测试短字符串（不需要截断）"""
        result = truncate_string("short", max_length=100)
        assert result == "short"

    def test_exact_length(self):
        """测试正好等于最大长度"""
        result = truncate_string("a" * 50, max_length=50)
        assert result == "a" * 50

    def test_long_string(self):
        """测试需要截断的长字符串"""
        result = truncate_string("a" * 100, max_length=50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_truncation_in_middle(self):
        """测试截断发生在中间"""
        result = truncate_string("a" * 60, max_length=20)
        assert result == "a" * 17 + "..."
        assert len(result) == 20

    def test_empty_string(self):
        """测试空字符串"""
        result = truncate_string("")
        assert result == ""

    def test_none_input(self):
        """测试 None 输入"""
        result = truncate_string(None)
        assert result == ""

    def test_custom_max_length(self):
        """测试自定义最大长度"""
        result = truncate_string("hello world", max_length=8)
        assert result == "hello..."

    def test_very_short_max_length(self):
        """测试非常短的最大长度"""
        result = truncate_string("hello", max_length=4)
        # max_length=4, so we take text[:1] + "..." = "h..."
        assert result == "h..."
