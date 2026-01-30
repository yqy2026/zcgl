"""
Comprehensive Unit Tests for UserManagementService

Tests cover:
1. User creation and validation
2. User update operations
3. User deactivation/deletion
4. Email/username uniqueness checks
5. User lookup methods
6. Password management
7. Error handling

Total: 43 comprehensive tests
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.exceptions import BusinessLogicError
from src.models.auth import User, UserRole
from src.schemas.auth import UserCreate, UserUpdate
from src.services.core.user_management_service import UserManagementService

# ===================== Fixtures =====================




@pytest.fixture
def mock_password_service():
    """Mock password service"""
    with patch("src.services.core.user_management_service.PasswordService") as mock:
        password_service = mock.return_value
        password_service.validate_password_strength.return_value = True
        password_service.get_password_hash.return_value = "hashed_password_123"
        password_service.verify_password.return_value = True
        password_service.is_password_in_history.return_value = False
        yield password_service


@pytest.fixture
def mock_session_service():
    """Mock session service"""
    with patch("src.services.core.user_management_service.SessionService") as mock:
        session_service = mock.return_value
        session_service.revoke_all_user_sessions.return_value = 0
        yield session_service


@pytest.fixture
def user_management_service(mock_db, mock_password_service, mock_session_service):
    """Create user management service instance"""
    with (
        patch(
            "src.services.core.user_management_service.PasswordService",
            return_value=mock_password_service,
        ),
        patch(
            "src.services.core.user_management_service.SessionService",
            return_value=mock_session_service,
        ),
    ):
        return UserManagementService(mock_db)


@pytest.fixture
def sample_user():
    """Create sample user object"""
    user = User(
        id="user_123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password_hash="hashed_password",
        role=UserRole.USER.value,
        is_active=True,
        is_locked=False,
        failed_login_attempts=0,
        employee_id="emp_123",
        default_organization_id="org_123",
    )
    return user


@pytest.fixture
def sample_user_create():
    """Create sample user creation data"""
    return UserCreate(
        username="newuser",
        email="newuser@example.com",
        full_name="New User",
        password="SecurePass123!",
        role=UserRole.USER,
        employee_id="emp_456",
        default_organization_id="org_456",
    )


@pytest.fixture
def sample_user_update():
    """Create sample user update data"""
    return UserUpdate(
        email="updated@example.com",
        full_name="Updated Name",
        role=UserRole.ADMIN,
    )


# ===================== User Lookup Tests =====================


class TestUserLookupMethods:
    """Test user lookup methods"""

    def test_get_user_by_id_found(self, user_management_service, mock_db, sample_user):
        """Test get_user_by_id when user exists"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        result = user_management_service.get_user_by_id("user_123")

        assert result == sample_user
        mock_db.query.assert_called_once_with(User)
        mock_db.query.return_value.filter.assert_called_once()

    def test_get_user_by_id_not_found(self, user_management_service, mock_db):
        """Test get_user_by_id when user doesn't exist"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = user_management_service.get_user_by_id("nonexistent")

        assert result is None

    def test_get_user_by_username_found(
        self, user_management_service, mock_db, sample_user
    ):
        """Test get_user_by_username when user exists"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        result = user_management_service.get_user_by_username("testuser")

        assert result == sample_user

    def test_get_user_by_username_not_found(self, user_management_service, mock_db):
        """Test get_user_by_username when user doesn't exist"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = user_management_service.get_user_by_username("nonexistent")

        assert result is None

    def test_get_user_by_email_found(
        self, user_management_service, mock_db, sample_user
    ):
        """Test get_user_by_email when user exists"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        result = user_management_service.get_user_by_email("test@example.com")

        assert result == sample_user

    def test_get_user_by_email_not_found(self, user_management_service, mock_db):
        """Test get_user_by_email when user doesn't exist"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = user_management_service.get_user_by_email("nonexistent@example.com")

        assert result is None


# ===================== User Creation Tests =====================


class TestUserCreation:
    """Test user creation functionality"""

    def test_create_user_success(
        self,
        user_management_service,
        mock_db,
        sample_user_create,
        mock_password_service,
    ):
        """Test successful user creation"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        user_management_service.create_user(sample_user_create)

        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        # Verify password operations
        mock_password_service.validate_password_strength.assert_called_once_with(
            sample_user_create.password
        )
        mock_password_service.get_password_hash.assert_called_once_with(
            sample_user_create.password
        )
        mock_password_service.add_password_to_history.assert_called_once()

    def test_create_user_duplicate_username(
        self, user_management_service, mock_db, sample_user_create
    ):
        """Test user creation with duplicate username"""
        # Mock existing user with same username
        existing_user = User(
            id="existing_123",
            username="newuser",  # Same username as sample_user_create
            email="different@example.com",  # Different email
            full_name="Existing User",
            password_hash="hash",
            role=UserRole.USER.value,
        )
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = existing_user

        with pytest.raises(BusinessLogicError) as exc_info:
            user_management_service.create_user(sample_user_create)

        assert "用户名已存在" in str(exc_info.value)
        mock_db.add.assert_not_called()

    def test_create_user_duplicate_email(
        self, user_management_service, mock_db, sample_user_create
    ):
        """Test user creation with duplicate email"""
        # Create user with same email but different username
        existing_user = User(
            id="existing_123",
            username="different_user",
            email="newuser@example.com",  # Same email
            full_name="Existing User",
            password_hash="hash",
            role=UserRole.USER.value,
        )
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = existing_user

        with pytest.raises(BusinessLogicError) as exc_info:
            user_management_service.create_user(sample_user_create)

        assert "邮箱已存在" in str(exc_info.value)
        mock_db.add.assert_not_called()

    def test_create_user_weak_password(
        self,
        user_management_service,
        mock_db,
        mock_password_service,
    ):
        """Test user creation with weak password"""
        # Create valid password data, but mock validate_password_strength to return False
        weak_password_data = UserCreate(
            username="weakuser",
            email="weak@example.com",
            full_name="Weak User",
            password="WeakPass123!",  # Valid format, but we'll mock it as weak
        )
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None
        # Mock the service to reject this password
        mock_password_service.validate_password_strength.return_value = False

        with pytest.raises(BusinessLogicError) as exc_info:
            user_management_service.create_user(weak_password_data)

        assert "密码不符合安全要求" in str(exc_info.value)
        mock_db.add.assert_not_called()

    def test_create_user_with_all_fields(
        self,
        user_management_service,
        mock_db,
        sample_user_create,
        mock_password_service,
    ):
        """Test user creation with all optional fields"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        user_management_service.create_user(sample_user_create)

        # Verify all fields were set
        mock_db.add.assert_called_once()
        added_user = mock_db.add.call_args[0][0]
        assert added_user.username == sample_user_create.username
        assert added_user.email == sample_user_create.email
        assert added_user.full_name == sample_user_create.full_name
        assert added_user.role == sample_user_create.role
        assert added_user.employee_id == sample_user_create.employee_id
        assert (
            added_user.default_organization_id
            == sample_user_create.default_organization_id
        )

    def test_create_user_without_optional_fields(
        self, user_management_service, mock_db, mock_password_service
    ):
        """Test user creation without optional fields"""
        user_data = UserCreate(
            username="basicuser",
            email="basic@example.com",
            full_name="Basic User",
            password="SecurePass123!",
        )
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        user_management_service.create_user(user_data)

        # Verify user created with None for optional fields
        mock_db.add.assert_called_once()
        added_user = mock_db.add.call_args[0][0]
        assert added_user.employee_id is None
        assert added_user.default_organization_id is None


# ===================== User Update Tests =====================


class TestUserUpdate:
    """Test user update functionality"""

    def test_update_user_success(
        self, user_management_service, mock_db, sample_user, sample_user_update
    ):
        """Test successful user update"""
        # Setup mock query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.side_effect = [sample_user, None, None]

        result = user_management_service.update_user("user_123", sample_user_update)

        assert result == sample_user
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_update_user_not_found(
        self, user_management_service, mock_db, sample_user_update
    ):
        """Test update when user doesn't exist"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        result = user_management_service.update_user("nonexistent", sample_user_update)

        assert result is None
        mock_db.commit.assert_not_called()

    def test_update_user_email_duplicate(
        self, user_management_service, mock_db, sample_user, sample_user_update
    ):
        """Test update with duplicate email"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.side_effect = [
            sample_user,  # First call: get user by id
            User(  # Second call: email already exists
                id="other_user",
                username="other",
                email="updated@example.com",
                full_name="Other",
                password_hash="hash",
                role=UserRole.USER.value,
            ),
        ]

        with pytest.raises(BusinessLogicError) as exc_info:
            user_management_service.update_user("user_123", sample_user_update)

        assert "邮箱已被其他用户使用" in str(exc_info.value)

    def test_update_user_username_duplicate(
        self, user_management_service, mock_db, sample_user
    ):
        """Test update with duplicate username"""
        # UserUpdate doesn't have username field, so this test validates that
        # the update_data.model_dump() correctly excludes username and doesn't trigger
        # username uniqueness check
        update_data = UserUpdate(full_name="Updated Name")
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.side_effect = [sample_user, None]

        result = user_management_service.update_user("user_123", update_data)

        # Should succeed without triggering username check since UserUpdate has no username field
        assert result == sample_user
        mock_db.commit.assert_called_once()

    def test_update_user_same_email(
        self, user_management_service, mock_db, sample_user
    ):
        """Test update with same email (no duplicate check needed)"""
        update_data = UserUpdate(email="test@example.com")  # Same email
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.side_effect = [sample_user, None]

        result = user_management_service.update_user("user_123", update_data)

        assert result == sample_user
        mock_db.commit.assert_called_once()

    def test_update_user_same_username(
        self, user_management_service, mock_db, sample_user
    ):
        """Test update with same username (no duplicate check needed)"""
        update_data = UserUpdate(username="testuser")  # Same username
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.side_effect = [sample_user, None, None]

        result = user_management_service.update_user("user_123", update_data)

        assert result == sample_user
        mock_db.commit.assert_called_once()

    def test_update_user_partial_fields(
        self, user_management_service, mock_db, sample_user
    ):
        """Test update with only some fields"""
        update_data = UserUpdate(full_name="New Name Only")
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.side_effect = [sample_user, None, None]

        result = user_management_service.update_user("user_123", update_data)

        assert result == sample_user
        assert sample_user.full_name == "New Name Only"
        mock_db.commit.assert_called_once()

    def test_update_user_updates_timestamp(
        self, user_management_service, mock_db, sample_user
    ):
        """Test that update_user updates the updated_at timestamp"""
        update_data = UserUpdate(full_name="Updated")
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.side_effect = [sample_user, None, None]

        user_management_service.update_user("user_123", update_data)

        assert sample_user.updated_at is not None


# ===================== User Deactivation Tests =====================


class TestUserDeactivation:
    """Test user deactivation functionality"""

    def test_deactivate_user_success(
        self, user_management_service, mock_db, sample_user, mock_session_service
    ):
        """Test successful user deactivation"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = sample_user
        mock_session_service.revoke_all_user_sessions.return_value = 1

        result = user_management_service.deactivate_user("user_123")

        assert result is True
        assert sample_user.is_active is False
        assert mock_db.commit.call_count >= 1
        mock_session_service.revoke_all_user_sessions.assert_called_once_with(
            "user_123"
        )

    def test_deactivate_user_not_found(self, user_management_service, mock_db):
        """Test deactivation when user doesn't exist"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        result = user_management_service.deactivate_user("nonexistent")

        assert result is False
        mock_db.commit.assert_not_called()

    def test_deactivate_user_updates_timestamp(
        self, user_management_service, mock_db, sample_user, mock_session_service
    ):
        """Test that deactivation updates timestamp"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = sample_user
        mock_session_service.revoke_all_user_sessions.return_value = 0

        user_management_service.deactivate_user("user_123")

        assert sample_user.updated_at is not None


