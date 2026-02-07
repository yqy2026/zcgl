from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.asyncio

from src.core.exception_handler import DuplicateResourceError
from src.models.system_dictionary import AssetCustomField
from src.schemas.asset import AssetCustomFieldCreate
from src.services.custom_field.service import CustomFieldService

TEST_FIELD_ID = "field_123"


@pytest.fixture
def service():
    return CustomFieldService()


class TestCustomFieldService:
    async def test_create_custom_field_async(self, service, mock_db):
        obj_in = AssetCustomFieldCreate(
            field_name="test_field", display_name="Test Field", field_type="text"
        )

        with patch(
            "src.crud.custom_field.custom_field_crud.get_by_field_name_async",
            new=AsyncMock(return_value=None),
        ):
            with patch("src.crud.custom_field.custom_field_crud.create", new=AsyncMock()) as mock_create:
                mock_create.return_value = AssetCustomField(
                    id=TEST_FIELD_ID, field_name="test_field"
                )

                result = await service.create_custom_field_async(mock_db, obj_in=obj_in)

                assert result.field_name == "test_field"
                mock_create.assert_called()

    async def test_create_custom_field_duplicate(self, service, mock_db):
        obj_in = AssetCustomFieldCreate(
            field_name="test_field", display_name="Test Field", field_type="text"
        )

        with patch(
            "src.crud.custom_field.custom_field_crud.get_by_field_name_async",
            new=AsyncMock(return_value=AssetCustomField()),
        ):
            with pytest.raises(DuplicateResourceError) as excinfo:
                await service.create_custom_field_async(mock_db, obj_in=obj_in)

            assert "已存在" in str(excinfo.value)

    async def test_validate_field_value_text(self, service):
        field = AssetCustomField(field_type="text", display_name="Test")

        # Valid
        is_valid, _ = service.validate_field_value(field, "some text")
        assert is_valid is True

        # Invalid type
        is_valid, msg = service.validate_field_value(field, 123)
        assert is_valid is False
        assert "必须为文本" in msg

    async def test_validate_field_value_number(self, service):
        field = AssetCustomField(field_type="number", display_name="Test")

        # Valid
        is_valid, _ = service.validate_field_value(field, 123)
        assert is_valid is True

        # Invalid type
        is_valid, msg = service.validate_field_value(field, "not number")
        assert is_valid is False
        assert "必须为整数" in msg

    async def test_validate_field_value_required(self, service):
        field = AssetCustomField(
            field_type="text", display_name="Test", is_required=True
        )

        # Invalid empty
        is_valid, msg = service.validate_field_value(field, "")
        assert is_valid is False
        assert "必填" in msg

    async def test_toggle_active_status_async(self, service, mock_db):
        field = AssetCustomField(id=TEST_FIELD_ID, is_active=True)

        with patch("src.crud.custom_field.custom_field_crud.get", new=AsyncMock(return_value=field)):
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            result = await service.toggle_active_status_async(mock_db, id=TEST_FIELD_ID)

            assert result.is_active is False
            mock_db.commit.assert_called()
