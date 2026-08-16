"""
End-to-end project aggregate endpoint tests (REQ-PRJ-003).

Covers the project-perspective aggregations over a populated project
(upstream + downstream contracts with generated ledgers): contract
relations, ledger summary amounts, tenants, risks, analytics, per-project
assets, plus the empty-project and not-found/view-mode guards.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.e2e.factories import create_approved_legal_party

pytestmark = pytest.mark.e2e


def _create_project(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    *,
    suffix: str,
    manager_party_id: str,
) -> str:
    response = authenticated_client.post(
        "/api/v1/projects",
        json={
            "project_name": f"E2E聚合项目-{suffix}",
            "status": "planning",
            "manager_party_id": manager_party_id,
            "data_status": "正常",
        },
        headers=csrf_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _create_contract_group(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    *,
    project_id: str,
    operator_party_id: str,
    owner_party_id: str,
    suffix: str,
) -> str:
    response = authenticated_client.post(
        "/api/v1/contract-groups",
        json={
            "project_id": project_id,
            "revenue_mode": "lease",
            "operator_party_id": operator_party_id,
            "owner_party_id": owner_party_id,
            "effective_from": "2026-01-01",
            "settlement_rule": {
                "version": "v1",
                "cycle": "月付",
                "settlement_mode": "固定",
                "amount_rule": {"base": 5000},
                "payment_rule": {"due_day": 10},
            },
        },
        headers=csrf_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["contract_group_id"]


def _add_contract(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    *,
    group_id: str,
    lessor_party_id: str,
    lessee_party_id: str,
    suffix: str,
    group_relation_type: str,
) -> str:
    response = authenticated_client.post(
        f"/api/v1/contract-groups/{group_id}/contracts",
        json={
            "contract_group_id": group_id,
            "contract_number": f"E2E-HT-{suffix}",
            "contract_direction": "出租",
            "group_relation_type": group_relation_type,
            "lessor_party_id": lessor_party_id,
            "lessee_party_id": lessee_party_id,
            "sign_date": "2026-01-01",
            "effective_from": "2026-01-01",
            "effective_to": "2026-12-31",
            "payment_cycle": "月付",
            "lease_detail": {
                "total_deposit": 10000,
                "rent_amount": 5000,
                "monthly_rent_base": 5000,
                "payment_cycle": "月付",
                "tenant_name": f"E2E租户-{suffix}",
            },
            "rent_terms": [
                {
                    "sort_order": 1,
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "monthly_rent": 5000,
                }
            ],
        },
        headers=csrf_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["contract_id"]


def test_project_aggregates_over_populated_project_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Upstream + downstream contracts feed every aggregate endpoint."""
    suffix = uuid4().hex[:8]
    operator = create_approved_legal_party(
        db_session, suffix=f"{suffix}op", name=f"聚合运营方-{suffix}"
    )
    owner = create_approved_legal_party(
        db_session, suffix=f"{suffix}ow", name=f"聚合产权方-{suffix}"
    )
    lessor = create_approved_legal_party(
        db_session, suffix=f"{suffix}ls", name=f"聚合出租方-{suffix}"
    )
    lessee = create_approved_legal_party(
        db_session, suffix=f"{suffix}lz", name=f"聚合承租方-{suffix}"
    )

    project_id = _create_project(
        authenticated_client,
        csrf_headers,
        suffix=suffix,
        manager_party_id=operator.id,
    )
    group_id = _create_contract_group(
        authenticated_client,
        csrf_headers,
        project_id=project_id,
        operator_party_id=operator.id,
        owner_party_id=owner.id,
        suffix=suffix,
    )
    # Upstream feeds operator_cost (payable); downstream feeds
    # terminal_collection (receivable) and the tenants summary.
    _add_contract(
        authenticated_client,
        csrf_headers,
        group_id=group_id,
        lessor_party_id=lessor.id,
        lessee_party_id=operator.id,
        suffix=f"{suffix}up",
        group_relation_type="上游",
    )
    _add_contract(
        authenticated_client,
        csrf_headers,
        group_id=group_id,
        lessor_party_id=operator.id,
        lessee_party_id=lessee.id,
        suffix=f"{suffix}down",
        group_relation_type="下游",
    )

    overview = authenticated_client.get("/api/v1/projects/stats/overview")
    assert overview.status_code == 200, overview.text
    assert overview.json()["total_projects"] >= 1

    relations = authenticated_client.get(
        f"/api/v1/projects/{project_id}/contract-relations"
    )
    assert relations.status_code == 200, relations.text
    relation_items = relations.json()["data"]["items"]
    assert len(relation_items) == 1
    relation = relation_items[0]
    assert relation["display_name"].startswith("GRP-")
    assert relation["revenue_mode"] == "lease"
    assert relation["relation_kind"] == "lease_sublease"

    # 12 × 5000 on each side of the ledger.
    ledger_summary = authenticated_client.get(
        f"/api/v1/projects/{project_id}/ledger-summary"
    )
    assert ledger_summary.status_code == 200, ledger_summary.text
    summary = ledger_summary.json()["data"]
    assert Decimal(str(summary["receivable_amount"])) == Decimal("60000")
    assert Decimal(str(summary["payable_amount"])) == Decimal("60000")
    assert Decimal(str(summary["terminal_collection"]["amount_due"])) == Decimal(
        "60000"
    )
    assert Decimal(str(summary["operator_cost"]["amount_due"])) == Decimal("60000")

    tenants = authenticated_client.get(
        f"/api/v1/projects/{project_id}/tenants"
    )
    assert tenants.status_code == 200, tenants.text
    tenant_items = tenants.json()["data"]["items"]
    assert len(tenant_items) == 1
    assert tenant_items[0]["party_id"] == lessee.id
    assert tenant_items[0]["group_relation_type"] == "下游"
    assert tenant_items[0]["contract_count"] == 1

    risks = authenticated_client.get(f"/api/v1/projects/{project_id}/risks")
    assert risks.status_code == 200, risks.text
    assert "items" in risks.json()["data"]

    analytics = authenticated_client.get(
        f"/api/v1/projects/{project_id}/analytics"
    )
    assert analytics.status_code == 200, analytics.text
    analytics_data = analytics.json()["data"]
    assert analytics_data["contract_relation_count"] >= 1
    assert Decimal(str(analytics_data["receivable_amount"])) == Decimal("60000")
    mode_summaries = analytics_data["mode_summaries"]
    assert any(m["label"] == "承租转租" for m in mode_summaries)
    trends = analytics_data["monthly_trends"]
    assert len(trends) == 12
    assert {t["period"] for t in trends} == {
        f"2026-{month:02d}" for month in range(1, 13)
    }

    assets = authenticated_client.get(f"/api/v1/projects/{project_id}/assets")
    assert assets.status_code == 200, assets.text
    assets_data = assets.json()["data"]
    assert assets_data["total"] == 0
    assert "summary" in assets_data


