"""Focused async unit tests for CustomFieldService."""

from unittest.mock import AsyncMock, patch

import pytest

from src.core.exception_handler import (
    BusinessValidationError,
    DuplicateResourceError,
    ResourceNotFoundError,
)
from src.models.system_dictionary import AssetCustomField
from src.schemas.asset import (
    AssetCustomFieldCreate,
    AssetCustomFieldUpdate,
    CustomFieldValueItem,
)
from src.services.custom_field.service import CustomFieldService

pytestmark = pytest.mark.asyncio

TEST_FIELD_ID = "field_123"
TEST_ASSET_ID = "asset_456"


@pytest.fixture
def service():
    return CustomFieldService()


@pytest.fixture
def sample_field():
    return AssetCustomField(
        id=TEST_FIELD_ID,
        field_name="test_field",
        display_name="Test Field",
        field_type="text",
        is_required=False,
        is_active=True,
        sort_order=0,
    )


class TestCreateCustomField:
    async def test_create_custom_field_success(self, service, mock_db):
        obj_in = AssetCustomFieldCreate(
            field_name="new_field",
            display_name="New Field",
            field_type="text",
            is_required=False,
        )

        with patch(
            "src.services.custom_field.service.custom_field_crud.get_by_field_name_async",
            new=AsyncMock(return_value=None),
        ):
            with patch(
                "src.services.custom_field.service.custom_field_crud.create",
                new=AsyncMock(return_value=AssetCustomField(id=TEST_FIELD_ID)),
            ) as mock_create:
                result = await service.create_custom_field_async(mock_db, obj_in=obj_in)

                assert result.id == TEST_FIELD_ID
                mock_create.assert_called_once()

    async def test_create_custom_field_duplicate_name(self, service, mock_db):
        obj_in = AssetCustomFieldCreate(
            field_name="existing_field",
            display_name="Existing Field",
            field_type="text",
        )

        with patch(
            "src.services.custom_field.service.custom_field_crud.get_by_field_name_async",
            new=AsyncMock(return_value=AssetCustomField(id="existing_id")),
        ):
            with pytest.raises(DuplicateResourceError):
                await service.create_custom_field_async(mock_db, obj_in=obj_in)


class TestGlobalResourceBehavior:
    async def test_get_custom_fields_should_not_resolve_party_scope(
        self, service, mock_db
    ):
        with patch(
            "src.services.custom_field.service.custom_field_crud.get_multi_with_filters_async",
            new=AsyncMock(return_value=[]),
        ) as mock_get:
            result = await service.get_custom_fields_async(
                mock_db,
                filters={"field_type": "text"},
            )

        assert result == []
        mock_get.assert_awaited_once_with(
            db=mock_db,
            filters={"field_type": "text"},
        )

    async def test_get_custom_field_should_read_directly_without_party_scope(
        self, service, mock_db, sample_field
    ):
        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            new=AsyncMock(return_value=sample_field),
        ) as mock_get:
            result = await service.get_custom_field_async(
                mock_db,
                field_id=TEST_FIELD_ID,
            )

        assert result == sample_field
        mock_get.assert_awaited_once_with(db=mock_db, id=TEST_FIELD_ID)


class TestUpdateCustomField:
    async def test_update_custom_field_success(self, service, mock_db, sample_field):
        obj_in = AssetCustomFieldUpdate(display_name="Updated Display Name")

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            new=AsyncMock(return_value=sample_field),
        ):
            with patch(
                "src.services.custom_field.service.custom_field_crud.get_by_field_name_async",
                new=AsyncMock(return_value=None),
            ):
                with patch(
                    "src.services.custom_field.service.custom_field_crud.update",
                    new=AsyncMock(return_value=sample_field),
                ) as mock_update:
                    await service.update_custom_field_async(
                        mock_db, id=TEST_FIELD_ID, obj_in=obj_in
                    )
                    mock_update.assert_called_once()

    async def test_update_custom_field_not_found(self, service, mock_db):
        obj_in = AssetCustomFieldUpdate(display_name="Updated Name")
        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(ResourceNotFoundError):
                await service.update_custom_field_async(
                    mock_db, id="missing", obj_in=obj_in
                )


