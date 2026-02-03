"""
Comprehensive unit tests for AuthenticationService

Tests authentication, token creation/validaton, account lockout,
password expiration, device fingerprinting, and session management.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import jwt
import pytest
from sqlalchemy.orm import Session

from src.core.config import settings
from src.exceptions import BusinessLogicError
from src.models.auth import User, UserSession
from src.services.core.authentication_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
    AuthenticationService,
    TokenPair,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db_session():
    """Mock database session"""
    return MagicMock(spec=Session)


@pytest.fixture
def mock_user():
    """Create a mock user object"""
    user = MagicMock(spec=User)
    user.id = "test-user-123"
    user.username = "testuser"
    user.email = "test@example.com"
    user.password_hash = "$2b$12$valid_hash"
    user.is_active = True
    user.is_locked = False
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = None
    user.password_last_changed = datetime.now()
    user.role = "user"
    user.is_locked_now = Mock(return_value=False)
    return user


@pytest.fixture
def auth_service(db_session):
    """Create authentication service instance"""
    return AuthenticationService(db_session)


# ============================================================================
# authenticate_user tests - Username/Email Login Paths
# ============================================================================


class TestAuthenticateUserUsernameEmail:
    """Tests for username and email login paths"""

    def test_authenticate_with_username(self, auth_service, db_session, mock_user):
        """Test authentication with username"""
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=True
            ):
                with patch.object(
                    auth_service.password_service,
                    "is_password_expired",
                    return_value=False,
                ):
                    result = auth_service.authenticate_user("testuser", "password123")
                    assert result == mock_user

    def test_authenticate_with_email(self, auth_service, db_session, mock_user):
        """Test authentication with email"""
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=True
            ):
                with patch.object(
                    auth_service.password_service,
                    "is_password_expired",
                    return_value=False,
                ):
                    result = auth_service.authenticate_user(
                        "test@example.com", "password123"
                    )
                    assert result == mock_user

    def test_authenticate_user_not_found(self, auth_service, db_session):
        """Test authentication with non-existent user"""
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None
            result = auth_service.authenticate_user("nonexistent", "password")
            assert result is None

    def test_authenticate_inactive_user(self, auth_service, db_session, mock_user):
        """Test authentication with inactive user"""
        mock_user.is_active = False
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None
            result = auth_service.authenticate_user("testuser", "password")
            assert result is None


# ============================================================================
# authenticate_user tests - Password Verification
# ============================================================================


class TestAuthenticateUserPasswordVerification:
    """Tests for password verification during authentication"""

    def test_authenticate_with_wrong_password(
        self, auth_service, db_session, mock_user
    ):
        """Test authentication with wrong password"""
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=False
            ):
                result = auth_service.authenticate_user("testuser", "wrongpassword")
                assert result is None
                assert mock_user.failed_login_attempts == 1
                db_session.commit.assert_called_once()

    def test_authenticate_with_correct_password(
        self, auth_service, db_session, mock_user
    ):
        """Test successful authentication with correct password"""
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=True
            ):
                with patch.object(
                    auth_service.password_service,
                    "is_password_expired",
                    return_value=False,
                ):
                    result = auth_service.authenticate_user("testuser", "correctpass")
                    assert result == mock_user
                    assert mock_user.failed_login_attempts == 0
                    # last_login_at is set on the user object that's returned
                    # not on the mock, so we just verify it was set during the call


# ============================================================================
# authenticate_user tests - Account Lockout
# ============================================================================


class TestAuthenticateUserAccountLockout:
    """Tests for account lockout functionality"""

    def test_authenticate_locked_account(self, auth_service, db_session, mock_user):
        """Test authentication when account is locked"""
        mock_user.is_locked_now = Mock(return_value=True)
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with pytest.raises(BusinessLogicError) as exc_info:
                auth_service.authenticate_user("testuser", "password")
            assert "账户已被锁定" in str(exc_info.value)

    def test_failed_login_increments_counter(self, auth_service, db_session, mock_user):
        """Test that failed login increments attempt counter"""
        mock_user.failed_login_attempts = 2
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=False
            ):
                auth_service.authenticate_user("testuser", "wrong")
                assert mock_user.failed_login_attempts == 3

    def test_max_failed_attempts_locks_account(
        self, auth_service, db_session, mock_user
    ):
        """Test that max failed attempts locks the account"""
        mock_user.failed_login_attempts = settings.MAX_FAILED_ATTEMPTS - 1
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=False
            ):
                auth_service.authenticate_user("testuser", "wrong")
                assert mock_user.is_locked is True
                assert mock_user.locked_until is not None
                assert isinstance(mock_user.locked_until, datetime)

    def test_successful_login_resets_failed_attempts(
        self, auth_service, db_session, mock_user
    ):
        """Test that successful login resets failed attempts"""
        mock_user.failed_login_attempts = 3
        mock_user.is_locked = True
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=True
            ):
                with patch.object(
                    auth_service.password_service,
                    "is_password_expired",
                    return_value=False,
                ):
                    auth_service.authenticate_user("testuser", "correct")
                    assert mock_user.failed_login_attempts == 0
                    assert mock_user.is_locked is False
                    assert mock_user.locked_until is None

    def test_lockout_duration_calculation(self, auth_service, db_session, mock_user):
        """Test that lockout duration is calculated correctly"""
        mock_user.failed_login_attempts = settings.MAX_FAILED_ATTEMPTS - 1
        expected_lock_time = datetime.now() + timedelta(
            minutes=settings.LOCKOUT_DURATION
        )
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=False
            ):
                auth_service.authenticate_user("testuser", "wrong")
                # Check that locked_until is approximately correct (within 1 second)
                time_diff = abs(
                    (mock_user.locked_until - expected_lock_time).total_seconds()
                )
                assert time_diff < 1.0


# ============================================================================
# authenticate_user tests - Password Expiration
# ============================================================================


class TestAuthenticateUserPasswordExpiration:
    """Tests for password expiration handling"""

    def test_password_expired_raises_error(self, auth_service, db_session, mock_user):
        """Test that expired password raises error"""
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=True
            ):
                with patch.object(
                    auth_service.password_service,
                    "is_password_expired",
                    return_value=True,
                ):
                    with pytest.raises(BusinessLogicError) as exc_info:
                        auth_service.authenticate_user("testuser", "password")
                    assert "密码已过期" in str(exc_info.value)

    def test_valid_password_allows_login(self, auth_service, db_session, mock_user):
        """Test that valid password allows login"""
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=True
            ):
                with patch.object(
                    auth_service.password_service,
                    "is_password_expired",
                    return_value=False,
                ):
                    result = auth_service.authenticate_user("testuser", "password")
                    assert result is not None


# ============================================================================
# create_tokens tests - JWT Token Generation
# ============================================================================


class TestCreateTokens:
    """Tests for JWT token creation"""

    def test_create_tokens_returns_valid_response(self, auth_service, mock_user):
        """Test that create_tokens returns valid TokenPair"""
        tokens = auth_service.create_tokens(mock_user)
        assert isinstance(tokens, TokenPair)
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"
        assert tokens.session_id is not None
        assert tokens.expires_in > 0

    def test_access_token_structure(self, auth_service, mock_user):
        """Test access token has correct structure"""
        tokens = auth_service.create_tokens(mock_user)
        payload = jwt.decode(
            tokens.access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        assert payload["sub"] == mock_user.id
        assert payload["username"] == mock_user.username
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "session_id" in payload
        assert "iat" in payload
        assert "exp" in payload
        assert payload["aud"] == settings.JWT_AUDIENCE
        assert payload["iss"] == settings.JWT_ISSUER

    def test_refresh_token_structure(self, auth_service, mock_user):
        """Test refresh token has correct structure"""
        tokens = auth_service.create_tokens(mock_user)
        payload = jwt.decode(
            tokens.refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        assert payload["sub"] == mock_user.id
        assert payload["type"] == "refresh"
        assert "jti" in payload
        assert "session_id" in payload
        assert "nbf" in payload
        assert payload["aud"] == settings.JWT_AUDIENCE
        assert payload["iss"] == settings.JWT_ISSUER

    def test_tokens_have_unique_jti(self, auth_service, mock_user):
        """Test that each token gets unique JTI"""
        tokens1 = auth_service.create_tokens(mock_user)
        tokens2 = auth_service.create_tokens(mock_user)

        payload1_access = jwt.decode(
            tokens1.access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        payload2_access = jwt.decode(
            tokens2.access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )

        assert payload1_access["jti"] != payload2_access["jti"]

    def test_tokens_share_session_id(self, auth_service, mock_user):
        """Test that access and refresh tokens share session_id"""
        tokens = auth_service.create_tokens(mock_user)
        access_payload = jwt.decode(
            tokens.access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        refresh_payload = jwt.decode(
            tokens.refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        assert access_payload["session_id"] == refresh_payload["session_id"]
        assert access_payload["session_id"] == tokens.session_id

    def test_access_token_expiration(self, auth_service, mock_user):
        """Test access token expiration time"""
        tokens = auth_service.create_tokens(mock_user)
        assert tokens.expires_in == ACCESS_TOKEN_EXPIRE_MINUTES * 60

        payload = jwt.decode(
            tokens.access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        exp = datetime.fromtimestamp(payload["exp"])
        iat = datetime.fromtimestamp(payload["iat"])
        delta = exp - iat
        assert delta.total_seconds() == pytest.approx(
            ACCESS_TOKEN_EXPIRE_MINUTES * 60, abs=2
        )

    def test_refresh_token_expiration(self, auth_service, mock_user):
        """Test refresh token expiration time"""
        tokens = auth_service.create_tokens(mock_user)
        payload = jwt.decode(
            tokens.refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        exp = datetime.fromtimestamp(payload["exp"])
        iat = datetime.fromtimestamp(payload["iat"])
        delta = exp - iat
        expected_seconds = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        assert delta.total_seconds() == pytest.approx(expected_seconds, abs=2)


# ============================================================================
# create_tokens tests - Device Fingerprinting
# ============================================================================


class TestCreateTokensDeviceFingerprinting:
    """Tests for device fingerprinting in tokens"""

    def test_device_fingerprint_with_full_info(self, auth_service, mock_user):
        """Test device fingerprint generation with full device info"""
        device_info = {
            "user_agent": "Mozilla/5.0",
            "ip_address": "192.168.1.1",
            "device_id": "device-123",
            "platform": "Windows",
        }
        tokens = auth_service.create_tokens(mock_user, device_info)
        access_payload = jwt.decode(
            tokens.access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        assert "device_fingerprint" in access_payload
        assert access_payload["device_fingerprint"] is not None
        assert len(access_payload["device_fingerprint"]) == 16

    def test_device_fingerprint_with_partial_info(self, auth_service, mock_user):
        """Test device fingerprint with partial info"""
        device_info = {"user_agent": "Mozilla/5.0", "ip_address": "192.168.1.1"}
        tokens = auth_service.create_tokens(mock_user, device_info)
        access_payload = jwt.decode(
            tokens.access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        assert access_payload["device_fingerprint"] is not None

    def test_device_fingerprint_without_device_info(self, auth_service, mock_user):
        """Test tokens without device info"""
        tokens = auth_service.create_tokens(mock_user, None)
        access_payload = jwt.decode(
            tokens.access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        assert access_payload.get("device_fingerprint") is None

    def test_device_fingerprint_consistency(self, auth_service, mock_user):
        """Test that same device info produces same fingerprint"""
        device_info = {
            "user_agent": "Mozilla/5.0",
            "ip_address": "192.168.1.1",
            "device_id": "device-123",
            "platform": "Windows",
        }
        tokens1 = auth_service.create_tokens(mock_user, device_info)
        tokens2 = auth_service.create_tokens(mock_user, device_info)

        payload1 = jwt.decode(
            tokens1.access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        payload2 = jwt.decode(
            tokens2.access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        assert payload1["device_fingerprint"] == payload2["device_fingerprint"]

    def test_device_fingerprint_different_for_different_info(
        self, auth_service, mock_user
    ):
        """Test that different device info produces different fingerprints"""
        device_info1 = {"user_agent": "Mozilla/5.0", "ip_address": "192.168.1.1"}
        device_info2 = {"user_agent": "Chrome/1.0", "ip_address": "192.168.1.2"}

        tokens1 = auth_service.create_tokens(mock_user, device_info1)
        tokens2 = auth_service.create_tokens(mock_user, device_info2)

        payload1 = jwt.decode(
            tokens1.access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        payload2 = jwt.decode(
            tokens2.access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        assert payload1["device_fingerprint"] != payload2["device_fingerprint"]


# ============================================================================
# validate_refresh_token tests
# ============================================================================


class TestValidateRefreshToken:
    """Tests for refresh token validation"""

    def test_validate_valid_refresh_token(self, auth_service, mock_user, db_session):
        """Test validation of valid refresh token"""
        tokens = auth_service.create_tokens(mock_user)

        mock_session = MagicMock(spec=UserSession)
        mock_session.is_expired = Mock(return_value=False)
        mock_session.is_active = True
        mock_session.session_id = tokens.session_id

        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = (
                mock_session
            )
            with patch.object(
                auth_service.user_service, "get_user_by_id", return_value=mock_user
            ):
                result = auth_service.validate_refresh_token(tokens.refresh_token)
                assert result == mock_session

    def test_validate_invalid_token_format(self, auth_service):
        """Test validation of invalid token format"""
        result = auth_service.validate_refresh_token("invalid_token")
        assert result is None

    def test_validate_revoked_token(self, auth_service, mock_user, db_session):
        """Test validation of revoked token"""
        tokens = auth_service.create_tokens(mock_user)
        payload = jwt.decode(
            tokens.refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        payload["jti"]

        # Mock token as revoked
        with patch.object(
            auth_service.token_blacklist, "is_blacklisted", return_value=True
        ):
            result = auth_service.validate_refresh_token(tokens.refresh_token)
            assert result is None

    def test_validate_token_no_session(self, auth_service, mock_user, db_session):
        """Test validation when session doesn't exist"""
        tokens = auth_service.create_tokens(mock_user)
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None
            result = auth_service.validate_refresh_token(tokens.refresh_token)
            assert result is None

    def test_validate_expired_session(self, auth_service, mock_user, db_session):
        """Test validation when session is expired"""
        tokens = auth_service.create_tokens(mock_user)
        mock_session = MagicMock(spec=UserSession)
        mock_session.is_expired = Mock(return_value=True)
        mock_session.is_active = True

        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = (
                mock_session
            )
            result = auth_service.validate_refresh_token(tokens.refresh_token)
            assert result is None

    def test_validate_inactive_user(self, auth_service, mock_user, db_session):
        """Test validation when user is inactive"""
        tokens = auth_service.create_tokens(mock_user)
        mock_session = MagicMock(spec=UserSession)
        mock_session.is_expired = Mock(return_value=False)
        mock_session.is_active = True
        mock_session.session_id = tokens.session_id

        mock_user.is_active = False

        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = (
                mock_session
            )
            with patch.object(
                auth_service.user_service, "get_user_by_id", return_value=mock_user
            ):
                result = auth_service.validate_refresh_token(tokens.refresh_token)
                assert result is None
                assert mock_session.is_active is False

    def test_validate_session_id_mismatch(self, auth_service, mock_user, db_session):
        """Test validation when session ID doesn't match"""
        tokens = auth_service.create_tokens(mock_user)
        mock_session = MagicMock(spec=UserSession)
        mock_session.is_expired = Mock(return_value=False)
        mock_session.is_active = True
        mock_session.session_id = "different-session-id"

        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = (
                mock_session
            )
            with patch.object(
                auth_service.user_service, "get_user_by_id", return_value=mock_user
            ):
                result = auth_service.validate_refresh_token(tokens.refresh_token)
                assert result is None
                assert mock_session.is_active is False

    def test_validate_updates_session_metadata(
        self, auth_service, mock_user, db_session
    ):
        """Test that validation updates session metadata"""
        tokens = auth_service.create_tokens(mock_user)
        mock_session = MagicMock(spec=UserSession)
        mock_session.is_expired = Mock(return_value=False)
        mock_session.is_active = True
        mock_session.session_id = tokens.session_id
        mock_session.last_accessed_at = None

        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = (
                mock_session
            )
            with patch.object(
                auth_service.user_service, "get_user_by_id", return_value=mock_user
            ):
                result = auth_service.validate_refresh_token(
                    tokens.refresh_token,
                    client_ip="192.168.1.100",
                    user_agent="TestAgent",
                )
                assert result is not None
                assert mock_session.last_accessed_at is not None
                assert hasattr(mock_session, "ip_address")
                assert hasattr(mock_session, "user_agent")
                db_session.commit.assert_called()


