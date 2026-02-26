"""分层约束测试：rent_contract excel_ops 路由应委托服务层。"""

import re
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.rent_contracts import excel_ops as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_excel_ops_module_should_not_import_rent_contract_crud_directly() -> None:
    """excel_ops 路由模块不应直接导入 rent_contract CRUD。"""
    module_source = _read_module_source()
    assert "from ....crud.rent_contract" not in module_source
    assert "rent_contract." not in module_source


def test_excel_ops_module_should_import_authz_dependency() -> None:
    """excel_ops 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_excel_ops_endpoints_should_use_require_authz() -> None:
    """Excel 相关端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def download_excel_template[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
        r"async def import_contracts_from_excel[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_contract_bulk_create_authz\)",
        r"async def export_contracts_to_excel[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_export_contracts_to_excel_should_delegate_service() -> None:
    """Excel 导出接口应委托 rent_contract_excel_service.export_contracts_to_excel。"""
    from src.api.v1.rent_contracts import excel_ops as module
    from src.api.v1.rent_contracts.excel_ops import export_contracts_to_excel

    mock_service = MagicMock()
    mock_service.export_contracts_to_excel = AsyncMock(
        return_value={
            "success": True,
            "file_path": "/tmp/contracts.xlsx",
            "file_name": "contracts.xlsx",
        }
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "EXCEL_SERVICE_AVAILABLE", True)
        monkeypatch.setattr(module, "rent_contract_excel_service", mock_service)
        result = await export_contracts_to_excel(
            contract_ids=None,
            current_user=MagicMock(),
            db=MagicMock(),
            should_include_terms=True,
            should_include_ledger=True,
            start_date=None,
            end_date=None,
        )

    assert result is not None
    mock_service.export_contracts_to_excel.assert_awaited_once_with(
        db=ANY,
        contract_ids=None,
        include_terms=True,
        include_ledger=True,
        start_date=None,
        end_date=None,
        owner_party_id=None,
        manager_party_id=None,
        owner_party_ids=None,
        manager_party_ids=None,
    )


@pytest.mark.asyncio
async def test_export_contracts_to_excel_should_apply_authz_scope_filters() -> None:
    """Excel 导出接口应把鉴权作用域透传到导出查询。"""
    from src.api.v1.rent_contracts import excel_ops as module
    from src.api.v1.rent_contracts.excel_ops import export_contracts_to_excel
    from src.middleware.auth import AuthzContext

    mock_service = MagicMock()
    mock_service.export_contracts_to_excel = AsyncMock(
        return_value={
            "success": True,
            "file_path": "/tmp/contracts.xlsx",
            "file_name": "contracts.xlsx",
        }
    )
    authz_ctx = AuthzContext(
        current_user=MagicMock(id="user-1"),
        action="read",
        resource_type="rent_contract",
        resource_id=None,
        resource_context={
            "owner_party_ids": ["owner-1", "owner-2"],
            "manager_party_ids": ["manager-1", "manager-2"],
            "owner_party_id": "owner-1",
            "manager_party_id": "manager-1",
        },
        allowed=True,
        reason_code="allow",
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "EXCEL_SERVICE_AVAILABLE", True)
        monkeypatch.setattr(module, "rent_contract_excel_service", mock_service)
        await export_contracts_to_excel(
            contract_ids=["contract-1"],
            current_user=MagicMock(),
            authz_ctx=authz_ctx,
            db=MagicMock(),
            should_include_terms=False,
            should_include_ledger=False,
            start_date=None,
            end_date=None,
        )

    mock_service.export_contracts_to_excel.assert_awaited_once_with(
        db=ANY,
        contract_ids=["contract-1"],
        include_terms=False,
        include_ledger=False,
        start_date=None,
        end_date=None,
        owner_party_id="owner-1",
        manager_party_id="manager-1",
        owner_party_ids=["owner-1", "owner-2"],
        manager_party_ids=["manager-1", "manager-2"],
    )


@pytest.mark.asyncio
async def test_excel_import_create_authz_should_include_organization_scope_context() -> None:
    """Excel 导入 create 鉴权应注入组织/主体上下文，避免空资源上下文放行。"""
    from src.api.v1.rent_contracts import excel_ops as module

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        monkeypatch.setattr(
            module,
            "_resolve_organization_party_id",
            AsyncMock(return_value="party-org-1"),
        )
        result = await module._require_contract_bulk_create_authz(  # type: ignore[attr-defined]
            current_user=MagicMock(id="user-1", default_organization_id="org-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["organization_id"] == "org-1"
    assert result.resource_context["party_id"] == "party-org-1"
    assert result.resource_context["owner_party_id"] == "party-org-1"
    assert result.resource_context["manager_party_id"] == "party-org-1"
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource_type"] == "rent_contract"
    assert kwargs["action"] == "create"
    assert kwargs["resource_id"] is None
    assert kwargs["resource"]["party_id"] == "party-org-1"


@pytest.mark.asyncio
async def test_excel_import_create_authz_should_fallback_to_unscoped_sentinel() -> None:
    """Excel 导入 create 缺少组织上下文时应写入 unscoped 哨兵。"""
    from src.api.v1.rent_contracts import excel_ops as module

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_contract_bulk_create_authz(  # type: ignore[attr-defined]
            current_user=MagicMock(id="user-1", default_organization_id=None),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context == {
        "party_id": module._CONTRACT_BULK_CREATE_UNSCOPED_PARTY_ID,  # type: ignore[attr-defined]
        "owner_party_id": module._CONTRACT_BULK_CREATE_UNSCOPED_PARTY_ID,  # type: ignore[attr-defined]
        "manager_party_id": module._CONTRACT_BULK_CREATE_UNSCOPED_PARTY_ID,  # type: ignore[attr-defined]
    }
