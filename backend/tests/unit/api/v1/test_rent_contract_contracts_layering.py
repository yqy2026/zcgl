"""分层约束测试：rent_contract contracts 路由应委托服务层。"""

import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from src.core.exception_handler import PermissionDeniedError, ResourceNotFoundError
from src.schemas.rent_contract import RentContractCreate, RentTermCreate

pytestmark = pytest.mark.api


def _build_contract_create_payload() -> RentContractCreate:
    term = RentTermCreate(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        monthly_rent=Decimal("1000.00"),
    )
    return RentContractCreate(
        contract_number="CT-2026-001",
        tenant_name="Tenant A",
        ownership_id="ownership-1",
        asset_ids=["asset-1"],
        sign_date=date(2026, 1, 1),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        rent_terms=[term],
    )


def test_contracts_module_should_not_import_crud_directly() -> None:
    """contracts 路由模块不应直接导入 asset/ownership/rent_contract CRUD。"""
    from src.api.v1.rent_contracts import contracts as module

    module_source = Path(module.__file__).read_text(encoding="utf-8")
    assert "from ....crud.asset import asset_crud" not in module_source
    assert "from ....crud.ownership import ownership" not in module_source
    assert "from ....crud.rent_contract import rent_contract" not in module_source
    assert "asset_crud." not in module_source
    assert "ownership." not in module_source
    assert "rent_contract." not in module_source


