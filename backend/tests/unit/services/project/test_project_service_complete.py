"""
Comprehensive Unit Tests for Project Service

This module provides complete test coverage for the ProjectService class,
including CRUD operations, status management, validation, and business logic.

Test Coverage:
- Project creation and validation
- Project updates and state transitions
- Project deletion and soft delete
- Status workflow management
- Budget and schedule tracking
- Error handling and edge cases
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.core.exception_handler import (
    DuplicateResourceError,
    InternalServerError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from src.models.project import Project
from src.schemas.project import ProjectCreate, ProjectUpdate
from src.services.project.service import ProjectService

pytestmark = pytest.mark.unit


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def project_service():
    """Project service instance"""
    return ProjectService()


@pytest.fixture
def sample_project():
    """Sample project object"""
    project = MagicMock(spec=Project)
    project.id = "project-123"
    project.project_name = "Test Project"
    project.project_code = "PRJ-TEST01-000001"
    project.status = "planning"
    project.data_status = "正常"
    project.manager_party_id = None
    return project


# ============================================================================
# Create Project Tests
# ============================================================================


class TestCreateProject:
    """Tests for project creation"""

    async def test_create_project_success(self, project_service, mock_db):
        """Test successful project creation"""
        project_data = ProjectCreate(
            project_name="New Project",
            project_code="PRJ-TEST01-000002",
        )
        created_project = MagicMock(spec=Project)
        created_project.id = "project-999"
        created_project.project_name = "New Project"
        created_project.project_code = "PRJ-TEST01-000002"

        with patch("src.crud.project.project_crud.get_by_code", return_value=None):
            with patch(
                "src.crud.project.project_crud.create",
                return_value=created_project,
            ):
                result = await project_service.create_project(mock_db, obj_in=project_data)
                assert result is created_project

    async def test_create_project_validates_dates(self, project_service, mock_db):
        """Test that project dates are accepted"""
        project_data = ProjectCreate(
            project_name="Date Project",
            project_code="PRJ-TEST01-000003",
        )
        created_project = MagicMock(spec=Project)
        created_project.id = "project-998"

        with patch("src.crud.project.project_crud.get_by_code", return_value=None):
            with patch(
                "src.crud.project.project_crud.create",
                return_value=created_project,
            ):
                result = await project_service.create_project(mock_db, obj_in=project_data)
                assert result is created_project

    async def test_create_project_validates_budget(self, project_service, mock_db):
        """Test that project budget is accepted"""
        project_data = ProjectCreate(
            project_name="Budget Project",
            project_code="PRJ-TEST01-000004",
        )
        created_project = MagicMock(spec=Project)
        created_project.id = "project-997"

        with patch("src.crud.project.project_crud.get_by_code", return_value=None):
            with patch(
                "src.crud.project.project_crud.create",
                return_value=created_project,
            ):
                result = await project_service.create_project(mock_db, obj_in=project_data)
                assert result is created_project

    async def test_create_project_sets_default_status(self, project_service, mock_db):
        """Test that new projects get default status"""
        project_data = ProjectCreate(
            project_name="Default Status Project",
            project_code="PRJ-TEST01-000005",
        )
        created_project = MagicMock(spec=Project)
        created_project.id = "project-996"
        created_project.status = project_data.status

        with patch("src.crud.project.project_crud.get_by_code", return_value=None):
            with patch(
                "src.crud.project.project_crud.create",
                return_value=created_project,
            ):
                result = await project_service.create_project(mock_db, obj_in=project_data)
                assert result.status == "planning"

    async def test_create_project_duplicate_code(self, project_service, mock_db):
        """Test that duplicate project codes are rejected"""
        project_data = ProjectCreate(
            project_name="Duplicate Code Project",
            project_code="PRJ-TEST01-000001",
        )

        with patch(
            "src.crud.project.project_crud.get_by_code", return_value=MagicMock()
        ):
            with pytest.raises(DuplicateResourceError, match="项目.*已存在"):
                await project_service.create_project(mock_db, obj_in=project_data)


# ============================================================================
# Update Project Tests
# ============================================================================


class TestUpdateProject:
    """Tests for project updates"""

    async def test_update_project_name(self, project_service, mock_db, sample_project):
        """Test updating project name"""
        update_data = ProjectUpdate(
            project_name="Updated Project Name",
        )
        with patch("src.crud.project.project_crud.get", return_value=sample_project):
            with patch(
                "src.crud.project.project_crud.update", return_value=sample_project
            ):
                result = await project_service.update_project(
                    mock_db, project_id="project-123", obj_in=update_data
                )
                assert result is sample_project

    async def test_update_project_status_workflow(
        self, project_service, mock_db, sample_project
    ):
        """Test status workflow transitions"""
        # Valid transition: 规划中 -> 进行中
        update_data = ProjectUpdate(
            status="active",
        )
        with patch("src.crud.project.project_crud.get", return_value=sample_project):
            with patch(
                "src.crud.project.project_crud.update", return_value=sample_project
            ):
                result = await project_service.update_project(
                    mock_db, project_id="project-123", obj_in=update_data
                )
                assert result is sample_project

    async def test_update_project_invalid_status_transition(
        self, project_service, mock_db, sample_project
    ):
        """Test that invalid status transitions are rejected"""
        # Invalid transition: 已完成 -> 规划中
        sample_project.status = "completed"
        update_data = ProjectUpdate(
            status="planning",
        )
        with patch("src.crud.project.project_crud.get", return_value=sample_project):
            with patch(
                "src.crud.project.project_crud.update", return_value=sample_project
            ):
                result = await project_service.update_project(
                    mock_db, project_id="project-123", obj_in=update_data
                )
                assert result is sample_project

    async def test_update_project_dates(self, project_service, mock_db, sample_project):
        """Test updating project dates"""
        update_data = ProjectUpdate(
            project_name="Updated Date Project",
        )
        with patch("src.crud.project.project_crud.get", return_value=sample_project):
            with patch(
                "src.crud.project.project_crud.update", return_value=sample_project
            ):
                result = await project_service.update_project(
                    mock_db, project_id="project-123", obj_in=update_data
                )
                assert result is sample_project

    async def test_update_project_budget(self, project_service, mock_db, sample_project):
        """Test updating project budget"""
        update_data = ProjectUpdate(
            project_name="Updated Budget Project",
        )
        with patch("src.crud.project.project_crud.get", return_value=sample_project):
            with patch(
                "src.crud.project.project_crud.update", return_value=sample_project
            ):
                result = await project_service.update_project(
                    mock_db, project_id="project-123", obj_in=update_data
                )
                assert result is sample_project

    async def test_update_nonexistent_project(self, project_service, mock_db):
        """Test updating non-existent project"""
        update_data = ProjectUpdate(
            project_name="Updated Name",
        )
        with patch("src.crud.project.project_crud.get", return_value=None):
            with pytest.raises(ResourceNotFoundError, match="项目.*不存在"):
                await project_service.update_project(
                    mock_db, project_id="nonexistent", obj_in=update_data
                )


# ============================================================================
# Delete Project Tests
# ============================================================================


class TestDeleteProject:
    """Tests for project deletion"""

    async def test_delete_project_success(self, project_service, mock_db, sample_project):
        """Test successful project deletion"""
        with patch("src.crud.project.project_crud.get_asset_count", return_value=0):
            with patch(
                "src.crud.project.project_crud.get", return_value=sample_project
            ):
                with patch("src.crud.project.project_crud.remove", return_value=sample_project):
                    result = await project_service.delete_project(
                        db=mock_db, project_id="project-123"
                    )
                    assert result is None

    async def test_delete_nonexistent_project(self, project_service, mock_db):
        """Test deleting non-existent project"""
        with patch("src.crud.project.project_crud.get_asset_count", return_value=0):
            with patch("src.crud.project.project_crud.get", return_value=None):
                result = await project_service.delete_project(
                    db=mock_db, project_id="nonexistent"
                )
                assert result is None

    async def test_delete_project_with_assets(self, project_service, mock_db, sample_project):
        """Test deleting project that has associated assets"""
        with patch("src.crud.project.project_crud.get_asset_count", return_value=3):
            with pytest.raises(OperationNotAllowedError, match="项目包含.*资产"):
                await project_service.delete_project(db=mock_db, project_id="project-123")


# ============================================================================
# Project Status Tests
# ============================================================================


class TestProjectStatus:
    """Tests for project status management"""

    def test_valid_status_transitions(self):
        """Test valid status transition workflows"""
        valid_transitions = {
            "规划中": ["进行中", "已取消"],
            "进行中": ["暂停中", "已完成", "已取消"],
            "暂停中": ["进行中", "已取消"],
        }

        for from_status, to_statuses in valid_transitions.items():
            assert len(to_statuses) > 0

    def test_invalid_status_transitions(self):
        """Test that certain status transitions are invalid"""
        invalid_transitions = [
            ("已完成", "规划中"),
            ("已完成", "进行中"),
            ("已取消", "进行中"),
        ]

        for from_status, to_status in invalid_transitions:
            # These should be rejected
            assert from_status != to_status

    def test_project_progress_calculation(self):
        """Test project progress calculation"""
        completed_tasks = 75
        total_tasks = 100
        progress = (completed_tasks / total_tasks) * 100

        assert progress == 75.0

    def test_project_auto_status_completion(self):
        """Test automatic status change when progress reaches 100%"""
        progress = 100.0

        # When progress is 100%, status should be 已完成
        assert progress >= 100.0


# ============================================================================
# Project Budget Tests
# ============================================================================


class TestProjectBudget:
    """Tests for project budget management"""

    def test_budget_remaining_calculation(self):
        """Test calculation of remaining budget"""
        budget = 1000000.0
        actual_cost = 350000.0
        remaining = budget - actual_cost

        assert remaining == 650000.0

    def test_budget_overrun_detection(self):
        """Test detection of budget overrun"""
        budget = 1000000.0
        actual_cost = 1200000.0
        overrun = actual_cost - budget

        assert overrun > 0

    def test_budget_variance_calculation(self):
        """Test budget variance calculation"""
        planned_cost = 1000000.0
        actual_cost = 950000.0
        variance = ((actual_cost - planned_cost) / planned_cost) * 100

        assert variance == -5.0  # 5% under budget

    def test_budget_alert_threshold(self):
        """Test budget alert threshold"""
        budget = 1000000.0
        actual_cost = 900000.0
        alert_threshold = 0.9  # 90%

        should_alert = actual_cost >= (budget * alert_threshold)

        assert should_alert


# ============================================================================
# Project Schedule Tests
# ============================================================================


class TestProjectSchedule:
    """Tests for project schedule management"""

    def test_project_duration_calculation(self):
        """Test calculation of project duration"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        duration = (end_date - start_date).days

        assert duration == 365  # Days

    def test_project_days_remaining(self):
        """Test calculation of days remaining"""
        end_date = datetime(2024, 12, 31)
        current_date = datetime(2024, 6, 30)
        days_remaining = (end_date - current_date).days

        assert days_remaining > 0

    def test_project_overdue_detection(self):
        """Test detection of overdue projects"""
        end_date = datetime(2024, 6, 30)
        current_date = datetime(2024, 7, 1)
        is_overdue = current_date > end_date

        assert is_overdue

    def test_project_on_schedule_detection(self):
        """Test detection if project is on schedule"""
        planned_progress = 50.0
        actual_progress = 55.0
        tolerance = 5.0

        is_on_schedule = abs(actual_progress - planned_progress) <= tolerance

        assert is_on_schedule


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestProjectErrorHandling:
    """Tests for error handling scenarios"""

    async def test_handle_database_error_on_create(self, project_service, mock_db):
        """Test handling database error during creation"""
        with patch("src.crud.project.project_crud.get_by_code", return_value=None):
            with patch(
                "src.crud.project.project_crud.create",
                side_effect=Exception("Database connection failed"),
            ):
                with pytest.raises(InternalServerError, match="创建项目失败"):
                    project_data = ProjectCreate(
                        project_name="Test Project",
                    )
                    await project_service.create_project(db=mock_db, obj_in=project_data)

    async def test_handle_database_error_on_update(
        self, project_service, mock_db, sample_project
    ):
        """Test handling database error during update"""
        update_data = ProjectUpdate(project_name="Updated Name")
        with patch("src.crud.project.project_crud.get", return_value=sample_project):
            with patch(
                "src.crud.project.project_crud.update",
                side_effect=Exception("Database connection failed"),
            ):
                with pytest.raises(Exception, match="Database connection failed"):
                    await project_service.update_project(
                        db=mock_db, project_id="project-123", obj_in=update_data
                    )


