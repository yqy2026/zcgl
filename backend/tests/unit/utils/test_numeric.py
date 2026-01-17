"""
数值工具函数单元测试

测试 src.utils.numeric 模块的工具函数
"""

import pytest
from decimal import Decimal

from src.utils.numeric import (
    calculate_percentage,
    safe_divide,
    to_decimal,
    to_float,
)


# ============================================================================
# to_float 测试
# ============================================================================
class TestToFloat:
    """测试 to_float 函数"""

    def test_from_int(self):
        """测试从整数转换"""
        assert to_float(42) == 42.0

    def test_from_float(self):
        """测试从浮点数转换"""
        assert to_float(3.14) == 3.14

    def test_from_string(self):
        """测试从字符串转换"""
        assert to_float("123.45") == 123.45

    def test_from_decimal(self):
        """测试从 Decimal 转换"""
        assert to_float(Decimal("99.99")) == 99.99

    def test_from_none(self):
        """测试 None 返回 0.0"""
        assert to_float(None) == 0.0

    def test_from_invalid_string(self):
        """测试无效字符串返回 0.0"""
        assert to_float("not a number") == 0.0

    def test_from_empty_string(self):
        """测试空字符串返回 0.0"""
        assert to_float("") == 0.0

    def test_from_bool(self):
        """测试布尔值转换"""
        assert to_float(True) == 1.0
        assert to_float(False) == 0.0

    def test_negative_number(self):
        """测试负数"""
        assert to_float(-42.5) == -42.5

    def test_zero(self):
        """测试零"""
        assert to_float(0) == 0.0
        assert to_float(0.0) == 0.0

    def test_very_large_number(self):
        """测试大数字"""
        assert to_float(999999.99) == 999999.99

    def test_scientific_notation_string(self):
        """测试科学计数法字符串"""
        assert to_float("1.5e2") == 150.0


# ============================================================================
# to_decimal 测试
# ============================================================================
class TestToDecimal:
    """测试 to_decimal 函数"""

    def test_from_int(self):
        """测试从整数转换"""
        assert to_decimal(42) == Decimal("42")

    def test_from_float(self):
        """测试从浮点数转换"""
        result = to_decimal(3.14)
        assert result == Decimal("3.14")

    def test_from_string(self):
        """测试从字符串转换"""
        assert to_decimal("123.45") == Decimal("123.45")

    def test_from_decimal(self):
        """测试从 Decimal 转换"""
        d = Decimal("99.99")
        assert to_decimal(d) == d

    def test_from_none(self):
        """测试 None 返回默认值"""
        assert to_decimal(None) == Decimal("0")

    def test_from_none_with_custom_default(self):
        """测试 None 返回自定义默认值"""
        default = Decimal("999")
        assert to_decimal(None, default=default) == default

    def test_from_invalid_string(self):
        """测试无效字符串返回默认值"""
        assert to_decimal("not a number") == Decimal("0")

    def test_from_invalid_string_with_custom_default(self):
        """测试无效字符串返回自定义默认值"""
        default = Decimal("100")
        assert to_decimal("invalid", default=default) == default

    def test_from_empty_string(self):
        """测试空字符串"""
        assert to_decimal("") == Decimal("0")

    def test_negative_number(self):
        """测试负数"""
        assert to_decimal(-42.5) == Decimal("-42.5")

    def test_zero(self):
        """测试零"""
        assert to_decimal(0) == Decimal("0")

    def test_precision_preservation(self):
        """测试精度保持"""
        assert to_decimal("0.1") + to_decimal("0.2") == Decimal("0.3")


# ============================================================================
# safe_divide 测试
# ============================================================================
class TestSafeDivide:
    """测试 safe_divide 函数"""

    def test_normal_division(self):
        """测试正常除法"""
        assert safe_divide(10, 2) == 5.0

    def test_divide_by_zero_returns_default(self):
        """测试除以零返回默认值"""
        assert safe_divide(10, 0) == 0.0

    def test_divide_by_zero_custom_default(self):
        """测试除以零返回自定义默认值"""
        assert safe_divide(10, 0, default=-1.0) == -1.0

    def test_with_decimals(self):
        """测试 Decimal 类型"""
        assert safe_divide(Decimal("10"), Decimal("2")) == 5.0

    def test_with_mixed_types(self):
        """测试混合类型"""
        assert safe_divide(10, Decimal("2")) == 5.0
        assert safe_divide(Decimal("10"), 2) == 5.0

    def test_negative_numbers(self):
        """测试负数"""
        assert safe_divide(-10, 2) == -5.0
        assert safe_divide(10, -2) == -5.0
        assert safe_divide(-10, -2) == 5.0

    def test_fractional_result(self):
        """测试小数结果"""
        result = safe_divide(1, 3)
        assert abs(result - 0.333333) < 0.001

    def test_zero_numerator(self):
        """测试分子为零"""
        assert safe_divide(0, 5) == 0.0

    def test_very_small_denominator(self):
        """测试很小的分母"""
        result = safe_divide(1, 0.001)
        assert abs(result - 1000.0) < 0.001

    def test_invalid_numerator(self):
        """测试无效分子返回默认值"""
        assert safe_divide("invalid", 2) == 0.0

    def test_invalid_denominator(self):
        """测试无效分母返回默认值"""
        assert safe_divide(10, "invalid") == 0.0


# ============================================================================
# calculate_percentage 测试
# ============================================================================
class TestCalculatePercentage:
    """测试 calculate_percentage 函数"""

    def test_normal_percentage(self):
        """测试正常百分比计算"""
        # 50 是 100 的 50%
        assert calculate_percentage(50, 100) == 50.0

    def test_zero_whole(self):
        """测试整体为零返回0"""
        assert calculate_percentage(50, 0) == 0.0

    def test_zero_part(self):
        """测试部分为零"""
        assert calculate_percentage(0, 100) == 0.0

    def test_both_zero(self):
        """测试两者都为零"""
        assert calculate_percentage(0, 0) == 0.0

    def test_full_percentage(self):
        """测试100%"""
        assert calculate_percentage(100, 100) == 100.0

    def test_over_100_percent(self):
        """测试超过100%"""
        # 150 是 100 的 150%
        assert calculate_percentage(150, 100) == 150.0

    def test_small_percentage(self):
        """测试小百分比"""
        # 1 是 1000 的 0.1%
        assert calculate_percentage(1, 1000) == 0.1

    def test_custom_decimal_places(self):
        """测试自定义小数位数"""
        # 1/3 = 33.333...
        assert calculate_percentage(1, 3, decimal_places=0) == 33.0
        assert calculate_percentage(1, 3, decimal_places=2) == 33.33
        assert calculate_percentage(1, 3, decimal_places=4) == 33.3333

    def test_rounding(self):
        """测试四舍五入"""
        # 2/3 = 66.666...%
        assert calculate_percentage(2, 3) == 66.67

    def test_with_decimals(self):
        """测试 Decimal 类型"""
        assert calculate_percentage(Decimal("50"), Decimal("100")) == 50.0

    def test_negative_part(self):
        """测试负的部分值"""
        assert calculate_percentage(-50, 100) == -50.0

    def test_negative_whole(self):
        """测试负的整体值"""
        assert calculate_percentage(50, -100) == -50.0

    def test_fractional_values(self):
        """测试小数值"""
        # 0.5 是 2.0 的 25%
        assert calculate_percentage(0.5, 2.0) == 25.0
