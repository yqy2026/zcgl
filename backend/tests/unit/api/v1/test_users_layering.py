"""分层约束测试：users 路由应委托服务层。"""

import json
import re
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_users_module_should_not_import_auth_crud_directly() -> None:
    """users 路由模块不应直接导入 crud.auth。"""
    from src.api.v1.auth.auth_modules import users as users_module

    module_source = Path(users_module.__file__).read_text(encoding="utf-8")
    assert "from .....crud.auth" not in module_source
    assert "user_crud." not in module_source
    assert "audit_crud." not in module_source


def test_users_module_should_not_commit_in_route_layer() -> None:
    """users 路由模块不应直接执行事务控制。"""
    from src.api.v1.auth.auth_modules import users as users_module

    module_source = Path(users_module.__file__).read_text(encoding="utf-8")
    assert "await db.commit()" not in module_source
    assert "await db.rollback()" not in module_source


def test_users_module_should_import_authz_dependency() -> None:
    """users 路由应引入统一 ABAC 依赖。"""
    from src.api.v1.auth.auth_modules import users as users_module

    module_source = Path(users_module.__file__).read_text(encoding="utf-8")
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source
    assert "require_any_role" in module_source


def test_users_endpoints_should_use_require_authz() -> None:
    """users 关键端点应接入 require_authz。"""
    from src.api.v1.auth.auth_modules import users as users_module

    module_source = Path(users_module.__file__).read_text(encoding="utf-8")
    expected_patterns = [
        r"async def get_users[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"user\"",
        r"async def create_user[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"user\"",
        r"async def get_user[\s\S]*?Depends\(_require_user_read_or_self_authz\)",
        r"async def _require_user_read_or_self_authz[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"user\"[\s\S]*?resource_id=\"\{user_id\}\"",
        r"async def update_user[\s\S]*?Depends\(_require_user_update_or_self_authz\)",
        r"async def _require_user_update_or_self_authz[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"user\"[\s\S]*?resource_id=\"\{user_id\}\"",
        r"async def deactivate_user[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"user\"[\s\S]*?resource_id=\"\{user_id\}\"",
        r"async def delete_user[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"user\"[\s\S]*?resource_id=\"\{user_id\}\"",
        r"async def activate_user[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"user\"[\s\S]*?resource_id=\"\{user_id\}\"",
        r"async def lock_user[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"user\"[\s\S]*?resource_id=\"\{user_id\}\"",
        r"async def unlock_user_account[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"user\"[\s\S]*?resource_id=\"\{user_id\}\"",
        r"async def reset_user_password[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"user\"[\s\S]*?resource_id=\"\{user_id\}\"",
        r"async def get_user_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"user\"",
    ]

    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_change_password_should_not_require_asset_authz() -> None:
    """自助修改密码不应依赖资产 ABAC 权限。"""
    from src.api.v1.auth.auth_modules import users as users_module

    module_source = Path(users_module.__file__).read_text(encoding="utf-8")
    match = re.search(
        r"async def change_password[\s\S]*?\n\nasync def _deactivate_user",
        module_source,
    )
    assert match is not None
    assert "require_authz(" not in match.group(0)


