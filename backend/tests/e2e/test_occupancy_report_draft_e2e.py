"""REQ-RPT-002: monthly occupancy-report draft over PostgreSQL, Redis and HTTP.

Only signed starting facts are bootstrapped through the ORM. Draft derivation,
note persistence, fail-closed scope handling and the submitted-month guard run
through the real authenticated application.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.models.assessment_scope import (
    AssessmentScopeItem,
    AssessmentScopeVersion,
)
from src.models.asset_contract import (
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from src.models.asset_unit import AssetUnit
from src.models.attachment import Attachment
from src.models.project import Project
from tests.e2e.factories import create_approved_legal_party

pytestmark = pytest.mark.e2e

_TODAY = datetime.now(UTC).astimezone(ZoneInfo("Asia/Shanghai")).date()


def _closed_period() -> str:
    """The most recent fully closed month, so today's date never gates it."""
    if _TODAY.month == 1:
        return f"{_TODAY.year - 1}-12"
    return f"{_TODAY.year}-{_TODAY.month - 1:02d}"


_PERIOD = _closed_period()
_YEAR = int(_PERIOD[:4])


def _seed_reporting_month(db_session: Session, actor_id: str) -> dict[str, str]:
    """Operator, scope version with one included and one pending unit."""
    suffix = uuid4().hex[:12]
    operator = create_approved_legal_party(
        db_session, suffix=suffix, name=f"报送运营主体-{suffix}"
    )
    tenant = create_approved_legal_party(
        db_session, suffix=suffix, name=f"报送租户-{suffix}"
    )
    project = Project(
        id=str(uuid4()),
        project_code=f"PRJ-RPT-{suffix}",
        project_name=f"报送项目-{suffix}",
        manager_party_id=operator.id,
        status="active",
    )
    db_session.add(project)
    db_session.flush()
    included = AssetUnit(
        id=str(uuid4()),
        unit_code=f"AU-RPT-IN-{suffix}",
        name=f"在租单元-{suffix}",
        project_id=project.id,
        owner_party_id=operator.id,
        address="报送 E2E 地址一",
        usage_type="commercial",
        acquisition_mode="managed",
        is_operating=True,
        land_area=Decimal("1.5"),
        building_area=Decimal("100"),
        rentable_area=Decimal("80"),
        managed_from=_TODAY - timedelta(days=400),
        predecessor_unit_ids=[],
        version=1,
    )
    vacant = AssetUnit(
        id=str(uuid4()),
        unit_code=f"AU-RPT-VAC-{suffix}",
        name=f"空置单元-{suffix}",
        project_id=project.id,
        owner_party_id=operator.id,
        address="报送 E2E 地址二",
        usage_type="commercial",
        acquisition_mode="managed",
        is_operating=True,
        land_area=Decimal("0"),
        building_area=Decimal("60"),
        rentable_area=Decimal("50"),
        managed_from=_TODAY - timedelta(days=400),
        predecessor_unit_ids=[],
        version=1,
    )
    takeover = AssetUnit(
        id=str(uuid4()),
        unit_code=f"AU-RPT-TAKE-{suffix}",
        name=f"年中接管单元-{suffix}",
        project_id=project.id,
        owner_party_id=operator.id,
        address="报送 E2E 地址三",
        usage_type="commercial",
        acquisition_mode="managed",
        is_operating=True,
        land_area=Decimal("0"),
        building_area=Decimal("40"),
        rentable_area=Decimal("30"),
        managed_from=datetime(_YEAR, 6, 15, tzinfo=UTC).date(),
        predecessor_unit_ids=[],
        version=1,
    )
    db_session.add_all([included, vacant, takeover])
    db_session.flush()

    scope_version = AssessmentScopeVersion(
        id=str(uuid4()),
        operator_party_id=operator.id,
        year=_YEAR,
        version_number=1,
        status="active",
        effective_from_period=f"{_YEAR}-01",
        created_by=actor_id,
        activated_by=actor_id,
        activated_at=datetime.now(UTC).replace(tzinfo=None),
        version=1,
    )
    db_session.add(scope_version)
    db_session.flush()
    for unit, reason in (
        (included, None),
        (vacant, None),
    ):
        db_session.add(
            AssessmentScopeItem(
                scope_version_id=scope_version.id,
                asset_unit_id=unit.id,
                included=True,
                exclusion_reason=reason,
                unit_snapshot={},
            )
        )
    db_session.commit()

    # Live terminal contract over the included unit makes it rented at month end.
    upstream_id, terminal_id, scan_id, terminal_scan_id = (
        str(uuid4()),
        str(uuid4()),
        str(uuid4()),
        str(uuid4()),
    )
    db_session.add(
        Attachment(
            id=scan_id,
            owner_type="contract",
            owner_id=upstream_id,
            file_name=f"{scan_id}.pdf",
            file_type="pdf",
            file_size=1,
            storage_key=f"e2e/rpt/{scan_id}.pdf",
            created_by=actor_id,
        )
    )
    db_session.add(
        Attachment(
            id=terminal_scan_id,
            owner_type="contract",
            owner_id=terminal_id,
            file_name="terminal.pdf",
            file_type="pdf",
            file_size=1,
            storage_key=f"e2e/rpt/terminal-{terminal_id}.pdf",
            created_by=actor_id,
        )
    )
    db_session.flush()
    db_session.add(
        UpstreamContract(
            id=upstream_id,
            contract_number=f"UP-RPT-{suffix}",
            contract_type="lease",
            name="报送归属上游",
            owner_party_id=operator.id,
            operator_party_id=operator.id,
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
            asset_unit_id=included.id,
            effective_from=_TODAY - timedelta(days=200),
            effective_to=_TODAY + timedelta(days=365),
        )
    )
    db_session.add(
        TerminalContract(
            id=terminal_id,
            contract_number=f"TM-RPT-{suffix}",
            contract_mode="sublease",
            tenant_party_id=tenant.id,
            lessor_party_id=operator.id,
            upstream_contract_id=upstream_id,
            start_date=_TODAY - timedelta(days=200),
            end_date=_TODAY + timedelta(days=365),
            rent_collector="operator",
            deposit_amount=Decimal("0"),
            scan_document_id=terminal_scan_id,
            version=1,
        )
    )
    db_session.flush()
    db_session.add(
        TerminalContractAssetUnit(
            terminal_contract_id=terminal_id,
            asset_unit_id=included.id,
            effective_from=_TODAY - timedelta(days=200),
            effective_to=_TODAY + timedelta(days=365),
        )
    )
    db_session.commit()
    return {
        "operator_party_id": operator.id,
        "scope_version_id": scope_version.id,
        "included_unit_id": included.id,
        "vacant_unit_id": vacant.id,
        "takeover_unit_id": takeover.id,
        "terminal_id": terminal_id,
    }


