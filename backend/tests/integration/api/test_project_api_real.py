"""
Project API integration tests with real DB/auth flow.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _get_auth_headers(client: TestClient, admin_user) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": admin_user.username, "password": "Admin123!@#"},
    )
    assert response.status_code == 200
    csrf_token = response.cookies.get("csrf_token")
    assert csrf_token is not None
    return {"X-CSRF-Token": csrf_token}


def _request_with_reauth(
    client: TestClient,
    *,
    method: str,
    url: str,
    admin_user,
    headers: dict[str, str],
    json: dict | None = None,
):
    """Retry once on transient 401 caused by token iat skew in test runtime."""
    response = client.request(method, url, headers=headers, json=json)
    if response.status_code != 401:
        return response

    refreshed_headers = _get_auth_headers(client, admin_user)
    return client.request(method, url, headers=refreshed_headers, json=json)


def _build_project_code() -> str:
    segment = uuid.uuid4().hex[:6].upper()
    serial = f"{uuid.uuid4().int % 1000000:06d}"
    return f"PRJ-{segment}-{serial}"


@pytest.mark.integration
def test_project_crud_real_flow(client: TestClient, test_data):
    """真实链路验证：项目 CRUD + 列表搜索。"""
    admin_user = test_data["admin"]
    headers = _get_auth_headers(client, admin_user)

    project_name = f"IT-Real-Project-{uuid.uuid4().hex[:8]}"
    create_payload = {
        "project_name": project_name,
        "project_code": _build_project_code(),
        "status": "active",
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
    assert detail["project_name"] == project_name
    assert detail["project_code"] == create_payload["project_code"]

    update_response = client.put(
        f"/api/v1/projects/{project_id}",
        json={"status": "paused"},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "paused"

    delete_response = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json().get("message") == "项目删除成功"

    after_delete_response = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert after_delete_response.status_code == 404


@pytest.mark.integration
def test_project_list_and_detail_should_tolerate_legacy_project_code(
    client: TestClient,
    db_session: Session,
    test_data: dict[str, object],
) -> None:
    """历史 project_code 不符合新格式时，列表/详情仍应可读。"""
    from sqlalchemy import select

    from src.models.party import Party, PartyType
    from src.models.project import Project

    admin_user = test_data["admin"]
    headers = _get_auth_headers(client, admin_user)

    suffix = uuid.uuid4().hex[:8]
    legacy_code = f"LEGACY-{suffix}"

    organization_id = str(getattr(test_data["organization"], "id"))
    manager_party = db_session.execute(
        select(Party).where(
            Party.party_type == PartyType.ORGANIZATION.value,
            Party.external_ref == organization_id,
        )
    ).scalar_one_or_none()
    if manager_party is None:
        manager_party = Party(
            party_type=PartyType.ORGANIZATION.value,
            name=f"Legacy Test Party {suffix}",
            code=f"LEGACY-PARTY-{suffix}",
            external_ref=organization_id,
            status="active",
        )
        db_session.add(manager_party)
        db_session.flush()

    project = Project(
        project_name=f"Legacy Project {suffix}",
        project_code=legacy_code,
        status="active",
        manager_party_id=manager_party.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    list_response = _request_with_reauth(
        client,
        method="GET",
        url=f"/api/v1/projects/?keyword={suffix}",
        admin_user=admin_user,
        headers=headers,
    )
    assert list_response.status_code == 200
    items = list_response.json()["data"]["items"]
    matched = [item for item in items if item.get("id") == project.id]
    assert len(matched) == 1
    assert matched[0].get("project_code") == legacy_code

    detail_response = _request_with_reauth(
        client,
        method="GET",
        url=f"/api/v1/projects/{project.id}",
        admin_user=admin_user,
        headers=headers,
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail.get("id") == project.id
    assert detail.get("project_code") == legacy_code


@pytest.mark.integration
def test_project_search_should_tolerate_legacy_project_code(
    client: TestClient,
    db_session: Session,
    test_data: dict[str, object],
) -> None:
    """历史 project_code 不符合新格式时，POST /search 仍应可读。"""
    from sqlalchemy import select

    from src.models.party import Party, PartyType
    from src.models.project import Project

    admin_user = test_data["admin"]
    headers = _get_auth_headers(client, admin_user)

    suffix = uuid.uuid4().hex[:8]
    legacy_code = f"LEGACY-SEARCH-{suffix}"

    organization_id = str(getattr(test_data["organization"], "id"))
    manager_party = db_session.execute(
        select(Party).where(
            Party.party_type == PartyType.ORGANIZATION.value,
            Party.external_ref == organization_id,
        )
    ).scalar_one_or_none()
    if manager_party is None:
        manager_party = Party(
            party_type=PartyType.ORGANIZATION.value,
            name=f"Legacy Search Party {suffix}",
            code=f"LEGACY-SEARCH-PARTY-{suffix}",
            external_ref=organization_id,
            status="active",
        )
        db_session.add(manager_party)
        db_session.flush()

    project = Project(
        project_name=f"Legacy Search Project {suffix}",
        project_code=legacy_code,
        status="active",
        manager_party_id=manager_party.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    search_payload = {
        "keyword": suffix,
        "page": 1,
        "page_size": 20,
    }
    search_response = _request_with_reauth(
        client,
        method="POST",
        url="/api/v1/projects/search",
        admin_user=admin_user,
        headers=headers,
        json=search_payload,
    )
    assert search_response.status_code == 200
    items = search_response.json()["data"]["items"]
    matched = [item for item in items if item.get("id") == project.id]
    assert len(matched) == 1
    assert matched[0].get("project_code") == legacy_code
