"""分层约束测试：rent_contract statistics 路由应委托服务层。"""

import re
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from src.schemas.rent_contract import RentStatisticsQuery

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.rent_contracts import statistics as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_statistics_module_should_not_import_rent_contract_crud_directly() -> None:
    """statistics 路由模块不应直接导入 rent_contract CRUD。"""
    module_source = _read_module_source()
    assert "from ....crud.rent_contract" not in module_source
    assert "rent_contract." not in module_source


def test_statistics_module_should_import_authz_dependency() -> None:
    """statistics 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_statistics_endpoints_should_use_require_authz() -> None:
    """统计端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def get_rent_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
        r"async def get_ownership_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
        r"async def get_asset_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
        r"async def get_monthly_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
        r"async def export_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_get_rent_statistics_should_delegate_service_query() -> None:
    """统计概览接口应委托 rent_contract_service.get_statistics_async。"""
    from src.api.v1.rent_contracts import statistics as module
    from src.api.v1.rent_contracts.statistics import get_rent_statistics

    expected = {"total_contracts": 1}
    mock_service = MagicMock()
    mock_service.get_statistics_async = AsyncMock(return_value=expected)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        result = await get_rent_statistics(
            db=MagicMock(),
            current_user=MagicMock(),
            start_date=None,
            end_date=None,
            owner_party_ids=None,
            ownership_ids=None,
            asset_ids=None,
            contract_status=None,
        )

    assert result == expected
    call_kwargs = mock_service.get_statistics_async.await_args.kwargs
    assert call_kwargs["db"] is not None
    assert isinstance(call_kwargs["query_params"], RentStatisticsQuery)
    assert call_kwargs["query_params"].owner_party_ids is None
    assert call_kwargs["query_params"].manager_party_ids is None


@pytest.mark.asyncio
async def test_get_ownership_statistics_should_delegate_service_query() -> None:
    """权属方统计接口应委托 rent_contract_service.get_ownership_statistics_async。"""
    from src.api.v1.rent_contracts import statistics as module
    from src.api.v1.rent_contracts.statistics import get_ownership_statistics

    expected = [MagicMock()]
    mock_service = MagicMock()
    mock_service.get_ownership_statistics_async = AsyncMock(return_value=expected)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        result = await get_ownership_statistics(
            db=MagicMock(),
            current_user=MagicMock(),
            start_date=None,
            end_date=None,
            owner_party_ids=["party-1"],
            ownership_ids=None,
        )

    assert result == expected
    mock_service.get_ownership_statistics_async.assert_awaited_once_with(
        db=ANY,
        start_date=None,
        end_date=None,
        owner_party_ids=["party-1"],
        manager_party_ids=None,
        ownership_ids=None,
    )


@pytest.mark.asyncio
async def test_get_rent_statistics_should_apply_authz_scope_filters() -> None:
    """统计概览应优先透传鉴权上下文 owner/manager 多主体作用域。"""
    from src.api.v1.rent_contracts import statistics as module
    from src.api.v1.rent_contracts.statistics import get_rent_statistics

    expected = {"total_contracts": 1}
    mock_service = MagicMock()
    mock_service.get_statistics_async = AsyncMock(return_value=expected)

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
        await get_rent_statistics(
            db=MagicMock(),
            current_user=MagicMock(),
            authz_ctx=authz_ctx,
            start_date=None,
            end_date=None,
            owner_party_ids=None,
            ownership_ids=None,
            asset_ids=None,
            contract_status=None,
        )

    call_kwargs = mock_service.get_statistics_async.await_args.kwargs
    assert call_kwargs["query_params"].owner_party_ids == [
        "owner-party-1",
        "owner-party-2",
    ]
    assert call_kwargs["query_params"].manager_party_ids == [
        "manager-party-1",
        "manager-party-2",
    ]


@pytest.mark.asyncio
async def test_get_rent_statistics_should_skip_scope_filters_for_admin_bypass() -> None:
    """管理员 bypass 决策下统计查询不应套用 resource_context scope hint。"""
    from src.api.v1.rent_contracts import statistics as module
    from src.api.v1.rent_contracts.statistics import get_rent_statistics

    expected = {"total_contracts": 1}
    mock_service = MagicMock()
    mock_service.get_statistics_async = AsyncMock(return_value=expected)

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
        await get_rent_statistics(
            db=MagicMock(),
            current_user=MagicMock(),
            authz_ctx=authz_ctx,
            start_date=None,
            end_date=None,
            owner_party_ids=None,
            ownership_ids=None,
            asset_ids=None,
            contract_status=None,
        )

    call_kwargs = mock_service.get_statistics_async.await_args.kwargs
    assert call_kwargs["query_params"].owner_party_ids is None
    assert call_kwargs["query_params"].manager_party_ids is None


@pytest.mark.asyncio
async def test_get_rent_statistics_should_allow_owner_filter_within_scoped_owner_collection() -> None:
    """请求 owner 过滤命中鉴权 owner 列表时应允许并按请求收窄。"""
    from src.api.v1.rent_contracts import statistics as module
    from src.api.v1.rent_contracts.statistics import get_rent_statistics

    expected = {"total_contracts": 1}
    mock_service = MagicMock()
    mock_service.get_statistics_async = AsyncMock(return_value=expected)

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
        await get_rent_statistics(
            db=MagicMock(),
            current_user=MagicMock(),
            authz_ctx=authz_ctx,
            start_date=None,
            end_date=None,
            owner_party_ids=["owner-party-2"],
            ownership_ids=None,
            asset_ids=None,
            contract_status=None,
        )

    call_kwargs = mock_service.get_statistics_async.await_args.kwargs
    assert call_kwargs["query_params"].owner_party_ids == ["owner-party-2"]
    assert call_kwargs["query_params"].manager_party_ids is None


@pytest.mark.asyncio
async def test_get_rent_statistics_should_forbid_owner_override_with_manager_only_scope() -> None:
    """仅 manager 作用域时不允许注入 owner_party_ids。"""
    from src.api.v1.rent_contracts import statistics as module
    from src.api.v1.rent_contracts.statistics import get_rent_statistics

    mock_service = MagicMock()
    mock_service.get_statistics_async = AsyncMock(return_value={"total_contracts": 1})

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
            await get_rent_statistics(
                db=MagicMock(),
                current_user=MagicMock(),
                authz_ctx=authz_ctx,
                start_date=None,
                end_date=None,
                owner_party_ids=["owner-party-2"],
                ownership_ids=None,
                asset_ids=None,
                contract_status=None,
            )

    assert getattr(exc_info.value, "status_code", None) == 403
    mock_service.get_statistics_async.assert_not_called()
