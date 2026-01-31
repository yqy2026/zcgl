"""
产权证验证器测试

Tests for Property Certificate Validator
"""

from datetime import UTC, datetime

import pytest

from src.core.exception_handler import BusinessValidationError
from src.services.property_certificate.validator import PropertyCertificateValidator


@pytest.fixture
def validator():
    """验证器实例"""
    return PropertyCertificateValidator()


class TestPropertyCertificateValidator:
    """测试产权证验证器"""

    def test_validate_certificate_number_valid(self, validator):
        """测试有效的产权证号"""
        # 18位产权证号
        result = validator.validate_certificate_number("202012345678901234")
        assert result is True

    def test_validate_certificate_number_invalid_length(self, validator):
        """测试无效长度的产权证号"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_certificate_number("12345")  # 太短
        assert "certificate_number" in exc_info.value.field_errors

        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_certificate_number("20201234567890123456789")  # 太长
        assert "certificate_number" in exc_info.value.field_errors

    def test_validate_certificate_number_empty(self, validator):
        """测试空产权证号"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_certificate_number("")
        assert "certificate_number" in exc_info.value.field_errors

        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_certificate_number(None)
        assert "certificate_number" in exc_info.value.field_errors

    def test_validate_area_positive(self, validator):
        """测试有效面积"""
        result = validator.validate_area(100.0)
        assert result is True

    def test_validate_area_zero(self, validator):
        """测试零面积"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_area(0.0)
        assert "area" in exc_info.value.field_errors

    def test_validate_area_negative(self, validator):
        """测试负面积"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_area(-100.0)
        assert "area" in exc_info.value.field_errors

    def test_validate_area_unreasonably_large(self, validator):
        """测试不合理的大面积"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_area(999999999.0)
        assert "area" in exc_info.value.field_errors

    def test_validate_issue_date_future(self, validator):
        """测试未来发证日期"""
        future_date = datetime(2030, 1, 1)
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_issue_date(future_date)
        assert "issue_date" in exc_info.value.field_errors

    def test_validate_issue_date_past(self, validator):
        """测试过去发证日期"""
        past_date = datetime(2020, 1, 1)
        result = validator.validate_issue_date(past_date)
        assert result is True

    def test_validate_issue_date_today(self, validator):
        """测试今天发证日期"""
        today = datetime.now(UTC)
        result = validator.validate_issue_date(today)
        assert result is True

    def test_validate_expiry_date_after_issue(self, validator):
        """测试到期日期晚于发证日期"""
        issue_date = datetime(2020, 1, 1)
        expiry_date = datetime(2030, 1, 1)
        result = validator.validate_expiry_date(expiry_date, issue_date)
        assert result is True

    def test_validate_expiry_date_before_issue(self, validator):
        """测试到期日期早于发证日期"""
        issue_date = datetime(2020, 1, 1)
        expiry_date = datetime(2010, 1, 1)
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_expiry_date(expiry_date, issue_date)
        assert "expiry_date" in exc_info.value.field_errors

    def test_validate_expiry_date_same_as_issue(self, validator):
        """测试到期日期等于发证日期"""
        issue_date = datetime(2020, 1, 1)
        expiry_date = datetime(2020, 1, 1)
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_expiry_date(expiry_date, issue_date)
        assert "expiry_date" in exc_info.value.field_errors

    def test_validate_property_name_empty(self, validator):
        """测试空房产名称"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_property_name("")
        assert "property_name" in exc_info.value.field_errors

        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_property_name(None)
        assert "property_name" in exc_info.value.field_errors

    def test_validate_property_name_valid(self, validator):
        """测试有效房产名称"""
        result = validator.validate_property_name("测试房产名称")
        assert result is True

    def test_validate_property_name_too_short(self, validator):
        """测试过短的房产名称"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_property_name("ab")
        assert "property_name" in exc_info.value.field_errors

    def test_validate_address_format(self, validator):
        """测试地址格式"""
        # 有效地址
        result = validator.validate_address("北京市朝阳区测试街道123号")
        assert result is True

    def test_validate_address_empty(self, validator):
        """测试空地址"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_address("")
        assert "address" in exc_info.value.field_errors

    def test_validate_certificate_data_complete(self, validator):
        """测试完整的产权证数据"""
        certificate_data = {
            "certificate_number": "202012345678901234",
            "property_name": "测试房产",
            "area": 100.0,
            "issue_date": datetime(2020, 1, 1),
            "expiry_date": datetime(2030, 1, 1),
            "address": "北京市朝阳区测试地址",
        }

        result = validator.validate_certificate_data(certificate_data)
        assert result is True

    def test_validate_certificate_data_missing_fields(self, validator):
        """测试缺少必填字段"""
        incomplete_data = {
            "certificate_number": "202012345678901234",
            # 缺少property_name
            "area": 100.0,
        }

        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_certificate_data(incomplete_data)
        assert "property_name" in exc_info.value.field_errors

    def test_validate_registration_number_format(self, validator):
        """测试注册号格式"""
        # 有效注册号
        result = validator.validate_registration_number("REG-2020-001234")
        assert result is True

    def test_validate_registration_number_invalid(self, validator):
        """测试无效注册号"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_registration_number("INVALID")
        assert "registration_number" in exc_info.value.field_errors

    def test_validate_owner_name_empty(self, validator):
        """测试空业主姓名"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_owner_name("")
        assert "owner_name" in exc_info.value.field_errors

    def test_validate_owner_name_valid(self, validator):
        """测试有效业主姓名"""
        result = validator.validate_owner_name("张三")
        assert result is True

    def test_validate_certificate_type_valid(self, validator):
        """测试有效产权证类型"""
        result = validator.validate_certificate_type("house")
        assert result is True

    def test_validate_certificate_type_invalid(self, validator):
        """测试无效产权证类型"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_certificate_type("invalid_type")
        assert "certificate_type" in exc_info.value.field_errors

    def test_validate_land_use_right_valid(self, validator):
        """测试有效土地使用权"""
        result = validator.validate_land_use_right("residential")
        assert result is True

    def test_validate_land_use_right_invalid(self, validator):
        """测试无效土地使用权"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_land_use_right("invalid")
        assert "land_use_right" in exc_info.value.field_errors

    def test_validate_land_term_positive(self, validator):
        """测试有效土地年限"""
        result = validator.validate_land_term(70)
        assert result is True

    def test_validate_land_term_negative(self, validator):
        """测试负土地年限"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_land_term(-10)
        assert "land_term" in exc_info.value.field_errors

    def test_validate_land_term_zero(self, validator):
        """测试零土地年限"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_land_term(0)
        assert "land_term" in exc_info.value.field_errors

    def test_validate_land_term_too_long(self, validator):
        """测试过长土地年限"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_land_term(1000)
        assert "land_term" in exc_info.value.field_errors

    def test_validate_certificate_copy_number(self, validator):
        """测试产权证份数"""
        result = validator.validate_certificate_copy_number(1)
        assert result is True

    def test_validate_certificate_copy_number_zero(self, validator):
        """测试零份数"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_certificate_copy_number(0)
        assert "certificate_copy_number" in exc_info.value.field_errors

    def test_validate_certificate_copy_number_negative(self, validator):
        """测试负份数"""
        with pytest.raises(BusinessValidationError) as exc_info:
            validator.validate_certificate_copy_number(-1)
        assert "certificate_copy_number" in exc_info.value.field_errors
