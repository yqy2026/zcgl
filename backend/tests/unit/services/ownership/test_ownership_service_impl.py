"""
权属方服务单元测试（异步）
"""

import inspect
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import (
    BusinessValidationError,
    DuplicateResourceError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from src.models.ownership import Ownership
from src.schemas.ownership import OwnershipCreate, OwnershipUpdate
from src.services.ownership.service import OwnershipService

pytestmark = pytest.mark.asyncio


def test_ownership_service_module_should_not_use_datetime_utcnow() -> None:
    """权属方服务模块不应直接调用 datetime.utcnow。"""
    from src.services.ownership import service as ownership_service_module

    module_source = inspect.getsource(ownership_service_module)
    assert "datetime.utcnow(" not in module_source


def _result_with_scalars(values: list[object]) -> MagicMock:
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    scalars.first.return_value = values[0] if values else None
    result.scalars.return_value = scalars
    return result


def _result_with_one(value: tuple[object, object]) -> MagicMock:
    result = MagicMock()
    result.one.return_value = value
    return result


def _result_with_scalar(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar.return_value = value
    return result


@pytest.fixture
def ownership_service() -> OwnershipService:
    return OwnershipService()


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_ownership() -> MagicMock:
    ownership = MagicMock(spec=Ownership)
    ownership.id = "ownership_123"
    ownership.name = "测试权属方"
    ownership.code = "OW2501001"
    ownership.short_name = "测试"
    ownership.is_active = True
    ownership.created_at = datetime.now(UTC)
    ownership.updated_at = datetime.now(UTC)
    return ownership


class TestGenerateOwnershipCode:
    async def test_generate_code_first_of_month(
        self, ownership_service: OwnershipService, mock_db: AsyncMock
    ):
        mock_db.execute.return_value = _result_with_scalars([])

        with patch(
            "src.crud.ownership.ownership.get_by_code", new_callable=AsyncMock
        ) as mock_get_by_code:
            mock_get_by_code.return_value = None
            code = await ownership_service.generate_ownership_code(mock_db)

        assert code.startswith("OW")
        assert len(code) == 9
        assert code.endswith("001")
        mock_get_by_code.assert_awaited_once()

    async def test_generate_code_sequence_increment(
        self, ownership_service: OwnershipService, mock_db: AsyncMock
    ):
        mock_db.execute.return_value = _result_with_scalars(["OW2501002"])

        with patch(
            "src.crud.ownership.ownership.get_by_code", new_callable=AsyncMock
        ) as mock_get_by_code:
            mock_get_by_code.return_value = None
            code = await ownership_service.generate_ownership_code(mock_db)

        assert code.endswith("003")

    async def test_generate_code_collision_handling(
        self, ownership_service: OwnershipService, mock_db: AsyncMock
    ):
        mock_db.execute.return_value = _result_with_scalars(["OW2501001"])

        with patch(
            "src.crud.ownership.ownership.get_by_code", new_callable=AsyncMock
        ) as mock_get_by_code:
            mock_get_by_code.side_effect = [MagicMock(), None]
            code = await ownership_service.generate_ownership_code(mock_db)

        assert code.endswith("003")
        assert mock_get_by_code.await_count == 2

    async def test_generate_code_ignores_old_format(
        self, ownership_service: OwnershipService, mock_db: AsyncMock
    ):
        mock_db.execute.return_value = _result_with_scalars(["OLD001", "OW2501001"])

        with patch(
            "src.crud.ownership.ownership.get_by_code", new_callable=AsyncMock
        ) as mock_get_by_code:
            mock_get_by_code.return_value = None
            code = await ownership_service.generate_ownership_code(mock_db)

        assert code.endswith("002")


class TestCreateOwnership:
    async def test_create_ownership_success(
        self, ownership_service: OwnershipService, mock_db: AsyncMock, mock_ownership: MagicMock
    ):
        obj_in = OwnershipCreate(name="新权属方", short_name="新")

        with patch(
            "src.crud.ownership.ownership.get_by_name", new_callable=AsyncMock
        ) as mock_get_by_name, patch.object(
            ownership_service, "generate_ownership_code", new_callable=AsyncMock
        ) as mock_generate_code, patch(
            "src.crud.ownership.ownership.create", new_callable=AsyncMock
        ) as mock_create:
            mock_get_by_name.return_value = None
            mock_generate_code.return_value = "OW2501001"
            mock_create.return_value = mock_ownership

            result = await ownership_service.create_ownership(mock_db, obj_in=obj_in)

        assert result is mock_ownership
        mock_create.assert_awaited_once()
        create_kwargs = mock_create.await_args.kwargs
        assert create_kwargs["obj_in"]["name"] == "新权属方"
        assert create_kwargs["obj_in"]["code"] == "OW2501001"

    async def test_create_ownership_duplicate_name(
        self, ownership_service: OwnershipService, mock_db: AsyncMock
    ):
        obj_in = OwnershipCreate(name="已存在权属方", short_name="已存在")

        with patch(
            "src.crud.ownership.ownership.get_by_name", new_callable=AsyncMock
        ) as mock_get_by_name:
            mock_get_by_name.return_value = MagicMock(spec=Ownership)

            with pytest.raises(DuplicateResourceError, match="权属方已存在"):
                await ownership_service.create_ownership(mock_db, obj_in=obj_in)


class TestUpdateOwnership:
    async def test_update_ownership_basic(
        self, ownership_service: OwnershipService, mock_db: AsyncMock, mock_ownership: MagicMock
    ):
        obj_in = OwnershipUpdate(name="更新后的名称")

        with patch(
            "src.crud.ownership.ownership.get_by_name", new_callable=AsyncMock
        ) as mock_get_by_name, patch(
            "src.crud.ownership.ownership.update", new_callable=AsyncMock
        ) as mock_update:
            mock_get_by_name.return_value = None
            mock_update.return_value = mock_ownership

            result = await ownership_service.update_ownership(
                mock_db,
                db_obj=mock_ownership,
                obj_in=obj_in,
            )

        assert result is mock_ownership
        update_kwargs = mock_update.await_args.kwargs
        assert update_kwargs["obj_in"]["name"] == "更新后的名称"
        assert isinstance(update_kwargs["obj_in"]["updated_at"], datetime)

    async def test_update_ownership_name_conflict(
        self, ownership_service: OwnershipService, mock_db: AsyncMock, mock_ownership: MagicMock
    ):
        obj_in = OwnershipUpdate(name="已存在名称")

        existing = MagicMock(spec=Ownership)
        existing.id = "ownership_other"

        with patch(
            "src.crud.ownership.ownership.get_by_name", new_callable=AsyncMock
        ) as mock_get_by_name:
            mock_get_by_name.return_value = existing

            with pytest.raises(DuplicateResourceError, match="权属方已存在"):
                await ownership_service.update_ownership(
                    mock_db,
                    db_obj=mock_ownership,
                    obj_in=obj_in,
                )

    async def test_update_ownership_same_name_allowed(
        self, ownership_service: OwnershipService, mock_db: AsyncMock, mock_ownership: MagicMock
    ):
        obj_in = OwnershipUpdate(name=mock_ownership.name)

        with patch(
            "src.crud.ownership.ownership.get_by_name", new_callable=AsyncMock
        ) as mock_get_by_name, patch(
            "src.crud.ownership.ownership.update", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = mock_ownership
            await ownership_service.update_ownership(
                mock_db,
                db_obj=mock_ownership,
                obj_in=obj_in,
            )

        mock_get_by_name.assert_not_called()
        mock_update.assert_awaited_once()

    async def test_update_ownership_by_id_not_found(
        self, ownership_service: OwnershipService, mock_db: AsyncMock
    ):
        with patch.object(
            ownership_service, "get_ownership", new_callable=AsyncMock
        ) as mock_get_ownership:
            mock_get_ownership.return_value = None

            with pytest.raises(ResourceNotFoundError, match="权属方"):
                await ownership_service.update_ownership_by_id(
                    mock_db,
                    ownership_id="not-found",
                    obj_in=OwnershipUpdate(name="x"),
                )


class TestGetStatistics:
    async def test_get_statistics_basic(
        self, ownership_service: OwnershipService, mock_db: AsyncMock, mock_ownership: MagicMock
    ):
        mock_db.execute.side_effect = [
            _result_with_one((10, 7)),
            _result_with_scalars([mock_ownership]),
        ]

        result = await ownership_service.get_statistics(mock_db)

        assert result["total_count"] == 10
        assert result["active_count"] == 7
        assert result["inactive_count"] == 3
        assert len(result["recent_created"]) == 1

    async def test_get_statistics_empty(
        self, ownership_service: OwnershipService, mock_db: AsyncMock
    ):
        mock_db.execute.side_effect = [
            _result_with_one((0, None)),
            _result_with_scalars([]),
        ]

        result = await ownership_service.get_statistics(mock_db)

        assert result["total_count"] == 0
        assert result["active_count"] == 0
        assert result["inactive_count"] == 0
        assert result["recent_created"] == []


class TestUpdateRelatedProjects:
    async def test_update_projects_success(
        self, ownership_service: OwnershipService, mock_db: AsyncMock
    ):
        with patch(
            "src.crud.ownership.ownership.get", new_callable=AsyncMock
        ) as mock_get_ownership:
            mock_get_ownership.return_value = MagicMock(spec=Ownership)
            mock_db.execute.side_effect = [
                _result_with_scalars(["project_1", "project_2"]),
                MagicMock(),
            ]

            await ownership_service.update_related_projects(
                mock_db,
                ownership_id="ownership_123",
                project_ids=["project_1", "project_2"],
            )

        assert mock_db.add.call_count == 2
        mock_db.commit.assert_awaited_once()

    async def test_update_projects_ownership_not_found(
        self, ownership_service: OwnershipService, mock_db: AsyncMock
    ):
        with patch(
            "src.crud.ownership.ownership.get", new_callable=AsyncMock
        ) as mock_get_ownership:
            mock_get_ownership.return_value = None

            with pytest.raises(ResourceNotFoundError, match="权属方"):
                await ownership_service.update_related_projects(
                    mock_db,
                    ownership_id="not-found",
                    project_ids=["project_1"],
                )

    async def test_update_projects_invalid_project_id(
        self, ownership_service: OwnershipService, mock_db: AsyncMock
    ):
        with patch(
            "src.crud.ownership.ownership.get", new_callable=AsyncMock
        ) as mock_get_ownership:
            mock_get_ownership.return_value = MagicMock(spec=Ownership)
            mock_db.execute.side_effect = [_result_with_scalars(["project_1"])]

            with pytest.raises(BusinessValidationError, match="以下项目ID不存在"):
                await ownership_service.update_related_projects(
                    mock_db,
                    ownership_id="ownership_123",
                    project_ids=["project_1", "project_2"],
                )


class TestCountsAndDelete:
    async def test_get_project_count(
        self, ownership_service: OwnershipService, mock_db: AsyncMock
    ):
        mock_db.execute.return_value = _result_with_scalar(5)

        result = await ownership_service.get_project_count(mock_db, "ownership_123")

        assert result == 5

    async def test_get_asset_count(
        self, ownership_service: OwnershipService, mock_db: AsyncMock
    ):
        mock_db.execute.return_value = _result_with_scalar(10)

        result = await ownership_service.get_asset_count(mock_db, "ownership_123")

        assert result == 10

    async def test_delete_ownership_success(
        self, ownership_service: OwnershipService, mock_db: AsyncMock, mock_ownership: MagicMock
    ):
        with patch(
            "src.crud.ownership.ownership.get", new_callable=AsyncMock
        ) as mock_get_ownership, patch(
            "src.crud.ownership.ownership.remove", new_callable=AsyncMock
        ) as mock_remove:
            mock_get_ownership.return_value = mock_ownership
            mock_db.execute.return_value = _result_with_scalar(0)

            result = await ownership_service.delete_ownership(
                mock_db,
                id="ownership_123",
            )

        assert result is mock_ownership
        mock_remove.assert_awaited_once_with(mock_db, id="ownership_123")

    async def test_delete_ownership_not_found(
        self, ownership_service: OwnershipService, mock_db: AsyncMock
    ):
        with patch(
            "src.crud.ownership.ownership.get", new_callable=AsyncMock
        ) as mock_get_ownership:
            mock_get_ownership.return_value = None

            with pytest.raises(ResourceNotFoundError, match="权属方"):
                await ownership_service.delete_ownership(mock_db, id="not-found")

    async def test_delete_ownership_with_assets_fails(
        self, ownership_service: OwnershipService, mock_db: AsyncMock, mock_ownership: MagicMock
    ):
        with patch(
            "src.crud.ownership.ownership.get", new_callable=AsyncMock
        ) as mock_get_ownership:
            mock_get_ownership.return_value = mock_ownership
            mock_db.execute.return_value = _result_with_scalar(2)

            with pytest.raises(OperationNotAllowedError, match="关联资产"):
                await ownership_service.delete_ownership(mock_db, id="ownership_123")


class TestToggleStatus:
    async def test_toggle_status_success(
        self, ownership_service: OwnershipService, mock_db: AsyncMock, mock_ownership: MagicMock
    ):
        mock_ownership.is_active = True

        with patch(
            "src.crud.ownership.ownership.get", new_callable=AsyncMock
        ) as mock_get_ownership, patch.object(
            ownership_service, "update_ownership", new_callable=AsyncMock
        ) as mock_update_ownership:
            mock_get_ownership.return_value = mock_ownership
            mock_update_ownership.return_value = mock_ownership

            await ownership_service.toggle_status(mock_db, id="ownership_123")

        update_kwargs = mock_update_ownership.await_args.kwargs
        update_in: OwnershipUpdate = update_kwargs["obj_in"]
        assert update_in.is_active is False

    async def test_toggle_status_not_found(
        self, ownership_service: OwnershipService, mock_db: AsyncMock
    ):
        with patch(
            "src.crud.ownership.ownership.get", new_callable=AsyncMock
        ) as mock_get_ownership:
            mock_get_ownership.return_value = None

            with pytest.raises(ResourceNotFoundError, match="权属方"):
                await ownership_service.toggle_status(mock_db, id="not-found")
