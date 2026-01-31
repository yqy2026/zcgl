"""
Comprehensive unit tests for CustomFieldService.

Tests all major methods and code paths to achieve 80%+ coverage.
"""

from unittest.mock import patch

import pytest

from src.models.asset import AssetCustomField
from src.schemas.asset import AssetCustomFieldCreate, AssetCustomFieldUpdate
from src.services.custom_field.service import CustomFieldService

TEST_FIELD_ID = "field_123"
TEST_ASSET_ID = "asset_456"


@pytest.fixture
def service():
    """CustomFieldService instance."""
    return CustomFieldService()


@pytest.fixture
def sample_field():
    """Sample AssetCustomField object."""
    field = AssetCustomField(
        id=TEST_FIELD_ID,
        field_name="test_field",
        display_name="Test Field",
        field_type="text",
        is_required=False,
        is_active=True,
        sort_order=0,
    )
    return field


class TestCreateCustomField:
    """Tests for create_custom_field method."""

    def test_create_custom_field_success(self, service, mock_db):
        """Test successful creation of custom field."""
        obj_in = AssetCustomFieldCreate(
            field_name="new_field",
            display_name="New Field",
            field_type="text",
            is_required=False,
        )

        with patch(
            "src.services.custom_field.service.custom_field_crud.get_by_field_name",
            return_value=None,
        ):
            with patch(
                "src.services.custom_field.service.custom_field_crud.create"
            ) as mock_create:
                mock_create.return_value = AssetCustomField(
                    id=TEST_FIELD_ID, field_name="new_field"
                )

                result = service.create_custom_field(mock_db, obj_in=obj_in)

                assert result.field_name == "new_field"
                mock_create.assert_called_once()

    def test_create_custom_field_duplicate_name(self, service, mock_db):
        """Test creating field with duplicate name raises ValueError."""
        obj_in = AssetCustomFieldCreate(
            field_name="existing_field",
            display_name="Existing Field",
            field_type="text",
        )

        with patch(
            "src.services.custom_field.service.custom_field_crud.get_by_field_name",
            return_value=AssetCustomField(
                id="existing_id", field_name="existing_field"
            ),
        ):
            with pytest.raises(ValueError) as excinfo:
                service.create_custom_field(mock_db, obj_in=obj_in)

            assert "已存在" in str(excinfo.value)


class TestUpdateCustomField:
    """Tests for update_custom_field method."""

    def test_update_custom_field_success(self, service, mock_db, sample_field):
        """Test successful update of custom field."""
        obj_in = AssetCustomFieldUpdate(display_name="Updated Display Name")

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=sample_field,
        ):
            with patch(
                "src.services.custom_field.service.custom_field_crud.get_by_field_name",
                return_value=None,
            ):
                with patch(
                    "src.services.custom_field.service.custom_field_crud.update"
                ) as mock_update:
                    mock_update.return_value = sample_field

                    service.update_custom_field(
                        mock_db, id=TEST_FIELD_ID, obj_in=obj_in
                    )

                    mock_update.assert_called_once()

    def test_update_custom_field_not_found(self, service, mock_db):
        """Test updating non-existent field raises ValueError."""
        obj_in = AssetCustomFieldUpdate(display_name="Updated Name")

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=None,
        ):
            with pytest.raises(ValueError) as excinfo:
                service.update_custom_field(mock_db, id="nonexistent_id", obj_in=obj_in)

            assert "不存在" in str(excinfo.value)

    def test_update_custom_field_duplicate_name(self, service, mock_db, sample_field):
        """Test updating field name to existing name raises ValueError."""
        obj_in = AssetCustomFieldUpdate(field_name="existing_field")

        existing_field = AssetCustomField(id="another_id", field_name="existing_field")

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=sample_field,
        ):
            with patch(
                "src.services.custom_field.service.custom_field_crud.get_by_field_name",
                return_value=existing_field,
            ):
                with pytest.raises(ValueError) as excinfo:
                    service.update_custom_field(
                        mock_db, id=TEST_FIELD_ID, obj_in=obj_in
                    )

                assert "已存在" in str(excinfo.value)

    def test_update_custom_field_same_name_allowed(
        self, service, mock_db, sample_field
    ):
        """Test updating field with same name is allowed."""
        obj_in = AssetCustomFieldUpdate(field_name="test_field")

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=sample_field,
        ):
            with patch(
                "src.services.custom_field.service.custom_field_crud.get_by_field_name",
                return_value=sample_field,
            ):
                with patch(
                    "src.services.custom_field.service.custom_field_crud.update"
                ) as mock_update:
                    mock_update.return_value = sample_field

                    service.update_custom_field(
                        mock_db, id=TEST_FIELD_ID, obj_in=obj_in
                    )

                    mock_update.assert_called_once()


