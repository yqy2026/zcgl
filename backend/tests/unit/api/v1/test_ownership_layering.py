"""分层约束测试：ownership 路由应委托服务层。"""

import re
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.assets import ownership as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_ownership_module_should_not_import_ownership_crud_directly() -> None:
    """ownership 路由模块不应直接导入 ownership CRUD。"""
    module_source = _read_module_source()
    assert "from ....crud.ownership import ownership" not in module_source
    assert "ownership_crud." not in module_source


def test_ownership_module_should_import_authz_dependency() -> None:
    """ownership 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_ownership_endpoints_should_use_require_authz() -> None:
    """ownership 关键端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def get_ownership_dropdown_options[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"ownership\"",
        r"async def create_ownership[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_ownership_create_authz\)",
        r"async def update_ownership[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"ownership\"[\s\S]*?resource_id=\"\{ownership_id\}\"",
        r"async def update_ownership_projects[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"ownership\"[\s\S]*?resource_id=\"\{ownership_id\}\"",
        r"async def delete_ownership[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"ownership\"[\s\S]*?resource_id=\"\{ownership_id\}\"",
        r"async def get_ownerships[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"ownership\"",
            r"async def search_ownerships[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"ownership\"",
        r"async def get_ownership_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"ownership\"",
        r"async def toggle_ownership_status[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"ownership\"[\s\S]*?resource_id=\"\{ownership_id\}\"",
        r"async def get_ownership_financial_summary[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"ownership\"[\s\S]*?resource_id=\"\{ownership_id\}\"[\s\S]*?deny_as_not_found=True",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_get_ownership_dropdown_options_should_delegate_service() -> None:
    """下拉接口应委托 ownership_service.get_ownership_dropdown_options。"""
    from src.api.v1.assets import ownership as module
    from src.api.v1.assets.ownership import get_ownership_dropdown_options

    item = {
        "id": "ownership-1",
        "name": "Ownership 1",
        "code": "OW2501001",
        "short_name": "O1",
        "is_active": True,
        "data_status": "正常",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "asset_count": 3,
        "project_count": 1,
    }
    mock_service = MagicMock()
    mock_service.get_ownership_dropdown_options = AsyncMock(return_value=[item])

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "ownership_service", mock_service)
        result = await get_ownership_dropdown_options(
            current_user=MagicMock(),
            db=MagicMock(),
            is_active=True,
        )

    assert len(result) == 1
    assert result[0].asset_count == 3
    mock_service.get_ownership_dropdown_options.assert_awaited_once()


@pytest.mark.asyncio
async def test_ownership_create_authz_should_include_organization_scope_context() -> None:
    """权属方 create 鉴权应注入组织/主体上下文，避免空资源上下文放行。"""
    from src.api.v1.assets import ownership as module

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
        result = await module._require_ownership_create_authz(  # type: ignore[attr-defined]
            current_user=MagicMock(id="user-1", default_organization_id="org-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["organization_id"] == "org-1"
    assert result.resource_context["party_id"] == "party-org-1"
    assert result.resource_context["owner_party_id"] == "party-org-1"
    assert result.resource_context["manager_party_id"] == "party-org-1"
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource_type"] == "ownership"
    assert kwargs["action"] == "create"
    assert kwargs["resource_id"] is None
    assert kwargs["resource"]["party_id"] == "party-org-1"


@pytest.mark.asyncio
async def test_ownership_create_authz_should_fallback_to_unscoped_sentinel() -> None:
    """权属方 create 缺少组织上下文时应写入 unscoped 哨兵。"""
    from src.api.v1.assets import ownership as module

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_ownership_create_authz(  # type: ignore[attr-defined]
            current_user=MagicMock(id="user-1", default_organization_id=None),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context == {
        "party_id": module._OWNERSHIP_CREATE_UNSCOPED_PARTY_ID,  # type: ignore[attr-defined]
        "owner_party_id": module._OWNERSHIP_CREATE_UNSCOPED_PARTY_ID,  # type: ignore[attr-defined]
        "manager_party_id": module._OWNERSHIP_CREATE_UNSCOPED_PARTY_ID,  # type: ignore[attr-defined]
    }