# ===================== User Activation Tests =====================


class TestUserActivation:
    """Test user activation functionality"""

    def test_activate_user_success(self, user_management_service, mock_db, sample_user):
        """Test successful user activation"""
        sample_user.is_active = False
        sample_user.is_locked = True
        sample_user.failed_login_attempts = 5
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = sample_user

        result = user_management_service.activate_user("user_123")

        assert result is True
        assert sample_user.is_active is True
        assert sample_user.is_locked is False
        assert sample_user.failed_login_attempts == 0
        assert sample_user.locked_until is None
        mock_db.commit.assert_called_once()

    def test_activate_user_not_found(self, user_management_service, mock_db):
        """Test activation when user doesn't exist"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        result = user_management_service.activate_user("nonexistent")

        assert result is False
        mock_db.commit.assert_not_called()

    def test_activate_user_already_active(
        self, user_management_service, mock_db, sample_user
    ):
        """Test activation of already active user"""
        sample_user.is_active = True
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = sample_user

        result = user_management_service.activate_user("user_123")

        assert result is True
        assert sample_user.is_active is True

    def test_activate_unlocks_locked_user(
        self, user_management_service, mock_db, sample_user
    ):
        """Test that activation unlocks a locked user"""
        sample_user.is_locked = True
        sample_user.locked_until = datetime.now()
        sample_user.failed_login_attempts = 3
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = sample_user

        user_management_service.activate_user("user_123")

        assert sample_user.is_locked is False
        assert sample_user.locked_until is None
        assert sample_user.failed_login_attempts == 0


# ===================== User Unlock Tests =====================


class TestUserUnlock:
    """Test user unlock functionality"""

    def test_unlock_user_success(self, user_management_service, mock_db, sample_user):
        """Test successful user unlock"""
        sample_user.is_locked = True
        sample_user.locked_until = datetime.now()
        sample_user.failed_login_attempts = 5
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = sample_user

        result = user_management_service.unlock_user("user_123")

        assert result is True
        assert sample_user.is_locked is False
        assert sample_user.locked_until is None
        assert sample_user.failed_login_attempts == 0
        mock_db.commit.assert_called_once()

    def test_unlock_user_not_found(self, user_management_service, mock_db):
        """Test unlock when user doesn't exist"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        result = user_management_service.unlock_user("nonexistent")

        assert result is False
        mock_db.commit.assert_not_called()

    def test_unlock_user_already_unlocked(
        self, user_management_service, mock_db, sample_user
    ):
        """Test unlock of already unlocked user"""
        sample_user.is_locked = False
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = sample_user

        result = user_management_service.unlock_user("user_123")

        assert result is True
        assert sample_user.is_locked is False

    def test_unlock_user_clears_failed_attempts(
        self, user_management_service, mock_db, sample_user
    ):
        """Test that unlock clears failed login attempts"""
        sample_user.is_locked = True
        sample_user.failed_login_attempts = 10
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = sample_user

        user_management_service.unlock_user("user_123")

        assert sample_user.failed_login_attempts == 0


