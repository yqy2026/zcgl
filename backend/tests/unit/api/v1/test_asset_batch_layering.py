"""分层约束测试：asset batch 路由应委托服务层。"""

import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_asset_batch_module_should_not_use_crud_adapter_calls() -> None:
    """路由模块不应直接调用 asset_crud。"""
    from src.api.v1.assets import asset_batch

    module_source = Path(asset_batch.__file__).read_text(encoding="utf-8")
    assert "asset_crud." not in module_source


def test_asset_batch_module_should_import_authz_dependency() -> None:
    """asset batch 路由应引入统一 ABAC 依赖。"""
    from src.api.v1.assets import asset_batch

    module_source = Path(asset_batch.__file__).read_text(encoding="utf-8")
    assert "AuthzContext" in module_source
    assert "get_current_active_user" in module_source
    assert "require_authz" in module_source
    assert "require_permission(" not in module_source


def test_asset_batch_write_endpoints_should_use_require_authz() -> None:
    """批量写端点应接入 require_authz。"""
    from src.api.v1.assets import asset_batch

    module_source = Path(asset_batch.__file__).read_text(encoding="utf-8")
    expected_patterns = [
        r"async def batch_update_assets[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_context=_ASSET_BATCH_UPDATE_RESOURCE_CONTEXT",
        r"async def batch_update_custom_fields[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_context=_ASSET_BATCH_UPDATE_RESOURCE_CONTEXT",
        r"async def batch_delete_assets[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_context=_ASSET_BATCH_DELETE_RESOURCE_CONTEXT",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_asset_batch_unscoped_write_context_should_be_defined() -> None:
    from src.api.v1.assets import asset_batch

    expected_update = "__unscoped__:asset:batch_update"
    assert asset_batch._ASSET_BATCH_UPDATE_UNSCOPED_PARTY_ID == expected_update
    assert asset_batch._ASSET_BATCH_UPDATE_RESOURCE_CONTEXT == {
        "party_id": expected_update,
        "owner_party_id": expected_update,
        "manager_party_id": expected_update,
    }

    expected_delete = "__unscoped__:asset:batch_delete"
    assert asset_batch._ASSET_BATCH_DELETE_UNSCOPED_PARTY_ID == expected_delete
    assert asset_batch._ASSET_BATCH_DELETE_RESOURCE_CONTEXT == {
        "party_id": expected_delete,
        "owner_party_id": expected_delete,
        "manager_party_id": expected_delete,
    }


def test_asset_batch_read_endpoints_should_use_require_authz() -> None:
    """批量读端点应接入 require_authz。"""
    from src.api.v1.assets import asset_batch

    module_source = Path(asset_batch.__file__).read_text(encoding="utf-8")
    expected_patterns = [
        r"async def validate_asset_data[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"asset\"",
        r"async def get_all_assets[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"asset\"",
        r"async def get_assets_by_ids[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"asset\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


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
