"""
Unit tests for core.validators
"""

from datetime import datetime

import pytest

from src.core.validators import (
    AssetValidator,
    BaseValidator,
    DataCleaner,
    OrganizationValidator,
    RentContractValidator,
    UserValidator,
    ValidationMixin,
    validate_field_length,
    validate_field_values,
    validate_required_fields,
)
from src.exceptions import BusinessLogicError


class TestBaseValidator:
    def test_validate_email(self):
        assert BaseValidator.validate_email("user@example.com") is True
        assert BaseValidator.validate_email("bad-email") is False

    def test_validate_phone(self):
        assert BaseValidator.validate_phone("13812345678") is True
        assert BaseValidator.validate_phone("12345678901") is False

    def test_validate_id_card(self):
        assert BaseValidator.validate_id_card("11010519491231002X") is True
        assert BaseValidator.validate_id_card("123") is False

    def test_validate_url(self):
        assert BaseValidator.validate_url("https://example.com/path?x=1#y") is True
        assert BaseValidator.validate_url("not-a-url") is False

    def test_validate_ip_address(self):
        assert BaseValidator.validate_ip_address("192.168.1.1") is True
        assert BaseValidator.validate_ip_address("999.1.1.1") is False

    def test_validate_date_range(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 2)
        assert BaseValidator.validate_date_range(start, end) is True
        assert BaseValidator.validate_date_range(end, start) is False

    def test_validate_numbers_and_percentage(self):
        assert BaseValidator.validate_positive_number(1) is True
        assert BaseValidator.validate_positive_number(0) is False
        assert BaseValidator.validate_non_negative_number(0) is True
        assert BaseValidator.validate_non_negative_number(-1) is False
        assert BaseValidator.validate_percentage(0) is True
        assert BaseValidator.validate_percentage(100) is True
        assert BaseValidator.validate_percentage(101) is False

    def test_validate_length_and_regex(self):
        assert BaseValidator.validate_length("abc", 1, 3) is True
        assert BaseValidator.validate_length("", 1, 3) is False
        assert BaseValidator.validate_regex("abc123", r"^[a-z0-9]+$") is True


class TestAssetValidator:
    def test_validate_asset_data_required_fields(self):
        errors = AssetValidator.validate_asset_data({})
        assert "缺少必填字段" in " ".join(errors)

    def test_validate_asset_data_field_rules(self):
        data = {
            "property_name": "",
            "property_address": "x",
            "ownership_status": "owned",
            "property_nature": "commercial",
            "building_area": -1,
            "construction_year": 1899,
        }
        errors = AssetValidator.validate_asset_data(data)
        error_text = " ".join(errors)
        assert "物业名称长度" in error_text
        assert "物业地址长度" in error_text
        assert "建筑面积必须为正数" in error_text
        assert "建成年份应在" in error_text


class TestUserValidator:
    def test_validate_user_data(self):
        data = {
            "username": "ab",
            "email": "bad-email",
            "phone": "123",
        }
        errors = UserValidator.validate_user_data(data)
        error_text = " ".join(errors)
        assert "用户名长度" in error_text
        assert "邮箱格式" in error_text
        assert "手机号格式" in error_text


class TestOrganizationValidator:
    def test_validate_organization_data(self):
        data = {"name": "", "code": "abc"}
        errors = OrganizationValidator.validate_organization_data(data)
        error_text = " ".join(errors)
        assert "组织名称长度" in error_text
        assert "组织代码只能包含大写字母" in error_text


class TestRentContractValidator:
    def test_validate_contract_data(self):
        data = {
            "monthly_rent": -1,
            "security_deposit": -1,
            "lease_start_date": datetime(2024, 1, 2),
            "lease_end_date": datetime(2024, 1, 1),
        }
        errors = RentContractValidator.validate_contract_data(data)
        error_text = " ".join(errors)
        assert "月租金必须为正数" in error_text
        assert "保证金不能为负数" in error_text
        assert "租赁开始日期不能晚于结束日期" in error_text


class TestValidationMixin:
    def test_validate_and_raise(self):
        class Sample(ValidationMixin):
            pass

        with pytest.raises(BusinessLogicError):
            Sample().validate_and_raise(["error"], context="测试")


class TestDataCleaner:
    def test_clean_phone(self):
        assert DataCleaner.clean_phone("138-1234-5678") == "13812345678"

    def test_clean_whitespace(self):
        assert DataCleaner.clean_whitespace("  hello   world ") == "hello world"

    def test_clean_numeric_string(self):
        assert DataCleaner.clean_numeric_string("$1,234.50") == "1234.50"

    def test_standardize_boolean(self):
        assert DataCleaner.standardize_boolean(True) is True
        assert DataCleaner.standardize_boolean("yes") is True
        assert DataCleaner.standardize_boolean("0") is False
        assert DataCleaner.standardize_boolean(1) is True
        assert DataCleaner.standardize_boolean(0) is False

    def test_standardize_datetime(self):
        value = DataCleaner.standardize_datetime("2024-01-02 10:20:30")
        assert value == datetime(2024, 1, 2, 10, 20, 30)
        value2 = DataCleaner.standardize_datetime("2024/01/02")
        assert value2 == datetime(2024, 1, 2)
        assert DataCleaner.standardize_datetime("not-a-date") is None


class TestValidationHelpers:
    def test_validate_required_fields(self):
        errors = validate_required_fields({"name": "", "age": None}, ["name", "age"])
        assert len(errors) == 2

    def test_validate_field_length(self):
        errors = validate_field_length(
            {"name": "a", "code": "toolong"},
            {"name": {"min": 2, "max": 10}, "code": {"max": 3}},
        )
        assert "name长度不能少于" in " ".join(errors)
        assert "code长度不能超过" in " ".join(errors)

    def test_validate_field_values(self):
        errors = validate_field_values({"status": "bad"}, {"status": ["ok", "good"]})
        assert "status的值应为以下之一" in " ".join(errors)
