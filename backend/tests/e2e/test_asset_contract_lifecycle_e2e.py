"""REQ-CTR-001/002: signed-contract lifecycle over PostgreSQL, Redis and HTTP.

Only the already-signed starting facts are bootstrapped through ORM. Preview,
commit, replay and detail projections use the real authenticated application.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.asset_contract import (
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from src.models.asset_unit import AssetUnit
from src.models.attachment import Attachment
from src.models.deposit_ledger import DepositLedgerEntry
from src.models.project import Project
from tests.e2e.factories import create_approved_legal_party

pytestmark = pytest.mark.e2e


def _seed_signed_contracts(db_session: Session, actor_id: str) -> dict[str, str]:
    """Bootstrap a signed upstream/terminal pair with one shared asset unit."""
    suffix = uuid4().hex[:12]
    today = datetime.now(UTC).astimezone(ZoneInfo("Asia/Shanghai")).date()
    start = today - timedelta(days=60)
    end = today + timedelta(days=365)
    owner = create_approved_legal_party(
        db_session, suffix=suffix, name=f"生命周期产权方-{suffix}"
    )
    tenant = create_approved_legal_party(
        db_session, suffix=suffix, name=f"生命周期租户-{suffix}"
    )
    project = Project(
        id=str(uuid4()),
        project_code=f"PRJ-LIFE-{suffix}",
        project_name=f"生命周期项目-{suffix}",
        manager_party_id=owner.id,
        status="active",
    )
    db_session.add(project)
    db_session.flush()
    unit = AssetUnit(
        id=str(uuid4()),
        unit_code=f"AU-LIFE-{suffix}",
        name=f"生命周期单元-{suffix}",
        project_id=project.id,
        owner_party_id=owner.id,
        address="生命周期 E2E 地址",
        usage_type="commercial",
        acquisition_mode="leased",
        is_operating=True,
        land_area=Decimal("0"),
        building_area=Decimal("100"),
        rentable_area=Decimal("80"),
        managed_from=start,
        predecessor_unit_ids=[],
        version=1,
    )
    db_session.add(unit)
    upstream_id, terminal_id = str(uuid4()), str(uuid4())
    upstream_scan, terminal_scan = str(uuid4()), str(uuid4())
    for scan_id, contract_id in (
        (upstream_scan, upstream_id),
        (terminal_scan, terminal_id),
    ):
        db_session.add(
            Attachment(
                id=scan_id,
                owner_type="contract",
                owner_id=contract_id,
                file_name=f"{scan_id}.pdf",
                file_type="pdf",
                file_size=1,
                storage_key=f"e2e/lifecycle/{scan_id}.pdf",
                created_by=actor_id,
            )
        )
    db_session.flush()
    db_session.add(
        UpstreamContract(
            id=upstream_id,
            contract_number=f"UP-LIFE-{suffix}",
            contract_type="lease",
            name="E2E 已签上游合同",
            owner_party_id=owner.id,
            operator_party_id=owner.id,
            start_date=start,
            end_date=end,
            payment_cycle="monthly",
            payment_day=15,
            deposit_amount=Decimal("1000"),
            scan_document_id=upstream_scan,
            version=1,
        )
    )
    db_session.flush()
    db_session.add(
        TerminalContract(
            id=terminal_id,
            contract_number=f"TM-LIFE-{suffix}",
            contract_mode="sublease",
            tenant_party_id=tenant.id,
            lessor_party_id=owner.id,
            upstream_contract_id=upstream_id,
            start_date=start,
            end_date=end,
            rent_collector="operator",
            deposit_amount=Decimal("500"),
            scan_document_id=terminal_scan,
            version=1,
        )
    )
    db_session.flush()
    db_session.add_all(
        [
            UpstreamContractAssetUnit(
                upstream_contract_id=upstream_id,
                asset_unit_id=unit.id,
                effective_from=start,
                effective_to=end,
            ),
            TerminalContractAssetUnit(
                terminal_contract_id=terminal_id,
                asset_unit_id=unit.id,
                effective_from=start,
                effective_to=end,
            ),
        ]
    )
    db_session.add_all(
        [
            DepositLedgerEntry(
                id=str(uuid4()),
                contract_kind="upstream",
                contract_id=upstream_id,
                collector="owner",
                version=1,
            ),
            DepositLedgerEntry(
                id=str(uuid4()),
                contract_kind="terminal",
                contract_id=terminal_id,
                collector="operator",
                version=1,
            ),
        ]
    )
    db_session.commit()
    return {
        "upstream_id": upstream_id,
        "terminal_id": terminal_id,
        "unit_id": unit.id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "effective_date": today.isoformat(),
        "cutoff": (today - timedelta(days=1)).isoformat(),
    }


def test_terminal_termination_unlocks_upstream_exit_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    """Block exit, terminate terminal, then exit upstream; replay each once."""
    client = authenticated_client
    facts = _seed_signed_contracts(db_session, getattr(client, "_user_id"))
    upstream_path = f"/api/v1/upstream-contracts/{facts['upstream_id']}"
    terminal_path = f"/api/v1/terminal-contracts/{facts['terminal_id']}"
    exit_proposal = {
        "effective_date": facts["effective_date"],
        "reason": "E2E 上游退出",
    }

    missing_csrf = client.post(f"{upstream_path}/exit/preview", json=exit_proposal)
    assert missing_csrf.status_code == 403, missing_csrf.text

    blocked = client.post(
        f"{upstream_path}/exit/preview", json=exit_proposal, headers=csrf_headers
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["error"]["code"] == "ACTIVE_TERMINAL_CONTRACTS_BLOCK_EXIT"
    assert (
        facts["terminal_id"]
        in blocked.json()["error"]["details"]["terminal_contract_ids"]
    )

    upstream_before = client.get(upstream_path)
    assert upstream_before.status_code == 200, upstream_before.text
    for invalid_terms in (
        {"management_fee_rate": "0.10"},
        {"management_fee_rate": None},
        {"payment_cycle": "quarterly"},
        {"payment_day": 20},
    ):
        rejected = client.patch(
            upstream_path,
            json={
                "expected_version": upstream_before.json()["version"],
                **invalid_terms,
            },
            headers=csrf_headers,
        )
        assert rejected.status_code == 422, rejected.text
        if "management_fee_rate" in invalid_terms:
            assert rejected.json()["error"]["code"] == "CONTRACT_FIELD_NOT_APPLICABLE"

    for path, action, proposal, event_type, expected_status in (
        (
            terminal_path,
            "termination",
            {
                "effective_date": facts["effective_date"],
                "termination_type": "early",
                "handover_status": "completed",
                "deposit_settlement_status": "settled",
                "reason": "E2E 终端交接结清后终止",
            },
            "terminated",
            "ended",
        ),
        (upstream_path, "exit", exit_proposal, "exited", "exited"),
    ):
        before = client.get(path)
        assert before.status_code == 200, before.text
        assert before.json()["status"] == "active"
        assert before.json()["lifecycle_events"] == []
        assert before.json()["coverages"] == [
            {
                "asset_unit_id": facts["unit_id"],
                "effective_from": facts["start"],
                "effective_to": facts["end"],
            }
        ]
        preview = client.post(
            f"{path}/{action}/preview", json=proposal, headers=csrf_headers
        )
        assert preview.status_code == 200, preview.text
        impact = preview.json()
        assert impact["last_valid_day"] == facts["cutoff"]
        assert impact["coverage_impact"] == [
            {
                "asset_unit_id": facts["unit_id"],
                "effective_from": facts["start"],
                "current_effective_to": facts["end"],
                "new_effective_to": facts["cutoff"],
            }
        ]
        payload = {
            "preview_token": impact["preview_token"],
            "expected_version": impact["contract_version"],
        }
        headers = {**csrf_headers, "Idempotency-Key": str(uuid4())}
        committed = client.post(f"{path}/{action}", json=payload, headers=headers)
        assert committed.status_code == 200, committed.text
        event = committed.json()
        assert event["event_type"] == event_type
        assert event["effective_date"] == facts["effective_date"]
        assert event["idempotent"] is False
        replay = client.post(f"{path}/{action}", json=payload, headers=headers)
        assert replay.status_code == 200, replay.text
        assert replay.json()["id"] == event["id"]
        assert replay.json()["idempotent"] is True

        detail = client.get(path)
        assert detail.status_code == 200, detail.text
        assert detail.json()["status"] == expected_status
        assert detail.json()["coverages"] == [
            {
                "asset_unit_id": facts["unit_id"],
                "effective_from": facts["start"],
                "effective_to": facts["cutoff"],
            }
        ]
        events = detail.json()["lifecycle_events"]
        assert len(events) == 1
        assert events[0]["id"] == event["id"]
        assert events[0]["event_type"] == event_type

        changes = client.get(
            "/api/v1/business-change-events",
            params={
                "target_type": (
                    "terminal_contract"
                    if action == "termination"
                    else "upstream_contract"
                ),
                "target_id": path.rsplit("/", 1)[1],
            },
        )
        assert changes.status_code == 200, changes.text
        audit = changes.json()
        assert audit["total"] == 2, "命令和重排各一条，幂等重试不得重复写入"
        assert len(audit["items"]) == 2
        change = next(item for item in audit["items"] if item["action"] == event_type)
        assert len({item["correlation_id"] for item in audit["items"]}) == 1
        assert change["action"] == event_type
        assert change["actor_id"] == getattr(client, "_user_id")
        assert change["reason"] == proposal["reason"]
        assert change["correlation_id"]
        assert change["summary"]

    unit_detail = client.get(f"/api/v1/asset-units/{facts['unit_id']}")
    assert unit_detail.status_code == 200, unit_detail.text
    assert unit_detail.json()["rental_status"] == "vacant"
    assert unit_detail.json()["terminal_contract_ids"] == []
    invalid_period = client.get(
        "/api/v1/business-change-events", params={"period": "2026-13"}
    )
    assert invalid_period.status_code == 400, invalid_period.text
    assert invalid_period.json()["error"]["code"] == "INVALID_PERIOD"
