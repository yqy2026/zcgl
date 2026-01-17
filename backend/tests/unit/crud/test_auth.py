"""
Comprehensive unit tests for auth CRUD operations
Targeting 70%+ coverage for backend/src/crud/auth.py
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy.orm import Session

from src.crud.auth import AuditLogCRUD, UserCRUD, UserSessionCRUD
from src.models.auth import AuditLog, User, UserRole, UserSession
from src.schemas.auth import UserCreate, UserUpdate


# ===================== Fixtures =====================
@pytest.fixture
def mock_db():
    """Mock database session"""
    return MagicMock(spec=Session)


@pytest.fixture
def user_crud():
    """UserCRUD instance"""
    return UserCRUD()


@pytest.fixture
def session_crud():
    """UserSessionCRUD instance"""
    return UserSessionCRUD()


@pytest.fixture
def audit_crud():
    """AuditLogCRUD instance"""
    return AuditLogCRUD()


@pytest.fixture
def sample_user():
    """Sample user object"""
    user = User(
        id="user_123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password_hash="hashed_password_here",
        role=UserRole.USER,
        is_active=True,
        employee_id=None,
        default_organization_id=None,
    )
    return user


@pytest.fixture
def sample_session():
    """Sample user session object"""
    session = UserSession(
        id="session_123",
        user_id="user_123",
        refresh_token="refresh_token_value",
        device_info="Chrome on Windows",
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        is_active=True,
        expires_at=datetime.now() + timedelta(days=7),
    )
    return session


@pytest.fixture
def sample_audit_log():
    """Sample audit log object"""
    log = AuditLog(
        id="log_123",
        user_id="user_123",
        username="testuser",
        user_role=UserRole.USER.value,
        action="user_login",
        resource_type=None,
        resource_id=None,
        response_status=200,
    )
    return log


@pytest.fixture
def user_create_data():
    """User creation data"""
    return UserCreate(
        username="newuser",
        email="newuser@example.com",
        full_name="New User",
        password="SecurePass123!",
        role=UserRole.USER,
        employee_id=None,
        default_organization_id=None,
    )


@pytest.fixture
def user_update_data():
    """User update data"""
    return UserUpdate(
        email="updated@example.com",
        full_name="Updated Name",
        role=UserRole.ADMIN,
    )


# ===================== UserCRUD Tests =====================
class TestUserCRUD:
    """Test UserCRUD operations"""

    def test_get_user_by_id(self, user_crud, mock_db, sample_user):
        """Test getting user by ID"""
        # Setup mock query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user

        # Execute
        result = user_crud.get(mock_db, "user_123")

        # Verify
        assert result == sample_user
        mock_db.query.assert_called_once_with(User)
        mock_query.filter.assert_called_once()
        mock_query.first.assert_called_once()

    def test_get_user_by_id_not_found(self, user_crud, mock_db):
        """Test getting non-existent user returns None"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        result = user_crud.get(mock_db, "nonexistent")

        assert result is None

    def test_get_by_username(self, user_crud, mock_db, sample_user):
        """Test getting user by username"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user

        result = user_crud.get_by_username(mock_db, "testuser")

        assert result == sample_user
        mock_db.query.assert_called_once_with(User)

    def test_get_by_email(self, user_crud, mock_db, sample_user):
        """Test getting user by email"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user

        result = user_crud.get_by_email(mock_db, "test@example.com")

        assert result == sample_user
        mock_db.query.assert_called_once_with(User)

    def test_get_multi(self, user_crud, mock_db, sample_user):
        """Test getting multiple users with pagination"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_user]

        result = user_crud.get_multi(mock_db, skip=0, limit=10)

        assert result == [sample_user]
        mock_query.offset.assert_called_once_with(0)
        mock_query.limit.assert_called_once_with(10)

    def test_get_multi_with_filters_search(self, user_crud, mock_db, sample_user):
        """Test getting users with search filter"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_user]

        users, total = user_crud.get_multi_with_filters(
            mock_db, skip=0, limit=10, search="test"
        )

        assert users == [sample_user]
        assert total == 1
        # Verify filter was called for search
        assert mock_query.filter.called

    def test_get_multi_with_filters_role(self, user_crud, mock_db, sample_user):
        """Test getting users filtered by role"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_user]

        users, total = user_crud.get_multi_with_filters(
            mock_db, skip=0, limit=10, role=UserRole.USER
        )

        assert users == [sample_user]
        assert total == 1

    def test_get_multi_with_filters_is_active(self, user_crud, mock_db, sample_user):
        """Test getting users filtered by active status"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_user]

        users, total = user_crud.get_multi_with_filters(
            mock_db, skip=0, limit=10, is_active=True
        )

        assert users == [sample_user]
        assert total == 1

    def test_get_multi_with_filters_organization(
        self, user_crud, mock_db, sample_user
    ):
        """Test getting users filtered by organization"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_user]

        users, total = user_crud.get_multi_with_filters(
            mock_db, skip=0, limit=10, organization_id="org_123"
        )

        assert users == [sample_user]
        assert total == 1

    def test_create_user(self, user_crud, mock_db, user_create_data):
        """Test creating a new user with password hashing"""
        # Mock the database operations
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        # Execute
        result = user_crud.create(mock_db, user_create_data)

        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        # Verify returned user object
        assert result.username == user_create_data.username
        assert result.email == user_create_data.email
        assert result.full_name == user_create_data.full_name
        assert result.role == user_create_data.role
        assert hasattr(result, "password_hash")
        assert result.password_hash is not None

    def test_update_user(self, user_crud, mock_db, sample_user, user_update_data):
        """Test updating a user"""
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        result = user_crud.update(mock_db, sample_user, user_update_data)

        # Verify fields were updated
        assert result.email == user_update_data.email
        assert result.full_name == user_update_data.full_name
        assert result.role == user_update_data.role
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_delete_user_soft(self, user_crud, mock_db, sample_user):
        """Test soft deleting a user"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user
        mock_db.commit = MagicMock()

        result = user_crud.delete(mock_db, "user_123")

        assert result is True
        assert sample_user.is_active is False
        mock_db.commit.assert_called_once()

    def test_delete_user_not_found(self, user_crud, mock_db):
        """Test deleting non-existent user returns False"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        result = user_crud.delete(mock_db, "nonexistent")

        assert result is False

    def test_count_users(self, user_crud, mock_db):
        """Test counting total users"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.scalar.return_value = 42

        result = user_crud.count(mock_db)

        assert result == 42
        mock_db.query.assert_called_once()

    def test_count_users_none(self, user_crud, mock_db):
        """Test counting users when result is None"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.scalar.return_value = None

        result = user_crud.count(mock_db)

        assert result == 0

    def test_count_active_users(self, user_crud, mock_db):
        """Test counting active users"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 30

        result = user_crud.count_active(mock_db)

        assert result == 30
        mock_query.filter.assert_called_once()

    def test_count_by_role(self, user_crud, mock_db):
        """Test counting users by role"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 15

        result = user_crud.count_by_role(mock_db, UserRole.USER)

        assert result == 15
        mock_query.filter.assert_called_once()

    def test_get_recent_logins(self, user_crud, mock_db, sample_user):
        """Test getting recently logged in users"""
        sample_user.last_login_at = datetime.now()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_user]

        result = user_crud.get_recent_logins(mock_db, limit=10)

        assert result == [sample_user]
        mock_query.filter.assert_called_once()
        mock_query.order_by.assert_called_once()
        mock_query.limit.assert_called_once_with(10)

    def test_get_users_by_role(self, user_crud, mock_db, sample_user):
        """Test getting users filtered by role ID"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_user]

        users, total = user_crud.get_users_by_role(
            mock_db, role_id=UserRole.USER.value, skip=0, limit=10
        )

        assert users == [sample_user]
        assert total == 1