# ===================== Password Change Tests =====================


class TestPasswordChange:
    """Test password change functionality"""

    def test_change_password_success(
        self,
        user_management_service,
        sample_user,
        mock_password_service,
        mock_session_service,
    ):
        """Test successful password change"""
        mock_password_service.verify_password.return_value = True
        mock_password_service.validate_password_strength.return_value = True
        mock_password_service.is_password_in_history.return_value = False

        result = user_management_service.change_password(
            sample_user, "OldPass123!", "NewPass456!"
        )

        assert result is True
        mock_password_service.verify_password.assert_called_once()
        mock_password_service.validate_password_strength.assert_called_once()
        mock_password_service.is_password_in_history.assert_called_once()
        mock_password_service.get_password_hash.assert_called_once_with("NewPass456!")
        mock_session_service.revoke_all_user_sessions.assert_called_once_with(
            sample_user.id
        )

    def test_change_password_wrong_current_password(
        self, user_management_service, sample_user, mock_password_service
    ):
        """Test password change with wrong current password"""
        mock_password_service.verify_password.return_value = False

        with pytest.raises(BusinessLogicError) as exc_info:
            user_management_service.change_password(
                sample_user, "WrongPass123!", "NewPass456!"
            )

        assert "当前密码不正确" in str(exc_info.value)

    def test_change_password_weak_new_password(
        self, user_management_service, sample_user, mock_password_service
    ):
        """Test password change with weak new password"""
        mock_password_service.verify_password.return_value = True
        mock_password_service.validate_password_strength.return_value = False

        with pytest.raises(BusinessLogicError) as exc_info:
            user_management_service.change_password(sample_user, "OldPass123!", "weak")

        assert "新密码不符合安全要求" in str(exc_info.value)

    def test_change_password_reused_password(
        self, user_management_service, sample_user, mock_password_service
    ):
        """Test password change with reused password from history"""
        mock_password_service.verify_password.return_value = True
        mock_password_service.validate_password_strength.return_value = True
        mock_password_service.is_password_in_history.return_value = True

        with pytest.raises(BusinessLogicError) as exc_info:
            user_management_service.change_password(
                sample_user, "OldPass123!", "OldPass123!"
            )

        assert "新密码不能与最近使用过的密码相同" in str(exc_info.value)

    def test_change_password_adds_to_history(
        self,
        user_management_service,
        sample_user,
        mock_password_service,
        mock_session_service,
    ):
        """Test that password change adds new password to history"""
        mock_password_service.verify_password.return_value = True
        mock_password_service.validate_password_strength.return_value = True
        mock_password_service.is_password_in_history.return_value = False
        mock_password_service.get_password_hash.return_value = "new_hash"

        user_management_service.change_password(
            sample_user, "OldPass123!", "NewPass456!"
        )

        mock_password_service.add_password_to_history.assert_called_once()

    def test_change_password_revokes_sessions(
        self,
        user_management_service,
        sample_user,
        mock_password_service,
        mock_session_service,
    ):
        """Test that password change revokes all sessions"""
        mock_password_service.verify_password.return_value = True
        mock_password_service.validate_password_strength.return_value = True
        mock_password_service.is_password_in_history.return_value = False

        user_management_service.change_password(
            sample_user, "OldPass123!", "NewPass456!"
        )

        mock_session_service.revoke_all_user_sessions.assert_called_once_with(
            sample_user.id
        )