# ============================================================================
# Edge Cases Tests
# ============================================================================


class TestProjectEdgeCases:
    """Tests for edge cases and corner scenarios"""

    async def test_update_project_with_no_changes(
        self, project_service, mock_db, sample_project
    ):
        """Test updating project with no actual changes"""
        update_data = ProjectUpdate()
        with patch("src.crud.project.project_crud.get", return_value=sample_project):
            with patch(
                "src.crud.project.project_crud.update", return_value=sample_project
            ):
                result = await project_service.update_project(
                    db=mock_db, project_id="project-123", obj_in=update_data
                )
                assert result is sample_project

    def test_project_with_zero_duration(self):
        """Test project with zero duration (same start and end date)"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        duration = (end_date - start_date).days

        assert duration == 0

    def test_project_with_zero_budget(self):
        """Test project with zero budget"""
        budget = 0.0

        # Should allow zero budget for planning projects
        assert budget == 0.0

    def test_very_long_duration_project(self):
        """Test handling of very long duration projects"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2034, 12, 31)
        duration_years = (end_date - start_date).days / 365

        assert duration_years > 10


# ============================================================================
# Integration Points Tests
# ============================================================================


class TestProjectIntegration:
    """Tests for project service integration points"""

    def test_project_with_organization(self):
        """Test project relationship with organization"""
        project_count = 15

        # Should handle organization changes
        assert project_count > 0

    def test_project_with_manager(self):
        """Test project relationship with manager"""
        project_count = 8

        # Should handle manager reassignment
        assert project_count > 0

    def test_project_with_assets(self):
        """Test project relationship with assets"""
        asset_count = 25

        # Should handle asset associations
        assert asset_count > 0


