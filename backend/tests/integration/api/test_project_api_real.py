"""
Project API integration tests with real DB/auth flow.
"""

import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient


def _get_auth_headers(client: TestClient, admin_user) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": admin_user.username, "password": "Admin123!@#"},
    )
    assert response.status_code == 200
    csrf_token = response.cookies.get("csrf_token")
    assert csrf_token is not None
    return {"X-CSRF-Token": csrf_token}


def _build_project_code() -> str:
    prefix = datetime.now().strftime("%y%m")
    suffix = f"{uuid.uuid4().int % 10000:04d}"
    return f"PJ{prefix}{suffix}"


@pytest.mark.integration
def test_project_crud_real_flow(client: TestClient, test_data):
    """真实链路验证：项目 CRUD + 列表搜索。"""
    admin_user = test_data["admin"]
    headers = _get_auth_headers(client, admin_user)

    project_name = f"IT-Real-Project-{uuid.uuid4().hex[:8]}"
    create_payload = {
        "name": project_name,
        "code": _build_project_code(),
        "city": "Shanghai",
        "district": "Pudong",
        "address": "No.1 Real Integration Road",
        "project_type": "office",
        "project_status": "active",
    }

    create_response = client.post(
        "/api/v1/projects/",
        json=create_payload,
        headers=headers,
    )
    assert create_response.status_code == 200
    created = create_response.json()
    project_id = created["id"]

    list_response = client.get(
        f"/api/v1/projects/?keyword={project_name}",
        headers=headers,
    )
    assert list_response.status_code == 200
    items = list_response.json()["data"]["items"]
    assert any(item["id"] == project_id for item in items)

    detail_response = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["name"] == project_name
    assert detail["code"] == create_payload["code"]

    update_response = client.put(
        f"/api/v1/projects/{project_id}",
        json={"city": "Suzhou", "district": "Gusu"},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["city"] == "Suzhou"

    delete_response = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json().get("message") == "项目删除成功"

    after_delete_response = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert after_delete_response.status_code == 404
