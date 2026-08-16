"""
End-to-end project, organization, and analytics tests.

Covers the public project CRUD + status switch, organization tree/CRUD,
and the analytics surfaces that are reachable from the app shell.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.e2e.factories import (
    create_approved_legal_party,
    create_scoped_asset_via_api,
)

pytestmark = pytest.mark.e2e


def _create_project(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    *,
    suffix: str,
    manager_party_id: str,
    status: str = "planning",
) -> dict[str, object]:
    response = authenticated_client.post(
        "/api/v1/projects",
        json={
            "project_name": f"E2E项目-{suffix}",
            "status": status,
            "manager_party_id": manager_party_id,
            "data_status": "正常",
        },
        headers=csrf_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_project_lifecycle_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Create → list → detail → update → status switch → delete."""
    suffix = uuid4().hex[:8]
    manager = create_approved_legal_party(
        db_session, suffix=suffix, name=f"项目运营方-{suffix}"
    )

    created = _create_project(
        authenticated_client,
        csrf_headers,
        suffix=suffix,
        manager_party_id=manager.id,
    )
    project_id = created.get("id")
    assert isinstance(project_id, str) and project_id != ""
    assert created.get("project_code", "").startswith("PRJ-")
    assert created.get("manager_party_id") == manager.id

    # List contains the project and search finds it by keyword.
    list_response = authenticated_client.get(
        f"/api/v1/projects?page=1&page_size=20&keyword={suffix}"
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    items = list_payload.get("data", {}).get("items", [])
    assert isinstance(items, list)
    assert any(item.get("id") == project_id for item in items)

    # Detail round-trip.
    detail_response = authenticated_client.get(f"/api/v1/projects/{project_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail.get("id") == project_id
    assert detail.get("project_name") == f"E2E项目-{suffix}"

    # Update name.
    update_response = authenticated_client.put(
        f"/api/v1/projects/{project_id}",
        json={"project_name": f"E2E项目改名-{suffix}"},
        headers=csrf_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json().get("project_name") == f"E2E项目改名-{suffix}"

    # Status toggle pauses the planning project (no request body required).
    status_response = authenticated_client.put(
        f"/api/v1/projects/{project_id}/status",
        headers=csrf_headers,
    )
    assert status_response.status_code == 200
    assert status_response.json().get("status") == "paused"

    # Delete (soft) then detail resolves as gone (404).
    delete_response = authenticated_client.delete(
        f"/api/v1/projects/{project_id}",
        headers=csrf_headers,
    )
    assert delete_response.status_code == 200
    after_delete = authenticated_client.get(f"/api/v1/projects/{project_id}")
    assert after_delete.status_code == 404


def test_project_requires_manager_party_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    """ACC-005: a project without a resolvable manager party is rejected."""
    suffix = uuid4().hex[:8]
    response = authenticated_client.post(
        "/api/v1/projects",
        json={
            "project_name": f"E2E无运营方项目-{suffix}",
            "status": "planning",
            "data_status": "正常",
        },
        headers=csrf_headers,
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "OPERATION_NOT_ALLOWED"


def test_organization_lifecycle_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    """Create → tree → detail → update → soft delete."""
    suffix = uuid4().hex[:8]
    create_response = authenticated_client.post(
        "/api/v1/organizations",
        json={
            "name": f"E2E组织-{suffix}",
            "code": f"E2E-ORG-{suffix.upper()[:8]}",
            "level": 2,
            "type": "company",
            "status": "active",
            "parent_id": None,
        },
        headers=csrf_headers,
    )
    assert create_response.status_code == 200, create_response.text
    organization = create_response.json()
    org_id = organization.get("id")
    assert isinstance(org_id, str) and org_id != ""
    assert organization.get("code") == f"E2E-ORG-{suffix.upper()[:8]}"

    # Tree contains the created node.
    tree_response = authenticated_client.get("/api/v1/organizations/tree")
    assert tree_response.status_code == 200
    tree = tree_response.json()
    assert isinstance(tree, list)
    assert any(node.get("id") == org_id for node in tree)

    # Detail round-trip.
    detail_response = authenticated_client.get(f"/api/v1/organizations/{org_id}")
    assert detail_response.status_code == 200
    assert detail_response.json().get("id") == org_id

    # Update name.
    update_response = authenticated_client.put(
        f"/api/v1/organizations/{org_id}",
        json={"name": f"E2E组织改名-{suffix}"},
        headers=csrf_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json().get("name") == f"E2E组织改名-{suffix}"

    # Soft delete.
    delete_response = authenticated_client.delete(
        f"/api/v1/organizations/{org_id}",
        headers=csrf_headers,
    )
    assert delete_response.status_code == 200
    after_delete = authenticated_client.get(f"/api/v1/organizations/{org_id}")
    assert after_delete.status_code == 200
    assert after_delete.json().get("is_deleted") is True


def test_organization_rejects_invalid_type_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    """organization_type must be one of the canonical enum values."""
    suffix = uuid4().hex[:8]
    response = authenticated_client.post(
        "/api/v1/organizations",
        json={
            "name": f"E2E非法组织-{suffix}",
            "code": f"E2E-BAD-{suffix.upper()[:8]}",
            "level": 2,
            "type": "区域公司",
            "status": "active",
        },
        headers=csrf_headers,
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "INVALID_REQUEST"


def test_analytics_comprehensive_and_basic_stats_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Analytics surfaces respond with the seeded asset population."""
    suffix = uuid4().hex[:8]
    holder = create_approved_legal_party(
        db_session, suffix=suffix, name=f"分析权利人-{suffix}"
    )
    create_scoped_asset_via_api(
        authenticated_client,
        db_session,
        suffix=suffix,
        holder_party_id=holder.id,
        csrf_headers=csrf_headers,
    )

    # Basic statistics reflect the created asset.
    basic_response = authenticated_client.get("/api/v1/statistics/basic")
    assert basic_response.status_code == 200
    basic = basic_response.json()
    assert basic.get("total_assets") >= 1
    assert isinstance(basic.get("usage_status", {}), dict)

    # Comprehensive analytics requires an explicit owner/manager view.
    comprehensive_response = authenticated_client.get(
        "/api/v1/analytics/comprehensive?view_mode=owner"
    )
    assert comprehensive_response.status_code == 200
    payload = comprehensive_response.json()
    assert payload.get("success") is True
    data = payload.get("data", {})
    assert isinstance(data, dict)
    # The transaction-isolated DB holds exactly this test's seeded asset,
    # so the owner-view distributions must carry it with count == 1.
    usage_distribution = data.get("usage_status_distribution", [])
    assert any(
        item.get("status") == "出租" and item.get("count") == 1
        for item in usage_distribution
    ), f"seeded 出租 asset missing from usage distribution: {usage_distribution}"
    nature_distribution = data.get("property_nature_distribution", [])
    assert any(
        item.get("name") == "经营类" and item.get("count") == 1
        for item in nature_distribution
    ), f"seeded 经营类 asset missing from nature distribution: {nature_distribution}"

    # view_mode=all is rejected for the customer dual-metric caliber.
    rejected = authenticated_client.get("/api/v1/analytics/comprehensive?view_mode=all")
    assert rejected.status_code == 400
    error = rejected.json().get("error", {})
    assert error.get("code") == "INVALID_REQUEST"

def test_project_creation_requires_csrf_header_e2e(authenticated_client) -> None:
    """E2E Admission Standard #2: mutations need the CSRF negative branch."""
    response = authenticated_client.post(
        "/api/v1/projects", json={"project_name": "CSRF守卫项目"}
    )
    assert response.status_code == 403
