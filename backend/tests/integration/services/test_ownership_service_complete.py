"""
Ownership service integration smoke tests (async-era aligned).
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def authenticated_client(client: TestClient, test_data) -> TestClient:
    admin_user = test_data["admin"]
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": admin_user.username, "password": "Admin123!@#"},
    )
    assert response.status_code == 200
    auth_token = response.cookies.get("auth_token")
    csrf_token = response.cookies.get("csrf_token")
    assert auth_token is not None
    client.cookies.set("auth_token", auth_token)
    if csrf_token is not None:
        client.cookies.set("csrf_token", csrf_token)
    setattr(client, "_csrf_token", csrf_token)
    return client


@pytest.fixture
def csrf_headers(authenticated_client: TestClient) -> dict[str, str]:
    csrf_token = getattr(authenticated_client, "_csrf_token", None)
    if csrf_token is None:
        return {}
    return {"X-CSRF-Token": csrf_token}


def _create_ownership(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    unique_suffix: str,
) -> dict:
    create_response = authenticated_client.post(
        "/api/v1/ownerships",
        json={
            "name": f"集成权属方-{unique_suffix}",
            "short_name": f"IT-{unique_suffix[:4]}",
        },
        headers=csrf_headers,
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created.get("id") is not None
    return created


def test_ownership_create_search_toggle_and_delete_roundtrip(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    unique_suffix = uuid4().hex[:8]
    created = _create_ownership(authenticated_client, csrf_headers, unique_suffix)
    ownership_id = created["id"]
    initial_status = bool(created.get("is_active"))
    assert str(created.get("code", "")).startswith("OW")

    list_response = authenticated_client.get(
        f"/api/v1/ownerships?page=1&page_size=20&keyword={unique_suffix}",
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload.get("success") is True
    list_items = list_payload.get("data", {}).get("items", [])
    assert any(
        item.get("id") == ownership_id for item in list_items if isinstance(item, dict)
    )

    search_response = authenticated_client.post(
        "/api/v1/ownerships/search",
        json={"keyword": unique_suffix, "page": 1, "page_size": 20},
        headers=csrf_headers,
    )
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert search_payload.get("success") is True
    search_items = search_payload.get("data", {}).get("items", [])
    assert any(
        item.get("id") == ownership_id
        for item in search_items
        if isinstance(item, dict)
    )

    toggle_response = authenticated_client.post(
        f"/api/v1/ownerships/{ownership_id}/toggle-status",
        headers=csrf_headers,
    )
    assert toggle_response.status_code == 200
    toggled = toggle_response.json()
    assert toggled.get("id") == ownership_id
    assert toggled.get("is_active") is (not initial_status)

    dropdown_response = authenticated_client.get(
        f"/api/v1/ownerships/dropdown-options?is_active="
        f"{str(toggled.get('is_active')).lower()}",
    )
    assert dropdown_response.status_code == 200
    dropdown_items = dropdown_response.json()
    assert isinstance(dropdown_items, list)
    assert any(
        item.get("id") == ownership_id
        for item in dropdown_items
        if isinstance(item, dict)
    )

    delete_response = authenticated_client.delete(
        f"/api/v1/ownerships/{ownership_id}",
        headers=csrf_headers,
    )
    assert delete_response.status_code == 200
    delete_payload = delete_response.json()
    assert delete_payload.get("id") == ownership_id

    search_after_delete = authenticated_client.post(
        "/api/v1/ownerships/search",
        json={"keyword": unique_suffix, "page": 1, "page_size": 20},
        headers=csrf_headers,
    )
    assert search_after_delete.status_code == 200
    after_items = search_after_delete.json().get("data", {}).get("items", [])
    assert all(
        item.get("id") != ownership_id for item in after_items if isinstance(item, dict)
    )


def test_ownership_statistics_summary_consistency(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    before_response = authenticated_client.get("/api/v1/ownerships/statistics/summary")
    assert before_response.status_code == 200
    before_stats = before_response.json()
    before_total = int(before_stats.get("total_count", 0))

    unique_suffix = uuid4().hex[:8]
    created = _create_ownership(authenticated_client, csrf_headers, unique_suffix)
    ownership_id = created["id"]

    after_create_response = authenticated_client.get(
        "/api/v1/ownerships/statistics/summary",
    )
    assert after_create_response.status_code == 200
    after_create_stats = after_create_response.json()
    assert int(after_create_stats.get("total_count", 0)) == before_total + 1
    assert (
        int(after_create_stats.get("total_count", 0))
        == int(after_create_stats.get("active_count", 0))
        + int(after_create_stats.get("inactive_count", 0))
    )

    delete_response = authenticated_client.delete(
        f"/api/v1/ownerships/{ownership_id}",
        headers=csrf_headers,
    )
    assert delete_response.status_code == 200

    after_delete_response = authenticated_client.get(
        "/api/v1/ownerships/statistics/summary",
    )
    assert after_delete_response.status_code == 200
    after_delete_stats = after_delete_response.json()
    assert int(after_delete_stats.get("total_count", 0)) == before_total


def test_ownership_financial_summary_nonexistent(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.get(
        "/api/v1/ownerships/nonexistent/financial-summary"
    )
    assert response.status_code == 404


def test_delete_nonexistent_ownership(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    response = authenticated_client.delete(
        "/api/v1/ownerships/nonexistent",
        headers=csrf_headers,
    )
    assert response.status_code == 404
    payload = response.json()
    assert payload.get("success") is False


def test_toggle_status_nonexistent_ownership(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    response = authenticated_client.post(
        "/api/v1/ownerships/nonexistent/toggle-status",
        headers=csrf_headers,
    )
    assert response.status_code == 404
    payload = response.json()
    assert payload.get("success") is False


def test_update_projects_nonexistent_ownership(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    response = authenticated_client.put(
        "/api/v1/ownerships/nonexistent/projects",
        json=[],
        headers=csrf_headers,
    )
    assert response.status_code == 404
    payload = response.json()
    assert payload.get("success") is False
