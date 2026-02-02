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

    result = get_optional_current_user(token=token, db=db)

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

    result = get_optional_current_user(token=token, db=db)

    assert result is None
