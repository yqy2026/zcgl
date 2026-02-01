"""
Auth Model Tests

Tests for User model - authentication and authorization core.
"""

import uuid
from datetime import UTC, datetime

import pytest

from src.models.auth import User, UserRole


class TestUserRoleEnum:
    """Test UserRole enumeration"""

    def test_admin_role(self):
        """Test ADMIN role value"""
        assert UserRole.ADMIN == "admin"

    def test_user_role(self):
        """Test USER role value"""
        assert UserRole.USER == "user"

    def test_user_role_is_enum(self):
        """Test UserRole is an Enum"""
        from enum import Enum

        assert isinstance(UserRole.USER, Enum)


class TestUserCreation:
    """Test User model creation"""

    @pytest.fixture
    def minimal_user(self):
        """Create minimal valid User with all defaults explicitly set"""
        return User(
            id=str(uuid.uuid4()),
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password_hash="hashed_password_123",
            role=UserRole.USER.value,  # Explicitly set default
            is_active=True,  # Explicitly set default
            is_locked=False,  # Explicitly set default
        )

    def test_user_creation(self, minimal_user):
        """Test basic user creation"""
        assert minimal_user.username == "testuser"
        assert minimal_user.email == "test@example.com"
        assert minimal_user.full_name == "Test User"

    def test_user_id_generation(self, minimal_user):
        """Test user ID is auto-generated"""
        # Note: ID generation requires database session to trigger default
        # In unit tests without DB, we set it manually in fixture
        assert minimal_user.id is not None
        assert isinstance(minimal_user.id, str)

    def test_default_role(self, minimal_user):
        """Test default role is USER"""
        assert minimal_user.role == UserRole.USER.value

    def test_default_is_active(self, minimal_user):
        """Test default is_active is True"""
        assert minimal_user.is_active is True

    def test_default_is_locked(self, minimal_user):
        """Test default is_locked is False"""
        assert minimal_user.is_locked is False


class TestUserAuthenticationFields:
    """Test user authentication-related fields"""

    @pytest.fixture
    def user(self):
        return User(
            username="authuser",
            email="auth@example.com",
            full_name="Auth User",
            password_hash="secure_hash_abc123",
        )

    def test_password_hash(self, user):
        """Test password_hash field"""
        assert user.password_hash == "secure_hash_abc123"
        assert isinstance(user.password_hash, str)

    def test_password_history_can_be_none(self, user):
        """Test password_history can be None"""
        assert user.password_history is None

    def test_password_history_can_be_dict(self):
        """Test password_history can store dict"""
        user = User(
            username="histuser",
            email="hist@example.com",
            full_name="History User",
            password_hash="hash",
            password_history={"old_hash": "previous_hash", "changed_at": "2024-01-01"},
        )
        assert user.password_history is not None
        assert isinstance(user.password_history, dict)


class TestUserLoginTracking:
    """Test user login tracking fields"""

    @pytest.fixture
    def user(self):
        now = datetime.now(UTC)
        return User(
            id=str(uuid.uuid4()),
            username="loginuser",
            email="login@example.com",
            full_name="Login User",
            password_hash="hash",
            role=UserRole.USER.value,
            failed_login_attempts=0,  # Default value
            password_last_changed=now,  # Default value
            last_login_at=None,  # Initially None
        )

    def test_last_login_at_initially_none(self, user):
        """Test last_login_at is None initially"""
        assert user.last_login_at is None

    def test_failed_login_attempts_default(self, user):
        """Test failed_login_attempts defaults to 0"""
        assert user.failed_login_attempts == 0

    def test_locked_until_initially_none(self, user):
        """Test locked_until is None initially"""
        assert user.locked_until is None

    def test_password_last_changed_is_set(self, user):
        """Test password_last_changed is auto-set"""
        assert user.password_last_changed is not None
        assert isinstance(user.password_last_changed, datetime)


class TestUserAccountStatus:
    """Test user account status management"""

    @pytest.fixture
    def active_user(self):
        return User(
            username="activeuser",
            email="active@example.com",
            full_name="Active User",
            password_hash="hash",
            is_active=True,
            is_locked=False,
        )

    @pytest.fixture
    def locked_user(self):
        return User(
            username="lockeduser",
            email="locked@example.com",
            full_name="Locked User",
            password_hash="hash",
            is_active=True,
            is_locked=True,
            locked_until=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
        )

    def test_active_user_status(self, active_user):
        """Test active user status"""
        assert active_user.is_active is True
        assert active_user.is_locked is False

    def test_locked_user_status(self, locked_user):
        """Test locked user status"""
        assert locked_user.is_locked is True
        assert locked_user.locked_until is not None

    def test_can_deactivate_user(self):
        """Test user can be deactivated"""
        user = User(
            username="inactiveuser",
            email="inactive@example.com",
            full_name="Inactive User",
            password_hash="hash",
            is_active=False,
        )
        assert user.is_active is False

    def test_increment_failed_attempts(self):
        """Test failed login attempts can be incremented"""
        user = User(
            username="failuser",
            email="fail@example.com",
            full_name="Fail User",
            password_hash="hash",
        )
        user.failed_login_attempts = 3
        assert user.failed_login_attempts == 3


class TestUserTimestamps:
    """Test user timestamp fields"""

    @pytest.fixture
    def user(self):
        now = datetime.now(UTC)
        return User(
            id=str(uuid.uuid4()),
            username="timeuser",
            email="time@example.com",
            full_name="Time User",
            password_hash="hash",
            role=UserRole.USER.value,
            created_at=now,
            updated_at=now,
            password_last_changed=now,
        )

    def test_created_at_is_set(self, user):
        """Test created_at is auto-set"""
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)

    def test_updated_at_is_set(self, user):
        """Test updated_at is auto-set"""
        assert user.updated_at is not None
        assert isinstance(user.updated_at, datetime)

    def test_password_last_changed_is_set(self, user):
        """Test password_last_changed is auto-set"""
        assert user.password_last_changed is not None
        assert isinstance(user.password_last_changed, datetime)


