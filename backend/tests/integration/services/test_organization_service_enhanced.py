"""
Organization service enhanced smoke tests (async-era aligned).
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
        json={"username": admin_user.username, "password": "Admin123!@#"},
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


def _resolve_org_type_and_status(authenticated_client: TestClient) -> tuple[str, str]:
    response = authenticated_client.get("/api/v1/organizations?page=1&page_size=1")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("success") is True
    items = payload.get("data", {}).get("items", [])
    if items:
        item = items[0]
        return (
            str(item.get("type") or "department"),
            str(item.get("status") or "active"),
        )
    return ("department", "active")


def test_organization_statistics_endpoint_consistency(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.get("/api/v1/organizations/statistics")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert isinstance(payload.get("total"), int)
    assert isinstance(payload.get("active"), int)
    assert isinstance(payload.get("inactive"), int)
    assert isinstance(payload.get("by_type"), dict)
    assert isinstance(payload.get("by_level"), dict)
    assert payload["total"] == payload["active"] + payload["inactive"]


def test_organization_update_history_and_search_roundtrip(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    org_type, org_status = _resolve_org_type_and_status(authenticated_client)
    unique_suffix = uuid4().hex[:8]
    create_payload = {
        "name": f"组织更新测试-{unique_suffix}",
        "code": f"UPD-ORG-{unique_suffix}",
        "type": org_type,
        "status": org_status,
        "description": "before update",
        "created_by": "integration_test",
    }

    create_response = authenticated_client.post(
        "/api/v1/organizations",
        json=create_payload,
        headers=csrf_headers,
    )
    assert create_response.status_code == 200
    created = create_response.json()
    organization_id = created.get("id")
    assert organization_id is not None

    updated_name = f"组织更新完成-{unique_suffix}"
    update_response = authenticated_client.put(
        f"/api/v1/organizations/{organization_id}",
        json={
            "name": updated_name,
            "description": "after update",
            "updated_by": "integration_test",
        },
        headers=csrf_headers,
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated.get("id") == organization_id
    assert updated.get("name") == updated_name

    history_response = authenticated_client.get(
        f"/api/v1/organizations/{organization_id}/history?page=1&page_size=20",
    )
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload.get("success") is True
    history_items = history_payload.get("data", {}).get("items", [])
    assert isinstance(history_items, list)
    assert len(history_items) >= 1

    search_response = authenticated_client.get(
        f"/api/v1/organizations/search?keyword={unique_suffix}",
    )
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert search_payload.get("success") is True
    search_items = search_payload.get("data", {}).get("items", [])
    assert any(
        item.get("id") == organization_id
        for item in search_items
        if isinstance(item, dict)
    )

    delete_response = authenticated_client.delete(
        f"/api/v1/organizations/{organization_id}",
        headers=csrf_headers,
    )
    assert delete_response.status_code == 200
