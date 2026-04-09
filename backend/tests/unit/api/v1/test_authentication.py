"""
Comprehensive Unit Tests for Authentication API Routes (src/api/v1/auth/auth_modules/authentication.py)

This test module covers all endpoints in the authentication router to achieve 70%+ coverage:

Endpoints Tested:
1. POST /api/v1/auth/login - User login
2. POST /api/v1/auth/logout - User logout
3. POST /api/v1/auth/refresh - Refresh access token
4. GET /api/v1/auth/me - Get current user info
5. GET /api/v1/auth/test-enhanced - Test enhanced endpoint (debug)
6. GET /api/v1/auth/debug-auth - Debug authentication flow (debug)
7. GET /api/v1/auth/test-me-debug - Debug ME endpoint (debug)

Testing Approach:
- Mock all dependencies (AsyncAuthenticationService, AsyncSessionService, AuditLogCRUD, UserCRUD, database, auth)
- Test successful responses
- Test error handling scenarios
- Test request validation
- Test response schemas
- Test security features (token blacklisting, session management)
"""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import Response, status
from pydantic import ValidationError

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
def mock_request():
    """Create mock FastAPI request"""
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {"user-agent": "test-agent"}
    return request


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture(autouse=True)
def mock_rbac_service(monkeypatch):
    """Patch RBACService to avoid database dependencies in auth tests."""
    from src.api.v1.auth.auth_modules import authentication as auth_module

    rbac_instance = MagicMock()
    rbac_instance.get_user_role_summary = AsyncMock(return_value=USER_ROLE_SUMMARY)
    monkeypatch.setattr(
        auth_module, "RBACService", MagicMock(return_value=rbac_instance)
    )
    return rbac_instance