def _draft_path(period: str) -> str:
    return f"/api/v1/occupancy-reports/{period}/draft"


def test_occupancy_report_draft_derives_lines_and_gates_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    """Totals recompute from lines; pending units gate submission."""
    client = authenticated_client
    facts = _seed_reporting_month(db_session, getattr(client, "_user_id"))
    operator_id = facts["operator_party_id"]

    draft = client.get(
        _draft_path(_PERIOD), params={"operator_party_id": operator_id}
    )
    assert draft.status_code == 200, draft.text
    body = draft.json()
    assert body["first_report"] is True
    assert body["scope_version"]["version_id"] == facts["scope_version_id"]
    assert body["change_note"] is None

    lines = {line["asset_unit_id"]: line for line in body["lines"]}
    assert set(lines) == {
        facts["included_unit_id"],
        facts["vacant_unit_id"],
    }
    assert lines[facts["included_unit_id"]]["rental_status"] == "rented"
    assert lines[facts["included_unit_id"]]["terminal_contract_ids"] == [
        facts["terminal_id"]
    ]
    assert lines[facts["vacant_unit_id"]]["rental_status"] == "vacant"

    totals = body["totals"]
    assert totals["unit_count"] == 2
    assert totals["rented_unit_count"] == 1
    assert totals["occupancy_rate"] == "0.5"
    assert Decimal(totals["building_area"]) == Decimal("160")
    assert Decimal(totals["rentable_area"]) == Decimal("130")
    assert Decimal(totals["rented_area"]) == Decimal("80")

    assert {p["asset_unit_id"] for p in body["pending"]} == {
        facts["takeover_unit_id"]
    }
    assert body["can_submit"] is False
    assert body["gate_reasons"] == ["pending_units_unconfirmed"]