@pytest.mark.asyncio
async def test_get_users_should_delegate_repository_call() -> None:
    """用户列表接口应委托 UserCRUD 适配器。"""
    from src.api.v1.auth.auth_modules import users as users_module
    from src.api.v1.auth.auth_modules.users import get_users

    user_repo = MagicMock()
    user_repo.get_multi_with_filters_async = AsyncMock(
        return_value=([MagicMock(id="user-1")], 1)
    )

    params = MagicMock(
        page=1,
        page_size=10,
        search="user",
        role_id=None,
        is_active=True,
        organization_id=None,
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(users_module, "UserCRUD", MagicMock(return_value=user_repo))
        monkeypatch.setattr(
            users_module,
            "_build_user_response",
            AsyncMock(return_value={"id": "user-1"}),
        )
        response = await get_users(
            params=params,
            db=MagicMock(),
            current_user=MagicMock(id="admin-id"),
        )

    payload = json.loads(response.body)
    assert payload["data"]["pagination"]["total"] == 1
    user_repo.get_multi_with_filters_async.assert_awaited_once_with(
        db=ANY,
        skip=0,
        limit=10,
        search="user",
        role_id=None,
        is_active=True,
        organization_id=None,
    )


@pytest.mark.asyncio
async def test_deactivate_user_should_delegate_repository_delete() -> None:
    """停用用户接口应委托 UserCRUD.delete_async。"""
    from src.api.v1.auth.auth_modules import users as users_module
    from src.api.v1.auth.auth_modules.users import deactivate_user

    user_repo = MagicMock()
    user_repo.get_async = AsyncMock(return_value=MagicMock(id="user-1"))
    user_repo.delete_async = AsyncMock(return_value=True)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(users_module, "UserCRUD", MagicMock(return_value=user_repo))
        result = await deactivate_user(
            user_id="user-1",
            db=MagicMock(),
            current_user=MagicMock(id="admin-id"),
        )

    assert result["message"] == "用户已停用"
    user_repo.get_async.assert_awaited_once()
    user_repo.delete_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_lock_user_should_delegate_user_service_lock_method() -> None:
    """锁定用户接口应委托 AsyncUserManagementService.lock_user。"""
    from src.api.v1.auth.auth_modules import users as users_module
    from src.api.v1.auth.auth_modules.users import lock_user

    user_service = MagicMock()
    user_service.lock_user = AsyncMock(return_value=MagicMock(username="tester"))
    audit_logger = MagicMock()
    audit_logger.create_async = AsyncMock(return_value=None)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            users_module,
            "AsyncUserManagementService",
            MagicMock(return_value=user_service),
        )
        monkeypatch.setattr(
            users_module,
            "AuditLogCRUD",
            MagicMock(return_value=audit_logger),
        )
        result = await lock_user(
            user_id="user-1",
            request=MagicMock(headers={"user-agent": "ua"}, client=MagicMock(host="127.0.0.1")),
            db=MagicMock(),
            current_user=MagicMock(id="admin-id"),
        )

    assert result["success"] is True
    user_service.lock_user.assert_awaited_once_with("user-1")
    audit_logger.create_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_reset_password_should_delegate_user_service_admin_reset() -> None:
    """管理员重置密码接口应委托 AsyncUserManagementService.admin_reset_password。"""
    from src.api.v1.auth.auth_modules import users as users_module
    from src.api.v1.auth.auth_modules.users import reset_user_password
    from src.schemas.auth import AdminPasswordResetRequest

    user_service = MagicMock()
    user_service.admin_reset_password = AsyncMock(return_value=MagicMock(username="tester"))
    audit_logger = MagicMock()
    audit_logger.create_async = AsyncMock(return_value=None)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            users_module,
            "AsyncUserManagementService",
            MagicMock(return_value=user_service),
        )
        monkeypatch.setattr(
            users_module,
            "AuditLogCRUD",
            MagicMock(return_value=audit_logger),
        )
        result = await reset_user_password(
            user_id="user-1",
            password_data=AdminPasswordResetRequest(
                new_password="NewSecurePass123!",
                reason="ops",
            ),
            request=MagicMock(headers={"user-agent": "ua"}, client=MagicMock(host="127.0.0.1")),
            db=MagicMock(),
            current_user=MagicMock(id="admin-id"),
        )

    assert result["success"] is True
    user_service.admin_reset_password.assert_awaited_once_with(
        user_id="user-1",
        new_password="NewSecurePass123!",
    )
    audit_logger.create_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_authz_should_allow_self_without_user_policy() -> None:
    from src.api.v1.auth.auth_modules.users import _require_user_read_or_self_authz

    current_user = MagicMock(id="user-1")
    request = MagicMock(path_params={"user_id": "user-1"})

    result = await _require_user_read_or_self_authz(
        request=request,
        current_user=current_user,
        db=MagicMock(),
    )

    assert result.allowed is True
    assert result.resource_type == "user"
    assert result.resource_id == "user-1"
    assert result.reason_code == "self_access_bypass"