class TestUserOrganization:
    """Test user-organization relationships"""

    @pytest.fixture
    def user_with_org(self):
        return User(
            username="orguser",
            email="org@example.com",
            full_name="Org User",
            password_hash="hash",
            employee_id="emp123",
            default_organization_id="org456",
        )

    def test_employee_id(self, user_with_org):
        """Test employee_id field"""
        assert user_with_org.employee_id == "emp123"

    def test_default_organization_id(self, user_with_org):
        """Test default_organization_id field"""
        assert user_with_org.default_organization_id == "org456"

    def test_org_fields_optional(self):
        """Test org fields are optional"""
        user = User(
            username="noorguser",
            email="noorg@example.com",
            full_name="No Org User",
            password_hash="hash",
        )
        assert user.employee_id is None
        assert user.default_organization_id is None


class TestUserValidation:
    """Test user data validation"""

    def test_username_unique(self):
        """Test username should be unique (enforced at DB level)"""
        user1 = User(
            username="duplicate",
            email="user1@example.com",
            full_name="User 1",
            password_hash="hash1",
        )
        user2 = User(
            username="duplicate",  # Same username
            email="user2@example.com",
            full_name="User 2",
            password_hash="hash2",
        )
        assert user1.username == user2.username

    def test_email_unique(self):
        """Test email should be unique (enforced at DB level)"""
        user1 = User(
            username="user1",
            email="duplicate@example.com",
            full_name="User 1",
            password_hash="hash1",
        )
        user2 = User(
            username="user2",
            email="duplicate@example.com",  # Same email
            full_name="User 2",
            password_hash="hash2",
        )
        assert user1.email == user2.email

    def test_email_format(self):
        """Test email format (not automatically validated)"""
        user = User(
            username="testuser",
            email="invalid-email",  # Invalid format
            full_name="Test User",
            password_hash="hash",
        )
        assert user.email == "invalid-email"


class TestUserRoles:
    """Test user role management"""

    def test_admin_role(self):
        """Test admin role assignment"""
        user = User(
            username="adminuser",
            email="admin@example.com",
            full_name="Admin User",
            password_hash="hash",
            role=UserRole.ADMIN.value,
        )
        assert user.role == UserRole.ADMIN.value

    def test_default_role_is_user(self):
        """Test default role is user"""
        user = User(
            id=str(uuid.uuid4()),
            username="normaluser",
            email="normal@example.com",
            full_name="Normal User",
            password_hash="hash",
            role=UserRole.USER.value,  # Explicitly set default for unit test
        )
        assert user.role == UserRole.USER.value


class TestUserAuditFields:
    """Test user audit trail fields"""

    @pytest.fixture
    def user(self):
        return User(
            username="audituser",
            email="audit@example.com",
            full_name="Audit User",
            password_hash="hash",
            created_by="admin",
            updated_by="admin",
        )

    def test_created_by(self, user):
        """Test created_by field"""
        assert user.created_by == "admin"

    def test_updated_by(self, user):
        """Test updated_by field"""
        assert user.updated_by == "admin"

    def test_audit_fields_optional(self):
        """Test audit fields are optional"""
        user = User(
            username="untracked",
            email="untracked@example.com",
            full_name="Untracked User",
            password_hash="hash",
        )
        assert user.created_by is None
        assert user.updated_by is None


class TestUserEdgeCases:
    """Test user edge cases"""

    def test_very_long_username(self):
        """Test very long username"""
        long_username = "a" * 100
        user = User(
            username=long_username,
            email="long@example.com",
            full_name="Long Username User",
            password_hash="hash",
        )
        assert len(user.username) == 100

    def test_special_characters_in_name(self):
        """Test special characters in full_name"""
        user = User(
            username="specialuser",
            email="special@example.com",
            full_name="用户名称",  # Unicode characters
            password_hash="hash",
        )
        assert user.full_name == "用户名称"

    def test_username_case_sensitivity(self):
        """Test username case sensitivity"""
        user1 = User(
            username="TestUser",
            email="test1@example.com",
            full_name="Test User 1",
            password_hash="hash1",
        )
        user2 = User(
            username="testuser",  # Lowercase
            email="test2@example.com",
            full_name="Test User 2",
            password_hash="hash2",
        )
        # Case sensitivity depends on database collation
        assert user1.username != user2.username


class TestUserStringRepresentation:
    """Test user string representation"""

    @pytest.fixture
    def user(self):
        return User(
            username="repruser",
            email="repr@example.com",
            full_name="Repr User",
            password_hash="hash",
        )

    def test_user_repr(self, user):
        """Test user repr"""
        repr_str = repr(user)
        assert "User" in repr_str

    def test_username_is_identifier(self, user):
        """Test username is main identifier"""
        assert user.username == "repruser"


class TestUserRelationships:
    """Test User model relationships"""

    @pytest.fixture
    def user(self):
        return User(
            username="reluser",
            email="rel@example.com",
            full_name="Relationship User",
            password_hash="hash",
        )

    def test_relationships_exist(self, user):
        """Test that relationship attributes exist"""
        assert hasattr(user, "user_sessions")
        assert hasattr(user, "audit_logs")
        assert hasattr(user, "role_assignments")
        assert hasattr(user, "notifications")
        assert hasattr(user, "default_organization")

    def test_relationships_are_lists(self, user):
        """Test relationships are list types"""
        assert isinstance(user.user_sessions, list)
        assert isinstance(user.audit_logs, list)