def test_contracts_module_should_import_authz_dependency() -> None:
    """contracts 路由应引入统一 ABAC 依赖。"""
    from src.api.v1.rent_contracts import contracts as module

    module_source = Path(module.__file__).read_text(encoding="utf-8")
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_contracts_list_endpoints_should_use_require_authz() -> None:
    """合同列表与资产合同列表端点应接入 require_authz。"""
    from src.api.v1.rent_contracts import contracts as module

    module_source = Path(module.__file__).read_text(encoding="utf-8")
    expected_patterns = [
        r"async def get_contracts[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
        r"async def get_asset_contracts[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_id=\"\{asset_id\}\"",
        r"async def get_asset_contracts[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_create_contract_endpoint_should_use_create_authz_dependency() -> None:
    """创建合同端点必须绑定创建场景专用鉴权依赖。"""
    from src.api.v1.rent_contracts import contracts as module

    module_source = Path(module.__file__).read_text(encoding="utf-8")
    pattern = (
        r"async def create_contract[\s\S]*?"
        r"_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_contract_create_authz\)"
    )
    assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_create_contract_should_delegate_service_validation_and_create() -> None:
    """创建合同应委托服务层做资产/权属校验与创建。"""
    from src.api.v1.rent_contracts import contracts as module
    from src.api.v1.rent_contracts.contracts import create_contract

    mock_service = MagicMock()
    mock_service.get_assets_by_ids_async = AsyncMock(return_value=[MagicMock(id="asset-1")])
    mock_service.get_ownership_by_id_async = AsyncMock(return_value=MagicMock(id="ownership-1"))
    mock_service.create_contract_async = AsyncMock(return_value=MagicMock(id="contract-1"))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        result = await create_contract(
            db=MagicMock(),
            contract_in=_build_contract_create_payload(),
            current_user=MagicMock(),
        )

    assert getattr(result, "id", None) == "contract-1"
    mock_service.get_assets_by_ids_async.assert_awaited_once_with(
        db=ANY,
        asset_ids=["asset-1"],
    )
    mock_service.get_ownership_by_id_async.assert_awaited_once_with(
        db=ANY,
        ownership_id="ownership-1",
    )
    mock_service.create_contract_async.assert_awaited_once_with(
        db=ANY,
        obj_in=ANY,
    )


@pytest.mark.asyncio
async def test_create_contract_should_validate_ownership_even_with_owner_party_id() -> None:
    """创建合同时即使提供 owner_party_id，也应校验 ownership_id。"""
    from src.api.v1.rent_contracts import contracts as module
    from src.api.v1.rent_contracts.contracts import create_contract

    contract_in = _build_contract_create_payload().model_copy(
        update={
            "owner_party_id": "party-1",
            "ownership_id": "ownership-missing",
        }
    )

    mock_service = MagicMock()
    mock_service.get_assets_by_ids_async = AsyncMock(return_value=[MagicMock(id="asset-1")])
    mock_service.get_owner_party_by_id_async = AsyncMock(return_value=MagicMock(id="party-1"))
    mock_service.get_ownership_by_id_async = AsyncMock(return_value=None)
    mock_service.create_contract_async = AsyncMock(return_value=MagicMock(id="contract-1"))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        with pytest.raises(ResourceNotFoundError, match="ownership不存在"):
            await create_contract(
                db=MagicMock(),
                contract_in=contract_in,
                current_user=MagicMock(),
            )

    mock_service.get_owner_party_by_id_async.assert_awaited_once_with(
        db=ANY,
        owner_party_id="party-1",
    )
    mock_service.get_ownership_by_id_async.assert_awaited_once_with(
        db=ANY,
        ownership_id="ownership-missing",
    )
    mock_service.create_contract_async.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_contracts_should_delegate_service_query() -> None:
    """合同列表接口应委托服务层分页查询。"""
    from src.api.v1.rent_contracts import contracts as module
    from src.api.v1.rent_contracts.contracts import get_contracts

    mock_service = MagicMock()
    mock_service.get_contract_page_async = AsyncMock(return_value=([MagicMock(id="c-1")], 1))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(
            module.RentContractResponse,
            "model_validate",
            staticmethod(lambda _: {"id": "c-1"}),
        )
        response = await get_contracts(
            db=MagicMock(),
            current_user=MagicMock(),
            page=2,
            page_size=10,
            contract_number="CT",
            tenant_name="Tenant",
            asset_id="asset-1",
            ownership_id="ownership-1",
            contract_status="ACTIVE",
            start_date=None,
            end_date=None,
        )

    body = json.loads(response.body.decode())
    assert body["data"]["pagination"]["page"] == 2
    assert body["data"]["pagination"]["total"] == 1
    mock_service.get_contract_page_async.assert_awaited_once()
    call_kwargs = mock_service.get_contract_page_async.await_args.kwargs
    assert call_kwargs["db"] is not None
    assert call_kwargs["skip"] == 10
    assert call_kwargs["limit"] == 10
    assert call_kwargs["contract_number"] == "CT"
    assert call_kwargs["tenant_name"] == "Tenant"
    assert call_kwargs["asset_id"] == "asset-1"
    assert call_kwargs["owner_party_id"] is None
    assert call_kwargs["manager_party_id"] is None
    assert call_kwargs["owner_party_ids"] is None
    assert call_kwargs["manager_party_ids"] is None
    assert call_kwargs["ownership_id"] == "ownership-1"
    assert call_kwargs["contract_status"] == "ACTIVE"
    assert call_kwargs["start_date"] is None
    assert call_kwargs["end_date"] is None


@pytest.mark.asyncio
async def test_get_contracts_should_apply_authz_scope_filters() -> None:
    """合同列表应按鉴权上下文注入 owner/manager 作用域过滤。"""
    from src.api.v1.rent_contracts import contracts as module
    from src.api.v1.rent_contracts.contracts import get_contracts

    mock_service = MagicMock()
    mock_service.get_contract_page_async = AsyncMock(return_value=([], 0))

    authz_ctx = module.AuthzContext(
        current_user=MagicMock(id="user-1"),
        action="read",
        resource_type="rent_contract",
        resource_id=None,
        resource_context={
            "owner_party_id": "owner-party-1",
            "manager_party_id": "manager-party-1",
            "owner_party_ids": ["owner-party-1", "owner-party-2"],
            "manager_party_ids": ["manager-party-1", "manager-party-2"],
        },
        allowed=True,
        reason_code="allow",
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        await get_contracts(
            db=MagicMock(),
            current_user=MagicMock(),
            authz_ctx=authz_ctx,
            page=1,
            page_size=10,
            contract_number=None,
            tenant_name=None,
            asset_id=None,
            owner_party_id=None,
            ownership_id=None,
            contract_status=None,
            start_date=None,
            end_date=None,
        )

    mock_service.get_contract_page_async.assert_awaited_once()
    call_kwargs = mock_service.get_contract_page_async.await_args.kwargs
    assert call_kwargs["owner_party_ids"] == ["owner-party-1", "owner-party-2"]
    assert call_kwargs["manager_party_ids"] == ["manager-party-1", "manager-party-2"]
    assert call_kwargs["owner_party_id"] == "owner-party-1"
    assert call_kwargs["manager_party_id"] == "manager-party-1"


@pytest.mark.asyncio
async def test_get_contracts_should_skip_scope_filters_for_admin_bypass() -> None:
    """管理员 bypass 决策下不应套用 resource_context 的作用域提示。"""
    from src.api.v1.rent_contracts import contracts as module
    from src.api.v1.rent_contracts.contracts import get_contracts

    mock_service = MagicMock()
    mock_service.get_contract_page_async = AsyncMock(return_value=([], 0))

    authz_ctx = module.AuthzContext(
        current_user=MagicMock(id="admin-1"),
        action="read",
        resource_type="rent_contract",
        resource_id=None,
        resource_context={
            "owner_party_id": "owner-party-hint",
            "manager_party_id": "manager-party-hint",
            "owner_party_ids": ["owner-party-hint"],
            "manager_party_ids": ["manager-party-hint"],
        },
        allowed=True,
        reason_code="rbac_admin_bypass",
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        await get_contracts(
            db=MagicMock(),
            current_user=MagicMock(),
            authz_ctx=authz_ctx,
            page=1,
            page_size=10,
            contract_number=None,
            tenant_name=None,
            asset_id=None,
            owner_party_id=None,
            ownership_id=None,
            contract_status=None,
            start_date=None,
            end_date=None,
        )

    call_kwargs = mock_service.get_contract_page_async.await_args.kwargs
    assert call_kwargs["owner_party_ids"] is None
    assert call_kwargs["manager_party_ids"] is None
    assert call_kwargs["owner_party_id"] is None
    assert call_kwargs["manager_party_id"] is None


@pytest.mark.asyncio
async def test_get_contracts_should_allow_owner_filter_within_owner_scope_union() -> None:
    """owner 过滤值在 owner scope 并集内时应允许并收敛为单值查询。"""
    from src.api.v1.rent_contracts import contracts as module
    from src.api.v1.rent_contracts.contracts import get_contracts

    mock_service = MagicMock()
    mock_service.get_contract_page_async = AsyncMock(return_value=([], 0))

    authz_ctx = module.AuthzContext(
        current_user=MagicMock(id="user-1"),
        action="read",
        resource_type="rent_contract",
        resource_id=None,
        resource_context={
            "owner_party_id": "owner-party-1",
            "manager_party_id": "manager-party-1",
            "owner_party_ids": ["owner-party-1", "owner-party-2"],
            "manager_party_ids": ["manager-party-1"],
        },
        allowed=True,
        reason_code="allow",
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        await get_contracts(
            db=MagicMock(),
            current_user=MagicMock(),
            authz_ctx=authz_ctx,
            page=1,
            page_size=10,
            contract_number=None,
            tenant_name=None,
            asset_id=None,
            owner_party_id="owner-party-2",
            ownership_id=None,
            contract_status=None,
            start_date=None,
            end_date=None,
        )

    mock_service.get_contract_page_async.assert_awaited_once()
    call_kwargs = mock_service.get_contract_page_async.await_args.kwargs
    assert call_kwargs["owner_party_ids"] == ["owner-party-2"]
    assert call_kwargs["manager_party_ids"] is None
    assert call_kwargs["owner_party_id"] == "owner-party-2"
    assert call_kwargs["manager_party_id"] is None


@pytest.mark.asyncio
async def test_get_contracts_should_forbid_owner_filter_with_manager_only_scope() -> None:
    """仅 manager 作用域时不允许注入 owner_party_id 过滤。"""
    from src.api.v1.rent_contracts import contracts as module
    from src.api.v1.rent_contracts.contracts import get_contracts

    mock_service = MagicMock()
    mock_service.get_contract_page_async = AsyncMock(return_value=([], 0))

    authz_ctx = module.AuthzContext(
        current_user=MagicMock(id="user-1"),
        action="read",
        resource_type="rent_contract",
        resource_id=None,
        resource_context={
            "manager_party_id": "manager-party-1",
            "manager_party_ids": ["manager-party-1", "manager-party-2"],
        },
        allowed=True,
        reason_code="allow",
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        with pytest.raises(Exception) as exc_info:
            await get_contracts(
                db=MagicMock(),
                current_user=MagicMock(),
                authz_ctx=authz_ctx,
                page=1,
                page_size=10,
                contract_number=None,
                tenant_name=None,
                asset_id=None,
                owner_party_id="owner-party-1",
                ownership_id=None,
                contract_status=None,
                start_date=None,
                end_date=None,
            )

    assert getattr(exc_info.value, "status_code", None) == 403
    mock_service.get_contract_page_async.assert_not_called()


@pytest.mark.asyncio
async def test_get_asset_contracts_should_apply_authz_scope_filters() -> None:
    """资产合同列表应按鉴权上下文注入 owner/manager 作用域过滤。"""
    from src.api.v1.rent_contracts import contracts as module
    from src.api.v1.rent_contracts.contracts import get_asset_contracts

    mock_service = MagicMock()
    mock_service.get_asset_contracts_async = AsyncMock(return_value=[])

    authz_ctx = module.AuthzContext(
        current_user=MagicMock(id="user-1"),
        action="read",
        resource_type="rent_contract",
        resource_id=None,
        resource_context={
            "owner_party_id": "owner-party-1",
            "manager_party_id": "manager-party-1",
            "owner_party_ids": ["owner-party-1", "owner-party-2"],
            "manager_party_ids": ["manager-party-1", "manager-party-2"],
        },
        allowed=True,
        reason_code="allow",
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        await get_asset_contracts(
            asset_id="asset-1",
            db=MagicMock(),
            current_user=MagicMock(),
            authz_ctx=authz_ctx,
        )

    mock_service.get_asset_contracts_async.assert_awaited_once_with(
        db=ANY,
        asset_id="asset-1",
        owner_party_id="owner-party-1",
        manager_party_id="manager-party-1",
        owner_party_ids=["owner-party-1", "owner-party-2"],
        manager_party_ids=["manager-party-1", "manager-party-2"],
        limit=1000,
    )


def test_update_contract_should_not_use_legacy_contract_edit_guard() -> None:
    """更新合同端点不应再在函数体内执行 can_edit_contract 旧权限链路。"""
    from src.api.v1.rent_contracts import contracts as module

    module_source = Path(module.__file__).read_text(encoding="utf-8")
    match = re.search(
        r"async def update_contract[\s\S]*?@router.delete",
        module_source,
    )
    assert match is not None
    assert "can_edit_contract(" not in match.group(0)


def test_delete_contract_should_not_use_legacy_admin_guard() -> None:
    """删除合同端点不应再在函数体内执行 RBACService.is_admin 旧权限链路。"""
    from src.api.v1.rent_contracts import contracts as module

    module_source = Path(module.__file__).read_text(encoding="utf-8")
    match = re.search(
        r"async def delete_contract[\s\S]*?@router.get",
        module_source,
    )
    assert match is not None
    endpoint_body = match.group(0)
    assert "RBACService(" not in endpoint_body
    assert ".is_admin(" not in endpoint_body


@pytest.mark.asyncio
async def test_contract_create_authz_should_include_party_scope_context() -> None:
    """创建合同鉴权应携带 owner/manager 主体上下文。"""
    from src.api.v1.rent_contracts import contracts as module

    contract_in = _build_contract_create_payload().model_copy(
        update={
            "owner_party_id": "owner-party-1",
            "manager_party_id": "manager-party-1",
        }
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
        result = await module._require_contract_create_authz(  # type: ignore[attr-defined]
            contract_in=contract_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["ownership_id"] == "ownership-1"
    assert result.resource_context["owner_party_id"] == "owner-party-1"
    assert result.resource_context["manager_party_id"] == "manager-party-1"
    assert result.resource_context["party_id"] == "manager-party-1"
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource_type"] == "rent_contract"
    assert kwargs["action"] == "create"
    assert kwargs["resource_id"] is None
    assert kwargs["resource"]["ownership_id"] == "ownership-1"
    assert kwargs["resource"]["owner_party_id"] == "owner-party-1"
    assert kwargs["resource"]["manager_party_id"] == "manager-party-1"


@pytest.mark.asyncio
async def test_contract_create_authz_should_normalize_party_fields_on_input_model() -> None:
    """创建合同鉴权应将 owner/manager/ownership 字段归一化回写到入参。"""
    from src.api.v1.rent_contracts import contracts as module

    contract_in = _build_contract_create_payload().model_copy(
        update={
            "owner_party_id": " owner-party-1 ",
            "manager_party_id": " manager-party-1 ",
            "ownership_id": " ownership-1 ",
        }
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
        await module._require_contract_create_authz(  # type: ignore[attr-defined]
            contract_in=contract_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert contract_in.owner_party_id == "owner-party-1"
    assert contract_in.manager_party_id == "manager-party-1"
    assert contract_in.ownership_id == "ownership-1"


@pytest.mark.asyncio
async def test_contract_update_authz_should_include_party_scope_context() -> None:
    """更新合同鉴权应携带 owner/manager 主体上下文。"""
    from src.api.v1.rent_contracts import contracts as module

    mock_service = MagicMock()
    mock_service.get_contract_with_details_async = AsyncMock(
        return_value=MagicMock(
            id="contract-1",
            owner_party_id="owner-party-1",
            manager_party_id="manager-party-1",
            ownership_id=None,
        )
    )
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_contract_update_authz(  # type: ignore[attr-defined]
            contract_id="contract-1",
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["contract_id"] == "contract-1"
    assert result.resource_context["owner_party_id"] == "owner-party-1"
    assert result.resource_context["manager_party_id"] == "manager-party-1"
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource_type"] == "rent_contract"
    assert kwargs["action"] == "update"
    assert kwargs["resource_id"] == "contract-1"
    assert kwargs["resource"]["owner_party_id"] == "owner-party-1"
    assert kwargs["resource"]["manager_party_id"] == "manager-party-1"


@pytest.mark.asyncio
async def test_contract_create_authz_should_resolve_party_scope_from_ownership_when_party_fields_absent() -> None:
    """创建合同仅提供 ownership_id 时，应解析并写入对应的 party scope。"""
    from src.api.v1.rent_contracts import contracts as module

    contract_in = _build_contract_create_payload()

    mock_service = MagicMock()
    mock_service.resolve_owner_party_scope_by_ownership_id_async = AsyncMock(
        return_value="owner-party-from-ownership"
    )
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_contract_create_authz(  # type: ignore[attr-defined]
            contract_in=contract_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["ownership_id"] == "ownership-1"
    assert result.resource_context["owner_party_id"] == "owner-party-from-ownership"
    assert result.resource_context["party_id"] == "owner-party-from-ownership"
    mock_service.resolve_owner_party_scope_by_ownership_id_async.assert_awaited_once_with(
        db=ANY,
        ownership_id="ownership-1",
    )
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource"]["owner_party_id"] == "owner-party-from-ownership"
    assert kwargs["resource"]["party_id"] == "owner-party-from-ownership"
    assert kwargs["resource"]["ownership_id"] == "ownership-1"


@pytest.mark.asyncio
async def test_contract_create_authz_should_backfill_owner_party_id_for_persistence() -> None:
    """创建合同在 legacy ownership_id 场景应回填 owner_party_id 到入参对象。"""
    from src.api.v1.rent_contracts import contracts as module

    contract_in = _build_contract_create_payload()

    mock_service = MagicMock()
    mock_service.resolve_owner_party_scope_by_ownership_id_async = AsyncMock(
        return_value="owner-party-from-ownership"
    )
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        await module._require_contract_create_authz(  # type: ignore[attr-defined]
            contract_in=contract_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert contract_in.owner_party_id == "owner-party-from-ownership"


@pytest.mark.asyncio
async def test_contract_create_authz_should_infer_manager_scope_before_ownership_scope() -> None:
    """创建合同在 legacy payload 下应先注入 manager scope，避免 manager-only 误拒绝。"""
    from src.api.v1.rent_contracts import contracts as module

    contract_in = _build_contract_create_payload()

    mock_service = MagicMock()
    mock_service.resolve_owner_party_scope_by_ownership_id_async = AsyncMock(
        return_value="owner-party-from-ownership"
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

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_contract_create_authz(  # type: ignore[attr-defined]
            contract_in=contract_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["manager_party_id"] == "subject-manager"
    assert result.resource_context["owner_party_id"] == "owner-party-from-ownership"
    assert result.resource_context["party_id"] == "subject-manager"
    mock_service.resolve_owner_party_scope_by_ownership_id_async.assert_awaited_once_with(
        db=ANY,
        ownership_id="ownership-1",
    )
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource"]["manager_party_id"] == "subject-manager"
    assert kwargs["resource"]["owner_party_id"] == "owner-party-from-ownership"
    assert kwargs["resource"]["party_id"] == "subject-manager"


@pytest.mark.asyncio
async def test_create_contract_should_backfill_owner_party_from_authz_context() -> None:
    """创建合同端点应基于鉴权上下文兜底回填 owner_party_id。"""
    from src.api.v1.rent_contracts import contracts as module
    from src.api.v1.rent_contracts.contracts import create_contract

    contract_in = _build_contract_create_payload().model_copy(
        update={"asset_ids": [], "owner_party_id": None}
    )
    current_user = MagicMock(id="user-1")
    authz_ctx = module.AuthzContext(
        current_user=current_user,
        action="create",
        resource_type="rent_contract",
        resource_id=None,
        resource_context={"owner_party_id": "owner-party-from-authz"},
        allowed=True,
        reason_code="allow",
    )

    mock_service = MagicMock()
    mock_service.get_owner_party_by_id_async = AsyncMock(return_value=MagicMock(id="party-1"))
    mock_service.get_ownership_by_id_async = AsyncMock(return_value=MagicMock(id="ownership-1"))
    mock_service.create_contract_async = AsyncMock(return_value=MagicMock(id="contract-1"))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        result = await create_contract(
            db=MagicMock(),
            contract_in=contract_in,
            current_user=current_user,
            _authz_ctx=authz_ctx,
        )

    assert contract_in.owner_party_id == "owner-party-from-authz"
    assert getattr(result, "id", None) == "contract-1"
    mock_service.get_owner_party_by_id_async.assert_awaited_once_with(
        db=ANY,
        owner_party_id="owner-party-from-authz",
    )
    assert mock_service.create_contract_async.await_args.kwargs["obj_in"] is contract_in


@pytest.mark.asyncio
async def test_contract_create_authz_should_not_force_unscoped_party_when_ownership_scope_unresolved() -> None:
    """创建合同 ownership scope 无法解析时，不应写入 unscoped 哨兵。"""
    from src.api.v1.rent_contracts import contracts as module

    contract_in = _build_contract_create_payload()

    mock_service = MagicMock()
    mock_service.resolve_owner_party_scope_by_ownership_id_async = AsyncMock(return_value=None)
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_contract_create_authz(  # type: ignore[attr-defined]
            contract_in=contract_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["ownership_id"] == "ownership-1"
    assert "party_id" not in result.resource_context
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource"]["ownership_id"] == "ownership-1"
    assert "party_id" not in kwargs["resource"]


@pytest.mark.asyncio
async def test_contract_update_authz_should_resolve_party_scope_from_ownership_when_party_fields_absent() -> None:
    """更新合同 owner/manager 为空时，应从 ownership_id 回退解析 party scope。"""
    from src.api.v1.rent_contracts import contracts as module

    mock_service = MagicMock()
    mock_service.get_contract_with_details_async = AsyncMock(
        return_value=MagicMock(
            id="contract-1",
            owner_party_id=None,
            manager_party_id=None,
            ownership_id="ownership-1",
        )
    )
    mock_service.resolve_owner_party_scope_by_ownership_id_async = AsyncMock(
        return_value="owner-party-from-ownership"
    )
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_contract_update_authz(  # type: ignore[attr-defined]
            contract_id="contract-1",
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["ownership_id"] == "ownership-1"
    assert result.resource_context["owner_party_id"] == "owner-party-from-ownership"
    assert result.resource_context["party_id"] == "owner-party-from-ownership"
    mock_service.resolve_owner_party_scope_by_ownership_id_async.assert_awaited_once_with(
        db=ANY,
        ownership_id="ownership-1",
    )
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource"]["owner_party_id"] == "owner-party-from-ownership"
    assert kwargs["resource"]["party_id"] == "owner-party-from-ownership"


@pytest.mark.asyncio
async def test_contract_update_authz_should_fail_closed_when_ownership_scope_unresolved() -> None:
    """更新合同 owner/manager 均缺失且 ownership scope 无法解析时，应 fail-closed。"""
    from src.api.v1.rent_contracts import contracts as module

    mock_service = MagicMock()
    mock_service.get_contract_with_details_async = AsyncMock(
        return_value=MagicMock(
            id="contract-1",
            owner_party_id=None,
            manager_party_id=None,
            ownership_id="ownership-1",
        )
    )
    mock_service.resolve_owner_party_scope_by_ownership_id_async = AsyncMock(return_value=None)
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=False,
            reason_code="deny_by_default",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        with pytest.raises(PermissionDeniedError, match="权限不足"):
            await module._require_contract_update_authz(  # type: ignore[attr-defined]
                contract_id="contract-1",
                current_user=MagicMock(id="user-1"),
                db=MagicMock(),
            )

    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource"]["ownership_id"] == "ownership-1"
    assert kwargs["resource"]["party_id"] == module._CONTRACT_MUTATION_UNSCOPED_PARTY_ID  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_contract_delete_authz_should_raise_not_found_before_abac() -> None:
    """删除合同鉴权应先解析合同，不存在时返回 404 且不触发 ABAC。"""
    from src.api.v1.rent_contracts import contracts as module

    mock_service = MagicMock()
    mock_service.get_contract_with_details_async = AsyncMock(return_value=None)
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        with pytest.raises(ResourceNotFoundError, match="contract不存在"):
            await module._require_contract_delete_authz(  # type: ignore[attr-defined]
                contract_id="contract-404",
                current_user=MagicMock(id="user-1"),
                db=MagicMock(),
            )

    mock_authz_service.check_access.assert_not_awaited()