def test_occupancy_report_draft_note_persists_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    """Note save upserts the chain draft and the draft reads it back."""
    client = authenticated_client
    facts = _seed_reporting_month(db_session, getattr(client, "_user_id"))
    operator_id = facts["operator_party_id"]

    saved = client.put(
        f"/api/v1/occupancy-reports/{_PERIOD}/draft-note",
        json={
            "operator_party_id": operator_id,
            "change_note": "  上月空置单元已出租  ",
        },
        headers=csrf_headers,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["change_note"] == "上月空置单元已出租"

    cleared = client.put(
        f"/api/v1/occupancy-reports/{_PERIOD}/draft-note",
        json={"operator_party_id": operator_id, "change_note": "   "},
        headers=csrf_headers,
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["change_note"] is None


def test_occupancy_report_draft_requires_known_party_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    """Unknown reporting units fail closed before any scope gate."""
    client = authenticated_client
    missing = client.get(
        _draft_path(_PERIOD), params={"operator_party_id": str(uuid4())}
    )
    assert missing.status_code == 404, missing.text

    note = client.put(
        f"/api/v1/occupancy-reports/{_PERIOD}/draft-note",
        json={"operator_party_id": str(uuid4()), "change_note": "x"},
        headers=csrf_headers,
    )
    assert note.status_code == 404, note.text


def test_occupancy_report_draft_rejects_bad_period_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    client = authenticated_client
    facts = _seed_reporting_month(db_session, getattr(client, "_user_id"))
    operator_id = facts["operator_party_id"]

    malformed = client.get(
        _draft_path("2026-13"), params={"operator_party_id": operator_id}
    )
    assert malformed.status_code == 422, malformed.text
    assert (
        malformed.json()["error"]["code"] == "OCCUPANCY_REPORT_PERIOD_INVALID"
    )

    future_month = 12 if _TODAY.month < 12 else 11
    future = client.get(
        _draft_path(f"{_YEAR + 1}-{future_month:02d}"),
        params={"operator_party_id": operator_id},
    )
    assert future.status_code == 422, future.text
    assert future.json()["error"]["details"]["reason"] == "future"

    _ = csrf_headers


def test_occupancy_report_draft_blocks_submitted_month_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    """A submitted snapshot is read-only until withdrawal exists (V3-3)."""
    client = authenticated_client
    facts = _seed_reporting_month(db_session, getattr(client, "_user_id"))
    operator_id = facts["operator_party_id"]
    db_session.execute(
        text(
            "INSERT INTO monthly_occupancy_reports "
            "(id, operator_party_id, period, status, created_by, version) "
            "VALUES (:id, :op, :period, 'submitted', :actor, 1)"
        ),
        {
            "id": str(uuid4()),
            "op": operator_id,
            "period": _PERIOD,
            "actor": str(getattr(client, "_user_id")),
        },
    )
    db_session.commit()

    blocked = client.get(
        _draft_path(_PERIOD), params={"operator_party_id": operator_id}
    )
    assert blocked.status_code == 409, blocked.text
    assert (
        blocked.json()["error"]["code"] == "OCCUPANCY_REPORT_ALREADY_SUBMITTED"
    )

    note_blocked = client.put(
        f"/api/v1/occupancy-reports/{_PERIOD}/draft-note",
        json={"operator_party_id": operator_id, "change_note": "x"},
        headers=csrf_headers,
    )
    assert note_blocked.status_code == 409, note_blocked.text


def test_occupancy_report_draft_fails_closed_without_scope_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    """A real operator without an active scope gets 409 on both endpoints."""
    client = authenticated_client
    suffix = uuid4().hex[:12]
    operator = create_approved_legal_party(
        db_session, suffix=suffix, name=f"无范围主体-{suffix}"
    )
    db_session.commit()

    draft = client.get(
        _draft_path(_PERIOD), params={"operator_party_id": operator.id}
    )
    assert draft.status_code == 409, draft.text
    assert draft.json()["error"]["code"] == "OCCUPANCY_REPORT_SCOPE_MISSING"

    note = client.put(
        f"/api/v1/occupancy-reports/{_PERIOD}/draft-note",
        json={"operator_party_id": operator.id, "change_note": "x"},
        headers=csrf_headers,
    )
    assert note.status_code == 409, note.text
    assert note.json()["error"]["code"] == "OCCUPANCY_REPORT_SCOPE_MISSING"


def test_occupancy_report_draft_empty_denominator_has_null_rate_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    """A scope with no included units yields zero totals and a null rate."""
    client = authenticated_client
    suffix = uuid4().hex[:12]
    operator = create_approved_legal_party(
        db_session, suffix=suffix, name=f"零分母主体-{suffix}"
    )
    project = Project(
        id=str(uuid4()),
        project_code=f"PRJ-ZERO-{suffix}",
        project_name=f"零分母项目-{suffix}",
        manager_party_id=operator.id,
        status="active",
    )
    db_session.add(project)
    db_session.flush()
    unit = AssetUnit(
        id=str(uuid4()),
        unit_code=f"AU-ZERO-{suffix}",
        name=f"排除单元-{suffix}",
        project_id=project.id,
        owner_party_id=operator.id,
        address="x",
        usage_type="commercial",
        acquisition_mode="managed",
        is_operating=True,
        land_area=Decimal("0"),
        building_area=Decimal("10"),
        rentable_area=Decimal("10"),
        managed_from=_TODAY - timedelta(days=400),
        predecessor_unit_ids=[],
        version=1,
    )
    db_session.add(unit)
    db_session.flush()
    scope_version = AssessmentScopeVersion(
        id=str(uuid4()),
        operator_party_id=operator.id,
        year=_YEAR,
        version_number=1,
        status="active",
        effective_from_period=f"{_YEAR}-01",
        created_by=str(getattr(client, "_user_id")),
        activated_by=str(getattr(client, "_user_id")),
        activated_at=datetime.now(UTC).replace(tzinfo=None),
        version=1,
    )
    db_session.add(scope_version)
    db_session.flush()
    db_session.add(
        AssessmentScopeItem(
            scope_version_id=scope_version.id,
            asset_unit_id=unit.id,
            included=False,
            exclusion_reason="整栋自用",
            unit_snapshot={},
        )
    )
    db_session.commit()

    draft = client.get(
        _draft_path(_PERIOD), params={"operator_party_id": operator.id}
    )
    assert draft.status_code == 200, draft.text
    body = draft.json()
    assert body["lines"] == []
    assert body["totals"]["unit_count"] == 0
    assert body["totals"]["occupancy_rate"] is None
    assert body["pending"] == []
    assert body["can_submit"] is True