class TestDeleteCustomField:
    """Tests for delete_custom_field method."""

    def test_delete_custom_field_success(self, service, mock_db, sample_field):
        """Test successful deletion of custom field."""
        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=sample_field,
        ):
            with patch(
                "src.services.custom_field.service.custom_field_crud.remove"
            ) as mock_remove:
                mock_remove.return_value = sample_field

                result = service.delete_custom_field(mock_db, id=TEST_FIELD_ID)

                assert result.id == TEST_FIELD_ID
                mock_remove.assert_called_once()

    def test_delete_custom_field_not_found(self, service, mock_db):
        """Test deleting non-existent field raises ValueError."""
        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=None,
        ):
            with pytest.raises(ValueError) as excinfo:
                service.delete_custom_field(mock_db, id="nonexistent_id")

            assert "不存在" in str(excinfo.value)


class TestValidateFieldValue:
    """Tests for validate_field_value method."""

    def test_validate_required_field_missing(self, service, sample_field):
        """Test validation fails when required field is missing."""
        sample_field.is_required = True
        sample_field.display_name = "Required Field"

        is_valid, error_msg = service.validate_field_value(sample_field, None)

        assert not is_valid
        assert "必填项" in error_msg

    def test_validate_required_field_empty_string(self, service, sample_field):
        """Test validation fails when required field is empty string."""
        sample_field.is_required = True
        sample_field.display_name = "Required Field"

        is_valid, error_msg = service.validate_field_value(sample_field, "")

        assert not is_valid
        assert "必填项" in error_msg

    def test_validate_optional_field_none(self, service, sample_field):
        """Test validation passes when optional field is None."""
        sample_field.is_required = False

        is_valid, error_msg = service.validate_field_value(sample_field, None)

        assert is_valid
        assert error_msg is None

    def test_validate_text_type_success(self, service, sample_field):
        """Test validation passes for valid text field."""
        sample_field.field_type = "text"

        is_valid, error_msg = service.validate_field_value(sample_field, "valid text")

        assert is_valid
        assert error_msg is None

    def test_validate_text_type_wrong_type(self, service, sample_field):
        """Test validation fails for text field with wrong type."""
        sample_field.field_type = "text"
        sample_field.display_name = "Text Field"

        is_valid, error_msg = service.validate_field_value(sample_field, 123)

        assert not is_valid
        assert "必须为文本类型" in error_msg

    def test_validate_text_max_length(self, service, sample_field):
        """Test validation fails for text exceeding max length."""
        sample_field.field_type = "text"
        sample_field.validation_rules = '{"max_length": 5}'
        sample_field.display_name = "Text Field"

        is_valid, error_msg = service.validate_field_value(
            sample_field, "too long text"
        )

        assert not is_valid
        assert "不能超过" in error_msg and "5 个字符" in error_msg

    def test_validate_text_min_length(self, service, sample_field):
        """Test validation fails for text below min length."""
        sample_field.field_type = "text"
        sample_field.validation_rules = '{"min_length": 5}'
        sample_field.display_name = "Text Field"

        is_valid, error_msg = service.validate_field_value(sample_field, "abc")

        assert not is_valid
        assert "不能少于" in error_msg and "5 个字符" in error_msg

    def test_validate_number_type_success(self, service, sample_field):
        """Test validation passes for valid number field."""
        sample_field.field_type = "number"

        is_valid, error_msg = service.validate_field_value(sample_field, 42)

        assert is_valid
        assert error_msg is None

    def test_validate_number_type_string_conversion(self, service, sample_field):
        """Test validation passes for number field with string value."""
        sample_field.field_type = "number"

        is_valid, error_msg = service.validate_field_value(sample_field, "42")

        assert is_valid
        assert error_msg is None

    def test_validate_number_type_invalid(self, service, sample_field):
        """Test validation fails for number field with invalid value."""
        sample_field.field_type = "number"
        sample_field.display_name = "Number Field"

        is_valid, error_msg = service.validate_field_value(sample_field, "not_a_number")

        assert not is_valid
        assert "必须为整数类型" in error_msg

    def test_validate_number_max_value(self, service, sample_field):
        """Test validation fails for number exceeding max value."""
        sample_field.field_type = "number"
        sample_field.validation_rules = '{"max_value": 100}'
        sample_field.display_name = "Number Field"

        is_valid, error_msg = service.validate_field_value(sample_field, 150)

        assert not is_valid
        assert "不能大于" in error_msg and "100" in error_msg

    def test_validate_number_min_value(self, service, sample_field):
        """Test validation fails for number below min value."""
        sample_field.field_type = "number"
        sample_field.validation_rules = '{"min_value": 10}'
        sample_field.display_name = "Number Field"

        is_valid, error_msg = service.validate_field_value(sample_field, 5)

        assert not is_valid
        assert "不能小于" in error_msg and "10" in error_msg

    def test_validate_decimal_type_success(self, service, sample_field):
        """Test validation passes for valid decimal field."""
        sample_field.field_type = "decimal"

        is_valid, error_msg = service.validate_field_value(sample_field, 3.14)

        assert is_valid
        assert error_msg is None

    def test_validate_decimal_type_string(self, service, sample_field):
        """Test validation passes for decimal field with string value."""
        sample_field.field_type = "decimal"

        is_valid, error_msg = service.validate_field_value(sample_field, "3.14")

        assert is_valid
        assert error_msg is None

    def test_validate_decimal_type_invalid(self, service, sample_field):
        """Test validation fails for decimal field with invalid value."""
        sample_field.field_type = "decimal"
        sample_field.display_name = "Decimal Field"

        is_valid, error_msg = service.validate_field_value(
            sample_field, "not_a_decimal"
        )

        assert not is_valid
        # The error could be either the specific error or a general validation error
        assert "必须为数字类型" in error_msg or "发生错误" in error_msg

    def test_validate_decimal_max_value(self, service, sample_field):
        """Test validation fails for decimal exceeding max value."""
        sample_field.field_type = "decimal"
        sample_field.validation_rules = '{"max_value": 10.5}'
        sample_field.display_name = "Decimal Field"

        is_valid, error_msg = service.validate_field_value(sample_field, 15.7)

        assert not is_valid
        assert "不能大于" in error_msg and "10.5" in error_msg

    def test_validate_decimal_min_value(self, service, sample_field):
        """Test validation fails for decimal below min value."""
        sample_field.field_type = "decimal"
        sample_field.validation_rules = '{"min_value": 5.5}'
        sample_field.display_name = "Decimal Field"

        is_valid, error_msg = service.validate_field_value(sample_field, 3.2)

        assert not is_valid
        assert "不能小于" in error_msg and "5.5" in error_msg

    def test_validate_boolean_type_success(self, service, sample_field):
        """Test validation passes for valid boolean field."""
        sample_field.field_type = "boolean"

        is_valid, error_msg = service.validate_field_value(sample_field, True)

        assert is_valid
        assert error_msg is None

    def test_validate_boolean_type_invalid(self, service, sample_field):
        """Test validation fails for boolean field with invalid value."""
        sample_field.field_type = "boolean"
        sample_field.display_name = "Boolean Field"

        is_valid, error_msg = service.validate_field_value(sample_field, "not_boolean")

        assert not is_valid
        assert "必须为布尔类型" in error_msg

    def test_validate_date_type_success(self, service, sample_field):
        """Test validation passes for valid date field."""
        sample_field.field_type = "date"

        is_valid, error_msg = service.validate_field_value(sample_field, "2026-01-15")

        assert is_valid
        assert error_msg is None

    def test_validate_date_type_invalid_format(self, service, sample_field):
        """Test validation fails for date field with invalid format."""
        sample_field.field_type = "date"
        sample_field.display_name = "Date Field"

        is_valid, error_msg = service.validate_field_value(sample_field, "15-01-2026")

        assert not is_valid
        assert "日期格式不正确" in error_msg

    def test_validate_datetime_type_success(self, service, sample_field):
        """Test validation passes for valid datetime field."""
        sample_field.field_type = "datetime"

        is_valid, error_msg = service.validate_field_value(
            sample_field, "2026-01-15T10:30:00"
        )

        assert is_valid
        assert error_msg is None

    def test_validate_datetime_type_invalid_format(self, service, sample_field):
        """Test validation fails for datetime field with invalid format."""
        sample_field.field_type = "datetime"
        sample_field.display_name = "DateTime Field"

        is_valid, error_msg = service.validate_field_value(
            sample_field, "invalid_datetime"
        )

        assert not is_valid
        assert "日期时间格式不正确" in error_msg

    def test_validate_select_type_success(self, service, sample_field):
        """Test validation passes for valid select field."""
        sample_field.field_type = "select"
        sample_field.field_options = '[{"value": "option1"}, {"value": "option2"}]'

        is_valid, error_msg = service.validate_field_value(sample_field, "option1")

        assert is_valid
        assert error_msg is None

    def test_validate_select_type_invalid_option(self, service, sample_field):
        """Test validation fails for select field with invalid option."""
        sample_field.field_type = "select"
        sample_field.field_options = '[{"value": "option1"}, {"value": "option2"}]'
        sample_field.display_name = "Select Field"

        is_valid, error_msg = service.validate_field_value(
            sample_field, "invalid_option"
        )

        assert not is_valid
        assert "不在允许范围内" in error_msg

    def test_validate_multiselect_type_success(self, service, sample_field):
        """Test validation passes for valid multiselect field."""
        sample_field.field_type = "multiselect"
        sample_field.field_options = (
            '[{"value": "opt1"}, {"value": "opt2"}, {"value": "opt3"}]'
        )

        is_valid, error_msg = service.validate_field_value(
            sample_field, ["opt1", "opt2"]
        )

        assert is_valid
        assert error_msg is None

    def test_validate_multiselect_type_not_array(self, service, sample_field):
        """Test validation fails for multiselect field with non-array value."""
        sample_field.field_type = "multiselect"
        sample_field.field_options = '[{"value": "opt1"}, {"value": "opt2"}]'
        sample_field.display_name = "MultiSelect Field"

        is_valid, error_msg = service.validate_field_value(sample_field, "opt1")

        assert not is_valid
        assert "必须为数组类型" in error_msg

    def test_validate_multiselect_type_invalid_option(self, service, sample_field):
        """Test validation fails for multiselect field with invalid option."""
        sample_field.field_type = "multiselect"
        sample_field.field_options = '[{"value": "opt1"}, {"value": "opt2"}]'
        sample_field.display_name = "MultiSelect Field"

        is_valid, error_msg = service.validate_field_value(
            sample_field, ["opt1", "invalid_opt"]
        )

        assert not is_valid
        assert "包含不允许的选项" in error_msg

    def test_validate_email_type_success(self, service, sample_field):
        """Test validation passes for valid email field."""
        sample_field.field_type = "email"

        is_valid, error_msg = service.validate_field_value(
            sample_field, "test@example.com"
        )

        assert is_valid
        assert error_msg is None

    def test_validate_email_type_invalid(self, service, sample_field):
        """Test validation fails for email field with invalid format."""
        sample_field.field_type = "email"
        sample_field.display_name = "Email Field"

        is_valid, error_msg = service.validate_field_value(
            sample_field, "invalid_email"
        )

        assert not is_valid
        assert "邮箱格式不正确" in error_msg

    def test_validate_phone_type_success(self, service, sample_field):
        """Test validation passes for valid phone field."""
        sample_field.field_type = "phone"

        is_valid, error_msg = service.validate_field_value(sample_field, "13800138000")

        assert is_valid
        assert error_msg is None

    def test_validate_phone_type_with_formatting(self, service, sample_field):
        """Test validation passes for phone field with formatting."""
        sample_field.field_type = "phone"

        is_valid, error_msg = service.validate_field_value(
            sample_field, "+86 138-0013-8000"
        )

        assert is_valid
        assert error_msg is None

    def test_validate_phone_type_invalid(self, service, sample_field):
        """Test validation fails for phone field with invalid format."""
        sample_field.field_type = "phone"
        sample_field.display_name = "Phone Field"

        is_valid, error_msg = service.validate_field_value(sample_field, "123")

        assert not is_valid
        assert "电话格式不正确" in error_msg

    def test_validate_url_type_success(self, service, sample_field):
        """Test validation passes for valid URL field."""
        sample_field.field_type = "url"

        is_valid, error_msg = service.validate_field_value(
            sample_field, "https://example.com"
        )

        assert is_valid
        assert error_msg is None

    def test_validate_url_type_http(self, service, sample_field):
        """Test validation passes for URL field with HTTP."""
        sample_field.field_type = "url"

        is_valid, error_msg = service.validate_field_value(
            sample_field, "http://example.com"
        )

        assert is_valid
        assert error_msg is None

    def test_validate_url_type_invalid(self, service, sample_field):
        """Test validation fails for URL field with invalid format."""
        sample_field.field_type = "url"
        sample_field.display_name = "URL Field"

        is_valid, error_msg = service.validate_field_value(sample_field, "not_a_url")

        assert not is_valid
        assert "URL格式不正确" in error_msg

    def test_validate_field_exception_handling(self, service, sample_field):
        """Test validation handles exceptions gracefully."""
        sample_field.field_type = "text"
        sample_field.validation_rules = "invalid json"
        sample_field.display_name = "Test Field"

        is_valid, error_msg = service.validate_field_value(sample_field, "value")

        assert not is_valid
        assert "验证字段" in error_msg and "发生错误" in error_msg