class TestDeleteCustomField:
    async def test_delete_custom_field_success(self, service, mock_db, sample_field):
        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            new=AsyncMock(return_value=sample_field),
        ):
            with patch(
                "src.services.custom_field.service.custom_field_crud.remove",
                new=AsyncMock(return_value=sample_field),
            ) as mock_remove:
                result = await service.delete_custom_field_async(
                    mock_db, id=TEST_FIELD_ID
                )
                assert result == sample_field
                mock_remove.assert_called_once()

    async def test_delete_custom_field_not_found(self, service, mock_db):
        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(ResourceNotFoundError):
                await service.delete_custom_field_async(mock_db, id="missing")


class TestValidateFieldValue:
    async def test_validate_field_value_text(self, service):
        field = AssetCustomField(field_type="text", display_name="Test")
        is_valid, _ = service.validate_field_value(field, "some text")
        assert is_valid is True

        is_valid, msg = service.validate_field_value(field, 123)
        assert is_valid is False
        assert "必须为文本" in msg

    async def test_validate_field_value_required(self, service):
        field = AssetCustomField(
            field_type="text", display_name="Test", is_required=True
        )
        is_valid, msg = service.validate_field_value(field, "")
        assert is_valid is False
        assert "必填" in msg


class TestAssetFieldValues:
    async def test_update_asset_field_values_success(self, service, mock_db, sample_field):
        values = [CustomFieldValueItem(field_name="test_field", value="foo")]

        with patch(
            "src.services.custom_field.service.custom_field_crud.get_multi_by_field_names_async",
            new=AsyncMock(return_value=[sample_field]),
        ) as mock_get_by_names:
            with patch(
                "src.services.custom_field.service.custom_field_crud.get_multi_by_ids_async",
                new=AsyncMock(return_value=[]),
            ):
                result = await service.update_asset_field_values_async(
                    mock_db, asset_id=TEST_ASSET_ID, values=values
                )

                assert result[0]["field_name"] == "test_field"
                mock_get_by_names.assert_awaited_once()

    async def test_update_asset_field_values_by_id_success(
        self, service, mock_db, sample_field
    ):
        values = [{"field_id": TEST_FIELD_ID, "value": "foo"}]
        with patch(
            "src.services.custom_field.service.custom_field_crud.get_multi_by_ids_async",
            new=AsyncMock(return_value=[sample_field]),
        ):
            with patch(
                "src.services.custom_field.service.custom_field_crud.get_multi_by_field_names_async",
                new=AsyncMock(return_value=[]),
            ):
                result = await service.update_asset_field_values_async(
                    mock_db, asset_id=TEST_ASSET_ID, values=values
                )

                assert result[0]["field_id"] == TEST_FIELD_ID

    async def test_update_asset_field_values_validation_error(self, service, mock_db, sample_field):
        sample_field.field_type = "number"
        values = [CustomFieldValueItem(field_name="test_field", value="bad")]

        with patch(
            "src.services.custom_field.service.custom_field_crud.get_multi_by_field_names_async",
            new=AsyncMock(return_value=[sample_field]),
        ):
            with patch(
                "src.services.custom_field.service.custom_field_crud.get_multi_by_ids_async",
                new=AsyncMock(return_value=[]),
            ):
                with pytest.raises(BusinessValidationError):
                    await service.update_asset_field_values_async(
                        mock_db, asset_id=TEST_ASSET_ID, values=values
                    )

    async def test_get_asset_field_values_async(self, service, mock_db):
        expected = [{"field_id": TEST_FIELD_ID, "value": "foo"}]
        with patch(
            "src.services.custom_field.service.custom_field_crud.get_asset_field_values_async",
            new=AsyncMock(return_value=expected),
        ):
            result = await service.get_asset_field_values_async(
                mock_db, asset_id=TEST_ASSET_ID
            )
            assert result == expected


class TestToggleAndSort:
    async def test_toggle_active_status_async(self, service, mock_db, sample_field):
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch(
            "src.services.custom_field.service.custom_field_crud.get",
            new=AsyncMock(return_value=sample_field),
        ):
            result = await service.toggle_active_status_async(
                mock_db, id=TEST_FIELD_ID
            )

            assert result.is_active is False
            mock_db.commit.assert_called_once()

    async def test_update_sort_orders_async(self, service, mock_db, sample_field):
        mock_db.commit = AsyncMock()

        sort_data = [{"id": TEST_FIELD_ID, "sort_order": 5}]
        with patch(
            "src.services.custom_field.service.custom_field_crud.get_multi_by_ids_async",
            new=AsyncMock(return_value=[sample_field]),
        ):
            result = await service.update_sort_orders_async(
                mock_db, sort_data=sort_data
            )

            assert result[0].sort_order == 5
            mock_db.commit.assert_called_once()
