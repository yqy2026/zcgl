"""
Comprehensive unit tests for auth CRUD operations (async)
Targeting 70%+ coverage for backend/src/crud/auth.py
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.auth import AuditLogCRUD, UserCRUD, UserSessionCRUD
from src.models.auth import AuditLog, User, UserSession
from src.schemas.auth import UserCreate, UserUpdate

pytestmark = pytest.mark.asyncio


def _mock_execute_first(value):
    result = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = value
    result.scalars.return_value = scalars
    return result


def _mock_execute_scalars(values):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


def _mock_execute_scalar(value):
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _mock_execute_rowcount(value):
    result = MagicMock()
    result.rowcount = value
    return result


# ===================== Fixtures =====================


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def user_crud():
    return UserCRUD()


@pytest.fixture
def session_crud():
    return UserSessionCRUD()


@pytest.fixture
def audit_crud():
    return AuditLogCRUD()


@pytest.fixture
def sample_user():
    return User(
        id="user_123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password_hash="hashed_password_here",
        is_active=True,
        employee_id=None,
        default_organization_id=None,
    )


@pytest.fixture
def sample_session():
    return UserSession(
        id="session_123",
        user_id="user_123",
        refresh_token="refresh_token_value",
        device_info="Chrome on Windows",
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        is_active=True,
        expires_at=datetime.now() + timedelta(days=7),
    )


@pytest.fixture
def sample_audit_log():
    return AuditLog(
        id="log_123",
        user_id="user_123",
        username="testuser",
        user_role="asset_viewer",
        action="user_login",
        resource_type=None,
        resource_id=None,
        response_status=200,
    )


@pytest.fixture
def user_create_data():
    return UserCreate(
        username="newuser",
        email="newuser@example.com",
        full_name="New User",
        password="SecurePass123!",
        role_id="role-user-id",
        employee_id=None,
        default_organization_id=None,
    )


@pytest.fixture
def user_update_data():
    return UserUpdate(
        email="updated@example.com",
        full_name="Updated Name",
        role_id="role-admin-id",
    )


# ===================== UserCRUD Tests =====================


class TestUserCRUD:
    async def test_get_user_by_id(self, user_crud, mock_db, sample_user):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await user_crud.get_async(mock_db, "user_123")

        assert result == sample_user
        mock_db.execute.assert_awaited_once()

    async def test_get_user_by_id_not_found(self, user_crud, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        result = await user_crud.get_async(mock_db, "nonexistent")

        assert result is None

    async def test_get_by_username(self, user_crud, mock_db, sample_user):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await user_crud.get_by_username_async(mock_db, "testuser")

        assert result == sample_user
        mock_db.execute.assert_awaited_once()

    async def test_get_by_email(self, user_crud, mock_db, sample_user):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await user_crud.get_by_email_async(mock_db, "test@example.com")

        assert result == sample_user
        mock_db.execute.assert_awaited_once()

    async def test_get_multi(self, user_crud, mock_db, sample_user):
        mock_db.execute = AsyncMock(return_value=_mock_execute_scalars([sample_user]))

        result = await user_crud.get_multi_async(mock_db, skip=0, limit=10)

        assert result == [sample_user]
        mock_db.execute.assert_awaited_once()

    async def test_get_multi_with_filters_search(
        self, user_crud, mock_db, sample_user
    ):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_scalar(1),
                _mock_execute_scalars([sample_user]),
            ]
        )

        users, total = await user_crud.get_multi_with_filters_async(
            mock_db, skip=0, limit=10, search="test"
        )

        assert users == [sample_user]
        assert total == 1

    async def test_get_multi_with_filters_role(self, user_crud, mock_db, sample_user):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_scalar(1),
                _mock_execute_scalars([sample_user]),
            ]
        )

        users, total = await user_crud.get_multi_with_filters_async(
            mock_db, skip=0, limit=10, role_id="role-user-id"
        )

        assert users == [sample_user]
        assert total == 1

    async def test_get_multi_with_filters_is_active(
        self, user_crud, mock_db, sample_user
    ):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_scalar(1),
                _mock_execute_scalars([sample_user]),
            ]
        )

        users, total = await user_crud.get_multi_with_filters_async(
            mock_db, skip=0, limit=10, is_active=True
        )

        assert users == [sample_user]
        assert total == 1

    async def test_get_multi_with_filters_organization(
        self, user_crud, mock_db, sample_user
    ):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_scalar(1),
                _mock_execute_scalars([sample_user]),
            ]
        )

        users, total = await user_crud.get_multi_with_filters_async(
            mock_db, skip=0, limit=10, organization_id="org_123"
        )

        assert users == [sample_user]
        assert total == 1

    async def test_create_user(self, user_crud, mock_db, user_create_data):
        result = await user_crud.create_async(mock_db, user_create_data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

        assert result.username == user_create_data.username
        assert result.email == user_create_data.email
        assert result.full_name == user_create_data.full_name
        assert hasattr(result, "password_hash")
        assert result.password_hash is not None

    async def test_update_user(
        self, user_crud, mock_db, sample_user, user_update_data
    ):
        result = await user_crud.update_async(mock_db, sample_user, user_update_data)

        assert result.email == user_update_data.email
        assert result.full_name == user_update_data.full_name
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    async def test_delete_user_soft(self, user_crud, mock_db, sample_user):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await user_crud.delete_async(mock_db, "user_123")

        assert result is True
        assert sample_user.is_active is False
        mock_db.commit.assert_awaited_once()

    async def test_delete_user_not_found(self, user_crud, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        result = await user_crud.delete_async(mock_db, "nonexistent")

        assert result is False

    async def test_count_users(self, user_crud, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_scalar(42))

        result = await user_crud.count_async(mock_db)

        assert result == 42

    async def test_count_users_none(self, user_crud, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_scalar(None))

        result = await user_crud.count_async(mock_db)

        assert result == 0

    async def test_count_active_users(self, user_crud, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_scalar(30))

        result = await user_crud.count_active_async(mock_db)

        assert result == 30

    async def test_get_recent_logins(self, user_crud, mock_db, sample_user):
        sample_user.last_login_at = datetime.now()
        mock_db.execute = AsyncMock(return_value=_mock_execute_scalars([sample_user]))

        result = await user_crud.get_recent_logins_async(mock_db, limit=10)

        assert result == [sample_user]
        mock_db.execute.assert_awaited_once()

    async def test_get_users_by_role(self, user_crud, mock_db, sample_user):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_scalars([sample_user]),
                _mock_execute_scalar(1),
            ]
        )

        users, total = await user_crud.get_users_by_role(
            mock_db, role_id="role-user-id", skip=0, limit=10
        )

        assert users == [sample_user]
        assert total == 1


# ===================== UserSessionCRUD Tests =====================


class TestUserSessionCRUD:
    async def test_get_session_by_id(self, session_crud, mock_db, sample_session):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_session))

        result = await session_crud.get_async(mock_db, "session_123")

        assert result == sample_session

    async def test_get_session_by_refresh_token(
        self, session_crud, mock_db, sample_session
    ):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_session))

        result = await session_crud.get_by_refresh_token_async(
            mock_db, "refresh_token_value"
        )

        assert result == sample_session

    async def test_get_user_sessions_active_only(
        self, session_crud, mock_db, sample_session
    ):
        mock_db.execute = AsyncMock(return_value=_mock_execute_scalars([sample_session]))

        result = await session_crud.get_user_sessions_async(
            mock_db, "user_123", active_only=True
        )

        assert result == [sample_session]

    async def test_get_user_sessions_all(
        self, session_crud, mock_db, sample_session
    ):
        mock_db.execute = AsyncMock(return_value=_mock_execute_scalars([sample_session]))

        result = await session_crud.get_user_sessions_async(
            mock_db, "user_123", active_only=False
        )

        assert result == [sample_session]

    async def test_create_session(self, session_crud, mock_db):
        result = await session_crud.create_async(
            db=mock_db,
            user_id="user_123",
            refresh_token="new_refresh_token",
            device_info="Chrome",
            ip_address="192.168.1.1",
            user_agent="Mozilla",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()
        assert result.user_id == "user_123"
        assert result.refresh_token == "new_refresh_token"

    async def test_deactivate_session(self, session_crud, mock_db, sample_session):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_session))

        result = await session_crud.deactivate_async(mock_db, "session_123")

        assert result is True
        assert sample_session.is_active is False
        mock_db.commit.assert_awaited_once()

    async def test_deactivate_session_not_found(self, session_crud, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        result = await session_crud.deactivate_async(mock_db, "nonexistent")

        assert result is False

    async def test_deactivate_by_user(self, session_crud, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_rowcount(3))

        result = await session_crud.deactivate_by_user_async(mock_db, "user_123")

        assert result == 3
        mock_db.commit.assert_awaited_once()

    async def test_cleanup_expired_sessions(self, session_crud, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_rowcount(5))

        result = await session_crud.cleanup_expired_sessions_async(mock_db)

        assert result == 5
        mock_db.commit.assert_awaited_once()

    async def test_count_active_sessions_none(self, session_crud, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_scalar(None))

        result = await session_crud.count_active_sessions_async(mock_db)

        assert result == 0


# ===================== AuditLogCRUD Tests =====================


class TestAuditLogCRUD:
    async def test_get_audit_log_by_id(self, audit_crud, mock_db, sample_audit_log):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_audit_log))

        result = await audit_crud.get_async(mock_db, "log_123")

        assert result == sample_audit_log

    async def test_get_multi_audit_logs(self, audit_crud, mock_db, sample_audit_log):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_scalar(1),
                _mock_execute_scalars([sample_audit_log]),
            ]
        )

        logs, total = await audit_crud.get_multi_async(mock_db, skip=0, limit=10)

        assert logs == [sample_audit_log]
        assert total == 1

    async def test_get_multi_with_user_filter(
        self, audit_crud, mock_db, sample_audit_log
    ):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_scalar(1),
                _mock_execute_scalars([sample_audit_log]),
            ]
        )

        logs, total = await audit_crud.get_multi_async(
            mock_db, skip=0, limit=10, user_id="user_123"
        )

        assert logs == [sample_audit_log]
        assert total == 1

    async def test_get_multi_with_action_filter(
        self, audit_crud, mock_db, sample_audit_log
    ):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_scalar(1),
                _mock_execute_scalars([sample_audit_log]),
            ]
        )

        logs, total = await audit_crud.get_multi_async(
            mock_db, skip=0, limit=10, action="login"
        )

        assert logs == [sample_audit_log]
        assert total == 1

    async def test_get_multi_with_resource_type_filter(
        self, audit_crud, mock_db, sample_audit_log
    ):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_scalar(1),
                _mock_execute_scalars([sample_audit_log]),
            ]
        )

        logs, total = await audit_crud.get_multi_async(
            mock_db, skip=0, limit=10, resource_type="user"
        )

        assert logs == [sample_audit_log]
        assert total == 1

    async def test_get_multi_with_date_range(
        self, audit_crud, mock_db, sample_audit_log
    ):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_scalar(1),
                _mock_execute_scalars([sample_audit_log]),
            ]
        )

        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        logs, total = await audit_crud.get_multi_async(
            mock_db, skip=0, limit=10, start_date=start_date, end_date=end_date
        )

        assert logs == [sample_audit_log]
        assert total == 1

    async def test_create_audit_log(self, audit_crud, mock_db, sample_user):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await audit_crud.create_async(
            db=mock_db,
            user_id="user_123",
            action="user_login",
            resource_type="user",
            resource_id="user_123",
            response_status=200,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()
        assert result.action == "user_login"
        assert result.user_id == "user_123"

    async def test_create_audit_log_user_not_found(self, audit_crud, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        result = await audit_crud.create_async(
            db=mock_db,
            user_id="nonexistent",
            action="test_action",
        )

        assert result is None

    async def test_count_audit_logs(self, audit_crud, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_scalar(100))

        result = await audit_crud.count_async(mock_db)

        assert result == 100

    async def test_count_audit_logs_none(self, audit_crud, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_execute_scalar(None))

        result = await audit_crud.count_async(mock_db)

        assert result == 0

    async def test_get_user_actions(self, audit_crud, mock_db):
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_scalars(["user_login", "user_logout"])
        )

        result = await audit_crud.get_user_actions_async(mock_db, "user_123", days=30)

        assert result == ["user_login", "user_logout"]

    async def test_get_login_statistics(self, audit_crud, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_scalar(100),
                _mock_execute_scalar(95),
            ]
        )

        result = await audit_crud.get_login_statistics_async(mock_db, days=7)

        assert result["total_logins"] == 100
        assert result["successful_logins"] == 95
        assert result["failed_logins"] == 5
        assert result["success_rate"] == 95.0

    async def test_get_login_statistics_zero_logins(self, audit_crud, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_scalar(0),
                _mock_execute_scalar(0),
            ]
        )

        result = await audit_crud.get_login_statistics_async(mock_db, days=7)

        assert result["total_logins"] == 0
        assert result["successful_logins"] == 0
        assert result["failed_logins"] == 0
        assert result["success_rate"] == 0


# ===================== Edge Cases and Error Handling =====================


class TestAuthCRUDEdgeCases:
    async def test_user_create_with_all_fields(self, user_crud, mock_db):
        user_data = UserCreate(
            username="completeuser",
            email="complete@example.com",
            full_name="Complete User",
            password="SecurePass123!",
            role_id="role-admin-id",
            employee_id="emp_123",
            default_organization_id="org_123",
        )

        result = await user_crud.create_async(mock_db, user_data)

        assert result.employee_id == "emp_123"
        assert result.default_organization_id == "org_123"
        assert result.employee_id == "emp_123"

    async def test_user_update_no_changes(self, user_crud, mock_db, sample_user):
        empty_update = UserUpdate()

        await user_crud.update_async(mock_db, sample_user, empty_update)

        mock_db.commit.assert_awaited_once()

    async def test_session_create_with_minimal_params(self, session_crud, mock_db):
        result = await session_crud.create_async(
            db=mock_db, user_id="user_123", refresh_token="token"
        )

        assert result.user_id == "user_123"
        assert result.refresh_token == "token"
        assert result.expires_at is not None

    async def test_audit_log_create_with_all_params(
        self, audit_crud, mock_db, sample_user
    ):
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(sample_user))

        result = await audit_crud.create_async(
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

    async def test_get_multi_with_all_filters(self, user_crud, mock_db, sample_user):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_scalar(1),
                _mock_execute_scalars([sample_user]),
            ]
        )

        users, total = await user_crud.get_multi_with_filters_async(
            db=mock_db,
            skip=0,
            limit=10,
            search="test",
            role_id="role-user-id",
            is_active=True,
            organization_id="org_123",
        )

        assert users == [sample_user]
        assert total == 1


if __name__ == "__main__":
    pytest.main(
        [__file__, "-v", "--tb=short", "--cov=src/crud/auth", "--cov-report=term"]
    )
