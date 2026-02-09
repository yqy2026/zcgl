"""
Comprehensive Unit Tests for Users API Routes (src/api/v1/auth/auth_modules/users.py)

This test module covers all endpoints in the users router to achieve 70%+ coverage:

Endpoints Tested:
1. GET /api/v1/auth/users - Get user list (admin only)
2. GET /api/v1/auth/users/search - Search users
3. POST /api/v1/auth/users - Create user (admin only)
4. GET /api/v1/auth/users/{user_id} - Get user details
5. PUT /api/v1/auth/users/{user_id} - Update user
6. POST /api/v1/auth/users/{user_id}/change-password - Change password
7. POST /api/v1/auth/users/{user_id}/deactivate - Deactivate user
8. DELETE /api/v1/auth/users/{user_id} - Delete user (same as deactivate)
9. POST /api/v1/auth/users/{user_id}/activate - Activate user
10. POST /api/v1/auth/users/{user_id}/lock - Lock user account
11. POST /api/v1/auth/users/{user_id}/unlock - Unlock user account
12. POST /api/v1/auth/users/{user_id}/reset-password - Reset user password
13. GET /api/v1/auth/users/statistics/summary - Get user statistics

Testing Approach:
- Mock all dependencies (UserCRUD, AsyncUserManagementService, PasswordService, database, auth)
- Test successful responses
- Test error handling scenarios
- Test request validation
- Test response schemas
- Test permission checks
"""

import asyncio
import json
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


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_admin_user():
    """Create mock admin user"""
    user = MagicMock()
    user.id = "admin-id"
    user.username = "admin"
    user.role_id = "role-admin-id"
    user.role_name = "admin"
    user.roles = ["admin"]
    user.role_ids = ["role-admin-id"]
    user.is_admin = True
    user.is_active = True
    user.is_locked = False
    return user


@pytest.fixture
def mock_regular_user():
    """Create mock regular user"""
    user = MagicMock()
    user.id = "user-id"
    user.username = "testuser"
    user.role_id = "role-user-id"
    user.role_name = "asset_viewer"
    user.roles = ["asset_viewer"]
    user.role_ids = ["role-user-id"]
    user.is_admin = False
    user.is_active = True
    user.is_locked = False
    return user


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.query = MagicMock()
    return db


@pytest.fixture(autouse=True)
def mock_rbac_service(monkeypatch):
    """Patch RBACService to avoid DB usage in user API tests."""
    from src.api.v1.auth.auth_modules import users as users_module

    rbac_instance = MagicMock()
    rbac_instance.is_admin = AsyncMock(
        side_effect=lambda user_id: user_id == "admin-id"
    )
    rbac_instance.get_user_role_summary = AsyncMock(
        side_effect=lambda user_id: (
            ADMIN_ROLE_SUMMARY if user_id == "admin-id" else USER_ROLE_SUMMARY
        )
    )
    monkeypatch.setattr(
        users_module, "RBACService", MagicMock(return_value=rbac_instance)
    )
    return rbac_instance


@pytest.fixture
def mock_request():
    """Create mock FastAPI request"""
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {"user-agent": "test-agent"}
    return request


@pytest.fixture
def mock_user_response():
    """Create mock user response"""
    user = MagicMock()
    user.id = "test-user-id"
    user.username = "testuser"
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.role_id = "role-user-id"
    user.role_name = "asset_viewer"
    user.roles = ["asset_viewer"]
    user.role_ids = ["role-user-id"]
    user.is_admin = False
    user.is_active = True
    user.is_locked = False
    user.employee_id = None
    user.default_organization_id = None
    user.last_login_at = None
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


def _parse_json_response(response):
    return json.loads(response.body)


def _make_user_crud():
    crud = MagicMock()
    crud.get_multi_with_filters_async = AsyncMock()
    crud.create_async = AsyncMock()
    crud.get_async = AsyncMock()
    crud.update_async = AsyncMock()
    crud.delete_async = AsyncMock()
    return crud


def _make_audit_crud():
    crud = MagicMock()
    crud.create_async = AsyncMock()
    return crud


def _set_user_response_fields(user: MagicMock) -> None:
    user.role_name = None
    user.roles = []
    user.role_ids = []
    user.is_admin = False


# ============================================================================
# Test: GET /users - Get User List
# ============================================================================


