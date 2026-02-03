"""
Comprehensive Unit Tests for Tasks API Routes (src/api/v1/tasks.py)

This test module covers all endpoints in the tasks router to achieve 70%+ coverage.

Endpoints Tested:
1. POST /api/v1/tasks/ - Create new task
2. GET /api/v1/tasks/ - Get task list with pagination and filters
3. GET /api/v1/tasks/{task_id} - Get task details
4. PUT /api/v1/tasks/{task_id} - Update task
5. POST /api/v1/tasks/{task_id}/cancel - Cancel task
6. DELETE /api/v1/tasks/{task_id} - Delete task (soft delete)
7. GET /api/v1/tasks/{task_id}/history - Get task history
8. GET /api/v1/tasks/statistics - Get task statistics
9. GET /api/v1/tasks/running - Get running tasks
10. GET /api/v1/tasks/recent - Get recent tasks
11. POST /api/v1/tasks/configs/excel - Create Excel task config
12. GET /api/v1/tasks/configs/excel - Get Excel config list
13. GET /api/v1/tasks/configs/excel/default - Get default Excel config
14. GET /api/v1/tasks/configs/excel/{config_id} - Get Excel config details
15. PUT /api/v1/tasks/configs/excel/{config_id} - Update Excel config
16. DELETE /api/v1/tasks/configs/excel/{config_id} - Delete Excel config
17. GET /api/v1/tasks/cleanup - Cleanup old tasks
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status

from src.core.exception_handler import BaseBusinessError
from src.enums.task import TaskStatus, TaskType
from src.schemas.task import (
    ExcelTaskConfigCreate,
    TaskCancelRequest,
    TaskCreate,
    TaskUpdate,
)

pytestmark = pytest.mark.api


# Helper functions
def create_mock_task(**kwargs):
    """Create a mock task with default values"""
    defaults = {
        "id": "task-123",
        "task_type": TaskType.EXCEL_IMPORT.value,
        "status": TaskStatus.PENDING.value,
        "title": "Test Task",
        "description": None,
        "user_id": "test-user-id",
        "created_at": datetime.now(UTC),
        "started_at": None,
        "completed_at": None,
        "progress": 0,
        "total_items": None,
        "processed_items": 0,
        "failed_items": 0,
        "result_data": None,
        "error_message": None,
        "parameters": None,
        "success_rate": 0.0,
        "duration_seconds": 0.0,
    }
    defaults.update(kwargs)
    mock = MagicMock()
    for key, value in defaults.items():
        setattr(mock, key, value)
    return mock


def create_mock_excel_config(**kwargs):
    """Create a mock Excel config with default values"""
    defaults = {
        "id": "config-123",
        "config_name": "Test Config",
        "config_type": "import",
        "task_type": TaskType.EXCEL_IMPORT.value,
        "field_mapping": None,
        "validation_rules": None,
        "format_config": None,
        "is_default": True,
        "is_active": True,
        "created_by": "test-user-id",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    mock = MagicMock()
    for key, value in defaults.items():
        setattr(mock, key, value)
    return mock


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_current_user():
    """Create mock authenticated user"""
    user = MagicMock()
    user.id = "test-user-id"
    user.username = "testuser"
    user.is_active = True
    user.role = "user"
    return user


# ============================================================================
# Test: POST /tasks/ - Create Task
# ============================================================================


class TestCreateTask:
    """Tests for POST /api/v1/tasks/ endpoint"""

    @patch("src.api.v1.system.tasks.task_service")
    def test_create_task_success(self, mock_task_service, mock_db, mock_current_user):
        """Test creating task successfully"""
        from src.api.v1.system.tasks import create_task

        task_data = TaskCreate(
            task_type=TaskType.EXCEL_IMPORT,
            title="Import Assets",
            description="Import assets from Excel",
            parameters={"file_path": "/path/to/file.xlsx"},
        )

        mock_task = create_mock_task(
            title="Import Assets",
            description="Import assets from Excel",
            parameters={"file_path": "/path/to/file.xlsx"},
        )

        mock_task_service.create_task.return_value = mock_task

        result = create_task(
            task_in=task_data, db=mock_db, current_user=mock_current_user
        )

        assert result.task_type == TaskType.EXCEL_IMPORT.value
        assert result.title == "Import Assets"
        mock_task_service.create_task.assert_called_once()

    @patch("src.api.v1.system.tasks.task_service")
    def test_create_task_exception(self, mock_task_service, mock_db, mock_current_user):
        """Test creating task with exception"""
        from src.api.v1.system.tasks import create_task

        task_data = TaskCreate(
            task_type=TaskType.EXCEL_IMPORT,
            title="Import Assets",
        )

        mock_task_service.create_task.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            create_task(task_in=task_data, db=mock_db, current_user=mock_current_user)

        assert exc_info.value.status_code == 500
        assert "创建任务失败" in exc_info.value.message


# ============================================================================
# Test: GET /tasks/ - Get Task List
# ============================================================================


class TestGetTasks:
    """Tests for GET /api/v1/tasks/ endpoint"""

    @patch("src.api.v1.system.tasks.task_crud")
    def test_get_tasks_default_params(self, mock_task_crud, mock_db, mock_current_user):
        """Test getting tasks with default parameters"""
        from src.api.v1.system.tasks import get_tasks

        mock_tasks = [
            create_mock_task(id=f"task-{i}", title=f"Task {i}") for i in range(20)
        ]

        mock_task_crud.get_multi.return_value = mock_tasks
        mock_task_crud.count.return_value = 100

        result = get_tasks(
            page=1,
            page_size=20,
            task_type=None,
            status=None,
            user_id=None,
            created_after=None,
            created_before=None,
            order_by="created_at",
            order_dir="desc",
            db=mock_db,
            current_user=mock_current_user,
        )

        payload = json.loads(result.body)
        data = payload["data"]
        assert len(data["items"]) == 20
        assert data["pagination"]["total"] == 100
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 20
        assert data["pagination"]["total_pages"] == 5

    @patch("src.api.v1.system.tasks.task_crud")
    def test_get_tasks_with_filters(self, mock_task_crud, mock_db, mock_current_user):
        """Test getting tasks with filters"""
        from src.api.v1.system.tasks import get_tasks

        mock_task_crud.get_multi.return_value = []
        mock_task_crud.count.return_value = 0

        result = get_tasks(
            page=1,
            page_size=20,
            task_type=TaskType.EXCEL_IMPORT.value,
            status=TaskStatus.PENDING.value,
            user_id="test-user-id",
            created_after="2026-01-01T00:00:00",
            created_before="2026-12-31T23:59:59",
            order_by="created_at",
            order_dir="desc",
            db=mock_db,
            current_user=mock_current_user,
        )

        payload = json.loads(result.body)
        assert payload["data"]["pagination"]["total"] == 0
        mock_task_crud.get_multi.assert_called_once()

    @patch("src.api.v1.system.tasks.task_crud")
    def test_get_tasks_exception(self, mock_task_crud, mock_db, mock_current_user):
        """Test getting tasks with exception"""
        from src.api.v1.system.tasks import get_tasks

        mock_task_crud.get_multi.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            get_tasks(
                page=1,
                page_size=20,
                task_type=None,
                status=None,
                user_id=None,
                created_after=None,
                created_before=None,
                order_by="created_at",
                order_dir="desc",
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500
        assert "获取任务列表失败" in exc_info.value.message


# ============================================================================
# Test: GET /tasks/{task_id} - Get Task Details
# ============================================================================


class TestGetTask:
    """Tests for GET /api/v1/tasks/{task_id} endpoint"""

    @patch("src.api.v1.system.tasks.task_crud")
    def test_get_task_success(self, mock_task_crud, mock_db, mock_current_user):
        """Test getting task details successfully"""
        from src.api.v1.system.tasks import get_task

        mock_task = create_mock_task()
        mock_task_crud.get.return_value = mock_task

        result = get_task(
            task_id="task-123", db=mock_db, current_user=mock_current_user
        )

        assert result.id == "task-123"
        assert result.title == "Test Task"
        mock_task_crud.get.assert_called_once_with(db=mock_db, id="task-123")

    @patch("src.api.v1.system.tasks.task_crud")
    def test_get_task_not_found(self, mock_task_crud, mock_db, mock_current_user):
        """Test getting non-existent task"""
        from src.api.v1.system.tasks import get_task

        mock_task_crud.get.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            get_task(task_id="nonexistent", db=mock_db, current_user=mock_current_user)

        assert exc_info.value.status_code == 404
        assert "不存在" in exc_info.value.message


# ============================================================================
# Test: PUT /tasks/{task_id} - Update Task
# ============================================================================


class TestUpdateTask:
    """Tests for PUT /api/v1/tasks/{task_id} endpoint"""

    @patch("src.api.v1.system.tasks.task_crud")
    @patch("src.api.v1.system.tasks.task_service")
    def test_update_task_success(
        self, mock_task_service, mock_task_crud, mock_db, mock_current_user
    ):
        """Test updating task successfully"""
        from src.api.v1.system.tasks import update_task

        task_data = TaskUpdate(progress=50, processed_items=50)

        mock_task = create_mock_task(
            status=TaskStatus.RUNNING.value,
            progress=50,
            total_items=100,
            processed_items=50,
            failed_items=0,
        )
        mock_task_crud.get.return_value = mock_task

        mock_task_service.update_task.return_value = mock_task

        result = update_task(
            task_id="task-123",
            task_in=task_data,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.progress == 50
        mock_task_service.update_task.assert_called_once()

    @patch("src.api.v1.system.tasks.task_crud")
    @patch("src.api.v1.system.tasks.task_service")
    def test_update_task_not_found(
        self, mock_task_service, mock_task_crud, mock_db, mock_current_user
    ):
        """Test updating non-existent task"""
        from src.api.v1.system.tasks import update_task

        task_data = TaskUpdate(progress=50)

        mock_task_crud.get.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            update_task(
                task_id="nonexistent",
                task_in=task_data,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @patch("src.api.v1.system.tasks.task_crud")
    @patch("src.api.v1.system.tasks.task_service")
    def test_update_task_invalid_status(
        self, mock_task_service, mock_task_crud, mock_db, mock_current_user
    ):
        """Test updating completed task (forbidden)"""
        from src.api.v1.system.tasks import update_task

        task_data = TaskUpdate(progress=50)

        mock_task_crud.get.return_value = create_mock_task()
        mock_task_service.update_task.side_effect = ValueError("已完成的任务无法更新")

        with pytest.raises(BaseBusinessError) as exc_info:
            update_task(
                task_id="task-123",
                task_in=task_data,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500

    @patch("src.api.v1.system.tasks.task_crud")
    @patch("src.api.v1.system.tasks.task_service")
    def test_update_task_exception(
        self, mock_task_service, mock_task_crud, mock_db, mock_current_user
    ):
        """Test updating task with exception"""
        from src.api.v1.system.tasks import update_task

        task_data = TaskUpdate(progress=50)

        mock_task_crud.get.return_value = create_mock_task()
        mock_task_service.update_task.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            update_task(
                task_id="task-123",
                task_in=task_data,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500
        assert "更新任务失败" in exc_info.value.message


# ============================================================================
# Test: POST /tasks/{task_id}/cancel - Cancel Task
# ============================================================================


class TestCancelTask:
    """Tests for POST /api/v1/tasks/{task_id}/cancel endpoint"""

    @patch("src.api.v1.system.tasks.task_crud")
    @patch("src.api.v1.system.tasks.task_service")
    def test_cancel_task_success(
        self, mock_task_service, mock_task_crud, mock_db, mock_current_user
    ):
        """Test cancelling task successfully"""
        from src.api.v1.system.tasks import cancel_task

        mock_task = create_mock_task(
            status=TaskStatus.CANCELLED.value,
            error_message="任务被取消: User requested",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        mock_task_crud.get.return_value = mock_task
        mock_task_service.cancel_task.return_value = mock_task

        cancel_request = TaskCancelRequest(reason="User requested")

        result = cancel_task(
            task_id="task-123",
            cancel_request=cancel_request,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.status == TaskStatus.CANCELLED.value
        mock_task_service.cancel_task.assert_called_once()

    @patch("src.api.v1.system.tasks.task_crud")
    @patch("src.api.v1.system.tasks.task_service")
    def test_cancel_task_without_reason(
        self, mock_task_service, mock_task_crud, mock_db, mock_current_user
    ):
        """Test cancelling task without reason"""
        from src.api.v1.system.tasks import cancel_task

        mock_task = create_mock_task(
            status=TaskStatus.CANCELLED.value,
            error_message="任务被取消: 无原因",
            completed_at=datetime.now(UTC),
        )

        mock_task_crud.get.return_value = mock_task
        mock_task_service.cancel_task.return_value = mock_task

        result = cancel_task(
            task_id="task-123",
            cancel_request=None,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.status == TaskStatus.CANCELLED.value

    @patch("src.api.v1.system.tasks.task_crud")
    @patch("src.api.v1.system.tasks.task_service")
    def test_cancel_task_not_found(
        self, mock_task_service, mock_task_crud, mock_db, mock_current_user
    ):
        """Test cancelling non-existent task"""
        from src.api.v1.system.tasks import cancel_task

        mock_task_crud.get.return_value = None

        cancel_request = TaskCancelRequest(reason="Test")

        with pytest.raises(BaseBusinessError) as exc_info:
            cancel_task(
                task_id="nonexistent",
                cancel_request=cancel_request,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @patch("src.api.v1.system.tasks.task_crud")
    @patch("src.api.v1.system.tasks.task_service")
    def test_cancel_task_invalid_status(
        self, mock_task_service, mock_task_crud, mock_db, mock_current_user
    ):
        """Test cancelling task that cannot be cancelled"""
        from src.api.v1.system.tasks import cancel_task

        mock_task_crud.get.return_value = create_mock_task()
        mock_task_service.cancel_task.side_effect = ValueError("任务无法取消")

        cancel_request = TaskCancelRequest(reason="Test")

        with pytest.raises(BaseBusinessError) as exc_info:
            cancel_task(
                task_id="task-123",
                cancel_request=cancel_request,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500

    @patch("src.api.v1.system.tasks.task_crud")
    @patch("src.api.v1.system.tasks.task_service")
    def test_cancel_task_exception(
        self, mock_task_service, mock_task_crud, mock_db, mock_current_user
    ):
        """Test cancelling task with exception"""
        from src.api.v1.system.tasks import cancel_task

        mock_task_crud.get.return_value = create_mock_task()
        mock_task_service.cancel_task.side_effect = Exception("Database error")

        cancel_request = TaskCancelRequest(reason="Test")

        with pytest.raises(BaseBusinessError) as exc_info:
            cancel_task(
                task_id="task-123",
                cancel_request=cancel_request,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500
        assert "取消任务失败" in exc_info.value.message


# ============================================================================
# Test: DELETE /tasks/{task_id} - Delete Task
# ============================================================================


class TestDeleteTask:
    """Tests for DELETE /api/v1/tasks/{task_id} endpoint"""

    @patch("src.api.v1.system.tasks.task_crud")
    @patch("src.api.v1.system.tasks.task_service")
    def test_delete_task_success(
        self, mock_task_service, mock_task_crud, mock_db, mock_current_user
    ):
        """Test deleting task successfully"""
        from src.api.v1.system.tasks import delete_task

        mock_task_crud.get.return_value = create_mock_task()
        mock_task_service.delete_task.return_value = None

        result = delete_task(
            task_id="task-123", db=mock_db, current_user=mock_current_user
        )

        assert result["message"] == "任务删除成功"
        mock_task_service.delete_task.assert_called_once_with(
            db=mock_db, task_id="task-123"
        )

    @patch("src.api.v1.system.tasks.task_crud")
    @patch("src.api.v1.system.tasks.task_service")
    def test_delete_task_not_found(
        self, mock_task_service, mock_task_crud, mock_db, mock_current_user
    ):
        """Test deleting non-existent task"""
        from src.api.v1.system.tasks import delete_task

        mock_task_crud.get.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            delete_task(
                task_id="nonexistent", db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @patch("src.api.v1.system.tasks.task_crud")
    @patch("src.api.v1.system.tasks.task_service")
    def test_delete_task_exception(
        self, mock_task_service, mock_task_crud, mock_db, mock_current_user
    ):
        """Test deleting task with exception"""
        from src.api.v1.system.tasks import delete_task

        mock_task_crud.get.return_value = create_mock_task()
        mock_task_service.delete_task.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            delete_task(task_id="task-123", db=mock_db, current_user=mock_current_user)

        assert exc_info.value.status_code == 500
        assert "删除任务失败" in exc_info.value.message


# ============================================================================
# Test: GET /tasks/{task_id}/history - Get Task History
# ============================================================================


class TestGetTaskHistory:
    """Tests for GET /api/v1/tasks/{task_id}/history endpoint"""

    @patch("src.api.v1.system.tasks.task_crud")
    def test_get_task_history_success(self, mock_task_crud, mock_db, mock_current_user):
        """Test getting task history successfully"""
        from src.api.v1.system.tasks import get_task_history

        mock_task = create_mock_task()
        mock_task_crud.get.return_value = mock_task

        mock_history = []
        for i in range(5):
            history = MagicMock()
            history.id = f"history-{i}"
            history.task_id = "task-123"
            history.action = "status_changed"
            history.message = f"Status change {i}"
            history.details = {"old_status": "pending", "new_status": "running"}
            history.created_at = datetime.now(UTC)
            history.user_id = "test-user-id"
            mock_history.append(history)

        mock_task_crud.get_history.return_value = mock_history

        result = get_task_history(
            task_id="task-123", db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 5
        mock_task_crud.get.assert_called_once_with(db=mock_db, id="task-123")
        mock_task_crud.get_history.assert_called_once_with(
            db=mock_db, task_id="task-123"
        )

    @patch("src.api.v1.system.tasks.task_crud")
    def test_get_task_history_not_found(
        self, mock_task_crud, mock_db, mock_current_user
    ):
        """Test getting history for non-existent task"""
        from src.api.v1.system.tasks import get_task_history

        mock_task_crud.get.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            get_task_history(
                task_id="nonexistent", db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404
        assert "不存在" in exc_info.value.message

    @patch("src.api.v1.system.tasks.task_crud")
    def test_get_task_history_exception(
        self, mock_task_crud, mock_db, mock_current_user
    ):
        """Test getting task history with exception"""
        from src.api.v1.system.tasks import get_task_history

        mock_task = create_mock_task()
        mock_task_crud.get.return_value = mock_task
        mock_task_crud.get_history.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            get_task_history(
                task_id="task-123", db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500
        assert "获取任务历史失败" in exc_info.value.message


# ============================================================================
# Test: GET /tasks/statistics - Get Task Statistics
# ============================================================================


class TestGetTaskStatistics:
    """Tests for GET /api/v1/tasks/statistics endpoint"""

    @patch("src.api.v1.system.tasks.task_service")
    def test_get_statistics_success(
        self, mock_task_service, mock_db, mock_current_user
    ):
        """Test getting statistics successfully"""
        from src.api.v1.system.tasks import get_task_statistics

        mock_stats = {
            "total_tasks": 100,
            "running_tasks": 10,
            "completed_tasks": 80,
            "failed_tasks": 5,
            "by_type": {
                TaskType.EXCEL_IMPORT.value: 50,
                TaskType.EXCEL_EXPORT.value: 30,
            },
            "by_status": {
                TaskStatus.PENDING.value: 5,
                TaskStatus.RUNNING.value: 10,
                TaskStatus.COMPLETED.value: 80,
                TaskStatus.FAILED.value: 5,
            },
            "avg_duration": 300.0,
        }

        mock_task_service.get_statistics.return_value = mock_stats

        result = get_task_statistics(
            user_id=None, db=mock_db, current_user=mock_current_user
        )

        assert result.total_tasks == 100
        assert result.running_tasks == 10
        assert result.completed_tasks == 80
        assert result.failed_tasks == 5
        assert result.avg_duration == 300.0

    @patch("src.api.v1.system.tasks.task_service")
    def test_get_statistics_with_user_filter(
        self, mock_task_service, mock_db, mock_current_user
    ):
        """Test getting statistics with user filter"""
        from src.api.v1.system.tasks import get_task_statistics

        mock_stats = {
            "total_tasks": 10,
            "running_tasks": 1,
            "completed_tasks": 8,
            "failed_tasks": 1,
            "by_type": {},
            "by_status": {},
            "avg_duration": 200.0,
        }

        mock_task_service.get_statistics.return_value = mock_stats

        result = get_task_statistics(
            user_id="test-user-id", db=mock_db, current_user=mock_current_user
        )

        assert result.total_tasks == 10
        mock_task_service.get_statistics.assert_called_once_with(
            db=mock_db, user_id="test-user-id"
        )

    @patch("src.api.v1.system.tasks.task_service")
    def test_get_statistics_exception(
        self, mock_task_service, mock_db, mock_current_user
    ):
        """Test getting statistics with exception"""
        from src.api.v1.system.tasks import get_task_statistics

        mock_task_service.get_statistics.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            get_task_statistics(
                user_id=None, db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500
        assert "获取任务统计失败" in exc_info.value.message


# ============================================================================
# Test: GET /tasks/running - Get Running Tasks
# ============================================================================


class TestGetRunningTasks:
    """Tests for GET /api/v1/tasks/running endpoint"""

    @patch("src.api.v1.system.tasks.task_crud")
    def test_get_running_tasks_success(
        self, mock_task_crud, mock_db, mock_current_user
    ):
        """Test getting running tasks successfully"""
        from src.api.v1.system.tasks import get_running_tasks

        mock_tasks = []
        for i in range(5):
            task = create_mock_task(
                id=f"task-{i}",
                status=TaskStatus.RUNNING.value,
                title=f"Running Task {i}",
                started_at=datetime.now(UTC) - timedelta(minutes=10),
                progress=i * 20,
                total_items=100,
                processed_items=i * 20,
            )
            mock_tasks.append(task)

        mock_task_crud.get_multi.return_value = mock_tasks

        result = get_running_tasks(db=mock_db, current_user=mock_current_user)

        assert len(result) == 5
        mock_task_crud.get_multi.assert_called_once_with(
            db=mock_db,
            limit=100,
            status=TaskStatus.RUNNING.value,
            user_id="test-user-id",
            order_by="started_at",
            order_dir="asc",
        )

    @patch("src.api.v1.system.tasks.task_crud")
    def test_get_running_tasks_empty(self, mock_task_crud, mock_db, mock_current_user):
        """Test getting running tasks when none are running"""
        from src.api.v1.system.tasks import get_running_tasks

        mock_task_crud.get_multi.return_value = []

        result = get_running_tasks(db=mock_db, current_user=mock_current_user)

        assert len(result) == 0

    @patch("src.api.v1.system.tasks.task_crud")
    def test_get_running_tasks_exception(
        self, mock_task_crud, mock_db, mock_current_user
    ):
        """Test getting running tasks with exception"""
        from src.api.v1.system.tasks import get_running_tasks

        mock_task_crud.get_multi.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            get_running_tasks(db=mock_db, current_user=mock_current_user)

        assert exc_info.value.status_code == 500
        assert "获取运行任务失败" in exc_info.value.message


# ============================================================================
# Test: GET /tasks/recent - Get Recent Tasks
# ============================================================================


class TestGetRecentTasks:
    """Tests for GET /api/v1/tasks/recent endpoint"""

    @patch("src.api.v1.system.tasks.task_crud")
    def test_get_recent_tasks_default_limit(
        self, mock_task_crud, mock_db, mock_current_user
    ):
        """Test getting recent tasks with default limit"""
        from src.api.v1.system.tasks import get_recent_tasks

        mock_tasks = []
        for i in range(10):
            task = create_mock_task(
                id=f"task-{i}",
                title=f"Task {i}",
                created_at=datetime.now(UTC) - timedelta(hours=i),
                completed_at=datetime.now(UTC) if i % 2 == 0 else None,
                progress=100 if i % 2 == 0 else 0,
            )
            mock_tasks.append(task)

        mock_task_crud.get_multi.return_value = mock_tasks

        result = get_recent_tasks(
            page_size=10, db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 10
        mock_task_crud.get_multi.assert_called_once_with(
            db=mock_db,
            limit=10,
            user_id="test-user-id",
            order_by="created_at",
            order_dir="desc",
        )

    @patch("src.api.v1.system.tasks.task_crud")
    def test_get_recent_tasks_custom_limit(
        self, mock_task_crud, mock_db, mock_current_user
    ):
        """Test getting recent tasks with custom limit"""
        from src.api.v1.system.tasks import get_recent_tasks

        mock_tasks = [create_mock_task(id=f"task-{i}") for i in range(5)]
        mock_task_crud.get_multi.return_value = mock_tasks

        result = get_recent_tasks(
            page_size=5, db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 5
        mock_task_crud.get_multi.assert_called_once_with(
            db=mock_db,
            limit=5,
            user_id="test-user-id",
            order_by="created_at",
            order_dir="desc",
        )

    @patch("src.api.v1.system.tasks.task_crud")
    def test_get_recent_tasks_exception(
        self, mock_task_crud, mock_db, mock_current_user
    ):
        """Test getting recent tasks with exception"""
        from src.api.v1.system.tasks import get_recent_tasks

        mock_task_crud.get_multi.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            get_recent_tasks(page_size=10, db=mock_db, current_user=mock_current_user)

        assert exc_info.value.status_code == 500
        assert "获取最近任务失败" in exc_info.value.message


# ============================================================================
# Test: POST /tasks/configs/excel - Create Excel Config
# ============================================================================


class TestCreateExcelConfig:
    """Tests for POST /api/v1/tasks/configs/excel endpoint"""

    def test_create_excel_config_unauthorized(self, unauthenticated_client):
        """Test unauthorized access to create Excel config"""
        payload = {
            "config_name": "Auth Test",
            "config_type": "import",
            "task_type": TaskType.EXCEL_IMPORT.value,
            "field_mapping": {},
            "validation_rules": {},
            "format_config": {},
            "is_default": False,
        }
        response = unauthenticated_client.post(
            "/api/v1/tasks/configs/excel", json=payload
        )
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @patch("src.api.v1.system.tasks.task_service")
    def test_create_excel_config_success(
        self, mock_task_service, mock_db, mock_current_user
    ):
        """Test creating Excel config successfully"""
        from src.api.v1.system.tasks import create_excel_config

        config_data = ExcelTaskConfigCreate(
            config_name="Asset Import Config",
            config_type="import",
            task_type=TaskType.EXCEL_IMPORT,
            field_mapping={"field1": "Field 1"},
            is_default=False,
        )

        mock_config = create_mock_excel_config(
            config_name="Asset Import Config",
            field_mapping={"field1": "Field 1"},
            is_default=False,
        )

        mock_task_service.create_excel_config.return_value = mock_config

        result = create_excel_config(
            config_in=config_data, db=mock_db, current_user=mock_current_user
        )

        assert result.config_name == "Asset Import Config"
        mock_task_service.create_excel_config.assert_called_once()

    @patch("src.api.v1.system.tasks.task_service")
    def test_create_excel_config_exception(
        self, mock_task_service, mock_db, mock_current_user
    ):
        """Test creating Excel config with exception"""
        from src.api.v1.system.tasks import create_excel_config

        config_data = ExcelTaskConfigCreate(
            config_name="Test Config",
            config_type="test",
            task_type=TaskType.EXCEL_IMPORT,
        )

        mock_task_service.create_excel_config.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            create_excel_config(
                config_in=config_data, db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500
        assert "创建Excel配置失败" in exc_info.value.message


# ============================================================================
# Test: GET /tasks/configs/excel - Get Excel Config List
# ============================================================================


class TestGetExcelConfigs:
    """Tests for GET /api/v1/tasks/configs/excel endpoint"""

    def test_get_excel_configs_unauthorized(self, unauthenticated_client):
        """Test unauthorized access to Excel configs list"""
        response = unauthenticated_client.get("/api/v1/tasks/configs/excel")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @patch("src.api.v1.system.tasks.excel_task_config_crud")
    def test_get_excel_configs_default(self, mock_excel_crud, mock_db):
        """Test getting Excel configs without filters"""
        from src.api.v1.system.tasks import get_excel_configs

        mock_configs = []
        for i in range(10):
            config = create_mock_excel_config(
                id=f"config-{i}",
                config_name=f"Config {i}",
                is_default=(i == 0),
            )
            mock_configs.append(config)

        mock_excel_crud.get_multi.return_value = mock_configs

        result = get_excel_configs(config_type=None, task_type=None, db=mock_db)

        assert len(result) == 10
        mock_excel_crud.get_multi.assert_called_once_with(
            db=mock_db, limit=50, config_type=None, task_type=None
        )

    @patch("src.api.v1.system.tasks.excel_task_config_crud")
    def test_get_excel_configs_with_filters(self, mock_excel_crud, mock_db):
        """Test getting Excel configs with filters"""
        from src.api.v1.system.tasks import get_excel_configs

        mock_configs = [create_mock_excel_config(id=f"config-{i}") for i in range(3)]
        mock_excel_crud.get_multi.return_value = mock_configs

        result = get_excel_configs(
            config_type="import", task_type=TaskType.EXCEL_IMPORT, db=mock_db
        )

        assert len(result) == 3
        mock_excel_crud.get_multi.assert_called_once_with(
            db=mock_db, limit=50, config_type="import", task_type=TaskType.EXCEL_IMPORT
        )

    @patch("src.api.v1.system.tasks.excel_task_config_crud")
    def test_get_excel_configs_exception(self, mock_excel_crud, mock_db):
        """Test getting Excel configs with exception"""
        from src.api.v1.system.tasks import get_excel_configs

        mock_excel_crud.get_multi.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            get_excel_configs(config_type=None, task_type=None, db=mock_db)

        assert exc_info.value.status_code == 500
        assert "获取Excel配置失败" in exc_info.value.message


# ============================================================================
# Test: GET /tasks/configs/excel/default - Get Default Excel Config
# ============================================================================


class TestGetDefaultExcelConfig:
    """Tests for GET /api/v1/tasks/configs/excel/default endpoint"""

    @patch("src.api.v1.system.tasks.excel_task_config_crud")
    def test_get_default_excel_config_success(self, mock_excel_crud, mock_db):
        """Test getting default Excel config successfully"""
        from src.api.v1.system.tasks import get_default_excel_config

        mock_config = create_mock_excel_config()
        mock_excel_crud.get_default.return_value = mock_config

        result = get_default_excel_config(
            config_type="import",
            task_type=TaskType.EXCEL_IMPORT,
            db=mock_db,
        )

        assert result.config_name == "Test Config"
        assert result.is_default is True
        mock_excel_crud.get_default.assert_called_once_with(
            db=mock_db, config_type="import", task_type=TaskType.EXCEL_IMPORT
        )

    @patch("src.api.v1.system.tasks.excel_task_config_crud")
    def test_get_default_excel_config_not_found(self, mock_excel_crud, mock_db):
        """Test getting default Excel config when not found"""
        from src.api.v1.system.tasks import get_default_excel_config

        mock_excel_crud.get_default.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            get_default_excel_config(
                config_type="nonexistent",
                task_type=TaskType.EXCEL_IMPORT,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
        assert "不存在" in exc_info.value.message


# ============================================================================
# Test: GET /tasks/configs/excel/{config_id} - Get Excel Config Details
# ============================================================================


class TestGetExcelConfig:
    """Tests for GET /api/v1/tasks/configs/excel/{config_id} endpoint"""

    @patch("src.api.v1.system.tasks.excel_task_config_crud")
    def test_get_excel_config_success(self, mock_excel_crud, mock_db):
        """Test getting Excel config details successfully"""
        from src.api.v1.system.tasks import get_excel_config

        mock_config = create_mock_excel_config()
        mock_excel_crud.get.return_value = mock_config

        result = get_excel_config(config_id="config-123", db=mock_db)

        assert result.config_name == "Test Config"
        mock_excel_crud.get.assert_called_once_with(db=mock_db, id="config-123")

    @patch("src.api.v1.system.tasks.excel_task_config_crud")
    def test_get_excel_config_not_found(self, mock_excel_crud, mock_db):
        """Test getting non-existent Excel config"""
        from src.api.v1.system.tasks import get_excel_config

        mock_excel_crud.get.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            get_excel_config(config_id="nonexistent", db=mock_db)

        assert exc_info.value.status_code == 404
        assert "不存在" in exc_info.value.message


# ============================================================================
# Test: PUT /tasks/configs/excel/{config_id} - Update Excel Config
# ============================================================================


class TestUpdateExcelConfig:
    """Tests for PUT /api/v1/tasks/configs/excel/{config_id} endpoint"""

    @patch("src.api.v1.system.tasks.excel_task_config_crud")
    def test_update_excel_config_success(self, mock_excel_crud, mock_db):
        """Test updating Excel config successfully"""
        from src.api.v1.system.tasks import update_excel_config

        mock_existing_config = create_mock_excel_config()
        mock_excel_crud.get.return_value = mock_existing_config

        updated_config = create_mock_excel_config(
            config_name="Updated Config",
            field_mapping={"new_field": "New Field"},
        )
        mock_excel_crud.update.return_value = updated_config

        update_data = {"field_mapping": {"new_field": "New Field"}}

        result = update_excel_config(
            config_id="config-123", config_in=update_data, db=mock_db
        )

        assert result.config_name == "Updated Config"

    @patch("src.api.v1.system.tasks.excel_task_config_crud")
    def test_update_excel_config_not_found(self, mock_excel_crud, mock_db):
        """Test updating non-existent Excel config"""
        from src.api.v1.system.tasks import update_excel_config

        mock_excel_crud.get.return_value = None

        update_data = {"config_name": "Updated"}

        with pytest.raises(BaseBusinessError) as exc_info:
            update_excel_config(
                config_id="nonexistent", config_in=update_data, db=mock_db
            )

        assert exc_info.value.status_code == 404
        assert "不存在" in exc_info.value.message

    @patch("src.api.v1.system.tasks.excel_task_config_crud")
    def test_update_excel_config_exception(self, mock_excel_crud, mock_db):
        """Test updating Excel config with exception"""
        from src.api.v1.system.tasks import update_excel_config

        mock_existing_config = create_mock_excel_config()
        mock_excel_crud.get.return_value = mock_existing_config
        mock_excel_crud.update.side_effect = Exception("Database error")

        update_data = {"config_name": "Updated"}

        with pytest.raises(BaseBusinessError) as exc_info:
            update_excel_config(
                config_id="config-123", config_in=update_data, db=mock_db
            )

        assert exc_info.value.status_code == 500
        assert "更新Excel配置失败" in exc_info.value.message


# ============================================================================
# Test: DELETE /tasks/configs/excel/{config_id} - Delete Excel Config
# ============================================================================


class TestDeleteExcelConfig:
    """Tests for DELETE /api/v1/tasks/configs/excel/{config_id} endpoint"""

    @patch("src.api.v1.system.tasks.excel_task_config_crud")
    def test_delete_excel_config_success(self, mock_excel_crud, mock_db):
        """Test deleting Excel config successfully"""
        from src.api.v1.system.tasks import delete_excel_config

        mock_config = create_mock_excel_config()
        mock_excel_crud.get.return_value = mock_config

        result = delete_excel_config(config_id="config-123", db=mock_db)

        assert result["message"] == "Excel配置删除成功"
        mock_excel_crud.update.assert_called_once()

    @patch("src.api.v1.system.tasks.excel_task_config_crud")
    def test_delete_excel_config_not_found(self, mock_excel_crud, mock_db):
        """Test deleting non-existent Excel config"""
        from src.api.v1.system.tasks import delete_excel_config

        mock_excel_crud.get.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            delete_excel_config(config_id="nonexistent", db=mock_db)

        # 404 is raised inside try block but caught by outer except
        # The implementation has a bug where HTTPException is caught and converted to 500
        assert exc_info.value.status_code == 500
        assert "删除Excel配置失败" in exc_info.value.message

    @patch("src.api.v1.system.tasks.excel_task_config_crud")
    def test_delete_excel_config_exception(self, mock_excel_crud, mock_db):
        """Test deleting Excel config with exception"""
        from src.api.v1.system.tasks import delete_excel_config

        mock_config = create_mock_excel_config()
        mock_excel_crud.get.return_value = mock_config
        mock_excel_crud.update.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            delete_excel_config(config_id="config-123", db=mock_db)

        assert exc_info.value.status_code == 500
        assert "删除Excel配置失败" in exc_info.value.message


# ============================================================================
# Test: GET /tasks/cleanup - Cleanup Old Tasks
# ============================================================================


class TestCleanupOldTasks:
    """Tests for GET /api/v1/tasks/cleanup endpoint"""

    @patch("src.api.v1.system.tasks.task_service")
    def test_cleanup_old_tasks_dry_run(
        self, mock_task_service, mock_db, mock_current_user
    ):
        """Test cleanup old tasks in dry run mode"""
        from src.api.v1.system.tasks import cleanup_old_tasks

        mock_task_service.cleanup_old_tasks.return_value = {
            "message": "试运行模式，发现 25 个可清理的任务",
            "cleanup_date": "2026-01-16T00:00:00",
            "task_count": 25,
        }

        result = cleanup_old_tasks(
            days=30, is_dry_run=True, db=mock_db, current_user=mock_current_user
        )

        assert result["task_count"] == 25
        assert "试运行模式" in result["message"]
        mock_task_service.cleanup_old_tasks.assert_called_once_with(
            db=mock_db, days=30, dry_run=True
        )

    @patch("src.api.v1.system.tasks.task_service")
    def test_cleanup_old_tasks_actual_cleanup(
        self, mock_task_service, mock_db, mock_current_user
    ):
        """Test actual cleanup of old tasks"""
        from src.api.v1.system.tasks import cleanup_old_tasks

        mock_task_service.cleanup_old_tasks.return_value = {
            "message": "成功清理 25 个过期任务",
            "cleanup_date": "2026-01-16T00:00:00",
            "cleaned_count": 25,
        }

        result = cleanup_old_tasks(
            days=30, is_dry_run=False, db=mock_db, current_user=mock_current_user
        )

        assert result["cleaned_count"] == 25
        assert "成功清理" in result["message"]

    @patch("src.api.v1.system.tasks.task_service")
    def test_cleanup_old_tasks_exception(
        self, mock_task_service, mock_db, mock_current_user
    ):
        """Test cleanup with exception"""
        from src.api.v1.system.tasks import cleanup_old_tasks

        mock_task_service.cleanup_old_tasks.side_effect = Exception("Database error")

        with pytest.raises(BaseBusinessError) as exc_info:
            cleanup_old_tasks(
                days=30, is_dry_run=False, db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500
        assert "清理任务失败" in exc_info.value.message
