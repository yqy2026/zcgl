"""Expired-password recovery uses the real authentication stack and test user only."""

from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.e2e


def test_expired_password_can_be_changed_without_a_login_session(
    client, test_admin_user, db_session
):
    test_admin_user.password_last_changed = datetime.now(UTC).replace(
        tzinfo=None
    ) - timedelta(days=3650)
    db_session.commit()
    credentials = {"identifier": test_admin_user.username, "password": "AdminPass123!"}
    expired = client.post("/api/v1/auth/login", json=credentials)
    assert expired.status_code == 400, expired.text
    assert expired.json()["error"]["code"] == "PASSWORD_EXPIRED"
    changed = client.post(
        "/api/v1/auth/expired-password",
        json={
            "username": test_admin_user.username,
            "current_password": "AdminPass123!",
            "new_password": "NewPassword!2026",
        },
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["success"] is True
    assert "set-cookie" not in changed.headers
    old = client.post("/api/v1/auth/login", json=credentials)
    assert old.status_code == 401, old.text
    credentials["password"] = "NewPassword!2026"
    current = client.post("/api/v1/auth/login", json=credentials)
    assert current.status_code == 200, current.text
