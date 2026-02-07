"""
资产 CRUD 单元测试（异步接口）
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.asset import AssetCRUD
from src.models.asset import Asset
from src.models.asset_search_index import AssetSearchIndex

pytestmark = pytest.mark.asyncio


@pytest.fixture
def crud() -> AssetCRUD:
    return AssetCRUD()


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock()
    db.delete = AsyncMock()
    db.add = MagicMock()
    return db


class TestCRUDAssetGet:
    async def test_get_existing_asset(self, crud: AssetCRUD, mock_db: MagicMock) -> None:
        mock_asset = MagicMock(spec=Asset)
        mock_asset.id = "1"
        mock_asset.property_name = "测试物业"

        with patch.object(crud, "get", new_callable=AsyncMock, return_value=mock_asset):
            result = await crud.get(mock_db, id="1")

        assert result is not None

    async def test_get_nonexistent_asset(self, crud: AssetCRUD, mock_db: MagicMock) -> None:
        with patch.object(crud, "get", new_callable=AsyncMock, return_value=None):
            result = await crud.get(mock_db, id="999")

        assert result is None


class TestCRUDAssetGetByName:
    async def test_get_by_name_exists(self, crud: AssetCRUD, mock_db: MagicMock) -> None:
        mock_asset = MagicMock(spec=Asset)
        mock_asset.property_name = "测试物业A"

        with patch.object(
            crud,
            "get_by_name_async",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ):
            result = await crud.get_by_name_async(mock_db, property_name="测试物业A")

        assert result is not None
        assert result.property_name == "测试物业A"

    async def test_get_by_name_not_exists(self, crud: AssetCRUD, mock_db: MagicMock) -> None:
        with patch.object(
            crud,
            "get_by_name_async",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await crud.get_by_name_async(mock_db, property_name="不存在的物业")

        assert result is None


class TestCRUDAssetGetMulti:
    async def test_get_multi_default_params(self, crud: AssetCRUD, mock_db: MagicMock) -> None:
        mock_assets = [MagicMock(spec=Asset), MagicMock(spec=Asset)]
        with patch.object(
            crud,
            "get_multi_with_search_async",
            new_callable=AsyncMock,
            return_value=(mock_assets, 2),
        ):
            result = await crud.get_multi_with_search_async(mock_db)

        assert isinstance(result, tuple)
        assert len(result[0]) == 2
        assert result[1] == 2

    async def test_get_multi_with_pagination(self, crud: AssetCRUD, mock_db: MagicMock) -> None:
        mock_assets = [MagicMock(spec=Asset)]
        with patch.object(
            crud,
            "get_multi_with_search_async",
            new_callable=AsyncMock,
            return_value=(mock_assets, 1),
        ) as mock_get_multi:
            await crud.get_multi_with_search_async(mock_db, skip=10, limit=20)

        mock_get_multi.assert_awaited_once_with(mock_db, skip=10, limit=20)

    async def test_get_multi_by_ids_decrypts_assets(
        self, crud: AssetCRUD, mock_db: MagicMock
    ) -> None:
        mock_assets = [MagicMock(spec=Asset), MagicMock(spec=Asset)]
        with (
            patch.object(
                crud,
                "get_with_filters",
                new_callable=AsyncMock,
                return_value=mock_assets,
            ) as mock_get_with_filters,
            patch.object(crud, "_decrypt_asset_object") as mock_decrypt,
        ):
            result = await crud.get_multi_by_ids_async(
                mock_db, ids=["asset-1", "asset-2"]
            )

        assert result == mock_assets
        mock_get_with_filters.assert_awaited_once()
        assert mock_decrypt.call_count == 2
        mock_decrypt.assert_any_call(mock_assets[0])
        mock_decrypt.assert_any_call(mock_assets[1])


class TestCRUDAssetCreate:
    async def test_create_asset(self, crud: AssetCRUD, mock_db: MagicMock) -> None:
        create_data = {"property_name": "新物业", "address": "测试地址123号"}
        mock_asset = MagicMock(spec=Asset)
        mock_asset.id = "new-id"

        with patch.object(
            crud,
            "create_async",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ):
            result = await crud.create_async(mock_db, obj_in=create_data)

        assert result is not None


class TestCRUDAssetUpdate:
    async def test_update_asset(self, crud: AssetCRUD, mock_db: MagicMock) -> None:
        mock_asset = MagicMock(spec=Asset)
        mock_asset.id = "1"
        update_data = {"property_name": "更新后的物业名称"}

        with patch.object(
            crud,
            "update_async",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ):
            result = await crud.update_async(mock_db, db_obj=mock_asset, obj_in=update_data)

        assert result is not None


class TestCRUDAssetDelete:
    async def test_delete_asset(self, crud: AssetCRUD, mock_db: MagicMock) -> None:
        mock_asset = MagicMock(spec=Asset)
        mock_asset.id = "1"

        with patch.object(
            crud,
            "remove_async",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ):
            result = await crud.remove_async(mock_db, id="1")

        assert result is not None


class TestCRUDAssetSearch:
    async def test_search_with_filters(self, crud: AssetCRUD, mock_db: MagicMock) -> None:
        mock_assets = [MagicMock(spec=Asset)]
        with patch.object(
            crud,
            "get_multi_with_search_async",
            new_callable=AsyncMock,
            return_value=(mock_assets, 1),
        ) as mock_get_multi:
            filters = {"ownership_id": "ownership-1"}
            await crud.get_multi_with_search_async(mock_db, filters=filters)

        mock_get_multi.assert_awaited_once()
        call_kwargs = mock_get_multi.call_args.kwargs
        assert call_kwargs["filters"] == {"ownership_id": "ownership-1"}


class TestAssetSearchIndexRefresh:
    async def test_refresh_batches_delete_and_insert(
        self, crud: AssetCRUD, mock_db: MagicMock
    ) -> None:
        data = {"address": "测试地址", "manager_name": "张三"}

        def _build_entries(
            *,
            asset_id: str,
            field_name: str,
            value: str,
            key_manager: object,
        ) -> list[AssetSearchIndex]:
            del value, key_manager
            return [
                AssetSearchIndex(
                    asset_id=asset_id,
                    field_name=field_name,
                    token_hash=f"{field_name}-token",
                    key_version=1,
                )
            ]

        with (
            patch("src.crud.asset.SEARCH_INDEX_FIELDS", {"address", "manager_name"}),
            patch("src.crud.asset.build_search_index_entries", side_effect=_build_entries),
        ):
            await crud._refresh_search_index_entries(
                mock_db, asset_id="asset-1", data=data
            )

        assert mock_db.execute.await_count == 2
        delete_stmt = mock_db.execute.await_args_list[0].args[0]
        insert_stmt = mock_db.execute.await_args_list[1].args[0]
        insert_values = mock_db.execute.await_args_list[1].args[1]

        assert delete_stmt.__visit_name__ == "delete"
        assert insert_stmt.__visit_name__ == "insert"
        assert " IN " in str(delete_stmt)
        assert len(insert_values) == 2
        assert {item["field_name"] for item in insert_values} == {
            "address",
            "manager_name",
        }

    async def test_refresh_skips_when_no_indexed_fields(
        self, crud: AssetCRUD, mock_db: MagicMock
    ) -> None:
        with patch("src.crud.asset.SEARCH_INDEX_FIELDS", {"address"}):
            await crud._refresh_search_index_entries(
                mock_db,
                asset_id="asset-1",
                data={"property_name": "测试物业"},
            )

        mock_db.execute.assert_not_awaited()

    async def test_refresh_only_deletes_when_no_entries(
        self, crud: AssetCRUD, mock_db: MagicMock
    ) -> None:
        with (
            patch("src.crud.asset.SEARCH_INDEX_FIELDS", {"address"}),
            patch("src.crud.asset.build_search_index_entries", return_value=[]),
        ):
            await crud._refresh_search_index_entries(
                mock_db, asset_id="asset-1", data={"address": "测试地址"}
            )

        assert mock_db.execute.await_count == 1
        delete_stmt = mock_db.execute.await_args_list[0].args[0]
        assert delete_stmt.__visit_name__ == "delete"
