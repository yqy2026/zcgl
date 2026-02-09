"""分层约束测试：asset batch 路由应委托服务层。"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_asset_batch_module_should_not_use_crud_adapter_calls() -> None:
    """路由模块不应直接调用 asset_crud。"""
    from src.api.v1.assets import asset_batch

    module_source = Path(asset_batch.__file__).read_text(encoding="utf-8")
    assert "asset_crud." not in module_source


@pytest.mark.asyncio
async def test_get_assets_by_ids_should_delegate_asset_service() -> None:
    """根据 ID 列表获取资产应委托 AsyncAssetService.get_assets_by_ids。"""
    from src.api.v1.assets import asset_batch as module
    from src.api.v1.assets.asset_batch import get_assets_by_ids

    mock_service = MagicMock()
    mock_service.get_assets_by_ids = AsyncMock(return_value=[MagicMock()])

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            module,
            "AsyncAssetService",
            MagicMock(return_value=mock_service),
        )
        monkeypatch.setattr(
            module.AssetListItemResponse,
            "model_validate",
            staticmethod(lambda _: {"id": "asset-1"}),
        )

        result = await get_assets_by_ids(
            request={"ids": ["asset-1"]},
            db=MagicMock(),
            current_user=MagicMock(),
            include_relations=False,
        )

    assert result["success"] is True
    assert len(result["data"]) == 1
    mock_service.get_assets_by_ids.assert_awaited_once_with(
        ids=["asset-1"],
        include_relations=False,
    )