def test_project_aggregate_guards_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Empty projects answer with empty structures; guards reject bad input."""
    suffix = uuid4().hex[:8]
    operator = create_approved_legal_party(
        db_session, suffix=f"{suffix}g", name=f"守卫运营方-{suffix}"
    )
    empty_project_id = _create_project(
        authenticated_client,
        csrf_headers,
        suffix=f"{suffix}empty",
        manager_party_id=operator.id,
    )

    empty_tenants = authenticated_client.get(
        f"/api/v1/projects/{empty_project_id}/tenants"
    )
    assert empty_tenants.status_code == 200
    assert empty_tenants.json()["data"]["total"] == 0

    empty_summary = authenticated_client.get(
        f"/api/v1/projects/{empty_project_id}/ledger-summary"
    )
    assert empty_summary.status_code == 200
    summary = empty_summary.json()["data"]
    assert Decimal(str(summary["receivable_amount"])) == Decimal("0")
    assert Decimal(str(summary["terminal_collection"]["amount_due"])) == Decimal("0")

    empty_analytics = authenticated_client.get(
        f"/api/v1/projects/{empty_project_id}/analytics"
    )
    assert empty_analytics.status_code == 200
    assert empty_analytics.json()["data"]["contract_relation_count"] == 0

    empty_risks = authenticated_client.get(
        f"/api/v1/projects/{empty_project_id}/risks"
    )
    assert empty_risks.status_code == 200

    # Unknown projects are a clean 404 on every aggregate.
    missing_id = uuid4()
    for path in ("tenants", "ledger-summary", "analytics", "risks"):
        missing = authenticated_client.get(
            f"/api/v1/projects/{missing_id}/{path}"
        )
        assert missing.status_code == 404, path
        assert missing.json().get("error", {}).get("code") == "RESOURCE_NOT_FOUND"

    # view_mode=all is rejected on the single-perspective tenants endpoint.
    mixed_mode = authenticated_client.get(
        f"/api/v1/projects/{empty_project_id}/tenants",
        params={"view_mode": "all"},
    )
    assert mixed_mode.status_code == 400
    assert mixed_mode.json().get("error", {}).get("code") == "INVALID_REQUEST"

    invalid_mode = authenticated_client.get(
        f"/api/v1/projects/{empty_project_id}/tenants",
        params={"view_mode": "tenant"},
    )
    assert invalid_mode.status_code == 400

def test_project_creation_requires_csrf_header_e2e(authenticated_client) -> None:
    """E2E Admission Standard #2: mutations need the CSRF negative branch."""
    response = authenticated_client.post(
        "/api/v1/projects", json={"project_name": "CSRF守卫项目"}
    )
    assert response.status_code == 403
