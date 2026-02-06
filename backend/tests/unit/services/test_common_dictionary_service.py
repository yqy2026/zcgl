from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import BaseBusinessError
from src.schemas.dictionary import (
    DictionaryOptionCreate,
    DictionaryValueCreate,
    SimpleDictionaryCreate,
)
from src.services.common_dictionary_service import common_dictionary_service

pytestmark = pytest.mark.asyncio


class TestCommonDictionaryService:
    @pytest.fixture
    def mock_db(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.flush = AsyncMock()
        return mock_db

    @pytest.fixture
    def mock_enum_type_crud(self):
        with patch(
            "src.services.common_dictionary_service.get_enum_field_type_crud"
        ) as mock:
            yield mock.return_value

    @pytest.fixture
    def mock_enum_value_crud(self):
        with patch(
            "src.services.common_dictionary_service.get_enum_field_value_crud"
        ) as mock:
            yield mock.return_value

    async def test_get_combined_options_from_enum(
        self, mock_db, mock_enum_type_crud, mock_enum_value_crud
    ):
        """Test getting options from enum field"""
        # Setup mock return values
        mock_type = MagicMock()
        mock_type.id = 1
        mock_enum_type_crud.get_by_code_async = AsyncMock(return_value=mock_type)

        mock_value = MagicMock()
        mock_value.label = "Test Label"
        mock_value.value = "test_value"
        mock_value.code = "TEST"
        mock_value.sort_order = 1
        mock_value.color = "blue"
        mock_value.icon = "user"
        mock_enum_value_crud.get_by_type_async = AsyncMock(return_value=[mock_value])

        # Call service
        result = await common_dictionary_service.get_combined_options_async(
            mock_db, "test_type"
        )

        # Verify results
        assert len(result) == 1
        assert result[0].label == "Test Label"
        assert result[0].value == "test_value"
        assert result[0].code == "TEST"
        mock_enum_type_crud.get_by_code_async.assert_called_with(mock_db, "test_type")
        mock_enum_value_crud.get_by_type_async.assert_called()

    async def test_quick_create_enum_dictionary_success(
        self, mock_db, mock_enum_type_crud, mock_enum_value_crud
    ):
        """Test successful dictionary creation"""
        # Setup mocks
        mock_enum_type_crud.get_by_code_async = AsyncMock(return_value=None)

        mock_created_type = MagicMock()
        mock_created_type.id = 1
        mock_enum_type_crud.create_async = AsyncMock(return_value=mock_created_type)

        mock_created_value = MagicMock()
        mock_enum_value_crud.create_async = AsyncMock(return_value=mock_created_value)

        # Input data
        data = SimpleDictionaryCreate(
            options=[DictionaryOptionCreate(label="Option 1", value="opt1")],
            description="Test Dictionary",
        )

        # Call service
        result = await common_dictionary_service.quick_create_enum_dictionary_async(
            mock_db, "test_new_dict", data, "admin"
        )

        # Verify
        assert result["type_id"] == "1"
        assert result["values_count"] == 1
        mock_enum_type_crud.create_async.assert_called_once()
        mock_enum_value_crud.create_async.assert_called_once()

    async def test_quick_create_conflict(self, mock_db, mock_enum_type_crud):
        """Test creation when dictionary already exists"""
        mock_enum_type_crud.get_by_code_async = AsyncMock(return_value=MagicMock())

        data = SimpleDictionaryCreate(options=[])

        with pytest.raises(BaseBusinessError) as exc:
            await common_dictionary_service.quick_create_enum_dictionary_async(
                mock_db, "existing_dict", data, "admin"
            )

        assert exc.value.status_code == 409

    async def test_add_dictionary_value_success(
        self, mock_db, mock_enum_type_crud, mock_enum_value_crud
    ):
        """Test adding a value to existing dictionary"""
        mock_type = MagicMock()
        mock_type.id = 1
        mock_enum_type_crud.get_by_code_async = AsyncMock(return_value=mock_type)

        mock_enum_value_crud.get_by_type_and_value_async = AsyncMock(return_value=None)

        mock_created = MagicMock()
        mock_created.id = 100
        mock_enum_value_crud.create_async = AsyncMock(return_value=mock_created)

        value_data = DictionaryValueCreate(label="New Val", value="new_val")

        result = await common_dictionary_service.add_dictionary_value_async(
            mock_db, "test_dict", value_data, "admin"
        )

        assert result["value_id"] == "100"
        mock_enum_value_crud.create_async.assert_called_once()

    async def test_delete_dictionary_type(self, mock_db, mock_enum_type_crud):
        """Test deleting dictionary type"""
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        mock_db.flush = AsyncMock()

        mock_type = MagicMock()
        mock_type.id = 1
        mock_enum_type_crud.get_by_code_async = AsyncMock(return_value=mock_type)
        mock_enum_type_crud.delete_async = AsyncMock(return_value=True)

        result = await common_dictionary_service.delete_dictionary_type_async(
            mock_db, "test_dict", "admin"
        )

        assert "成功" in result["message"]
        mock_enum_type_crud.delete_async.assert_called_with(
            mock_db, "1", deleted_by="admin"
        )
