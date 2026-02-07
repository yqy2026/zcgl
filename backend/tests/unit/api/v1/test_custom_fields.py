"""
Comprehensive Unit Tests for Custom Fields API Routes (src/api/v1/assets/custom_fields.py)

This test module covers all endpoints in the custom_fields router to achieve 70%+ coverage.

Endpoints Tested:
1. GET /api/v1/asset-custom-fields/ - Get custom fields list
2. GET /api/v1/asset-custom-fields/{field_id} - Get custom field details
3. POST /api/v1/asset-custom-fields/ - Create custom field
4. PUT /api/v1/asset-custom-fields/{field_id} - Update custom field
5. DELETE /api/v1/asset-custom-fields/{field_id} - Delete custom field
6. POST /api/v1/asset-custom-fields/validate - Validate custom field value
7. GET /api/v1/asset-custom-fields/types - Get field types list
8. GET /api/v1/asset-custom-fields/assets/{asset_id}/values - Get asset custom field values
9. PUT /api/v1/asset-custom-fields/assets/{asset_id}/values - Update asset custom field values
10. POST /api/v1/asset-custom-fields/assets/batch-values - Batch set custom field values

Testing Approach:
- Mock all dependencies (CustomFieldService, CustomFieldCRUD, database, auth)
- Test successful responses
- Test error handling scenarios
- Test request validation
- Test response schemas
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import (
    BaseBusinessError,
    BusinessValidationError,
    DuplicateResourceError,
    ResourceNotFoundError,
)

pytestmark = pytest.mark.api


@pytest.fixture
def mock_current_user():
    user = MagicMock()
    user.id = "test-user-id"
    user.username = "testuser"
    user.is_active = True
    return user


@pytest.fixture
def mock_custom_field():
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
def mock_custom_field_list(mock_custom_field):
    other = MagicMock()
    other.id = "field-2"
    other.field_name = "field_2"
    other.display_name = "Field 2"
    other.field_type = "number"
    other.is_required = False
    other.is_active = True
    other.sort_order = 1
    other.default_value = None
    other.field_options = None
    other.validation_rules = None
    other.help_text = None
    other.description = None
    other.created_at = datetime.now(UTC)
    other.updated_at = datetime.now(UTC)
    return [mock_custom_field, other]


class TestGetCustomFields:
    async def test_get_custom_fields_success(
        self, mock_db, mock_current_user, mock_custom_field_list
    ):
        from src.api.v1.assets.custom_fields import get_custom_fields

        with patch("src.api.v1.assets.custom_fields.custom_field_crud") as mock_crud:
            mock_crud.get_multi_with_filters_async = AsyncMock(
                return_value=mock_custom_field_list
            )
            result = await get_custom_fields(
                asset_id=None,
                field_type=None,
                is_required=None,
                is_active=None,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert len(result) == 2
        assert result[0].field_name == "test_field"
        mock_crud.get_multi_with_filters_async.assert_awaited_once_with(
            db=mock_db, filters={}
        )

    async def test_get_custom_fields_with_filters(
        self, mock_db, mock_current_user, mock_custom_field_list
    ):
        from src.api.v1.assets.custom_fields import get_custom_fields

        with patch("src.api.v1.assets.custom_fields.custom_field_crud") as mock_crud:
            mock_crud.get_multi_with_filters_async = AsyncMock(
                return_value=[mock_custom_field_list[0]]
            )
            result = await get_custom_fields(
                asset_id="asset-123",
                field_type="text",
                is_required=True,
                is_active=True,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert len(result) == 1
        call_filters = mock_crud.get_multi_with_filters_async.call_args.kwargs["filters"]
        assert call_filters["asset_id"] == "asset-123"
        assert call_filters["field_type"] == "text"
        assert call_filters["is_required"] is True
        assert call_filters["is_active"] is True

    async def test_get_custom_fields_exception(self, mock_db, mock_current_user):
        from src.api.v1.assets.custom_fields import get_custom_fields

        with patch("src.api.v1.assets.custom_fields.custom_field_crud") as mock_crud:
            mock_crud.get_multi_with_filters_async = AsyncMock(
                side_effect=Exception("Database error")
            )
            with pytest.raises(BaseBusinessError) as exc_info:
                await get_custom_fields(
                    asset_id=None,
                    field_type=None,
                    is_required=None,
                    is_active=None,
                    db=mock_db,
                    current_user=mock_current_user,
                )

        assert exc_info.value.status_code == 500
        assert "获取自定义字段列表失败" in exc_info.value.message


class TestGetCustomField:
    async def test_get_custom_field_success(
        self, mock_db, mock_current_user, mock_custom_field
    ):
        from src.api.v1.assets.custom_fields import get_custom_field

        with patch("src.api.v1.assets.custom_fields.custom_field_crud") as mock_crud:
            mock_crud.get = AsyncMock(return_value=mock_custom_field)
            result = await get_custom_field(
                field_id="test-field-id",
                db=mock_db,
                current_user=mock_current_user,
            )

        assert result.id == "test-field-id"
        assert result.field_name == "test_field"
        mock_crud.get.assert_awaited_once_with(db=mock_db, id="test-field-id")

    async def test_get_custom_field_not_found(self, mock_db, mock_current_user):
        from src.api.v1.assets.custom_fields import get_custom_field

        with patch("src.api.v1.assets.custom_fields.custom_field_crud") as mock_crud:
            mock_crud.get = AsyncMock(return_value=None)
            with pytest.raises(BaseBusinessError) as exc_info:
                await get_custom_field(
                    field_id="nonexistent-id",
                    db=mock_db,
                    current_user=mock_current_user,
                )

        assert exc_info.value.status_code == 404
        assert "nonexistent-id" in exc_info.value.message


class TestCreateCustomField:
    async def test_create_custom_field_success(
        self, mock_db, mock_current_user, mock_custom_field
    ):
        from src.api.v1.assets.custom_fields import create_custom_field
        from src.schemas.asset import AssetCustomFieldCreate

        field_data = AssetCustomFieldCreate(
            field_name="new_field",
            display_name="New Field",
            field_type="text",
            is_required=False,
            is_active=True,
        )

        with patch("src.api.v1.assets.custom_fields.custom_field_service") as mock_service:
            mock_service.create_custom_field_async = AsyncMock(return_value=mock_custom_field)
            result = await create_custom_field(
                field_in=field_data,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert result.id == "test-field-id"
        mock_service.create_custom_field_async.assert_awaited_once_with(
            db=mock_db, obj_in=field_data
        )

    async def test_create_custom_field_duplicate_name(self, mock_db, mock_current_user):
        from src.api.v1.assets.custom_fields import create_custom_field
        from src.schemas.asset import AssetCustomFieldCreate

        field_data = AssetCustomFieldCreate(
            field_name="existing_field",
            display_name="Existing Field",
            field_type="text",
        )

        with patch("src.api.v1.assets.custom_fields.custom_field_service") as mock_service:
            mock_service.create_custom_field_async = AsyncMock(
                side_effect=DuplicateResourceError("字段", "field_name", "existing_field")
            )
            with pytest.raises(BaseBusinessError) as exc_info:
                await create_custom_field(
                    field_in=field_data,
                    db=mock_db,
                    current_user=mock_current_user,
                )

        assert exc_info.value.status_code == 409


class TestUpdateCustomField:
    async def test_update_custom_field_success(
        self, mock_db, mock_current_user, mock_custom_field
    ):
        from src.api.v1.assets.custom_fields import update_custom_field
        from src.schemas.asset import AssetCustomFieldUpdate

        update_data = AssetCustomFieldUpdate(display_name="Updated Display Name")

        with patch("src.api.v1.assets.custom_fields.custom_field_service") as mock_service:
            mock_service.update_custom_field_async = AsyncMock(return_value=mock_custom_field)
            result = await update_custom_field(
                field_id="test-field-id",
                field_in=update_data,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert result.id == "test-field-id"
        mock_service.update_custom_field_async.assert_awaited_once_with(
            db=mock_db, id="test-field-id", obj_in=update_data
        )

    async def test_update_custom_field_not_found(self, mock_db, mock_current_user):
        from src.api.v1.assets.custom_fields import update_custom_field
        from src.schemas.asset import AssetCustomFieldUpdate

        update_data = AssetCustomFieldUpdate(display_name="Updated Name")

        with patch("src.api.v1.assets.custom_fields.custom_field_service") as mock_service:
            mock_service.update_custom_field_async = AsyncMock(
                side_effect=ResourceNotFoundError("字段", "nonexistent-id")
            )
            with pytest.raises(BaseBusinessError) as exc_info:
                await update_custom_field(
                    field_id="nonexistent-id",
                    field_in=update_data,
                    db=mock_db,
                    current_user=mock_current_user,
                )

        assert exc_info.value.status_code == 404


class TestDeleteCustomField:
    async def test_delete_custom_field_success(self, mock_db, mock_current_user):
        from src.api.v1.assets.custom_fields import delete_custom_field

        with patch("src.api.v1.assets.custom_fields.custom_field_service") as mock_service:
            mock_service.delete_custom_field_async = AsyncMock(return_value=None)
            result = await delete_custom_field(
                field_id="test-field-id",
                db=mock_db,
                current_user=mock_current_user,
            )

        assert result["message"] == "字段 test-field-id 已成功删除"
        mock_service.delete_custom_field_async.assert_awaited_once_with(
            db=mock_db, id="test-field-id"
        )

    async def test_delete_custom_field_not_found(self, mock_db, mock_current_user):
        from src.api.v1.assets.custom_fields import delete_custom_field

        with patch("src.api.v1.assets.custom_fields.custom_field_service") as mock_service:
            mock_service.delete_custom_field_async = AsyncMock(
                side_effect=ResourceNotFoundError("字段", "nonexistent-id")
            )
            with pytest.raises(BaseBusinessError) as exc_info:
                await delete_custom_field(
                    field_id="nonexistent-id",
                    db=mock_db,
                    current_user=mock_current_user,
                )

        assert exc_info.value.status_code == 404


class TestValidateCustomFieldValue:
    async def test_validate_custom_field_value_success(
        self, mock_db, mock_current_user, mock_custom_field
    ):
        from src.api.v1.assets.custom_fields import validate_custom_field_value

        with patch("src.api.v1.assets.custom_fields.custom_field_crud") as mock_crud:
            with patch("src.api.v1.assets.custom_fields.custom_field_service") as mock_service:
                mock_crud.get = AsyncMock(return_value=mock_custom_field)
                mock_service.validate_field_value = MagicMock(return_value=(True, None))
                result = await validate_custom_field_value(
                    field_id="test-field-id",
                    value="test value",
                    db=mock_db,
                    current_user=mock_current_user,
                )

        assert result["valid"] is True
        assert result["message"] == "验证通过"

    async def test_validate_custom_field_value_not_found(self, mock_db, mock_current_user):
        from src.api.v1.assets.custom_fields import validate_custom_field_value

        with patch("src.api.v1.assets.custom_fields.custom_field_crud") as mock_crud:
            mock_crud.get = AsyncMock(return_value=None)
            with pytest.raises(BaseBusinessError) as exc_info:
                await validate_custom_field_value(
                    field_id="nonexistent-id",
                    value="test",
                    db=mock_db,
                    current_user=mock_current_user,
                )

        assert exc_info.value.status_code == 404


class TestGetFieldTypes:
    def test_get_field_types_success(self, mock_current_user):
        from src.api.v1.assets.custom_fields import get_field_types

        result = get_field_types(current_user=mock_current_user)
        assert "field_types" in result
        assert len(result["field_types"]) == 12
        assert any(item["value"] == "text" for item in result["field_types"])


class TestGetAssetCustomFieldValues:
    async def test_get_asset_custom_field_values_success(self, mock_db, mock_current_user):
        from src.api.v1.assets.custom_fields import get_asset_custom_field_values

        mock_values = [{"field_name": "field1", "value": "value1"}]
        with patch("src.api.v1.assets.custom_fields.custom_field_crud") as mock_crud:
            mock_crud.get_asset_field_values_async = AsyncMock(return_value=mock_values)
            result = await get_asset_custom_field_values(
                asset_id="asset-123",
                db=mock_db,
                current_user=mock_current_user,
            )

        assert result["asset_id"] == "asset-123"
        assert result["values"] == mock_values
        mock_crud.get_asset_field_values_async.assert_awaited_once_with(
            db=mock_db, asset_id="asset-123"
        )


class TestUpdateAssetCustomFieldValues:
    async def test_update_asset_custom_field_values_success(self, mock_db, mock_current_user):
        from src.api.v1.assets.custom_fields import update_asset_custom_field_values
        from src.schemas.asset import CustomFieldValueUpdate

        values_update = CustomFieldValueUpdate(
            values=[{"field_name": "field1", "value": "new_value1"}]
        )
        with patch("src.api.v1.assets.custom_fields.custom_field_service") as mock_service:
            mock_service.update_asset_field_values_async = AsyncMock(
                return_value=values_update.values
            )
            result = await update_asset_custom_field_values(
                asset_id="asset-123",
                values_update=values_update,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert result["asset_id"] == "asset-123"
        assert result["values"] == values_update.values

    async def test_update_asset_custom_field_values_validation_error(
        self, mock_db, mock_current_user
    ):
        from src.api.v1.assets.custom_fields import update_asset_custom_field_values
        from src.schemas.asset import CustomFieldValueUpdate

        values_update = CustomFieldValueUpdate(
            values=[{"field_name": "field1", "value": "invalid"}]
        )
        with patch("src.api.v1.assets.custom_fields.custom_field_service") as mock_service:
            mock_service.update_asset_field_values_async = AsyncMock(
                side_effect=BusinessValidationError(
                    message="字段值验证失败",
                    field_errors={"custom_fields": ["字段值验证失败"]},
                )
            )
            with pytest.raises(BaseBusinessError) as exc_info:
                await update_asset_custom_field_values(
                    asset_id="asset-123",
                    values_update=values_update,
                    db=mock_db,
                    current_user=mock_current_user,
                )

        assert exc_info.value.status_code == 422


class TestBatchSetCustomFieldValues:
    async def test_batch_set_custom_field_values_success(self, mock_db, mock_current_user):
        from src.api.v1.assets.custom_fields import batch_set_custom_field_values

        updates = [
            {"asset_id": "asset-1", "values": [{"field_name": "f1", "value": "v1"}]},
            {"asset_id": "asset-2", "values": [{"field_name": "f2", "value": "v2"}]},
        ]
        with patch("src.api.v1.assets.custom_fields.custom_field_service") as mock_service:
            mock_service.update_asset_field_values_async = AsyncMock(
                side_effect=[updates[0]["values"], updates[1]["values"]]
            )
            result = await batch_set_custom_field_values(
                updates=updates,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert len(result["results"]) == 2
        assert result["results"][0]["success"] is True
        assert result["results"][1]["success"] is True

    async def test_batch_set_custom_field_values_partial_failure(
        self, mock_db, mock_current_user
    ):
        from src.api.v1.assets.custom_fields import batch_set_custom_field_values

        updates = [
            {"asset_id": "asset-1", "values": [{"field_name": "f1", "value": "v1"}]},
            {"asset_id": "asset-2", "values": [{"field_name": "f2", "value": "v2"}]},
        ]
        with patch("src.api.v1.assets.custom_fields.custom_field_service") as mock_service:
            mock_service.update_asset_field_values_async = AsyncMock(
                side_effect=[updates[0]["values"], Exception("Update failed")]
            )
            result = await batch_set_custom_field_values(
                updates=updates,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert len(result["results"]) == 2
        assert result["results"][0]["success"] is True
        assert result["results"][1]["success"] is False
        assert "error" in result["results"][1]

    async def test_batch_set_custom_field_values_skip_missing_asset_id(
        self, mock_db, mock_current_user
    ):
        from src.api.v1.assets.custom_fields import batch_set_custom_field_values

        updates = [
            {"asset_id": "asset-1", "values": [{"field_name": "f1", "value": "v1"}]},
            {"values": [{"field_name": "f2", "value": "v2"}]},
            {"asset_id": "asset-3", "values": [{"field_name": "f3", "value": "v3"}]},
        ]
        with patch("src.api.v1.assets.custom_fields.custom_field_service") as mock_service:
            mock_service.update_asset_field_values_async = AsyncMock(
                side_effect=[updates[0]["values"], updates[2]["values"]]
            )
            result = await batch_set_custom_field_values(
                updates=updates,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert len(result["results"]) == 2
        assert {item["asset_id"] for item in result["results"]} == {"asset-1", "asset-3"}
