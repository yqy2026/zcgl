"""分层约束测试：assets 路由关键端点应接入统一 ABAC 依赖。"""

import re
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api

_ASSETS_API_MODULE_PATH = Path(__file__).resolve().parents[4] / "src/api/v1/assets/assets.py"


def _read_module_source() -> str:
    return _ASSETS_API_MODULE_PATH.read_text(encoding="utf-8")


def test_assets_module_should_import_authz_dependency() -> None:
    """assets 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "get_current_active_user" in module_source
    assert "require_authz" in module_source
    assert "require_permission(" not in module_source


def test_assets_endpoints_should_use_authz_dependencies() -> None:
    """assets 本批关键端点应接入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def get_assets[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_asset_collection_read_authz\)",
        r"async def create_asset[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_asset_create_authz\)",
        r"async def get_ownership_entities[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_asset_collection_read_authz\)",
        r"async def get_business_categories[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_asset_collection_read_authz\)",
        r"async def get_usage_statuses[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_asset_collection_read_authz\)",
        r"async def get_property_natures[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_asset_collection_read_authz\)",
        r"async def get_ownership_statuses[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_asset_collection_read_authz\)",
        r"async def restore_asset[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_id=\"\{asset_id\}\"",
        r"async def hard_delete_asset[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_id=\"\{asset_id\}\"",
        r"async def get_asset_history[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_id=\"\{asset_id\}\"[\s\S]*?deny_as_not_found=True",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_asset_create_authz_should_include_party_scope_context() -> None:
    """创建资产鉴权应携带 owner/manager 主体上下文。"""
    from src.api.v1.assets import assets as module

    asset_in = MagicMock(
        owner_party_id="owner-party-1",
        manager_party_id="manager-party-1",
        ownership_id="ownership-1",
        organization_id="org-1",
    )

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        monkeypatch.setattr(
            module,
            "_resolve_owner_party_scope_by_ownership_id",
            AsyncMock(return_value=None),
            raising=False,
        )
        result = await module._require_asset_create_authz(  # type: ignore[attr-defined]
            asset_in=asset_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["owner_party_id"] == "owner-party-1"
    assert result.resource_context["manager_party_id"] == "manager-party-1"
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource_type"] == "asset"
    assert kwargs["action"] == "create"
    assert kwargs["resource_id"] is None
    assert kwargs["resource"]["owner_party_id"] == "owner-party-1"
    assert kwargs["resource"]["manager_party_id"] == "manager-party-1"


@pytest.mark.asyncio
async def test_get_assets_should_pass_selected_view_party_filter_to_service() -> None:
    """资产列表必须把当前已选视角收窄条件透传到 service。"""
    from src.api.v1.assets import assets as module

    selected_view_party_filter = MagicMock()
    mock_asset_service = MagicMock()
    mock_asset_service.get_assets = AsyncMock(return_value=([], 0))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "AsyncAssetService", lambda db: mock_asset_service)
        monkeypatch.setattr(
            module._asset_list_item_adapter,
            "validate_python",
            MagicMock(return_value=[]),
        )

        await module.get_assets(
            request=MagicMock(),
            page=1,
            page_size=20,
            search=None,
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            ownership_id=None,
            management_entity=None,
            business_category=None,
            data_status=None,
            min_area=None,
            max_area=None,
            min_occupancy_rate=None,
            max_occupancy_rate=None,
            is_litigated=None,
            db=MagicMock(),
            current_user=MagicMock(id="user-1"),
            _authz_ctx=MagicMock(),
            selected_view_party_filter=selected_view_party_filter,
            sort_field=None,
            sort_by=None,
            sort_order="desc",
            include_relations=False,
        )

    _args, kwargs = mock_asset_service.get_assets.await_args
    assert kwargs["party_filter"] is selected_view_party_filter
    assert kwargs["current_user_id"] == "user-1"


@pytest.mark.asyncio
async def test_get_asset_should_pass_selected_view_party_filter_to_service() -> None:
    """资产详情必须把当前已选视角收窄条件透传到 service。"""
    from src.api.v1.assets import assets as module

    selected_view_party_filter = MagicMock()
    mock_asset_service = MagicMock()
    asset_result = MagicMock(name="asset-result")
    mock_asset_service.get_asset = AsyncMock(return_value=asset_result)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "AsyncAssetService", lambda db: mock_asset_service)
        monkeypatch.setattr(
            module.AssetResponse,
            "model_validate",
            MagicMock(return_value=asset_result),
        )

        result = await module.get_asset(
            request=MagicMock(),
            asset_id="asset-1",
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
            _authz_ctx=MagicMock(),
            selected_view_party_filter=selected_view_party_filter,
        )

    _args, kwargs = mock_asset_service.get_asset.await_args
    assert kwargs["party_filter"] is selected_view_party_filter
    assert kwargs["current_user_id"] == "user-1"
    assert result is asset_result