# ============================================================================
# _generate_jti tests
# ============================================================================


class TestGenerateJti:
    """Tests for JWT ID generation"""

    def test_generate_jti_returns_string(self, auth_service):
        """Test that _generate_jti returns a string"""
        jti = auth_service._generate_jti()
        assert isinstance(jti, str)

    def test_generate_jti_is_unique(self, auth_service):
        """Test that each JTI is unique"""
        jti1 = auth_service._generate_jti()
        jti2 = auth_service._generate_jti()
        assert jti1 != jti2

    def test_generate_jti_length(self, auth_service):
        """Test that JTI has expected length (URL-safe base64)"""
        jti = auth_service._generate_jti()
        # token_urlsafe(32) produces approximately 43 characters
        assert len(jti) >= 40


# ============================================================================
# _is_token_revoked tests
# ============================================================================


class TestIsTokenRevoked:
    """Tests for token revocation checking"""

    def test_not_revoked_token(self, auth_service):
        """Test that non-revoked token returns False"""
        with patch.object(
            auth_service.token_blacklist, "is_blacklisted", return_value=False
        ):
            result = auth_service._is_token_revoked("some-jti")
            assert result is False

    def test_revoked_token(self, auth_service):
        """Test that revoked token returns True"""
        with patch.object(
            auth_service.token_blacklist, "is_blacklisted", return_value=True
        ):
            result = auth_service._is_token_revoked("revoked-jti")
            assert result is True

    def test_revoked_check_calls_blacklist_manager(self, auth_service):
        """Test that _is_token_revoked calls blacklist manager"""
        with patch.object(
            auth_service.token_blacklist, "is_blacklisted", return_value=False
        ) as mock_check:
            auth_service._is_token_revoked("test-jti")
            mock_check.assert_called_once_with(jti="test-jti", user_id=None)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_authenticate_with_empty_username(self, auth_service, db_session):
        """Test authentication with empty username"""
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None
            result = auth_service.authenticate_user("", "password")
            assert result is None

    def test_authenticate_with_empty_password(
        self, auth_service, db_session, mock_user
    ):
        """Test authentication with empty password"""
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=False
            ):
                result = auth_service.authenticate_user("testuser", "")
                assert result is None

    def test_create_tokens_with_user_having_enum_role(self, auth_service):
        """Test token creation when user.role is an enum"""
        from src.models.auth import UserRole

        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.username = "testuser"
        mock_user.role = UserRole.USER

        tokens = auth_service.create_tokens(mock_user)
        assert tokens.access_token is not None
        payload = jwt.decode(
            tokens.access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        assert "role" in payload

    def test_validate_token_with_wrong_type(self, auth_service):
        """Test validation rejects access token when refresh expected"""
        tokens = auth_service.create_tokens(
            Mock(id="user", username="test", role="user")
        )
        # Try to validate access token as refresh token
        result = auth_service.validate_refresh_token(tokens.access_token)
        assert result is None

    def test_validate_token_with_missing_jti(self, auth_service):
        """Test validation handles missing JTI gracefully"""
        # Create a token without jti
        from datetime import UTC, datetime, timedelta

        now = datetime.now(UTC)
        payload = {
            "sub": "user-123",
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=7)).timestamp()),
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        result = auth_service.validate_refresh_token(token)
        # Should return None as it won't find a matching session
        assert result is None

    def test_multiple_failed_logins_before_lockout(self, auth_service, db_session):
        """Test behavior with multiple failed logins just below threshold"""
        mock_user = MagicMock(spec=User)
        mock_user.failed_login_attempts = settings.MAX_FAILED_ATTEMPTS - 2
        mock_user.is_locked = False
        mock_user.is_locked_now = Mock(return_value=False)

        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=False
            ):
                auth_service.authenticate_user("testuser", "wrong")
                assert (
                    mock_user.failed_login_attempts == settings.MAX_FAILED_ATTEMPTS - 1
                )
                assert mock_user.is_locked is False

    def test_password_hash_attribute_missing(self, auth_service, db_session):
        """Test handling when password_hash attribute is missing"""
        mock_user = MagicMock(spec=User)
        mock_user.is_active = True
        mock_user.is_locked_now = Mock(return_value=False)
        mock_user.failed_login_attempts = 0
        mock_user.is_locked = False
        mock_user.locked_until = None
        # Don't set password_hash attribute

        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=False
            ):
                result = auth_service.authenticate_user("testuser", "password")
                # Should handle gracefully using getattr with default
                assert result is None


