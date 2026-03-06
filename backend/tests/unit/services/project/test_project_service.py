"""
测试项目服务（异步）
"""

import inspect
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from src.constants.business_constants import DataStatusValues
from src.core.exception_handler import (
    DuplicateResourceError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from src.crud.query_builder import PartyFilter
from src.models import Project
from src.schemas.project import ProjectCreate, ProjectSearchRequest, ProjectUpdate
from src.services.project.service import ProjectService

pytestmark = pytest.mark.asyncio


async def test_project_service_module_should_not_use_datetime_utcnow() -> None:
    """项目服务模块不应直接调用 datetime.utcnow。"""
    from src.services.project import service as project_service_module

    module_source = inspect.getsource(project_service_module)
    assert "datetime.utcnow(" not in module_source


@pytest.fixture
def project_service() -> ProjectService:
    return ProjectService()


@pytest.fixture
def mock_project() -> MagicMock:
    project = MagicMock(spec=Project)
    project.id = "project_123"
    project.project_name = "测试项目"
    project.project_code = "PRJ-TEST01-000001"
    project.status = "active"
    project.created_by = "user_123"
    project.created_at = datetime.now()
    return project


class TestCreateProject:
    async def test_create_project_success(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectCreate(project_name="新项目", project_code="PRJ-TEST01-000002", status="planning")

        with patch("src.crud.project.project_crud.get_by_code", new_callable=AsyncMock, return_value=None):
            with patch("src.crud.project.project_crud.create", new_callable=AsyncMock, return_value=mock_project):
                result = await project_service.create_project(mock_db, obj_in=obj_in)

        assert result is not None

    async def test_create_project_auto_generates_code(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectCreate(project_name="新项目", project_code=None, status="planning")

        with patch.object(project_service, "generate_project_code", new_callable=AsyncMock, return_value="PRJ-TEST01-000003"):
            with patch("src.crud.project.project_crud.get_by_code", new_callable=AsyncMock, return_value=None):
                with patch("src.crud.project.project_crud.create", new_callable=AsyncMock, return_value=mock_project):
                    result = await project_service.create_project(mock_db, obj_in=obj_in)

        assert result is not None

    async def test_create_project_duplicate_code(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectCreate(project_name="新项目", project_code="PRJ-TEST01-000001", status="planning")

        with patch("src.crud.project.project_crud.get_by_code", new_callable=AsyncMock, return_value=mock_project):
            with pytest.raises(DuplicateResourceError):
                await project_service.create_project(mock_db, obj_in=obj_in)

    async def test_create_project_with_user(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectCreate(project_name="新项目", project_code="PRJ-TEST01-000002", status="planning")

        with patch("src.crud.project.project_crud.get_by_code", new_callable=AsyncMock, return_value=None):
            with patch("src.crud.project.project_crud.create", new_callable=AsyncMock, return_value=mock_project):
                result = await project_service.create_project(
                    mock_db,
                    obj_in=obj_in,
                    created_by="user_123",
                )

        assert result is not None

    async def test_create_project_should_not_touch_relation_table_when_party_relations_provided(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectCreate(
            project_name="新项目",
            project_code="PRJ-TEST01-000010",
            status="planning",
            party_relations=[
                {
                    "party_id": "ownership-001",
                    "relation_type": "owner",
                    "is_primary": True,
                    "is_active": True,
                }
            ],
        )

        mock_db.add.reset_mock()
        mock_db.execute.reset_mock()

        with patch(
            "src.crud.project.project_crud.get_by_code",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch(
                "src.crud.project.project_crud.create",
                new_callable=AsyncMock,
                return_value=mock_project,
            ):
                await project_service.create_project(
                    mock_db,
                    obj_in=obj_in,
                    created_by="user_123",
                )

            mock_db.execute.assert_not_awaited()
            mock_db.add.assert_not_called()

    async def test_create_project_should_not_touch_relation_table_when_party_relations_missing(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectCreate(
            project_name="新项目",
            project_code="PRJ-TEST01-000011",
            status="planning",
        )

        mock_db.add.reset_mock()
        mock_db.execute.reset_mock()

        with patch(
            "src.crud.project.project_crud.get_by_code",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch(
                "src.crud.project.project_crud.create",
                new_callable=AsyncMock,
                return_value=mock_project,
            ):
                await project_service.create_project(
                    mock_db,
                    obj_in=obj_in,
                    created_by="user_123",
                )

        mock_db.execute.assert_not_awaited()
        mock_db.add.assert_not_called()


class TestUpdateProject:
    async def test_update_project_basic(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectUpdate(project_name="更新后的项目名称")

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            with patch("src.crud.project.project_crud.update", new_callable=AsyncMock, return_value=mock_project):
                result = await project_service.update_project(
                    mock_db, project_id="project_123", obj_in=obj_in
                )

        assert result is not None

    async def test_update_project_not_found(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        obj_in = ProjectUpdate(project_name="新名称")

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=None):
            with pytest.raises(ResourceNotFoundError):
                await project_service.update_project(
                    mock_db, project_id="nonexistent", obj_in=obj_in
                )

    async def test_update_project_with_user(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectUpdate(status="active")

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            with patch("src.crud.project.project_crud.update", new_callable=AsyncMock, return_value=mock_project):
                result = await project_service.update_project(
                    mock_db,
                    project_id="project_123",
                    obj_in=obj_in,
                    updated_by="user_123",
                )

        assert result is not None

    async def test_update_project_should_not_touch_relation_table_when_party_relations_provided(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectUpdate(
            status="active",
            party_relations=[
                {
                    "party_id": "ownership-001",
                    "relation_type": "owner",
                    "is_active": True,
                },
                {
                    "party_id": "ownership-002",
                    "relation_type": "owner",
                    "is_active": True,
                },
                {
                    "party_id": "ownership-003",
                    "relation_type": "owner",
                    "is_active": False,
                },
                {
                    "party_id": "ownership-001",
                    "relation_type": "owner",
                    "is_active": False,
                },
            ],
        )

        mock_db.add.reset_mock()
        mock_db.execute.reset_mock()

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            with patch("src.crud.project.project_crud.update", new_callable=AsyncMock, return_value=mock_project):
                result = await project_service.update_project(
                    mock_db,
                    project_id="project_123",
                    obj_in=obj_in,
                    updated_by="user_123",
                )

        assert result is mock_project
        mock_db.execute.assert_not_awaited()
        mock_db.add.assert_not_called()

    async def test_update_project_should_not_replace_party_relations_when_not_provided(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectUpdate(status="active")

        mock_db.add.reset_mock()
        mock_db.execute.reset_mock()

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            with patch("src.crud.project.project_crud.update", new_callable=AsyncMock, return_value=mock_project):
                await project_service.update_project(
                    mock_db,
                    project_id="project_123",
                    obj_in=obj_in,
                    updated_by="user_123",
                )

        mock_db.execute.assert_not_awaited()
        mock_db.add.assert_not_called()

    async def test_update_project_should_not_touch_relation_table_when_party_relations_empty(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectUpdate(status="active", party_relations=[])

        mock_db.add.reset_mock()
        mock_db.execute.reset_mock()

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            with patch("src.crud.project.project_crud.update", new_callable=AsyncMock, return_value=mock_project):
                await project_service.update_project(
                    mock_db,
                    project_id="project_123",
                    obj_in=obj_in,
                    updated_by="user_123",
                )

        mock_db.execute.assert_not_awaited()
        mock_db.add.assert_not_called()


class TestToggleStatus:
    async def test_toggle_status_from_active_to_paused(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        mock_project.status = "active"

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            result = await project_service.toggle_status(mock_db, project_id="project_123")

        assert result is not None
        assert result.status == "paused"
        mock_db.commit.assert_awaited_once()

    async def test_toggle_status_from_paused_to_active(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        mock_project.status = "paused"

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            result = await project_service.toggle_status(mock_db, project_id="project_123")

        assert result is not None
        assert result.status == "active"
        mock_db.commit.assert_awaited_once()

    async def test_toggle_status_from_planning_to_paused(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        mock_project.status = "planning"

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            result = await project_service.toggle_status(mock_db, project_id="project_123")

        assert result is not None
        assert result.status == "paused"

    async def test_toggle_status_unknown_status(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        mock_project.status = "unknown"

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            result = await project_service.toggle_status(mock_db, project_id="project_123")

        assert result is not None
        assert result.status == "active"

    async def test_toggle_status_not_found(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=None):
            with pytest.raises(ResourceNotFoundError):
                await project_service.toggle_status(mock_db, project_id="nonexistent")

    async def test_toggle_status_with_user(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        mock_project.status = "active"

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            result = await project_service.toggle_status(
                mock_db,
                project_id="project_123",
                updated_by="user_123",
            )

        assert result is not None
        assert result.updated_by == "user_123"


class TestDeleteProject:
    async def test_delete_project_success(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        with patch("src.crud.project.project_crud.get_asset_count", new_callable=AsyncMock, return_value=0):
            with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
                with patch("src.crud.project.project_crud.remove", new_callable=AsyncMock) as mock_remove:
                    await project_service.delete_project(mock_db, project_id="project_123")

        mock_remove.assert_awaited_once_with(mock_db, id="project_123")

    async def test_delete_project_with_assets_fails(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with patch("src.crud.project.project_crud.get_asset_count", new_callable=AsyncMock, return_value=5):
            with pytest.raises(OperationNotAllowedError):
                await project_service.delete_project(mock_db, project_id="project_123")

    async def test_delete_project_not_found(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with patch("src.crud.project.project_crud.get_asset_count", new_callable=AsyncMock, return_value=0):
            with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=None):
                await project_service.delete_project(mock_db, project_id="nonexistent")


class TestGenerateProjectCode:
    async def test_generate_code_first_of_month(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await project_service.generate_project_code(mock_db)

        assert result.startswith("PRJ-")
        assert len(result) > 9

    async def test_generate_code_sequence_increment(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        mock_last_project = MagicMock()
        mock_last_project.project_code = "PRJ-TEST01-000001"

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_last_project
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await project_service.generate_project_code(mock_db)

        assert result[-6:] == "000002"

    async def test_generate_code_with_name(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with patch("src.crud.project.project_crud.get_by_code", new_callable=AsyncMock, return_value=None):
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            mock_scalars.first.return_value = None
            mock_result.scalars.return_value = mock_scalars
            mock_db.execute = AsyncMock(return_value=mock_result)

            result = await project_service.generate_project_code(mock_db, name="测试项目")

        assert result is not None


class TestSearchProjects:
    async def test_search_projects_basic(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        search_params = ProjectSearchRequest(keyword="测试", page=1, page_size=10)
        mock_items = [MagicMock(), MagicMock()]

        with patch("src.crud.project.project_crud.search", new_callable=AsyncMock, return_value=(mock_items, 2)):
            result = await project_service.search_projects(mock_db, search_params)

        assert result["total"] == 2
        assert result["page"] == 1
        assert result["page_size"] == 10
        assert result["pages"] == 1

    async def test_search_projects_pagination(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        search_params = ProjectSearchRequest(keyword="", page=2, page_size=20)
        mock_items = [MagicMock()]

        with patch("src.crud.project.project_crud.search", new_callable=AsyncMock, return_value=(mock_items, 25)):
            result = await project_service.search_projects(mock_db, search_params)

        assert result["page"] == 2
        assert result["pages"] == 2

    async def test_search_projects_empty(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        search_params = ProjectSearchRequest(keyword="不存在", page=1, page_size=10)

        with patch("src.crud.project.project_crud.search", new_callable=AsyncMock, return_value=([], 0)):
            result = await project_service.search_projects(mock_db, search_params)

        assert result["total"] == 0
        assert result["items"] == []


class TestProjectDropdownOptions:
    async def test_get_project_dropdown_options_filters_by_status(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
    ) -> None:
        active_project = MagicMock(spec=Project)
        active_project.id = "p1"
        active_project.project_name = "项目A"
        active_project.project_code = "PRJ-TEST01-000001"
        active_project.status = "active"

        planning_project = MagicMock(spec=Project)
        planning_project.id = "p2"
        planning_project.project_name = "项目B"
        planning_project.project_code = "PRJ-TEST01-000002"
        planning_project.status = "planning"

        with patch.object(
            project_service,
            "_resolve_party_filter",
            new=AsyncMock(return_value=None),
        ):
            with patch(
                "src.crud.project.project_crud.get_multi",
                new_callable=AsyncMock,
                return_value=[active_project, planning_project],
            ) as mock_get_multi:
                result = await project_service.get_project_dropdown_options(
                    mock_db,
                    status="active",
                )

        mock_get_multi.assert_awaited_once_with(
            mock_db,
            skip=0,
            limit=1000,
            status="active",
            party_filter=None,
        )
        assert [item["id"] for item in result] == ["p1", "p2"]
        assert all(
            set(item.keys()) == {"id", "project_name", "project_code"}
            for item in result
        )

    async def test_get_project_dropdown_options_uses_all_status_when_filter_is_empty(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
    ) -> None:
        with patch.object(
            project_service,
            "_resolve_party_filter",
            new=AsyncMock(return_value=None),
        ):
            with patch(
                "src.crud.project.project_crud.get_multi",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_get_multi:
                await project_service.get_project_dropdown_options(
                    mock_db,
                    status="",
                )

        mock_get_multi.assert_awaited_once_with(
            mock_db,
            skip=0,
            limit=1000,
            status=None,
            party_filter=None,
        )


class TestGetProjectById:
    async def test_get_project_by_id_resolves_tenant_filter(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        party_filter = PartyFilter(party_ids=["org-1"])

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=party_filter),
            ) as mock_resolve,
            patch(
                "src.crud.project.project_crud.get",
                new_callable=AsyncMock,
                return_value=mock_project,
            ) as mock_get,
        ):
            result = await project_service.get_project_by_id(
                mock_db,
                project_id="project_123",
                current_user_id="user_1",
            )

        assert result == mock_project
        mock_resolve.assert_awaited_once_with(
            mock_db,
            current_user_id="user_1",
            party_filter=None,
        )
        mock_get.assert_awaited_once_with(
            db=mock_db,
            id="project_123",
            party_filter=party_filter,
        )

    async def test_get_project_by_id_fail_closed_when_no_accessible_org(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with patch.object(
            project_service,
            "_resolve_party_filter",
            new=AsyncMock(return_value=PartyFilter(party_ids=[])),
        ):
            with patch(
                "src.crud.project.project_crud.get",
                new_callable=AsyncMock,
            ) as mock_get:
                result = await project_service.get_project_by_id(
                    mock_db,
                    project_id="project_123",
                    current_user_id="user_1",
                )

        assert result is None
        mock_get.assert_not_awaited()


class TestTenantFilterResolution:
    async def test_resolve_party_filter_disables_legacy_default_org_fallback(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        resolved_filter = PartyFilter(party_ids=["party-1"])

        with patch(
            "src.services.project.service.resolve_user_party_filter",
            new=AsyncMock(return_value=resolved_filter),
        ) as mock_resolve:
            party_filter = await project_service._resolve_party_filter(
                mock_db,
                current_user_id="user-1",
            )

        assert party_filter == resolved_filter
        mock_resolve.assert_awaited_once_with(
            mock_db,
            current_user_id="user-1",
            party_filter=None,
            logger=ANY,
            allow_legacy_default_organization_fallback=False,
        )

    async def test_resolve_party_filter_uses_user_party_bindings(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        """应使用 user_party_bindings 解析过滤范围。"""
        binding = MagicMock()
        binding.party_id = "party-1"

        with patch(
            "src.services.party_scope.party_crud.get_user_bindings",
            new=AsyncMock(return_value=[binding]),
        ):
            party_filter = await project_service._resolve_party_filter(
                mock_db,
                current_user_id="user-1",
            )

        assert party_filter is not None
        assert party_filter.party_ids == ["party-1"]

    async def test_resolve_party_filter_keeps_bindings_when_org_lookup_fails(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        """party binding 解析成功时应返回绑定范围。"""
        binding = MagicMock()
        binding.party_id = "party-1"

        with patch(
            "src.services.party_scope.party_crud.get_user_bindings",
            new=AsyncMock(return_value=[binding]),
        ):
            party_filter = await project_service._resolve_party_filter(
                mock_db,
                current_user_id="user-1",
            )

        assert party_filter is not None
        assert party_filter.party_ids == ["party-1"]


class TestGetProjectActiveAssets:
    async def test_get_project_active_assets_filters_inactive(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        active_binding = SimpleNamespace(asset_id="asset-active", valid_to=None)
        inactive_binding = SimpleNamespace(
            asset_id="asset-inactive",
            valid_to=datetime.now(),
        )
        active_asset = SimpleNamespace(
            id="asset-active",
            data_status=DataStatusValues.ASSET_NORMAL,
            rentable_area=Decimal("100.00"),
            rented_area=Decimal("80.00"),
        )
        inactive_asset = SimpleNamespace(
            id="asset-inactive",
            data_status=DataStatusValues.ASSET_NORMAL,
            rentable_area=Decimal("30.00"),
            rented_area=Decimal("10.00"),
        )

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(return_value=SimpleNamespace(id="project-1")),
            ),
            patch(
                "src.services.project.service.project_asset_crud.get_project_assets",
                new=AsyncMock(return_value=[active_binding, inactive_binding]),
            ) as mock_get_project_assets,
            patch(
                "src.services.project.service.asset_crud.get_multi_by_ids_async",
                new=AsyncMock(return_value=[active_asset, inactive_asset]),
            ),
        ):
            assets, summary = await project_service.get_project_active_assets(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        mock_get_project_assets.assert_awaited_once_with(
            mock_db,
            project_id="project-1",
            active_only=True,
        )
        assert [asset.id for asset in assets] == ["asset-active"]
        assert summary.total_assets == 1
        assert summary.total_rentable_area == 100.0
        assert summary.total_rented_area == 80.0
        assert summary.occupancy_rate == 80.0

    async def test_get_project_active_assets_excludes_deleted_assets(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        project_assets = [SimpleNamespace(asset_id="asset-1", valid_to=None)]
        normal_asset = SimpleNamespace(
            id="asset-1",
            data_status=DataStatusValues.ASSET_NORMAL,
            rentable_area=Decimal("50.00"),
            rented_area=Decimal("30.00"),
        )
        deleted_asset = SimpleNamespace(
            id="asset-2",
            data_status=DataStatusValues.ASSET_DELETED,
            rentable_area=Decimal("60.00"),
            rented_area=Decimal("50.00"),
        )
        abnormal_asset = SimpleNamespace(
            id="asset-3",
            data_status=DataStatusValues.ASSET_ABNORMAL,
            rentable_area=Decimal("70.00"),
            rented_area=Decimal("20.00"),
        )

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(return_value=SimpleNamespace(id="project-1")),
            ),
            patch(
                "src.services.project.service.project_asset_crud.get_project_assets",
                new=AsyncMock(return_value=project_assets),
            ),
            patch(
                "src.services.project.service.asset_crud.get_multi_by_ids_async",
                new=AsyncMock(return_value=[normal_asset, deleted_asset, abnormal_asset]),
            ),
        ):
            assets, summary = await project_service.get_project_active_assets(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert [asset.id for asset in assets] == ["asset-1"]
        assert summary.total_assets == 1
        assert summary.total_rentable_area == 50.0
        assert summary.total_rented_area == 30.0
        assert summary.occupancy_rate == 60.0

    async def test_get_project_active_assets_summary_zero_rentable_area(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        project_assets = [SimpleNamespace(asset_id="asset-1", valid_to=None)]
        zero_rentable_asset = SimpleNamespace(
            id="asset-1",
            data_status=DataStatusValues.ASSET_NORMAL,
            rentable_area=Decimal("0.00"),
            rented_area=Decimal("12.00"),
        )

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(return_value=SimpleNamespace(id="project-1")),
            ),
            patch(
                "src.services.project.service.project_asset_crud.get_project_assets",
                new=AsyncMock(return_value=project_assets),
            ),
            patch(
                "src.services.project.service.asset_crud.get_multi_by_ids_async",
                new=AsyncMock(return_value=[zero_rentable_asset]),
            ),
        ):
            assets, summary = await project_service.get_project_active_assets(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert len(assets) == 1
        assert summary.total_rentable_area == 0.0
        assert summary.total_rented_area == 12.0
        assert summary.occupancy_rate == 0.0

    async def test_get_project_active_assets_empty_project(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(return_value=SimpleNamespace(id="project-1")),
            ),
            patch(
                "src.services.project.service.project_asset_crud.get_project_assets",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.project.service.asset_crud.get_multi_by_ids_async",
                new=AsyncMock(return_value=[]),
            ) as mock_get_assets,
        ):
            assets, summary = await project_service.get_project_active_assets(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        mock_get_assets.assert_not_awaited()
        assert assets == []
        assert summary.total_assets == 0
        assert summary.total_rentable_area == 0.0
        assert summary.total_rented_area == 0.0
        assert summary.occupancy_rate == 0.0

    async def test_get_project_active_assets_project_not_found(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(return_value=None),
            ),
        ):
            with pytest.raises(ResourceNotFoundError):
                await project_service.get_project_active_assets(
                    mock_db,
                    project_id="missing-project",
                    current_user_id="user-1",
                )
