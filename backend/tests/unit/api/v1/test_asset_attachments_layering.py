"""分层约束测试：asset_attachments 路由应委托服务层。"""

import re
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.assets import asset_attachments as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_asset_attachments_module_should_not_import_asset_crud_directly() -> None:
    """asset_attachments 路由模块不应直接导入 crud.asset。"""
    module_source = _read_module_source()
    assert "from ....crud.asset import asset_crud" not in module_source
    assert "asset_crud.get_async(" not in module_source


def test_asset_attachments_module_should_import_authz_dependency() -> None:
    """asset_attachments 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_asset_attachment_endpoints_should_use_require_authz() -> None:
    """资产附件关键端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def upload_asset_attachments[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_id=\"\{asset_id\}\"",
        r"async def get_asset_attachments[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_id=\"\{asset_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def download_asset_attachment[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_id=\"\{asset_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def delete_asset_attachment[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_id=\"\{asset_id\}\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_asset_lookup_adapter_should_delegate_asset_service() -> None:
    """AssetCRUD 适配器应委托 AsyncAssetService.get_asset。"""
    from src.api.v1.assets import asset_attachments as module
    from src.api.v1.assets.asset_attachments import AssetCRUD

    mock_service = MagicMock()
    mock_service.get_asset = AsyncMock(return_value=MagicMock(id="asset-1"))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "AsyncAssetService", MagicMock(return_value=mock_service))
        adapter = AssetCRUD()
        result = await adapter.get_async(db=MagicMock(), id="asset-1")

    assert getattr(result, "id", None) == "asset-1"
    mock_service.get_asset.assert_awaited_once_with("asset-1")


@pytest.mark.asyncio
async def test_get_asset_attachments_should_use_lookup_adapter() -> None:
    """附件列表接口应通过适配器进行资产存在性校验。"""
    from src.api.v1.assets import asset_attachments as module
    from src.api.v1.assets.asset_attachments import get_asset_attachments

    lookup_adapter = MagicMock()
    lookup_adapter.get_async = AsyncMock(return_value=MagicMock(id="asset-1"))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "asset_crud", lookup_adapter)
        monkeypatch.setattr(module.Path, "exists", lambda _self: False)
        result = await get_asset_attachments(
            asset_id="asset-1",
            db=MagicMock(),
            current_user=MagicMock(),
        )

    assert result == []
    lookup_adapter.get_async.assert_awaited_once_with(db=ANY, id="asset-1")
