"""
Tests for AuthenticationService (services/core/authentication_service.py)
"""

from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, Mock, patch
import pytest
from sqlalchemy.orm import Session

from src.services.core.authentication_service import AuthenticationService
from src.models.auth import User
from src.exceptions import BusinessLogicError


class TestAuthenticateUser:
    """Tests for authenticate_user method"""

    def test_authenticate_user_success(self, db_session):
        """Test successful user authentication"""
        service = AuthenticationService(db_session)
        mock_user = MagicMock(spec=User)
        mock_user.id = "test-user-id"
        mock_user.username = "testuser"
        mock_user.is_active = True
        mock_user.password_hash = "valid_hash"
        mock_user.failed_login_attempts = 0
        mock_user.is_locked_now = Mock(return_value=False)

        with patch.object(db_session, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            with patch.object(service.password_service, 'verify_password', return_value=True):
                with patch.object(service.password_service, 'is_password_expired', return_value=False):
                    result = service.authenticate_user("testuser", "password123")
                    assert result is not None

    def test_authenticate_user_not_found(self, db_session):
        """Test authentication with non-existent user"""
        service = AuthenticationService(db_session)
        with patch.object(db_session, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None
            result = service.authenticate_user("nonexistent", "password")
            assert result is None


@pytest.fixture
def db_session():
    """Fixture providing mock database session"""
    return MagicMock(spec=Session)
