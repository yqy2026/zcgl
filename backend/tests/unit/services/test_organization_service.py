from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import OperationNotAllowedError
from src.models.organization import Organization
from src.schemas.organization import OrganizationCreate, OrganizationUpdate
from src.services.organization.service import OrganizationService

TEST_ORG_ID = "org_123"
TEST_PARENT_ID = "org_root"


@pytest.fixture
def service():
    return OrganizationService()


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


class TestOrganizationService:
    @pytest.mark.asyncio
    async def test_create_organization_root(self, service, mock_db):
        obj_in = OrganizationCreate(
            name="Root Org",
            code="ROOT",
            type="department",
            status="active",
            sort_order=1,
        )

        result = await service.create_organization(mock_db, obj_in=obj_in)

        assert result.level == 1
        assert result.path.startswith("/")
        mock_db.add.assert_called()
        assert mock_db.commit.await_count >= 1

    @pytest.mark.asyncio
    async def test_create_organization_child(self, service, mock_db):
        obj_in = OrganizationCreate(
            name="Child Org",
            code="CHILD",
            type="department",
            status="active",
            parent_id=TEST_PARENT_ID,
        )

        # Mock parent
        parent = Organization(
            id=TEST_PARENT_ID, name="Root", level=1, path=f"/{TEST_PARENT_ID}"
        )

        with patch(
            "src.services.organization.service.organization_crud.get_async",
            new=AsyncMock(return_value=parent),
        ):
            result = await service.create_organization(mock_db, obj_in=obj_in)

            assert result.level == 2
            mock_db.add.assert_called()

    @pytest.mark.asyncio
    async def test_update_organization(self, service, mock_db):
        db_obj = Organization(id=TEST_ORG_ID, name="Old Name")
        obj_in = OrganizationUpdate(name="New Name")

        with patch(
            "src.services.organization.service.organization_crud.get_async",
            new=AsyncMock(return_value=db_obj),
        ):
            result = await service.update_organization(
                mock_db, org_id=TEST_ORG_ID, obj_in=obj_in
            )

            assert result.name == "New Name"
            assert mock_db.commit.await_count >= 1

    @pytest.mark.asyncio
    async def test_move_organization_cycle(self, service, mock_db):
        # Move org to under itself or its child
        db_obj = Organization(id=TEST_ORG_ID, name="Moving Org")
        obj_in = OrganizationUpdate(parent_id="child_id")

        with patch(
            "src.services.organization.service.organization_crud.get_async",
            new=AsyncMock(return_value=db_obj),
        ):
            # Mock _would_create_cycle to return True
            service._would_create_cycle = AsyncMock(return_value=True)

            with pytest.raises(OperationNotAllowedError) as excinfo:
                await service.update_organization(
                    mock_db, org_id=TEST_ORG_ID, obj_in=obj_in
                )

            assert "不能将组织移动到其子组织下" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_delete_organization_with_children(self, service, mock_db):
        db_obj = Organization(id=TEST_ORG_ID)

        with patch(
            "src.services.organization.service.organization_crud.get_async",
            new=AsyncMock(return_value=db_obj),
        ):
            with patch(
                "src.services.organization.service.organization_crud.get_children_async",
                new=AsyncMock(return_value=[MagicMock()]),
            ):
                # Returns children

                with pytest.raises(OperationNotAllowedError) as excinfo:
                    await service.delete_organization(mock_db, org_id=TEST_ORG_ID)

                assert "子组织" in str(excinfo.value)