@pytest.mark.asyncio
async def test_asset_create_authz_should_normalize_party_fields_on_input_model() -> None:
    """创建资产鉴权应将 owner/manager/ownership/org 字段归一化回写到入参。"""
    from src.api.v1.assets import assets as module

    asset_in = MagicMock(
        owner_party_id=" owner-party-1 ",
        manager_party_id=" manager-party-1 ",
        ownership_id=" ownership-1 ",
        organization_id=" org-1 ",
    )

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        monkeypatch.setattr(
            module,
            "_resolve_owner_party_scope_by_ownership_id",
            AsyncMock(return_value=None),
            raising=False,
        )
        await module._require_asset_create_authz(  # type: ignore[attr-defined]
            asset_in=asset_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert asset_in.owner_party_id == "owner-party-1"
    assert asset_in.manager_party_id == "manager-party-1"
    assert asset_in.ownership_id == "ownership-1"
    assert asset_in.organization_id == "org-1"


@pytest.mark.asyncio
async def test_asset_create_authz_should_fallback_to_unscoped_party_context() -> None:
    """创建资产缺少主体字段时应写入 unscoped 哨兵，避免空上下文放行。"""
    from src.api.v1.assets import assets as module

    asset_in = MagicMock(
        owner_party_id=None,
        manager_party_id=None,
        ownership_id="ownership-1",
        organization_id=None,
    )

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        monkeypatch.setattr(
            module,
            "_resolve_owner_party_scope_by_ownership_id",
            AsyncMock(return_value=None),
            raising=False,
        )
        result = await module._require_asset_create_authz(  # type: ignore[attr-defined]
            asset_in=asset_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["party_id"] == module._ASSET_CREATE_UNSCOPED_PARTY_ID  # type: ignore[attr-defined]
    assert result.resource_context["ownership_id"] == "ownership-1"


@pytest.mark.asyncio
async def test_asset_create_authz_should_resolve_party_scope_from_ownership_id() -> None:
    """创建资产在 legacy ownership_id 场景应回填 owner/party scope。"""
    from src.api.v1.assets import assets as module

    asset_in = MagicMock(
        owner_party_id=None,
        manager_party_id=None,
        ownership_id="ownership-1",
        organization_id=None,
    )

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        monkeypatch.setattr(
            module,
            "_resolve_owner_party_scope_by_ownership_id",
            AsyncMock(return_value="party-from-ownership"),
            raising=False,
        )
        result = await module._require_asset_create_authz(  # type: ignore[attr-defined]
            asset_in=asset_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["owner_party_id"] == "party-from-ownership"
    assert result.resource_context["party_id"] == "party-from-ownership"
    assert result.resource_context["ownership_id"] == "ownership-1"


@pytest.mark.asyncio
async def test_asset_create_authz_should_backfill_owner_party_id_for_persistence() -> None:
    """创建资产在 legacy ownership_id 场景应回填 owner_party_id 到入参对象。"""
    from src.api.v1.assets import assets as module

    asset_in = MagicMock(
        owner_party_id=None,
        manager_party_id=None,
        ownership_id="ownership-1",
        organization_id=None,
    )

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        monkeypatch.setattr(
            module,
            "_resolve_owner_party_scope_by_ownership_id",
            AsyncMock(return_value="party-from-ownership"),
            raising=False,
        )
        await module._require_asset_create_authz(  # type: ignore[attr-defined]
            asset_in=asset_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert asset_in.owner_party_id == "party-from-ownership"


@pytest.mark.asyncio
async def test_asset_create_authz_should_infer_manager_scope_before_ownership_scope() -> None:
    """创建资产在 legacy payload 下应先注入 manager scope，避免 manager-only 误拒绝。"""
    from src.api.v1.assets import assets as module

    asset_in = MagicMock(
        owner_party_id=None,
        manager_party_id=None,
        ownership_id="ownership-1",
        organization_id=None,
    )

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )
    mock_authz_service.context_builder = MagicMock()
    mock_authz_service.context_builder.build_subject_context = AsyncMock(
        return_value=MagicMock(
            owner_party_ids=[],
            manager_party_ids=["subject-manager"],
        )
    )
    resolve_owner_scope = AsyncMock(return_value="owner-party-from-ownership")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        monkeypatch.setattr(
            module,
            "_resolve_owner_party_scope_by_ownership_id",
            resolve_owner_scope,
            raising=False,
        )
        result = await module._require_asset_create_authz(  # type: ignore[attr-defined]
            asset_in=asset_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["manager_party_id"] == "subject-manager"
    assert result.resource_context["owner_party_id"] == "owner-party-from-ownership"
    assert result.resource_context["party_id"] == "subject-manager"
    resolve_owner_scope.assert_awaited_once_with(
        db=ANY,
        ownership_id="ownership-1",
    )
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource"]["manager_party_id"] == "subject-manager"
    assert kwargs["resource"]["owner_party_id"] == "owner-party-from-ownership"
    assert kwargs["resource"]["party_id"] == "subject-manager"


@pytest.mark.asyncio
async def test_asset_collection_read_authz_should_merge_ownership_scope_and_subject_scope() -> None:
    """集合读取鉴权应合并 ownership scope 与 subject scope hint。"""
    from src.api.v1.assets import assets as module

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        monkeypatch.setattr(
            module,
            "_resolve_owner_party_scope_by_ownership_id",
            AsyncMock(return_value="owner-party-from-ownership"),
            raising=False,
        )
        monkeypatch.setattr(
            module,
            "_build_subject_scope_hint",
            AsyncMock(
                return_value={
                    "owner_party_id": "subject-owner",
                    "manager_party_id": "subject-manager",
                    "party_id": "subject-owner",
                }
            ),
            raising=False,
        )
        result = await module._require_asset_collection_read_authz(  # type: ignore[attr-defined]
            ownership_id="ownership-1",
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["ownership_id"] == "ownership-1"
    assert result.resource_context["owner_party_id"] == "owner-party-from-ownership"
    assert result.resource_context["manager_party_id"] == "subject-manager"
    assert result.resource_context["party_id"] == "owner-party-from-ownership"


@pytest.mark.asyncio
async def test_asset_collection_read_authz_should_inject_subject_scope_without_ownership_filter() -> None:
    """集合读取在无 ownership 参数时仍应注入 subject scope，避免无上下文拒绝。"""
    from src.api.v1.assets import assets as module

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )
    resolve_ownership_scope = AsyncMock(return_value=None)
    subject_scope_hint = {
        "owner_party_id": "subject-owner",
        "manager_party_id": "subject-manager",
        "party_id": "subject-owner",
    }

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        monkeypatch.setattr(
            module,
            "_resolve_owner_party_scope_by_ownership_id",
            resolve_ownership_scope,
            raising=False,
        )
        monkeypatch.setattr(
            module,
            "_build_subject_scope_hint",
            AsyncMock(return_value=subject_scope_hint),
            raising=False,
        )
        result = await module._require_asset_collection_read_authz(  # type: ignore[attr-defined]
            ownership_id=None,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert "ownership_id" not in result.resource_context
    assert result.resource_context["owner_party_id"] == "subject-owner"
    assert result.resource_context["manager_party_id"] == "subject-manager"
    assert result.resource_context["party_id"] == "subject-owner"
    assert resolve_ownership_scope.await_count == 0

    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource"]["party_id"] == "subject-owner"


@pytest.mark.asyncio
async def test_create_asset_should_backfill_owner_party_from_authz_context() -> None:
    """创建资产端点应基于鉴权上下文兜底回填 owner_party_id。"""
    from src.api.v1.assets import assets as module

    mock_service = MagicMock()
    mock_service.create_asset = AsyncMock(return_value=MagicMock(id="asset-1"))

    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {}
    asset_in = MagicMock(owner_party_id=None)
    current_user = MagicMock(id="user-1")
    authz_ctx = module.AuthzContext(
        current_user=current_user,
        action="create",
        resource_type="asset",
        resource_id=None,
        resource_context={"owner_party_id": "owner-party-from-authz"},
        allowed=True,
        reason_code="allow",
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "AsyncAssetService", lambda _db: mock_service)
        monkeypatch.setattr(
            module.AssetResponse,
            "model_validate",
            staticmethod(lambda _: {"id": "asset-1"}),
        )
        result = await module.create_asset(
            asset_in=asset_in,
            request=request,
            db=MagicMock(),
            current_user=current_user,
            _authz_ctx=authz_ctx,
            audit_logger=MagicMock(),
        )

    assert asset_in.owner_party_id == "owner-party-from-authz"
    assert result["id"] == "asset-1"
    assert mock_service.create_asset.await_args.args[0] is asset_in
