"""REQ-RPT-002: occupancy-report submission, snapshot and withdrawal over HTTP.

Signed starting facts are bootstrapped through the ORM; preview, submit,
snapshot diff, withdrawal and replay run through the real application.
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
from tests.e2e.test_occupancy_report_draft_e2e import _closed_period

pytestmark = pytest.mark.e2e

_TODAY = datetime.now(UTC).astimezone(ZoneInfo("Asia/Shanghai")).date()
_PERIOD = _closed_period()
_YEAR = int(_PERIOD[:4])


def _seed_submission_ready(
    db_session: Session,
    actor_id: str,
    *,
    with_contract: bool = True,
    change_note: str | None = None,
) -> dict[str, str]:
    """Operator with one included unit at month end and an active scope."""
    suffix = uuid4().hex[:12]
    operator = create_approved_legal_party(
        db_session, suffix=suffix, name=f"提交主体-{suffix}"
    )
    project = Project(
        id=str(uuid4()),
        project_code=f"PRJ-SUB-{suffix}",
        project_name=f"提交项目-{suffix}",
        manager_party_id=operator.id,
        status="active",
    )
    db_session.add(project)
    db_session.flush()
    unit = AssetUnit(
        id=str(uuid4()),
        unit_code=f"AU-SUB-{suffix}",
        name=f"提交单元-{suffix}",
        project_id=project.id,
        owner_party_id=operator.id,
        address="提交 E2E 地址",
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
    db_session.add(unit)
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
    db_session.add(
        AssessmentScopeItem(
            scope_version_id=scope_version.id,
            asset_unit_id=unit.id,
            included=True,
            exclusion_reason=None,
            unit_snapshot={},
        )
    )
    if change_note is not None:
        db_session.add(
            _chain_row(
                operator_id=operator.id,
                period=_PERIOD,
                actor_id=actor_id,
                change_note=change_note,
            )
        )
    db_session.commit()

    terminal_id: str | None = None
    if with_contract:
        tenant = create_approved_legal_party(
            db_session, suffix=suffix, name=f"提交租户-{suffix}"
        )
        upstream_id, terminal_id, scan_id, terminal_scan = (
            str(uuid4()),
            str(uuid4()),
            str(uuid4()),
            str(uuid4()),
        )
        for attachment_id, owner in (
            (scan_id, upstream_id),
            (terminal_scan, terminal_id),
        ):
            db_session.add(
                Attachment(
                    id=attachment_id,
                    owner_type="contract",
                    owner_id=owner,
                    file_name=f"{attachment_id}.pdf",
                    file_type="pdf",
                    file_size=1,
                    storage_key=f"e2e/sub/{attachment_id}.pdf",
                    created_by=actor_id,
                )
            )
        db_session.flush()
        db_session.add(
            UpstreamContract(
                id=upstream_id,
                contract_number=f"UP-SUB-{suffix}",
                contract_type="lease",
                name="提交归属上游",
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
                asset_unit_id=unit.id,
                effective_from=_TODAY - timedelta(days=200),
                effective_to=_TODAY + timedelta(days=365),
            )
        )
        db_session.add(
            TerminalContract(
                id=terminal_id,
                contract_number=f"TM-SUB-{suffix}",
                contract_mode="sublease",
                tenant_party_id=tenant.id,
                lessor_party_id=operator.id,
                upstream_contract_id=upstream_id,
                start_date=_TODAY - timedelta(days=200),
                end_date=_TODAY + timedelta(days=365),
                rent_collector="operator",
                deposit_amount=Decimal("0"),
                scan_document_id=terminal_scan,
                version=1,
            )
        )
        db_session.flush()
        db_session.add(
            TerminalContractAssetUnit(
                terminal_contract_id=terminal_id,
                asset_unit_id=unit.id,
                effective_from=_TODAY - timedelta(days=200),
                effective_to=_TODAY + timedelta(days=365),
            )
        )
        db_session.commit()
    return {
        "operator_party_id": operator.id,
        "scope_version_id": scope_version.id,
        "unit_id": unit.id,
        "terminal_id": terminal_id,
    }


def _chain_row(
    *,
    operator_id: str,
    period: str,
    actor_id: str,
    change_note: str | None,
    status: str = "draft",
) -> object:
    from src.models.occupancy_report import MonthlyOccupancyReport

    return MonthlyOccupancyReport(
        id=str(uuid4()),
        operator_party_id=operator_id,
        period=period,
        status=status,
        change_note=change_note,
        created_by=actor_id,
    )


def _preview(
    client: TestClient, csrf_headers: dict[str, str], operator_id: str
) -> dict:
    response = client.post(
        f"/api/v1/occupancy-reports/{_PERIOD}/submission-preview",
        params={"operator_party_id": operator_id},
        headers=csrf_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _submit(
    client: TestClient,
    csrf_headers: dict[str, str],
    operator_id: str,
    payload: dict,
    key: str,
):
    return client.post(
        f"/api/v1/occupancy-reports/{_PERIOD}/submissions",
        params={"operator_party_id": operator_id},
        json=payload,
        headers={**csrf_headers, "Idempotency-Key": key},
    )


def test_occupancy_report_submit_snapshot_and_export_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    """Preview, submit, read the snapshot and queue an export (V3-T08 base)."""
    client = authenticated_client
    facts = _seed_submission_ready(
        db_session, getattr(client, "_user_id"), change_note="首次报送"
    )
    operator_id = facts["operator_party_id"]

    preview = _preview(client, csrf_headers, operator_id)
    assert preview["can_submit"] is True
    assert preview["preview_token"] is not None
    assert preview["scope_version"]["version_id"] == facts["scope_version_id"]
    assert preview["normalized_note"] == "首次报送"

    token = preview["preview_token"]
    committed = _submit(
        client,
        csrf_headers,
        operator_id,
        {
            "preview_token": token,
            "expected_scope_version_id": facts["scope_version_id"],
            "expected_scope_version": 1,
        },
        f"submit-{uuid4().hex}",
    )
    assert committed.status_code == 200, committed.text
    body = committed.json()
    assert body["status"] == "submitted"
    assert body["line_count"] == 1
    assert body["totals"]["unit_count"] == 1
    assert body["totals"]["rented_unit_count"] == 1
    assert Decimal(body["totals"]["rented_area"]) == Decimal("80")
    report_id = body["report_id"]

    blocked_draft = client.get(
        f"/api/v1/occupancy-reports/{_PERIOD}/draft",
        params={"operator_party_id": operator_id},
    )
    assert blocked_draft.status_code == 409, blocked_draft.text
    assert (
        blocked_draft.json()["error"]["code"]
        == "OCCUPANCY_REPORT_ALREADY_SUBMITTED"
    )

    snapshot = client.get(f"/api/v1/occupancy-reports/{report_id}")
    assert snapshot.status_code == 200, snapshot.text
    snap = snapshot.json()
    assert snap["status"] == "submitted"
    assert snap["scope_version"]["version_id"] == facts["scope_version_id"]
    assert len(snap["lines"]) == 1
    assert snap["lines"][0]["terminal_contract_ids"] == [facts["terminal_id"]]
    assert snap["differences"] == []
    assert snap["project_counts"]["project_count"] == 1
    assert snap["project_counts"]["operating_project_count"] == 1

    export = client.post(
        f"/api/v1/occupancy-reports/{report_id}/exports", headers=csrf_headers
    )
    assert export.status_code == 200, export.text
    task_id = export.json()["task_id"]
    task_view = client.get(f"/api/v1/tasks/{task_id}")
    assert task_view.status_code == 200, task_view.text
    result = task_view.json().get("result_data")
    assert result is not None, task_view.text
    import base64 as _base64

    csv_content = _base64.b64decode(result["content_base64"]).decode("utf-8")
    header = csv_content.splitlines()[0]
    assert header.startswith("asset_unit_id,owner_name")
    assert facts["unit_id"] in csv_content


def test_occupancy_report_gates_cannot_be_bypassed_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    """Pending units block preview tokens; direct submits cannot pass (T06)."""
    client = authenticated_client
    facts = _seed_submission_ready(
        db_session, getattr(client, "_user_id"), with_contract=False
    )
    operator_id = facts["operator_party_id"]
    # A mid-period takeover creates a must-handle pending unit.
    takeover = AssetUnit(
        id=str(uuid4()),
        unit_code=f"AU-PEND-{uuid4().hex[:8]}",
        name="待确认单元",
        project_id=db_session.get(AssetUnit, facts["unit_id"]).project_id,
        owner_party_id=operator_id,
        address="x",
        usage_type="commercial",
        acquisition_mode="managed",
        is_operating=True,
        land_area=Decimal("0"),
        building_area=Decimal("10"),
        rentable_area=Decimal("10"),
        managed_from=datetime(_YEAR, 6, 1, tzinfo=UTC).date(),
        predecessor_unit_ids=[],
        version=1,
    )
    db_session.add(takeover)
    db_session.commit()

    preview = _preview(client, csrf_headers, operator_id)
    assert preview["can_submit"] is False
    assert preview["gate_reasons"] == ["pending_units_unconfirmed"]
    assert preview["preview_token"] is None
    assert preview["must_handle"] == [
        {"asset_unit_id": takeover.id, "reason": "new_takeover"}
    ]

    bypass = _submit(
        client,
        csrf_headers,
        operator_id,
        {
            "preview_token": "forged-token",
            "expected_scope_version_id": facts["scope_version_id"],
            "expected_scope_version": 1,
        },
        f"bypass-{uuid4().hex}",
    )
    assert bypass.status_code == 409, bypass.text
    assert bypass.json()["error"]["code"] == "PREVIEW_STALE"

    orphan_lines = db_session.execute(
        text(
            "SELECT count(*) FROM monthly_occupancy_report_lines l "
            "JOIN monthly_occupancy_reports r ON r.id = l.report_id "
            "WHERE r.operator_party_id = :op"
        ),
        {"op": operator_id},
    ).scalar_one()
    assert orphan_lines == 0


def test_occupancy_report_rejects_stale_state_without_side_effects_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    """Facts drifting after preview make commit stale; nothing persists (T07)."""
    client = authenticated_client
    facts = _seed_submission_ready(
        db_session, getattr(client, "_user_id"), change_note="说明"
    )
    operator_id = facts["operator_party_id"]
    preview = _preview(client, csrf_headers, operator_id)
    assert preview["can_submit"] is True

    db_session.execute(
        text("UPDATE asset_units SET version = version + 1 WHERE id = :u"),
        {"u": facts["unit_id"]},
    )
    db_session.commit()

    stale = _submit(
        client,
        csrf_headers,
        operator_id,
        {
            "preview_token": preview["preview_token"],
            "expected_scope_version_id": facts["scope_version_id"],
            "expected_scope_version": 1,
        },
        f"stale-{uuid4().hex}",
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["error"]["code"] == "PREVIEW_STALE"
    assert stale.json()["error"]["details"]["reason"] == "state_changed"

    # Failure leaves no snapshot, lines, receipts or audit rows behind.
    draft = client.get(
        f"/api/v1/occupancy-reports/{_PERIOD}/draft",
        params={"operator_party_id": operator_id},
    )
    assert draft.status_code == 200, draft.text
    lines_count = db_session.execute(
        text(
            "SELECT count(*) FROM monthly_occupancy_report_lines l "
            "JOIN monthly_occupancy_reports r ON r.id = l.report_id "
            "WHERE r.operator_party_id = :op"
        ),
        {"op": operator_id},
    ).scalar_one()
    assert lines_count == 0
    receipt_count = db_session.execute(
        text(
            "SELECT count(*) FROM asset_contract_write_receipts "
            "WHERE command_kind = 'submit_occupancy_report' "
            "AND result_data->>'operatorPartyId' = :op"
        ),
        {"op": operator_id},
    ).scalar_one()
    assert receipt_count == 0
    audit_count = db_session.execute(
        text(
            "SELECT count(*) FROM business_change_events "
            "WHERE target_type = 'monthly_occupancy_report' "
            "AND before->>'operator_party_id' = :op"
        ),
        {"op": operator_id},
    ).scalar_one()
    assert audit_count == 0


def test_occupancy_report_submit_replay_requires_same_request_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    client = authenticated_client
    facts = _seed_submission_ready(
        db_session, getattr(client, "_user_id"), change_note="回放"
    )
    operator_id = facts["operator_party_id"]
    preview = _preview(client, csrf_headers, operator_id)
    key = f"replay-{uuid4().hex}"
    payload = {
        "preview_token": preview["preview_token"],
        "expected_scope_version_id": facts["scope_version_id"],
        "expected_scope_version": 1,
    }
    first = _submit(client, csrf_headers, operator_id, payload, key)
    assert first.status_code == 200, first.text

    replayed = _submit(client, csrf_headers, operator_id, payload, key)
    assert replayed.status_code == 200, replayed.text
    assert replayed.json()["idempotent"] is True
    assert replayed.json()["report_id"] == first.json()["report_id"]

    conflict = _submit(
        client,
        csrf_headers,
        operator_id,
        {**payload, "expected_scope_version": 1},
        f"other-{uuid4().hex}",
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["error"]["code"] == "PREVIEW_STALE"


def test_occupancy_report_withdrawal_chain_and_resubmit_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    """Withdraw keeps the snapshot, opens a successor, resubmit relinks (T09)."""
    client = authenticated_client
    facts = _seed_submission_ready(
        db_session, getattr(client, "_user_id"), change_note="撤回演练"
    )
    operator_id = facts["operator_party_id"]
    preview = _preview(client, csrf_headers, operator_id)
    first = _submit(
        client,
        csrf_headers,
        operator_id,
        {
            "preview_token": preview["preview_token"],
            "expected_scope_version_id": facts["scope_version_id"],
            "expected_scope_version": 1,
        },
        f"wd-{uuid4().hex}",
    )
    assert first.status_code == 200, first.text
    report_id = first.json()["report_id"]

    wd_preview = client.post(
        f"/api/v1/occupancy-reports/{report_id}/withdrawal-preview",
        headers=csrf_headers,
    )
    assert wd_preview.status_code == 200, wd_preview.text
    assert (
        wd_preview.json()["successor_draft_rule"]
        == "fresh_draft_with_predecessor_link"
    )

    withdraw_key = f"wd-{uuid4().hex}"
    withdraw_payload = {
        "preview_token": wd_preview.json()["preview_token"],
        "expected_version": wd_preview.json()["report_version"],
        "withdraw_reason": "数据口径需要更正",
    }
    withdrawn = client.post(
        f"/api/v1/occupancy-reports/{report_id}/withdrawal",
        json=withdraw_payload,
        headers={**csrf_headers, "Idempotency-Key": withdraw_key},
    )
    assert withdrawn.status_code == 200, withdrawn.text
    successor_id = withdrawn.json()["successor_draft_id"]
    assert successor_id

    repeat = client.post(
        f"/api/v1/occupancy-reports/{report_id}/withdrawal",
        json={
            "preview_token": wd_preview.json()["preview_token"],
            "expected_version": wd_preview.json()["report_version"],
            "withdraw_reason": "重复撤回",
        },
        headers={**csrf_headers, "Idempotency-Key": f"wd-{uuid4().hex}"},
    )
    assert repeat.status_code == 409, repeat.text
    assert (
        repeat.json()["error"]["code"] == "OCCUPANCY_REPORT_ALREADY_WITHDRAWN"
    )

    snapshot = client.get(f"/api/v1/occupancy-reports/{report_id}")
    assert snapshot.status_code == 200, snapshot.text
    snap = snapshot.json()
    assert snap["status"] == "withdrawn"
    assert len(snap["lines"]) == 1
    assert snap["withdraw_reason"] == "数据口径需要更正"

    # Same-key replay of the withdrawal returns the first response verbatim.
    replayed_withdraw = client.post(
        f"/api/v1/occupancy-reports/{report_id}/withdrawal",
        json={
            "preview_token": wd_preview.json()["preview_token"],
            "expected_version": wd_preview.json()["report_version"],
            "withdraw_reason": "数据口径需要更正",
        },
        headers={**csrf_headers, "Idempotency-Key": withdraw_key},
    )
    assert replayed_withdraw.status_code == 200, replayed_withdraw.text
    assert replayed_withdraw.json()["idempotent"] is True
    assert replayed_withdraw.json()["report_id"] == report_id

    # The successor draft is immediately editable and resubmittable.
    noted = client.put(
        f"/api/v1/occupancy-reports/{_PERIOD}/draft-note",
        json={"operator_party_id": operator_id, "change_note": "重报说明"},
        headers=csrf_headers,
    )
    assert noted.status_code == 200, noted.text
    assert noted.json()["draft_id"] == successor_id

    second_preview = _preview(client, csrf_headers, operator_id)
    assert second_preview["can_submit"] is True
    second = _submit(
        client,
        csrf_headers,
        operator_id,
        {
            "preview_token": second_preview["preview_token"],
            "expected_scope_version_id": facts["scope_version_id"],
            "expected_scope_version": 1,
        },
        f"wd2-{uuid4().hex}",
    )
    assert second.status_code == 200, second.text
    assert second.json()["report_id"] != report_id

    # Editing the master data now only surfaces as snapshot differences.
    db_session.execute(
        text(
            "UPDATE asset_units SET usage_type = 'industrial', "
            "rentable_area = rentable_area - 10 WHERE id = :u"
        ),
        {"u": facts["unit_id"]},
    )
    db_session.commit()
    diffed = client.get(f"/api/v1/occupancy-reports/{second.json()['report_id']}")
    assert diffed.status_code == 200, diffed.text
    diffs = diffed.json()["differences"]
    assert len(diffs) == 1
    assert diffs[0]["kind"] == "changed"
    changed_fields = {change["field_name"] for change in diffs[0]["changes"]}
    # rented_area of a rented line derives from rentable_area, so the cut
    # shows up in both columns of the snapshot diff.
    assert changed_fields == {"usage_type", "rentable_area", "rented_area"}


def test_occupancy_report_withdraw_race_admits_single_winner_e2e(
    require_redis,
    test_database_url,
) -> None:
    """Two concurrent withdrawals of one snapshot admit exactly one (T09)."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from sqlalchemy import text as sql_text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from src.core.exception_handler import BaseBusinessError
    from src.models.auth import User
    from src.models.occupancy_report import MonthlyOccupancyReport
    from src.models.party import Party, PartyType
    from src.schemas.asset_operations import WithdrawOccupancyReportRequest
    from src.services.asset_operations.errors import (
        OccupancyReportAlreadyWithdrawnError,
    )
    from src.services.asset_operations.occupancy_report_submission_service import (
        occupancy_report_submission_service as svc,
    )
    from src.services.party_scope_resolver import EffectivePartyScope

    async_url = test_database_url.replace(
        "postgresql+psycopg://", "postgresql+asyncpg://", 1
    )

    async def seed():
        engine = create_async_engine(async_url, poolclass=NullPool)
        try:
            maker = async_sessionmaker(engine, expire_on_commit=False)
            async with maker() as db:
                actor = User(
                    id=str(uuid4()),
                    username=f"wdrace-{uuid4().hex[:10]}",
                    email=f"wdrace-{uuid4().hex[:10]}@example.com",
                    phone=f"13{uuid4().int % 10**9:09d}",
                    full_name="撤回并发",
                    password_hash="unused",
                    account_type="service",
                    is_active=True,
                )
                operator = Party(
                    id=str(uuid4()),
                    party_type=PartyType.LEGAL_ENTITY,
                    name=f"撤回并发主体-{uuid4().hex[:8]}",
                    code=f"LE-{uuid4().int % 1_000_000:06d}",
                    status="active",
                    review_status="approved",
                )
                db.add_all([actor, operator])
                await db.flush()
                report = MonthlyOccupancyReport(
                    id=str(uuid4()),
                    operator_party_id=operator.id,
                    period=_PERIOD,
                    status="submitted",
                    submitted_by=actor.id,
                    submitted_at=datetime.now(UTC).replace(tzinfo=None),
                    created_by=actor.id,
                )
                db.add(report)
                await db.commit()
                return {
                    "actor_id": actor.id,
                    "operator_id": operator.id,
                    "report_id": report.id,
                    "report_version": report.version,
                }
        finally:
            await engine.dispose()

    facts = asyncio.run(seed())
    scope = EffectivePartyScope(
        user_id=facts["actor_id"], source="role", scope_mode="unrestricted"
    )

    async def make_token() -> str:
        engine = create_async_engine(async_url, poolclass=NullPool)
        try:
            maker = async_sessionmaker(engine, expire_on_commit=False)
            async with maker() as db:
                preview = await svc.withdrawal_preview(
                    db,
                    report_id=facts["report_id"],
                    actor_id=facts["actor_id"],
                    scope=scope,
                )
                return preview.preview_token
        finally:
            await engine.dispose()

    token = asyncio.run(make_token())

    def attempt(key: str):
        async def run():
            engine = create_async_engine(async_url, poolclass=NullPool)
            try:
                maker = async_sessionmaker(engine, expire_on_commit=False)
                async with maker() as db:
                    try:
                        return await svc.withdraw(
                            db,
                            report_id=facts["report_id"],
                            request=WithdrawOccupancyReportRequest(
                                preview_token=token,
                                expected_version=facts["report_version"],
                                withdraw_reason="竞争撤回",
                            ),
                            actor_id=facts["actor_id"],
                            scope=scope,
                            idempotency_key=key,
                        )
                    except Exception as error:  # noqa: BLE001
                        await db.rollback()
                        return error
            finally:
                await engine.dispose()

        return asyncio.run(run())

    keys = [f"wd-race-{uuid4().hex}", f"wd-race-{uuid4().hex}"]
    blocker_ready = Event()
    started = Event()
    lock_key = f"occupancy_report:{facts['operator_id']}:{_PERIOD}"

    def hold_lock():
        engine = create_async_engine(async_url, poolclass=NullPool)

        async def hold():
            maker = async_sessionmaker(engine)
            async with maker() as db:
                await db.execute(
                    sql_text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
                    {"k": lock_key},
                )
                blocker_ready.set()
                started.wait(timeout=15)
                await asyncio.sleep(2)
            await db.rollback()

        try:
            asyncio.run(hold())
        finally:
            engine.dispose()

    with ThreadPoolExecutor(max_workers=3) as workers:
        holder = workers.submit(hold_lock)
        blocker_ready.wait(timeout=10)
        results = list(workers.map(attempt, keys))
        holder.result(timeout=20)

    successes = [r for r in results if not isinstance(r, BaseBusinessError)]
    failures = [r for r in results if isinstance(r, BaseBusinessError)]
    assert len(successes) == 1, results
    assert len(failures) == 1, results
    failure = failures[0]
    # 终态检查先于 token 消费（见 withdraw 实现）：败方必然收到"已撤回"，
    # 而非笼统的业务错误，这里不得再放宽到 BaseBusinessError。
    assert isinstance(failure, OccupancyReportAlreadyWithdrawnError), results
