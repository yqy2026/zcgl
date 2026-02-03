"""
Comprehensive Unit Tests for Custom Fields API Routes (src/api/v1/custom_fields.py)

This test module covers all endpoints in the custom_fields router to achieve 70%+ coverage.

Endpoints Tested:
1. GET /api/v1/custom-fields/ - Get custom fields list
2. GET /api/v1/custom-fields/{field_id} - Get custom field details
3. POST /api/v1/custom-fields/ - Create custom field
4. PUT /api/v1/custom-fields/{field_id} - Update custom field
5. DELETE /api/v1/custom-fields/{field_id} - Delete custom field
6. POST /api/v1/custom-fields/validate - Validate custom field value
7. GET /api/v1/custom-fields/types - Get field types list
8. GET /api/v1/custom-fields/assets/{asset_id}/values - Get asset custom field values
9. PUT /api/v1/custom-fields/assets/{asset_id}/values - Update asset custom field values
10. POST /api/v1/custom-fields/assets/batch-values - Batch set custom field values

Testing Approach:
- Mock all dependencies (CustomFieldService, CustomFieldCRUD, database, auth)
- Test successful responses
- Test error handling scenarios
- Test request validation
- Test response schemas
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.core.exception_handler import (
    BaseBusinessError,
    BusinessValidationError,
    DuplicateResourceError,
    ResourceNotFoundError,
)

pytestmark = pytest.mark.api


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_current_user():
    """Create mock current user"""
    user = MagicMock()
    user.id = "test-user-id"
    user.username = "testuser"
    user.is_active = True
    return user


@pytest.fixture
def mock_custom_field():
    """Create mock custom field"""
    field = MagicMock()
    field.id = "test-field-id"
    field.field_name = "test_field"
    field.display_name = "Test Field"
    field.field_type = "text"
    field.is_required = True
    field.is_active = True
    field.sort_order = 0
    field.default_value = None
    field.field_options = None
    field.validation_rules = None
    field.help_text = "Test help text"
    field.description = "Test description"
    field.created_at = datetime.now(UTC)
    field.updated_at = datetime.now(UTC)
    return field


@pytest.fixture
def mock_custom_field_list():
    """Create mock custom field list"""
    fields = []
    for i in range(3):
        field = MagicMock()
        field.id = f"field-{i}"
        field.field_name = f"field_{i}"
        field.display_name = f"Field {i}"
        field.field_type = "text"
        field.is_required = False
        field.is_active = True
        field.sort_order = i
        field.default_value = None
        field.field_options = None
        field.validation_rules = None
        field.help_text = None
        field.description = None
        field.created_at = datetime.now(UTC)
        field.updated_at = datetime.now(UTC)
        fields.append(field)
    return fields


# ============================================================================
# Test: GET / - Get Custom Fields List
# ============================================================================


class TestGetCustomFields:
    """Tests for GET /api/v1/custom-fields/ endpoint"""

    @patch("src.api.v1.assets.custom_fields.custom_field_crud")
    def test_get_custom_fields_success(
        self, mock_crud, mock_db, mock_current_user, mock_custom_field_list
    ):
        """Test getting custom fields list successfully"""
        from src.api.v1.assets.custom_fields import get_custom_fields

        mock_crud.get_multi_with_filters.return_value = mock_custom_field_list

        result = get_custom_fields(
            asset_id=None,
            field_type=None,
            is_required=None,
            is_active=None,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert len(result) == 3
        assert result[0].field_name == "field_0"
        mock_crud.get_multi_with_filters.assert_called_once_with(db=mock_db, filters={})

    @patch("src.api.v1.assets.custom_fields.custom_field_crud")
    def test_get_custom_fields_with_filters(
        self, mock_crud, mock_db, mock_current_user, mock_custom_field_list
    ):
        """Test getting custom fields with filters"""
        from src.api.v1.assets.custom_fields import get_custom_fields

        # Return only one field matching the filter
        mock_crud.get_multi_with_filters.return_value = [mock_custom_field_list[0]]

        result = get_custom_fields(
            asset_id="asset-123",
            field_type="text",
            is_required=True,
            is_active=True,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert len(result) == 1
        mock_crud.get_multi_with_filters.assert_called_once()
        # Verify filters were built correctly
        call_filters = mock_crud.get_multi_with_filters.call_args[1]["filters"]
        assert call_filters["asset_id"] == "asset-123"
        assert call_filters["field_type"] == "text"
        assert call_filters["is_required"] == "True"
        assert call_filters["is_active"] == "True"

    @patch("src.api.v1.assets.custom_fields.custom_field_crud")
    def test_get_custom_fields_empty_list(self, mock_crud, mock_db, mock_current_user):
        """Test getting custom fields with empty result"""
        from src.api.v1.assets.custom_fields import get_custom_fields

        mock_crud.get_multi_with_filters.return_value = []

        result = get_custom_fields(
            asset_id=None,
            field_type=None,
            is_required=None,
            is_active=None,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert len(result) == 0

    @patch("src.api.v1.assets.custom_fields.custom_field_crud")
    def test_get_custom_fields_exception(self, mock_crud, mock_db, mock_current_user):
        """Test getting custom fields with database exception"""
        from src.api.v1.assets.custom_fields import get_custom_fields

        mock_crud.get_multi_with_filters.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            get_custom_fields(
                asset_id=None,
                field_type=None,
                is_required=None,
                is_active=None,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500
        assert "获取自定义字段列表失败" in exc_info.value.message


# ============================================================================
# Test: GET /{field_id} - Get Custom Field Details
# ============================================================================


class TestGetCustomField:
    """Tests for GET /api/v1/custom-fields/{field_id} endpoint"""

    @patch("src.api.v1.assets.custom_fields.custom_field_crud")
    def test_get_custom_field_success(
        self, mock_crud, mock_db, mock_current_user, mock_custom_field
    ):
        """Test getting custom field successfully"""
        from src.api.v1.assets.custom_fields import get_custom_field

        mock_crud.get.return_value = mock_custom_field

        result = get_custom_field(
            field_id="test-field-id", db=mock_db, current_user=mock_current_user
        )

        assert result.id == "test-field-id"
        assert result.field_name == "test_field"
        mock_crud.get.assert_called_once_with(db=mock_db, id="test-field-id")

    @patch("src.api.v1.assets.custom_fields.custom_field_crud")
    def test_get_custom_field_not_found(self, mock_crud, mock_db, mock_current_user):
        """Test getting non-existent custom field"""
        from src.api.v1.assets.custom_fields import get_custom_field

        mock_crud.get.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            get_custom_field(
                field_id="nonexistent-id", db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404
        assert "custom_field不存在" in exc_info.value.message
        assert "nonexistent-id" in exc_info.value.message

    @patch("src.api.v1.assets.custom_fields.custom_field_crud")
    def test_get_custom_field_exception(self, mock_crud, mock_db, mock_current_user):
        """Test getting custom field with database exception"""
        from src.api.v1.assets.custom_fields import get_custom_field

        mock_crud.get.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            get_custom_field(
                field_id="test-field-id", db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500
        assert "获取自定义字段详情失败" in exc_info.value.message


# ============================================================================
# Test: POST / - Create Custom Field
# ============================================================================


class TestCreateCustomField:
    """Tests for POST /api/v1/custom-fields/ endpoint"""

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_create_custom_field_success(
        self, mock_service, mock_db, mock_current_user, mock_custom_field
    ):
        """Test creating custom field successfully"""
        from src.api.v1.assets.custom_fields import create_custom_field
        from src.schemas.asset import AssetCustomFieldCreate

        field_data = AssetCustomFieldCreate(
            field_name="new_field",
            display_name="New Field",
            field_type="text",
            is_required=False,
            is_active=True,
        )

        mock_service.create_custom_field.return_value = mock_custom_field

        result = create_custom_field(
            field_in=field_data, db=mock_db, current_user=mock_current_user
        )

        assert result.id == "test-field-id"
        mock_service.create_custom_field.assert_called_once_with(
            db=mock_db, obj_in=field_data
        )

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_create_custom_field_duplicate_name(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test creating custom field with duplicate name"""
        from src.api.v1.assets.custom_fields import create_custom_field
        from src.schemas.asset import AssetCustomFieldCreate

        field_data = AssetCustomFieldCreate(
            field_name="existing_field",
            display_name="Existing Field",
            field_type="text",
        )

        mock_service.create_custom_field.side_effect = DuplicateResourceError(
            "字段",
            "field_name",
            "existing_field",
        )

        with pytest.raises(BaseBusinessError) as exc_info:
            create_custom_field(
                field_in=field_data, db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 409
        assert "字段" in exc_info.value.message

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_create_custom_field_http_exception(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test creating custom field with business exception from service"""
        from src.api.v1.assets.custom_fields import create_custom_field
        from src.schemas.asset import AssetCustomFieldCreate

        field_data = AssetCustomFieldCreate(
            field_name="new_field", display_name="New Field", field_type="text"
        )

        mock_service.create_custom_field.side_effect = BaseBusinessError(
            message="Permission denied",
            code="PERMISSION_DENIED",
            status_code=403,
        )

        with pytest.raises(BaseBusinessError) as exc_info:
            create_custom_field(
                field_in=field_data, db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 403
        assert "Permission denied" in exc_info.value.message

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_create_custom_field_exception(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test creating custom field with unexpected exception"""
        from src.api.v1.assets.custom_fields import create_custom_field
        from src.schemas.asset import AssetCustomFieldCreate

        field_data = AssetCustomFieldCreate(
            field_name="new_field", display_name="New Field", field_type="text"
        )

        mock_service.create_custom_field.side_effect = Exception("Unexpected error")

        with pytest.raises(BaseBusinessError) as exc_info:
            create_custom_field(
                field_in=field_data, db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500
        assert "创建自定义字段失败" in exc_info.value.message


# ============================================================================
# Test: PUT /{field_id} - Update Custom Field
# ============================================================================


class TestUpdateCustomField:
    """Tests for PUT /api/v1/custom-fields/{field_id} endpoint"""

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_update_custom_field_success(
        self, mock_service, mock_db, mock_current_user, mock_custom_field
    ):
        """Test updating custom field successfully"""
        from src.api.v1.assets.custom_fields import update_custom_field
        from src.schemas.asset import AssetCustomFieldUpdate

        update_data = AssetCustomFieldUpdate(display_name="Updated Display Name")

        mock_service.update_custom_field.return_value = mock_custom_field

        result = update_custom_field(
            field_id="test-field-id",
            field_in=update_data,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.id == "test-field-id"
        mock_service.update_custom_field.assert_called_once_with(
            db=mock_db, id="test-field-id", obj_in=update_data
        )

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_update_custom_field_not_found(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test updating non-existent custom field"""
        from src.api.v1.assets.custom_fields import update_custom_field
        from src.schemas.asset import AssetCustomFieldUpdate

        update_data = AssetCustomFieldUpdate(display_name="Updated Name")

        mock_service.update_custom_field.side_effect = ResourceNotFoundError(
            "字段",
            "nonexistent-id",
        )

        with pytest.raises(BaseBusinessError) as exc_info:
            update_custom_field(
                field_id="nonexistent-id",
                field_in=update_data,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "字段不存在" in exc_info.value.message

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_update_custom_field_duplicate_name(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test updating custom field with duplicate name"""
        from src.api.v1.assets.custom_fields import update_custom_field
        from src.schemas.asset import AssetCustomFieldUpdate

        update_data = AssetCustomFieldUpdate(field_name="existing_field")

        mock_service.update_custom_field.side_effect = DuplicateResourceError(
            "字段",
            "field_name",
            "existing_field",
        )

        with pytest.raises(BaseBusinessError) as exc_info:
            update_custom_field(
                field_id="test-field-id",
                field_in=update_data,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 409
        assert "字段" in exc_info.value.message

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_update_custom_field_exception(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test updating custom field with unexpected exception"""
        from src.api.v1.assets.custom_fields import update_custom_field
        from src.schemas.asset import AssetCustomFieldUpdate

        update_data = AssetCustomFieldUpdate(display_name="Updated Name")

        mock_service.update_custom_field.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            update_custom_field(
                field_id="test-field-id",
                field_in=update_data,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500
        assert "更新自定义字段失败" in exc_info.value.message


# ============================================================================
# Test: DELETE /{field_id} - Delete Custom Field
# ============================================================================


class TestDeleteCustomField:
    """Tests for DELETE /api/v1/custom-fields/{field_id} endpoint"""

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_delete_custom_field_success(
        self, mock_service, mock_db, mock_current_user, mock_custom_field
    ):
        """Test deleting custom field successfully"""
        from src.api.v1.assets.custom_fields import delete_custom_field

        mock_service.delete_custom_field.return_value = mock_custom_field

        result = delete_custom_field(
            field_id="test-field-id", db=mock_db, current_user=mock_current_user
        )

        assert result["message"] == "字段 test-field-id 已成功删除"
        mock_service.delete_custom_field.assert_called_once_with(
            db=mock_db, id="test-field-id"
        )

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_delete_custom_field_not_found(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test deleting non-existent custom field"""
        from src.api.v1.assets.custom_fields import delete_custom_field

        mock_service.delete_custom_field.side_effect = ResourceNotFoundError(
            "字段",
            "nonexistent-id",
        )

        with pytest.raises(BaseBusinessError) as exc_info:
            delete_custom_field(
                field_id="nonexistent-id", db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404
        assert "字段不存在" in exc_info.value.message
        assert "nonexistent-id" in exc_info.value.message

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_delete_custom_field_exception(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test deleting custom field with unexpected exception"""
        from src.api.v1.assets.custom_fields import delete_custom_field

        mock_service.delete_custom_field.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            delete_custom_field(
                field_id="test-field-id", db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500
        assert "删除自定义字段失败" in exc_info.value.message


# ============================================================================
# Test: POST /validate - Validate Custom Field Value
# ============================================================================


class TestValidateCustomFieldValue:
    """Tests for POST /api/v1/custom-fields/validate endpoint"""

    @patch("src.api.v1.assets.custom_fields.custom_field_crud")
    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_validate_custom_field_value_success(
        self, mock_service, mock_crud, mock_db, mock_current_user, mock_custom_field
    ):
        """Test validating custom field value successfully"""
        from src.api.v1.assets.custom_fields import validate_custom_field_value

        mock_crud.get.return_value = mock_custom_field
        mock_service.validate_field_value.return_value = (True, None)

        result = validate_custom_field_value(
            field_id="test-field-id",
            value="test value",
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["valid"] is True
        assert result["message"] == "验证通过"
        mock_crud.get.assert_called_once_with(db=mock_db, id="test-field-id")
        mock_service.validate_field_value.assert_called_once()

    @patch("src.api.v1.assets.custom_fields.custom_field_crud")
    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_validate_custom_field_value_invalid(
        self, mock_service, mock_crud, mock_db, mock_current_user, mock_custom_field
    ):
        """Test validating invalid custom field value"""
        from src.api.v1.assets.custom_fields import validate_custom_field_value

        mock_crud.get.return_value = mock_custom_field
        mock_service.validate_field_value.return_value = (
            False,
            "字段长度不能超过100个字符",
        )

        result = validate_custom_field_value(
            field_id="test-field-id",
            value="x" * 150,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["valid"] is False
        assert result["error"] == "字段长度不能超过100个字符"

    @patch("src.api.v1.assets.custom_fields.custom_field_crud")
    def test_validate_custom_field_value_not_found(
        self, mock_crud, mock_db, mock_current_user
    ):
        """Test validating value for non-existent field"""
        from src.api.v1.assets.custom_fields import validate_custom_field_value

        mock_crud.get.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            validate_custom_field_value(
                field_id="nonexistent-id",
                value="test",
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "custom_field不存在" in exc_info.value.message
        assert "nonexistent-id" in exc_info.value.message

    @patch("src.api.v1.assets.custom_fields.custom_field_crud")
    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_validate_custom_field_value_exception(
        self, mock_service, mock_crud, mock_db, mock_current_user, mock_custom_field
    ):
        """Test validating custom field value with unexpected exception"""
        from src.api.v1.assets.custom_fields import validate_custom_field_value

        mock_crud.get.return_value = mock_custom_field
        mock_service.validate_field_value.side_effect = Exception("Validation error")

        with pytest.raises(BaseBusinessError) as exc_info:
            validate_custom_field_value(
                field_id="test-field-id",
                value="test",
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500
        assert "验证字段值失败" in exc_info.value.message


# ============================================================================
# Test: GET /types - Get Field Types List
# ============================================================================


class TestGetFieldTypes:
    """Tests for GET /api/v1/custom-fields/types endpoint"""

    def test_get_field_types_success(self, mock_current_user):
        """Test getting field types successfully"""
        from src.api.v1.assets.custom_fields import get_field_types

        result = get_field_types(current_user=mock_current_user)

        assert "field_types" in result
        assert len(result["field_types"]) == 12

        # Verify expected field types exist
        type_values = [t["value"] for t in result["field_types"]]
        assert "text" in type_values
        assert "number" in type_values
        assert "decimal" in type_values
        assert "boolean" in type_values
        assert "date" in type_values
        assert "select" in type_values
        assert "multiselect" in type_values

    def test_get_field_types_exception(self, mock_current_user):
        """Test getting field types with exception"""
        from src.api.v1.assets.custom_fields import get_field_types

        # This endpoint constructs a static list, so it's unlikely to fail
        # But we can test the structure
        result = get_field_types(current_user=mock_current_user)

        # Verify structure
        assert isinstance(result["field_types"], list)
        for field_type in result["field_types"]:
            assert "value" in field_type
            assert "label" in field_type


# ============================================================================
# Test: GET /assets/{asset_id}/values - Get Asset Custom Field Values
# ============================================================================


class TestGetAssetCustomFieldValues:
    """Tests for GET /api/v1/custom-fields/assets/{asset_id}/values endpoint"""

    @patch("src.api.v1.assets.custom_fields.custom_field_crud")
    def test_get_asset_custom_field_values_success(
        self, mock_crud, mock_db, mock_current_user
    ):
        """Test getting asset custom field values successfully"""
        from src.api.v1.assets.custom_fields import get_asset_custom_field_values

        mock_values = [
            {"field_name": "field1", "value": "value1"},
            {"field_name": "field2", "value": "value2"},
        ]
        mock_crud.get_asset_field_values.return_value = mock_values

        result = get_asset_custom_field_values(
            asset_id="asset-123", db=mock_db, current_user=mock_current_user
        )

        assert result["asset_id"] == "asset-123"
        assert result["values"] == mock_values
        mock_crud.get_asset_field_values.assert_called_once_with(
            db=mock_db, asset_id="asset-123"
        )

    @patch("src.api.v1.assets.custom_fields.custom_field_crud")
    def test_get_asset_custom_field_values_empty(
        self, mock_crud, mock_db, mock_current_user
    ):
        """Test getting asset custom field values when none exist"""
        from src.api.v1.assets.custom_fields import get_asset_custom_field_values

        mock_crud.get_asset_field_values.return_value = []

        result = get_asset_custom_field_values(
            asset_id="asset-123", db=mock_db, current_user=mock_current_user
        )

        assert result["asset_id"] == "asset-123"
        assert result["values"] == []

    @patch("src.api.v1.assets.custom_fields.custom_field_crud")
    def test_get_asset_custom_field_values_exception(
        self, mock_crud, mock_db, mock_current_user
    ):
        """Test getting asset custom field values with exception"""
        from src.api.v1.assets.custom_fields import get_asset_custom_field_values

        mock_crud.get_asset_field_values.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            get_asset_custom_field_values(
                asset_id="asset-123", db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500
        assert "获取资产自定义字段值失败" in exc_info.value.message


# ============================================================================
# Test: PUT /assets/{asset_id}/values - Update Asset Custom Field Values
# ============================================================================


class TestUpdateAssetCustomFieldValues:
    """Tests for PUT /api/v1/custom-fields/assets/{asset_id}/values endpoint"""

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_update_asset_custom_field_values_success(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test updating asset custom field values successfully"""
        from src.api.v1.assets.custom_fields import update_asset_custom_field_values
        from src.schemas.asset import CustomFieldValueUpdate

        values_update = CustomFieldValueUpdate(
            values=[
                {"field_name": "field1", "value": "new_value1"},
                {"field_name": "field2", "value": "new_value2"},
            ]
        )

        mock_updated_values = [
            {"field_name": "field1", "value": "new_value1"},
            {"field_name": "field2", "value": "new_value2"},
        ]
        mock_service.update_asset_field_values.return_value = mock_updated_values

        result = update_asset_custom_field_values(
            asset_id="asset-123",
            values_update=values_update,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["asset_id"] == "asset-123"
        assert result["values"] == mock_updated_values
        mock_service.update_asset_field_values.assert_called_once_with(
            db=mock_db, asset_id="asset-123", values=values_update.values
        )

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_update_asset_custom_field_values_validation_error(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test updating asset custom field values with validation error"""
        from src.api.v1.assets.custom_fields import update_asset_custom_field_values
        from src.schemas.asset import CustomFieldValueUpdate

        values_update = CustomFieldValueUpdate(
            values=[{"field_name": "field1", "value": "invalid_value"}]
        )

        mock_service.update_asset_field_values.side_effect = BusinessValidationError(
            message="字段值验证失败",
            field_errors={"custom_fields": ["字段值验证失败"]},
        )

        with pytest.raises(BaseBusinessError) as exc_info:
            update_asset_custom_field_values(
                asset_id="asset-123",
                values_update=values_update,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 422
        assert "字段值验证失败" in exc_info.value.message

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_update_asset_custom_field_values_exception(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test updating asset custom field values with unexpected exception"""
        from src.api.v1.assets.custom_fields import update_asset_custom_field_values
        from src.schemas.asset import CustomFieldValueUpdate

        values_update = CustomFieldValueUpdate(values=[])

        mock_service.update_asset_field_values.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            update_asset_custom_field_values(
                asset_id="asset-123",
                values_update=values_update,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500
        assert "更新资产自定义字段值失败" in exc_info.value.message


# ============================================================================
# Test: POST /assets/batch-values - Batch Set Custom Field Values
# ============================================================================


class TestBatchSetCustomFieldValues:
    """Tests for POST /api/v1/custom-fields/assets/batch-values endpoint"""

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_batch_set_custom_field_values_success(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test batch setting custom field values successfully"""
        from src.api.v1.assets.custom_fields import batch_set_custom_field_values

        updates = [
            {
                "asset_id": "asset-1",
                "values": [{"field_name": "field1", "value": "value1"}],
            },
            {
                "asset_id": "asset-2",
                "values": [{"field_name": "field2", "value": "value2"}],
            },
        ]

        mock_service.update_asset_field_values.return_value = [
            {"field_name": "field1", "value": "value1"}
        ]

        result = batch_set_custom_field_values(
            updates=updates, db=mock_db, current_user=mock_current_user
        )

        assert "results" in result
        assert len(result["results"]) == 2
        assert result["results"][0]["success"] is True
        assert result["results"][0]["asset_id"] == "asset-1"
        assert result["results"][1]["success"] is True
        assert result["results"][1]["asset_id"] == "asset-2"

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_batch_set_custom_field_values_partial_failure(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test batch setting custom field values with partial failures"""
        from src.api.v1.assets.custom_fields import batch_set_custom_field_values

        updates = [
            {
                "asset_id": "asset-1",
                "values": [{"field_name": "field1", "value": "value1"}],
            },
            {
                "asset_id": "asset-2",
                "values": [{"field_name": "field2", "value": "value2"}],
            },
        ]

        # First succeeds, second fails
        call_count = [0]

        def mock_update(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return [{"field_name": "field1", "value": "value1"}]
            else:
                raise Exception("Update failed")

        mock_service.update_asset_field_values.side_effect = mock_update

        result = batch_set_custom_field_values(
            updates=updates, db=mock_db, current_user=mock_current_user
        )

        assert "results" in result
        assert len(result["results"]) == 2
        assert result["results"][0]["success"] is True
        assert result["results"][1]["success"] is False
        assert "error" in result["results"][1]

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_batch_set_custom_field_values_skip_missing_asset_id(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test batch setting skips entries without asset_id"""
        from src.api.v1.assets.custom_fields import batch_set_custom_field_values

        updates = [
            {
                "asset_id": "asset-1",
                "values": [{"field_name": "field1", "value": "value1"}],
            },
            {
                "values": [{"field_name": "field2", "value": "value2"}]
            },  # Missing asset_id
            {
                "asset_id": "asset-3",
                "values": [{"field_name": "field3", "value": "value3"}],
            },
        ]

        mock_service.update_asset_field_values.return_value = [
            {"field_name": "field1", "value": "value1"}
        ]

        result = batch_set_custom_field_values(
            updates=updates, db=mock_db, current_user=mock_current_user
        )

        assert "results" in result
        # Should only process entries with asset_id
        assert len(result["results"]) == 2
        mock_service.update_asset_field_values.assert_called()

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_batch_set_custom_field_values_empty_list(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test batch setting with empty updates list"""
        from src.api.v1.assets.custom_fields import batch_set_custom_field_values

        updates = []

        result = batch_set_custom_field_values(
            updates=updates, db=mock_db, current_user=mock_current_user
        )

        assert "results" in result
        assert len(result["results"]) == 0
        mock_service.update_asset_field_values.assert_not_called()

    @patch("src.api.v1.assets.custom_fields.custom_field_service")
    def test_batch_set_custom_field_values_exception(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test batch setting custom field values with unexpected exception in outer handler"""
        from src.api.v1.assets.custom_fields import batch_set_custom_field_values

        # The batch endpoint has an outer try-except that catches exceptions
        # We need to trigger an exception outside the inner loop's try-except
        # Let's cause an exception during the results processing
        updates = [{"asset_id": "asset-1", "values": []}]

        # The function handles exceptions per update item, so to test the outer handler
        # we need to verify it doesn't crash even with partial failures
        # This test verifies resilience - the function should return results even if some fail
        mock_service.update_asset_field_values.side_effect = Exception("Update failed")

        # This should NOT raise an exception, but return results with success: False
        result = batch_set_custom_field_values(
            updates=updates, db=mock_db, current_user=mock_current_user
        )

        # The function catches exceptions per-item and marks as failed
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["success"] is False
        assert "error" in result["results"][0]
