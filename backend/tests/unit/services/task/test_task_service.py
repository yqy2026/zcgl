"""
测试任务服务（异步）
"""

import inspect
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import OperationNotAllowedError, ResourceNotFoundError
from src.enums.task import TaskStatus, TaskType
from src.models.task import AsyncTask, ExcelTaskConfig, TaskHistory
from src.schemas.task import ExcelTaskConfigCreate, TaskCreate, TaskUpdate
from src.services.task.service import TaskService

pytestmark = pytest.mark.asyncio


async def test_task_service_module_should_not_use_datetime_utcnow() -> None:
    """任务服务模块不应直接调用 datetime.utcnow。"""
    from src.services.task import service as task_service_module

    module_source = inspect.getsource(task_service_module)
    assert "datetime.utcnow(" not in module_source


def _result_with_scalars(values: list[object] | None = None) -> MagicMock:
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values or []
    result.scalars.return_value = scalars
    return result


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def task_service():
    return TaskService()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_task():
    task = MagicMock(spec=AsyncTask)
    task.id = "task_123"
    task.task_type = "excel_import"
    task.title = "测试任务"
    task.description = "测试描述"
    task.status = TaskStatus.PENDING
    task.progress = 0
    task.user_id = "user_123"
    task.created_at = datetime.now(UTC)
    task.started_at = None
    task.completed_at = None
    return task


@pytest.fixture
def mock_history():
    history = MagicMock(spec=TaskHistory)
    history.id = "history_123"
    history.task_id = "task_123"
    history.action = "created"
    history.message = "任务已创建"
    return history


# ============================================================================
# Test create_task
# ============================================================================


class TestCreateTask:
    async def test_create_task_success(self, task_service, mock_db):
        obj_in = TaskCreate(
            task_type="excel_import",
            title="新任务",
            description="任务描述",
            parameters={"file": "test.xlsx"},
        )

        result = await task_service.create_task(
            mock_db, obj_in=obj_in, user_id="user_123"
        )

        assert result.title == "新任务"
        assert mock_db.add.call_count >= 1
        assert mock_db.commit.await_count >= 1

    async def test_create_task_without_user(self, task_service, mock_db):
        obj_in = TaskCreate(task_type="excel_import", title="新任务")

        result = await task_service.create_task(mock_db, obj_in=obj_in)

        assert result.title == "新任务"
        assert mock_db.commit.await_count >= 1

    async def test_create_task_logs_history(self, task_service, mock_db):
        obj_in = TaskCreate(task_type="excel_import", title="历史任务")

        with patch.object(task_service, "create_history", new_callable=AsyncMock) as m:
            await task_service.create_task(mock_db, obj_in=obj_in, user_id="user_123")
            m.assert_awaited_once()
            call_args = m.call_args
            assert call_args.kwargs["action"] == "created"
            assert "已创建" in call_args.kwargs["message"]


# ============================================================================
# Test update_task_status
# ============================================================================


class TestUpdateTaskStatus:
    async def test_update_status_to_running(self, task_service, mock_db, mock_task):
        mock_task.status = TaskStatus.PENDING

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = mock_task
            result = await task_service.update_task_status(
                mock_db, task_id="task_123", status=TaskStatus.RUNNING
            )

            assert result is not None
            mock_db.commit.assert_awaited()

    async def test_update_status_to_completed(self, task_service, mock_db, mock_task):
        mock_task.status = TaskStatus.RUNNING

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = mock_task
            result = await task_service.update_task_status(
                mock_db, task_id="task_123", status=TaskStatus.COMPLETED
            )

            assert result is not None
            mock_db.commit.assert_awaited()

    async def test_update_status_to_failed(self, task_service, mock_db, mock_task):
        mock_task.status = TaskStatus.RUNNING

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = mock_task
            result = await task_service.update_task_status(
                mock_db,
                task_id="task_123",
                status=TaskStatus.FAILED,
                error_message="处理失败",
            )

            assert result is not None
            mock_db.commit.assert_awaited()

    async def test_update_status_task_not_found(self, task_service, mock_db):
        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = None
            with pytest.raises(ResourceNotFoundError, match="任务"):
                await task_service.update_task_status(
                    mock_db, task_id="nonexistent", status=TaskStatus.RUNNING
                )

    async def test_update_status_logs_history(self, task_service, mock_db, mock_task):
        mock_task.status = TaskStatus.PENDING

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = mock_task
            with patch.object(
                task_service, "create_history", new_callable=AsyncMock
            ) as m_history:
                await task_service.update_task_status(
                    mock_db, task_id="task_123", status=TaskStatus.RUNNING
                )
                m_history.assert_awaited_once()


