"""
任务 CRUD 单元测试

测试 TaskCRUD 和 ExcelTaskConfigCRUD 的所有主要方法
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.crud.task import (
    ExcelTaskConfigCRUD,
    TaskCRUD,
    excel_task_config_crud,
    task_crud,
)
from src.models.task import AsyncTask, ExcelTaskConfig, TaskHistory


class TestTaskCRUDGetMulti:
    """测试 TaskCRUD get_multi 方法"""

    @pytest.fixture
    def crud(self):
        return TaskCRUD(AsyncTask)

    @pytest.fixture
    def mock_db(self, db_session):
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        db_session.query = MagicMock(return_value=mock_query)
        return db_session

    def test_get_multi_default_params(self, crud, mock_db):
        """测试默认参数获取任务列表"""
        result = crud.get_multi(mock_db)

        assert isinstance(result, list)
        mock_db.query.assert_called_once_with(AsyncTask)

    def test_get_multi_with_task_type_filter(self, crud, mock_db):
        """测试按任务类型筛选"""
        crud.get_multi(mock_db, task_type="excel_import")

        # 验证 filter 被调用
        assert mock_db.query.return_value.filter.called

    def test_get_multi_with_status_filter(self, crud, mock_db):
        """测试按状态筛选"""
        crud.get_multi(mock_db, status="running")

        assert mock_db.query.return_value.filter.called

    def test_get_multi_with_user_id_filter(self, crud, mock_db):
        """测试按用户ID筛选"""
        crud.get_multi(mock_db, user_id="user-123")

        assert mock_db.query.return_value.filter.called

    def test_get_multi_with_date_range(self, crud, mock_db):
        """测试按日期范围筛选"""
        now = datetime.now()
        crud.get_multi(
            mock_db,
            created_after=now - timedelta(days=7),
            created_before=now,
        )

        assert mock_db.query.return_value.filter.called

    def test_get_multi_with_pagination(self, crud, mock_db):
        """测试分页参数"""
        crud.get_multi(mock_db, skip=10, limit=20)

        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.assert_called_with(
            10
        )

    def test_get_multi_with_order_asc(self, crud, mock_db):
        """测试升序排序"""
        crud.get_multi(mock_db, order_by="created_at", order_dir="asc")

        assert mock_db.query.return_value.filter.return_value.order_by.called


class TestTaskCRUDCount:
    """测试 TaskCRUD count 方法"""

    @pytest.fixture
    def crud(self):
        return TaskCRUD(AsyncTask)

    @pytest.fixture
    def mock_db(self, db_session):
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 5
        db_session.query = MagicMock(return_value=mock_query)
        return db_session

    def test_count_all_active(self, crud, mock_db):
        """测试统计所有活跃任务"""
        result = crud.count(mock_db)

        assert result == 5

    def test_count_with_filters(self, crud, mock_db):
        """测试带筛选条件的统计"""
        result = crud.count(mock_db, filters={"user_id": "user-1"})

        assert result == 5
        assert mock_db.query.return_value.filter.called

    def test_count_with_task_type(self, crud, mock_db):
        """测试按任务类型统计"""
        result = crud.count(mock_db, task_type="excel_export")

        assert result == 5


class TestTaskCRUDGetStatistics:
    """测试 TaskCRUD get_statistics 方法"""

    @pytest.fixture
    def crud(self):
        return TaskCRUD(AsyncTask)

    @pytest.fixture
    def mock_db(self, db_session):
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 10
        mock_query.all.return_value = []
        db_session.query = MagicMock(return_value=mock_query)
        return db_session

    def test_get_statistics_basic(self, crud, mock_db):
        """测试获取基本统计信息"""
        result = crud.get_statistics(mock_db)

        assert "total_tasks" in result
        assert "running_tasks" in result
        assert "completed_tasks" in result
        assert "failed_tasks" in result
        assert "by_type" in result
        assert "by_status" in result
        assert "avg_duration" in result

    def test_get_statistics_with_user_id(self, crud, mock_db):
        """测试按用户获取统计"""
        result = crud.get_statistics(mock_db, user_id="user-123")

        assert isinstance(result, dict)

    def test_get_statistics_avg_duration_calculation(self, crud, mock_db):
        """测试平均持续时间计算"""
        now = datetime.now()
        mock_task1 = MagicMock()
        mock_task1.started_at = now - timedelta(seconds=100)
        mock_task1.completed_at = now

        mock_task2 = MagicMock()
        mock_task2.started_at = now - timedelta(seconds=200)
        mock_task2.completed_at = now

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 2
        mock_query.all.return_value = [mock_task1, mock_task2]
        mock_db.query.return_value = mock_query

        result = crud.get_statistics(mock_db)

        # 验证返回结构
        assert "avg_duration" in result


class TestTaskCRUDGetHistory:
    """测试 TaskCRUD get_history 方法"""

    @pytest.fixture
    def crud(self):
        return TaskCRUD(AsyncTask)

    @pytest.fixture
    def mock_db(self, db_session):
        db_session.query = MagicMock()
        return db_session

    def test_get_history_exists(self, crud, mock_db):
        """测试获取存在的任务历史"""
        mock_histories = [
            MagicMock(spec=TaskHistory),
            MagicMock(spec=TaskHistory),
        ]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_histories

        result = crud.get_history(mock_db, task_id="task-1")

        assert len(result) == 2

    def test_get_history_empty(self, crud, mock_db):
        """测试获取空历史"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = crud.get_history(mock_db, task_id="task-not-exist")

        assert result == []


