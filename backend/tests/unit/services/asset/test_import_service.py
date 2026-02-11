"""资产导入服务测试。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.asset.import_service import AsyncAssetImportService

pytestmark = pytest.mark.asyncio


def test_import_service_module_exports_service_class() -> None:
    assert AsyncAssetImportService is not None


class TestAsyncAssetImportService:
    async def test_load_existing_assets_map_uses_non_decrypt_query(self) -> None:
        mock_db = MagicMock()
        service = AsyncAssetImportService(mock_db)
        existing_asset = MagicMock()
        existing_asset.property_name = "物业A"

        with patch(
            "src.services.asset.import_service.asset_crud.get_by_property_names_async",
            new_callable=AsyncMock,
            return_value=[existing_asset],
        ) as mock_get_assets:
            result = await service._load_existing_assets_map(
                [{"property_name": "物业A"}]
            )

        assert result == {"物业A": existing_asset}
        mock_get_assets.assert_awaited_once_with(
            mock_db,
            ["物业A"],
            exclude_deleted=True,
            decrypt=False,
        )