@pytest.mark.asyncio
async def test_create_user_authz_context_should_include_party_scope_fields() -> None:
    from src.api.v1.auth.auth_modules.users import _resolve_user_create_resource_context

    request = MagicMock()
    request.json = AsyncMock(return_value={"default_organization_id": "org-001"})

    result = await _resolve_user_create_resource_context(request)

    assert result == {
        "organization_id": "org-001",
        "party_id": "org-001",
        "owner_party_id": "org-001",
        "manager_party_id": "org-001",
    }


@pytest.mark.asyncio
async def test_create_user_authz_context_should_fallback_to_unscoped_sentinel() -> None:
    from src.api.v1.auth.auth_modules.users import (
        _USER_CREATE_UNSCOPED_PARTY_ID,
        _resolve_user_create_resource_context,
    )

    request = MagicMock()
    request.json = AsyncMock(return_value={})

    result = await _resolve_user_create_resource_context(request)

    assert result == {
        "party_id": _USER_CREATE_UNSCOPED_PARTY_ID,
        "owner_party_id": _USER_CREATE_UNSCOPED_PARTY_ID,
        "manager_party_id": _USER_CREATE_UNSCOPED_PARTY_ID,
    }


@pytest.mark.asyncio
async def test_get_user_authz_should_delegate_for_non_self_requests() -> None:
    from src.api.v1.auth.auth_modules import users as users_module

    delegated = MagicMock()
    delegated.allowed = True
    delegated.resource_type = "user"
    delegated.resource_id = "target-user"
    delegated.reason_code = "delegated"

    checker = AsyncMock(return_value=delegated)

    with pytest.MonkeyPatch.context() as monkeypatch:
        mock_require_authz = MagicMock(return_value=checker)
        monkeypatch.setattr(users_module, "require_authz", mock_require_authz)
        result = await users_module._require_user_read_or_self_authz(
            request=MagicMock(path_params={"user_id": "target-user"}),
            current_user=MagicMock(id="current-user"),
            db=MagicMock(),
        )
        mock_require_authz.assert_called_once_with(
            action="read",
            resource_type="user",
            resource_id="{user_id}",
            deny_as_not_found=True,
        )
    checker.assert_awaited_once()
    assert result is delegated


@pytest.mark.asyncio
async def test_update_user_authz_should_allow_self_without_user_policy() -> None:
    from src.api.v1.auth.auth_modules.users import _require_user_update_or_self_authz

    current_user = MagicMock(id="user-1")
    request = MagicMock(path_params={"user_id": "user-1"})

    result = await _require_user_update_or_self_authz(
        request=request,
        current_user=current_user,
        db=MagicMock(),
    )

    assert result.allowed is True
    assert result.action == "update"
    assert result.resource_type == "user"
    assert result.resource_id == "user-1"
    assert result.reason_code == "self_access_bypass"


@pytest.mark.asyncio
async def test_update_user_authz_should_delegate_for_non_self_requests() -> None:
    from src.api.v1.auth.auth_modules import users as users_module

    delegated = MagicMock()
    delegated.allowed = True
    delegated.resource_type = "user"
    delegated.resource_id = "target-user"
    delegated.reason_code = "delegated"

    checker = AsyncMock(return_value=delegated)

    with pytest.MonkeyPatch.context() as monkeypatch:
        mock_require_authz = MagicMock(return_value=checker)
        monkeypatch.setattr(users_module, "require_authz", mock_require_authz)
        result = await users_module._require_user_update_or_self_authz(
            request=MagicMock(path_params={"user_id": "target-user"}),
            current_user=MagicMock(id="current-user"),
            db=MagicMock(),
        )
        mock_require_authz.assert_called_once_with(
            action="update",
            resource_type="user",
            resource_id="{user_id}",
        )
    checker.assert_awaited_once()
    assert result is delegated