# ============================================================================
# Test update_task
# ============================================================================


class TestUpdateTask:
    async def test_update_task_basic(self, task_service, mock_db, mock_task):
        mock_task.status = TaskStatus.RUNNING
        obj_in = TaskUpdate(title="更新后的标题")

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = mock_task
            result = await task_service.update_task(
                mock_db, task_id="task_123", obj_in=obj_in
            )

            assert result is not None
            mock_db.commit.assert_awaited()

    async def test_update_task_completed_fails(
        self, task_service, mock_db, mock_task
    ):
        mock_task.status = TaskStatus.COMPLETED
        obj_in = TaskUpdate(title="新标题")

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = mock_task
            with pytest.raises(OperationNotAllowedError, match="已完成"):
                await task_service.update_task(
                    mock_db, task_id="task_123", obj_in=obj_in
                )

    async def test_update_task_with_status_change(
        self, task_service, mock_db, mock_task
    ):
        mock_task.status = TaskStatus.PENDING
        obj_in = TaskUpdate(status=TaskStatus.RUNNING)

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = mock_task
            with patch.object(
                task_service, "create_history", new_callable=AsyncMock
            ) as m_history:
                result = await task_service.update_task(
                    mock_db, task_id="task_123", obj_in=obj_in
                )

                assert result is not None
                m_history.assert_awaited_once()

    async def test_update_task_not_found(self, task_service, mock_db):
        obj_in = TaskUpdate(title="新标题")

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = None
            with pytest.raises(ResourceNotFoundError, match="任务"):
                await task_service.update_task(
                    mock_db, task_id="nonexistent", obj_in=obj_in
                )


# ============================================================================
# Test cancel_task
# ============================================================================


class TestCancelTask:
    async def test_cancel_task_pending(self, task_service, mock_db, mock_task):
        mock_task.status = TaskStatus.PENDING

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = mock_task
            with patch.object(
                task_service, "update_task_status", new_callable=AsyncMock
            ) as m_update:
                result = await task_service.cancel_task(mock_db, task_id="task_123")

                assert result is not None
                m_update.assert_awaited_once()

    async def test_cancel_task_running(self, task_service, mock_db, mock_task):
        mock_task.status = TaskStatus.RUNNING

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = mock_task
            with patch.object(
                task_service, "update_task_status", new_callable=AsyncMock
            ):
                result = await task_service.cancel_task(
                    mock_db, task_id="task_123", reason="用户取消"
                )

                assert result is not None

    async def test_cancel_task_not_found(self, task_service, mock_db):
        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = None
            with pytest.raises(ResourceNotFoundError, match="任务"):
                await task_service.cancel_task(mock_db, task_id="nonexistent")

    async def test_cancel_task_already_completed(
        self, task_service, mock_db, mock_task
    ):
        mock_task.status = TaskStatus.COMPLETED

        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = mock_task
            with pytest.raises(OperationNotAllowedError, match="任务无法取消"):
                await task_service.cancel_task(mock_db, task_id="task_123")


# ============================================================================
# Test delete_task
# ============================================================================


class TestDeleteTask:
    async def test_delete_task_success(self, task_service, mock_db, mock_task):
        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = mock_task
            with patch.object(
                task_service, "create_history", new_callable=AsyncMock
            ) as m_history:
                await task_service.delete_task(mock_db, task_id="task_123")

                mock_db.commit.assert_awaited()
                m_history.assert_awaited_once()

    async def test_delete_task_not_found(self, task_service, mock_db):
        with patch("src.crud.task.task_crud.get", new_callable=AsyncMock) as m_get:
            m_get.return_value = None
            with pytest.raises(ResourceNotFoundError, match="任务"):
                await task_service.delete_task(mock_db, task_id="nonexistent")