class TestExcelTaskConfigCRUDGetDefault:
    """测试 ExcelTaskConfigCRUD get_default 方法"""

    @pytest.fixture
    def crud(self):
        return ExcelTaskConfigCRUD(ExcelTaskConfig)

    @pytest.fixture
    def mock_db(self, db_session):
        db_session.query = MagicMock()
        return db_session

    def test_get_default_exists(self, crud, mock_db):
        """测试获取存在的默认配置"""
        mock_config = MagicMock(spec=ExcelTaskConfig)
        mock_config.is_default = True

        mock_db.query.return_value.filter.return_value.first.return_value = mock_config

        result = crud.get_default(mock_db, config_type="import", task_type="asset")

        assert result is not None
        assert result.is_default is True

    def test_get_default_not_exists(self, crud, mock_db):
        """测试获取不存在的默认配置"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = crud.get_default(mock_db, config_type="export", task_type="not-exist")

        assert result is None


class TestExcelTaskConfigCRUDGetMulti:
    """测试 ExcelTaskConfigCRUD get_multi 方法"""

    @pytest.fixture
    def crud(self):
        return ExcelTaskConfigCRUD(ExcelTaskConfig)

    @pytest.fixture
    def mock_db(self, db_session):
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        db_session.query = MagicMock(return_value=mock_query)
        return db_session

    def test_get_multi_default_params(self, crud, mock_db):
        """测试默认参数获取配置列表"""
        result = crud.get_multi(mock_db)

        assert isinstance(result, list)

    def test_get_multi_with_config_type(self, crud, mock_db):
        """测试按配置类型筛选"""
        crud.get_multi(mock_db, config_type="import")

        assert mock_db.query.return_value.filter.called

    def test_get_multi_with_task_type(self, crud, mock_db):
        """测试按任务类型筛选"""
        crud.get_multi(mock_db, task_type="asset")

        assert mock_db.query.return_value.filter.called

    def test_get_multi_inactive(self, crud, mock_db):
        """测试获取非活跃配置"""
        crud.get_multi(mock_db, is_active=False)

        assert mock_db.query.called


class TestCRUDInstances:
    """测试 CRUD 实例"""

    def test_task_crud_instance(self):
        """测试任务 CRUD 实例"""
        assert task_crud is not None
        assert isinstance(task_crud, TaskCRUD)

    def test_excel_task_config_crud_instance(self):
        """测试 Excel 任务配置 CRUD 实例"""
        assert excel_task_config_crud is not None
        assert isinstance(excel_task_config_crud, ExcelTaskConfigCRUD)