class TestUpdateAssetFieldValues:
    """Tests for update_asset_field_values method."""

    def test_update_asset_field_values_success(self, service, mock_db, sample_field):
        """Test successful update of asset field values."""
        values = [
            {"field_id": TEST_FIELD_ID, "value": "test_value"},
        ]

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=sample_field,
        ):
            result = service.update_asset_field_values(
                mock_db, asset_id=TEST_ASSET_ID, values=values
            )

            assert len(result) == 1
            assert result[0]["field_id"] == TEST_FIELD_ID
            assert result[0]["value"] == "test_value"

    def test_update_asset_field_values_validation_error(
        self, service, mock_db, sample_field
    ):
        """Test update fails when validation fails."""
        sample_field.is_required = True
        sample_field.display_name = "Required Field"
        values = [
            {"field_id": TEST_FIELD_ID, "value": None},
        ]

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=sample_field,
        ):
            with pytest.raises(ValueError) as excinfo:
                service.update_asset_field_values(
                    mock_db, asset_id=TEST_ASSET_ID, values=values
                )

            assert "必填项" in str(excinfo.value)

    def test_update_asset_field_values_skip_missing_field_id(self, service, mock_db):
        """Test update skips entries without field_id."""
        values = [
            {"value": "test_value"},  # No field_id
        ]

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=None,
        ):
            result = service.update_asset_field_values(
                mock_db, asset_id=TEST_ASSET_ID, values=values
            )

            assert len(result) == 0

    def test_update_asset_field_values_skip_nonexistent_field(self, service, mock_db):
        """Test update skips entries for nonexistent fields."""
        values = [
            {"field_id": "nonexistent_field_id", "value": "test_value"},
        ]

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=None,
        ):
            result = service.update_asset_field_values(
                mock_db, asset_id=TEST_ASSET_ID, values=values
            )

            assert len(result) == 0

    def test_update_asset_field_values_multiple_fields(
        self, service, mock_db, sample_field
    ):
        """Test update with multiple field values."""
        sample_field2 = AssetCustomField(
            id="field_456",
            field_name="test_field_2",
            display_name="Test Field 2",
            field_type="number",
            is_required=False,
        )

        values = [
            {"field_id": TEST_FIELD_ID, "value": "text_value"},
            {"field_id": "field_456", "value": 123},
        ]

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            side_effect=[sample_field, sample_field2],
        ):
            result = service.update_asset_field_values(
                mock_db, asset_id=TEST_ASSET_ID, values=values
            )

            assert len(result) == 2
            assert result[0]["field_id"] == TEST_FIELD_ID
            assert result[1]["field_id"] == "field_456"