# ============================================================================
# Test create_history
# ============================================================================


class TestCreateHistory:
    async def test_create_history_basic(self, task_service, mock_db):
        result = await task_service.create_history(
            mock_db,
            task_id="task_123",
            action="created",
            message="任务已创建",
            user_id="user_123",
        )

        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    async def test_create_history_with_details(self, task_service, mock_db):
        details = {"old_status": "pending", "new_status": "running"}

        result = await task_service.create_history(
            mock_db,
            task_id="task_123",
            action="status_changed",
            message="状态已更改",
            details=details,
        )

        assert result is not None
        mock_db.add.assert_called_once()


# ============================================================================
# Test get_statistics
# ============================================================================


class TestGetStatistics:
    async def test_get_statistics_basic(self, task_service, mock_db):
        stats = {"total": 10, "active": 5, "completed": 3}

        with patch(
            "src.crud.task.task_crud.get_statistics_async", new_callable=AsyncMock
        ) as m_stats:
            m_stats.return_value = stats
            result = await task_service.get_statistics(mock_db)
            assert result == stats

    async def test_get_statistics_with_user(self, task_service, mock_db):
        stats = {"total": 5, "active": 2}

        with patch(
            "src.crud.task.task_crud.get_statistics_async", new_callable=AsyncMock
        ) as m_stats:
            m_stats.return_value = stats
            result = await task_service.get_statistics(mock_db, user_id="user_123")
            m_stats.assert_awaited_with(mock_db, user_id="user_123")
            assert result == stats


# ============================================================================
# Test cleanup_old_tasks
# ============================================================================


class TestCleanupOldTasks:
    async def test_cleanup_dry_run(self, task_service, mock_db):
        old_task1 = MagicMock(spec=AsyncTask)
        old_task2 = MagicMock(spec=AsyncTask)

        mock_db.execute = AsyncMock(return_value=_result_with_scalars([old_task1, old_task2]))

        result = await task_service.cleanup_old_tasks(mock_db, days=30, dry_run=True)

        assert result["task_count"] == 2
        assert "试运行" in result["message"]
        mock_db.commit.assert_not_awaited()

    async def test_cleanup_actual(self, task_service, mock_db):
        old_task = MagicMock(spec=AsyncTask)
        old_task.task_type = TaskType.EXCEL_EXPORT
        old_task.result_data = {}

        mock_db.execute = AsyncMock(return_value=_result_with_scalars([old_task]))

        result = await task_service.cleanup_old_tasks(mock_db, days=30, dry_run=False)

        assert result["cleaned_count"] == 1
        assert "成功清理" in result["message"]
        mock_db.commit.assert_awaited_once()

    async def test_cleanup_empty(self, task_service, mock_db):
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([]))

        result = await task_service.cleanup_old_tasks(mock_db, days=30, dry_run=False)

        assert result["cleaned_count"] == 0


# ============================================================================
# Test create_excel_config
# ============================================================================


class TestCreateExcelConfig:
    async def test_create_excel_config_basic(self, task_service, mock_db):
        obj_in = ExcelTaskConfigCreate(
            config_name="测试配置",
            config_type="asset_import",
            task_type="excel_import",
            is_default=False,
        )

        mock_config = MagicMock(spec=ExcelTaskConfig)
        mock_config.id = "config_123"

        with patch(
            "src.crud.task.excel_task_config_crud.create", new_callable=AsyncMock
        ) as m_create:
            m_create.return_value = mock_config
            result = await task_service.create_excel_config(mock_db, obj_in=obj_in)

            assert result is not None

    async def test_create_excel_config_with_default(self, task_service, mock_db):
        obj_in = ExcelTaskConfigCreate(
            config_name="默认配置",
            config_type="asset_import",
            task_type="excel_import",
            is_default=True,
        )

        mock_config = MagicMock(spec=ExcelTaskConfig)
        mock_config.id = "config_123"

        with patch(
            "src.crud.task.excel_task_config_crud.create", new_callable=AsyncMock
        ) as m_create:
            m_create.return_value = mock_config
            result = await task_service.create_excel_config(mock_db, obj_in=obj_in)

            assert result is not None
            mock_db.execute.assert_awaited_once()
