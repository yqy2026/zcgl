from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import OperationNotAllowedError
from src.models.ownership import Ownership
from src.schemas.ownership import OwnershipCreate, OwnershipUpdate
from src.services.ownership.service import OwnershipService

pytestmark = pytest.mark.asyncio

# Constants
TEST_OWNERSHIP_ID = "ownership_123"
TEST_OWNERSHIP_NAME = "Test Ownership"


@pytest.fixture
def service():
    return OwnershipService()


class TestOwnershipService:
    async def test_generate_ownership_code(self, service, mock_db):
        result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = []
        result.scalars.return_value = scalars
        mock_db.execute = AsyncMock(return_value=result)

        from src.services.ownership import service as service_module

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                service_module.ownership_crud,
                "get_by_code",
                AsyncMock(return_value=None),
            )
            code = await service.generate_ownership_code(mock_db)

        assert code.startswith("OW")
        assert len(code) == 9  # OW + YYMM + 001

    async def test_create_ownership(self, service, mock_db):
        create_in = OwnershipCreate(name=TEST_OWNERSHIP_NAME, short_name="TO")
        expected = MagicMock(spec=Ownership)
        expected.name = TEST_OWNERSHIP_NAME
        expected.code = "OW2401001"

        from src.services.ownership import service as service_module

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                service_module.ownership_crud,
                "get_by_name",
                AsyncMock(return_value=None),
            )
            monkeypatch.setattr(
                service,
                "generate_ownership_code",
                AsyncMock(return_value="OW2401001"),
            )
            create_mock = AsyncMock(return_value=expected)
            monkeypatch.setattr(service_module.ownership_crud, "create", create_mock)

            result = await service.create_ownership(mock_db, obj_in=create_in)

        assert result.name == TEST_OWNERSHIP_NAME
        assert result.code == "OW2401001"
        create_mock.assert_awaited_once()
        create_payload = create_mock.await_args.kwargs["obj_in"]
        assert create_payload["code"] == "OW2401001"

    async def test_update_ownership(self, service, mock_db):
        db_obj = Ownership(id=TEST_OWNERSHIP_ID, name=TEST_OWNERSHIP_NAME, code="OW2501001")
        update_in = OwnershipUpdate(name="New Name")
        expected = MagicMock(spec=Ownership)
        expected.name = "New Name"

        from src.services.ownership import service as service_module

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                service_module.ownership_crud,
                "get_by_name",
                AsyncMock(return_value=None),
            )
            update_mock = AsyncMock(return_value=expected)
            monkeypatch.setattr(service_module.ownership_crud, "update", update_mock)

            result = await service.update_ownership(
                mock_db, db_obj=db_obj, obj_in=update_in
            )

        assert result.name == "New Name"
        update_mock.assert_awaited_once()

    async def test_delete_ownership_with_assets(self, service, mock_db):
        db_obj = Ownership(id=TEST_OWNERSHIP_ID, name=TEST_OWNERSHIP_NAME, code="OW2501001")

        execute_result = MagicMock()
        execute_result.scalar.return_value = 5
        mock_db.execute = AsyncMock(return_value=execute_result)

        from src.services.ownership import service as service_module

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                service_module.ownership_crud,
                "get",
                AsyncMock(return_value=db_obj),
            )

            with pytest.raises(OperationNotAllowedError) as excinfo:
                await service.delete_ownership(mock_db, id=TEST_OWNERSHIP_ID)

        assert "关联资产" in str(excinfo.value)

    async def test_delete_ownership_success(self, service, mock_db):
        db_obj = Ownership(id=TEST_OWNERSHIP_ID, name=TEST_OWNERSHIP_NAME, code="OW2501001")

        execute_result = MagicMock()
        execute_result.scalar.return_value = 0
        mock_db.execute = AsyncMock(return_value=execute_result)

        from src.services.ownership import service as service_module

        remove_mock = AsyncMock(return_value=db_obj)
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                service_module.ownership_crud,
                "get",
                AsyncMock(return_value=db_obj),
            )
            monkeypatch.setattr(service_module.ownership_crud, "remove", remove_mock)

            result = await service.delete_ownership(mock_db, id=TEST_OWNERSHIP_ID)

        assert result == db_obj
        remove_mock.assert_awaited_once_with(mock_db, id=TEST_OWNERSHIP_ID)

    async def test_toggle_status(self, service, mock_db):
        db_obj = Ownership(
            id=TEST_OWNERSHIP_ID,
            name=TEST_OWNERSHIP_NAME,
            code="OW2501001",
            is_active=True,
        )

        updated = MagicMock(spec=Ownership)
        updated.is_active = False

        from src.services.ownership import service as service_module

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                service_module.ownership_crud,
                "get",
                AsyncMock(return_value=db_obj),
            )
            update_mock = AsyncMock(return_value=updated)
            monkeypatch.setattr(service, "update_ownership", update_mock)

            result = await service.toggle_status(mock_db, id=TEST_OWNERSHIP_ID)

        assert result.is_active is False
        update_mock.assert_awaited_once()
        obj_in = update_mock.await_args.kwargs["obj_in"]
        assert isinstance(obj_in, OwnershipUpdate)
        assert obj_in.is_active is False
