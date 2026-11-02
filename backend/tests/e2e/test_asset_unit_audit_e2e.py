"""REQ-RPT-001/REQ-UNT-001: asset-unit maintenance and boundary audit trail.

Unit edits, splits and merges must land in business_change_events in the same
transaction, and the change-feed reader must expose them under party scope.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.models.asset_contract import (
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from src.models.asset_unit import AssetUnit
from src.models.attachment import Attachment
from src.models.project import Project
from tests.e2e.factories import create_approved_legal_party

pytestmark = pytest.mark.e2e

_TODAY = datetime.now(UTC).astimezone(ZoneInfo("Asia/Shanghai")).date()


def _seed_unit(db_session: Session, actor_id: str) -> dict[str, str]:
    suffix = uuid4().hex[:12]
    operator = create_approved_legal_party(
        db_session, suffix=suffix, name=f"审计主体-{suffix}"
    )
    project = Project(
        id=str(uuid4()),
        project_code=f"PRJ-AUD-{suffix}",
        project_name=f"审计项目-{suffix}",
        manager_party_id=operator.id,
        status="active",
    )
    db_session.add(project)
    db_session.flush()
    unit = AssetUnit(
        id=str(uuid4()),
        unit_code=f"AU-AUD-{suffix}",
        name=f"审计单元-{suffix}",
        project_id=project.id,
        owner_party_id=operator.id,
        address="审计 E2E 地址",
        usage_type="commercial",
        acquisition_mode="managed",
        is_operating=True,
        land_area=Decimal("0"),
        building_area=Decimal("100"),
        rentable_area=Decimal("80"),
        managed_from=_TODAY - timedelta(days=400),
        predecessor_unit_ids=[],
        version=1,
    )
    db_session.add(unit)
    db_session.commit()
    return {
        "operator_party_id": operator.id,
        "unit_id": unit.id,
        "unit_code": unit.unit_code,
    }


def _seed_split_target(db_session: Session, actor_id: str) -> dict[str, str]:
    """A unit with a signed upstream so the split command accepts it."""
    facts = _seed_unit(db_session, actor_id)
    suffix = uuid4().hex[:8]
    upstream_id, scan_id = str(uuid4()), str(uuid4())
    db_session.add(
        Attachment(
            id=scan_id,
            owner_type="contract",
            owner_id=upstream_id,
            file_name=f"{scan_id}.pdf",
            file_type="pdf",
            file_size=1,
            storage_key=f"e2e/audit/{scan_id}.pdf",
            created_by=actor_id,
        )
    )
    db_session.flush()
    db_session.add(
        UpstreamContract(
            id=upstream_id,
            contract_number=f"UP-AUD-{suffix}",
            contract_type="lease",
            name="审计拆分上游",
            owner_party_id=facts["operator_party_id"],
            operator_party_id=facts["operator_party_id"],
            start_date=_TODAY - timedelta(days=200),
            end_date=_TODAY + timedelta(days=365),
            payment_cycle="monthly",
            payment_day=15,
            deposit_amount=Decimal("0"),
            scan_document_id=scan_id,
            version=1,
        )
    )
    db_session.flush()
    db_session.add(
        UpstreamContractAssetUnit(
            upstream_contract_id=upstream_id,
            asset_unit_id=facts["unit_id"],
            effective_from=_TODAY - timedelta(days=200),
            effective_to=_TODAY + timedelta(days=365),
        )
    )
    db_session.commit()
    return facts


def test_asset_unit_update_writes_audit_event_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    client = authenticated_client
    facts = _seed_unit(db_session, getattr(client, "_user_id"))
    path = f"/api/v1/asset-units/{facts['unit_id']}"

    before = client.get(path)
    assert before.status_code == 200, before.text

    updated = client.patch(
        path,
        json={
            "expected_version": before.json()["version"],
            "name": "改名后的审计单元",
            "rentable_area": "75.50",
        },
        headers=csrf_headers,
    )
    assert updated.status_code == 200, updated.text

    events = db_session.execute(
        text(
            "SELECT action, before, after FROM business_change_events "
            "WHERE target_type = 'asset_unit' AND target_id = :unit_id "
            "ORDER BY occurred_at"
        ),
        {"unit_id": facts["unit_id"]},
    ).all()
    assert len(events) == 1
    action, before_payload, after_payload = events[0]
    assert action == "update"
    assert before_payload["name"] == f"审计单元-{facts['unit_code'][-12:]}" or (
        before_payload["name"].startswith("审计单元-")
    )
    assert after_payload["name"] == "改名后的审计单元"
    assert after_payload["rentable_area"] == "75.50"
    # Only touched fields appear in the diff payloads.
    assert "building_area" not in after_payload

    feed = client.get(
        "/api/v1/business-change-events",
        params={"target_type": "asset_unit", "target_id": facts["unit_id"]},
    )
    assert feed.status_code == 200, feed.text
    items = feed.json()["items"] if "items" in feed.json() else feed.json()
    assert any(
        event.get("target_type") == "asset_unit" for event in items
    )


def test_asset_unit_split_writes_audit_event_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    client = authenticated_client
    facts = _seed_split_target(db_session, getattr(client, "_user_id"))
    effective = _TODAY + timedelta(days=30)
    proposal = {
        "effective_date": effective.isoformat(),
        "parts": [
            {
                "unit_code": f"AU-SPLT-A-{uuid4().hex[:6]}",
                "name": "拆分结果A",
                "land_area": "0",
                "building_area": "50",
                "rentable_area": "40",
            },
            {
                "unit_code": f"AU-SPLT-B-{uuid4().hex[:6]}",
                "name": "拆分结果B",
                "land_area": "0",
                "building_area": "50",
                "rentable_area": "40",
            },
        ],
    }
    preview = client.post(
        f"/api/v1/asset-units/{facts['unit_id']}/split/preview",
        json=proposal,
        headers=csrf_headers,
    )
    assert preview.status_code == 200, preview.text
    commit = client.post(
        f"/api/v1/asset-units/{facts['unit_id']}/split",
        json={
            "preview_token": preview.json()["preview_token"],
            "expected_version": preview.json()["versions"][facts["unit_id"]],
            "reason": "审计拆分演练",
        },
        headers={**csrf_headers, "Idempotency-Key": f"split-{uuid4().hex}"},
    )
    assert commit.status_code == 200, commit.text

    events = db_session.execute(
        text(
            "SELECT action, before, after FROM business_change_events "
            "WHERE target_type = 'asset_unit_boundary_change' "
            "AND target_id = :change_id"
        ),
        {"change_id": commit.json()["boundary_change_id"]},
    ).all()
    assert len(events) == 1
    action, before_payload, after_payload = events[0]
    assert action == "split"
    assert before_payload["source_unit_ids"] == [facts["unit_id"]]
    assert len(after_payload["result_unit_ids"]) == 2