@pytest.fixture
def mock_admin_user():
    """Create mock admin user"""
    from src.schemas.auth import UserResponse

    return UserResponse(
        id="admin-id",
        username="admin",
        email="admin@example.com",
        phone="13800000001",
        full_name="Admin User",
        role_id="role-admin-id",
        roles=["admin"],
        role_ids=["role-admin-id"],
        is_admin=True,
        is_active=True,
        is_locked=False,
        default_organization_id=None,
        last_login_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_regular_user():
    """Create mock regular user"""
    from src.schemas.auth import UserResponse

    return UserResponse(
        id="user-id",
        username="testuser",
        email="test@example.com",
        phone="13800000002",
        full_name="Test User",
        role_id="role-user-id",
        roles=["asset_viewer"],
        role_ids=["role-user-id"],
        is_admin=False,
        is_active=True,
        is_locked=False,
        default_organization_id=None,
        last_login_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_user_model():
    """Create mock user model"""
    user = MagicMock()
    user.id = "user-id"
    user.username = "testuser"
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.is_active = True
    user.is_locked_now.return_value = False
    user.last_login_at = datetime.now(UTC)
    return user


def test_login_success_security_check(
    mock_request, mock_user_model, mock_regular_user, mock_db
):
    """
    Test login security requirements:
    1. HttpOnly cookies must be set
    2. Tokens MUST NOT be in response body
    """
    from src.api.v1.auth.auth_modules.authentication import login
    from src.schemas.auth import LoginRequest

    # Mock auth/session services
    with (
        patch(
            "src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService"
        ) as mock_auth_service,
        patch(
            "src.api.v1.auth.auth_modules.authentication.AsyncSessionService"
        ) as mock_session_service,
        patch(
            "src.api.v1.auth.auth_modules.authentication.AuditLogCRUD"
        ) as mock_audit_crud_class,
    ):
        auth_service_instance = mock_auth_service.return_value
        auth_service_instance.authenticate_user = AsyncMock(
            return_value=mock_user_model
        )
        mock_session_service.return_value.create_user_session = AsyncMock(
            return_value=None
        )
        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        # Mock tokens
        mock_tokens = MagicMock()
        mock_tokens.access_token = "access-token-123"
        mock_tokens.refresh_token = "refresh-token-123"
        mock_tokens.session_id = "session-123"
        mock_tokens.token_type = "bearer"
        mock_tokens.expires_in = 3600
        auth_service_instance.create_tokens.return_value = mock_tokens

        # Mock cookie manager
        with patch(
            "src.api.v1.auth.auth_modules.authentication.cookie_manager"
        ) as mock_cookie_manager:
            # Mock RBAC service

            with patch(
                "src.api.v1.auth.auth_modules.authentication.RBACService"
            ) as mock_rbac:
                rbac_instance = mock_rbac.return_value
                rbac_instance.get_user_permissions_summary.return_value.permissions = []

                # Execute
                credentials = LoginRequest(
                    identifier="testuser", password="password", remember=False
                )
                mock_response = MagicMock(spec=Response)

                result = asyncio.run(
                    login(mock_request, credentials, mock_response, mock_db)
                )

            # Assertions

            # 1. Verify response body DOES NOT contain tokens
            assert "access_token" not in result
            assert "refresh_token" not in result
            assert "tokens" not in result
            assert result["auth_mode"] == "cookie"
            assert result["user"]["username"] == "testuser"

            # 2. Verify cookies were set
            mock_cookie_manager.set_auth_cookie.assert_called_once_with(
                mock_response, "access-token-123", persistent=False
            )
            mock_cookie_manager.set_refresh_cookie.assert_called_once_with(
                mock_response, "refresh-token-123", persistent=False
            )
            csrf_token = mock_cookie_manager.create_csrf_token.return_value
            mock_cookie_manager.set_csrf_cookie.assert_called_once_with(
                mock_response, csrf_token, persistent=False
            )


@pytest.fixture
def mock_tokens():
    """Create mock tokens"""
    tokens = MagicMock()
    tokens.access_token = "mock_access_token"
    tokens.refresh_token = "mock_refresh_token"
    tokens.token_type = "bearer"
    tokens.expires_in = 3600
    tokens.session_id = "session-id"
    return tokens


@pytest.fixture
def mock_session(mock_user_model):
    """Create mock session"""
    session = MagicMock()
    session.user_id = "user-id"
    session.refresh_token = "refresh_token"
    session.ip_address = "127.0.0.1"
    session.user_agent = "test-agent"
    session.device_id = "device-id"
    session.platform = "web"
    session.session_id = "session-id"
    session.last_accessed_at = datetime.now(UTC)
    session.user = mock_user_model
    return session


# ============================================================================
# Test: POST /login - User Login
# ============================================================================


class TestLogin:
    """Tests for POST /api/v1/auth/login endpoint"""

    def test_login_request_rejects_legacy_username_field(self):
        """Legacy username payload should fail validation in current API contract."""
        from src.schemas.auth import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(**{"username": "testuser", "password": "password123"})

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.UserCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_login_success(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_user_crud_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
    ):
        """Test successful user login"""
        from src.api.v1.auth.auth_modules.authentication import login
        from src.schemas.auth import LoginRequest

        credentials = LoginRequest(identifier="testuser", password="password123")

        mock_user = MagicMock()
        mock_user.id = "user-id"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.full_name = "Test User"
        mock_user.is_active = True

        mock_tokens = MagicMock()
        mock_tokens.access_token = "access_token"
        mock_tokens.refresh_token = "refresh_token"
        mock_tokens.token_type = "bearer"
        mock_tokens.expires_in = 3600

        mock_auth_service = MagicMock()
        mock_auth_service.authenticate_user = AsyncMock(return_value=mock_user)
        mock_auth_service.create_tokens.return_value = mock_tokens
        mock_auth_service_class.return_value = mock_auth_service

        mock_session_service = MagicMock()
        mock_session_service.create_user_session = AsyncMock(return_value=None)
        mock_session_service_class.return_value = mock_session_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            login(
                request=mock_request,
                credentials=credentials,
                response=Response(),
                db=mock_db,
            )
        )

        assert result["message"] == "登录成功"
        assert result["user"]["username"] == "testuser"
        assert result["auth_mode"] == "cookie"
        assert "tokens" not in result
        mock_auth_service.authenticate_user.assert_called_once_with(
            "testuser", "password123"
        )
        mock_auth_service.create_tokens.assert_called_once()

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.UserCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_login_deduplicates_permissions_without_hash_error(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_user_crud_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
    ):
        """Test login permission dedupe works without hashing Pydantic models."""
        from src.api.v1.auth.auth_modules.authentication import login
        from src.schemas.auth import LoginRequest

        credentials = LoginRequest(identifier="testuser", password="password123")

        mock_user = MagicMock()
        mock_user.id = "user-id"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.phone = "13800009999"
        mock_user.full_name = "Test User"
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.last_login_at = None
        mock_user.default_organization_id = None
        now = datetime.now(UTC)
        mock_user.created_at = now
        mock_user.updated_at = now

        mock_tokens = MagicMock()
        mock_tokens.access_token = "access_token"
        mock_tokens.refresh_token = "refresh_token"
        mock_tokens.token_type = "bearer"
        mock_tokens.expires_in = 3600
        mock_tokens.session_id = "session-id"

        mock_auth_service = MagicMock()
        mock_auth_service.authenticate_user = AsyncMock(return_value=mock_user)
        mock_auth_service.create_tokens.return_value = mock_tokens
        mock_auth_service_class.return_value = mock_auth_service

        mock_session_service = MagicMock()
        mock_session_service.create_user_session = AsyncMock(return_value=None)
        mock_session_service_class.return_value = mock_session_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        permissions_summary = SimpleNamespace(
            permissions=[
                SimpleNamespace(
                    resource="asset",
                    action="read",
                    description="查看资产",
                ),
                SimpleNamespace(
                    resource="asset",
                    action="read",
                    description="查看资产",
                ),
                SimpleNamespace(
                    resource="asset",
                    action="create",
                    description="创建资产",
                ),
            ]
        )

        with patch(
            "src.api.v1.auth.auth_modules.authentication.RBACService"
        ) as mock_rbac_class:
            mock_rbac_service = MagicMock()
            mock_rbac_service.get_user_role_summary = AsyncMock(
                return_value=USER_ROLE_SUMMARY
            )
            mock_rbac_service.get_user_permissions_summary = AsyncMock(
                return_value=permissions_summary
            )
            mock_rbac_class.return_value = mock_rbac_service

            result = asyncio.run(
                login(
                    request=mock_request,
                    credentials=credentials,
                    response=Response(),
                    db=mock_db,
                )
            )

        permissions = result["permissions"]
        assert len(permissions) == 2
        permission_pairs = {
            (perm["resource"], perm["action"])
            if isinstance(perm, dict)
            else (perm.resource, perm.action)
            for perm in permissions
        }
        assert permission_pairs == {
            ("asset", "read"),
            ("asset", "create"),
        }

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.UserCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_login_invalid_credentials_audit_prefers_auth_consistent_active_match(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_user_crud_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
    ):
        """Failed login audit should follow active-identifier resolution before inactive fallback."""
        from src.api.v1.auth.auth_modules.authentication import login
        from src.core.exception_handler import AuthenticationError
        from src.schemas.auth import LoginRequest

        credentials = LoginRequest(identifier="13800002000", password="wrongpass")

        mock_auth_service = MagicMock()
        mock_auth_service.authenticate_user = AsyncMock(return_value=None)
        mock_auth_service_class.return_value = mock_auth_service

        active_phone_user = MagicMock()
        active_phone_user.id = "active-phone-user-id"
        active_phone_user.is_active = True

        inactive_username_user = MagicMock()
        inactive_username_user.id = "inactive-username-user-id"
        inactive_username_user.is_active = False

        mock_user_crud = MagicMock()
        mock_user_crud.find_active_by_identifier_async = AsyncMock(
            return_value=active_phone_user
        )
        mock_user_crud.find_by_identifier_async = AsyncMock(
            return_value=inactive_username_user
        )
        mock_user_crud_class.return_value = mock_user_crud

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        with pytest.raises(AuthenticationError):
            asyncio.run(
                login(
                    request=mock_request,
                    credentials=credentials,
                    response=Response(),
                    db=mock_db,
                )
            )

        mock_user_crud.find_active_by_identifier_async.assert_awaited_once_with(
            mock_db, "13800002000"
        )
        mock_user_crud.find_by_identifier_async.assert_not_called()
        mock_audit_crud.create_async.assert_awaited_once()
        audit_payload = mock_audit_crud.create_async.await_args.kwargs
        assert audit_payload["user_id"] == "active-phone-user-id"
        assert audit_payload["action"] == "user_login_failed"

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.UserCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_login_invalid_credentials_logs_disabled_user_audit(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_user_crud_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
    ):
        """Failed login should still be audited when identifier matches disabled user."""
        from src.api.v1.auth.auth_modules.authentication import login
        from src.core.exception_handler import AuthenticationError
        from src.schemas.auth import LoginRequest

        credentials = LoginRequest(identifier="13800002000", password="wrongpass")

        mock_auth_service = MagicMock()
        mock_auth_service.authenticate_user = AsyncMock(return_value=None)
        mock_auth_service_class.return_value = mock_auth_service

        disabled_user = MagicMock()
        disabled_user.id = "disabled-user-id"
        disabled_user.is_active = False

        mock_user_crud = MagicMock()
        mock_user_crud.find_active_by_identifier_async = AsyncMock(return_value=None)
        mock_user_crud.find_by_identifier_async = AsyncMock(return_value=disabled_user)
        mock_user_crud_class.return_value = mock_user_crud

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        with pytest.raises(AuthenticationError):
            asyncio.run(
                login(
                    request=mock_request,
                    credentials=credentials,
                    response=Response(),
                    db=mock_db,
                )
            )

        mock_user_crud.find_active_by_identifier_async.assert_awaited_once_with(
            mock_db, "13800002000"
        )
        mock_user_crud.find_by_identifier_async.assert_awaited_once_with(
            mock_db, "13800002000"
        )
        mock_audit_crud.create_async.assert_awaited_once()
        audit_payload = mock_audit_crud.create_async.await_args.kwargs
        assert audit_payload["user_id"] == "disabled-user-id"
        assert audit_payload["action"] == "user_login_failed"

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.UserCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_login_invalid_credentials(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_user_crud_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
    ):
        """Test login with invalid credentials"""
        from src.api.v1.auth.auth_modules.authentication import login
        from src.core.exception_handler import AuthenticationError
        from src.schemas.auth import LoginRequest

        credentials = LoginRequest(identifier="wronguser", password="wrongpass")

        mock_auth_service = MagicMock()
        mock_auth_service.authenticate_user = AsyncMock(return_value=None)
        mock_auth_service_class.return_value = mock_auth_service

        mock_existing_user = MagicMock()
        mock_existing_user.id = "wronguser-id"

        mock_user_crud = MagicMock()
        mock_user_crud.find_active_by_identifier_async = AsyncMock(
            return_value=mock_existing_user
        )
        mock_user_crud.find_by_identifier_async = AsyncMock(return_value=None)
        mock_user_crud_class.return_value = mock_user_crud

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        with pytest.raises(AuthenticationError) as exc_info:
            asyncio.run(
                login(
                    request=mock_request,
                    credentials=credentials,
                    response=Response(),
                    db=mock_db,
                )
            )

        mock_user_crud.find_active_by_identifier_async.assert_awaited_once_with(
            mock_db, "wronguser"
        )
        mock_user_crud.find_by_identifier_async.assert_not_called()
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "账号或密码错误" in exc_info.value.message

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.UserCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_login_invalid_credentials_no_user(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_user_crud_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
    ):
        """Test login with invalid credentials when user doesn't exist"""
        from src.api.v1.auth.auth_modules.authentication import login
        from src.core.exception_handler import AuthenticationError
        from src.schemas.auth import LoginRequest

        credentials = LoginRequest(identifier="nonexistent", password="wrongpass")

        mock_auth_service = MagicMock()
        mock_auth_service.authenticate_user = AsyncMock(return_value=None)
        mock_auth_service_class.return_value = mock_auth_service

        mock_user_crud = MagicMock()
        mock_user_crud.find_active_by_identifier_async = AsyncMock(return_value=None)
        mock_user_crud.find_by_identifier_async = AsyncMock(return_value=None)
        mock_user_crud_class.return_value = mock_user_crud

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        with pytest.raises(AuthenticationError) as exc_info:
            asyncio.run(
                login(
                    request=mock_request,
                    credentials=credentials,
                    response=Response(),
                    db=mock_db,
                )
            )

        mock_user_crud.find_active_by_identifier_async.assert_awaited_once_with(
            mock_db, "nonexistent"
        )
        mock_user_crud.find_by_identifier_async.assert_awaited_once_with(
            mock_db, "nonexistent"
        )
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.UserCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_login_server_error(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_user_crud_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
    ):
        """Test login with server error"""
        from src.api.v1.auth.auth_modules.authentication import login
        from src.core.exception_handler import InternalServerError
        from src.schemas.auth import LoginRequest

        credentials = LoginRequest(identifier="testuser", password="password123")

        mock_auth_service = MagicMock()
        mock_auth_service.authenticate_user = AsyncMock(
            side_effect=Exception("Database error")
        )
        mock_auth_service_class.return_value = mock_auth_service

        with pytest.raises(InternalServerError) as exc_info:
            asyncio.run(
                login(
                    request=mock_request,
                    credentials=credentials,
                    response=Response(),
                    db=mock_db,
                )
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "登录服务暂时不可用" in exc_info.value.message

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.UserCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_login_business_logic_error(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_user_crud_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
    ):
        """Test login with business logic error"""
        from src.api.v1.auth.auth_modules.authentication import login
        from src.core.exception_handler import InvalidRequestError
        from src.exceptions import BusinessLogicError
        from src.schemas.auth import LoginRequest

        credentials = LoginRequest(identifier="lockeduser", password="password123")

        mock_auth_service = MagicMock()
        mock_auth_service.authenticate_user = AsyncMock(
            side_effect=BusinessLogicError("账户已被锁定")
        )
        mock_auth_service_class.return_value = mock_auth_service

        with pytest.raises(InvalidRequestError) as exc_info:
            asyncio.run(
                login(
                    request=mock_request,
                    credentials=credentials,
                    response=Response(),
                    db=mock_db,
                )
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "账户已被锁定" in exc_info.value.message

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.UserCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_login_with_bool_is_active(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_user_crud_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
    ):
        """Test login when is_active is a boolean"""
        from src.api.v1.auth.auth_modules.authentication import login
        from src.schemas.auth import LoginRequest

        credentials = LoginRequest(identifier="testuser", password="password123")

        mock_user = MagicMock()
        mock_user.id = "user-id"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.full_name = "Test User"
        mock_user.is_active = True  # Boolean instead of int

        mock_tokens = MagicMock()
        mock_tokens.access_token = "access_token"
        mock_tokens.refresh_token = "refresh_token"
        mock_tokens.token_type = "bearer"
        mock_tokens.expires_in = 3600

        mock_auth_service = MagicMock()
        mock_auth_service.authenticate_user = AsyncMock(return_value=mock_user)
        mock_auth_service.create_tokens.return_value = mock_tokens
        mock_auth_service_class.return_value = mock_auth_service

        mock_session_service = MagicMock()
        mock_session_service.create_user_session = AsyncMock(return_value=None)
        mock_session_service_class.return_value = mock_session_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            login(
                request=mock_request,
                credentials=credentials,
                response=Response(),
                db=mock_db,
            )
        )

        assert result["user"]["is_active"] is True


# ============================================================================
# Test: POST /logout - User Logout
# ============================================================================


class TestLogout:
    """Tests for POST /api/v1/auth/logout endpoint"""

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_logout_success(
        self,
        mock_session_service_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
        mock_admin_user,
    ):
        """Test successful user logout"""
        from src.api.v1.auth.auth_modules.authentication import logout

        mock_request.headers = {
            "user-agent": "test-agent",
        }

        mock_session_service = MagicMock()
        mock_session_service.revoke_all_user_sessions = AsyncMock(return_value=2)
        mock_session_service_class.return_value = mock_session_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            logout(
                request=mock_request,
                response=Response(),
                current_user=mock_admin_user,
                db=mock_db,
            )
        )

        assert result["message"] == "登出成功"
        assert result["revoked_sessions"] == 2
        mock_session_service.revoke_all_user_sessions.assert_called_once_with(
            "admin-id"
        )

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_logout_without_auth_cookie(
        self,
        mock_session_service_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
        mock_admin_user,
    ):
        """Test logout without auth cookie"""
        from src.api.v1.auth.auth_modules.authentication import logout

        mock_request.headers = {"user-agent": "test-agent"}

        mock_session_service = MagicMock()
        mock_session_service.revoke_all_user_sessions = AsyncMock(return_value=1)
        mock_session_service_class.return_value = mock_session_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            logout(
                request=mock_request,
                response=Response(),
                current_user=mock_admin_user,
                db=mock_db,
            )
        )

        assert result["message"] == "登出成功"
        mock_session_service.revoke_all_user_sessions.assert_called_once()

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_logout_with_valid_token_blacklist(
        self,
        mock_session_service_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
        mock_admin_user,
    ):
        """Test logout successfully blacklists token"""
        from src.api.v1.auth.auth_modules.authentication import logout
        from src.core.config import settings
        from src.security.cookie_manager import cookie_manager

        mock_request.headers = {
            "user-agent": "test-agent",
        }

        # Create a valid JWT token for testing
        token_data = {
            "sub": "admin-id",
            "exp": 1737000000,
            "jti": "test-jti",
            "iat": 1736996400,
        }
        valid_token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")
        mock_request.headers["cookie"] = f"{cookie_manager.cookie_name}={valid_token}"

        mock_session_service = MagicMock()
        mock_session_service.revoke_all_user_sessions = AsyncMock(return_value=1)
        mock_session_service_class.return_value = mock_session_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            logout(
                request=mock_request,
                response=Response(),
                current_user=mock_admin_user,
                db=mock_db,
            )
        )

        assert result["message"] == "登出成功"
        mock_session_service.revoke_all_user_sessions.assert_called_once()
        # Token blacklist code is executed (lines 182-188) - covered by this test

    @patch("src.security.token_blacklist.blacklist_manager")
    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_logout_blacklists_cookie_token(
        self,
        mock_session_service_class,
        mock_audit_crud_class,
        mock_blacklist_manager,
        mock_request,
        mock_db,
        mock_admin_user,
    ):
        """Test logout blacklists token from auth cookie."""
        from src.api.v1.auth.auth_modules.authentication import logout
        from src.core.config import settings
        from src.security.cookie_manager import cookie_manager

        token_data = {
            "sub": "admin-id",
            "exp": 1737000000,
            "jti": "test-cookie-jti",
            "iat": 1736996400,
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        }
        valid_token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        mock_request.headers = {
            "cookie": f"{cookie_manager.cookie_name}={valid_token}",
            "user-agent": "test-agent",
        }

        mock_session_service = MagicMock()
        mock_session_service.revoke_all_user_sessions = AsyncMock(return_value=1)
        mock_session_service_class.return_value = mock_session_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            logout(
                request=mock_request,
                response=Response(),
                current_user=mock_admin_user,
                db=mock_db,
            )
        )

        assert result["message"] == "登出成功"
        mock_blacklist_manager.add_token.assert_called_once_with(
            "test-cookie-jti", 1737000000
        )

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_logout_with_invalid_token(
        self,
        mock_session_service_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
        mock_admin_user,
    ):
        """Test logout with invalid token (should still logout)"""
        from src.api.v1.auth.auth_modules.authentication import logout
        from src.security.cookie_manager import cookie_manager

        mock_request.headers = {
            "cookie": f"{cookie_manager.cookie_name}=invalid_token",
            "user-agent": "test-agent",
        }

        mock_session_service = MagicMock()
        mock_session_service.revoke_all_user_sessions = AsyncMock(return_value=1)
        mock_session_service_class.return_value = mock_session_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            logout(
                request=mock_request,
                response=Response(),
                current_user=mock_admin_user,
                db=mock_db,
            )
        )

        assert result["message"] == "登出成功"
        # Should still revoke sessions even if token blacklisting fails
        mock_session_service.revoke_all_user_sessions.assert_called_once()

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_logout_no_client(
        self,
        mock_session_service_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
        mock_admin_user,
    ):
        """Test logout when request.client is None"""
        from src.api.v1.auth.auth_modules.authentication import logout

        mock_request.client = None
        mock_request.headers = {"user-agent": "test-agent"}

        mock_session_service = MagicMock()
        mock_session_service.revoke_all_user_sessions = AsyncMock(return_value=1)
        mock_session_service_class.return_value = mock_session_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            logout(
                request=mock_request,
                response=Response(),
                current_user=mock_admin_user,
                db=mock_db,
            )
        )

        assert result["message"] == "登出成功"


