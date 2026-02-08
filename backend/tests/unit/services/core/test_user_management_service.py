"""
Comprehensive Unit Tests for AsyncUserManagementService

Tests cover:
1. User creation and validation
2. User update operations
3. User deactivation/activation/unlock
4. Email uniqueness checks
5. User lookup methods
6. Password management
7. Error handling
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import BusinessLogicError
from src.models.auth import User
from src.schemas.auth import UserCreate, UserUpdate
from src.services.core.user_management_service import AsyncUserManagementService

pytestmark = pytest.mark.asyncio


def _mock_execute_first(value):
    result = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = value
    result.scalars.return_value = scalars
    return result


# ===================== Fixtures =====================


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_password_service():
    service = MagicMock()
    service.validate_password_strength.return_value = True
    service.get_password_hash.return_value = "hashed_password_123"
    service.verify_password.return_value = True
    service.is_password_in_history.return_value = False
    service.add_password_to_history.return_value = None
    return service


@pytest.fixture
def mock_session_service():
    service = MagicMock()
    service.revoke_all_user_sessions = AsyncMock(return_value=0)
    return service


@pytest.fixture
def user_management_service(mock_db, mock_password_service, mock_session_service):
    with (
        patch(
            "src.services.core.user_management_service.PasswordService",
            return_value=mock_password_service,
        ),
        patch(
            "src.services.core.user_management_service.AsyncSessionService",
            return_value=mock_session_service,
        ),
    ):
        service = AsyncUserManagementService(mock_db)
        service.rbac_service.assign_role_to_user = AsyncMock()
        service.rbac_service.get_user_roles = AsyncMock(return_value=[])
        service.rbac_service.revoke_role_from_user = AsyncMock()
        return service


@pytest.fixture
def sample_user():
    return User(
        id="user_123",
        username="testuser",
        email="test@example.com",
        phone="13800001000",
        full_name="Test User",
        password_hash="hashed_password",
        is_active=True,
        is_locked=False,
        failed_login_attempts=0,
        default_organization_id="org_123",
    )


@pytest.fixture
def sample_user_create():
    return UserCreate(
        username="newuser",
        email="newuser@example.com",
        phone="13800001001",
        full_name="New User",
        password="SecurePass123!",
        role_id="role-user-id",
        default_organization_id="org_456",
    )


@pytest.fixture
def sample_user_update():
    return UserUpdate(
        email="updated@example.com",
        full_name="Updated Name",
        role_id="role-admin-id",
    )


# ===================== User Lookup Tests =====================


class TestUserLookupMethods:
    async def test_get_user_by_id_found(self, user_management_service, mock_db, sample_user):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await user_management_service.get_user_by_id("user_123")

        assert result == sample_user
        mock_db.execute.assert_awaited_once()

    async def test_get_user_by_id_not_found(self, user_management_service, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        result = await user_management_service.get_user_by_id("nonexistent")

        assert result is None

    async def test_get_user_by_username_found(
        self, user_management_service, mock_db, sample_user
    ):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await user_management_service.get_user_by_username("testuser")

        assert result == sample_user

    async def test_get_user_by_username_not_found(self, user_management_service, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        result = await user_management_service.get_user_by_username("nonexistent")

        assert result is None

    async def test_get_user_by_email_found(
        self, user_management_service, mock_db, sample_user
    ):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await user_management_service.get_user_by_email("test@example.com")

        assert result == sample_user

    async def test_get_user_by_email_not_found(self, user_management_service, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        result = await user_management_service.get_user_by_email("none@example.com")

        assert result is None


# ===================== User Creation Tests =====================


class TestUserCreation:
    async def test_create_user_success(
        self,
        user_management_service,
        mock_db,
        sample_user_create,
        mock_password_service,
    ):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        await user_management_service.create_user(sample_user_create)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

        mock_password_service.validate_password_strength.assert_called_once_with(
            sample_user_create.password
        )
        mock_password_service.get_password_hash.assert_called_once_with(
            sample_user_create.password
        )
        mock_password_service.add_password_to_history.assert_called_once()

    async def test_create_user_duplicate_username(
        self, user_management_service, mock_db, sample_user_create
    ):
        existing_user = User(
            id="existing_123",
            username="newuser",
            email="different@example.com",
            full_name="Existing User",
            password_hash="hash",
        )
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(existing_user))

        with pytest.raises(BusinessLogicError) as exc_info:
            await user_management_service.create_user(sample_user_create)

        assert "用户名已存在" in str(exc_info.value)
        mock_db.add.assert_not_called()

    async def test_create_user_duplicate_email(
        self, user_management_service, mock_db, sample_user_create
    ):
        existing_user = User(
            id="existing_123",
            username="different_user",
            email="newuser@example.com",
            full_name="Existing User",
            password_hash="hash",
        )
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(existing_user))

        with pytest.raises(BusinessLogicError) as exc_info:
            await user_management_service.create_user(sample_user_create)

        assert "邮箱已存在" in str(exc_info.value)
        mock_db.add.assert_not_called()

    async def test_create_user_weak_password(
        self,
        user_management_service,
        mock_db,
        mock_password_service,
    ):
        weak_password_data = UserCreate(
            username="weakuser",
            email="weak@example.com",
            phone="13800001002",
            full_name="Weak User",
            password="WeakPass123!",
        )
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))
        mock_password_service.validate_password_strength.return_value = False

        with pytest.raises(BusinessLogicError) as exc_info:
            await user_management_service.create_user(weak_password_data)

        assert "密码不符合安全要求" in str(exc_info.value)
        mock_db.add.assert_not_called()

    async def test_create_user_with_all_fields(
        self,
        user_management_service,
        mock_db,
        sample_user_create,
    ):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        await user_management_service.create_user(sample_user_create)

        mock_db.add.assert_called_once()
        added_user = mock_db.add.call_args[0][0]
        assert added_user.username == sample_user_create.username
        assert added_user.email == sample_user_create.email
        assert added_user.phone == sample_user_create.phone
        assert added_user.full_name == sample_user_create.full_name
        assert (
            added_user.default_organization_id
            == sample_user_create.default_organization_id
        )

    async def test_create_user_without_optional_fields(
        self, user_management_service, mock_db
    ):
        user_data = UserCreate(
            username="basicuser",
            email="basic@example.com",
            phone="13800001003",
            full_name="Basic User",
            password="SecurePass123!",
        )
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        await user_management_service.create_user(user_data)

        mock_db.add.assert_called_once()
        added_user = mock_db.add.call_args[0][0]
        assert added_user.phone == user_data.phone
        assert added_user.default_organization_id is None


# ===================== User Update Tests =====================


class TestUserUpdate:
    async def test_update_user_success(
        self, user_management_service, mock_db, sample_user, sample_user_update
    ):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_first(sample_user),
                _mock_execute_first(None),
            ]
        )

        result = await user_management_service.update_user(
            "user_123", sample_user_update
        )

        assert result == sample_user
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    async def test_update_user_not_found(
        self, user_management_service, mock_db, sample_user_update
    ):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        result = await user_management_service.update_user(
            "nonexistent", sample_user_update
        )

        assert result is None
        mock_db.commit.assert_not_awaited()

    async def test_update_user_email_duplicate(
        self, user_management_service, mock_db, sample_user, sample_user_update
    ):
        duplicate_user = User(
            id="other_user",
            username="other",
            email="updated@example.com",
            full_name="Other",
            password_hash="hash",
        )
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_first(sample_user),
                _mock_execute_first(duplicate_user),
            ]
        )

        with pytest.raises(BusinessLogicError) as exc_info:
            await user_management_service.update_user("user_123", sample_user_update)

        assert "邮箱已被其他用户使用" in str(exc_info.value)

    async def test_update_user_same_email(
        self, user_management_service, mock_db, sample_user
    ):
        update_data = UserUpdate(email="test@example.com")
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await user_management_service.update_user("user_123", update_data)

        assert result == sample_user
        mock_db.commit.assert_awaited_once()
        mock_db.execute.assert_awaited_once()

    async def test_update_user_partial_fields(
        self, user_management_service, mock_db, sample_user
    ):
        update_data = UserUpdate(full_name="New Name Only")
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await user_management_service.update_user("user_123", update_data)

        assert result == sample_user
        assert sample_user.full_name == "New Name Only"
        mock_db.commit.assert_awaited_once()

    async def test_update_user_updates_timestamp(
        self, user_management_service, mock_db, sample_user
    ):
        update_data = UserUpdate(full_name="Updated")
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        await user_management_service.update_user("user_123", update_data)

        assert sample_user.updated_at is not None

    async def test_update_with_no_changes(
        self, user_management_service, mock_db, sample_user
    ):
        update_data = UserUpdate()
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await user_management_service.update_user("user_123", update_data)

        assert result == sample_user
        mock_db.commit.assert_awaited_once()


# ===================== User Deactivation Tests =====================


class TestUserDeactivation:
    async def test_deactivate_user_success(
        self, user_management_service, mock_db, sample_user, mock_session_service
    ):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))
        mock_session_service.revoke_all_user_sessions.return_value = 1

        result = await user_management_service.deactivate_user("user_123")

        assert result is True
        assert sample_user.is_active is False
        mock_db.commit.assert_awaited_once()
        mock_session_service.revoke_all_user_sessions.assert_awaited_once_with(
            "user_123"
        )

    async def test_deactivate_user_not_found(self, user_management_service, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        result = await user_management_service.deactivate_user("nonexistent")

        assert result is False
        mock_db.commit.assert_not_awaited()

    async def test_deactivate_user_updates_timestamp(
        self, user_management_service, mock_db, sample_user
    ):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        await user_management_service.deactivate_user("user_123")

        assert sample_user.updated_at is not None


# ===================== User Activation Tests =====================


class TestUserActivation:
    async def test_activate_user_success(
        self, user_management_service, mock_db, sample_user
    ):
        sample_user.is_active = False
        sample_user.is_locked = True
        sample_user.failed_login_attempts = 5
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await user_management_service.activate_user("user_123")

        assert result is True
        assert sample_user.is_active is True
        assert sample_user.is_locked is False
        assert sample_user.failed_login_attempts == 0
        assert sample_user.locked_until is None
        mock_db.commit.assert_awaited_once()

    async def test_activate_user_not_found(self, user_management_service, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        result = await user_management_service.activate_user("nonexistent")

        assert result is False
        mock_db.commit.assert_not_awaited()

    async def test_activate_user_already_active(
        self, user_management_service, mock_db, sample_user
    ):
        sample_user.is_active = True
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await user_management_service.activate_user("user_123")

        assert result is True
        assert sample_user.is_active is True


# ===================== User Unlock Tests =====================


class TestUserUnlock:
    async def test_unlock_user_success(
        self, user_management_service, mock_db, sample_user
    ):
        sample_user.is_locked = True
        sample_user.locked_until = datetime.now()
        sample_user.failed_login_attempts = 5
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await user_management_service.unlock_user("user_123")

        assert result is True
        assert sample_user.is_locked is False
        assert sample_user.locked_until is None
        assert sample_user.failed_login_attempts == 0
        mock_db.commit.assert_awaited_once()

    async def test_unlock_user_not_found(self, user_management_service, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        result = await user_management_service.unlock_user("nonexistent")

        assert result is False
        mock_db.commit.assert_not_awaited()

    async def test_unlock_user_already_unlocked(
        self, user_management_service, mock_db, sample_user
    ):
        sample_user.is_locked = False
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await user_management_service.unlock_user("user_123")

        assert result is True
        assert sample_user.is_locked is False


# ===================== Password Change Tests =====================


class TestPasswordChange:
    async def test_change_password_success(
        self,
        user_management_service,
        sample_user,
        mock_password_service,
        mock_session_service,
        mock_db,
    ):
        mock_password_service.verify_password.return_value = True
        mock_password_service.validate_password_strength.return_value = True
        mock_password_service.is_password_in_history.return_value = False
        mock_password_service.get_password_hash.return_value = "new_hash"

        result = await user_management_service.change_password(
            sample_user, "OldPass123!", "NewPass456!"
        )

        assert result is True
        assert sample_user.password_hash == "new_hash"
        mock_password_service.verify_password.assert_called_once()
        mock_password_service.validate_password_strength.assert_called_once()
        mock_password_service.is_password_in_history.assert_called_once()
        mock_password_service.get_password_hash.assert_called_once_with("NewPass456!")
        mock_password_service.add_password_to_history.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_session_service.revoke_all_user_sessions.assert_awaited_once_with(
            sample_user.id
        )

    async def test_change_password_wrong_current_password(
        self, user_management_service, sample_user, mock_password_service
    ):
        mock_password_service.verify_password.return_value = False

        with pytest.raises(BusinessLogicError) as exc_info:
            await user_management_service.change_password(
                sample_user, "WrongPass123!", "NewPass456!"
            )

        assert "当前密码不正确" in str(exc_info.value)

    async def test_change_password_weak_new_password(
        self, user_management_service, sample_user, mock_password_service
    ):
        mock_password_service.verify_password.return_value = True
        mock_password_service.validate_password_strength.return_value = False

        with pytest.raises(BusinessLogicError) as exc_info:
            await user_management_service.change_password(
                sample_user, "OldPass123!", "weak"
            )

        assert "新密码不符合安全要求" in str(exc_info.value)

    async def test_change_password_reused_password(
        self, user_management_service, sample_user, mock_password_service
    ):
        mock_password_service.verify_password.return_value = True
        mock_password_service.validate_password_strength.return_value = True
        mock_password_service.is_password_in_history.return_value = True

        with pytest.raises(BusinessLogicError) as exc_info:
            await user_management_service.change_password(
                sample_user, "OldPass123!", "OldPass123!"
            )

        assert "新密码不能与最近使用过的密码相同" in str(exc_info.value)


# ===================== Edge Cases and Error Handling =====================


class TestEdgeCases:
    async def test_create_user_database_error(
        self,
        user_management_service,
        mock_db,
        sample_user_create,
    ):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))
        mock_db.commit.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            await user_management_service.create_user(sample_user_create)

        assert "Database error" in str(exc_info.value)

    async def test_update_user_database_error(
        self, user_management_service, mock_db, sample_user
    ):
        update_data = UserUpdate(full_name="Updated")
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))
        mock_db.commit.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            await user_management_service.update_user("user_123", update_data)

        assert "Database error" in str(exc_info.value)

    async def test_deactivate_user_database_error(
        self, user_management_service, mock_db, sample_user
    ):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))
        mock_db.commit.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            await user_management_service.deactivate_user("user_123")

        assert "Database error" in str(exc_info.value)

    async def test_create_user_with_admin_role(
        self, user_management_service, mock_db
    ):
        user_data = UserCreate(
            username="admin",
            email="admin@example.com",
            phone="13800001004",
            full_name="Admin User",
            password="AdminPass123!",
            role_id="role-admin-id",
        )
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        await user_management_service.create_user(user_data)

        mock_db.add.assert_called_once()
        user_management_service.rbac_service.assign_role_to_user.assert_awaited()
        assignment_call = user_management_service.rbac_service.assign_role_to_user.call_args
        assignment_data = assignment_call.kwargs.get("assignment_data")
        assert assignment_data is not None
        assert assignment_data.role_id == "role-admin-id"

    async def test_multiple_operations_on_same_user(
        self, user_management_service, mock_db, sample_user
    ):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_first(sample_user),
                _mock_execute_first(sample_user),
                _mock_execute_first(sample_user),
            ]
        )

        await user_management_service.activate_user("user_123")
        assert sample_user.is_active is True

        await user_management_service.deactivate_user("user_123")
        assert sample_user.is_active is False

        await user_management_service.activate_user("user_123")
        assert sample_user.is_active is True
