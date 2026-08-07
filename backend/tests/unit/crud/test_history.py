"""
资产历史 CRUD 操作单元测试（异步接口）
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.history import HistoryCRUD, history_crud
from src.models.asset_history import AssetHistory

pytestmark = pytest.mark.asyncio


@pytest.fixture
def crud() -> HistoryCRUD:
    """创建 CRUD 实例"""
    return HistoryCRUD()


@pytest.fixture
def mock_history() -> MagicMock:
    """模拟历史记录对象"""
    history = MagicMock(spec=AssetHistory)
    history.id = "history_123"
    history.asset_id = "asset_123"
    history.operation_type = "create"
    history.operation_time = "2024-01-01 10:00:00"
    history.operator = "user_123"
    return history


class TestGetAsync:
    """测试获取单个历史记录"""

    async def test_get_async_success(
        self, crud: HistoryCRUD, mock_db: MagicMock, mock_history: MagicMock
    ) -> None:
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_history
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await crud.get_async(mock_db, "history_123")

        assert result == mock_history
        mock_db.execute.assert_awaited_once()

    async def test_get_async_not_found(
        self, crud: HistoryCRUD, mock_db: MagicMock
    ) -> None:
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await crud.get_async(mock_db, "nonexistent")

        assert result is None


class TestGetMultiWithCountAsync:
    """测试获取历史记录列表及总数"""

    @staticmethod
    def _render(stmt: object) -> str:
        """将 SQLAlchemy 语句渲染为带字面量绑定的 SQL 字符串。"""
        return str(stmt.compile(compile_kwargs={"literal_binds": True}))

    async def test_get_multi_with_count_async(
        self, crud: HistoryCRUD, mock_db: MagicMock, mock_history: MagicMock
    ) -> None:
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        list_scalars = MagicMock()
        list_scalars.all.return_value = [mock_history]
        list_result = MagicMock()
        list_result.scalars.return_value = list_scalars

        mock_db.execute = AsyncMock(side_effect=[count_result, list_result])

        items, total = await crud.get_multi_with_count_async(
            mock_db, skip=20, limit=50, asset_id="asset_123"
        )

        assert total == 1
        assert items == [mock_history]
        assert mock_db.execute.await_count == 2
        # change_type=None 时不得生成 operation_type 过滤子句
        # （SELECT 列含 operation_type 列名，故按过滤表达式形式 `operation_type =` 断言）
        rendered = self._render(mock_db.execute.await_args_list[1].args[0])
        assert "operation_type =" not in rendered

    async def test_get_multi_with_count_async_orders_by_operation_time_then_id(
        self, crud: HistoryCRUD, mock_db: MagicMock, mock_history: MagicMock
    ) -> None:
        """分页排序应以 operation_time 倒序为主，id 倒序为 tie-breaker。"""
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        list_scalars = MagicMock()
        list_scalars.all.return_value = [mock_history]
        list_result = MagicMock()
        list_result.scalars.return_value = list_scalars
        mock_db.execute = AsyncMock(side_effect=[count_result, list_result])

        await crud.get_multi_with_count_async(mock_db, skip=0, limit=20, asset_id="asset_123")

        rendered = self._render(mock_db.execute.await_args_list[1].args[0])
        assert "operation_time DESC" in rendered
        assert "id DESC" in rendered

    async def test_get_multi_with_count_async_filters_change_type(
        self, crud: HistoryCRUD, mock_db: MagicMock, mock_history: MagicMock
    ) -> None:
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        list_scalars = MagicMock()
        list_scalars.all.return_value = [mock_history]
        list_result = MagicMock()
        list_result.scalars.return_value = list_scalars

        mock_db.execute = AsyncMock(side_effect=[count_result, list_result])

        items, total = await crud.get_multi_with_count_async(
            mock_db, skip=0, limit=20, asset_id="asset_123", change_type="create"
        )

        assert total == 1
        assert items == [mock_history]
        # 过滤条件应以绑定值 'create' 同时作用于 count 与列表查询
        count_rendered = self._render(mock_db.execute.await_args_list[0].args[0])
        list_rendered = self._render(mock_db.execute.await_args_list[1].args[0])
        assert "operation_type = 'create'" in count_rendered
        assert "operation_type = 'create'" in list_rendered


class TestCreateAsync:
    """测试创建历史记录"""

    async def test_create_async_with_commit(
        self, crud: HistoryCRUD, mock_db: MagicMock
    ) -> None:
        mock_db.add.reset_mock()
        mock_db.commit.reset_mock()
        mock_db.refresh.reset_mock()

        with patch("src.crud.history.AssetHistory") as mock_model:
            mock_model_instance = MagicMock(spec=AssetHistory)
            mock_model.return_value = mock_model_instance

            result = await crud.create_async(
                mock_db,
                commit=True,
                asset_id="asset_123",
                operation_type="create",
                operator="user_123",
            )

        mock_model.assert_called_once_with(
            asset_id="asset_123",
            operation_type="create",
            operator="user_123",
        )
        assert result == mock_model_instance
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(result)

    async def test_create_async_without_commit(
        self, crud: HistoryCRUD, mock_db: MagicMock
    ) -> None:
        mock_db.add.reset_mock()
        mock_db.commit.reset_mock()
        mock_db.flush.reset_mock()
        mock_db.refresh.reset_mock()

        with patch("src.crud.history.AssetHistory") as mock_model:
            mock_model_instance = MagicMock(spec=AssetHistory)
            mock_model.return_value = mock_model_instance

            result = await crud.create_async(
                mock_db,
                commit=False,
                asset_id="asset_123",
                operation_type="update",
                operator="user_123",
            )

        mock_model.assert_called_once_with(
            asset_id="asset_123",
            operation_type="update",
            operator="user_123",
        )
        assert result == mock_model_instance
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()
        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_awaited_once_with(result)

    async def test_create_async_rejects_legacy_operator_id(
        self, crud: HistoryCRUD, mock_db: MagicMock
    ) -> None:
        def raise_if_legacy_field(**kwargs):  # type: ignore[no-untyped-def]
            if "operator_id" in kwargs:
                raise TypeError("unexpected keyword argument 'operator_id'")
            return MagicMock(spec=AssetHistory)

        with patch("src.crud.history.AssetHistory", side_effect=raise_if_legacy_field):
            with pytest.raises(TypeError):
                await crud.create_async(
                    mock_db,
                    asset_id="asset_123",
                    operation_type="create",
                    operator_id="user_123",
                )


class TestRemoveAsync:
    """测试删除历史记录"""

    async def test_remove_async_success(
        self, crud: HistoryCRUD, mock_db: MagicMock, mock_history: MagicMock
    ) -> None:
        crud.get_async = AsyncMock(return_value=mock_history)  # type: ignore[method-assign]

        result = await crud.remove_async(mock_db, "history_123")

        assert result == mock_history
        mock_db.delete.assert_awaited_once_with(mock_history)
        mock_db.commit.assert_awaited_once()

    async def test_remove_async_not_found(
        self, crud: HistoryCRUD, mock_db: MagicMock
    ) -> None:
        mock_db.delete.reset_mock()
        mock_db.commit.reset_mock()
        crud.get_async = AsyncMock(return_value=None)  # type: ignore[method-assign]

        result = await crud.remove_async(mock_db, "nonexistent")

        assert result is None
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()


class TestRemoveByAssetIdAsync:
    """测试按资产ID删除历史记录"""

    async def test_remove_by_asset_id_async_with_commit(
        self, crud: HistoryCRUD, mock_db: MagicMock
    ) -> None:
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_db.execute = AsyncMock(return_value=mock_result)

        deleted_count = await crud.remove_by_asset_id_async(
            mock_db, asset_id="asset_123", commit=True
        )

        assert deleted_count == 3
        mock_db.execute.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    async def test_remove_by_asset_id_async_without_commit(
        self, crud: HistoryCRUD, mock_db: MagicMock
    ) -> None:
        mock_db.execute.reset_mock()
        mock_db.flush.reset_mock()
        mock_db.commit.reset_mock()

        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_db.execute = AsyncMock(return_value=mock_result)

        deleted_count = await crud.remove_by_asset_id_async(
            mock_db, asset_id="asset_123", commit=False
        )

        assert deleted_count == 2
        mock_db.execute.assert_awaited_once()
        mock_db.flush.assert_awaited_once()
        mock_db.commit.assert_not_called()


class TestGlobalInstance:
    """测试全局实例"""

    async def test_history_crud_instance_exists(self) -> None:
        assert history_crud is not None
        assert isinstance(history_crud, HistoryCRUD)
