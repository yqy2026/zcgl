"""分层约束测试：organization 路由应接入统一 ABAC 依赖。"""

import inspect
import re
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.auth import organization as module

    return inspect.getsource(module)


def test_organization_module_should_import_authz_dependency() -> None:
    """organization 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_organization_endpoints_should_use_require_authz() -> None:
    """organization 关键端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def get_organizations[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"organization\"",
        r"async def get_organization_tree[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"organization\"",
        r"async def search_organizations[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"organization\"",
        r"async def get_organization_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"organization\"",
        r"async def get_organization[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_id=\"\{org_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def get_organization_children[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_id=\"\{org_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def get_organization_path[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_id=\"\{org_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def get_organization_history[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_id=\"\{org_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def create_organization[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_organization_create_authz\)",
        r"async def update_organization[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_id=\"\{org_id\}\"",
        r"async def delete_organization[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_id=\"\{org_id\}\"",
        r"async def move_organization[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_id=\"\{org_id\}\"",
        r"async def batch_organization_operation[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"organization\"[\s\S]*?resource_context=_ORGANIZATION_BATCH_UPDATE_RESOURCE_CONTEXT",
        r"async def advanced_search_organizations[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"organization\"",
    ]

    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_organization_create_authz_should_include_parent_scope_context() -> None:
    from src.api.v1.auth import organization as module

    org_create = MagicMock(parent_id="org-parent-1")
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        monkeypatch.setattr(
            module,
            "_resolve_organization_party_id",
            AsyncMock(return_value="party-parent-1"),
        )
        result = await module._require_organization_create_authz(  # type: ignore[attr-defined]
            organization=org_create,
            current_user=MagicMock(id="user-1", default_organization_id="org-self-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["organization_id"] == "org-parent-1"
    assert result.resource_context["party_id"] == "party-parent-1"
    assert result.resource_context["owner_party_id"] == "party-parent-1"
    assert result.resource_context["manager_party_id"] == "party-parent-1"


@pytest.mark.asyncio
async def test_organization_create_authz_should_fallback_to_unscoped_sentinel() -> None:
    from src.api.v1.auth import organization as module

    org_create = MagicMock(parent_id=None)
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_organization_create_authz(  # type: ignore[attr-defined]
            organization=org_create,
            current_user=MagicMock(id="user-1", default_organization_id=None),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context == {
        "party_id": module._ORGANIZATION_CREATE_UNSCOPED_PARTY_ID,  # type: ignore[attr-defined]
        "owner_party_id": module._ORGANIZATION_CREATE_UNSCOPED_PARTY_ID,  # type: ignore[attr-defined]
        "manager_party_id": module._ORGANIZATION_CREATE_UNSCOPED_PARTY_ID,  # type: ignore[attr-defined]
    }


def test_organization_batch_update_unscoped_context_should_be_defined() -> None:
    from src.api.v1.auth import organization as module

    expected = "__unscoped__:organization:batch_update"
    assert module._ORGANIZATION_BATCH_UPDATE_UNSCOPED_PARTY_ID == expected  # type: ignore[attr-defined]
    assert module._ORGANIZATION_BATCH_UPDATE_RESOURCE_CONTEXT == {  # type: ignore[attr-defined]
        "party_id": expected,
        "owner_party_id": expected,
        "manager_party_id": expected,
    }
