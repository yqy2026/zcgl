"""
测试项目服务（异步）
"""

import inspect
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import (
    DuplicateResourceError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from src.crud.query_builder import TenantFilter
from src.models import Project
from src.schemas.project import ProjectCreate, ProjectSearchRequest, ProjectUpdate
from src.services.project.service import ProjectService

pytestmark = pytest.mark.asyncio


def test_project_service_module_should_not_use_datetime_utcnow() -> None:
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
    project.name = "测试项目"
    project.code = "PJ2501001"
    project.project_status = "进行中"
    project.created_by = "user_123"
    project.created_at = datetime.now()
    return project


class TestCreateProject:
    async def test_create_project_success(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectCreate(name="新项目", code="PJ2501002", project_status="规划中")

        with patch("src.crud.project.project_crud.get_by_code", new_callable=AsyncMock, return_value=None):
            with patch("src.crud.project.project_crud.create", new_callable=AsyncMock, return_value=mock_project):
                result = await project_service.create_project(mock_db, obj_in=obj_in)

        assert result is not None

    async def test_create_project_auto_generates_code(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectCreate(name="新项目", code=None, project_status="规划中")

        with patch.object(project_service, "generate_project_code", new_callable=AsyncMock, return_value="PJ2501003"):
            with patch("src.crud.project.project_crud.get_by_code", new_callable=AsyncMock, return_value=None):
                with patch("src.crud.project.project_crud.create", new_callable=AsyncMock, return_value=mock_project):
                    result = await project_service.create_project(mock_db, obj_in=obj_in)

        assert result is not None

    async def test_create_project_duplicate_code(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectCreate(name="新项目", code="PJ2501001", project_status="规划中")

        with patch("src.crud.project.project_crud.get_by_code", new_callable=AsyncMock, return_value=mock_project):
            with pytest.raises(DuplicateResourceError):
                await project_service.create_project(mock_db, obj_in=obj_in)

    async def test_create_project_with_user(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectCreate(name="新项目", code="PJ2501002", project_status="规划中")

        with patch("src.crud.project.project_crud.get_by_code", new_callable=AsyncMock, return_value=None):
            with patch("src.crud.project.project_crud.create", new_callable=AsyncMock, return_value=mock_project):
                result = await project_service.create_project(
                    mock_db,
                    obj_in=obj_in,
                    created_by="user_123",
                )

        assert result is not None


class TestUpdateProject:
    async def test_update_project_basic(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectUpdate(name="更新后的项目名称")

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            with patch("src.crud.project.project_crud.update", new_callable=AsyncMock, return_value=mock_project):
                result = await project_service.update_project(
                    mock_db, project_id="project_123", obj_in=obj_in
                )

        assert result is not None

    async def test_update_project_not_found(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        obj_in = ProjectUpdate(name="新名称")

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=None):
            with pytest.raises(ResourceNotFoundError):
                await project_service.update_project(
                    mock_db, project_id="nonexistent", obj_in=obj_in
                )

    async def test_update_project_with_user(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        obj_in = ProjectUpdate(project_status="进行中")

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            with patch("src.crud.project.project_crud.update", new_callable=AsyncMock, return_value=mock_project):
                result = await project_service.update_project(
                    mock_db,
                    project_id="project_123",
                    obj_in=obj_in,
                    updated_by="user_123",
                )

        assert result is not None


class TestToggleStatus:
    async def test_toggle_status_from_active_to_paused(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        mock_project.project_status = "进行中"

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            result = await project_service.toggle_status(mock_db, project_id="project_123")

        assert result is not None
        assert result.project_status == "暂停"
        mock_db.commit.assert_awaited_once()

    async def test_toggle_status_from_paused_to_active(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        mock_project.project_status = "暂停"

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            result = await project_service.toggle_status(mock_db, project_id="project_123")

        assert result is not None
        assert result.project_status == "进行中"
        mock_db.commit.assert_awaited_once()

    async def test_toggle_status_from_planning_to_paused(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        mock_project.project_status = "规划中"

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            result = await project_service.toggle_status(mock_db, project_id="project_123")

        assert result is not None
        assert result.project_status == "暂停"

    async def test_toggle_status_unknown_status(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        mock_project.project_status = "未知状态"

        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=mock_project):
            result = await project_service.toggle_status(mock_db, project_id="project_123")

        assert result is not None
        assert result.project_status == "进行中"

    async def test_toggle_status_not_found(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with patch("src.crud.project.project_crud.get", new_callable=AsyncMock, return_value=None):
            with pytest.raises(ResourceNotFoundError):
                await project_service.toggle_status(mock_db, project_id="nonexistent")

    async def test_toggle_status_with_user(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        mock_project.project_status = "进行中"

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

        assert result.startswith("PJ")
        assert len(result) == 9

    async def test_generate_code_sequence_increment(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        mock_last_project = MagicMock()
        mock_last_project.code = "PJ2501001"

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_last_project
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await project_service.generate_project_code(mock_db)

        assert result.endswith("002")

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


class TestGenerateNameCode:
    async def test_generate_name_code_disabled(self, project_service: ProjectService) -> None:
        result = project_service._generate_name_code("测试项目")
        assert result is None


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


class TestGetProjectById:
    async def test_get_project_by_id_resolves_tenant_filter(
        self, project_service: ProjectService, mock_db: MagicMock, mock_project: MagicMock
    ) -> None:
        tenant_filter = TenantFilter(organization_ids=["org-1"])

        with (
            patch.object(
                project_service,
                "_resolve_tenant_filter",
                new=AsyncMock(return_value=tenant_filter),
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
            tenant_filter=None,
        )
        mock_get.assert_awaited_once_with(
            db=mock_db,
            id="project_123",
            tenant_filter=tenant_filter,
        )

    async def test_get_project_by_id_fail_closed_when_no_accessible_org(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with patch.object(
            project_service,
            "_resolve_tenant_filter",
            new=AsyncMock(return_value=TenantFilter(organization_ids=[])),
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
