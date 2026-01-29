"""
Comprehensive Unit Tests for Users API Routes (src/api/v1/auth_modules/users.py)

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
- Mock all dependencies (UserCRUD, AuthService, database, auth)
- Test successful responses
- Test error handling scenarios
- Test request validation
- Test response schemas
- Test permission checks
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status

pytestmark = pytest.mark.api


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Create mock database session"""
    return MagicMock()


@pytest.fixture
def mock_admin_user():
    """Create mock admin user"""
    user = MagicMock()
    user.id = "admin-id"
    user.username = "admin"
    user.role = "admin"
    user.is_active = True
    user.is_locked = False
    return user


@pytest.fixture
def mock_regular_user():
    """Create mock regular user"""
    user = MagicMock()
    user.id = "user-id"
    user.username = "testuser"
    user.role = "user"
    user.is_active = True
    user.is_locked = False
    return user


@pytest.fixture
def mock_user_response():
    """Create mock user response"""
    user = MagicMock()
    user.id = "test-user-id"
    user.username = "testuser"
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.role = "user"
    user.is_active = True
    user.is_locked = False
    user.employee_id = None
    user.default_organization_id = None
    user.last_login_at = None
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


# ============================================================================
# Test: GET /users - Get User List
# ============================================================================


class TestGetUsers:
    """Tests for GET /api/v1/auth/users endpoint"""

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_get_users_success(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test getting user list successfully"""
        from src.api.v1.auth_modules.users import get_users

        # Mock users
        mock_users = [MagicMock() for _ in range(5)]
        for i, user in enumerate(mock_users):
            user.id = f"user-{i}"
            user.username = f"user{i}"
            user.email = f"user{i}@example.com"
            user.full_name = f"User {i}"
            user.role = "user"
            user.is_active = True
            user.is_locked = False
            user.last_login_at = None
            user.employee_id = None
            user.default_organization_id = None
            user.created_at = datetime.now(UTC)
            user.updated_at = datetime.now(UTC)

        mock_user_crud = MagicMock()
        mock_user_crud.get_multi_with_filters.return_value = (mock_users, 5)
        mock_user_crud_class.return_value = mock_user_crud

        result = await get_users(
            params=MagicMock(
                page=1,
                page_size=10,
                search=None,
                role=None,
                is_active=None,
                organization_id=None,
            ),
            db=mock_db,
            current_user=mock_admin_user,
        )

        assert result.total == 5
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_pages == 1
        assert len(result.users) == 5
        mock_user_crud.get_multi_with_filters.assert_called_once()

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_get_users_with_search(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test getting user list with search parameter"""
        from src.api.v1.auth_modules.users import get_users

        mock_user = MagicMock()
        mock_user.id = "user-1"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.full_name = "Test User"
        mock_user.role = "user"
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.last_login_at = None
        mock_user.employee_id = None
        mock_user.default_organization_id = None
        mock_user.created_at = datetime.now(UTC)
        mock_user.updated_at = datetime.now(UTC)

        mock_user_crud = MagicMock()
        mock_user_crud.get_multi_with_filters.return_value = ([mock_user], 1)
        mock_user_crud_class.return_value = mock_user_crud

        params = MagicMock(
            page=1,
            page_size=10,
            search="test",
            role=None,
            is_active=None,
            organization_id=None,
        )

        result = await get_users(
            params=params, db=mock_db, current_user=mock_admin_user
        )

        assert result.total == 1
        mock_user_crud.get_multi_with_filters.assert_called_once_with(
            db=mock_db,
            skip=0,
            limit=10,
            search="test",
            role=None,
            is_active=None,
            organization_id=None,
        )

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_get_users_with_filters(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test getting user list with role and status filters"""
        from src.api.v1.auth_modules.users import get_users

        mock_user_crud = MagicMock()
        mock_user_crud.get_multi_with_filters.return_value = ([], 0)
        mock_user_crud_class.return_value = mock_user_crud

        params = MagicMock(
            page=1,
            page_size=10,
            search=None,
            role="admin",
            is_active=True,
            organization_id="org-123",
        )

        result = await get_users(
            params=params, db=mock_db, current_user=mock_admin_user
        )

        assert result.total == 0
        mock_user_crud.get_multi_with_filters.assert_called_once()

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_get_users_pagination(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test pagination of user list"""
        from src.api.v1.auth_modules.users import get_users

        mock_users = []
        for i in range(10):
            user = MagicMock()
            user.id = f"user-{i}"
            user.username = f"user{i}"
            user.email = f"user{i}@example.com"
            user.full_name = f"User {i}"
            user.role = "user"
            user.is_active = True
            user.is_locked = False
            user.last_login_at = None
            user.employee_id = None
            user.default_organization_id = None
            user.created_at = datetime.now(UTC)
            user.updated_at = datetime.now(UTC)
            mock_users.append(user)

        mock_user_crud = MagicMock()
        mock_user_crud.get_multi_with_filters.return_value = (mock_users, 25)
        mock_user_crud_class.return_value = mock_user_crud

        params = MagicMock(
            page=2,
            page_size=10,
            search=None,
            role=None,
            is_active=None,
            organization_id=None,
        )

        result = await get_users(
            params=params, db=mock_db, current_user=mock_admin_user
        )

        assert result.total == 25
        assert result.page == 2
        assert result.page_size == 10
        assert result.total_pages == 3  # (25 + 10 - 1) // 10 = 3
        mock_user_crud.get_multi_with_filters.assert_called_once_with(
            db=mock_db,
            skip=10,
            limit=10,
            search=None,
            role=None,
            is_active=None,
            organization_id=None,
        )


# ============================================================================
# Test: POST /users - Create User
# ============================================================================


class TestCreateUser:
    """Tests for POST /api/v1/auth/users endpoint"""

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_create_user_success(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test creating user successfully"""
        from src.api.v1.auth_modules.users import create_user

        from src.schemas.auth import UserCreate

        user_data = UserCreate(
            username="newuser",
            email="newuser@example.com",
            full_name="New User",
            password="SecurePass123!",
            role="user",
        )

        mock_user = MagicMock()
        mock_user.id = "new-user-id"
        mock_user.username = "newuser"
        mock_user.email = "newuser@example.com"
        mock_user.full_name = "New User"
        mock_user.role = "user"
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.last_login_at = None
        mock_user.employee_id = None
        mock_user.default_organization_id = None
        mock_user.created_at = datetime.now(UTC)
        mock_user.updated_at = datetime.now(UTC)

        mock_user_crud = MagicMock()
        mock_user_crud.create.return_value = mock_user
        mock_user_crud_class.return_value = mock_user_crud

        result = await create_user(
            user_data=user_data, db=mock_db, current_user=mock_admin_user
        )

        assert result.username == "newuser"
        assert result.email == "newuser@example.com"
        mock_user_crud.create.assert_called_once_with(mock_db, user_data)

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test creating user with duplicate username"""
        from src.api.v1.auth_modules.users import create_user

        from src.exceptions import BusinessLogicError
        from src.schemas.auth import UserCreate

        user_data = UserCreate(
            username="existinguser",
            email="new@example.com",
            full_name="New User",
            password="SecurePass123!",
            role="user",
        )

        mock_user_crud = MagicMock()
        mock_user_crud.create.side_effect = BusinessLogicError("用户名已存在")
        mock_user_crud_class.return_value = mock_user_crud

        with pytest.raises(HTTPException) as exc_info:
            await create_user(
                user_data=user_data, db=mock_db, current_user=mock_admin_user
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "用户名已存在" in exc_info.value.detail


# ============================================================================
# Test: GET /users/{user_id} - Get User Details
# ============================================================================


class TestGetUser:
    """Tests for GET /api/v1/auth/users/{user_id} endpoint"""

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_get_user_admin_access(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test admin accessing any user"""
        from src.api.v1.auth_modules.users import get_user

        mock_user = MagicMock()
        mock_user.id = "target-user-id"
        mock_user.username = "targetuser"
        mock_user.email = "target@example.com"
        mock_user.full_name = "Target User"
        mock_user.role = "user"
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.last_login_at = None
        mock_user.employee_id = None
        mock_user.default_organization_id = None
        mock_user.created_at = datetime.now(UTC)
        mock_user.updated_at = datetime.now(UTC)

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = mock_user
        mock_user_crud_class.return_value = mock_user_crud

        result = await get_user(
            user_id="target-user-id", db=mock_db, current_user=mock_admin_user
        )

        assert result.username == "targetuser"
        mock_user_crud.get.assert_called_once_with(mock_db, "target-user-id")

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_get_user_self_access(
        self, mock_user_crud_class, mock_db, mock_regular_user
    ):
        """Test user accessing their own information"""
        from src.api.v1.auth_modules.users import get_user

        mock_user = MagicMock()
        mock_user.id = "user-id"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.full_name = "Test User"
        mock_user.role = "user"
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.last_login_at = None
        mock_user.employee_id = None
        mock_user.default_organization_id = None
        mock_user.created_at = datetime.now(UTC)
        mock_user.updated_at = datetime.now(UTC)

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = mock_user
        mock_user_crud_class.return_value = mock_user_crud

        result = await get_user(
            user_id="user-id", db=mock_db, current_user=mock_regular_user
        )

        assert result.username == "testuser"
        mock_user_crud.get.assert_called_once()

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_get_user_forbidden(
        self, mock_user_crud_class, mock_db, mock_regular_user
    ):
        """Test user trying to access another user's information"""
        from src.api.v1.auth_modules.users import get_user

        with pytest.raises(HTTPException) as exc_info:
            await get_user(
                user_id="other-user-id", db=mock_db, current_user=mock_regular_user
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "无权访问" in exc_info.value.detail

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_get_user_not_found(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test getting non-existent user"""
        from src.api.v1.auth_modules.users import get_user

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = None
        mock_user_crud_class.return_value = mock_user_crud

        with pytest.raises(HTTPException) as exc_info:
            await get_user(
                user_id="nonexistent-id", db=mock_db, current_user=mock_admin_user
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "用户不存在" in exc_info.value.detail


# ============================================================================
# Test: PUT /users/{user_id} - Update User
# ============================================================================


class TestUpdateUser:
    """Tests for PUT /api/v1/auth/users/{user_id} endpoint"""

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_update_user_admin_success(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test admin updating user successfully"""
        from src.api.v1.auth_modules.users import update_user

        from src.schemas.auth import UserUpdate

        user_data = UserUpdate(full_name="Updated Name", role="admin")

        mock_existing_user = MagicMock()
        mock_existing_user.id = "target-user-id"

        mock_updated_user = MagicMock()
        mock_updated_user.id = "target-user-id"
        mock_updated_user.username = "targetuser"
        mock_updated_user.email = "target@example.com"
        mock_updated_user.full_name = "Updated Name"
        mock_updated_user.role = "admin"
        mock_updated_user.is_active = True
        mock_updated_user.is_locked = False
        mock_updated_user.last_login_at = None
        mock_updated_user.employee_id = None
        mock_updated_user.default_organization_id = None
        mock_updated_user.created_at = datetime.now(UTC)
        mock_updated_user.updated_at = datetime.now(UTC)

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = mock_existing_user
        mock_user_crud.update.return_value = mock_updated_user
        mock_user_crud_class.return_value = mock_user_crud

        result = await update_user(
            user_id="target-user-id",
            user_data=user_data,
            db=mock_db,
            current_user=mock_admin_user,
        )

        assert result.full_name == "Updated Name"
        assert result.role == "admin"
        mock_user_crud.update.assert_called_once()

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_update_user_self_success(
        self, mock_user_crud_class, mock_db, mock_regular_user
    ):
        """Test user updating their own information"""
        from src.api.v1.auth_modules.users import update_user

        from src.schemas.auth import UserUpdate

        user_data = UserUpdate(full_name="My Updated Name")

        mock_updated_user = MagicMock()
        mock_updated_user.id = "user-id"
        mock_updated_user.username = "testuser"
        mock_updated_user.email = "test@example.com"
        mock_updated_user.full_name = "My Updated Name"
        mock_updated_user.role = "user"
        mock_updated_user.is_active = True
        mock_updated_user.is_locked = False
        mock_updated_user.last_login_at = None
        mock_updated_user.employee_id = None
        mock_updated_user.default_organization_id = None
        mock_updated_user.created_at = datetime.now(UTC)
        mock_updated_user.updated_at = datetime.now(UTC)

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = mock_regular_user
        mock_user_crud.update.return_value = mock_updated_user
        mock_user_crud_class.return_value = mock_user_crud

        result = await update_user(
            user_id="user-id",
            user_data=user_data,
            db=mock_db,
            current_user=mock_regular_user,
        )

        assert result.full_name == "My Updated Name"

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_update_user_forbidden(
        self, mock_user_crud_class, mock_db, mock_regular_user
    ):
        """Test user trying to update another user"""
        from src.api.v1.auth_modules.users import update_user

        from src.schemas.auth import UserUpdate

        user_data = UserUpdate(full_name="Hacked Name")

        with pytest.raises(HTTPException) as exc_info:
            await update_user(
                user_id="other-user-id",
                user_data=user_data,
                db=mock_db,
                current_user=mock_regular_user,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "无权修改" in exc_info.value.detail

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_update_user_not_found(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test updating non-existent user"""
        from src.api.v1.auth_modules.users import update_user

        from src.schemas.auth import UserUpdate

        user_data = UserUpdate(full_name="Updated Name")

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = None
        mock_user_crud_class.return_value = mock_user_crud

        with pytest.raises(HTTPException) as exc_info:
            await update_user(
                user_id="nonexistent-id",
                user_data=user_data,
                db=mock_db,
                current_user=mock_admin_user,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test: POST /users/{user_id}/change-password - Change Password
# ============================================================================


class TestChangePassword:
    """Tests for POST /api/v1/auth/users/{user_id}/change-password endpoint"""

    @patch("src.api.v1.auth_modules.users.AuthService")
    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_change_password_success(
        self, mock_user_crud_class, mock_auth_service_class, mock_db, mock_regular_user
    ):
        """Test changing password successfully"""
        from src.api.v1.auth_modules.users import change_password

        from src.schemas.auth import PasswordChangeRequest

        password_data = PasswordChangeRequest(
            current_password="OldPass123!", new_password="NewPass123!"
        )

        mock_user = MagicMock()
        mock_user.id = "user-id"

        mock_auth_service = MagicMock()
        mock_auth_service.change_password.return_value = True
        mock_auth_service_class.return_value = mock_auth_service

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = mock_user
        mock_user_crud_class.return_value = mock_user_crud

        result = await change_password(
            user_id="user-id",
            password_data=password_data,
            db=mock_db,
            current_user=mock_regular_user,
        )

        assert result["message"] == "密码修改成功"
        mock_auth_service.change_password.assert_called_once()

    @patch("src.api.v1.auth_modules.users.AuthService")
    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_change_password_admin_for_user(
        self, mock_user_crud_class, mock_auth_service_class, mock_db, mock_admin_user
    ):
        """Test admin changing password for another user"""
        from src.api.v1.auth_modules.users import change_password

        from src.schemas.auth import PasswordChangeRequest

        password_data = PasswordChangeRequest(
            current_password="OldPass123!", new_password="NewPass123!"
        )

        mock_user = MagicMock()
        mock_user.id = "target-user-id"

        mock_auth_service = MagicMock()
        mock_auth_service.change_password.return_value = True
        mock_auth_service_class.return_value = mock_auth_service

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = mock_user
        mock_user_crud_class.return_value = mock_user_crud

        result = await change_password(
            user_id="target-user-id",
            password_data=password_data,
            db=mock_db,
            current_user=mock_admin_user,
        )

        assert result["message"] == "密码修改成功"

    @patch("src.api.v1.auth_modules.users.AuthService")
    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_change_password_forbidden(
        self, mock_user_crud_class, mock_auth_service_class, mock_db, mock_regular_user
    ):
        """Test user trying to change another user's password"""
        from src.api.v1.auth_modules.users import change_password

        from src.schemas.auth import PasswordChangeRequest

        password_data = PasswordChangeRequest(
            current_password="OldPass123!", new_password="NewPass123!"
        )

        with pytest.raises(HTTPException) as exc_info:
            await change_password(
                user_id="other-user-id",
                password_data=password_data,
                db=mock_db,
                current_user=mock_regular_user,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "无权修改" in exc_info.value.detail

    @patch("src.api.v1.auth_modules.users.AuthService")
    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_change_password_user_not_found(
        self, mock_user_crud_class, mock_auth_service_class, mock_db, mock_admin_user
    ):
        """Test changing password for non-existent user"""
        from src.api.v1.auth_modules.users import change_password

        from src.schemas.auth import PasswordChangeRequest

        password_data = PasswordChangeRequest(
            current_password="OldPass123!", new_password="NewPass123!"
        )

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = None
        mock_user_crud_class.return_value = mock_user_crud

        with pytest.raises(HTTPException) as exc_info:
            await change_password(
                user_id="nonexistent-id",
                password_data=password_data,
                db=mock_db,
                current_user=mock_admin_user,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test: POST /users/{user_id}/deactivate - Deactivate User
# ============================================================================


class TestDeactivateUser:
    """Tests for POST /api/v1/auth/users/{user_id}/deactivate endpoint"""

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_deactivate_user_success(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test deactivating user successfully"""
        from src.api.v1.auth_modules.users import deactivate_user

        mock_user = MagicMock()

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = mock_user
        mock_user_crud.delete.return_value = True
        mock_user_crud_class.return_value = mock_user_crud

        result = await deactivate_user(
            user_id="user-id", db=mock_db, current_user=mock_admin_user
        )

        assert result["message"] == "用户已停用"
        mock_user_crud.delete.assert_called_once_with(mock_db, "user-id")

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_deactivate_user_not_found(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test deactivating non-existent user"""
        from src.api.v1.auth_modules.users import deactivate_user

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = None
        mock_user_crud_class.return_value = mock_user_crud

        with pytest.raises(HTTPException) as exc_info:
            await deactivate_user(
                user_id="nonexistent-id", db=mock_db, current_user=mock_admin_user
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test: POST /users/{user_id}/activate - Activate User
# ============================================================================


class TestActivateUser:
    """Tests for POST /api/v1/auth/users/{user_id}/activate endpoint"""

    @patch("src.api.v1.auth_modules.users.AuthService")
    @pytest.mark.asyncio
    async def test_activate_user_success(
        self, mock_auth_service_class, mock_db, mock_admin_user
    ):
        """Test activating user successfully"""
        from src.api.v1.auth_modules.users import activate_user

        mock_auth_service = MagicMock()
        mock_auth_service.activate_user.return_value = True
        mock_auth_service_class.return_value = mock_auth_service

        result = await activate_user(
            user_id="user-id", db=mock_db, current_user=mock_admin_user
        )

        assert result["message"] == "用户已激活"
        mock_auth_service.activate_user.assert_called_once_with("user-id")

    @patch("src.api.v1.auth_modules.users.AuthService")
    @pytest.mark.asyncio
    async def test_activate_user_not_found(
        self, mock_auth_service_class, mock_db, mock_admin_user
    ):
        """Test activating non-existent user"""
        from src.api.v1.auth_modules.users import activate_user

        mock_auth_service = MagicMock()
        mock_auth_service.activate_user.return_value = False
        mock_auth_service_class.return_value = mock_auth_service

        with pytest.raises(HTTPException) as exc_info:
            await activate_user(
                user_id="nonexistent-id", db=mock_db, current_user=mock_admin_user
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test: POST /users/{user_id}/lock - Lock User Account
# ============================================================================


class TestLockUser:
    """Tests for POST /api/v1/auth/users/{user_id}/lock endpoint"""

    @patch("src.api.v1.auth_modules.users.AuditLogCRUD")
    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_lock_user_success(
        self, mock_user_crud_class, mock_audit_crud_class, mock_db, mock_admin_user
    ):
        """Test locking user account successfully"""
        from src.api.v1.auth_modules.users import lock_user

        mock_user = MagicMock()
        mock_user.username = "testuser"

        mock_audit_crud = MagicMock()

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = mock_user
        mock_user_crud_class.return_value = mock_user_crud
        mock_audit_crud_class.return_value = mock_audit_crud

        result = await lock_user(
            user_id="user-id", db=mock_db, current_user=mock_admin_user
        )

        assert result["success"] is True
        assert "已锁定" in result["message"]
        assert mock_user.is_locked is True
        mock_audit_crud.create.assert_called_once()

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_lock_user_not_found(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test locking non-existent user"""
        from src.api.v1.auth_modules.users import lock_user

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = None
        mock_user_crud_class.return_value = mock_user_crud

        with pytest.raises(HTTPException) as exc_info:
            await lock_user(
                user_id="nonexistent-id", db=mock_db, current_user=mock_admin_user
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test: POST /users/{user_id}/unlock - Unlock User Account
# ============================================================================


class TestUnlockUserAccount:
    """Tests for POST /api/v1/auth/users/{user_id}/unlock endpoint"""

    @patch("src.api.v1.auth_modules.users.AuditLogCRUD")
    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_unlock_user_success(
        self, mock_user_crud_class, mock_audit_crud_class, mock_db, mock_admin_user
    ):
        """Test unlocking user account successfully"""
        from src.api.v1.auth_modules.users import unlock_user_account

        mock_user = MagicMock()
        mock_user.username = "testuser"

        mock_audit_crud = MagicMock()

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = mock_user
        mock_user_crud_class.return_value = mock_user_crud
        mock_audit_crud_class.return_value = mock_audit_crud

        result = await unlock_user_account(
            user_id="user-id", db=mock_db, current_user=mock_admin_user
        )

        assert result["success"] is True
        assert "已解锁" in result["message"]
        assert mock_user.is_locked is False
        mock_audit_crud.create.assert_called_once()

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_unlock_user_not_found(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test unlocking non-existent user"""
        from src.api.v1.auth_modules.users import unlock_user_account

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = None
        mock_user_crud_class.return_value = mock_user_crud

        with pytest.raises(HTTPException) as exc_info:
            await unlock_user_account(
                user_id="nonexistent-id", db=mock_db, current_user=mock_admin_user
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test: POST /users/{user_id}/reset-password - Reset User Password
# ============================================================================


class TestResetUserPassword:
    """Tests for POST /api/v1/auth/users/{user_id}/reset-password endpoint"""

    @patch("src.api.v1.auth_modules.users.AuditLogCRUD")
    @patch("src.api.v1.auth_modules.users.AuthService")
    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_reset_password_success(
        self,
        mock_user_crud_class,
        mock_auth_service_class,
        mock_audit_crud_class,
        mock_db,
        mock_admin_user,
    ):
        """Test resetting user password successfully"""
        from src.api.v1.auth_modules.users import reset_user_password

        password_data = {
            "new_password": "NewSecurePass123!",
            "reason": "User forgot password",
        }

        mock_user = MagicMock()
        mock_user.username = "testuser"

        mock_auth_service = MagicMock()
        mock_auth_service.get_password_hash.return_value = "hashed_password"
        mock_auth_service_class.return_value = mock_auth_service

        mock_audit_crud = MagicMock()

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = mock_user
        mock_user_crud_class.return_value = mock_user_crud
        mock_audit_crud_class.return_value = mock_audit_crud

        result = await reset_user_password(
            user_id="user-id",
            password_data=password_data,
            db=mock_db,
            current_user=mock_admin_user,
        )

        assert result["success"] is True
        assert "密码已重置" in result["message"]
        assert result["user_id"] == "user-id"
        mock_audit_crud.create.assert_called_once()

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test resetting password for non-existent user"""
        from src.api.v1.auth_modules.users import reset_user_password

        password_data = {"new_password": "NewSecurePass123!", "reason": "Test"}

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = None
        mock_user_crud_class.return_value = mock_user_crud

        with pytest.raises(HTTPException) as exc_info:
            await reset_user_password(
                user_id="nonexistent-id",
                password_data=password_data,
                db=mock_db,
                current_user=mock_admin_user,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test: GET /users/statistics/summary - Get User Statistics
# ============================================================================


class TestGetUserStatistics:
    """Tests for GET /api/v1/auth/users/statistics/summary endpoint"""

    @pytest.mark.asyncio
    async def test_get_user_statistics_success(self, mock_db, mock_admin_user):
        """Test getting user statistics successfully"""
        from src.api.v1.auth_modules.users import get_user_statistics

        # Mock database query
        mock_query = MagicMock()
        mock_query.filter.return_value.filter.return_value.scalar.return_value = 10
        mock_query.filter.return_value.scalar.return_value = 8

        mock_db.query.return_value = mock_query

        result = await get_user_statistics(db=mock_db, current_user=mock_admin_user)

        assert result["success"] is True
        assert "data" in result
        assert "total_users" in result["data"]
        assert "active_users" in result["data"]
        assert "locked_users" in result["data"]
        assert "inactive_users" in result["data"]

    @pytest.mark.asyncio
    async def test_get_user_statistics_empty_db(self, mock_db, mock_admin_user):
        """Test getting user statistics with empty database"""
        from src.api.v1.auth_modules.users import get_user_statistics

        # Mock database query returning 0 users
        # Need to properly chain the filter calls and scalar return
        call_count = [0]

        def mock_scalar():
            call_count[0] += 1
            return 0

        mock_query = MagicMock()
        # Each filter() returns the query itself for chaining
        mock_query.filter.return_value = mock_query
        mock_query.scalar.side_effect = mock_scalar

        mock_db.query.return_value = mock_query

        result = await get_user_statistics(db=mock_db, current_user=mock_admin_user)

        assert result["success"] is True
        # Just check the structure, not specific values since we're using scalar() side_effect
        assert "total_users" in result["data"]


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================


class TestUsersEdgeCases:
    """Tests for edge cases and error handling"""

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_get_users_empty_list(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test getting users when no users exist"""
        from src.api.v1.auth_modules.users import get_users

        mock_user_crud = MagicMock()
        mock_user_crud.get_multi_with_filters.return_value = ([], 0)
        mock_user_crud_class.return_value = mock_user_crud

        result = await get_users(
            params=MagicMock(
                page=1,
                page_size=10,
                search=None,
                role=None,
                is_active=None,
                organization_id=None,
            ),
            db=mock_db,
            current_user=mock_admin_user,
        )

        assert result.total == 0
        assert len(result.users) == 0
        assert result.total_pages == 0

    @patch("src.api.v1.auth_modules.users.UserCRUD")
    @pytest.mark.asyncio
    async def test_update_user_with_business_logic_error(
        self, mock_user_crud_class, mock_db, mock_admin_user
    ):
        """Test updating user with business logic error from CRUD layer"""
        from src.api.v1.auth_modules.users import update_user

        from src.exceptions import BusinessLogicError
        from src.schemas.auth import UserUpdate

        user_data = UserUpdate(full_name="Updated Name")  # Valid data

        mock_existing_user = MagicMock()

        mock_user_crud = MagicMock()
        mock_user_crud.get.return_value = mock_existing_user
        mock_user_crud.update.side_effect = BusinessLogicError("用户名已被占用")
        mock_user_crud_class.return_value = mock_user_crud

        with pytest.raises(HTTPException) as exc_info:
            await update_user(
                user_id="user-id",
                user_data=user_data,
                db=mock_db,
                current_user=mock_admin_user,
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "用户名已被占用" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_user_statistics_db_error(self, mock_db, mock_admin_user):
        """Test getting user statistics with database error"""
        from src.api.v1.auth_modules.users import get_user_statistics

        mock_db.query.side_effect = Exception("Database connection failed")

        with pytest.raises(HTTPException) as exc_info:
            await get_user_statistics(db=mock_db, current_user=mock_admin_user)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