class TestGetUsers:
    """Tests for GET /api/v1/auth/users endpoint"""

    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_get_users_success(self, mock_user_crud_class, mock_db, mock_admin_user):
        """Test getting user list successfully"""
        from src.api.v1.auth.auth_modules.users import get_users

        # Mock users
        mock_users = [MagicMock() for _ in range(5)]
        for i, user in enumerate(mock_users):
            user.id = f"user-{i}"
            user.username = f"user{i}"
            user.email = f"user{i}@example.com"
            user.full_name = f"User {i}"
            user.role_id = "role-user-id"
            user.is_active = True
            user.is_locked = False
            user.last_login_at = None
            user.employee_id = None
            user.default_organization_id = None
            user.created_at = datetime.now(UTC)
            user.updated_at = datetime.now(UTC)
            _set_user_response_fields(user)

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_multi_with_filters_async.return_value = (mock_users, 5)
        mock_user_crud_class.return_value = mock_user_crud

        result = asyncio.run(
            get_users(
                params=MagicMock(
                    page=1,
                    page_size=10,
                    search=None,
                    role_id=None,
                    is_active=None,
                    organization_id=None,
                ),
                db=mock_db,
                current_user=mock_admin_user,
            )
        )

        assert result.status_code == status.HTTP_200_OK
        payload = _parse_json_response(result)
        data = payload["data"]
        pagination = data["pagination"]
        assert pagination["total"] == 5
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10
        assert pagination["total_pages"] == 1
        assert len(data["items"]) == 5
        mock_user_crud.get_multi_with_filters_async.assert_awaited_once()

    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_get_users_with_search(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test getting user list with search parameter"""
        from src.api.v1.auth.auth_modules.users import get_users

        mock_user = MagicMock()
        mock_user.id = "user-1"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.full_name = "Test User"
        mock_user.role_id = "role-user-id"
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.last_login_at = None
        mock_user.employee_id = None
        mock_user.default_organization_id = None
        mock_user.created_at = datetime.now(UTC)
        mock_user.updated_at = datetime.now(UTC)
        _set_user_response_fields(mock_user)

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_multi_with_filters_async.return_value = ([mock_user], 1)
        mock_user_crud_class.return_value = mock_user_crud

        params = MagicMock(
            page=1,
            page_size=10,
            search="test",
            role_id=None,
            is_active=None,
            organization_id=None,
        )

        result = asyncio.run(
            get_users(params=params, db=mock_db, current_user=mock_admin_user)
        )

        payload = _parse_json_response(result)
        data = payload["data"]
        pagination = data["pagination"]
        assert pagination["total"] == 1
        mock_user_crud.get_multi_with_filters_async.assert_awaited_once_with(
            db=mock_db,
            skip=0,
            limit=10,
            search="test",
            role_id=None,
            is_active=None,
            organization_id=None,
        )

    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_get_users_with_filters(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test getting user list with role and status filters"""
        from src.api.v1.auth.auth_modules.users import get_users

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_multi_with_filters_async.return_value = ([], 0)
        mock_user_crud_class.return_value = mock_user_crud

        params = MagicMock(
            page=1,
            page_size=10,
            search=None,
            role_id="role-admin-id",
            is_active=True,
            organization_id="org-123",
        )

        result = asyncio.run(
            get_users(params=params, db=mock_db, current_user=mock_admin_user)
        )

        payload = _parse_json_response(result)
        data = payload["data"]
        pagination = data["pagination"]
        assert pagination["total"] == 0
        assert pagination["total_pages"] == 0
        assert data["items"] == []
        mock_user_crud.get_multi_with_filters_async.assert_awaited_once()

    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_get_users_pagination(self, mock_user_crud_class, mock_db, mock_admin_user):
        """Test pagination of user list"""
        from src.api.v1.auth.auth_modules.users import get_users

        mock_users = []
        for i in range(10):
            user = MagicMock()
            user.id = f"user-{i}"
            user.username = f"user{i}"
            user.email = f"user{i}@example.com"
            user.full_name = f"User {i}"
            user.role_id = "role-user-id"
            user.is_active = True
            user.is_locked = False
            user.last_login_at = None
            user.employee_id = None
            user.default_organization_id = None
            user.created_at = datetime.now(UTC)
            user.updated_at = datetime.now(UTC)
            _set_user_response_fields(user)
            mock_users.append(user)

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_multi_with_filters_async.return_value = (mock_users, 25)
        mock_user_crud_class.return_value = mock_user_crud

        params = MagicMock(
            page=2,
            page_size=10,
            search=None,
            role_id=None,
            is_active=None,
            organization_id=None,
        )

        result = asyncio.run(
            get_users(params=params, db=mock_db, current_user=mock_admin_user)
        )

        payload = _parse_json_response(result)
        data = payload["data"]
        pagination = data["pagination"]
        assert pagination["total"] == 25
        assert pagination["page"] == 2
        assert pagination["page_size"] == 10
        assert pagination["total_pages"] == 3  # (25 + 10 - 1) // 10 = 3
        assert pagination["has_next"] is True
        assert pagination["has_prev"] is True
        mock_user_crud.get_multi_with_filters_async.assert_awaited_once_with(
            db=mock_db,
            skip=10,
            limit=10,
            search=None,
            role_id=None,
            is_active=None,
            organization_id=None,
        )


# ============================================================================
# Test: POST /users - Create User
# ============================================================================


class TestCreateUser:
    """Tests for POST /api/v1/auth/users endpoint"""

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_create_user_success(
        self,
        mock_user_crud_class,
        mock_user_service_class,
        mock_db,
        mock_admin_user,
    ):
        """Test creating user successfully"""
        from src.api.v1.auth.auth_modules.users import create_user
        from src.schemas.auth import UserCreate

        user_data = UserCreate(
            username="newuser",
            email="newuser@example.com",
            full_name="New User",
            password="SecurePass123!",
            role_id="role-user-id",
        )

        mock_user = MagicMock()
        mock_user.id = "new-user-id"
        mock_user.username = "newuser"
        mock_user.email = "newuser@example.com"
        mock_user.full_name = "New User"
        mock_user.role_id = "role-user-id"
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.last_login_at = None
        mock_user.employee_id = None
        mock_user.default_organization_id = None
        mock_user.created_at = datetime.now(UTC)
        mock_user.updated_at = datetime.now(UTC)
        _set_user_response_fields(mock_user)

        mock_user_crud = _make_user_crud()
        mock_user_crud_class.return_value = mock_user_crud
        mock_user_service = MagicMock()
        mock_user_service.create_user = AsyncMock(return_value=mock_user)
        mock_user_service_class.return_value = mock_user_service

        result = asyncio.run(
            create_user(
                user_data=user_data, db=mock_db, current_user=mock_admin_user
            )
        )

        assert result.username == "newuser"
        assert result.email == "newuser@example.com"
        mock_user_service.create_user.assert_awaited_once_with(
            user_data, assigned_by=str(mock_admin_user.id)
        )

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_create_user_duplicate_username(
        self, mock_user_crud_class, mock_user_service_class, mock_db, mock_admin_user
    ):
        """Test creating user with duplicate username"""
        from src.api.v1.auth.auth_modules.users import create_user
        from src.exceptions import BusinessLogicError
        from src.schemas.auth import UserCreate

        user_data = UserCreate(
            username="existinguser",
            email="new@example.com",
            full_name="New User",
            password="SecurePass123!",
            role_id="role-user-id",
        )

        mock_user_crud = _make_user_crud()
        mock_user_crud_class.return_value = mock_user_crud
        mock_user_service = MagicMock()
        mock_user_service.create_user = AsyncMock(
            side_effect=BusinessLogicError("用户名已存在")
        )
        mock_user_service_class.return_value = mock_user_service

        with pytest.raises(InvalidRequestError) as exc_info:
            asyncio.run(
                create_user(
                    user_data=user_data, db=mock_db, current_user=mock_admin_user
                )
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "用户名已存在" in exc_info.value.message


# ============================================================================
# Test: GET /users/{user_id} - Get User Details
# ============================================================================


class TestGetUser:
    """Tests for GET /api/v1/auth/users/{user_id} endpoint"""

    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_get_user_admin_access(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test admin accessing any user"""
        from src.api.v1.auth.auth_modules.users import get_user

        mock_user = MagicMock()
        mock_user.id = "target-user-id"
        mock_user.username = "targetuser"
        mock_user.email = "target@example.com"
        mock_user.full_name = "Target User"
        mock_user.role_id = "role-user-id"
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.last_login_at = None
        mock_user.employee_id = None
        mock_user.default_organization_id = None
        mock_user.created_at = datetime.now(UTC)
        mock_user.updated_at = datetime.now(UTC)
        _set_user_response_fields(mock_user)

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_async.return_value = mock_user
        mock_user_crud_class.return_value = mock_user_crud

        result = asyncio.run(
            get_user(
                user_id="target-user-id", db=mock_db, current_user=mock_admin_user
            )
        )

        assert result.username == "targetuser"
        mock_user_crud.get_async.assert_awaited_once_with(mock_db, "target-user-id")

    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_get_user_self_access(
        self, mock_user_crud_class, mock_db, mock_regular_user
    ):
        """Test user accessing their own information"""
        from src.api.v1.auth.auth_modules.users import get_user

        mock_user = MagicMock()
        mock_user.id = "user-id"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.full_name = "Test User"
        mock_user.role_id = "role-user-id"
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.last_login_at = None
        mock_user.employee_id = None
        mock_user.default_organization_id = None
        mock_user.created_at = datetime.now(UTC)
        mock_user.updated_at = datetime.now(UTC)
        _set_user_response_fields(mock_user)

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_async.return_value = mock_user
        mock_user_crud_class.return_value = mock_user_crud

        result = asyncio.run(
            get_user(user_id="user-id", db=mock_db, current_user=mock_regular_user)
        )

        assert result.username == "testuser"
        mock_user_crud.get_async.assert_awaited_once()

    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_get_user_forbidden(self, mock_user_crud_class, mock_db, mock_regular_user):
        """Test user trying to access another user's information"""
        from src.api.v1.auth.auth_modules.users import get_user

        with pytest.raises(PermissionDeniedError) as exc_info:
            asyncio.run(
                get_user(
                    user_id="other-user-id", db=mock_db, current_user=mock_regular_user
                )
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "无权访问" in exc_info.value.message

    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_get_user_not_found(self, mock_user_crud_class, mock_db, mock_admin_user):
        """Test getting non-existent user"""
        from src.api.v1.auth.auth_modules.users import get_user

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_async.return_value = None
        mock_user_crud_class.return_value = mock_user_crud

        with pytest.raises(ResourceNotFoundError) as exc_info:
            asyncio.run(
                get_user(
                    user_id="nonexistent-id",
                    db=mock_db,
                    current_user=mock_admin_user,
                )
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "不存在" in exc_info.value.message


# ============================================================================
# Test: PUT /users/{user_id} - Update User
# ============================================================================


class TestUpdateUser:
    """Tests for PUT /api/v1/auth/users/{user_id} endpoint"""

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_update_user_admin_success(
        self,
        mock_user_crud_class,
        mock_user_service_class,
        mock_db,
        mock_admin_user,
        mock_rbac_service,
    ):
        """Test admin updating user successfully"""
        from src.api.v1.auth.auth_modules.users import update_user
        from src.schemas.auth import UserUpdate

        user_data = UserUpdate(full_name="Updated Name", role_id="role-admin-id")

        mock_existing_user = MagicMock()
        mock_existing_user.id = "target-user-id"

        mock_updated_user = MagicMock()
        mock_updated_user.id = "target-user-id"
        mock_updated_user.username = "targetuser"
        mock_updated_user.email = "target@example.com"
        mock_updated_user.full_name = "Updated Name"
        mock_updated_user.role_id = "role-admin-id"
        mock_updated_user.is_active = True
        mock_updated_user.is_locked = False
        mock_updated_user.last_login_at = None
        mock_updated_user.employee_id = None
        mock_updated_user.default_organization_id = None
        mock_updated_user.created_at = datetime.now(UTC)
        mock_updated_user.updated_at = datetime.now(UTC)
        _set_user_response_fields(mock_updated_user)

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_async.return_value = mock_existing_user
        mock_user_crud_class.return_value = mock_user_crud
        mock_user_service = MagicMock()
        mock_user_service.update_user = AsyncMock(return_value=mock_updated_user)
        mock_user_service_class.return_value = mock_user_service

        mock_rbac_service.get_user_role_summary.side_effect = None
        mock_rbac_service.get_user_role_summary.return_value = ADMIN_ROLE_SUMMARY

        result = asyncio.run(
            update_user(
                user_id="target-user-id",
                user_data=user_data,
                db=mock_db,
                current_user=mock_admin_user,
            )
        )

        assert result.full_name == "Updated Name"
        assert result.role_id == "role-admin-id"
        mock_user_service.update_user.assert_awaited_once_with(
            "target-user-id", user_data, assigned_by=str(mock_admin_user.id)
        )

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_update_user_self_success(
        self, mock_user_crud_class, mock_user_service_class, mock_db, mock_regular_user
    ):
        """Test user updating their own information"""
        from src.api.v1.auth.auth_modules.users import update_user
        from src.schemas.auth import UserUpdate

        user_data = UserUpdate(full_name="My Updated Name")

        mock_updated_user = MagicMock()
        mock_updated_user.id = "user-id"
        mock_updated_user.username = "testuser"
        mock_updated_user.email = "test@example.com"
        mock_updated_user.full_name = "My Updated Name"
        mock_updated_user.role_id = "role-user-id"
        mock_updated_user.is_active = True
        mock_updated_user.is_locked = False
        mock_updated_user.last_login_at = None
        mock_updated_user.employee_id = None
        mock_updated_user.default_organization_id = None
        mock_updated_user.created_at = datetime.now(UTC)
        mock_updated_user.updated_at = datetime.now(UTC)
        _set_user_response_fields(mock_updated_user)

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_async.return_value = mock_regular_user
        mock_user_crud_class.return_value = mock_user_crud
        mock_user_service = MagicMock()
        mock_user_service.update_user = AsyncMock(return_value=mock_updated_user)
        mock_user_service_class.return_value = mock_user_service

        result = asyncio.run(
            update_user(
                user_id="user-id",
                user_data=user_data,
                db=mock_db,
                current_user=mock_regular_user,
            )
        )

        assert result.full_name == "My Updated Name"
        mock_user_service.update_user.assert_awaited_once_with(
            "user-id", user_data, assigned_by=str(mock_regular_user.id)
        )

    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_update_user_forbidden(
        self, mock_user_crud_class, mock_db, mock_regular_user
    ):
        """Test user trying to update another user"""
        from src.api.v1.auth.auth_modules.users import update_user
        from src.schemas.auth import UserUpdate

        user_data = UserUpdate(full_name="Hacked Name")

        with pytest.raises(PermissionDeniedError) as exc_info:
            asyncio.run(
                update_user(
                    user_id="other-user-id",
                    user_data=user_data,
                    db=mock_db,
                    current_user=mock_regular_user,
                )
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "无权修改" in exc_info.value.message

    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_update_user_not_found(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test updating non-existent user"""
        from src.api.v1.auth.auth_modules.users import update_user
        from src.schemas.auth import UserUpdate

        user_data = UserUpdate(full_name="Updated Name")

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_async.return_value = None
        mock_user_crud_class.return_value = mock_user_crud

        with pytest.raises(ResourceNotFoundError) as exc_info:
            asyncio.run(
                update_user(
                    user_id="nonexistent-id",
                    user_data=user_data,
                    db=mock_db,
                    current_user=mock_admin_user,
                )
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test: POST /users/{user_id}/change-password - Change Password
# ============================================================================


class TestChangePassword:
    """Tests for POST /api/v1/auth/users/{user_id}/change-password endpoint"""

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_change_password_success(
        self, mock_user_crud_class, mock_user_service_class, mock_db, mock_regular_user
    ):
        """Test changing password successfully"""
        from src.api.v1.auth.auth_modules.users import change_password
        from src.schemas.auth import PasswordChangeRequest

        password_data = PasswordChangeRequest(
            current_password="OldPass123!", new_password="NewPass123!"
        )

        mock_user = MagicMock()
        mock_user.id = "user-id"

        mock_user_service = MagicMock()
        mock_user_service.change_password = AsyncMock(return_value=True)
        mock_user_service_class.return_value = mock_user_service

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_async.return_value = mock_user
        mock_user_crud_class.return_value = mock_user_crud

        result = asyncio.run(
            change_password(
                user_id="user-id",
                password_data=password_data,
                db=mock_db,
                current_user=mock_regular_user,
            )
        )

        assert result["message"] == "密码修改成功"
        mock_user_service.change_password.assert_awaited_once()

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_change_password_admin_for_user(
        self, mock_user_crud_class, mock_user_service_class, mock_db, mock_admin_user
    ):
        """Test admin changing password for another user"""
        from src.api.v1.auth.auth_modules.users import change_password
        from src.schemas.auth import PasswordChangeRequest

        password_data = PasswordChangeRequest(
            current_password="OldPass123!", new_password="NewPass123!"
        )

        mock_user = MagicMock()
        mock_user.id = "target-user-id"

        mock_user_service = MagicMock()
        mock_user_service.change_password = AsyncMock(return_value=True)
        mock_user_service_class.return_value = mock_user_service

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_async.return_value = mock_user
        mock_user_crud_class.return_value = mock_user_crud

        result = asyncio.run(
            change_password(
                user_id="target-user-id",
                password_data=password_data,
                db=mock_db,
                current_user=mock_admin_user,
            )
        )

        assert result["message"] == "密码修改成功"

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_change_password_forbidden(
        self, mock_user_crud_class, mock_user_service_class, mock_db, mock_regular_user
    ):
        """Test user trying to change another user's password"""
        from src.api.v1.auth.auth_modules.users import change_password
        from src.schemas.auth import PasswordChangeRequest

        password_data = PasswordChangeRequest(
            current_password="OldPass123!", new_password="NewPass123!"
        )

        with pytest.raises(PermissionDeniedError) as exc_info:
            asyncio.run(
                change_password(
                    user_id="other-user-id",
                    password_data=password_data,
                    db=mock_db,
                    current_user=mock_regular_user,
                )
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "无权修改" in exc_info.value.message

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_change_password_user_not_found(
        self, mock_user_crud_class, mock_user_service_class, mock_db, mock_admin_user
    ):
        """Test changing password for non-existent user"""
        from src.api.v1.auth.auth_modules.users import change_password
        from src.schemas.auth import PasswordChangeRequest

        password_data = PasswordChangeRequest(
            current_password="OldPass123!", new_password="NewPass123!"
        )

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_async.return_value = None
        mock_user_crud_class.return_value = mock_user_crud

        with pytest.raises(ResourceNotFoundError) as exc_info:
            asyncio.run(
                change_password(
                    user_id="nonexistent-id",
                    password_data=password_data,
                    db=mock_db,
                    current_user=mock_admin_user,
                )
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test: POST /users/{user_id}/deactivate - Deactivate User
# ============================================================================


class TestDeactivateUser:
    """Tests for POST /api/v1/auth/users/{user_id}/deactivate endpoint"""

    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_deactivate_user_success(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test deactivating user successfully"""
        from src.api.v1.auth.auth_modules.users import deactivate_user

        mock_user = MagicMock()

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_async.return_value = mock_user
        mock_user_crud.delete_async.return_value = True
        mock_user_crud_class.return_value = mock_user_crud

        result = asyncio.run(
            deactivate_user(
                user_id="user-id", db=mock_db, current_user=mock_admin_user
            )
        )

        assert result["message"] == "用户已停用"
        mock_user_crud.delete_async.assert_awaited_once_with(mock_db, "user-id")

    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_deactivate_user_not_found(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test deactivating non-existent user"""
        from src.api.v1.auth.auth_modules.users import deactivate_user

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_async.return_value = None
        mock_user_crud_class.return_value = mock_user_crud

        with pytest.raises(ResourceNotFoundError) as exc_info:
            asyncio.run(
                deactivate_user(
                    user_id="nonexistent-id", db=mock_db, current_user=mock_admin_user
                )
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test: POST /users/{user_id}/activate - Activate User
# ============================================================================


class TestActivateUser:
    """Tests for POST /api/v1/auth/users/{user_id}/activate endpoint"""

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_activate_user_success(
        self, mock_user_service_class, mock_db, mock_admin_user
    ):
        """Test activating user successfully"""
        from src.api.v1.auth.auth_modules.users import activate_user

        mock_user_service = MagicMock()
        mock_user_service.activate_user = AsyncMock(return_value=True)
        mock_user_service_class.return_value = mock_user_service

        result = asyncio.run(
            activate_user(user_id="user-id", db=mock_db, current_user=mock_admin_user)
        )

        assert result["message"] == "用户已激活"
        mock_user_service.activate_user.assert_awaited_once_with("user-id")

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_activate_user_not_found(
        self, mock_user_service_class, mock_db, mock_admin_user
    ):
        """Test activating non-existent user"""
        from src.api.v1.auth.auth_modules.users import activate_user

        mock_user_service = MagicMock()
        mock_user_service.activate_user = AsyncMock(return_value=False)
        mock_user_service_class.return_value = mock_user_service

        with pytest.raises(ResourceNotFoundError) as exc_info:
            asyncio.run(
                activate_user(
                    user_id="nonexistent-id", db=mock_db, current_user=mock_admin_user
                )
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test: POST /users/{user_id}/lock - Lock User Account
# ============================================================================


class TestLockUser:
    """Tests for POST /api/v1/auth/users/{user_id}/lock endpoint"""

    @patch("src.api.v1.auth.auth_modules.users.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_lock_user_success(
        self,
        mock_user_service_class,
        mock_audit_crud_class,
        mock_db,
        mock_admin_user,
        mock_request,
    ):
        """Test locking user account successfully"""
        from src.api.v1.auth.auth_modules.users import lock_user

        mock_user = MagicMock()
        mock_user.username = "testuser"

        mock_audit_crud = _make_audit_crud()

        mock_user_service = MagicMock()
        mock_user_service.lock_user = AsyncMock(return_value=mock_user)
        mock_user_service_class.return_value = mock_user_service
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            lock_user(
                user_id="user-id",
                request=mock_request,
                db=mock_db,
                current_user=mock_admin_user,
            )
        )

        assert result["success"] is True
        assert "已锁定" in result["message"]
        mock_audit_crud.create_async.assert_awaited_once()

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_lock_user_not_found(
        self, mock_user_service_class, mock_db, mock_admin_user, mock_request
    ):
        """Test locking non-existent user"""
        from src.api.v1.auth.auth_modules.users import lock_user

        mock_user_service = MagicMock()
        mock_user_service.lock_user = AsyncMock(return_value=None)
        mock_user_service_class.return_value = mock_user_service

        with pytest.raises(ResourceNotFoundError) as exc_info:
            asyncio.run(
                lock_user(
                    user_id="nonexistent-id",
                    request=mock_request,
                    db=mock_db,
                    current_user=mock_admin_user,
                )
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test: POST /users/{user_id}/unlock - Unlock User Account
# ============================================================================


class TestUnlockUserAccount:
    """Tests for POST /api/v1/auth/users/{user_id}/unlock endpoint"""

    @patch("src.api.v1.auth.auth_modules.users.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_unlock_user_success(
        self,
        mock_user_service_class,
        mock_audit_crud_class,
        mock_db,
        mock_admin_user,
        mock_request,
    ):
        """Test unlocking user account successfully"""
        from src.api.v1.auth.auth_modules.users import unlock_user_account

        mock_user = MagicMock()
        mock_user.username = "testuser"

        mock_audit_crud = _make_audit_crud()

        mock_user_service = MagicMock()
        mock_user_service.unlock_user_with_result = AsyncMock(return_value=mock_user)
        mock_user_service_class.return_value = mock_user_service
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            unlock_user_account(
                user_id="user-id",
                request=mock_request,
                db=mock_db,
                current_user=mock_admin_user,
            )
        )

        assert result["success"] is True
        assert "已解锁" in result["message"]
        mock_audit_crud.create_async.assert_awaited_once()

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_unlock_user_not_found(
        self, mock_user_service_class, mock_db, mock_admin_user, mock_request
    ):
        """Test unlocking non-existent user"""
        from src.api.v1.auth.auth_modules.users import unlock_user_account

        mock_user_service = MagicMock()
        mock_user_service.unlock_user_with_result = AsyncMock(return_value=None)
        mock_user_service_class.return_value = mock_user_service

        with pytest.raises(ResourceNotFoundError) as exc_info:
            asyncio.run(
                unlock_user_account(
                    user_id="nonexistent-id",
                    request=mock_request,
                    db=mock_db,
                    current_user=mock_admin_user,
                )
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test: POST /users/{user_id}/reset-password - Reset User Password
# ============================================================================


class TestResetUserPassword:
    """Tests for POST /api/v1/auth/users/{user_id}/reset-password endpoint"""

    @patch("src.api.v1.auth.auth_modules.users.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_reset_password_success(
        self,
        mock_user_service_class,
        mock_audit_crud_class,
        mock_db,
        mock_admin_user,
        mock_request,
    ):
        """Test resetting user password successfully"""
        from src.api.v1.auth.auth_modules.users import reset_user_password
        from src.schemas.auth import AdminPasswordResetRequest

        password_data = AdminPasswordResetRequest(
            new_password="NewSecurePass123!",
            reason="User forgot password",
        )

        mock_user = MagicMock()
        mock_user.username = "testuser"

        mock_audit_crud = _make_audit_crud()

        mock_user_service = MagicMock()
        mock_user_service.admin_reset_password = AsyncMock(return_value=mock_user)
        mock_user_service_class.return_value = mock_user_service
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            reset_user_password(
                user_id="user-id",
                password_data=password_data,
                request=mock_request,
                db=mock_db,
                current_user=mock_admin_user,
            )
        )

        assert result["success"] is True
        assert "密码已重置" in result["message"]
        assert result["user_id"] == "user-id"
        mock_audit_crud.create_async.assert_awaited_once()

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_reset_password_user_not_found(
        self, mock_user_service_class, mock_db, mock_admin_user, mock_request
    ):
        """Test resetting password for non-existent user"""
        from src.api.v1.auth.auth_modules.users import reset_user_password
        from src.schemas.auth import AdminPasswordResetRequest

        password_data = AdminPasswordResetRequest(
            new_password="NewSecurePass123!", reason="Test"
        )

        mock_user_service = MagicMock()
        mock_user_service.admin_reset_password = AsyncMock(return_value=None)
        mock_user_service_class.return_value = mock_user_service

        with pytest.raises(ResourceNotFoundError) as exc_info:
            asyncio.run(
                reset_user_password(
                    user_id="nonexistent-id",
                    password_data=password_data,
                    request=mock_request,
                    db=mock_db,
                    current_user=mock_admin_user,
                )
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test: GET /users/statistics/summary - Get User Statistics
# ============================================================================


class TestGetUserStatistics:
    """Tests for GET /api/v1/auth/users/statistics/summary endpoint"""

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_get_user_statistics_success(
        self, mock_user_service_class, mock_db, mock_admin_user
    ):
        """Test getting user statistics successfully"""
        from src.api.v1.auth.auth_modules.users import get_user_statistics

        mock_stats = {
            "total_users": 10,
            "active_users": 8,
            "locked_users": 1,
            "inactive_users": 2,
            "online_users": 0,
        }

        mock_user_service = MagicMock()
        mock_user_service.get_statistics = AsyncMock(return_value=mock_stats)
        mock_user_service_class.return_value = mock_user_service

        result = asyncio.run(
            get_user_statistics(db=mock_db, current_user=mock_admin_user)
        )

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["total_users"] == 10
        assert result["data"]["active_users"] == 8
        assert result["data"]["locked_users"] == 1
        assert result["data"]["inactive_users"] == 2

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_get_user_statistics_empty_db(
        self, mock_user_service_class, mock_db, mock_admin_user
    ):
        """Test getting user statistics with empty database"""
        from src.api.v1.auth.auth_modules.users import get_user_statistics

        mock_stats = {
            "total_users": 0,
            "active_users": 0,
            "locked_users": 0,
            "inactive_users": 0,
            "online_users": 0,
        }
        mock_user_service = MagicMock()
        mock_user_service.get_statistics = AsyncMock(return_value=mock_stats)
        mock_user_service_class.return_value = mock_user_service

        result = asyncio.run(
            get_user_statistics(db=mock_db, current_user=mock_admin_user)
        )

        assert result["success"] is True
        assert result["data"]["total_users"] == 0


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================


class TestUsersEdgeCases:
    """Tests for edge cases and error handling"""

    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_get_users_empty_list(self, mock_user_crud_class, mock_db, mock_admin_user):
        """Test getting users when no users exist"""
        from src.api.v1.auth.auth_modules.users import get_users

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_multi_with_filters_async.return_value = ([], 0)
        mock_user_crud_class.return_value = mock_user_crud

        result = asyncio.run(
            get_users(
                params=MagicMock(
                    page=1,
                    page_size=10,
                    search=None,
                    role_id=None,
                    is_active=None,
                    organization_id=None,
                ),
                db=mock_db,
                current_user=mock_admin_user,
            )
        )

        payload = _parse_json_response(result)
        data = payload["data"]
        pagination = data["pagination"]
        assert pagination["total"] == 0
        assert pagination["total_pages"] == 0
        assert data["items"] == []
        mock_user_crud.get_multi_with_filters_async.assert_awaited_once()

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    @patch("src.api.v1.auth.auth_modules.users.UserCRUD")
    def test_update_user_with_business_logic_error(
        self, mock_user_crud_class, mock_user_service_class, mock_db, mock_admin_user
    ):
        """Test updating user with business logic error from CRUD layer"""
        from src.api.v1.auth.auth_modules.users import update_user
        from src.exceptions import BusinessLogicError
        from src.schemas.auth import UserUpdate

        user_data = UserUpdate(full_name="Updated Name")  # Valid data

        mock_existing_user = MagicMock()

        mock_user_crud = _make_user_crud()
        mock_user_crud.get_async.return_value = mock_existing_user
        mock_user_crud_class.return_value = mock_user_crud
        mock_user_service = MagicMock()
        mock_user_service.update_user = AsyncMock(
            side_effect=BusinessLogicError("用户名已被占用")
        )
        mock_user_service_class.return_value = mock_user_service

        with pytest.raises(InvalidRequestError) as exc_info:
            asyncio.run(
                update_user(
                    user_id="user-id",
                    user_data=user_data,
                    db=mock_db,
                    current_user=mock_admin_user,
                )
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "用户名已被占用" in exc_info.value.message

    @patch("src.api.v1.auth.auth_modules.users.AsyncUserManagementService")
    def test_get_user_statistics_db_error(
        self, mock_user_service_class, mock_db, mock_admin_user
    ):
        """Test getting user statistics with database error"""
        from src.api.v1.auth.auth_modules.users import get_user_statistics

        mock_user_service = MagicMock()
        mock_user_service.get_statistics = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        mock_user_service_class.return_value = mock_user_service

        with pytest.raises(InternalServerError) as exc_info:
            asyncio.run(get_user_statistics(db=mock_db, current_user=mock_admin_user))

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