# ============================================================================
# Test: POST /refresh - Refresh Token
# ============================================================================


class TestRefreshToken:
    """Tests for POST /api/v1/auth/refresh endpoint"""

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_refresh_token_success(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
        mock_user_model,
        mock_session,
        mock_tokens,
    ):
        """Test successful token refresh"""
        from src.api.v1.auth.auth_modules.authentication import refresh_token

        mock_request.headers = {
            "user-agent": "test-agent",
            "cookie": "refresh_token=valid_refresh_token",
        }
        mock_session.device_info = '{"remember": true}'

        mock_auth_service = MagicMock()
        mock_auth_service.validate_refresh_token = AsyncMock(return_value=mock_session)
        mock_auth_service.create_tokens.return_value = mock_tokens
        mock_auth_service_class.return_value = mock_auth_service
        mock_session_service = MagicMock()
        mock_session_service.rotate_refresh_session = AsyncMock(return_value=mock_session)
        mock_session_service_class.return_value = mock_session_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        with patch(
            "src.api.v1.auth.auth_modules.authentication.cookie_manager"
        ) as mock_cookie_manager:
            result = asyncio.run(
                refresh_token(
                    request=mock_request,
                    response=Response(),
                    db=mock_db,
                )
            )
            mock_cookie_manager.set_auth_cookie.assert_called_once_with(
                ANY, mock_tokens.access_token, persistent=True
            )
            mock_cookie_manager.set_refresh_cookie.assert_called_once_with(
                ANY, mock_tokens.refresh_token, persistent=True
            )
            csrf_token = mock_cookie_manager.create_csrf_token.return_value
            mock_cookie_manager.set_csrf_cookie.assert_called_once_with(
                ANY, csrf_token, persistent=True
            )

        assert result.auth_mode == "cookie"
        assert result.message == "令牌刷新成功"
        mock_auth_service.validate_refresh_token.assert_called_once()

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_refresh_token_with_remember_false_uses_session_cookie(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
        mock_user_model,
        mock_session,
        mock_tokens,
    ):
        """remember=false should issue session-scoped cookies."""
        from src.api.v1.auth.auth_modules.authentication import refresh_token

        mock_request.headers = {
            "user-agent": "test-agent",
            "cookie": "refresh_token=valid_refresh_token",
        }
        mock_session.device_info = '{"remember": false}'

        mock_auth_service = MagicMock()
        mock_auth_service.validate_refresh_token = AsyncMock(return_value=mock_session)
        mock_auth_service.create_tokens.return_value = mock_tokens
        mock_auth_service_class.return_value = mock_auth_service
        mock_session_service = MagicMock()
        mock_session_service.rotate_refresh_session = AsyncMock(return_value=mock_session)
        mock_session_service_class.return_value = mock_session_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        with patch(
            "src.api.v1.auth.auth_modules.authentication.cookie_manager"
        ) as mock_cookie_manager:
            asyncio.run(
                refresh_token(
                    request=mock_request,
                    response=Response(),
                    db=mock_db,
                )
            )
            mock_cookie_manager.set_auth_cookie.assert_called_once_with(
                ANY, mock_tokens.access_token, persistent=False
            )
            mock_cookie_manager.set_refresh_cookie.assert_called_once_with(
                ANY, mock_tokens.refresh_token, persistent=False
            )
            csrf_token = mock_cookie_manager.create_csrf_token.return_value
            mock_cookie_manager.set_csrf_cookie.assert_called_once_with(
                ANY, csrf_token, persistent=False
            )

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_refresh_token_without_remember_keeps_legacy_persistent_cookie(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
        mock_user_model,
        mock_session,
        mock_tokens,
    ):
        """Legacy sessions without remember should keep persistent cookies."""
        from src.api.v1.auth.auth_modules.authentication import refresh_token

        mock_request.headers = {
            "user-agent": "test-agent",
            "cookie": "refresh_token=valid_refresh_token",
        }

        mock_auth_service = MagicMock()
        mock_auth_service.validate_refresh_token = AsyncMock(return_value=mock_session)
        mock_auth_service.create_tokens.return_value = mock_tokens
        mock_auth_service_class.return_value = mock_auth_service
        mock_session_service = MagicMock()
        mock_session_service.rotate_refresh_session = AsyncMock(return_value=mock_session)
        mock_session_service_class.return_value = mock_session_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        legacy_device_info_cases = [
            '{"user_agent":"legacy-browser"}',
            '{"remember":"legacy"}',
            "Chrome on Windows",
            None,
        ]

        for legacy_device_info in legacy_device_info_cases:
            mock_session.device_info = legacy_device_info

            with patch(
                "src.api.v1.auth.auth_modules.authentication.cookie_manager"
            ) as mock_cookie_manager:
                asyncio.run(
                    refresh_token(
                        request=mock_request,
                        response=Response(),
                        db=mock_db,
                    )
                )
                mock_cookie_manager.set_auth_cookie.assert_called_once_with(
                    ANY, mock_tokens.access_token, persistent=True
                )
                mock_cookie_manager.set_refresh_cookie.assert_called_once_with(
                    ANY, mock_tokens.refresh_token, persistent=True
                )
                csrf_token = mock_cookie_manager.create_csrf_token.return_value
                mock_cookie_manager.set_csrf_cookie.assert_called_once_with(
                    ANY, csrf_token, persistent=True
                )

    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_refresh_token_missing_cookie(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_request,
        mock_db,
    ):
        """Test refresh fails when refresh cookie is missing"""
        from src.api.v1.auth.auth_modules.authentication import refresh_token
        from src.core.exception_handler import InvalidRequestError

        mock_request.headers = {"user-agent": "test-agent"}
        mock_auth_service = MagicMock()
        mock_auth_service_class.return_value = mock_auth_service

        with pytest.raises(InvalidRequestError) as exc_info:
            asyncio.run(
                refresh_token(
                    request=mock_request,
                    response=Response(),
                    db=mock_db,
                )
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "刷新令牌缺失" in exc_info.value.message

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_refresh_token_invalid(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
    ):
        """Test refresh with invalid token"""
        from src.api.v1.auth.auth_modules.authentication import refresh_token
        from src.core.exception_handler import AuthenticationError
        mock_request.headers = {
            "user-agent": "test-agent",
            "cookie": "refresh_token=invalid_refresh_token",
        }

        mock_auth_service = MagicMock()
        mock_auth_service.validate_refresh_token = AsyncMock(return_value=None)
        mock_auth_service_class.return_value = mock_auth_service

        # Note: AuditLogCRUD is imported inside the function, so we need to patch at the right location
        with patch(
            "src.api.v1.auth.auth_modules.authentication.AuditLogCRUD",
            return_value=mock_audit_crud_class,
        ):
            mock_audit_crud_class.create_async = AsyncMock()
            with pytest.raises(AuthenticationError) as exc_info:
                asyncio.run(
                    refresh_token(
                        request=mock_request,
                        response=Response(),
                        db=mock_db,
                    )
                )

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "无效的刷新令牌" in exc_info.value.message

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_refresh_token_user_not_found(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
        mock_session,
    ):
        """Test refresh when user not found"""
        from src.api.v1.auth.auth_modules.authentication import refresh_token
        from src.core.exception_handler import AuthenticationError
        mock_request.headers = {
            "user-agent": "test-agent",
            "cookie": "refresh_token=valid_refresh_token",
        }

        mock_auth_service = MagicMock()
        # validate_refresh_token returns a UserSession (or None)
        mock_auth_service.validate_refresh_token = AsyncMock(return_value=None)
        mock_auth_service_class.return_value = mock_auth_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        with pytest.raises(AuthenticationError) as exc_info:
            asyncio.run(
                refresh_token(
                    request=mock_request,
                    response=Response(),
                    db=mock_db,
                )
            )

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "无效的刷新令牌" in exc_info.value.message

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_refresh_token_user_inactive(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
        mock_user_model,
        mock_session,
    ):
        """Test refresh when user is inactive"""
        from src.api.v1.auth.auth_modules.authentication import refresh_token
        from src.core.exception_handler import AuthenticationError
        mock_request.headers = {
            "user-agent": "test-agent",
            "cookie": "refresh_token=valid_refresh_token",
        }

        mock_session.user.is_active = False

        mock_auth_service = MagicMock()
        mock_auth_service.validate_refresh_token = AsyncMock(return_value=mock_session)
        mock_auth_service_class.return_value = mock_auth_service
        mock_session_service = MagicMock()
        mock_session_service.revoke_session = AsyncMock(return_value=True)
        mock_session_service_class.return_value = mock_session_service

        with pytest.raises(AuthenticationError) as exc_info:
            asyncio.run(
                refresh_token(
                    request=mock_request,
                    response=Response(),
                    db=mock_db,
                )
            )

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "用户不存在或已被禁用" in exc_info.value.message

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_refresh_token_ip_change(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
        mock_user_model,
        mock_session,
        mock_tokens,
    ):
        """Test refresh with IP change still calls service and succeeds when service accepts"""
        from src.api.v1.auth.auth_modules.authentication import refresh_token
        mock_request.headers = {
            "user-agent": "test-agent",
            "cookie": "refresh_token=valid_refresh_token",
        }

        mock_session.ip_address = "192.168.1.1"  # Different from request.client.host

        mock_auth_service = MagicMock()
        mock_auth_service.validate_refresh_token = AsyncMock(return_value=mock_session)
        mock_auth_service.create_tokens.return_value = mock_tokens
        mock_auth_service_class.return_value = mock_auth_service
        mock_session_service = MagicMock()
        mock_session_service.rotate_refresh_session = AsyncMock(return_value=mock_session)
        mock_session_service_class.return_value = mock_session_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            refresh_token(
                request=mock_request,
                response=Response(),
                db=mock_db,
            )
        )

        assert result.auth_mode == "cookie"

    @patch("src.api.v1.auth.auth_modules.authentication.AuditLogCRUD")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService")
    @patch("src.api.v1.auth.auth_modules.authentication.AsyncSessionService")
    def test_refresh_token_no_client(
        self,
        mock_session_service_class,
        mock_auth_service_class,
        mock_audit_crud_class,
        mock_request,
        mock_db,
        mock_user_model,
        mock_session,
        mock_tokens,
    ):
        """Test refresh when request.client is None"""
        from src.api.v1.auth.auth_modules.authentication import refresh_token
        mock_request.headers = {
            "user-agent": "test-agent",
            "cookie": "refresh_token=valid_refresh_token",
        }

        mock_request.client = None

        mock_auth_service = MagicMock()
        mock_auth_service.validate_refresh_token = AsyncMock(return_value=mock_session)
        mock_auth_service.create_tokens.return_value = mock_tokens
        mock_auth_service_class.return_value = mock_auth_service
        mock_session_service = MagicMock()
        mock_session_service.rotate_refresh_session = AsyncMock(return_value=mock_session)
        mock_session_service_class.return_value = mock_session_service

        mock_audit_crud = MagicMock()
        mock_audit_crud.create_async = AsyncMock()
        mock_audit_crud_class.return_value = mock_audit_crud

        result = asyncio.run(
            refresh_token(
                request=mock_request,
                response=Response(),
                db=mock_db,
            )
        )

        assert result.auth_mode == "cookie"


