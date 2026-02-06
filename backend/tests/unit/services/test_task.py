from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import OperationNotAllowedError
from src.enums.task import TaskStatus, TaskType
from src.models.task import AsyncTask
from src.schemas.task import TaskCreate
from src.services.task.service import TaskService

pytestmark = pytest.mark.asyncio

TEST_TASK_ID = "task_123"
TEST_USER_ID = "user_123"


@pytest.fixture
def service():
    return TaskService()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


class TestTaskService:
    async def test_create_task(self, service, mock_db):
        obj_in = TaskCreate(
            task_type=TaskType.EXCEL_EXPORT,
            title="Export Task",
            description="Export data",
            parameters={"p": 1},
        )

        result = await service.create_task(
            mock_db, obj_in=obj_in, user_id=TEST_USER_ID
        )

        assert result.title == "Export Task"
        assert result.status == TaskStatus.PENDING
        mock_db.add.assert_called()
        mock_db.commit.assert_awaited()

    async def test_update_task_status(self, service, mock_db):
        task = AsyncTask(
            id=TEST_TASK_ID, status=TaskStatus.PENDING, user_id=TEST_USER_ID
        )

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = task
            result = await service.update_task_status(
                mock_db, task_id=TEST_TASK_ID, status=TaskStatus.RUNNING
            )

            assert result.status == TaskStatus.RUNNING
            assert result.started_at is not None
            mock_db.commit.assert_awaited()

    async def test_update_task_status_completed(self, service, mock_db):
        task = AsyncTask(
            id=TEST_TASK_ID, status=TaskStatus.RUNNING, user_id=TEST_USER_ID
        )

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = task
            result = await service.update_task_status(
                mock_db, task_id=TEST_TASK_ID, status=TaskStatus.COMPLETED
            )

            assert result.status == TaskStatus.COMPLETED
            assert result.completed_at is not None
            assert result.progress == 100

    async def test_cancel_task(self, service, mock_db):
        task = AsyncTask(
            id=TEST_TASK_ID, status=TaskStatus.RUNNING, user_id=TEST_USER_ID
        )

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = task
            with patch.object(
                service, "update_task_status", new_callable=AsyncMock
            ) as m_update:
                m_update.return_value = task
                result = await service.cancel_task(
                    mock_db, task_id=TEST_TASK_ID, reason="Manual"
                )

                assert result.status == TaskStatus.RUNNING

    async def test_cancel_task_invalid_state(self, service, mock_db):
        task = AsyncTask(
            id=TEST_TASK_ID, status=TaskStatus.COMPLETED, user_id=TEST_USER_ID
        )

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = task
            with pytest.raises(OperationNotAllowedError) as excinfo:
                await service.cancel_task(mock_db, task_id=TEST_TASK_ID)

            assert "无法取消" in str(excinfo.value)

    async def test_delete_task(self, service, mock_db):
        task = AsyncTask(id=TEST_TASK_ID, is_active=True, user_id=TEST_USER_ID)

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = task
            with patch.object(
                service, "create_history", new_callable=AsyncMock
            ) as m_history:
                await service.delete_task(mock_db, task_id=TEST_TASK_ID)

                assert task.is_active is False
                mock_db.commit.assert_awaited()
                m_history.assert_awaited()
