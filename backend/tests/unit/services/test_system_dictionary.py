from unittest.mock import patch

import pytest

from src.models.asset import SystemDictionary
from src.schemas.asset import SystemDictionaryCreate
from src.services.system_dictionary.service import SystemDictionaryService

TEST_DICT_ID = "dict_123"




@pytest.fixture
def service():
    return SystemDictionaryService()


class TestSystemDictionaryService:
    def test_create_dictionary(self, service, mock_db):
        obj_in = SystemDictionaryCreate(
            dict_type="type1", dict_code="code1", dict_label="Label", dict_value="Value"
        )

        with patch(
            "src.crud.system_dictionary.system_dictionary_crud.get_by_type_and_code",
            return_value=None,
        ):
            with patch(
                "src.crud.system_dictionary.system_dictionary_crud.create"
            ) as mock_create:
                mock_create.return_value = SystemDictionary(
                    id=TEST_DICT_ID, dict_code="code1"
                )

                result = service.create_dictionary(mock_db, obj_in=obj_in)

                assert result.dict_code == "code1"
                mock_create.assert_called()

    def test_create_dictionary_duplicate(self, service, mock_db):
        obj_in = SystemDictionaryCreate(
            dict_type="type1", dict_code="code1", dict_label="Label", dict_value="Value"
        )

        with patch(
            "src.crud.system_dictionary.system_dictionary_crud.get_by_type_and_code",
            return_value=SystemDictionary(),
        ):
            with pytest.raises(ValueError) as excinfo:
                service.create_dictionary(mock_db, obj_in=obj_in)

            assert "已存在" in str(excinfo.value)

    def test_toggle_active_status(self, service, mock_db):
        dict_item = SystemDictionary(id=TEST_DICT_ID, is_active=True)

        with patch(
            "src.crud.system_dictionary.system_dictionary_crud.get",
            return_value=dict_item,
        ):
            result = service.toggle_active_status(mock_db, id=TEST_DICT_ID)

            assert result.is_active is False
            mock_db.commit.assert_called()

    def test_update_sort_orders(self, service, mock_db):
        dict_item = SystemDictionary(id=TEST_DICT_ID, dict_type="type1", sort_order=0)

        with patch(
            "src.crud.system_dictionary.system_dictionary_crud.get",
            return_value=dict_item,
        ):
            sort_data = [{"id": TEST_DICT_ID, "sort_order": 5}]
            result = service.update_sort_orders(
                mock_db, dict_type="type1", sort_data=sort_data
            )

            assert result[0].sort_order == 5
            mock_db.commit.assert_called()
