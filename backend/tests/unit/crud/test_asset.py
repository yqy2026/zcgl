"""
资产 CRUD 单元测试（异步接口）
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.asset import AssetCRUD
from src.crud.query_builder import PartyFilter
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


class TestCRUDAssetSoftDeleteGuard:
    async def test_get_async_excludes_deleted_by_default(
        self, crud: AssetCRUD, mock_db: MagicMock
    ) -> None:
        execute_result = MagicMock()
        execute_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = execute_result

        await crud.get_async(mock_db, id="asset-1")

        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "assets.id = 'asset-1'" in compiled
        assert "assets.data_status IS NULL" in compiled
        assert (
            "assets.data_status != '已删除'" in compiled
            or "assets.data_status <> '已删除'" in compiled
        )

    async def test_get_async_can_include_deleted(
        self, crud: AssetCRUD, mock_db: MagicMock
    ) -> None:
        execute_result = MagicMock()
        execute_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = execute_result

        await crud.get_async(mock_db, id="asset-1", include_deleted=True)

        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "assets.id = 'asset-1'" in compiled
        assert "assets.data_status IS NULL" not in compiled
        assert "已删除" not in compiled

    async def test_get_async_with_tenant_filter_applies_tenant_filter(
        self, crud: AssetCRUD, mock_db: MagicMock
    ) -> None:
        execute_result = MagicMock()
        execute_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = execute_result
        party_filter = PartyFilter(party_ids=["org-1"])

        with patch.object(
            crud.query_builder,
            "apply_party_filter",
            side_effect=lambda stmt, _tf: stmt,
        ) as mock_apply_party_filter:
            await crud.get_async(mock_db, id="asset-1", party_filter=party_filter)

        assert mock_apply_party_filter.call_args.args[1] == party_filter


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

    async def test_get_multi_with_search_passes_tenant_filter(
        self, crud: AssetCRUD, mock_db: MagicMock
    ) -> None:
        party_filter = PartyFilter(party_ids=["org-1"])
        execute_result_assets = MagicMock()
        execute_result_assets.scalars.return_value.all.return_value = []
        execute_result_count = MagicMock()
        execute_result_count.scalar.return_value = 0
        mock_db.execute = AsyncMock(
            side_effect=[execute_result_assets, execute_result_count]
        )

        with (
            patch.object(
                crud.query_builder, "build_query", return_value=MagicMock()
            ) as mock_build_query,
            patch.object(
                crud.query_builder, "build_count_query", return_value=MagicMock()
            ) as mock_build_count_query,
        ):
            await crud.get_multi_with_search_async(
                mock_db,
                party_filter=party_filter,
            )

        assert mock_build_query.call_args.kwargs.get("party_filter") == party_filter
        assert mock_build_count_query.call_args.kwargs.get("party_filter") == party_filter

    async def test_get_multi_by_ids_decrypts_assets(
        self, crud: AssetCRUD, mock_db: MagicMock
    ) -> None:
        mock_assets = [MagicMock(spec=Asset), MagicMock(spec=Asset)]
        execute_result = MagicMock()
        execute_result.scalars.return_value.all.return_value = mock_assets
        mock_db.execute.return_value = execute_result

        with patch.object(crud, "_decrypt_asset_object") as mock_decrypt:
            result = await crud.get_multi_by_ids_async(
                mock_db, ids=["asset-1", "asset-2"]
            )

        assert result == mock_assets
        mock_db.execute.assert_awaited_once()
        assert mock_decrypt.call_count == 2
        mock_decrypt.assert_any_call(mock_assets[0])
        mock_decrypt.assert_any_call(mock_assets[1])

    async def test_get_multi_by_ids_skips_decrypt_when_disabled(
        self, crud: AssetCRUD, mock_db: MagicMock
    ) -> None:
        mock_assets = [MagicMock(spec=Asset), MagicMock(spec=Asset)]
        execute_result = MagicMock()
        execute_result.scalars.return_value.all.return_value = mock_assets
        mock_db.execute.return_value = execute_result

        with patch.object(crud, "_decrypt_asset_object") as mock_decrypt:
            result = await crud.get_multi_by_ids_async(
                mock_db,
                ids=["asset-1", "asset-2"],
                decrypt=False,
            )

        assert result == mock_assets
        mock_db.execute.assert_awaited_once()
        mock_decrypt.assert_not_called()


class TestCRUDAssetGetByPropertyNames:
    async def test_get_by_property_names_defaults_to_encrypted_rows(
        self, crud: AssetCRUD, mock_db: MagicMock
    ) -> None:
        mock_assets = [MagicMock(spec=Asset)]
        execute_result = MagicMock()
        execute_result.scalars.return_value.all.return_value = mock_assets
        mock_db.execute.return_value = execute_result

        with patch.object(crud, "_decrypt_asset_object") as mock_decrypt:
            result = await crud.get_by_property_names_async(
                mock_db,
                property_names=["物业A"],
            )

        assert result == mock_assets
        mock_db.execute.assert_awaited_once()
        mock_decrypt.assert_not_called()

    async def test_get_by_property_names_can_decrypt_on_demand(
        self, crud: AssetCRUD, mock_db: MagicMock
    ) -> None:
        mock_assets = [MagicMock(spec=Asset), MagicMock(spec=Asset)]
        execute_result = MagicMock()
        execute_result.scalars.return_value.all.return_value = mock_assets
        mock_db.execute.return_value = execute_result

        with patch.object(crud, "_decrypt_asset_object") as mock_decrypt:
            result = await crud.get_by_property_names_async(
                mock_db,
                property_names=["物业A", "物业B"],
                decrypt=True,
            )

        assert result == mock_assets
        mock_db.execute.assert_awaited_once()
        assert mock_decrypt.call_count == 2
        mock_decrypt.assert_any_call(mock_assets[0])
        mock_decrypt.assert_any_call(mock_assets[1])


class TestCRUDAssetQueryNormalization:
    async def test_normalize_sort_field_maps_occupancy_rate(
        self, crud: AssetCRUD
    ) -> None:
        assert crud._normalize_sort_field("occupancy_rate") == "cached_occupancy_rate"
        assert crud._normalize_sort_field("created_at") == "created_at"

    async def test_normalize_filters_maps_occupancy_and_area_fields(
        self, crud: AssetCRUD
    ) -> None:
        normalized = crud._normalize_filters(
            {
                "min_area": 10,
                "max_area": 20,
                "min_occupancy_rate": 30,
                "max_occupancy_rate": 90,
                "ids": ["asset-1", "asset-2"],
                "usage_status": "出租",
                "management_entity": "管理方A",
                "is_litigated": True,
            }
        )

        assert normalized["min_actual_property_area"] == 10
        assert normalized["max_actual_property_area"] == 20
        assert normalized["min_cached_occupancy_rate"] == 30
        assert normalized["max_cached_occupancy_rate"] == 90
        assert normalized["id__in"] == ["asset-1", "asset-2"]
        assert normalized["usage_status"] == "出租"
        assert normalized["management_entity"] == "管理方A"
        assert normalized["is_litigated"] is True

    async def test_normalize_filters_maps_is_litigated_chinese_string(
        self, crud: AssetCRUD
    ) -> None:
        normalized = crud._normalize_filters({"is_litigated": "否"})
        assert normalized["is_litigated"] is False


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
        method_globals = crud._refresh_search_index_entries.__globals__

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

        with patch.dict(
            method_globals,
            {
                "SEARCH_INDEX_FIELDS": {"address", "manager_name"},
                "build_search_index_entries": MagicMock(side_effect=_build_entries),
            },
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
        with patch.dict(
            crud._refresh_search_index_entries.__globals__,
            {"SEARCH_INDEX_FIELDS": {"address"}},
        ):
            await crud._refresh_search_index_entries(
                mock_db,
                asset_id="asset-1",
                data={"property_name": "测试物业"},
            )

        mock_db.execute.assert_not_awaited()

    async def test_refresh_only_deletes_when_no_entries(
        self, crud: AssetCRUD, mock_db: MagicMock
    ) -> None:
        with patch.dict(
            crud._refresh_search_index_entries.__globals__,
            {
                "SEARCH_INDEX_FIELDS": {"address"},
                "build_search_index_entries": MagicMock(return_value=[]),
            },
        ):
            await crud._refresh_search_index_entries(
                mock_db, asset_id="asset-1", data={"address": "测试地址"}
            )

        assert mock_db.execute.await_count == 1
        delete_stmt = mock_db.execute.await_args_list[0].args[0]
        assert delete_stmt.__visit_name__ == "delete"
