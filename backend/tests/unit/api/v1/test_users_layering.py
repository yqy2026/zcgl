"""分层约束测试：users 路由应委托服务层。"""

import json
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
