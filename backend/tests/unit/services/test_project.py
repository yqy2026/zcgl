from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import DuplicateResourceError, OperationNotAllowedError
from src.models.project import Project
from src.schemas.project import ProjectCreate, ProjectUpdate
from src.services.project.service import ProjectService

TEST_PROJECT_ID = "proj_123"
TEST_USER_ID = "user_123"

pytestmark = pytest.mark.unit


@pytest.fixture
def service() -> ProjectService:
    return ProjectService()


class TestProjectService:
    async def test_create_project_auto_code(self, service: ProjectService, mock_db):
        obj_in = ProjectCreate(name="Test Project")

        created_project = MagicMock(spec=Project)
        created_project.id = TEST_PROJECT_ID
        created_project.code = "PJ2501001"
        created_project.name = "Test Project"

        with patch.object(service, "generate_project_code", return_value="PJ2501001"):
            with patch("src.crud.project.project_crud.get_by_code", return_value=None):
                with patch(
                    "src.crud.project.project_crud.create",
                    return_value=created_project,
                ) as mock_create:
                    result = await service.create_project(
                        mock_db, obj_in=obj_in, created_by=TEST_USER_ID
                    )

        assert result.code == "PJ2501001"
        mock_create.assert_awaited_once()

    async def test_create_project_duplicate_code(self, service: ProjectService, mock_db):
        obj_in = ProjectCreate(name="Test Project", code="PJ2501002")

        with patch("src.crud.project.project_crud.get_by_code", return_value=MagicMock()):
            with pytest.raises(DuplicateResourceError) as excinfo:
                await service.create_project(mock_db, obj_in=obj_in)

        assert "已存在" in str(excinfo.value)

    async def test_update_project(self, service: ProjectService, mock_db):
        project = MagicMock(spec=Project)
        project.id = TEST_PROJECT_ID
        project.name = "Old Name"
        obj_in = ProjectUpdate(name="New Name")

        updated_project = MagicMock(spec=Project)
        updated_project.id = TEST_PROJECT_ID
        updated_project.name = "New Name"

        with patch("src.crud.project.project_crud.get", return_value=project):
            with patch(
                "src.crud.project.project_crud.update",
                return_value=updated_project,
            ) as mock_update:
                result = await service.update_project(
                    mock_db, project_id=TEST_PROJECT_ID, obj_in=obj_in
                )

        assert result.name == "New Name"
        mock_update.assert_awaited_once()

    async def test_toggle_status(self, service: ProjectService, mock_db):
        project = MagicMock(spec=Project)
        project.id = TEST_PROJECT_ID
        project.project_status = "规划中"

        with patch("src.crud.project.project_crud.get", return_value=project):
            result = await service.toggle_status(mock_db, project_id=TEST_PROJECT_ID)
        assert result.project_status == "暂停"

        project.project_status = "暂停"
        with patch("src.crud.project.project_crud.get", return_value=project):
            result = await service.toggle_status(mock_db, project_id=TEST_PROJECT_ID)
        assert result.project_status == "进行中"

    async def test_delete_project_with_assets(self, service: ProjectService, mock_db):
        with patch("src.crud.project.project_crud.get_asset_count", return_value=5):
            with pytest.raises(OperationNotAllowedError) as excinfo:
                await service.delete_project(mock_db, project_id=TEST_PROJECT_ID)

        assert "包含 5 个资产" in str(excinfo.value)

    async def test_delete_project_success(self, service: ProjectService, mock_db):
        with patch("src.services.project.service.project_crud") as mock_crud:
            mock_crud.get_asset_count = AsyncMock(return_value=0)
            mock_crud.get = AsyncMock(return_value=MagicMock(spec=Project))
            mock_crud.remove = AsyncMock(return_value=MagicMock(spec=Project))

            await service.delete_project(mock_db, project_id=TEST_PROJECT_ID)

            mock_crud.remove.assert_awaited_once_with(mock_db, id=TEST_PROJECT_ID)

    async def test_generate_project_code_fallback(self, service: ProjectService, mock_db):
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        code = await service.generate_project_code(mock_db, name=None)
        assert code.startswith("PJ")
        assert len(code) == 9