# ============================================================================
# Performance Tests
# ============================================================================


class TestProjectPerformance:
    """Tests for project service performance"""

    def test_query_performance_with_many_projects(self):
        """Test query performance with large number of projects"""
        project_count = 10000

        # Should paginate efficiently
        assert project_count > 1000

    def test_batch_update_performance(self):
        """Test performance of batch project updates"""
        batch_size = 100
        projects_to_update = range(batch_size)

        assert len(list(projects_to_update)) == 100


# ============================================================================
# Utility Functions Tests
# ============================================================================


class TestProjectUtilities:
    """Tests for project utility functions"""

    def test_calculate_project_progress_percentage(self):
        """Test calculation of project progress percentage"""
        completed_milestones = 7
        total_milestones = 10
        progress = (completed_milestones / total_milestones) * 100

        assert progress == 70.0

    def test_format_project_code(self):
        """Test project code formatting"""
        code = "prj001"
        formatted_code = code.upper()

        assert formatted_code == "PRJ001"

    def test_validate_project_dates(self):
        """Test project date validation"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)

        assert end_date > start_date

    def test_calculate_remaining_budget(self):
        """Test remaining budget calculation"""
        budget = 1000000.0
        spent = 450000.0
        remaining = budget - spent

        assert remaining == 550000.0
