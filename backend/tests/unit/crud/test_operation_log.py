"""
操作日志 CRUD 操作单元测试
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.operation_log import OperationLogCRUD
from src.models.operation_log import OperationLog


class _ScalarsResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values

    def first(self):
        return self._values[0] if self._values else None


class _ExecuteResult:
    def __init__(self, *, scalar_value=None, scalars_value=None, all_value=None):
        self._scalar_value = scalar_value
        self._scalars_value = scalars_value or []
        self._all_value = all_value or []

    def scalar(self):
        return self._scalar_value

    def scalars(self):
        return _ScalarsResult(self._scalars_value)

    def all(self):
        return self._all_value


@pytest.fixture
def crud():
    """创建 CRUD 实例"""
    return OperationLogCRUD()


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


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

    async def test_create_success(self, crud, mock_db):
        """测试成功创建操作日志"""
        result = await crud.create_async(
            mock_db,
            user_id="user_123",
            action="create",
            module="asset",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()
        assert result is not None

    async def test_create_with_all_fields(self, crud, mock_db):
        """测试创建包含所有字段的操作日志"""
        result = await crud.create_async(
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

    async def test_get_success(self, crud, mock_db, mock_log):
        """测试成功获取操作日志"""
        mock_db.execute = AsyncMock(
            return_value=_ExecuteResult(scalars_value=[mock_log])
        )

        result = await crud.get_async(mock_db, "log_123")

        assert result == mock_log

    async def test_get_not_found(self, crud, mock_db):
        """测试日志不存在"""
        mock_db.execute = AsyncMock(return_value=_ExecuteResult(scalars_value=[]))

        result = await crud.get_async(mock_db, "nonexistent")

        assert result is None


# ============================================================================
# OperationLogCRUD.get_multi 测试
# ============================================================================
class TestGetMulti:
    """测试获取多个操作日志"""

    async def test_get_multi_default_params(self, crud, mock_db, mock_log):
        """测试使用默认参数获取日志列表"""
        mock_db.execute = AsyncMock(
            side_effect=[
                _ExecuteResult(scalar_value=1),
                _ExecuteResult(scalars_value=[mock_log]),
            ]
        )

        logs, total = await crud.get_multi_with_count_async(mock_db)

        assert logs == [mock_log]
        assert total == 1

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"user_id": "user_123"},
            {"action": "create"},
            {"module": "asset"},
            {
                "start_date": datetime.now() - timedelta(days=7),
                "end_date": datetime.now(),
            },
            {"search": "测试"},
            {"response_status": "success"},
            {"response_status": "error"},
        ],
    )
    async def test_get_multi_with_filters(self, crud, mock_db, kwargs):
        """测试多种筛选条件"""
        mock_db.execute = AsyncMock(
            side_effect=[
                _ExecuteResult(scalar_value=0),
                _ExecuteResult(scalars_value=[]),
            ]
        )

        logs, total = await crud.get_multi_with_count_async(mock_db, **kwargs)

        assert logs == []
        assert total == 0


# ============================================================================
# OperationLogCRUD.delete_old_logs 测试
# ============================================================================
class TestDeleteOldLogs:
    """测试删除旧日志"""

    async def test_delete_old_logs_success(self, crud, mock_db):
        """测试成功删除旧日志"""
        mock_db.execute = AsyncMock(return_value=MagicMock(rowcount=100))

        result = await crud.delete_old_logs_async(mock_db, days=90)

        mock_db.commit.assert_awaited_once()
        assert result == 100

    async def test_delete_old_logs_custom_days(self, crud, mock_db):
        """测试自定义天数删除"""
        mock_db.execute = AsyncMock(return_value=MagicMock(rowcount=50))

        result = await crud.delete_old_logs_async(mock_db, days=30)

        assert result == 50


# ============================================================================
# OperationLogCRUD.get_user_statistics 测试
# ============================================================================
class TestGetUserStatistics:
    """测试获取用户统计"""

    async def test_get_user_statistics_success(self, crud, mock_db):
        """测试成功获取用户统计"""
        mock_db.execute = AsyncMock(
            side_effect=[
                _ExecuteResult(scalar_value=100),
                _ExecuteResult(
                    all_value=[("create", 50), ("update", 30), ("delete", 20)]
                ),
            ]
        )

        result = await crud.get_user_statistics_async(mock_db, "user_123", days=30)

        assert result["user_id"] == "user_123"
        assert result["days"] == 30
        assert result["total_operations"] == 100


# ============================================================================
# OperationLogCRUD.get_module_statistics 测试
# ============================================================================
class TestGetModuleStatistics:
    """测试获取模块统计"""

    async def test_get_module_statistics_success(self, crud, mock_db):
        """测试成功获取模块统计"""
        mock_db.execute = AsyncMock(
            side_effect=[
                _ExecuteResult(scalar_value=200),
                _ExecuteResult(all_value=[("create", 100), ("read", 80), ("update", 20)]),
            ]
        )

        result = await crud.get_module_statistics_async(mock_db, "asset", days=30)

        assert result["module"] == "asset"
        assert result["days"] == 30
        assert result["total_operations"] == 200


# ============================================================================
# OperationLogCRUD.get_daily_statistics 测试
# ============================================================================
class TestGetDailyStatistics:
    """测试获取每日统计"""

    async def test_get_daily_statistics_success(self, crud, mock_db):
        """测试成功获取每日统计"""
        mock_db.execute = AsyncMock(
            return_value=_ExecuteResult(
                all_value=[("2024-01-01", 50), ("2024-01-02", 60)]
            )
        )

        result = await crud.get_daily_statistics_async(mock_db, days=30)

        assert result["days"] == 30
        assert "daily_breakdown" in result


# ============================================================================
# OperationLogCRUD.get_error_statistics 测试
# ============================================================================
class TestGetErrorStatistics:
    """测试获取错误统计"""

    async def test_get_error_statistics_success(self, crud, mock_db):
        """测试成功获取错误统计"""
        mock_db.execute = AsyncMock(
            side_effect=[
                _ExecuteResult(scalar_value=10),
                _ExecuteResult(all_value=[("create", 5), ("update", 5)]),
            ]
        )

        result = await crud.get_error_statistics_async(mock_db, days=30)

        assert result["days"] == 30
        assert result["total_errors"] == 10
        assert "error_breakdown" in result


# ============================================================================
# OperationLogCRUD.count 测试
# ============================================================================
class TestCount:
    """测试日志计数"""

    async def test_count_success(self, crud, mock_db):
        """测试成功计数"""
        mock_db.execute = AsyncMock(return_value=_ExecuteResult(scalar_value=1000))

        result = await crud.count_async(mock_db)

        assert result == 1000

    async def test_count_returns_zero_for_none(self, crud, mock_db):
        """测试 None 返回零"""
        mock_db.execute = AsyncMock(return_value=_ExecuteResult(scalar_value=None))

        result = await crud.count_async(mock_db)

        assert result == 0
