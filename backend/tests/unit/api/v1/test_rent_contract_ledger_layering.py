"""分层约束测试：rent_contract ledger 路由应委托服务层。"""

import json
import re
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from src.schemas.rent_contract import GenerateLedgerRequest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.rent_contracts import ledger as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_ledger_module_should_not_import_rent_ledger_crud_directly() -> None:
    """ledger 路由模块不应直接导入 rent_ledger。"""
    module_source = _read_module_source()
    assert "from ....crud.rent_contract import rent_ledger" not in module_source
    assert "rent_ledger." not in module_source


def test_ledger_module_should_import_authz_dependency() -> None:
    """ledger 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_ledger_endpoints_should_use_require_authz() -> None:
    """关键台账端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def get_contract_deposit_ledger[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"[\s\S]*?resource_id=\"\{contract_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def get_contract_service_fee_ledger[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"[\s\S]*?resource_id=\"\{contract_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def generate_monthly_ledger[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_ledger_generate_authz\)",
        r"async def get_rent_ledger[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
        r"async def get_rent_ledger_detail[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_ledger_read_authz\)",
        r"async def batch_update_rent_ledger[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"rent_contract\"[\s\S]*?resource_context=_RENT_LEDGER_BATCH_UPDATE_RESOURCE_CONTEXT",
        r"async def update_rent_ledger[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_ledger_update_authz\)",
        r"async def get_contract_ledger[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"[\s\S]*?resource_id=\"\{contract_id\}\"[\s\S]*?deny_as_not_found=True",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_ledger_batch_update_unscoped_context_should_be_defined() -> None:
    from src.api.v1.rent_contracts import ledger as module

    expected = "__unscoped__:rent_contract_ledger:batch_update"
    assert module._RENT_LEDGER_BATCH_UPDATE_UNSCOPED_PARTY_ID == expected
    assert module._RENT_LEDGER_BATCH_UPDATE_RESOURCE_CONTEXT == {
        "party_id": expected,
        "owner_party_id": expected,
        "manager_party_id": expected,
    }


@pytest.mark.asyncio
async def test_get_rent_ledger_should_delegate_service_query() -> None:
    """租金台账列表接口应委托 rent_contract_service.get_rent_ledger_page_async。"""
    from src.api.v1.rent_contracts import ledger as module
    from src.api.v1.rent_contracts.ledger import get_rent_ledger

    mock_service = MagicMock()
    mock_service.get_rent_ledger_page_async = AsyncMock(return_value=([MagicMock()], 1))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(
            module.RentLedgerResponse,
            "model_validate",
            staticmethod(lambda _: {"id": "ledger-1"}),
        )
        response = await get_rent_ledger(
            db=MagicMock(),
            current_user=MagicMock(),
            page=1,
            page_size=10,
            contract_id=None,
            asset_id=None,
            ownership_id=None,
            year_month=None,
            payment_status=None,
            start_date=None,
            end_date=None,
        )

    payload = json.loads(response.body)
    assert payload["data"]["pagination"]["total"] == 1
    mock_service.get_rent_ledger_page_async.assert_awaited_once_with(
        db=ANY,
        skip=0,
        limit=10,
        contract_id=None,
        asset_id=None,
        owner_party_id=None,
        manager_party_id=None,
        owner_party_ids=None,
        manager_party_ids=None,
        ownership_id=None,
        year_month=None,
        payment_status=None,
        start_date=None,
        end_date=None,
    )


@pytest.mark.asyncio
async def test_get_rent_ledger_should_apply_authz_scope_filters() -> None:
    """租金台账列表应按鉴权上下文注入 owner/manager 多主体作用域过滤。"""
    from src.api.v1.rent_contracts import ledger as module
    from src.api.v1.rent_contracts.ledger import get_rent_ledger

    mock_service = MagicMock()
    mock_service.get_rent_ledger_page_async = AsyncMock(return_value=([], 0))

    authz_ctx = module.AuthzContext(
        current_user=MagicMock(id="user-1"),
        action="read",
        resource_type="rent_contract",
        resource_id=None,
        resource_context={
            "owner_party_ids": ["owner-party-1", "owner-party-2"],
            "manager_party_ids": ["manager-party-1", "manager-party-2"],
            "owner_party_id": "owner-party-1",
            "manager_party_id": "manager-party-1",
        },
        allowed=True,
        reason_code="allow",
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        await get_rent_ledger(
            db=MagicMock(),
            current_user=MagicMock(),
            authz_ctx=authz_ctx,
            page=1,
            page_size=10,
            contract_id=None,
            asset_id=None,
            owner_party_id=None,
            ownership_id=None,
            year_month=None,
            payment_status=None,
            start_date=None,
            end_date=None,
        )

    mock_service.get_rent_ledger_page_async.assert_awaited_once_with(
        db=ANY,
        skip=0,
        limit=10,
        contract_id=None,
        asset_id=None,
        owner_party_id="owner-party-1",
        manager_party_id="manager-party-1",
        owner_party_ids=["owner-party-1", "owner-party-2"],
        manager_party_ids=["manager-party-1", "manager-party-2"],
        ownership_id=None,
        year_month=None,
        payment_status=None,
        start_date=None,
        end_date=None,
    )


@pytest.mark.asyncio
async def test_get_rent_ledger_should_skip_scope_filters_for_admin_bypass() -> None:
    """管理员 bypass 决策下不应套用 resource_context 的作用域提示。"""
    from src.api.v1.rent_contracts import ledger as module
    from src.api.v1.rent_contracts.ledger import get_rent_ledger

    mock_service = MagicMock()
    mock_service.get_rent_ledger_page_async = AsyncMock(return_value=([], 0))

    authz_ctx = module.AuthzContext(
        current_user=MagicMock(id="admin-1"),
        action="read",
        resource_type="rent_contract",
        resource_id=None,
        resource_context={
            "owner_party_ids": ["owner-party-hint"],
            "manager_party_ids": ["manager-party-hint"],
            "owner_party_id": "owner-party-hint",
            "manager_party_id": "manager-party-hint",
        },
        allowed=True,
        reason_code="rbac_admin_bypass",
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        await get_rent_ledger(
            db=MagicMock(),
            current_user=MagicMock(),
            authz_ctx=authz_ctx,
            page=1,
            page_size=10,
            contract_id=None,
            asset_id=None,
            owner_party_id=None,
            ownership_id=None,
            year_month=None,
            payment_status=None,
            start_date=None,
            end_date=None,
        )

    mock_service.get_rent_ledger_page_async.assert_awaited_once_with(
        db=ANY,
        skip=0,
        limit=10,
        contract_id=None,
        asset_id=None,
        owner_party_id=None,
        manager_party_id=None,
        owner_party_ids=None,
        manager_party_ids=None,
        ownership_id=None,
        year_month=None,
        payment_status=None,
        start_date=None,
        end_date=None,
    )


@pytest.mark.asyncio
async def test_get_rent_ledger_should_allow_owner_filter_within_scoped_owner_collection() -> None:
    """请求 owner 过滤命中鉴权 owner 列表时应允许并按请求收窄。"""
    from src.api.v1.rent_contracts import ledger as module
    from src.api.v1.rent_contracts.ledger import get_rent_ledger

    mock_service = MagicMock()
    mock_service.get_rent_ledger_page_async = AsyncMock(return_value=([], 0))

    authz_ctx = module.AuthzContext(
        current_user=MagicMock(id="user-1"),
        action="read",
        resource_type="rent_contract",
        resource_id=None,
        resource_context={
            "owner_party_ids": ["owner-party-1", "owner-party-2"],
            "manager_party_ids": ["manager-party-1", "manager-party-2"],
            "owner_party_id": "owner-party-1",
            "manager_party_id": "manager-party-1",
        },
        allowed=True,
        reason_code="allow",
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        await get_rent_ledger(
            db=MagicMock(),
            current_user=MagicMock(),
            authz_ctx=authz_ctx,
            page=1,
            page_size=10,
            contract_id=None,
            asset_id=None,
            owner_party_id="owner-party-2",
            ownership_id=None,
            year_month=None,
            payment_status=None,
            start_date=None,
            end_date=None,
        )

    mock_service.get_rent_ledger_page_async.assert_awaited_once_with(
        db=ANY,
        skip=0,
        limit=10,
        contract_id=None,
        asset_id=None,
        owner_party_id="owner-party-2",
        manager_party_id=None,
        owner_party_ids=["owner-party-2"],
        manager_party_ids=None,
        ownership_id=None,
        year_month=None,
        payment_status=None,
        start_date=None,
        end_date=None,
    )


@pytest.mark.asyncio
async def test_get_rent_ledger_should_forbid_owner_scope_override() -> None:
    """请求 owner_party_id 与鉴权 owner scope 不一致时应拒绝。"""
    from src.api.v1.rent_contracts import ledger as module
    from src.api.v1.rent_contracts.ledger import get_rent_ledger

    mock_service = MagicMock()
    mock_service.get_rent_ledger_page_async = AsyncMock(return_value=([], 0))

    authz_ctx = module.AuthzContext(
        current_user=MagicMock(id="user-1"),
        action="read",
        resource_type="rent_contract",
        resource_id=None,
        resource_context={"owner_party_id": "owner-party-1"},
        allowed=True,
        reason_code="allow",
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        with pytest.raises(Exception) as exc_info:
            await get_rent_ledger(
                db=MagicMock(),
                current_user=MagicMock(),
                authz_ctx=authz_ctx,
                page=1,
                page_size=10,
                contract_id=None,
                asset_id=None,
                owner_party_id="owner-party-2",
                ownership_id=None,
                year_month=None,
                payment_status=None,
                start_date=None,
                end_date=None,
            )

    assert getattr(exc_info.value, "status_code", None) == 403
    mock_service.get_rent_ledger_page_async.assert_not_called()


@pytest.mark.asyncio
async def test_get_rent_ledger_should_forbid_owner_filter_with_manager_only_scope() -> None:
    """仅 manager 作用域时不允许注入 owner_party_id 过滤。"""
    from src.api.v1.rent_contracts import ledger as module
    from src.api.v1.rent_contracts.ledger import get_rent_ledger

    mock_service = MagicMock()
    mock_service.get_rent_ledger_page_async = AsyncMock(return_value=([], 0))

    authz_ctx = module.AuthzContext(
        current_user=MagicMock(id="user-1"),
        action="read",
        resource_type="rent_contract",
        resource_id=None,
        resource_context={"manager_party_id": "manager-party-1"},
        allowed=True,
        reason_code="allow",
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        with pytest.raises(Exception) as exc_info:
            await get_rent_ledger(
                db=MagicMock(),
                current_user=MagicMock(),
                authz_ctx=authz_ctx,
                page=1,
                page_size=10,
                contract_id=None,
                asset_id=None,
                owner_party_id="owner-party-1",
                ownership_id=None,
                year_month=None,
                payment_status=None,
                start_date=None,
                end_date=None,
            )

    assert getattr(exc_info.value, "status_code", None) == 403
    mock_service.get_rent_ledger_page_async.assert_not_called()


@pytest.mark.asyncio
async def test_get_rent_ledger_detail_should_delegate_service_lookup() -> None:
    """台账详情接口应委托 rent_contract_service.get_rent_ledger_by_id_async。"""
    from src.api.v1.rent_contracts import ledger as module
    from src.api.v1.rent_contracts.ledger import get_rent_ledger_detail

    mock_service = MagicMock()
    mock_service.get_rent_ledger_by_id_async = AsyncMock(return_value=MagicMock(id="ledger-1"))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        result = await get_rent_ledger_detail(
            ledger_id="ledger-1",
            db=MagicMock(),
            current_user=MagicMock(),
        )

    assert getattr(result, "id", None) == "ledger-1"
    mock_service.get_rent_ledger_by_id_async.assert_awaited_once_with(
        db=ANY,
        ledger_id="ledger-1",
    )


@pytest.mark.asyncio
async def test_get_contract_ledger_should_delegate_service_query() -> None:
    """合同台账接口应委托 rent_contract_service.get_contract_ledger_async。"""
    from src.api.v1.rent_contracts import ledger as module
    from src.api.v1.rent_contracts.ledger import get_contract_ledger

    mock_service = MagicMock()
    mock_service.get_contract_ledger_async = AsyncMock(return_value=[MagicMock(id="ledger-1")])

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        result = await get_contract_ledger(
            contract_id="contract-1",
            db=MagicMock(),
            current_user=MagicMock(),
        )

    assert len(result) == 1
    mock_service.get_contract_ledger_async.assert_awaited_once_with(
        db=ANY,
        contract_id="contract-1",
        limit=1000,
    )


@pytest.mark.asyncio
async def test_ledger_generate_authz_should_include_contract_scope_context() -> None:
    """台账生成 create 鉴权应基于目标合同解析 owner/manager 上下文。"""
    from src.api.v1.rent_contracts import ledger as module

    mock_service = MagicMock()
    mock_service.get_contract_with_details_async = AsyncMock(
        return_value=MagicMock(
            id="contract-1",
            owner_party_id="owner-party-1",
            manager_party_id="manager-party-1",
            ownership_id="ownership-1",
        )
    )
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_ledger_generate_authz(  # type: ignore[attr-defined]
            request=GenerateLedgerRequest(contract_id="contract-1"),
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["contract_id"] == "contract-1"
    assert result.resource_context["owner_party_id"] == "owner-party-1"
    assert result.resource_context["manager_party_id"] == "manager-party-1"
    assert result.resource_context["ownership_id"] == "ownership-1"
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource_type"] == "rent_contract"
    assert kwargs["action"] == "create"
    assert kwargs["resource_id"] == "contract-1"
    assert kwargs["resource"]["owner_party_id"] == "owner-party-1"


@pytest.mark.asyncio
async def test_ledger_generate_authz_should_resolve_owner_party_from_legacy_ownership() -> None:
    """台账生成鉴权在 party 列为空时应从 ownership 解析 owner_party。"""
    from src.api.v1.rent_contracts import ledger as module

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
        return_value="owner-party-legacy-1"
    )
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_ledger_generate_authz(  # type: ignore[attr-defined]
            request=GenerateLedgerRequest(contract_id="contract-1"),
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["ownership_id"] == "ownership-1"
    assert result.resource_context["owner_party_id"] == "owner-party-legacy-1"
    assert result.resource_context["party_id"] == "owner-party-legacy-1"
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource"]["owner_party_id"] == "owner-party-legacy-1"
    assert kwargs["resource"]["party_id"] == "owner-party-legacy-1"


@pytest.mark.asyncio
async def test_ledger_generate_authz_should_backfill_owner_scope_when_manager_party_exists() -> None:
    """台账生成鉴权在 owner 为空但 manager 存在时仍应桥接 legacy ownership。"""
    from src.api.v1.rent_contracts import ledger as module

    mock_service = MagicMock()
    mock_service.get_contract_with_details_async = AsyncMock(
        return_value=MagicMock(
            id="contract-1",
            owner_party_id=None,
            manager_party_id="manager-party-1",
            ownership_id="ownership-1",
        )
    )
    mock_service.resolve_owner_party_scope_by_ownership_id_async = AsyncMock(
        return_value="owner-party-legacy-1"
    )
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_ledger_generate_authz(  # type: ignore[attr-defined]
            request=GenerateLedgerRequest(contract_id="contract-1"),
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["manager_party_id"] == "manager-party-1"
    assert result.resource_context["owner_party_id"] == "owner-party-legacy-1"
    assert result.resource_context["party_id"] == "manager-party-1"
    mock_service.resolve_owner_party_scope_by_ownership_id_async.assert_awaited_once_with(
        db=ANY,
        ownership_id="ownership-1",
    )


@pytest.mark.asyncio
async def test_ledger_generate_authz_should_fail_closed_when_legacy_ownership_not_resolved() -> None:
    """台账生成鉴权在 legacy ownership 无法桥接时应使用 unscoped sentinel。"""
    from src.api.v1.rent_contracts import ledger as module

    mock_service = MagicMock()
    mock_service.get_contract_with_details_async = AsyncMock(
        return_value=MagicMock(
            id="contract-1",
            owner_party_id=None,
            manager_party_id=None,
            ownership_id="ownership-missing",
        )
    )
    mock_service.resolve_owner_party_scope_by_ownership_id_async = AsyncMock(
        return_value=None
    )
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_ledger_generate_authz(  # type: ignore[attr-defined]
            request=GenerateLedgerRequest(contract_id="contract-1"),
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["ownership_id"] == "ownership-missing"
    assert (
        result.resource_context["party_id"]
        == "__unscoped__:rent_contract_ledger:generate"
    )


@pytest.mark.asyncio
async def test_ledger_update_authz_should_authorize_with_parent_contract_scope() -> None:
    """台账更新鉴权应先解析台账归属合同，再按合同作用域鉴权。"""
    from src.api.v1.rent_contracts import ledger as module

    mock_service = MagicMock()
    mock_service.get_rent_ledger_by_id_async = AsyncMock(
        return_value=MagicMock(id="ledger-1", contract_id="contract-1")
    )
    mock_service.get_contract_with_details_async = AsyncMock(
        return_value=MagicMock(
            id="contract-1",
            owner_party_id="owner-party-1",
            manager_party_id="manager-party-1",
            ownership_id="ownership-1",
        )
    )
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_ledger_update_authz(  # type: ignore[attr-defined]
            ledger_id="ledger-1",
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_id == "contract-1"
    assert result.resource_context["ledger_id"] == "ledger-1"
    assert result.resource_context["contract_id"] == "contract-1"
    assert result.resource_context["owner_party_id"] == "owner-party-1"
    assert result.resource_context["manager_party_id"] == "manager-party-1"
    assert result.resource_context["ownership_id"] == "ownership-1"
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource_type"] == "rent_contract"
    assert kwargs["action"] == "update"
    assert kwargs["resource_id"] == "contract-1"
    assert kwargs["resource"]["contract_id"] == "contract-1"
    assert kwargs["resource"]["owner_party_id"] == "owner-party-1"


@pytest.mark.asyncio
async def test_ledger_read_authz_should_authorize_with_parent_contract_scope() -> None:
    """台账详情读取鉴权应先解析台账归属合同，再按合同作用域鉴权。"""
    from src.api.v1.rent_contracts import ledger as module

    mock_service = MagicMock()
    mock_service.get_rent_ledger_by_id_async = AsyncMock(
        return_value=MagicMock(id="ledger-1", contract_id="contract-1")
    )
    mock_service.get_contract_with_details_async = AsyncMock(
        return_value=MagicMock(
            id="contract-1",
            owner_party_id="owner-party-1",
            manager_party_id="manager-party-1",
            ownership_id="ownership-1",
        )
    )
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_ledger_read_authz(  # type: ignore[attr-defined]
            ledger_id="ledger-1",
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_id == "contract-1"
    assert result.resource_context["ledger_id"] == "ledger-1"
    assert result.resource_context["contract_id"] == "contract-1"
    assert result.resource_context["owner_party_id"] == "owner-party-1"
    assert result.resource_context["manager_party_id"] == "manager-party-1"
    assert result.resource_context["ownership_id"] == "ownership-1"
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource_type"] == "rent_contract"
    assert kwargs["action"] == "read"
    assert kwargs["resource_id"] == "contract-1"
    assert kwargs["resource"]["contract_id"] == "contract-1"
    assert kwargs["resource"]["owner_party_id"] == "owner-party-1"


@pytest.mark.asyncio
async def test_ledger_read_authz_should_resolve_owner_party_from_legacy_ownership() -> None:
    """台账读取鉴权在 party 列为空时应从 ownership 解析 owner_party。"""
    from src.api.v1.rent_contracts import ledger as module

    mock_service = MagicMock()
    mock_service.get_rent_ledger_by_id_async = AsyncMock(
        return_value=MagicMock(id="ledger-1", contract_id="contract-1")
    )
    mock_service.get_contract_with_details_async = AsyncMock(
        return_value=MagicMock(
            id="contract-1",
            owner_party_id=None,
            manager_party_id=None,
            ownership_id="ownership-1",
        )
    )
    mock_service.resolve_owner_party_scope_by_ownership_id_async = AsyncMock(
        return_value="owner-party-legacy-1"
    )
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_ledger_read_authz(  # type: ignore[attr-defined]
            ledger_id="ledger-1",
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["ownership_id"] == "ownership-1"
    assert result.resource_context["owner_party_id"] == "owner-party-legacy-1"
    assert result.resource_context["party_id"] == "owner-party-legacy-1"
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource"]["owner_party_id"] == "owner-party-legacy-1"
    assert kwargs["resource"]["party_id"] == "owner-party-legacy-1"


@pytest.mark.asyncio
async def test_ledger_read_authz_should_backfill_owner_scope_when_manager_party_exists() -> None:
    """台账读取鉴权在 owner 为空但 manager 存在时仍应桥接 legacy ownership。"""
    from src.api.v1.rent_contracts import ledger as module

    mock_service = MagicMock()
    mock_service.get_rent_ledger_by_id_async = AsyncMock(
        return_value=MagicMock(id="ledger-1", contract_id="contract-1")
    )
    mock_service.get_contract_with_details_async = AsyncMock(
        return_value=MagicMock(
            id="contract-1",
            owner_party_id=None,
            manager_party_id="manager-party-1",
            ownership_id="ownership-1",
        )
    )
    mock_service.resolve_owner_party_scope_by_ownership_id_async = AsyncMock(
        return_value="owner-party-legacy-1"
    )
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_ledger_read_authz(  # type: ignore[attr-defined]
            ledger_id="ledger-1",
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["manager_party_id"] == "manager-party-1"
    assert result.resource_context["owner_party_id"] == "owner-party-legacy-1"
    assert result.resource_context["party_id"] == "manager-party-1"
    mock_service.resolve_owner_party_scope_by_ownership_id_async.assert_awaited_once_with(
        db=ANY,
        ownership_id="ownership-1",
    )
