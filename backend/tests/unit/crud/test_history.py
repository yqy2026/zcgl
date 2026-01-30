"""
资产历史 CRUD 操作单元测试
"""

from unittest.mock import MagicMock

import pytest

from src.crud.history import HistoryCRUD, history_crud
from src.models.asset import AssetHistory


@pytest.fixture
def crud():
    """创建 CRUD 实例"""
    return HistoryCRUD()


@pytest.fixture
def mock_history():
    """模拟历史记录对象"""
    history = MagicMock(spec=AssetHistory)
    history.id = "history_123"
    history.asset_id = "asset_123"
    history.operation_type = "create"
    history.operation_time = "2024-01-01 10:00:00"
    history.operator_id = "user_123"
    history.changes = {"field": "value"}
    return history


# ============================================================================
# HistoryCRUD.get 测试
# ============================================================================
class TestGet:
    """测试获取单个历史记录"""

    def test_get_success(self, crud, mock_db, mock_history):
        """测试成功获取历史记录"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_history

        result = crud.get(mock_db, "history_123")

        assert result == mock_history
        mock_db.query.assert_called_once_with(AssetHistory)

    def test_get_not_found(self, crud, mock_db):
        """测试历史记录不存在"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = crud.get(mock_db, "nonexistent")

        assert result is None


# ============================================================================
# HistoryCRUD.get_by_asset_id 测试
# ============================================================================
class TestGetByAssetId:
    """测试根据资产ID获取历史记录"""

    def test_get_by_asset_id_success(self, crud, mock_db, mock_history):
        """测试成功获取资产的历史记录"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_history]

        result = crud.get_by_asset_id(mock_db, "asset_123")

        assert len(result) == 1
        assert result[0] == mock_history

    def test_get_by_asset_id_empty(self, crud, mock_db):
        """测试资产没有历史记录"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        result = crud.get_by_asset_id(mock_db, "asset_without_history")

        assert result == []

    def test_get_by_asset_id_ordered_by_time_desc(self, crud, mock_db):
        """测试历史记录按时间降序排列"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        crud.get_by_asset_id(mock_db, "asset_123")

        mock_query.order_by.assert_called_once()


# ============================================================================
# HistoryCRUD.get_multi 测试
# ============================================================================
class TestGetMulti:
    """测试获取多个历史记录"""

    def test_get_multi_default_params(self, crud, mock_db, mock_history):
        """测试使用默认参数获取历史记录"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_history]

        result = crud.get_multi(mock_db)

        assert len(result) == 1
        mock_query.offset.assert_called_with(0)
        mock_query.limit.assert_called_with(100)

    def test_get_multi_with_pagination(self, crud, mock_db):
        """测试带分页的历史记录查询"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        crud.get_multi(mock_db, skip=20, limit=50)

        mock_query.offset.assert_called_with(20)
        mock_query.limit.assert_called_with(50)


# ============================================================================
# HistoryCRUD.create 测试
# ============================================================================
class TestCreate:
    """测试创建历史记录"""

    def test_create_with_commit(self, crud, mock_db):
        """测试创建并提交历史记录"""
        crud.create(
            mock_db,
            commit=True,
            asset_id="asset_123",
            operation_type="create",
            operator_id="user_123",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_create_without_commit(self, crud, mock_db):
        """测试创建但不提交历史记录"""
        crud.create(
            mock_db,
            commit=False,
            asset_id="asset_123",
            operation_type="update",
            operator_id="user_123",
        )

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_not_called()

    def test_create_returns_history_object(self, crud, mock_db):
        """测试创建返回历史记录对象"""
        result = crud.create(
            mock_db,
            asset_id="asset_123",
            operation_type="delete",
            operator_id="user_123",
        )

        assert result is not None


# ============================================================================
# HistoryCRUD.remove 测试
# ============================================================================
class TestRemove:
    """测试删除历史记录"""

    def test_remove_success(self, crud, mock_db, mock_history):
        """测试成功删除历史记录"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_history

        result = crud.remove(mock_db, "history_123")

        mock_db.delete.assert_called_once_with(mock_history)
        mock_db.commit.assert_called_once()
        assert result == mock_history

    def test_remove_not_found(self, crud, mock_db):
        """测试删除不存在的历史记录"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = crud.remove(mock_db, "nonexistent")

        mock_db.delete.assert_not_called()
        assert result is None


# ============================================================================
# 全局实例测试
# ============================================================================
class TestGlobalInstance:
    """测试全局实例"""

    def test_history_crud_instance_exists(self):
        """测试全局实例存在"""
        assert history_crud is not None
        assert isinstance(history_crud, HistoryCRUD)
