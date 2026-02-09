"""
Organization CRUD unit tests（异步接口）。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.organization import CRUDOrganization, organization
from src.models.organization import Organization

pytestmark = pytest.mark.asyncio


@pytest.fixture
def crud_instance() -> CRUDOrganization:
    return CRUDOrganization(Organization)


@pytest.fixture
def sample_organization() -> Organization:
    return Organization(
        id="org_123",
        name="Test Organization",
        code="TEST001",
        level=1,
        sort_order=0,
        type="department",
        status="active",
        phone="13800138000",
        email="test@example.com",
        leader_name="John Doe",
        leader_phone="13900139000",
        parent_id=None,
        description="Test organization",
        is_deleted=False,
    )


@pytest.fixture
def sample_organization_dict() -> dict[str, object]:
    return {
        "name": "New Organization",
        "code": "NEW001",
        "level": 2,
        "sort_order": 1,
        "type": "team",
        "status": "active",
        "phone": "13700137000",
        "email": "new@example.com",
        "leader_name": "Jane Smith",
        "leader_phone": "13600136000",
        "parent_id": "org_123",
        "description": "New test organization",
        "created_by": "admin",
    }


def _mock_execute_result(
    *,
    scalar_value: int | None = None,
    all_values: list[object] | None = None,
) -> MagicMock:
    result = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = [] if all_values is None else all_values
    result.scalars.return_value = scalars_result
    result.scalar.return_value = scalar_value
    return result


class TestCRUDOrganizationInit:
    def test_init_creates_sensitive_data_handler(self, crud_instance: CRUDOrganization):
        assert hasattr(crud_instance, "sensitive_data_handler")
        assert crud_instance.sensitive_data_handler is not None

    def test_sensitive_fields_configured(self, crud_instance: CRUDOrganization):
        handler = crud_instance.sensitive_data_handler
        assert "phone" in handler.SEARCHABLE_FIELDS
        assert "leader_phone" in handler.SEARCHABLE_FIELDS
        assert "emergency_phone" in handler.SEARCHABLE_FIELDS
        assert "id_card" in handler.SEARCHABLE_FIELDS


class TestCRUDOrganizationCreate:
    async def test_create_with_schema_object(
        self,
        mock_db: MagicMock,
        crud_instance: CRUDOrganization,
        sample_organization: Organization,
        sample_organization_dict: dict[str, object],
    ):
        from src.schemas.organization import OrganizationCreate

        obj_in = MagicMock(spec=OrganizationCreate)
        obj_in.model_dump.return_value = sample_organization_dict
        encrypted_data = {"name": "enc-name"}

        with (
            patch.object(
                crud_instance.sensitive_data_handler,
                "encrypt_data",
                return_value=encrypted_data,
            ) as mock_encrypt,
            patch.object(
                crud_instance.__class__.__bases__[0],
                "create",
                new=AsyncMock(return_value=sample_organization),
            ) as mock_parent_create,
        ):
            result = await crud_instance.create_async(mock_db, obj_in=obj_in)

        assert result is sample_organization
        mock_encrypt.assert_called_once_with(sample_organization_dict)
        mock_parent_create.assert_awaited_once_with(
            db=mock_db,
            obj_in=encrypted_data,
        )

    async def test_create_with_dict(
        self,
        mock_db: MagicMock,
        crud_instance: CRUDOrganization,
        sample_organization: Organization,
        sample_organization_dict: dict[str, object],
    ):
        encrypted_data = {"name": "enc-name"}

        with (
            patch.object(
                crud_instance.sensitive_data_handler,
                "encrypt_data",
                return_value=encrypted_data,
            ) as mock_encrypt,
            patch.object(
                crud_instance.__class__.__bases__[0],
                "create",
                new=AsyncMock(return_value=sample_organization),
            ) as mock_parent_create,
        ):
            result = await crud_instance.create_async(mock_db, obj_in=sample_organization_dict)

        assert result is sample_organization
        mock_encrypt.assert_called_once_with(sample_organization_dict)
        mock_parent_create.assert_awaited_once_with(db=mock_db, obj_in=encrypted_data)


class TestCRUDOrganizationGet:
    async def test_get_decrypts_sensitive_fields(
        self,
        mock_db: MagicMock,
        crud_instance: CRUDOrganization,
        sample_organization: Organization,
    ):
        with (
            patch.object(
                crud_instance.__class__.__bases__[0],
                "get",
                new=AsyncMock(return_value=sample_organization),
            ) as mock_parent_get,
            patch.object(
                crud_instance.sensitive_data_handler,
                "decrypt_data",
            ) as mock_decrypt,
        ):
            result = await crud_instance.get_async(mock_db, id="org_123", use_cache=False)

        assert result is sample_organization
        mock_parent_get.assert_awaited_once_with(db=mock_db, id="org_123", use_cache=False)
        mock_decrypt.assert_called_once()

    async def test_get_returns_none_when_not_found(
        self, mock_db: MagicMock, crud_instance: CRUDOrganization
    ):
        with patch.object(
            crud_instance.__class__.__bases__[0],
            "get",
            new=AsyncMock(return_value=None),
        ):
            result = await crud_instance.get_async(mock_db, id="missing")

        assert result is None


class TestCRUDOrganizationUpdate:
    async def test_update_with_schema_object(
        self,
        mock_db: MagicMock,
        crud_instance: CRUDOrganization,
        sample_organization: Organization,
    ):
        from src.schemas.organization import OrganizationUpdate

        obj_in = MagicMock(spec=OrganizationUpdate)
        obj_in.model_dump.return_value = {"name": "Updated Name"}

        with (
            patch.object(
                crud_instance,
                "_encrypt_update_data",
                return_value={"name": "encrypted-name"},
            ) as mock_encrypt,
            patch.object(
                crud_instance.__class__.__bases__[0],
                "update",
                new=AsyncMock(return_value=sample_organization),
            ) as mock_parent_update,
        ):
            result = await crud_instance.update_async(
                mock_db,
                db_obj=sample_organization,
                obj_in=obj_in,
            )

        assert result is sample_organization
        mock_encrypt.assert_called_once_with({"name": "Updated Name"})
        mock_parent_update.assert_awaited_once_with(
            db=mock_db,
            db_obj=sample_organization,
            obj_in={"name": "encrypted-name"},
            commit=True,
        )

    async def test_update_with_dict(
        self,
        mock_db: MagicMock,
        crud_instance: CRUDOrganization,
        sample_organization: Organization,
    ):
        update_data = {"name": "Updated Name", "status": "inactive"}
        encrypted_data = {"name": "enc-updated", "status": "inactive"}

        with (
            patch.object(
                crud_instance,
                "_encrypt_update_data",
                return_value=encrypted_data,
            ) as mock_encrypt,
            patch.object(
                crud_instance.__class__.__bases__[0],
                "update",
                new=AsyncMock(return_value=sample_organization),
            ) as mock_parent_update,
        ):
            await crud_instance.update_async(
                mock_db,
                db_obj=sample_organization,
                obj_in=update_data,
                commit=False,
            )

        mock_encrypt.assert_called_once_with(update_data)
        mock_parent_update.assert_awaited_once_with(
            db=mock_db,
            db_obj=sample_organization,
            obj_in=encrypted_data,
            commit=False,
        )


class TestEncryptUpdateData:
    def test_encrypt_update_data_with_sensitive_fields(
        self, crud_instance: CRUDOrganization
    ):
        update_data = {
            "phone": "13800138000",
            "leader_phone": "13900139000",
            "name": "Updated Name",
        }

        with patch.object(
            crud_instance.sensitive_data_handler,
            "encrypt_field",
            return_value="encrypted_value",
        ) as mock_encrypt_field:
            result = crud_instance._encrypt_update_data(update_data)

        assert mock_encrypt_field.call_count == 2
        assert result["phone"] == "encrypted_value"
        assert result["leader_phone"] == "encrypted_value"
        assert result["name"] == "Updated Name"

    def test_encrypt_update_data_without_sensitive_fields(
        self, crud_instance: CRUDOrganization
    ):
        update_data = {"name": "Updated Name", "status": "inactive"}

        with patch.object(
            crud_instance.sensitive_data_handler,
            "encrypt_field",
        ) as mock_encrypt_field:
            result = crud_instance._encrypt_update_data(update_data)

        mock_encrypt_field.assert_not_called()
        assert result["name"] == "Updated Name"
        assert result["status"] == "inactive"


class TestQueryAsyncMethods:
    async def test_get_multi_with_filters_async(
        self,
        mock_db: MagicMock,
        crud_instance: CRUDOrganization,
        sample_organization: Organization,
    ):
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_result(all_values=[sample_organization])
        )

        with patch.object(
            crud_instance.sensitive_data_handler,
            "decrypt_data",
        ) as mock_decrypt:
            result = await crud_instance.get_multi_with_filters_async(
                mock_db,
                skip=0,
                limit=10,
                parent_id="root",
                keyword="Test",
            )

        assert len(result) == 1
        assert result[0] is sample_organization
        mock_db.execute.assert_awaited_once()
        mock_decrypt.assert_called_once()

    async def test_get_multi_with_count_async(
        self,
        mock_db: MagicMock,
        crud_instance: CRUDOrganization,
        sample_organization: Organization,
    ):
        count_result = _mock_execute_result(scalar_value=1)
        list_result = _mock_execute_result(all_values=[sample_organization])
        mock_db.execute = AsyncMock(side_effect=[count_result, list_result])

        with patch.object(
            crud_instance.sensitive_data_handler,
            "decrypt_data",
        ) as mock_decrypt:
            items, total = await crud_instance.get_multi_with_count_async(
                mock_db,
                filters={"parent_id": "root"},
                search="Test",
                skip=0,
                limit=10,
            )

        assert total == 1
        assert len(items) == 1
        assert items[0] is sample_organization
        assert mock_db.execute.await_count == 2
        mock_decrypt.assert_called_once()

    async def test_get_tree_async(
        self,
        mock_db: MagicMock,
        crud_instance: CRUDOrganization,
        sample_organization: Organization,
    ):
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_result(all_values=[sample_organization])
        )

        with patch.object(
            crud_instance.sensitive_data_handler,
            "decrypt_data",
        ) as mock_decrypt:
            result = await crud_instance.get_tree_async(mock_db, parent_id=None)

        assert len(result) == 1
        assert result[0] is sample_organization
        mock_decrypt.assert_called_once()


class TestGlobalInstance:
    def test_organization_crud_instance_exists(self):
        assert organization is not None
        assert isinstance(organization, CRUDOrganization)
