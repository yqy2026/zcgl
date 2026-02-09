"""分层约束测试：asset import 路由应委托服务层。"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.asset import AssetImportRequest, AssetImportResponse

pytestmark = pytest.mark.api


def test_asset_import_module_should_not_directly_use_crud() -> None:
    """路由模块不应直接调用 asset_crud。"""
    from src.api.v1.assets import asset_import

    module_source = Path(asset_import.__file__).read_text(encoding="utf-8")
    assert "asset_crud." not in module_source


@pytest.mark.asyncio
async def test_import_assets_should_delegate_to_import_service() -> None:
    """导入路由应委托 AsyncAssetImportService.import_assets。"""
    from src.api.v1.assets import asset_import as module
    from src.api.v1.assets.asset_import import import_assets

    request = AssetImportRequest(
        data=[{"property_name": "测试资产"}],
        import_mode="create",
        should_skip_errors=False,
        is_dry_run=True,
    )
    expected_response = AssetImportResponse(
        success_count=1,
        failed_count=0,
        total_count=1,
        errors=[],
        imported_assets=[],
        import_id=None,
    )

    mock_service = MagicMock()
    mock_service.import_assets = AsyncMock(return_value=expected_response)

    mock_db = MagicMock()
    mock_user = MagicMock()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            module,
            "AsyncAssetImportService",
            MagicMock(return_value=mock_service),
        )

        result = await import_assets(
            request=request,
            db=mock_db,
            current_user=mock_user,
        )

    assert result == expected_response
    mock_service.import_assets.assert_awaited_once_with(
        request=request,
        current_user=mock_user,
    )
