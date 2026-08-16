"""
End-to-end notification flow tests (REQ-NTF-001, in-app loop).

Covers the in-app notification loop through the public API: admin system
notices fan out to active users, unread counting, single and bulk read
marks, deletion, and the permission split (authenticated users read their
own notices; only admins may broadcast).
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.e2e.session_helpers import (
    capture_session,
    restore_session,
)

pytestmark = pytest.mark.e2e



def test_system_notice_broadcast_and_read_loop_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Admin broadcast → unread counts → read → read-all round-trip."""
    suffix = uuid4().hex[:8]
    admin_session = capture_session(authenticated_client)
    title = f"E2E系统通知-{suffix}"

    broadcast = authenticated_client.post(
        "/api/v1/notifications/system-notices",
        json={"title": title, "content": f"e2e 通知内容-{suffix}", "priority": "normal"},
        headers=csrf_headers,
    )
    assert broadcast.status_code == 200, broadcast.text
    assert broadcast.json()["created_count"] >= 1

    listing = authenticated_client.get("/api/v1/notifications")
    assert listing.status_code == 200, listing.text
    data = listing.json()["data"]
    notice = next(
        (item for item in data["items"] if item["title"] == title), None
    )
    assert notice is not None, f"broadcast notice missing from inbox: {data['items']}"
    assert notice["type"] == "system_notice"
    assert notice["is_read"] is False

    unread = authenticated_client.get("/api/v1/notifications/unread-count")
    assert unread.status_code == 200
    assert unread.json()["unread_count"] >= 1

    # Blank titles and PII payloads are rejected by the service layer.
    blank = authenticated_client.post(
        "/api/v1/notifications/system-notices",
        json={"title": "   ", "content": "x"},
        headers=csrf_headers,
    )
    assert blank.status_code == 422
    pii = authenticated_client.post(
        "/api/v1/notifications/system-notices",
        json={"title": "t", "content": "手机号 13800001234"},
        headers=csrf_headers,
    )
    assert pii.status_code == 422

    # Reading a single notice flips its state and clears one unread.
    read = authenticated_client.post(
        f"/api/v1/notifications/{notice['id']}/read", headers=csrf_headers
    )
    assert read.status_code == 200, read.text
    assert read.json()["is_read"] is True
    assert read.json()["read_at"] is not None

    mark_all = authenticated_client.post(
        "/api/v1/notifications/read-all", headers=csrf_headers
    )
    assert mark_all.status_code == 200
    unread_after = authenticated_client.get("/api/v1/notifications/unread-count")
    assert unread_after.json()["unread_count"] == 0

    # Deletion removes the notice.
    deleted = authenticated_client.delete(
        f"/api/v1/notifications/{notice['id']}", headers=csrf_headers
    )
    assert deleted.status_code == 200
    missing = authenticated_client.post(
        f"/api/v1/notifications/{notice['id']}/read", headers=csrf_headers
    )
    assert missing.status_code == 404

    # Permission split: authenticated users read their own inbox, but only
    # admins may broadcast.
    from tests.e2e.conftest import create_test_user

    create_test_user(
        db_session,
        username=f"e2e_notify_{suffix}",
        email=f"e2e_notify_{suffix}@example.com",
        password="UserPass123!@#",
        full_name=f"E2E通知用户-{suffix}",
        role="user",
    )
    authenticated_client.cookies.clear()
    login = authenticated_client.post(
        "/api/v1/auth/login",
        json={"identifier": f"e2e_notify_{suffix}", "password": "UserPass123!@#"},
    )
    assert login.status_code == 200
    regular_csrf = login.cookies.get("csrf_token")
    regular_headers = {"X-CSRF-Token": regular_csrf}

    regular_inbox = authenticated_client.get("/api/v1/notifications")
    assert regular_inbox.status_code == 200, regular_inbox.text

    regular_broadcast = authenticated_client.post(
        "/api/v1/notifications/system-notices",
        json={"title": "unauthorized", "content": "nope"},
        headers=regular_headers,
    )
    assert regular_broadcast.status_code == 403
    assert (
        regular_broadcast.json().get("error", {}).get("code") == "PERMISSION_DENIED"
    )

    # Restore the admin session for any later fixtures on the shared client.
    restore_session(authenticated_client, admin_session)
