"""资产导入服务测试。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.asset import AssetCreate, AssetImportRequest
from src.services.asset.import_service import AsyncAssetImportService

pytestmark = pytest.mark.asyncio


async def test_import_service_module_exports_service_class() -> None:
    assert AsyncAssetImportService is not None


class TestAsyncAssetImportService:
    async def test_load_existing_assets_map_uses_non_decrypt_query(self) -> None:
        mock_db = MagicMock()
        service = AsyncAssetImportService(mock_db)
        existing_asset = MagicMock()
        existing_asset.asset_name = "物业A"

        with patch(
            "src.services.asset.import_service.asset_crud.get_by_asset_names_async",
            new_callable=AsyncMock,
            return_value=[existing_asset],
        ) as mock_get_assets:
            result = await service._load_existing_assets_map([{"asset_name": "物业A"}])

        assert result == {"物业A": existing_asset}
        mock_get_assets.assert_awaited_once_with(
            mock_db,
            ["物业A"],
            exclude_deleted=True,
            decrypt=False,
        )

    async def test_create_import_uses_asset_service_and_ignores_asset_code(
        self,
    ) -> None:
        mock_db = MagicMock()
        service = AsyncAssetImportService(mock_db)
        service.batch_service.validate_asset_data = AsyncMock(
            return_value=(True, [], [], [])
        )
        imported_asset = SimpleNamespace(id="asset-1", asset_name="Asset A")

        request = AssetImportRequest(
            import_mode="create",
            data=[
                {
                    "asset_name": "Asset A",
                    "address_detail": "Building 1 Room 101",
                    "ownership_status": "confirmed",
                    "property_nature": "commercial",
                    "usage_status": "vacant",
                    "owner_party_id": "owner-party-1",
                    "asset_code": "CLIENT-SHOULD-NOT-WIN",
                }
            ],
        )

        with (
            patch.object(
                service,
                "_load_ownership_maps",
                new=AsyncMock(return_value=({}, {})),
            ),
            patch.object(
                service,
                "_load_existing_assets_map",
                new=AsyncMock(return_value={}),
            ),
            patch(
                "src.services.asset.import_service.AssetService",
                create=True,
            ) as mock_asset_service_cls,
            patch(
                "src.services.asset.import_service.asset_crud.create_with_history_async",
                new_callable=AsyncMock,
            ) as mock_crud_create,
        ):
            mock_asset_service = mock_asset_service_cls.return_value
            mock_asset_service.create_asset = AsyncMock(return_value=imported_asset)

            response = await service.import_assets(request=request)

        assert response.success_count == 1
        assert response.imported_assets == ["asset-1"]
        mock_asset_service_cls.assert_called_once_with(mock_db)
        mock_asset_service.create_asset.assert_awaited_once()
        created_payload = mock_asset_service.create_asset.await_args.args[0]
        assert isinstance(created_payload, AssetCreate)
        assert created_payload.asset_code is None
        mock_crud_create.assert_not_awaited()
