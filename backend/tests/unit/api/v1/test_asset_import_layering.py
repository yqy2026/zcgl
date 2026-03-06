"""分层约束测试：asset import 路由应委托服务层。"""

import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.asset import AssetImportRequest, AssetImportResponse

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.assets import asset_import as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_asset_import_module_should_not_directly_use_crud() -> None:
    """路由模块不应直接调用 asset_crud。"""
    module_source = _read_module_source()
    assert "asset_crud." not in module_source


def test_asset_import_module_should_import_authz_dependency() -> None:
    """asset_import 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "get_current_active_user" in module_source
    assert "require_permission(" not in module_source


def test_import_assets_endpoint_should_use_require_authz() -> None:
    """导入端点应接入 create 场景专用鉴权依赖。"""
    module_source = _read_module_source()
    pattern = (
        r"async def import_assets[\s\S]*?"
        r"_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_asset_import_create_authz\)"
    )
    assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_import_assets_should_delegate_to_import_service() -> None:
    """导入路由应委托 AsyncAssetImportService.import_assets。"""
    from src.api.v1.assets import asset_import as module
    from src.api.v1.assets.asset_import import import_assets

    request = AssetImportRequest(
        data=[{"asset_name": "测试资产"}],
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


@pytest.mark.asyncio
async def test_asset_import_create_authz_should_check_each_distinct_scope() -> None:
    """资产导入 create 鉴权应按导入数据的 distinct scope 逐一检查。"""
    from src.api.v1.assets import asset_import as module

    request = AssetImportRequest(
        data=[
            {"owner_party_id": "owner-1", "organization_id": "org-1"},
            {"owner_party_id": "owner-1", "organization_id": "org-1"},
            {"manager_party_id": "manager-2"},
        ],
        import_mode="create",
        should_skip_errors=False,
        is_dry_run=True,
    )

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_asset_import_create_authz(  # type: ignore[attr-defined]
            request=request,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["checked_scope_count"] == 2
    assert mock_authz_service.check_access.await_count == 2


@pytest.mark.asyncio
async def test_asset_import_create_authz_should_resolve_owner_party_from_legacy_ownership() -> None:
    """导入鉴权应把 legacy ownership 作用域桥接为 owner_party/party。"""
    from src.api.v1.assets import asset_import as module

    request = AssetImportRequest(
        data=[{"ownership_id": "ownership-legacy-1"}],
        import_mode="create",
        should_skip_errors=False,
        is_dry_run=True,
    )

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )
    mock_asset_service = MagicMock()
    mock_asset_service.resolve_owner_party_scope_by_ownership_id_async = AsyncMock(
        return_value="owner-party-legacy-1"
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        monkeypatch.setattr(
            module,
            "AsyncAssetService",
            MagicMock(return_value=mock_asset_service),
            raising=False,
        )
        await module._require_asset_import_create_authz(  # type: ignore[attr-defined]
            request=request,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource"]["ownership_id"] == "ownership-legacy-1"
    assert kwargs["resource"]["owner_party_id"] == "owner-party-legacy-1"
    assert kwargs["resource"]["party_id"] == "owner-party-legacy-1"


@pytest.mark.asyncio
async def test_asset_import_create_authz_should_resolve_party_from_legacy_organization() -> None:
    """导入鉴权应把 legacy organization 作用域桥接为 party_id。"""
    from src.api.v1.assets import asset_import as module

    request = AssetImportRequest(
        data=[{"organization_id": "org-legacy-1"}],
        import_mode="create",
        should_skip_errors=False,
        is_dry_run=True,
    )

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        monkeypatch.setattr(
            module,
            "_resolve_organization_party_scope_by_organization_id",
            AsyncMock(return_value="org-party-1"),
            raising=False,
        )
        await module._require_asset_import_create_authz(  # type: ignore[attr-defined]
            request=request,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource"]["organization_id"] == "org-legacy-1"
    assert kwargs["resource"]["party_id"] == "org-party-1"


@pytest.mark.asyncio
async def test_asset_import_create_authz_should_fail_closed_when_legacy_scope_not_resolved() -> None:
    """ownership/organization 无法桥接时应回退 unscoped sentinel。"""
    from src.api.v1.assets import asset_import as module

    request = AssetImportRequest(
        data=[{"ownership_id": "ownership-missing"}],
        import_mode="create",
        should_skip_errors=False,
        is_dry_run=True,
    )

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )
    mock_asset_service = MagicMock()
    mock_asset_service.resolve_owner_party_scope_by_ownership_id_async = AsyncMock(
        return_value=None
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        monkeypatch.setattr(
            module,
            "AsyncAssetService",
            MagicMock(return_value=mock_asset_service),
            raising=False,
        )
        await module._require_asset_import_create_authz(  # type: ignore[attr-defined]
            request=request,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource"]["ownership_id"] == "ownership-missing"
    assert kwargs["resource"]["party_id"] == "__unscoped__:asset:import"