# ============================================================================
# Test: GET /me - Get Current User Info
# ============================================================================


class TestGetCurrentUserInfo:
    """Tests for GET /api/v1/auth/me endpoint"""

    def test_get_current_user_info_success(
        self, mock_admin_user, mock_db, mock_rbac_service
    ):
        """Test getting current user info successfully"""
        from src.api.v1.auth.auth_modules.authentication import get_current_user_info

        mock_rbac_service.get_user_role_summary.return_value = ADMIN_ROLE_SUMMARY

        result = asyncio.run(
            get_current_user_info(current_user=mock_admin_user, db=mock_db)
        )

        assert result["username"] == "admin"
        assert result["email"] == "admin@example.com"
        assert result["full_name"] == "Admin User"
        assert result["id"] == "admin-id"
        assert result["role_id"] == "role-admin-id"
        assert result["is_active"] is True
        assert result["is_admin"] is True
        assert result["session_status"] == "active"
        assert "timestamp" in result

    def test_get_current_user_info_regular_user(
        self, mock_regular_user, mock_db, mock_rbac_service
    ):
        """Test getting current user info for regular user"""
        from src.api.v1.auth.auth_modules.authentication import get_current_user_info

        mock_rbac_service.get_user_role_summary.return_value = USER_ROLE_SUMMARY

        result = asyncio.run(
            get_current_user_info(current_user=mock_regular_user, db=mock_db)
        )

        assert result["username"] == "testuser"
        assert result["role_id"] == "role-user-id"
        assert result["is_admin"] is False


