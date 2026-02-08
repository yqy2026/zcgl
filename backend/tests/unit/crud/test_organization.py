from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.base import CRUDBase
from src.crud.organization import CRUDOrganization, organization
from src.models.organization import Organization
from src.schemas.organization import OrganizationCreate, OrganizationUpdate


@dataclass
class _ScalarResult:
    items: list[object] | None = None
    first_item: object | None = None
    scalar_value: object | None = None

    def scalars(self):
        return self

    def all(self):
        return self.items or []

    def first(self):
        return self.first_item

    def scalar(self):
        return self.scalar_value


@pytest.fixture
def crud_instance():
    return CRUDOrganization(Organization)


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def org_sample():
    return Organization(
        id="org-001",
        name="Org One",
        code="ORG001",
        level=1,
        sort_order=0,
        type="department",
        status="active",
        parent_id=None,
        description="Root organization",
        is_deleted=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestInitialization:
    def test_sensitive_fields_empty(self, crud_instance):
        assert crud_instance.sensitive_data_handler.SEARCHABLE_FIELDS == set()


class TestCreateAndUpdate:
    @pytest.mark.asyncio
    async def test_create_async_with_schema(self, crud_instance, mock_db):
        payload = OrganizationCreate(
            name="Org Two",
            code="ORG002",
            level=2,
            sort_order=1,
            parent_id="org-001",
            type="team",
            status="active",
            description="Child",
            created_by="admin",
        )
        created = Organization(id="org-002", name="Org Two", code="ORG002")

        with patch.object(CRUDBase, "create", new=AsyncMock(return_value=created)) as mock_create:
            result = await crud_instance.create_async(mock_db, obj_in=payload)

        assert result is created
        mock_create.assert_awaited_once()
        assert mock_create.call_args.kwargs["db"] is mock_db
        assert mock_create.call_args.kwargs["obj_in"]["name"] == "Org Two"

    @pytest.mark.asyncio
    async def test_create_async_with_dict(self, crud_instance, mock_db):
        payload = {
            "name": "Org Three",
            "code": "ORG003",
            "type": "team",
            "status": "active",
        }
        created = Organization(id="org-003", name="Org Three", code="ORG003")

        with patch.object(CRUDBase, "create", new=AsyncMock(return_value=created)) as mock_create:
            result = await crud_instance.create_async(mock_db, obj_in=payload)

        assert result is created
        assert mock_create.call_args.kwargs["obj_in"]["code"] == "ORG003"

    @pytest.mark.asyncio
    async def test_update_async_encrypts_via_helper(self, crud_instance, mock_db, org_sample):
        update_payload = OrganizationUpdate(name="Org One Updated", status="inactive")
        updated = Organization(id="org-001", name="Org One Updated", code="ORG001")

        with (
            patch.object(
                CRUDBase,
                "update",
                new=AsyncMock(return_value=updated),
            ) as mock_update,
            patch.object(
                crud_instance,
                "_encrypt_update_data",
                wraps=crud_instance._encrypt_update_data,
            ) as mock_encrypt,
        ):
            result = await crud_instance.update_async(
                mock_db,
                db_obj=org_sample,
                obj_in=update_payload,
            )

        assert result is updated
        mock_encrypt.assert_called_once()
        mock_update.assert_awaited_once()
        assert mock_update.call_args.kwargs["db"] is mock_db


class TestGetOperations:
    @pytest.mark.asyncio
    async def test_get_async_decrypts_result(self, crud_instance, mock_db, org_sample):
        with (
            patch.object(CRUDBase, "get", new=AsyncMock(return_value=org_sample)),
            patch.object(
                crud_instance.sensitive_data_handler, "decrypt_data"
            ) as mock_decrypt,
        ):
            result = await crud_instance.get_async(mock_db, id="org-001")

        assert result is org_sample
        mock_decrypt.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_multi_with_filters_async(self, crud_instance, mock_db, org_sample):
        org_two = Organization(id="org-002", name="Org Two", code="ORG002")
        mock_db.execute = AsyncMock(return_value=_ScalarResult(items=[org_sample, org_two]))

        with patch.object(crud_instance.sensitive_data_handler, "decrypt_data") as mock_decrypt:
            result = await crud_instance.get_multi_with_filters_async(
                mock_db, skip=0, limit=10, keyword="Org"
            )

        assert len(result) == 2
        assert mock_decrypt.call_count == 2
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_multi_with_count_async(self, crud_instance, mock_db, org_sample):
        org_two = Organization(id="org-002", name="Org Two", code="ORG002")
        mock_db.execute = AsyncMock(
            side_effect=[
                _ScalarResult(scalar_value=2),
                _ScalarResult(items=[org_sample, org_two]),
            ]
        )

        with patch.object(crud_instance.sensitive_data_handler, "decrypt_data") as mock_decrypt:
            items, total = await crud_instance.get_multi_with_count_async(mock_db, skip=0, limit=10)

        assert total == 2
        assert len(items) == 2
        assert mock_decrypt.call_count == 2
        assert mock_db.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_get_tree_async(self, crud_instance, mock_db, org_sample):
        mock_db.execute = AsyncMock(return_value=_ScalarResult(items=[org_sample]))

        with patch.object(crud_instance.sensitive_data_handler, "decrypt_data") as mock_decrypt:
            result = await crud_instance.get_tree_async(mock_db, parent_id=None)

        assert len(result) == 1
        mock_decrypt.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_children_async_recursive(self, crud_instance, mock_db):
        child = Organization(id="org-010", name="Child", code="C010", parent_id="org-root")
        grandchild = Organization(id="org-011", name="GrandChild", code="C011", parent_id="org-010")

        mock_db.execute = AsyncMock(
            side_effect=[
                _ScalarResult(items=[child]),
                _ScalarResult(items=[grandchild]),
                _ScalarResult(items=[]),
            ]
        )

        with patch.object(crud_instance.sensitive_data_handler, "decrypt_data"):
            result = await crud_instance.get_children_async(
                mock_db,
                parent_id="org-root",
                recursive=True,
            )

        assert [item.id for item in result] == ["org-010", "org-011"]

    @pytest.mark.asyncio
    async def test_get_path_to_root_async(self, crud_instance, mock_db):
        child = Organization(id="org-020", name="Child", code="C020", parent_id="org-021")
        parent = Organization(id="org-021", name="Parent", code="C021", parent_id=None)

        with patch.object(
            crud_instance,
            "get_async",
            new=AsyncMock(side_effect=[child, parent]),
        ):
            result = await crud_instance.get_path_to_root_async(mock_db, org_id="org-020")

        assert [item.id for item in result] == ["org-021", "org-020"]

    @pytest.mark.asyncio
    async def test_search_async_delegates(self, crud_instance, mock_db, org_sample):
        with patch.object(
            crud_instance,
            "get_multi_with_filters_async",
            new=AsyncMock(return_value=[org_sample]),
        ) as mock_query:
            result = await crud_instance.search_async(mock_db, keyword="Org")

        assert len(result) == 1
        mock_query.assert_awaited_once_with(mock_db, skip=0, limit=100, keyword="Org")


class TestGlobalInstance:
    def test_global_instance_available(self):
        assert isinstance(organization, CRUDOrganization)