# ===================== Edge Cases and Error Handling =====================


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_create_user_database_error(
        self,
        user_management_service,
        mock_db,
        sample_user_create,
        mock_password_service,
    ):
        """Test handling of database error during user creation"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None
        mock_db.commit.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            user_management_service.create_user(sample_user_create)

        assert "Database error" in str(exc_info.value)

    def test_update_user_database_error(
        self, user_management_service, mock_db, sample_user
    ):
        """Test handling of database error during user update"""
        update_data = UserUpdate(full_name="Updated")
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = sample_user
        mock_db.commit.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            user_management_service.update_user("user_123", update_data)

        assert "Database error" in str(exc_info.value)

    def test_deactivate_user_database_error(
        self, user_management_service, mock_db, sample_user
    ):
        """Test handling of database error during deactivation"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = sample_user
        mock_db.commit.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            user_management_service.deactivate_user("user_123")

        assert "Database error" in str(exc_info.value)

    def test_update_with_no_changes(
        self, user_management_service, mock_db, sample_user
    ):
        """Test update with no actual changes (empty update data)"""
        update_data = UserUpdate()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = sample_user

        result = user_management_service.update_user("user_123", update_data)

        assert result == sample_user
        mock_db.commit.assert_called_once()

    def test_create_user_with_admin_role(
        self, user_management_service, mock_db, mock_password_service
    ):
        """Test creating user with admin role"""
        user_data = UserCreate(
            username="admin",
            email="admin@example.com",
            full_name="Admin User",
            password="AdminPass123!",
            role=UserRole.ADMIN,
        )
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        user_management_service.create_user(user_data)

        mock_db.add.assert_called_once()
        added_user = mock_db.add.call_args[0][0]
        assert added_user.role == UserRole.ADMIN.value

    def test_multiple_operations_on_same_user(
        self, user_management_service, mock_db, sample_user
    ):
        """Test multiple operations on the same user object"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = sample_user

        # Activate user
        user_management_service.activate_user("user_123")
        assert sample_user.is_active is True

        # Deactivate user
        user_management_service.deactivate_user("user_123")
        assert sample_user.is_active is False

        # Activate again
        user_management_service.activate_user("user_123")
        assert sample_user.is_active is True