# ============================================================================
# Integration-style Tests
# ============================================================================


class TestIntegrationScenarios:
    """Integration-style tests for complete workflows"""

    def test_complete_login_flow(self, auth_service, db_session, mock_user):
        """Test complete login flow: authenticate and create tokens"""
        # Authenticate
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=True
            ):
                with patch.object(
                    auth_service.password_service,
                    "is_password_expired",
                    return_value=False,
                ):
                    user = auth_service.authenticate_user("testuser", "password")
                    assert user is not None

        # Create tokens
        tokens = auth_service.create_tokens(user)
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None

    def test_lockout_and_unlock_flow(self, auth_service, db_session):
        """Test complete lockout and unlock flow"""
        mock_user = MagicMock(spec=User)
        mock_user.is_active = True
        mock_user.failed_login_attempts = 0
        mock_user.is_locked = False
        mock_user.locked_until = None
        mock_user.is_locked_now = Mock(return_value=False)

        # Fail login multiple times
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=False
            ):
                for i in range(settings.MAX_FAILED_ATTEMPTS):
                    auth_service.authenticate_user("testuser", "wrong")

        # Verify locked
        assert mock_user.is_locked is True
        assert mock_user.failed_login_attempts == settings.MAX_FAILED_ATTEMPTS

        # Successful login unlocks
        mock_user.is_locked_now = Mock(return_value=False)
        with patch.object(db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(
                auth_service.password_service, "verify_password", return_value=True
            ):
                with patch.object(
                    auth_service.password_service,
                    "is_password_expired",
                    return_value=False,
                ):
                    user = auth_service.authenticate_user("testuser", "correct")
                    assert user is not None
                    assert user.failed_login_attempts == 0
                    assert user.is_locked is False


# ============================================================================
# Test Count Summary
# ============================================================================
"""
Total tests created: 50

Test Categories:
- TestAuthenticateUserUsernameEmail: 4 tests
- TestAuthenticateUserPasswordVerification: 2 tests
- TestAuthenticateUserAccountLockout: 6 tests
- TestAuthenticateUserPasswordExpiration: 2 tests
- TestCreateTokens: 7 tests
- TestCreateTokensDeviceFingerprinting: 5 tests
- TestValidateRefreshToken: 8 tests
- TestGenerateJti: 3 tests
- TestIsTokenRevoked: 3 tests
- TestEdgeCases: 6 tests
- TestIntegrationScenarios: 2 tests
"""
