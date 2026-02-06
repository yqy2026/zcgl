"""
任务 CRUD 单元测试（异步）

覆盖 TaskCRUD 与 ExcelTaskConfigCRUD 的主要异步方法。
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.task import (
    ExcelTaskConfigCRUD,
    TaskCRUD,
    excel_task_config_crud,
    task_crud,
)
from src.enums.task import TaskStatus, TaskType
from src.models.task import AsyncTask, ExcelTaskConfig, TaskHistory

pytestmark = pytest.mark.asyncio


def _result_with_scalar(value: object | None) -> MagicMock:
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _result_with_scalars(values: list[object] | None = None) -> MagicMock:
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values or []
    scalars.first.return_value = (values or [None])[0] if values is not None else None
    result.scalars.return_value = scalars
    return result


def _result_with_all(values: list[tuple[object, object]] | None = None) -> MagicMock:
    result = MagicMock()
    result.all.return_value = values or []
    return result


class TestTaskCRUDGetMulti:
    """测试 TaskCRUD get_multi_async 方法"""

    @pytest.fixture
    def crud(self):
        return TaskCRUD(AsyncTask)

    @pytest.fixture
    def mock_db(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([]))
        return mock_db

    async def test_get_multi_default_params(self, crud, mock_db):
        result = await crud.get_multi_async(mock_db)
        assert isinstance(result, list)
        mock_db.execute.assert_awaited()

    async def test_get_multi_with_filters(self, crud, mock_db):
        result = await crud.get_multi_async(
            mock_db,
            task_type="excel_import",
            status="running",
            user_id="user-123",
            created_after=datetime.now() - timedelta(days=7),
            created_before=datetime.now(),
        )
        assert isinstance(result, list)

    async def test_get_multi_with_pagination(self, crud, mock_db):
        result = await crud.get_multi_async(mock_db, skip=10, limit=20)
        assert isinstance(result, list)

    async def test_get_multi_with_order(self, crud, mock_db):
        result = await crud.get_multi_async(
            mock_db, order_by="created_at", order_dir="asc"
        )
        assert isinstance(result, list)


class TestTaskCRUDCount:
    """测试 TaskCRUD count_async 方法"""

    @pytest.fixture
    def crud(self):
        return TaskCRUD(AsyncTask)

    @pytest.fixture
    def mock_db(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_result_with_scalar(5))
        return mock_db

    async def test_count_all_active(self, crud, mock_db):
        result = await crud.count_async(mock_db)
        assert result == 5

    async def test_count_with_filters(self, crud, mock_db):
        result = await crud.count_async(mock_db, filters={"user_id": "user-1"})
        assert result == 5

    async def test_count_with_task_type(self, crud, mock_db):
        result = await crud.count_async(mock_db, task_type="excel_export")
        assert result == 5


class TestTaskCRUDGetStatistics:
    """测试 TaskCRUD get_statistics_async 方法"""

    @pytest.fixture
    def crud(self):
        return TaskCRUD(AsyncTask)

    @pytest.fixture
    def mock_db(self):
        mock_db = AsyncMock()
        count_results = [_result_with_scalar(0)] * (
            4 + len(TaskType) + len(TaskStatus)
        )
        mock_db.execute = AsyncMock(
            side_effect=[*count_results, _result_with_all([])]
        )
        return mock_db

    async def test_get_statistics_basic(self, crud, mock_db):
        result = await crud.get_statistics_async(mock_db)

        assert "total_tasks" in result
        assert "running_tasks" in result
        assert "completed_tasks" in result
        assert "failed_tasks" in result
        assert "by_type" in result
        assert "by_status" in result
        assert "avg_duration" in result

    async def test_get_statistics_with_user_id(self, crud, mock_db):
        result = await crud.get_statistics_async(mock_db, user_id="user-123")
        assert isinstance(result, dict)

    async def test_get_statistics_avg_duration_calculation(self, crud):
        now = datetime.now()
        rows = [(now - timedelta(seconds=100), now), (now - timedelta(seconds=200), now)]
        mock_db = AsyncMock()
        count_results = [_result_with_scalar(2)] * (
            4 + len(TaskType) + len(TaskStatus)
        )
        mock_db.execute = AsyncMock(
            side_effect=[*count_results, _result_with_all(rows)]
        )

        result = await crud.get_statistics_async(mock_db)
        assert result["avg_duration"] > 0


class TestTaskCRUDGetHistory:
    """测试 TaskCRUD get_history_async 方法"""

    @pytest.fixture
    def crud(self):
        return TaskCRUD(AsyncTask)

    async def test_get_history_exists(self, crud):
        mock_db = AsyncMock()
        mock_histories = [
            MagicMock(spec=TaskHistory),
            MagicMock(spec=TaskHistory),
        ]
        mock_db.execute = AsyncMock(return_value=_result_with_scalars(mock_histories))

        result = await crud.get_history_async(mock_db, task_id="task-1")
        assert len(result) == 2

    async def test_get_history_empty(self, crud):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([]))

        result = await crud.get_history_async(mock_db, task_id="task-not-exist")
        assert result == []


class TestExcelTaskConfigCRUDGetDefault:
    """测试 ExcelTaskConfigCRUD get_default_async 方法"""

    @pytest.fixture
    def crud(self):
        return ExcelTaskConfigCRUD(ExcelTaskConfig)

    async def test_get_default_exists(self, crud):
        mock_db = AsyncMock()
        mock_config = MagicMock(spec=ExcelTaskConfig)
        mock_config.is_default = True

        mock_db.execute = AsyncMock(return_value=_result_with_scalars([mock_config]))

        result = await crud.get_default_async(
            mock_db, config_type="import", task_type="asset"
        )
        assert result is not None
        assert result.is_default is True

    async def test_get_default_not_exists(self, crud):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([]))

        result = await crud.get_default_async(
            mock_db, config_type="export", task_type="not-exist"
        )
        assert result is None


class TestExcelTaskConfigCRUDGetMulti:
    """测试 ExcelTaskConfigCRUD get_multi_async 方法"""

    @pytest.fixture
    def crud(self):
        return ExcelTaskConfigCRUD(ExcelTaskConfig)

    async def test_get_multi_default_params(self, crud):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([]))

        result = await crud.get_multi_async(mock_db)
        assert isinstance(result, list)

    async def test_get_multi_with_filters(self, crud):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([]))

        result = await crud.get_multi_async(
            mock_db, config_type="import", task_type="asset"
        )
        assert isinstance(result, list)


class TestCRUDInstances:
    """测试 CRUD 实例"""

    async def test_task_crud_instance(self):
        assert task_crud is not None
        assert isinstance(task_crud, TaskCRUD)

    async def test_excel_task_config_crud_instance(self):
        assert excel_task_config_crud is not None
        assert isinstance(excel_task_config_crud, ExcelTaskConfigCRUD)