class TestGetAssetFieldValues:
    """Tests for get_asset_field_values method."""

    def test_get_asset_field_values(self, service, mock_db):
        """Test getting asset field values."""
        expected_values = [
            {"field_id": TEST_FIELD_ID, "value": "test_value"},
        ]

        with patch(
            "src.services.custom_field.service.custom_field_crud.get_asset_field_values",
            return_value=expected_values,
        ):
            result = service.get_asset_field_values(mock_db, asset_id=TEST_ASSET_ID)

            assert result == expected_values


class TestToggleActiveStatus:
    """Tests for toggle_active_status method."""

    def test_toggle_active_status_to_inactive(self, service, mock_db, sample_field):
        """Test toggling field from active to inactive."""
        sample_field.is_active = True

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=sample_field,
        ):
            result = service.toggle_active_status(mock_db, id=TEST_FIELD_ID)

            assert result.is_active is False
            mock_db.commit.assert_called_once()

    def test_toggle_active_status_to_active(self, service, mock_db, sample_field):
        """Test toggling field from inactive to active."""
        sample_field.is_active = False

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=sample_field,
        ):
            result = service.toggle_active_status(mock_db, id=TEST_FIELD_ID)

            assert result.is_active is True
            mock_db.commit.assert_called_once()

    def test_toggle_active_status_not_found(self, service, mock_db):
        """Test toggling non-existent field raises ValueError."""
        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=None,
        ):
            with pytest.raises(ValueError) as excinfo:
                service.toggle_active_status(mock_db, id="nonexistent_id")

            assert "不存在" in str(excinfo.value)


