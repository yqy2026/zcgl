from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from src.enums.task import TaskStatus, TaskType
from src.models.task import AsyncTask
from src.schemas.task import TaskCreate, TaskUpdate
from src.services.task.service import TaskService

TEST_TASK_ID = "task_123"
TEST_USER_ID = "user_123"

@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

@pytest.fixture
def service():
    return TaskService()

class TestTaskService:
    def test_create_task(self, service, mock_db):
        obj_in = TaskCreate(
            task_type=TaskType.EXCEL_EXPORT,
            title="Export Task",
            description="Export data",
            parameters={"p": 1}
        )
        
        result = service.create_task(mock_db, obj_in=obj_in, user_id=TEST_USER_ID)
        
        assert result.title == "Export Task"
        assert result.status == TaskStatus.PENDING
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_update_task_status(self, service, mock_db):
        task = AsyncTask(id=TEST_TASK_ID, status=TaskStatus.PENDING, user_id=TEST_USER_ID)
        
        with patch("src.crud.task.task_crud.get", return_value=task):
            result = service.update_task_status(
                mock_db, task_id=TEST_TASK_ID, status=TaskStatus.RUNNING
            )
            
            assert result.status == TaskStatus.RUNNING
            assert result.started_at is not None
            mock_db.commit.assert_called()
            
            # Verify history created
            mock_db.add.assert_called() # Task + History

    def test_update_task_status_completed(self, service, mock_db):
        task = AsyncTask(id=TEST_TASK_ID, status=TaskStatus.RUNNING, user_id=TEST_USER_ID)
        
        with patch("src.crud.task.task_crud.get", return_value=task):
            result = service.update_task_status(
                mock_db, task_id=TEST_TASK_ID, status=TaskStatus.COMPLETED
            )
            
            assert result.status == TaskStatus.COMPLETED
            assert result.completed_at is not None
            assert result.progress == 100

    def test_cancel_task(self, service, mock_db):
        task = AsyncTask(id=TEST_TASK_ID, status=TaskStatus.RUNNING, user_id=TEST_USER_ID)
        
        with patch("src.crud.task.task_crud.get", return_value=task):
            result = service.cancel_task(mock_db, task_id=TEST_TASK_ID, reason="Manual")
            
            assert result.status == TaskStatus.CANCELLED
            assert "Manual" in result.error_message
            
    def test_cancel_task_invalid_state(self, service, mock_db):
        task = AsyncTask(id=TEST_TASK_ID, status=TaskStatus.COMPLETED, user_id=TEST_USER_ID)
        
        with patch("src.crud.task.task_crud.get", return_value=task):
            with pytest.raises(ValueError) as excinfo:
                service.cancel_task(mock_db, task_id=TEST_TASK_ID)
            
            assert "无法取消" in str(excinfo.value)

    def test_delete_task(self, service, mock_db):
        task = AsyncTask(id=TEST_TASK_ID, is_active=True, user_id=TEST_USER_ID)
        
        with patch("src.crud.task.task_crud.get", return_value=task):
            service.delete_task(mock_db, task_id=TEST_TASK_ID)
            
            assert task.is_active is False
            mock_db.commit.assert_called()
