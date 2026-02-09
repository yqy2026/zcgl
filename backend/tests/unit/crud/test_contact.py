"""
联系人 CRUD 操作单元测试（异步接口）。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.contact import ContactCRUD, contact_crud
from src.models.contact import Contact, ContactType

pytestmark = pytest.mark.asyncio


@pytest.fixture
def crud() -> ContactCRUD:
    return ContactCRUD()


@pytest.fixture
def mock_contact() -> SimpleNamespace:
    return SimpleNamespace(
        id="contact_123",
        entity_type="asset",
        entity_id="asset_123",
        name="张三",
        phone="13800138000",
        office_phone="010-12345678",
        is_primary=True,
        is_active=True,
        contact_type=ContactType.PRIMARY,
    )


def _mock_execute_result(
    *,
    scalar_value: int | None = None,
    first_value: object | None = None,
    all_values: list[object] | None = None,
) -> MagicMock:
    result = MagicMock()
    scalars_result = MagicMock()
    scalars_result.first.return_value = first_value
    scalars_result.all.return_value = [] if all_values is None else all_values
    result.scalars.return_value = scalars_result
    result.scalar.return_value = scalar_value
    return result


class TestGetAsync:
    async def test_get_success(self, crud: ContactCRUD, mock_db: MagicMock, mock_contact):
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_result(first_value=mock_contact)
        )

        with patch.object(crud.sensitive_data_handler, "decrypt_data") as mock_decrypt:
            result = await crud.get_async(mock_db, "contact_123")

        assert result == mock_contact
        mock_db.execute.assert_awaited_once()
        mock_decrypt.assert_called_once()

    async def test_get_not_found(self, crud: ContactCRUD, mock_db: MagicMock):
        mock_db.execute = AsyncMock(return_value=_mock_execute_result(first_value=None))

        result = await crud.get_async(mock_db, "missing")

        assert result is None


class TestGetMultiAsync:
    async def test_get_multi_success(
        self, crud: ContactCRUD, mock_db: MagicMock, mock_contact
    ):
        count_result = _mock_execute_result(scalar_value=1)
        list_result = _mock_execute_result(all_values=[mock_contact])
        mock_db.execute = AsyncMock(side_effect=[count_result, list_result])

        with patch.object(crud.sensitive_data_handler, "decrypt_data") as mock_decrypt:
            contacts, total = await crud.get_multi_async(mock_db, "asset", "asset_123")

        assert total == 1
        assert len(contacts) == 1
        assert contacts[0] == mock_contact
        assert mock_db.execute.await_count == 2
        mock_decrypt.assert_called_once()

    async def test_get_multi_with_pagination(self, crud: ContactCRUD, mock_db: MagicMock):
        count_result = _mock_execute_result(scalar_value=0)
        list_result = _mock_execute_result(all_values=[])
        mock_db.execute = AsyncMock(side_effect=[count_result, list_result])

        contacts, total = await crud.get_multi_async(
            mock_db,
            "asset",
            "asset_123",
            skip=10,
            limit=20,
        )

        assert contacts == []
        assert total == 0
        assert mock_db.execute.await_count == 2


class TestGetPrimaryAsync:
    async def test_get_primary_success(
        self, crud: ContactCRUD, mock_db: MagicMock, mock_contact
    ):
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_result(first_value=mock_contact)
        )

        with patch.object(crud.sensitive_data_handler, "decrypt_data") as mock_decrypt:
            result = await crud.get_primary_async(mock_db, "asset", "asset_123")

        assert result == mock_contact
        mock_decrypt.assert_called_once()

    async def test_get_primary_not_found(self, crud: ContactCRUD, mock_db: MagicMock):
        mock_db.execute = AsyncMock(return_value=_mock_execute_result(first_value=None))

        result = await crud.get_primary_async(mock_db, "asset", "asset_123")

        assert result is None


class TestCreateAsync:
    async def test_create_success(self, crud: ContactCRUD, mock_db: MagicMock):
        contact_data = {
            "entity_type": "asset",
            "entity_id": "asset_123",
            "name": "张三",
            "phone": "13800138000",
            "is_primary": False,
        }
        mock_db.execute = AsyncMock()

        with (
            patch.object(
                crud.sensitive_data_handler,
                "encrypt_data",
                return_value=contact_data.copy(),
            ) as mock_encrypt,
            patch.object(crud.sensitive_data_handler, "decrypt_data") as mock_decrypt,
        ):
            result = await crud.create_async(mock_db, contact_data)

        assert isinstance(result, Contact)
        mock_encrypt.assert_called_once()
        mock_decrypt.assert_called_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()
        mock_db.execute.assert_not_awaited()

    async def test_create_primary_clears_existing_primary(
        self, crud: ContactCRUD, mock_db: MagicMock
    ):
        contact_data = {
            "entity_type": "asset",
            "entity_id": "asset_123",
            "name": "张三",
            "phone": "13800138000",
            "is_primary": True,
        }
        mock_db.execute = AsyncMock(return_value=_mock_execute_result())

        with patch.object(
            crud.sensitive_data_handler,
            "encrypt_data",
            return_value=contact_data.copy(),
        ):
            await crud.create_async(mock_db, contact_data)

        assert mock_db.execute.await_count == 2


class TestUpdateAsync:
    async def test_update_success(self, crud: ContactCRUD, mock_db: MagicMock, mock_contact):
        mock_db.execute = AsyncMock()
        mock_contact.is_primary = True

        with patch.object(crud.sensitive_data_handler, "decrypt_data") as mock_decrypt:
            result = await crud.update_async(mock_db, mock_contact, {"name": "李四"})

        assert result is mock_contact
        assert mock_contact.name == "李四"
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(mock_contact)
        mock_db.execute.assert_not_awaited()
        mock_decrypt.assert_called_once()

    async def test_update_to_primary_clears_existing_primary(
        self, crud: ContactCRUD, mock_db: MagicMock, mock_contact
    ):
        mock_contact.is_primary = False
        mock_db.execute = AsyncMock(return_value=_mock_execute_result())

        await crud.update_async(mock_db, mock_contact, {"is_primary": True})

        mock_db.execute.assert_awaited_once()
        assert mock_contact.is_primary is True


class TestDeleteAsync:
    async def test_delete_success(self, crud: ContactCRUD, mock_db: MagicMock, mock_contact):
        with patch.object(
            crud,
            "get_async",
            new=AsyncMock(return_value=mock_contact),
        ):
            result = await crud.delete_async(mock_db, "contact_123")

        assert result is mock_contact
        assert mock_contact.is_active is False
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(mock_contact)

    async def test_delete_not_found(self, crud: ContactCRUD, mock_db: MagicMock):
        with patch.object(crud, "get_async", new=AsyncMock(return_value=None)):
            result = await crud.delete_async(mock_db, "missing")

        assert result is None
        mock_db.commit.assert_not_awaited()


class TestGetMultiByTypeAsync:
    async def test_get_multi_by_type_success(
        self, crud: ContactCRUD, mock_db: MagicMock, mock_contact
    ):
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_result(all_values=[mock_contact])
        )

        results = await crud.get_multi_by_type_async(
            mock_db, "asset", ["asset_123", "asset_456"]
        )

        assert len(results) == 1
        assert results[0] == mock_contact

    async def test_get_multi_by_type_with_contact_type(
        self, crud: ContactCRUD, mock_db: MagicMock, mock_contact
    ):
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_result(all_values=[mock_contact])
        )

        results = await crud.get_multi_by_type_async(
            mock_db,
            "asset",
            ["asset_123"],
            contact_type=ContactType.PRIMARY,
        )

        assert len(results) == 1
        assert results[0].contact_type == ContactType.PRIMARY


class TestGlobalInstance:
    def test_contact_crud_instance_exists(self):
        assert contact_crud is not None
        assert isinstance(contact_crud, ContactCRUD)