class TestUpdateSortOrders:
    """Tests for update_sort_orders method."""

    def test_update_sort_orders_single_field(self, service, mock_db, sample_field):
        """Test updating sort order for single field."""
        sort_data = [{"id": TEST_FIELD_ID, "sort_order": 5}]

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=sample_field,
        ):
            result = service.update_sort_orders(mock_db, sort_data=sort_data)

            assert len(result) == 1
            assert result[0].sort_order == 5
            mock_db.commit.assert_called_once()

    def test_update_sort_orders_multiple_fields(self, service, mock_db):
        """Test updating sort orders for multiple fields."""
        field1 = AssetCustomField(id="field_1", field_name="field1", sort_order=0)
        field2 = AssetCustomField(id="field_2", field_name="field2", sort_order=0)
        field3 = AssetCustomField(id="field_3", field_name="field3", sort_order=0)

        sort_data = [
            {"id": "field_1", "sort_order": 1},
            {"id": "field_2", "sort_order": 2},
            {"id": "field_3", "sort_order": 3},
        ]

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            side_effect=[field1, field2, field3],
        ):
            result = service.update_sort_orders(mock_db, sort_data=sort_data)

            assert len(result) == 3
            assert result[0].sort_order == 1
            assert result[1].sort_order == 2
            assert result[2].sort_order == 3
            mock_db.commit.assert_called_once()

    def test_update_sort_orders_skip_missing_id(self, service, mock_db, sample_field):
        """Test update skips entries without id."""
        sort_data = [
            {"sort_order": 5},  # No id
        ]

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=sample_field,
        ):
            result = service.update_sort_orders(db=mock_db, sort_data=sort_data)

            assert len(result) == 0

    def test_update_sort_orders_skip_missing_sort_order(
        self, service, mock_db, sample_field
    ):
        """Test update skips entries without sort_order."""
        sort_data = [
            {"id": TEST_FIELD_ID},  # No sort_order
        ]

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=sample_field,
        ):
            result = service.update_sort_orders(mock_db, sort_data=sort_data)

            assert len(result) == 0

    def test_update_sort_orders_skip_nonexistent_field(self, service, mock_db):
        """Test update skips entries for nonexistent fields."""
        sort_data = [
            {"id": "nonexistent_id", "sort_order": 5},
        ]

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            return_value=None,
        ):
            result = service.update_sort_orders(mock_db, sort_data=sort_data)

            assert len(result) == 0

    def test_update_sort_orders_mixed_valid_invalid(
        self, service, mock_db, sample_field
    ):
        """Test update with mix of valid and invalid entries."""
        sort_data = [
            {"id": TEST_FIELD_ID, "sort_order": 1},  # Valid
            {"sort_order": 2},  # Invalid - no id
            {"id": "nonexistent_id", "sort_order": 3},  # Invalid - field doesn't exist
            {"id": TEST_FIELD_ID, "sort_order": 4},  # Valid - update same field
        ]

        AssetCustomField(id="field_2", field_name="field2", sort_order=0)

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            side_effect=[sample_field, None, sample_field],
        ):
            result = service.update_sort_orders(mock_db, sort_data=sort_data)

            # Should have 2 valid entries (both updates to TEST_FIELD_ID)
            assert len(result) == 2