# ===================== UserSessionCRUD Tests =====================
class TestUserSessionCRUD:
    """Test UserSessionCRUD operations"""

    def test_get_session_by_id(self, session_crud, mock_db, sample_session):
        """Test getting session by ID"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_session

        result = session_crud.get(mock_db, "session_123")

        assert result == sample_session
        mock_db.query.assert_called_once_with(UserSession)

    def test_get_session_by_refresh_token(
        self, session_crud, mock_db, sample_session
    ):
        """Test getting session by refresh token"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_session

        result = session_crud.get_by_refresh_token(mock_db, "refresh_token_value")

        assert result == sample_session
        mock_db.query.assert_called_once_with(UserSession)

    def test_get_user_sessions_active_only(self, session_crud, mock_db, sample_session):
        """Test getting user's active sessions"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_session]

        result = session_crud.get_user_sessions(mock_db, "user_123", active_only=True)

        assert result == [sample_session]
        mock_query.order_by.assert_called_once()

    def test_get_user_sessions_all(self, session_crud, mock_db, sample_session):
        """Test getting all user sessions including inactive"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_session]

        result = session_crud.get_user_sessions(mock_db, "user_123", active_only=False)

        assert result == [sample_session]

    def test_create_session(self, session_crud, mock_db):
        """Test creating a new user session"""
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        result = session_crud.create(
            db=mock_db,
            user_id="user_123",
            refresh_token="new_refresh_token",
            device_info="Chrome",
            ip_address="192.168.1.1",
            user_agent="Mozilla",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert result.user_id == "user_123"
        assert result.refresh_token == "new_refresh_token"

    def test_deactivate_session(self, session_crud, mock_db, sample_session):
        """Test deactivating a session"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_session
        mock_db.commit = MagicMock()

        result = session_crud.deactivate(mock_db, "session_123")

        assert result is True
        assert sample_session.is_active is False
        mock_db.commit.assert_called_once()

    def test_deactivate_session_not_found(self, session_crud, mock_db):
        """Test deactivating non-existent session returns False"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        result = session_crud.deactivate(mock_db, "nonexistent")

        assert result is False

    def test_deactivate_by_user(self, session_crud, mock_db):
        """Test deactivating all sessions for a user"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.update.return_value = 3
        mock_db.commit = MagicMock()

        result = session_crud.deactivate_by_user(mock_db, "user_123")

        assert result == 3
        mock_query.update.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_cleanup_expired_sessions(self, session_crud, mock_db):
        """Test cleaning up expired sessions"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.update.return_value = 5
        mock_db.commit = MagicMock()

        result = session_crud.cleanup_expired_sessions(mock_db)

        assert result == 5
        mock_query.filter.assert_called_once()
        mock_query.update.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_count_active_sessions(self, session_crud, mock_db):
        """Test counting active sessions"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 10

        result = session_crud.count_active_sessions(mock_db)

        assert result == 10
        mock_query.filter.assert_called_once()

    def test_count_active_sessions_none(self, session_crud, mock_db):
        """Test counting active sessions when result is None"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = None

        result = session_crud.count_active_sessions(mock_db)

        assert result == 0


# ===================== AuditLogCRUD Tests =====================
class TestAuditLogCRUD:
    """Test AuditLogCRUD operations"""

    def test_get_audit_log_by_id(self, audit_crud, mock_db, sample_audit_log):
        """Test getting audit log by ID"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_audit_log

        result = audit_crud.get(mock_db, "log_123")

        assert result == sample_audit_log
        mock_db.query.assert_called_once_with(AuditLog)

    def test_get_multi_audit_logs(self, audit_crud, mock_db, sample_audit_log):
        """Test getting multiple audit logs"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_audit_log]

        logs, total = audit_crud.get_multi(mock_db, skip=0, limit=10)

        assert logs == [sample_audit_log]
        assert total == 1

    def test_get_multi_with_user_filter(self, audit_crud, mock_db, sample_audit_log):
        """Test getting audit logs filtered by user"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_audit_log]

        logs, total = audit_crud.get_multi(
            mock_db, skip=0, limit=10, user_id="user_123"
        )

        assert logs == [sample_audit_log]
        assert total == 1
        # Verify filter was called for user_id
        assert mock_query.filter.called

    def test_get_multi_with_action_filter(self, audit_crud, mock_db, sample_audit_log):
        """Test getting audit logs filtered by action"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_audit_log]

        logs, total = audit_crud.get_multi(
            mock_db, skip=0, limit=10, action="login"
        )

        assert logs == [sample_audit_log]
        assert total == 1

    def test_get_multi_with_resource_type_filter(
        self, audit_crud, mock_db, sample_audit_log
    ):
        """Test getting audit logs filtered by resource type"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_audit_log]

        logs, total = audit_crud.get_multi(
            mock_db, skip=0, limit=10, resource_type="user"
        )

        assert logs == [sample_audit_log]
        assert total == 1

    def test_get_multi_with_date_range(self, audit_crud, mock_db, sample_audit_log):
        """Test getting audit logs with date range filter"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_audit_log]

        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        logs, total = audit_crud.get_multi(
            mock_db, skip=0, limit=10, start_date=start_date, end_date=end_date
        )

        assert logs == [sample_audit_log]
        assert total == 1

    def test_create_audit_log(self, audit_crud, mock_db, sample_user):
        """Test creating an audit log"""
        # Mock user query
        mock_user_query = MagicMock()
        mock_db.query.return_value = mock_user_query
        mock_user_query.filter.return_value = mock_user_query
        mock_user_query.first.return_value = sample_user

        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        result = audit_crud.create(
            db=mock_db,
            user_id="user_123",
            action="user_login",
            resource_type="user",
            resource_id="user_123",
            response_status=200,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert result.action == "user_login"
        assert result.user_id == "user_123"

    def test_create_audit_log_user_not_found(self, audit_crud, mock_db):
        """Test creating audit log when user doesn't exist returns None"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        result = audit_crud.create(
            db=mock_db,
            user_id="nonexistent",
            action="test_action",
        )

        assert result is None

    def test_count_audit_logs(self, audit_crud, mock_db):
        """Test counting total audit logs"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.scalar.return_value = 100

        result = audit_crud.count(mock_db)

        assert result == 100
        mock_db.query.assert_called_once()

    def test_count_audit_logs_none(self, audit_crud, mock_db):
        """Test counting audit logs when result is None"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.scalar.return_value = None

        result = audit_crud.count(mock_db)

        assert result == 0

    def test_get_user_actions(self, audit_crud, mock_db):
        """Test getting user's recent actions"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = [("user_login",), ("user_logout",)]

        result = audit_crud.get_user_actions(mock_db, "user_123", days=30)

        assert result == ["user_login", "user_logout"]
        mock_query.filter.assert_called_once()
        mock_query.distinct.assert_called_once()

    def test_get_login_statistics(self, audit_crud, mock_db):
        """Test getting login statistics"""
        # Setup different query chains for each scalar call
        call_count = [0]

        def query_side_effect(*args):
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query

            def scalar_side_effect():
                call_count[0] += 1
                if call_count[0] == 1:
                    return 100  # total_logins
                elif call_count[0] == 2:
                    return 95  # successful_logins
                return 0

            mock_query.scalar.side_effect = scalar_side_effect
            return mock_query

        mock_db.query.side_effect = query_side_effect

        result = audit_crud.get_login_statistics(mock_db, days=7)

        assert result["total_logins"] == 100
        assert result["successful_logins"] == 95
        assert result["failed_logins"] == 5
        assert result["success_rate"] == 95.0

    def test_get_login_statistics_zero_logins(self, audit_crud, mock_db):
        """Test login statistics when no logins recorded"""
        call_count = [0]

        def query_side_effect(*args):
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query

            def scalar_side_effect():
                call_count[0] += 1
                if call_count[0] == 1:
                    return 0  # total_logins
                return 0

            mock_query.scalar.side_effect = scalar_side_effect
            return mock_query

        mock_db.query.side_effect = query_side_effect

        result = audit_crud.get_login_statistics(mock_db, days=7)

        assert result["total_logins"] == 0
        assert result["successful_logins"] == 0
        assert result["failed_logins"] == 0
        assert result["success_rate"] == 0


# ===================== Edge Cases and Error Handling =====================
class TestAuthCRUDEdgeCases:
    """Test edge cases and error handling in auth CRUD operations"""

    def test_user_create_with_all_fields(self, user_crud, mock_db):
        """Test creating user with all optional fields"""
        user_data = UserCreate(
            username="completeuser",
            email="complete@example.com",
            full_name="Complete User",
            password="SecurePass123!",
            role=UserRole.ADMIN,
            employee_id="emp_123",
            default_organization_id="org_123",
        )

        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        result = user_crud.create(mock_db, user_data)

        assert result.employee_id == "emp_123"
        assert result.default_organization_id == "org_123"
        assert result.role == UserRole.ADMIN

    def test_user_update_no_changes(self, user_crud, mock_db, sample_user):
        """Test updating user with empty update data"""
        empty_update = UserUpdate()

        result = user_crud.update(mock_db, sample_user, empty_update)

        # Should still trigger update of updated_at
        mock_db.commit.assert_called_once()

    def test_session_create_with_minimal_params(self, session_crud, mock_db):
        """Test creating session with only required parameters"""
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        result = session_crud.create(
            db=mock_db, user_id="user_123", refresh_token="token"
        )

        assert result.user_id == "user_123"
        assert result.refresh_token == "token"
        assert result.expires_at is not None

    def test_audit_log_create_with_all_params(self, audit_crud, mock_db, sample_user):
        """Test creating audit log with all parameters"""
        mock_user_query = MagicMock()
        mock_db.query.return_value = mock_user_query
        mock_user_query.filter.return_value = mock_user_query
        mock_user_query.first.return_value = sample_user

        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        result = audit_crud.create(
            db=mock_db,
            user_id="user_123",
            action="user_update",
            resource_type="user",
            resource_id="user_123",
            resource_name="Test User",
            api_endpoint="/api/v1/users/user_123",
            http_method="PUT",
            request_params='{"id": "user_123"}',
            request_body='{"email": "new@example.com"}',
            response_status=200,
            response_message="Success",
            ip_address="192.168.1.1",
            user_agent="Mozilla",
            session_id="session_123",
        )

        assert result.resource_name == "Test User"
        assert result.api_endpoint == "/api/v1/users/user_123"
        assert result.response_status == 200

    def test_get_multi_with_all_filters(self, user_crud, mock_db, sample_user):
        """Test user query with all filters applied"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_user]

        users, total = user_crud.get_multi_with_filters(
            db=mock_db,
            skip=0,
            limit=10,
            search="test",
            role=UserRole.USER,
            is_active=True,
            organization_id="org_123",
        )

        assert users == [sample_user]
        assert total == 1
        # Multiple filter calls expected
        assert mock_query.filter.call_count >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--cov=src/crud/auth", "--cov-report=term"])
