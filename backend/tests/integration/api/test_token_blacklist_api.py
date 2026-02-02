"""
Token blacklist integration tests for protected endpoints.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from src.core.config import settings
from src.security.token_blacklist import blacklist_manager


def _build_access_token(user_id: str, username: str, role: str) -> tuple[str, str, int]:
    now = datetime.now(UTC)
    exp = now + timedelta(hours=1)
    jti = f"test-{uuid4().hex}"
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


@pytest.mark.usefixtures("db_tables")
class TestTokenBlacklistApi:
    def teardown_method(self) -> None:
        blacklist_manager.clear_blacklist()

    def test_blacklisted_token_rejected_on_protected_endpoint(self, client, test_data):
        admin = test_data["admin"]
        token, jti, exp = _build_access_token(
            user_id=str(admin.id),
            username=admin.username,
            role=str(admin.role),
        )

        # Sanity check: token should work before blacklisting
        ok_response = client.get("/api/v1/auth/me", cookies={"auth_token": token})
        assert ok_response.status_code == 200

        blacklist_manager.add_token(jti, exp)

        blocked_response = client.get("/api/v1/auth/me", cookies={"auth_token": token})
        assert blocked_response.status_code == 401
