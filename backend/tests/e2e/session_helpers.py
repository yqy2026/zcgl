"""Shared session-switch helpers for e2e tests that need multiple identities.

Single-TestClient rule (testing-standards E2E Admission Standard #4): swap
identities by saving/restoring cookie jars; never spin up a second
TestClient on the shared app (Windows event-loop teardown deadlocks), and
always clear the jar before a fresh login (fixture-set attribute-less
cookies coexist with response Set-Cookies and raise CookieConflict).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

COOKIE_NAMES = ("auth_token", "csrf_token", "refresh_token")


def login(client: TestClient, username: str, password: str) -> dict[str, str]:
    """Login and return the fresh CSRF header for this session."""
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": username, "password": password},
    )
    assert response.status_code == 200, response.text
    csrf_token = response.cookies.get("csrf_token")
    assert csrf_token
    return {"X-CSRF-Token": csrf_token}


def capture_session(client: TestClient) -> list[dict[str, str]]:
    """Snapshot cookie specs (name/value/domain/path) for later restore."""
    return [
        {
            "name": cookie.name,
            "value": cookie.value or "",
            "domain": cookie.domain,
            "path": cookie.path,
        }
        for cookie in client.cookies.jar
    ]


def restore_session(
    client: TestClient, session: list[dict[str, str]]
) -> dict[str, str]:
    """Restore a captured session; return its CSRF header."""
    client.cookies.clear()
    csrf_token = None
    for spec in session:
        client.cookies.set(
            spec["name"], spec["value"], domain=spec["domain"], path=spec["path"]
        )
        if spec["name"] == "csrf_token":
            csrf_token = spec["value"]
    assert csrf_token
    return {"X-CSRF-Token": csrf_token}
