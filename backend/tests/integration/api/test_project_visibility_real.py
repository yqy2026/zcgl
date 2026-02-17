"""
Project visibility integration tests for non-admin users across organizations.
"""

import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.auth import User
from src.models.organization import Organization
from src.models.project import Project
from src.services.core.password_service import PasswordService


def _build_project_code() -> str:
    prefix = datetime.now().strftime("%y%m")
    suffix = f"{uuid.uuid4().int % 10000:04d}"
    return f"PJ{prefix}{suffix}"


def _login(client: TestClient, username: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": username, "password": password},
    )
    assert response.status_code == 200


@pytest.mark.integration
def test_non_admin_project_visibility_isolation(client: TestClient, db_session: Session):
    """真实链路验证：非管理员仅能看到本组织项目。"""
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)

    org_a = Organization(
        name=f"Visibility Org A-{suffix}",
        code=f"VIS-ORG-A-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    org_b = Organization(
        name=f"Visibility Org B-{suffix}",
        code=f"VIS-ORG-B-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    db_session.add_all([org_a, org_b])
    db_session.flush()

    user_a = User(
        username=f"vis_user_a_{suffix}",
        email=f"vis_user_a_{suffix}@example.com",
        phone=f"139{uuid.uuid4().int % 10**8:08d}",
        full_name="Visibility User A",
        password_hash=password_hash,
        is_active=True,
        default_organization_id=org_a.id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    user_b = User(
        username=f"vis_user_b_{suffix}",
        email=f"vis_user_b_{suffix}@example.com",
        phone=f"137{uuid.uuid4().int % 10**8:08d}",
        full_name="Visibility User B",
        password_hash=password_hash,
        is_active=True,
        default_organization_id=org_b.id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add_all([user_a, user_b])
    db_session.flush()

    project_a = Project(
        name=f"Visibility Project A-{suffix}",
        code=_build_project_code(),
        project_status="active",
        organization_id=org_a.id,
        created_by=user_a.id,
    )
    project_b = Project(
        name=f"Visibility Project B-{suffix}",
        code=_build_project_code(),
        project_status="active",
        organization_id=org_b.id,
        created_by=user_b.id,
    )
    db_session.add_all([project_a, project_b])
    db_session.commit()

    _login(client, user_a.username, password)
    response_a = client.get("/api/v1/projects/")
    assert response_a.status_code == 200
    items_a = response_a.json()["data"]["items"]
    ids_a = {item["id"] for item in items_a}
    assert project_a.id in ids_a
    assert project_b.id not in ids_a

    client.cookies.clear()
    _login(client, user_b.username, password)
    response_b = client.get("/api/v1/projects/")
    assert response_b.status_code == 200
    items_b = response_b.json()["data"]["items"]
    ids_b = {item["id"] for item in items_b}
    assert project_b.id in ids_b
    assert project_a.id not in ids_b
