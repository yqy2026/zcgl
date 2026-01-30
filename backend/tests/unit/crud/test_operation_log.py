"""
操作日志 CRUD 操作单元测试
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.crud.operation_log import OperationLogCRUD
from src.models.operation_log import OperationLog


@pytest.fixture
def crud():
    """创建 CRUD 实例"""
    return OperationLogCRUD()


@pytest.fixture
def mock_log():
    """模拟操作日志对象"""
    log = MagicMock(spec=OperationLog)
    log.id = "log_123"
    log.user_id = "user_123"
    log.username = "testuser"
    log.action = "create"
    log.action_name = "创建"
    log.module = "asset"
    log.module_name = "资产管理"
    log.resource_type = "asset"
    log.resource_id = "asset_123"
    log.response_status = 200
    log.created_at = datetime.now()
    return log


# ============================================================================
# OperationLogCRUD.create 测试
# ============================================================================
class TestCreate:
    """测试创建操作日志"""

    def test_create_success(self, crud, mock_db):
        """测试成功创建操作日志"""
        result = crud.create(
            mock_db,
            user_id="user_123",
            action="create",
            module="asset",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert result is not None

    def test_create_with_all_fields(self, crud, mock_db):
        """测试创建包含所有字段的操作日志"""
        result = crud.create(
            mock_db,
            user_id="user_123",
            action="update",
            module="asset",
            resource_type="asset",
            resource_id="asset_123",
            resource_name="测试资产",
            request_method="PUT",
            request_url="/api/v1/assets/123",
            request_params="{}",
            request_body='{"name": "new"}',
            response_status=200,
            response_time=150,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            error_message=None,
            details="更新资产名称",
            username="testuser",
            action_name="更新",
            module_name="资产管理",
        )

        mock_db.add.assert_called_once()
        assert result is not None


# ============================================================================
# OperationLogCRUD.get 测试
# ============================================================================
class TestGet:
    """测试获取单个操作日志"""

    def test_get_success(self, crud, mock_db, mock_log):
        """测试成功获取操作日志"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_log

        result = crud.get(mock_db, "log_123")

        assert result == mock_log

    def test_get_not_found(self, crud, mock_db):
        """测试日志不存在"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = crud.get(mock_db, "nonexistent")

        assert result is None


# ============================================================================
# OperationLogCRUD.get_multi 测试
# ============================================================================
class TestGetMulti:
    """测试获取多个操作日志"""

    def test_get_multi_default_params(self, crud, mock_db, mock_log):
        """测试使用默认参数获取日志列表"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_log]

        logs, total = crud.get_multi(mock_db)

        assert len(logs) == 1
        assert total == 1

    def test_get_multi_with_user_filter(self, crud, mock_db):
        """测试按用户筛选"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        crud.get_multi(mock_db, user_id="user_123")

        # 验证 filter 被调用
        assert mock_query.filter.called

    def test_get_multi_with_action_filter(self, crud, mock_db):
        """测试按操作类型筛选"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        crud.get_multi(mock_db, action="create")

        assert mock_query.filter.called

    def test_get_multi_with_module_filter(self, crud, mock_db):
        """测试按模块筛选"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        crud.get_multi(mock_db, module="asset")

        assert mock_query.filter.called

    def test_get_multi_with_date_range(self, crud, mock_db):
        """测试按日期范围筛选"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        crud.get_multi(mock_db, start_date=start_date, end_date=end_date)

        assert mock_query.filter.called

    def test_get_multi_with_search(self, crud, mock_db):
        """测试关键词搜索"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        crud.get_multi(mock_db, search="测试")

        assert mock_query.filter.called

    def test_get_multi_with_response_status_success(self, crud, mock_db):
        """测试按成功状态筛选"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        crud.get_multi(mock_db, response_status="success")

        assert mock_query.filter.called

    def test_get_multi_with_response_status_error(self, crud, mock_db):
        """测试按错误状态筛选"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        crud.get_multi(mock_db, response_status="error")

        assert mock_query.filter.called


# ============================================================================
# OperationLogCRUD.delete_old_logs 测试
# ============================================================================
class TestDeleteOldLogs:
    """测试删除旧日志"""

    def test_delete_old_logs_success(self, crud, mock_db):
        """测试成功删除旧日志"""
        mock_db.query.return_value.filter.return_value.delete.return_value = 100

        result = crud.delete_old_logs(mock_db, days=90)

        mock_db.commit.assert_called_once()
        assert result == 100

    def test_delete_old_logs_custom_days(self, crud, mock_db):
        """测试自定义天数删除"""
        mock_db.query.return_value.filter.return_value.delete.return_value = 50

        result = crud.delete_old_logs(mock_db, days=30)

        assert result == 50


# ============================================================================
# OperationLogCRUD.get_user_statistics 测试
# ============================================================================
class TestGetUserStatistics:
    """测试获取用户统计"""

    def test_get_user_statistics_success(self, crud, mock_db):
        """测试成功获取用户统计"""
        mock_db.query.return_value.filter.return_value.scalar.return_value = 100
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [
            ("create", 50),
            ("update", 30),
            ("delete", 20),
        ]

        result = crud.get_user_statistics(mock_db, "user_123", days=30)

        assert result["user_id"] == "user_123"
        assert result["days"] == 30
        assert result["total_operations"] == 100


# ============================================================================
# OperationLogCRUD.get_module_statistics 测试
# ============================================================================
class TestGetModuleStatistics:
    """测试获取模块统计"""

    def test_get_module_statistics_success(self, crud, mock_db):
        """测试成功获取模块统计"""
        mock_db.query.return_value.filter.return_value.scalar.return_value = 200
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [
            ("create", 100),
            ("read", 80),
            ("update", 20),
        ]

        result = crud.get_module_statistics(mock_db, "asset", days=30)

        assert result["module"] == "asset"
        assert result["days"] == 30
        assert result["total_operations"] == 200


# ============================================================================
# OperationLogCRUD.get_daily_statistics 测试
# ============================================================================
class TestGetDailyStatistics:
    """测试获取每日统计"""

    def test_get_daily_statistics_success(self, crud, mock_db):
        """测试成功获取每日统计"""
        mock_db.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = [
            ("2024-01-01", 50),
            ("2024-01-02", 60),
        ]

        result = crud.get_daily_statistics(mock_db, days=30)

        assert result["days"] == 30
        assert "daily_breakdown" in result


# ============================================================================
# OperationLogCRUD.get_error_statistics 测试
# ============================================================================
class TestGetErrorStatistics:
    """测试获取错误统计"""

    def test_get_error_statistics_success(self, crud, mock_db):
        """测试成功获取错误统计"""
        mock_db.query.return_value.filter.return_value.scalar.return_value = 10
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [
            ("create", 5),
            ("update", 5),
        ]

        result = crud.get_error_statistics(mock_db, days=30)

        assert result["days"] == 30
        assert result["total_errors"] == 10
        assert "error_breakdown" in result


# ============================================================================
# OperationLogCRUD.count 测试
# ============================================================================
class TestCount:
    """测试日志计数"""

    def test_count_success(self, crud, mock_db):
        """测试成功计数"""
        mock_db.query.return_value.scalar.return_value = 1000

        result = crud.count(mock_db)

        assert result == 1000

    def test_count_returns_zero_for_none(self, crud, mock_db):
        """测试 None 返回零"""
        mock_db.query.return_value.scalar.return_value = None

        result = crud.count(mock_db)

        assert result == 0
