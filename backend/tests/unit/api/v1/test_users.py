import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from src.core.exception_handler import (
    InternalServerError,
    InvalidRequestError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from src.exceptions import BusinessLogicError
from src.schemas.auth import (
    AdminPasswordResetRequest,
    PasswordChangeRequest,
    UserCreate,
    UserQueryParams,
    UserResponse,
    UserUpdate,
)

pytestmark = pytest.mark.api


ADMIN_ROLE_SUMMARY = {
    "primary_role_id": "role-admin-id",
    "primary_role_name": "admin",
    "roles": ["admin"],
    "role_ids": ["role-admin-id"],
    "is_admin": True,
}

USER_ROLE_SUMMARY = {
    "primary_role_id": "role-user-id",
    "primary_role_name": "asset_viewer",
    "roles": ["asset_viewer"],
    "role_ids": ["role-user-id"],
    "is_admin": False,
}


@dataclass
class FakeUser:
    id: str
    username: str
    email: str
    phone: str
    full_name: str
    is_active: bool = True
    is_locked: bool = False
    last_login_at: datetime | None = None
    default_organization_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    role_id: str | None = None
    roles: list[str] = field(default_factory=list)
    role_ids: list[str] = field(default_factory=list)
    is_admin: bool = False


def _parse_json_response(response):
    return json.loads(response.body.decode("utf-8"))


def _build_fake_user(user_id: str, username: str) -> FakeUser:
    suffix = user_id[-2:] if len(user_id) >= 2 else "00"
    return FakeUser(
        id=user_id,
        username=username,
        email=f"{username}@example.com",
        phone=f"1380000{suffix}000",
        full_name=f"{username} Name",
    )


def _build_current_user(*, user_id: str, username: str, is_admin: bool) -> UserResponse:
    return UserResponse(
        id=user_id,
        username=username,
        email=f"{username}@example.com",
        phone="13800000001" if is_admin else "13800000002",
        full_name=f"{username} User",
        role_id="role-admin-id" if is_admin else "role-user-id",
        roles=["admin"] if is_admin else ["asset_viewer"],
        role_ids=["role-admin-id"] if is_admin else ["role-user-id"],
        is_admin=is_admin,
        is_active=True,
        is_locked=False,
        default_organization_id=None,
        last_login_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def admin_user():
    return _build_current_user(user_id="admin-id", username="admin", is_admin=True)


@pytest.fixture
def regular_user():
    return _build_current_user(user_id="user-id", username="user", is_admin=False)


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {"user-agent": "unit-test-agent"}
    return request


class TestGetUsers:
    @patch("src.api.v1.auth.auth_modules.users.RBACService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_get_users_success(self, mock_user_crud_class, mock_rbac_class, mock_db, admin_user):
        from src.api.v1.auth.auth_modules.users import get_users

        users = [_build_fake_user("user-01", "user1"), _build_fake_user("user-02", "user2")]
        mock_user_crud = MagicMock()
        mock_user_crud.get_multi_with_filters_async = AsyncMock(return_value=(users, 2))
        mock_user_crud_class.return_value = mock_user_crud

        mock_rbac = MagicMock()
        mock_rbac.get_user_role_summary = AsyncMock(return_value=USER_ROLE_SUMMARY)
        mock_rbac_class.return_value = mock_rbac

        result = asyncio.run(
            get_users(
                params=UserQueryParams(page=1, page_size=10),
                db=mock_db,
                current_user=admin_user,
            )
        )

        payload = _parse_json_response(result)
        assert result.status_code == status.HTTP_200_OK
        assert payload["success"] is True
        assert payload["data"]["pagination"]["total"] == 2
        assert len(payload["data"]["items"]) == 2

    @patch("src.api.v1.auth.auth_modules.users.RBACService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_get_users_with_search(self, mock_user_crud_class, mock_rbac_class, mock_db, admin_user):
        from src.api.v1.auth.auth_modules.users import get_users

        mock_user_crud = MagicMock()
        mock_user_crud.get_multi_with_filters_async = AsyncMock(return_value=([], 0))
        mock_user_crud_class.return_value = mock_user_crud

        mock_rbac = MagicMock()
        mock_rbac.get_user_role_summary = AsyncMock(return_value=USER_ROLE_SUMMARY)
        mock_rbac_class.return_value = mock_rbac

        asyncio.run(
            get_users(
                params=UserQueryParams(page=2, page_size=5, search="admin"),
                db=mock_db,
                current_user=admin_user,
            )
        )

        mock_user_crud.get_multi_with_filters_async.assert_awaited_once_with(
            db=mock_db,
            skip=5,
            limit=5,
            search="admin",
            role_id=None,
            is_active=None,
            organization_id=None,
        )


class TestCreateUser:
    @patch("src.api.v1.auth.auth_modules.users.RBACService")
    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_create_user_success(self, mock_service_class, mock_rbac_class, mock_db, admin_user):
        from src.api.v1.auth.auth_modules.users import create_user

        user_data = UserCreate(
            username="new-user",
            email="new-user@example.com",
            phone="13800000123",
            full_name="New User",
            password="StrongPass123!",
            role_id="role-user-id",
        )
        created_user = _build_fake_user("new-user-id", "new-user")

        mock_service = MagicMock()
        mock_service.create_user = AsyncMock(return_value=created_user)
        mock_service_class.return_value = mock_service

        mock_rbac = MagicMock()
        mock_rbac.get_user_role_summary = AsyncMock(return_value=USER_ROLE_SUMMARY)
        mock_rbac_class.return_value = mock_rbac

        result = asyncio.run(create_user(user_data=user_data, db=mock_db, current_user=admin_user))

        assert result.username == "new-user"
        assert result.roles == ["asset_viewer"]
        mock_service.create_user.assert_awaited_once()

    @patch("src.api.v1.auth.auth_modules.users.RBACService")
    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_create_user_should_accept_role_ids(
        self, mock_service_class, mock_rbac_class, mock_db, admin_user
    ):
        from src.api.v1.auth.auth_modules.users import create_user

        user_data = UserCreate(
            username="multi-role-user",
            email="multi-role-user@example.com",
            phone="13800000125",
            full_name="Multi Role User",
            password="StrongPass123!",
            role_ids=["role-user-id", "role-reviewer-id"],
        )
        created_user = _build_fake_user("multi-role-user-id", "multi-role-user")

        mock_service = MagicMock()
        mock_service.create_user = AsyncMock(return_value=created_user)
        mock_service_class.return_value = mock_service

        mock_rbac = MagicMock()
        mock_rbac.get_user_role_summary = AsyncMock(
            return_value={
                **USER_ROLE_SUMMARY,
                "roles": ["asset_viewer", "reviewer"],
                "role_ids": ["role-user-id", "role-reviewer-id"],
            }
        )
        mock_rbac_class.return_value = mock_rbac

        asyncio.run(create_user(user_data=user_data, db=mock_db, current_user=admin_user))

        created_payload = mock_service.create_user.await_args.args[0]
        assert created_payload.role_ids == ["role-user-id", "role-reviewer-id"]

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_create_user_duplicate(self, mock_service_class, mock_db, admin_user):
        from src.api.v1.auth.auth_modules.users import create_user

        user_data = UserCreate(
            username="exists-user",
            email="exists-user@example.com",
            phone="13800000124",
            full_name="Exists User",
            password="StrongPass123!",
        )

        mock_service = MagicMock()
        mock_service.create_user = AsyncMock(side_effect=BusinessLogicError("用户名已存在"))
        mock_service_class.return_value = mock_service

        with pytest.raises(InvalidRequestError):
            asyncio.run(create_user(user_data=user_data, db=mock_db, current_user=admin_user))


class TestGetUser:
    @patch("src.api.v1.auth.auth_modules.users.RBACService")
    def test_get_user_forbidden(self, mock_rbac_class, mock_db, regular_user):
        from src.api.v1.auth.auth_modules.users import get_user

        mock_rbac = MagicMock()
        mock_rbac.is_admin = AsyncMock(return_value=False)
        mock_rbac_class.return_value = mock_rbac

        with pytest.raises(PermissionDeniedError):
            asyncio.run(get_user(user_id="another-user", db=mock_db, current_user=regular_user))

    @patch("src.api.v1.auth.auth_modules.users.RBACService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_get_user_success(self, mock_user_crud_class, mock_rbac_class, mock_db, admin_user):
        from src.api.v1.auth.auth_modules.users import get_user

        target_user = _build_fake_user("target-id", "target")
        mock_user_crud = MagicMock()
        mock_user_crud.get_async = AsyncMock(return_value=target_user)
        mock_user_crud_class.return_value = mock_user_crud

        mock_rbac = MagicMock()
        mock_rbac.is_admin = AsyncMock(return_value=True)
        mock_rbac.get_user_role_summary = AsyncMock(return_value=USER_ROLE_SUMMARY)
        mock_rbac_class.return_value = mock_rbac

        result = asyncio.run(get_user(user_id="target-id", db=mock_db, current_user=admin_user))

        assert result.id == "target-id"
        assert result.roles == ["asset_viewer"]


class TestUpdateUser:
    @patch("src.api.v1.auth.auth_modules.users.RBACService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_update_user_not_found(self, mock_user_crud_class, mock_rbac_class, mock_db, admin_user):
        from src.api.v1.auth.auth_modules.users import update_user

        mock_user_crud = MagicMock()
        mock_user_crud.get_async = AsyncMock(return_value=None)
        mock_user_crud_class.return_value = mock_user_crud

        mock_rbac = MagicMock()
        mock_rbac.is_admin = AsyncMock(return_value=True)
        mock_rbac_class.return_value = mock_rbac

        with pytest.raises(ResourceNotFoundError):
            asyncio.run(
                update_user(
                    user_id="missing-id",
                    user_data=UserUpdate(full_name="Updated"),
                    db=mock_db,
                    current_user=admin_user,
                )
            )

    @patch("src.api.v1.auth.auth_modules.users.RBACService")
    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_update_user_success(
        self,
        mock_user_crud_class,
        mock_service_class,
        mock_rbac_class,
        mock_db,
        admin_user,
    ):
        from src.api.v1.auth.auth_modules.users import update_user

        existing_user = _build_fake_user("target-id", "target")
        updated_user = _build_fake_user("target-id", "target")
        updated_user.full_name = "Updated User"

        mock_user_crud = MagicMock()
        mock_user_crud.get_async = AsyncMock(return_value=existing_user)
        mock_user_crud_class.return_value = mock_user_crud

        mock_service = MagicMock()
        mock_service.update_user = AsyncMock(return_value=updated_user)
        mock_service_class.return_value = mock_service

        mock_rbac = MagicMock()
        mock_rbac.is_admin = AsyncMock(return_value=True)
        mock_rbac.get_user_role_summary = AsyncMock(return_value=USER_ROLE_SUMMARY)
        mock_rbac_class.return_value = mock_rbac

        result = asyncio.run(
            update_user(
                user_id="target-id",
                user_data=UserUpdate(full_name="Updated User"),
                db=mock_db,
                current_user=admin_user,
            )
        )

        assert result.full_name == "Updated User"

    @patch("src.api.v1.auth.auth_modules.users.RBACService")
    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_update_user_should_accept_role_ids(
        self,
        mock_user_crud_class,
        mock_service_class,
        mock_rbac_class,
        mock_db,
        admin_user,
    ):
        from src.api.v1.auth.auth_modules.users import update_user

        existing_user = _build_fake_user("target-id", "target")
        updated_user = _build_fake_user("target-id", "target")

        mock_user_crud = MagicMock()
        mock_user_crud.get_async = AsyncMock(return_value=existing_user)
        mock_user_crud_class.return_value = mock_user_crud

        mock_service = MagicMock()
        mock_service.update_user = AsyncMock(return_value=updated_user)
        mock_service_class.return_value = mock_service

        mock_rbac = MagicMock()
        mock_rbac.is_admin = AsyncMock(return_value=True)
        mock_rbac.get_user_role_summary = AsyncMock(
            return_value={
                **USER_ROLE_SUMMARY,
                "roles": ["asset_viewer", "reviewer"],
                "role_ids": ["role-user-id", "role-reviewer-id"],
            }
        )
        mock_rbac_class.return_value = mock_rbac

        asyncio.run(
            update_user(
                user_id="target-id",
                user_data=UserUpdate(role_ids=["role-user-id", "role-reviewer-id"]),
                db=mock_db,
                current_user=admin_user,
            )
        )

        updated_payload = mock_service.update_user.await_args.args[1]
        assert updated_payload.role_ids == ["role-user-id", "role-reviewer-id"]


class TestChangePassword:
    @patch("src.api.v1.auth.auth_modules.users.RBACService")
    def test_change_password_forbidden(self, mock_rbac_class, mock_db, regular_user):
        from src.api.v1.auth.auth_modules.users import change_password

        mock_rbac = MagicMock()
        mock_rbac.is_admin = AsyncMock(return_value=False)
        mock_rbac_class.return_value = mock_rbac

        with pytest.raises(PermissionDeniedError):
            asyncio.run(
                change_password(
                    user_id="another-user",
                    password_data=PasswordChangeRequest(
                        current_password="OldPass123!",
                        new_password="NewPass123!",
                    ),
                    db=mock_db,
                    current_user=regular_user,
                )
            )

    @patch("src.api.v1.auth.auth_modules.users.RBACService")
    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_change_password_success(
        self,
        mock_user_crud_class,
        mock_service_class,
        mock_rbac_class,
        mock_db,
        admin_user,
    ):
        from src.api.v1.auth.auth_modules.users import change_password

        target_user = _build_fake_user("target-id", "target")
        mock_user_crud = MagicMock()
        mock_user_crud.get_async = AsyncMock(return_value=target_user)
        mock_user_crud_class.return_value = mock_user_crud

        mock_service = MagicMock()
        mock_service.change_password = AsyncMock(return_value=True)
        mock_service_class.return_value = mock_service

        mock_rbac = MagicMock()
        mock_rbac.is_admin = AsyncMock(return_value=True)
        mock_rbac_class.return_value = mock_rbac

        result = asyncio.run(
            change_password(
                user_id="target-id",
                password_data=PasswordChangeRequest(
                    current_password="OldPass123!",
                    new_password="NewPass123!",
                ),
                db=mock_db,
                current_user=admin_user,
            )
        )

        assert result["message"] == "密码修改成功"


class TestUserStateTransitions:
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_deactivate_user_success(self, mock_user_crud_class, mock_db, admin_user):
        from src.api.v1.auth.auth_modules.users import deactivate_user

        mock_user_crud = MagicMock()
        mock_user_crud.get_async = AsyncMock(return_value=object())
        mock_user_crud.delete_async = AsyncMock(return_value=True)
        mock_user_crud_class.return_value = mock_user_crud

        result = asyncio.run(deactivate_user(user_id="target-id", db=mock_db, current_user=admin_user))
        assert result["message"] == "用户已停用"

    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_deactivate_user_not_found(self, mock_user_crud_class, mock_db, admin_user):
        from src.api.v1.auth.auth_modules.users import deactivate_user

        mock_user_crud = MagicMock()
        mock_user_crud.get_async = AsyncMock(return_value=None)
        mock_user_crud_class.return_value = mock_user_crud

        with pytest.raises(ResourceNotFoundError):
            asyncio.run(deactivate_user(user_id="missing-id", db=mock_db, current_user=admin_user))

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_activate_user_success(self, mock_service_class, mock_db, admin_user):
        from src.api.v1.auth.auth_modules.users import activate_user

        mock_service = MagicMock()
        mock_service.activate_user = AsyncMock(return_value=True)
        mock_service_class.return_value = mock_service

        result = asyncio.run(activate_user(user_id="target-id", db=mock_db, current_user=admin_user))
        assert result["message"] == "用户已激活"

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_activate_user_not_found(self, mock_service_class, mock_db, admin_user):
        from src.api.v1.auth.auth_modules.users import activate_user

        mock_service = MagicMock()
        mock_service.activate_user = AsyncMock(return_value=False)
        mock_service_class.return_value = mock_service

        with pytest.raises(ResourceNotFoundError):
            asyncio.run(activate_user(user_id="missing-id", db=mock_db, current_user=admin_user))


class TestUserSecurityActions:
    @patch("src.api.v1.auth.auth_modules.users.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_lock_user_success(
        self, mock_service_class, mock_audit_crud_class, mock_db, admin_user, mock_request
    ):
        from src.api.v1.auth.auth_modules.users import lock_user

        target_user = _build_fake_user("target-id", "target")
        target_user.is_locked = True

        mock_service = MagicMock()
        mock_service.lock_user = AsyncMock(return_value=target_user)
        mock_service_class.return_value = mock_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            lock_user(
                user_id="target-id",
                request=mock_request,
                db=mock_db,
                current_user=admin_user,
            )
        )

        assert result["success"] is True
        assert "已锁定" in result["message"]
        mock_service.lock_user.assert_awaited_once_with("target-id")

    @patch("src.api.v1.auth.auth_modules.users.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_unlock_user_success(
        self, mock_service_class, mock_audit_crud_class, mock_db, admin_user, mock_request
    ):
        from src.api.v1.auth.auth_modules.users import unlock_user_account

        target_user = _build_fake_user("target-id", "target")
        target_user.is_locked = False

        mock_service = MagicMock()
        mock_service.unlock_user_with_result = AsyncMock(return_value=target_user)
        mock_service_class.return_value = mock_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            unlock_user_account(
                user_id="target-id",
                request=mock_request,
                db=mock_db,
                current_user=admin_user,
            )
        )

        assert result["success"] is True
        assert "已解锁" in result["message"]
        mock_service.unlock_user_with_result.assert_awaited_once_with("target-id")

    @patch("src.api.v1.auth.auth_modules.users.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_reset_password_success(
        self,
        mock_service_class,
        mock_audit_crud_class,
        mock_db,
        admin_user,
        mock_request,
    ):
        from src.api.v1.auth.auth_modules.users import reset_user_password

        target_user = _build_fake_user("target-id", "target")
        mock_service = MagicMock()
        mock_service.admin_reset_password = AsyncMock(return_value=target_user)
        mock_service_class.return_value = mock_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            reset_user_password(
                user_id="target-id",
                password_data=AdminPasswordResetRequest(new_password="StrongPass123!"),
                request=mock_request,
                db=mock_db,
                current_user=admin_user,
            )
        )

        assert result["success"] is True
        assert result["user_id"] == "target-id"
        mock_service.admin_reset_password.assert_awaited_once_with(
            user_id="target-id",
            new_password="StrongPass123!",
        )


class TestUserStatistics:
    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_get_user_statistics_success(self, mock_service_class, mock_db, admin_user):
        from src.api.v1.auth.auth_modules.users import get_user_statistics

        stats = {
            "total_users": 12,
            "active_users": 10,
            "locked_users": 1,
            "inactive_users": 2,
            "online_users": 0,
        }
        mock_service = MagicMock()
        mock_service.get_statistics = AsyncMock(return_value=stats)
        mock_service_class.return_value = mock_service

        result = asyncio.run(get_user_statistics(db=mock_db, current_user=admin_user))
        assert result["success"] is True
        assert result["data"]["total_users"] == 12

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_get_user_statistics_error(self, mock_service_class, mock_db, admin_user):
        from src.api.v1.auth.auth_modules.users import get_user_statistics

        mock_service = MagicMock()
        mock_service.get_statistics = AsyncMock(side_effect=Exception("db down"))
        mock_service_class.return_value = mock_service

        with pytest.raises(InternalServerError):
            asyncio.run(get_user_statistics(db=mock_db, current_user=admin_user))
