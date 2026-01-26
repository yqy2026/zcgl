import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from src.services.common_dictionary_service import common_dictionary_service
from src.schemas.dictionary import SimpleDictionaryCreate, DictionaryOptionCreate, DictionaryValueCreate
from src.core.exception_handler import BaseBusinessError

class TestCommonDictionaryService:
    @pytest.fixture
    def mock_db(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def mock_enum_type_crud(self):
        with patch("src.services.common_dictionary_service.get_enum_field_type_crud") as mock:
            yield mock.return_value

    @pytest.fixture
    def mock_enum_value_crud(self):
        with patch("src.services.common_dictionary_service.get_enum_field_value_crud") as mock:
            yield mock.return_value

    def test_get_combined_options_from_enum(self, mock_db, mock_enum_type_crud, mock_enum_value_crud):
        """Test getting options from enum field"""
        # Setup mock return values
        mock_type = MagicMock()
        mock_type.id = 1
        mock_enum_type_crud.get_by_code.return_value = mock_type

        mock_value = MagicMock()
        mock_value.label = "Test Label"
        mock_value.value = "test_value"
        mock_value.code = "TEST"
        mock_value.sort_order = 1
        mock_value.color = "blue"
        mock_value.icon = "user"
        mock_enum_value_crud.get_by_type.return_value = [mock_value]

        # Call service
        result = common_dictionary_service.get_combined_options(mock_db, "test_type")

        # Verify results
        assert len(result) == 1
        assert result[0].label == "Test Label"
        assert result[0].value == "test_value"
        assert result[0].code == "TEST"
        mock_enum_type_crud.get_by_code.assert_called_with("test_type")
        mock_enum_value_crud.get_by_type.assert_called()

    def test_quick_create_enum_dictionary_success(self, mock_db, mock_enum_type_crud, mock_enum_value_crud):
        """Test successful dictionary creation"""
        # Setup mocks
        mock_enum_type_crud.get_by_code.return_value = None  # Not existing

        mock_created_type = MagicMock()
        mock_created_type.id = 1
        mock_enum_type_crud.create.return_value = mock_created_type

        mock_created_value = MagicMock()
        mock_enum_value_crud.create.return_value = mock_created_value

        # Input data
        data = SimpleDictionaryCreate(
            options=[
                DictionaryOptionCreate(label="Option 1", value="opt1")
            ],
            description="Test Dictionary"
        )

        # Call service
        result = common_dictionary_service.quick_create_enum_dictionary(
            mock_db, "test_new_dict", data, "admin"
        )

        # Verify
        assert result["type_id"] == "1"
        assert result["values_count"] == 1
        mock_enum_type_crud.create.assert_called_once()
        mock_enum_value_crud.create.assert_called_once()

    def test_quick_create_conflict(self, mock_db, mock_enum_type_crud):
        """Test creation when dictionary already exists"""
        mock_enum_type_crud.get_by_code.return_value = MagicMock() # Existing

        data = SimpleDictionaryCreate(options=[])

        with pytest.raises(BaseBusinessError) as exc:
            common_dictionary_service.quick_create_enum_dictionary(
                mock_db, "existing_dict", data, "admin"
            )

        assert exc.value.status_code == 409

    def test_add_dictionary_value_success(self, mock_db, mock_enum_type_crud, mock_enum_value_crud):
        """Test adding a value to existing dictionary"""
        mock_type = MagicMock()
        mock_type.id = 1
        mock_enum_type_crud.get_by_code.return_value = mock_type

        mock_enum_value_crud.get_by_type_and_value.return_value = None # Not existing value

        mock_created = MagicMock()
        mock_created.id = 100
        mock_enum_value_crud.create.return_value = mock_created

        value_data = DictionaryValueCreate(label="New Val", value="new_val")

        result = common_dictionary_service.add_dictionary_value(
            mock_db, "test_dict", value_data, "admin"
        )

        assert result["value_id"] == "100"
        mock_enum_value_crud.create.assert_called_once()

    def test_delete_dictionary_type(self, mock_db, mock_enum_type_crud):
        """Test deleting dictionary type"""
        mock_type = MagicMock()
        mock_type.id = 1
        mock_enum_type_crud.get_by_code.return_value = mock_type

        result = common_dictionary_service.delete_dictionary_type(mock_db, "test_dict", "admin")

        assert "成功" in result["message"]
        mock_enum_type_crud.delete.assert_called_with("1", deleted_by="admin")
