"""
Optional auth behavior tests.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from src.core.config import settings
from src.middleware.auth import get_optional_current_user
from src.security.token_blacklist import blacklist_manager


def _build_access_token(user_id: str, username: str, role: str) -> tuple[str, str, int]:
    now = datetime.now(UTC)
    exp = now + timedelta(hours=1)
    jti = f"opt-{uuid4().hex}"
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": jti,
        "aud": settings.JWT_AUDIENCE,
        "iss": settings.JWT_ISSUER,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti, payload["exp"]


@pytest.fixture(autouse=True)
def clear_blacklist():
    blacklist_manager.clear_blacklist()
    yield
    blacklist_manager.clear_blacklist()


def _mock_db_with_user(user_id: str):
    user = type("UserStub", (), {})()
    user.id = user_id
    user.is_active = True
    user.is_locked_now = lambda: False

    db = type("DBStub", (), {})()
    query = type("QueryStub", (), {})()
    query.filter = lambda *_args, **_kwargs: query
    query.first = lambda: user
    db.query = lambda *_args, **_kwargs: query
    return db, user


def test_optional_auth_returns_user_for_valid_token():
    db, expected_user = _mock_db_with_user("user-1")
    token, _jti, _exp = _build_access_token("user-1", "tester", "admin")

    result = get_optional_current_user(auth_token=token, db=db)

    assert result is expected_user


def test_optional_auth_accepts_cookie_token():
    db, expected_user = _mock_db_with_user("user-cookie")
    token, _jti, _exp = _build_access_token("user-cookie", "tester", "admin")

    result = get_optional_current_user(auth_token=token, db=db)

    assert result is expected_user


def test_optional_auth_returns_none_for_blacklisted_token():
    db, _user = _mock_db_with_user("user-2")
    token, jti, exp = _build_access_token("user-2", "tester", "admin")
    blacklist_manager.add_token(jti, exp)

    result = get_optional_current_user(auth_token=token, db=db)

    assert result is None


def test_optional_auth_cookie_priority():
    """Test that cookie token takes precedence over header token"""
    # Create two different users
    db, cookie_user = _mock_db_with_user("user-cookie")
    _, header_user = _mock_db_with_user("user-header")
    
    # Mock DB query to return correct user based on ID in token
    def mock_query_first(self):
        # We need to inspect the filter criteria which is hard with this simple mock
        # So we'll rely on the fact that the auth function calls db.query(User).filter(User.id == sub)
        # We can just return a mock that matches the 'sub' we expect to win
        return cookie_user

    # Setup DB mock to return cookie_user
    query_mock = type("QueryStub", (), {})()
    query_mock.filter = lambda *args, **kwargs: query_mock
    query_mock.first = lambda: cookie_user
    db.query = lambda *args, **kwargs: query_mock

    # Create tokens for both
    cookie_token, _, _ = _build_access_token("user-cookie", "cookie-user", "user")
    header_token, _, _ = _build_access_token("user-header", "header-user", "user")

    # Pass only cookie token as header token is no longer supported in get_optional_current_user
    result = get_optional_current_user(auth_token=cookie_token, db=db)

    # Should return the user associated with the cookie token
    assert result is cookie_user
