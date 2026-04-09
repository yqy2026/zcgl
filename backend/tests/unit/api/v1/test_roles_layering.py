"""分层约束测试：roles 路由应接入统一 ABAC 依赖。"""

import inspect
import re
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.auth import roles as module

    return inspect.getsource(module)


def test_roles_module_should_import_authz_dependency() -> None:
    """roles 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source
    assert "require_any_role" in module_source


def test_roles_endpoints_should_use_require_authz() -> None:
    """roles 关键端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def get_roles[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"role\"",
        r"async def create_role[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"role\"",
        r"async def check_user_permission[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"role\"",
        r"async def assign_role_to_user[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"user\"[\s\S]*?resource_id=_resolve_user_assignment_resource_id",
        r"async def _require_user_read_or_self_authz[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_id=\"\{user_id\}\"",
        r"async def get_user_roles[\s\S]*?Depends\(_require_user_read_or_self_authz\)",
        r"async def revoke_user_role[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_id=\"\{user_id\}\"",
        r"async def get_user_permissions_summary[\s\S]*?Depends\(_require_user_read_or_self_authz\)",
        r"async def create_permission_grant[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"role\"[\s\S]*?resource_context=_resolve_role_create_resource_context",
        r"async def get_permission_grants[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"role\"",
        r"async def get_permission_grant[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_id=\"\{grant_id\}\"",
        r"async def update_permission_grant[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_id=\"\{grant_id\}\"",
        r"async def revoke_permission_grant[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_id=\"\{grant_id\}\"",
        r"async def get_role[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_id=\"\{role_id\}\"",
        r"async def update_role[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_id=\"\{role_id\}\"",
        r"async def delete_role[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_id=\"\{role_id\}\"",
        r"async def get_all_permissions[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"role\"",
        r"async def set_role_permissions[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_id=\"\{role_id\}\"",
        r"async def get_role_users[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_id=\"\{role_id\}\"",
        r"async def get_role_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"role\"",
    ]

    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_roles_user_read_authz_should_allow_self_without_asset_policy() -> None:
    from src.api.v1.auth.roles import _require_user_read_or_self_authz

    current_user = MagicMock(id="user-1")
    request = MagicMock(path_params={"user_id": "user-1"})

    result = await _require_user_read_or_self_authz(
        request=request,
        current_user=current_user,
        db=MagicMock(),
    )

    assert result.allowed is True
    assert result.action == "read"
    assert result.resource_type == "user"
    assert result.resource_id == "user-1"
    assert result.reason_code == "self_access_bypass"


@pytest.mark.asyncio
async def test_roles_user_read_authz_should_delegate_for_non_self_requests() -> None:
    from src.api.v1.auth import roles as roles_module

    delegated = MagicMock()
    delegated.allowed = True
    delegated.resource_type = "user"
    delegated.resource_id = "target-user"
    delegated.reason_code = "delegated"

    checker = AsyncMock(return_value=delegated)

    with pytest.MonkeyPatch.context() as monkeypatch:
        mock_require_authz = MagicMock(return_value=checker)
        monkeypatch.setattr(roles_module, "require_authz", mock_require_authz)
        result = await roles_module._require_user_read_or_self_authz(
            request=MagicMock(path_params={"user_id": "target-user"}),
            current_user=MagicMock(id="current-user"),
            db=MagicMock(),
        )
        mock_require_authz.assert_called_once_with(
            action="read",
            resource_type="user",
            resource_id="{user_id}",
        )
    checker.assert_awaited_once()
    assert result is delegated


@pytest.mark.asyncio
async def test_create_role_authz_context_should_prefer_party_id() -> None:
    from src.api.v1.auth.roles import _resolve_role_create_resource_context

    request = MagicMock()
    request.json = AsyncMock(
        return_value={
            "party_id": "party-001",
            "organization_id": "org-001",
        }
    )

    result = await _resolve_role_create_resource_context(request)

    assert result == {
        "organization_id": "org-001",
        "party_id": "party-001",
        "owner_party_id": "party-001",
        "manager_party_id": "party-001",
    }


@pytest.mark.asyncio
async def test_create_role_authz_context_should_fallback_to_unscoped_sentinel() -> None:
    from src.api.v1.auth.roles import (
        _ROLE_CREATE_UNSCOPED_PARTY_ID,
        _resolve_role_create_resource_context,
    )

    request = MagicMock()
    request.json = AsyncMock(return_value={})

    result = await _resolve_role_create_resource_context(request)

    assert result == {
        "party_id": _ROLE_CREATE_UNSCOPED_PARTY_ID,
        "owner_party_id": _ROLE_CREATE_UNSCOPED_PARTY_ID,
        "manager_party_id": _ROLE_CREATE_UNSCOPED_PARTY_ID,
    }


@pytest.mark.asyncio
async def test_assign_role_authz_resource_id_should_parse_user_id_from_payload() -> None:
    from src.api.v1.auth.roles import _resolve_user_assignment_resource_id

    request = MagicMock()
    request.json = AsyncMock(return_value={"user_id": "user-001"})

    assert await _resolve_user_assignment_resource_id(request) == "user-001"


@pytest.mark.asyncio
async def test_assign_role_authz_resource_id_should_return_none_on_invalid_payload() -> None:
    from src.api.v1.auth.roles import _resolve_user_assignment_resource_id

    request = MagicMock()
    request.json = AsyncMock(return_value=[])

    assert await _resolve_user_assignment_resource_id(request) is None