# ============================================================================
# Test: GET /test-features - Test Features Endpoint
# ============================================================================


class TestTestFeatures:
    """Tests for GET /api/v1/debug/test-features endpoint"""

    @patch.dict("os.environ", {"DEBUG": "true"})
    def test_test_features(self):
        """Test features endpoint"""
        import os

        os.environ["DEBUG"] = "true"

        from src.api.v1.debug.auth_debug import test_features

        result = asyncio.run(test_features())

        assert result["success"] is True
        assert result["message"] == "功能测试正常"
        assert "timestamp" in result


# ============================================================================
# Test: GET /debug-auth - Debug Authentication Flow
# ============================================================================


class TestDebugAuth:
    """Tests for GET /api/v1/debug/auth endpoint"""

    @patch("src.api.v1.debug.auth_debug.RBACService")
    @patch("src.api.v1.debug.auth_debug.AsyncAuthenticationService")
    @patch("src.api.v1.debug.auth_debug.AsyncUserManagementService")
    @patch("src.api.v1.debug.auth_debug.PasswordService")
    def test_debug_auth_success(
        self,
        mock_password_service_class,
        mock_user_service_class,
        mock_auth_service_class,
        mock_rbac_class,
        mock_db,
    ):
        """Test debug authentication endpoint"""
        import os

        os.environ["DEBUG"] = "true"
        os.environ["DEBUG_AUTH_PASSWORD"] = "test-password"

        from src.api.v1.debug.auth_debug import debug_auth

        mock_admin_user = MagicMock()
        mock_admin_user.id = "admin-id"
        mock_admin_user.username = "admin"
        mock_admin_user.password_hash = "hashed_password"

        mock_authenticated_user = MagicMock()

        mock_tokens = MagicMock()
        mock_tokens.access_token = "test_access_token_with_sufficient_length"

        mock_user_service = MagicMock()
        mock_user_service.get_user_by_username = AsyncMock(return_value=mock_admin_user)
        mock_user_service_class.return_value = mock_user_service

        mock_password_service = MagicMock()
        mock_password_service.verify_password.return_value = True
        mock_password_service_class.return_value = mock_password_service

        mock_auth_service = MagicMock()
        mock_auth_service.authenticate_user = AsyncMock(
            return_value=mock_authenticated_user
        )
        mock_auth_service.create_tokens.return_value = mock_tokens
        mock_auth_service_class.return_value = mock_auth_service

        mock_rbac = mock_rbac_class.return_value
        mock_rbac.get_user_role_summary = AsyncMock(return_value=ADMIN_ROLE_SUMMARY)

        result = asyncio.run(debug_auth(db=mock_db))

        assert result["admin_user_found"] is True
        assert result["admin_username"] == "admin"
        assert result["admin_roles"] == ["admin"]
        assert result["password_valid"] is True
        assert result["auth_success"] is True
        assert result["token_success"] is True

    @patch("src.api.v1.debug.auth_debug.RBACService")
    @patch("src.api.v1.debug.auth_debug.AsyncAuthenticationService")
    @patch("src.api.v1.debug.auth_debug.AsyncUserManagementService")
    @patch("src.api.v1.debug.auth_debug.PasswordService")
    def test_debug_auth_admin_not_found(
        self,
        mock_password_service_class,
        mock_user_service_class,
        mock_auth_service_class,
        mock_rbac_class,
        mock_db,
    ):
        """Test debug auth when admin user not found"""
        import os

        os.environ["DEBUG"] = "true"
        os.environ["DEBUG_AUTH_PASSWORD"] = "test-password"

        from src.api.v1.debug.auth_debug import debug_auth

        mock_user_service = MagicMock()
        mock_user_service.get_user_by_username = AsyncMock(return_value=None)
        mock_user_service_class.return_value = mock_user_service

        result = asyncio.run(debug_auth(db=mock_db))

        assert result["error"] == "Test user 'admin' not found"

    @patch("src.api.v1.debug.auth_debug.RBACService")
    @patch("src.api.v1.debug.auth_debug.AsyncAuthenticationService")
    @patch("src.api.v1.debug.auth_debug.AsyncUserManagementService")
    @patch("src.api.v1.debug.auth_debug.PasswordService")
    def test_debug_auth_authenticate_exception(
        self,
        mock_password_service_class,
        mock_user_service_class,
        mock_auth_service_class,
        mock_rbac_class,
        mock_db,
    ):
        """Test debug auth when authenticate raises exception"""
        import os

        os.environ["DEBUG"] = "true"
        os.environ["DEBUG_AUTH_PASSWORD"] = "test-password"

        from src.api.v1.debug.auth_debug import debug_auth

        mock_admin_user = MagicMock()
        mock_admin_user.id = "admin-id"
        mock_admin_user.username = "admin"
        mock_admin_user.password_hash = "hashed_password"

        mock_user_service = MagicMock()
        mock_user_service.get_user_by_username = AsyncMock(return_value=mock_admin_user)
        mock_user_service_class.return_value = mock_user_service

        mock_password_service = MagicMock()
        mock_password_service.verify_password.return_value = True
        mock_password_service_class.return_value = mock_password_service

        mock_auth_service = MagicMock()
        mock_auth_service.authenticate_user = AsyncMock(
            side_effect=Exception("Auth failed")
        )
        mock_auth_service_class.return_value = mock_auth_service

        mock_rbac = mock_rbac_class.return_value
        mock_rbac.get_user_role_summary = AsyncMock(return_value=ADMIN_ROLE_SUMMARY)

        result = asyncio.run(debug_auth(db=mock_db))

        assert result["admin_user_found"] is True
        assert result["auth_success"] is False
        assert result["auth_error"] == "Auth failed"

    @patch("src.api.v1.debug.auth_debug.RBACService")
    @patch("src.api.v1.debug.auth_debug.AsyncAuthenticationService")
    @patch("src.api.v1.debug.auth_debug.AsyncUserManagementService")
    @patch("src.api.v1.debug.auth_debug.PasswordService")
    def test_debug_auth_token_exception(
        self,
        mock_password_service_class,
        mock_user_service_class,
        mock_auth_service_class,
        mock_rbac_class,
        mock_db,
    ):
        """Test debug auth when token creation raises exception"""
        import os

        os.environ["DEBUG"] = "true"
        os.environ["DEBUG_AUTH_PASSWORD"] = "test-password"

        from src.api.v1.debug.auth_debug import debug_auth

        mock_admin_user = MagicMock()
        mock_admin_user.id = "admin-id"
        mock_admin_user.username = "admin"
        mock_admin_user.password_hash = "hashed_password"

        mock_authenticated_user = MagicMock()

        mock_user_service = MagicMock()
        mock_user_service.get_user_by_username = AsyncMock(return_value=mock_admin_user)
        mock_user_service_class.return_value = mock_user_service

        mock_password_service = MagicMock()
        mock_password_service.verify_password.return_value = True
        mock_password_service_class.return_value = mock_password_service

        mock_auth_service = MagicMock()
        mock_auth_service.authenticate_user = AsyncMock(
            return_value=mock_authenticated_user
        )
        # Make create_tokens raise an exception when authenticated_user is truthy
        mock_auth_service.create_tokens.side_effect = Exception("Token creation failed")
        mock_auth_service_class.return_value = mock_auth_service

        mock_rbac = mock_rbac_class.return_value
        mock_rbac.get_user_role_summary = AsyncMock(return_value=ADMIN_ROLE_SUMMARY)

        result = asyncio.run(debug_auth(db=mock_db))

        assert result["admin_user_found"] is True
        assert result["auth_success"] is True
        assert result["token_success"] is False
        assert result["token_error"] == "Token creation failed"
        assert result["access_token_length"] == 0

    @patch("src.api.v1.debug.auth_debug.RBACService")
    @patch("src.api.v1.debug.auth_debug.AsyncAuthenticationService")
    @patch("src.api.v1.debug.auth_debug.AsyncUserManagementService")
    @patch("src.api.v1.debug.auth_debug.PasswordService")
    def test_debug_auth_general_exception(
        self,
        mock_password_service_class,
        mock_user_service_class,
        mock_auth_service_class,
        mock_rbac_class,
        mock_db,
    ):
        """Test debug auth with general exception"""
        import os

        os.environ["DEBUG"] = "true"
        os.environ["DEBUG_AUTH_PASSWORD"] = "test-password"

        from src.api.v1.debug.auth_debug import debug_auth

        MagicMock()
        mock_auth_service_class.side_effect = Exception("Service init failed")

        result = asyncio.run(debug_auth(db=mock_db))

        assert "error" in result
        assert "Debug endpoint error" in result["error"]


# ============================================================================
# Test: GET /test-me-debug - Debug ME Endpoint
# ============================================================================


class TestTestMeDebug:
    """Tests for GET /api/v1/debug/me endpoint"""

    def test_me_debug(self, mock_admin_user, mock_db):
        """Test ME debug endpoint"""
        import os

        os.environ["DEBUG"] = "true"

        from src.api.v1.debug.auth_debug import test_me_debug

        with patch("src.api.v1.debug.auth_debug.RBACService") as mock_rbac_class:
            mock_rbac = mock_rbac_class.return_value
            mock_rbac.get_user_role_summary = AsyncMock(
                return_value=ADMIN_ROLE_SUMMARY
            )
            result = asyncio.run(
                test_me_debug(current_user=mock_admin_user, db=mock_db)
            )

        assert result["username"] == "admin"
        assert result["email"] == "admin@example.com"
        assert result["full_name"] == "Admin User"
        assert result["id"] == "admin-id"
        assert result["role_id"] == "role-admin-id"
        assert result["is_active"] is True
        assert result["is_admin"] is True
        assert result["session_status"] == "active"
        assert "timestamp" in result
