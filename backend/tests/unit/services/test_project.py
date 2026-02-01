from unittest.mock import MagicMock, patch

import pytest

from src.core.exception_handler import DuplicateResourceError, OperationNotAllowedError
from src.models.asset import Project
from src.schemas.project import ProjectCreate, ProjectUpdate
from src.services.project.service import ProjectService

TEST_PROJECT_ID = "proj_123"
TEST_USER_ID = "user_123"


@pytest.fixture
def service():
    return ProjectService()


class TestProjectService:
    def test_create_project_auto_code(self, service, mock_db):
        obj_in = ProjectCreate(name="Test Project")

        # Mock generate_project_code
        with patch.object(service, "generate_project_code", return_value="PJ2501001"):
            with patch("src.crud.project.project_crud.get_by_code", return_value=None):
                with patch("src.crud.project.project_crud.create") as mock_create:
                    mock_create.return_value = Project(
                        id=TEST_PROJECT_ID, code="PJ2501001", name="Test Project"
                    )

                    result = service.create_project(
                        mock_db, obj_in=obj_in, created_by=TEST_USER_ID
                    )

                    assert result.code == "PJ2501001"
                    mock_create.assert_called()

    def test_create_project_duplicate_code(self, service, mock_db):
        obj_in = ProjectCreate(name="Test Project", code="PJ2501002")

        with patch("src.crud.project.project_crud.get_by_code", return_value=Project()):
            with pytest.raises(DuplicateResourceError) as excinfo:
                service.create_project(mock_db, obj_in=obj_in)

            assert "已存在" in str(excinfo.value)

    def test_update_project(self, service, mock_db):
        project = Project(id=TEST_PROJECT_ID, name="Old Name")
        obj_in = ProjectUpdate(name="New Name")

        with patch("src.crud.project.project_crud.get", return_value=project):
            with patch("src.crud.project.project_crud.update") as mock_update:
                mock_update.return_value = Project(id=TEST_PROJECT_ID, name="New Name")

                result = service.update_project(
                    mock_db, project_id=TEST_PROJECT_ID, obj_in=obj_in
                )

                assert result.name == "New Name"
                mock_update.assert_called()

    def test_toggle_status(self, service, mock_db):
        # Using string comparison as implemented in service
        project = Project(id=TEST_PROJECT_ID, project_status="规划中")

        with patch("src.crud.project.project_crud.get", return_value=project):
            result = service.toggle_status(mock_db, project_id=TEST_PROJECT_ID)

            assert result.project_status == "暂停"
            mock_db.commit.assert_called()

            # Toggle back
            project.project_status = "暂停"
            result = service.toggle_status(mock_db, project_id=TEST_PROJECT_ID)
            assert result.project_status == "进行中"

    def test_delete_project_with_assets(self, service, mock_db):
        with patch("src.crud.project.project_crud.get_asset_count", return_value=5):
            with pytest.raises(OperationNotAllowedError) as excinfo:
                service.delete_project(mock_db, project_id=TEST_PROJECT_ID)

            assert "包含 5 个资产" in str(excinfo.value)

    def test_delete_project_success(self, service, mock_db):
        with patch("src.services.project.service.project_crud") as mock_crud:
            mock_crud.get_asset_count.return_value = 0
            mock_project = MagicMock()
            mock_crud.get.return_value = mock_project

            service.delete_project(mock_db, project_id=TEST_PROJECT_ID)

            # Verify project_crud.remove was called with correct id
            mock_crud.remove.assert_called_once_with(mock_db, id=TEST_PROJECT_ID)

    def test_generate_project_code_fallback(self, service, mock_db):
        # Test the fallback logic when pinyin/name fails or no name
        with patch("src.models.Project"):
            # Mock the query for last project
            mock_query = mock_db.query.return_value
            mock_query.filter.return_value.order_by.return_value.first.return_value = (
                None
            )

            code = service.generate_project_code(mock_db, name=None)
            assert code.startswith("PJ")
            assert len(code) > 5
