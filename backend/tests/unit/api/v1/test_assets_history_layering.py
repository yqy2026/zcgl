"""分层约束测试：assets 历史端点应委托服务层。"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_assets_module_should_not_use_history_crud_directly() -> None:
    """assets 路由模块不应直接调用 history_crud。"""
    from src.api.v1.assets import assets as assets_module

    module_source = Path(assets_module.__file__).read_text(encoding="utf-8")
    assert "history_crud." not in module_source


@pytest.mark.asyncio
async def test_get_asset_history_should_delegate_asset_service() -> None:
    """资产历史接口应委托 AsyncAssetService.get_asset_history_records。"""
    from src.api.v1.assets import assets as module
    from src.api.v1.assets.assets import get_asset_history

    mock_service = MagicMock()
    mock_service.get_asset_history_records = AsyncMock(return_value=[{"id": "history-1"}])

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "AsyncAssetService", MagicMock(return_value=mock_service))
        result = await get_asset_history(
            asset_id="asset-1",
            db=MagicMock(),
            current_user=MagicMock(),
        )

    assert result == {"asset_id": "asset-1", "history": [{"id": "history-1"}]}
    mock_service.get_asset_history_records.assert_awaited_once_with("asset-1")
