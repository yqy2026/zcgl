"""REQ-RPT-001: assessment-scope versions over PostgreSQL, Redis and HTTP.

Only signed starting facts are bootstrapped through the ORM. Draft creation,
decisions, preview, commit, replay and conflict handling use the real
authenticated application.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.exception_handler import BaseBusinessError
from src.models.assessment_scope import (
    AssessmentScopeItem,
    AssessmentScopeVersion,
)
from src.models.asset_contract import (
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from src.models.asset_unit import AssetUnit
from src.models.attachment import Attachment
from src.models.project import Project
from tests.e2e.factories import create_approved_legal_party

pytestmark = pytest.mark.e2e

_YEAR = datetime.now(UTC).astimezone(ZoneInfo("Asia/Shanghai")).year


def _seed_scope_sources(db_session: Session, actor_id: str) -> dict[str, str]:
    """One operator with a stock unit, a mid-year takeover and a covered unit."""
    suffix = uuid4().hex[:12]
    today = datetime.now(UTC).astimezone(ZoneInfo("Asia/Shanghai")).date()
    operator = create_approved_legal_party(
        db_session, suffix=suffix, name=f"考核运营主体-{suffix}"
    )
    project = Project(
        id=str(uuid4()),
        project_code=f"PRJ-SCOPE-{suffix}",
        project_name=f"考核项目-{suffix}",
        manager_party_id=operator.id,
        status="active",
    )
    db_session.add(project)
    db_session.flush()
    stock = AssetUnit(
        id=str(uuid4()),
        unit_code=f"AU-STOCK-{suffix}",
        name=f"存量单元-{suffix}",
        project_id=project.id,
        owner_party_id=operator.id,
        address="考核 E2E 地址",
        usage_type="commercial",
        acquisition_mode="managed",
        is_operating=True,
        land_area=Decimal("0"),
        building_area=Decimal("100"),
        rentable_area=Decimal("80"),
        managed_from=today - timedelta(days=400),
        predecessor_unit_ids=[],
        version=1,
    )
    takeover = AssetUnit(
        id=str(uuid4()),
        unit_code=f"AU-TAKE-{suffix}",
        name=f"年中接管单元-{suffix}",
        project_id=project.id,
        owner_party_id=operator.id,
        address="考核 E2E 地址",
        usage_type="commercial",
        acquisition_mode="managed",
        is_operating=True,
        land_area=Decimal("0"),
        building_area=Decimal("50"),
        rentable_area=Decimal("40"),
        managed_from=datetime(_YEAR, 6, 15, tzinfo=UTC).date(),
        predecessor_unit_ids=[],
        version=1,
    )
    covered = AssetUnit(
        id=str(uuid4()),
        unit_code=f"AU-COV-{suffix}",
        name=f"上游覆盖单元-{suffix}",
        project_id=project.id,
        owner_party_id=operator.id,
        address="考核 E2E 地址",
        usage_type="commercial",
        acquisition_mode="leased",
        is_operating=True,
        land_area=Decimal("0"),
        building_area=Decimal("70"),
        rentable_area=Decimal("60"),
        managed_from=today - timedelta(days=200),
        predecessor_unit_ids=[],
        version=1,
    )
    db_session.add_all([stock, takeover, covered])
    db_session.flush()

    upstream_id, scan_id = str(uuid4()), str(uuid4())
    db_session.add(
        Attachment(
            id=scan_id,
            owner_type="contract",
            owner_id=upstream_id,
            file_name=f"{scan_id}.pdf",
            file_type="pdf",
            file_size=1,
            storage_key=f"e2e/scope/{scan_id}.pdf",
            created_by=actor_id,
        )
    )
    db_session.flush()
    db_session.add(
        UpstreamContract(
            id=upstream_id,
            contract_number=f"UP-SCOPE-{suffix}",
            contract_type="lease",
            name="E2E 考核归属上游合同",
            owner_party_id=operator.id,
            operator_party_id=operator.id,
            start_date=today - timedelta(days=200),
            end_date=today + timedelta(days=365),
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
            asset_unit_id=covered.id,
            effective_from=today - timedelta(days=200),
            effective_to=today + timedelta(days=365),
        )
    )
    db_session.commit()
    return {
        "operator_party_id": operator.id,
        "stock_unit_id": stock.id,
        "takeover_unit_id": takeover.id,
        "covered_unit_id": covered.id,
    }


def _draft_path(draft_id: str) -> str:
    return f"/api/v1/assessment-scope-drafts/{draft_id}"


def test_assessment_scope_draft_to_active_version_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    """Defaults, explicit decisions, preview and the first active version."""
    client = authenticated_client
    facts = _seed_scope_sources(db_session, getattr(client, "_user_id"))
    operator_id = facts["operator_party_id"]
    overview_path = f"/api/v1/assessment-scopes/{_YEAR}"

    empty = client.get(overview_path, params={"operator_party_id": operator_id})
    assert empty.status_code == 200, empty.text
    assert empty.json()["scope"] is None
    assert empty.json()["items"] == []
    assert {p["asset_unit_id"] for p in empty.json()["pending"]} == {
        facts["stock_unit_id"],
        facts["takeover_unit_id"],
        facts["covered_unit_id"],
    }

    created = client.post(
        f"{overview_path}/drafts",
        json={"operator_party_id": operator_id, "source": "current"},
        headers=csrf_headers,
    )
    assert created.status_code == 200, created.text
    draft = created.json()
    draft_id = draft["draft_id"]
    items = {item["asset_unit_id"]: item for item in draft["items"]}
    assert items[facts["stock_unit_id"]]["included"] is True
    assert set(items) == {facts["stock_unit_id"]}
    pending_reasons = {
        p["asset_unit_id"]: p["reason"] for p in draft["pending"]
    }
    assert pending_reasons[facts["takeover_unit_id"]] == "new_takeover"
    assert pending_reasons[facts["covered_unit_id"]] == "new_takeover"

    duplicate = client.post(
        f"{overview_path}/drafts",
        json={"operator_party_id": operator_id, "source": "current"},
        headers=csrf_headers,
    )
    assert duplicate.status_code == 409, duplicate.text
    assert (
        duplicate.json()["error"]["code"] == "ASSESSMENT_SCOPE_DRAFT_EXISTS"
    )
    assert duplicate.json()["error"]["details"]["draft_id"] == draft_id

    rejected = client.put(
        _draft_path(draft_id),
        json={
            "expected_version": draft["version"],
            "decisions": [
                {
                    "asset_unit_id": facts["stock_unit_id"],
                    "included": False,
                    "exclusion_reason": "   ",
                }
            ],
        },
        headers=csrf_headers,
    )
    assert rejected.status_code == 422, rejected.text

    unknown = client.put(
        _draft_path(draft_id),
        json={
            "expected_version": draft["version"],
            "decisions": [
                {
                    "asset_unit_id": str(uuid4()),
                    "included": False,
                    "exclusion_reason": "不存在",
                }
            ],
        },
        headers=csrf_headers,
    )
    assert unknown.status_code == 404, unknown.text

    updated = client.put(
        _draft_path(draft_id),
        json={
            "expected_version": draft["version"],
            "decisions": [
                {
                    "asset_unit_id": facts["stock_unit_id"],
                    "included": False,
                    "exclusion_reason": "整栋自用，不参与考核",
                },
                {
                    "asset_unit_id": facts["takeover_unit_id"],
                    "included": True,
                    "exclusion_reason": None,
                },
            ],
        },
        headers=csrf_headers,
    )
    assert updated.status_code == 200, updated.text
    updated_pending = {
        p["asset_unit_id"] for p in updated.json()["pending"]
    }
    assert updated_pending == {facts["covered_unit_id"]}
    updated_items = {
        item["asset_unit_id"]: item for item in updated.json()["items"]
    }
    assert updated_items[facts["stock_unit_id"]]["included"] is False
    assert updated_items[facts["takeover_unit_id"]]["included"] is True

    stale_put = client.put(
        _draft_path(draft_id),
        json={
            "expected_version": draft["version"],
            "decisions": [
                {"asset_unit_id": facts["stock_unit_id"], "included": True}
            ],
        },
        headers=csrf_headers,
    )
    assert stale_put.status_code == 409, stale_put.text
    assert stale_put.json()["error"]["code"] == "VERSION_CONFLICT"

    preview = client.post(
        f"{_draft_path(draft_id)}/preview", headers=csrf_headers
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()
    assert preview_body["current_version_number"] is None
    assert preview_body["new_included_count"] == 1
    assert preview_body["new_excluded_count"] == 1
    assert preview_body["pending_count"] == 1
    assert preview_body["affected_periods"][0].startswith(str(_YEAR))

    period = f"{_YEAR}-01"
    committed = client.post(
        f"{_draft_path(draft_id)}/commit",
        json={
            "preview_token": preview_body["preview_token"],
            "expected_version": updated.json()["version"],
            "effective_from_period": period,
        },
        headers={
            **csrf_headers,
            "Idempotency-Key": f"scope-commit-{uuid4().hex}",
        },
    )
    assert committed.status_code == 200, committed.text
    assert committed.json()["version_number"] == 1
    assert committed.json()["idempotent"] is False

    overview = client.get(overview_path, params={"operator_party_id": operator_id})
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["scope"]["version_number"] == 1
    assert body["scope"]["status"] == "active"
    assert len(body["items"]) == 2
    assert {p["asset_unit_id"] for p in body["pending"]} == {
        facts["covered_unit_id"]
    }
    assert body["occupancy"]["unit_count"] == 1
    assert body["occupancy"]["rented_unit_count"] == 0


def test_assessment_scope_commit_replay_and_conflicts_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    """Replay, key conflicts, stale tokens and supersession, end to end."""
    client = authenticated_client
    facts = _seed_scope_sources(db_session, getattr(client, "_user_id"))
    operator_id = facts["operator_party_id"]
    overview_path = f"/api/v1/assessment-scopes/{_YEAR}"

    first = client.post(
        f"{overview_path}/drafts",
        json={"operator_party_id": operator_id, "source": "current"},
        headers=csrf_headers,
    )
    assert first.status_code == 200, first.text
    first_draft = first.json()

    first_preview = client.post(
        f"{_draft_path(first_draft['draft_id'])}/preview", headers=csrf_headers
    )
    assert first_preview.status_code == 200, first_preview.text
    key = f"scope-commit-{uuid4().hex}"
    commit_payload = {
        "preview_token": first_preview.json()["preview_token"],
        "expected_version": first_draft["version"],
        "effective_from_period": f"{_YEAR}-01",
    }
    committed = client.post(
        f"{_draft_path(first_draft['draft_id'])}/commit",
        json=commit_payload,
        headers={**csrf_headers, "Idempotency-Key": key},
    )
    assert committed.status_code == 200, committed.text
    assert committed.json()["version_number"] == 1

    replayed = client.post(
        f"{_draft_path(first_draft['draft_id'])}/commit",
        json=commit_payload,
        headers={**csrf_headers, "Idempotency-Key": key},
    )
    assert replayed.status_code == 200, replayed.text
    assert replayed.json()["idempotent"] is True
    assert replayed.json()["version_number"] == 1

    activated_read = client.get(_draft_path(first_draft["draft_id"]))
    assert activated_read.status_code == 409, activated_read.text
    assert (
        activated_read.json()["error"]["code"]
        == "ASSESSMENT_SCOPE_DRAFT_STATE_INVALID"
    )

    second = client.post(
        f"{overview_path}/drafts",
        json={"operator_party_id": operator_id, "source": "current"},
        headers=csrf_headers,
    )
    assert second.status_code == 200, second.text
    second_draft = second.json()
    carried = {
        item["asset_unit_id"]: item for item in second_draft["items"]
    }
    assert carried[facts["stock_unit_id"]]["included"] is True
    assert facts["takeover_unit_id"] not in carried

    second_preview = client.post(
        f"{_draft_path(second_draft['draft_id'])}/preview", headers=csrf_headers
    )
    assert second_preview.status_code == 200, second_preview.text
    second_preview_token = second_preview.json()["preview_token"]

    db_session.execute(
        text("UPDATE asset_units SET version = version + 1 WHERE id = :unit_id"),
        {"unit_id": facts["covered_unit_id"]},
    )
    db_session.commit()

    stale = client.post(
        f"{_draft_path(second_draft['draft_id'])}/commit",
        json={
            "preview_token": second_preview_token,
            "expected_version": second_draft["version"],
            "effective_from_period": f"{_YEAR}-01",
        },
        headers={**csrf_headers, "Idempotency-Key": f"scope-commit-{uuid4().hex}"},
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["error"]["code"] == "PREVIEW_STALE"
    assert stale.json()["error"]["details"]["reason"] == "state_changed"

    mutated = client.put(
        _draft_path(second_draft["draft_id"]),
        json={
            "expected_version": second_draft["version"],
            "decisions": [
                {
                    "asset_unit_id": facts["takeover_unit_id"],
                    "included": True,
                }
            ],
        },
        headers=csrf_headers,
    )
    assert mutated.status_code == 200, mutated.text

    version_mismatch = client.post(
        f"{_draft_path(second_draft['draft_id'])}/commit",
        json={
            "preview_token": second_preview_token,
            "expected_version": mutated.json()["version"],
            "effective_from_period": f"{_YEAR}-01",
        },
        headers={**csrf_headers, "Idempotency-Key": f"scope-commit-{uuid4().hex}"},
    )
    assert version_mismatch.status_code == 409, version_mismatch.text
    assert version_mismatch.json()["error"]["code"] == "VERSION_CONFLICT"

    fresh_preview = client.post(
        f"{_draft_path(second_draft['draft_id'])}/preview", headers=csrf_headers
    )
    assert fresh_preview.status_code == 200, fresh_preview.text
    second_key = f"scope-commit-{uuid4().hex}"
    second_commit = client.post(
        f"{_draft_path(second_draft['draft_id'])}/commit",
        json={
            "preview_token": fresh_preview.json()["preview_token"],
            "expected_version": mutated.json()["version"],
            "effective_from_period": f"{_YEAR}-01",
        },
        headers={**csrf_headers, "Idempotency-Key": second_key},
    )
    assert second_commit.status_code == 200, second_commit.text
    assert second_commit.json()["version_number"] == 2

    overview = client.get(overview_path, params={"operator_party_id": operator_id})
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["scope"]["version_number"] == 2
    included_ids = {
        item["asset_unit_id"]
        for item in body["items"]
        if item["included"]
    }
    assert facts["takeover_unit_id"] in included_ids

    conflict = client.post(
        f"{_draft_path(second_draft['draft_id'])}/commit",
        json={
            "preview_token": fresh_preview.json()["preview_token"],
            "expected_version": mutated.json()["version"],
            "effective_from_period": f"{_YEAR}-02",
        },
        headers={**csrf_headers, "Idempotency-Key": second_key},
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_assessment_scope_requires_authentication_e2e(
    client: TestClient,
) -> None:
    """Anonymous callers cannot read or mutate assessment scopes."""
    anonymous_overview = client.get(
        f"/api/v1/assessment-scopes/{_YEAR}",
        params={"operator_party_id": str(uuid4())},
    )
    assert anonymous_overview.status_code in {401, 403}, anonymous_overview.text

    anonymous_draft = client.post(
        f"/api/v1/assessment-scopes/{_YEAR}/drafts",
        json={"operator_party_id": str(uuid4()), "source": "current"},
    )
    assert anonymous_draft.status_code in {401, 403}, anonymous_draft.text


def test_assessment_scope_operator_party_must_exist_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    """An unknown reporting unit is rejected instead of silently stored."""
    client = authenticated_client
    missing = client.post(
        f"/api/v1/assessment-scopes/{_YEAR}/drafts",
        json={"operator_party_id": str(uuid4()), "source": "current"},
        headers=csrf_headers,
    )
    assert missing.status_code == 404, missing.text


def test_assessment_scope_split_result_inherits_prior_inclusion_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session: Session,
) -> None:
    """A boundary result whose every source was included inherits (V3-T02)."""
    client = authenticated_client
    facts = _seed_scope_sources(db_session, getattr(client, "_user_id"))
    operator_id = facts["operator_party_id"]

    prior_version = AssessmentScopeVersion(
        id=str(uuid4()),
        operator_party_id=operator_id,
        year=_YEAR - 1,
        version_number=1,
        status="active",
        effective_from_period=f"{_YEAR - 1}-01",
        created_by=getattr(client, "_user_id"),
        activated_by=getattr(client, "_user_id"),
        activated_at=datetime.now(UTC).replace(tzinfo=None),
        version=1,
    )
    db_session.add(prior_version)
    db_session.flush()
    db_session.add(
        AssessmentScopeItem(
            scope_version_id=prior_version.id,
            asset_unit_id=facts["stock_unit_id"],
            included=True,
            exclusion_reason=None,
            unit_snapshot={},
        )
    )
    split_result = AssetUnit(
        id=str(uuid4()),
        unit_code=f"AU-SPLIT-{uuid4().hex[:8]}",
        name=f"拆分结果单元-{uuid4().hex[:6]}",
        project_id=db_session.get(AssetUnit, facts["stock_unit_id"]).project_id,
        owner_party_id=operator_id,
        address="考核 E2E 地址",
        usage_type="commercial",
        acquisition_mode="managed",
        is_operating=True,
        land_area=Decimal("0"),
        building_area=Decimal("40"),
        rentable_area=Decimal("30"),
        managed_from=datetime(_YEAR, 7, 1, tzinfo=UTC).date(),
        predecessor_unit_ids=[facts["stock_unit_id"]],
        version=1,
    )
    db_session.add(split_result)
    db_session.commit()

    created = client.post(
        f"/api/v1/assessment-scopes/{_YEAR}/drafts",
        json={"operator_party_id": operator_id, "source": "previous_year"},
        headers=csrf_headers,
    )
    assert created.status_code == 200, created.text
    items = {
        item["asset_unit_id"]: item for item in created.json()["items"]
    }
    assert items[facts["stock_unit_id"]]["included"] is True
    assert items[split_result.id]["included"] is True
    assert split_result.id not in {
        p["asset_unit_id"] for p in created.json()["pending"]
    }


def test_assessment_scope_commit_race_admits_single_winner_e2e(
    require_redis,
    test_database_url,
) -> None:
    """Two concurrent commits of one draft produce exactly one version (V3-T03)."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from sqlalchemy import text as sql_text
    from sqlalchemy.ext.asyncio import (
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.pool import NullPool

    from src.models.auth import User
    from src.models.party import Party, PartyType
    from src.models.project import Project
    from src.schemas.asset_operations import (
        AssessmentScopeCommitRequest,
        CreateAssessmentScopeDraftRequest,
    )
    from src.services.asset_operations.assessment_scope_command_service import (
        assessment_scope_command_service as svc,
    )

    # Mirror src/database.py: async engines speak asyncpg, which unlike
    # psycopg also works on Windows' default ProactorEventLoop.
    async_url = test_database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
    from src.services.asset_operations.errors import (
        AssetOperationsPreviewStaleError,
        AssetOperationsVersionConflictError,
    )
    from src.services.party_scope_resolver import EffectivePartyScope

    today = datetime.now(UTC).astimezone(ZoneInfo("Asia/Shanghai")).date()

    async def seed_and_preview():
        engine = create_async_engine(async_url, poolclass=NullPool)
        try:
            maker = async_sessionmaker(engine, expire_on_commit=False)
            async with maker() as db:
                actor = User(
                    id=str(uuid4()),
                    username=f"race-{uuid4().hex[:10]}",
                    email=f"race-{uuid4().hex[:10]}@example.com",
                    phone=f"13{uuid4().int % 10**9:09d}",
                    full_name="范围并发",
                    password_hash="unused",
                    account_type="service",
                    is_active=True,
                )
                operator = Party(
                    id=str(uuid4()),
                    party_type=PartyType.LEGAL_ENTITY,
                    name=f"并发主体-{uuid4().hex[:8]}",
                    code=f"LE-{uuid4().int % 1_000_000:06d}",
                    status="active",
                    review_status="approved",
                )
                db.add_all([actor, operator])
                await db.flush()
                project = Project(
                    id=str(uuid4()),
                    project_code=f"PRJ-RACE-{uuid4().hex[:8]}",
                    project_name="范围并发",
                    manager_party_id=operator.id,
                    status="active",
                )
                db.add(project)
                await db.flush()
                unit = AssetUnit(
                    id=str(uuid4()),
                    unit_code=f"AU-RACE-{uuid4().hex[:8]}",
                    name="并发单元",
                    project_id=project.id,
                    owner_party_id=operator.id,
                    address="x",
                    usage_type="commercial",
                    acquisition_mode="managed",
                    is_operating=True,
                    land_area=Decimal("0"),
                    building_area=Decimal("10"),
                    rentable_area=Decimal("10"),
                    managed_from=today - timedelta(days=400),
                    predecessor_unit_ids=[],
                    version=1,
                )
                db.add(unit)
                await db.commit()
                scope = EffectivePartyScope(
                    user_id=actor.id, source="role", scope_mode="unrestricted"
                )
                draft = await svc.create_draft(
                    db,
                    year=_YEAR,
                    request=CreateAssessmentScopeDraftRequest(
                        operator_party_id=operator.id, source="current"
                    ),
                    actor_id=actor.id,
                    scope=scope,
                )
                fresh = await svc.preview(
                    db, draft_id=draft.draft_id, actor_id=actor.id, scope=scope
                )
                return {
                    "actor_id": actor.id,
                    "operator_id": operator.id,
                    "draft_id": draft.draft_id,
                    "expected_version": draft.version,
                    "preview_token": fresh.preview_token,
                }
        finally:
            await engine.dispose()

    facts = asyncio.run(seed_and_preview())
    lock_key = f"assessment_scope:{facts['operator_id']}:{_YEAR}"
    started = Event()

    def attempt(key: str):
        started.set()

        async def run():
            engine = create_async_engine(async_url, poolclass=NullPool)
            try:
                maker = async_sessionmaker(engine, expire_on_commit=False)
                async with maker() as db:
                    scope = EffectivePartyScope(
                        user_id=facts["actor_id"],
                        source="role",
                        scope_mode="unrestricted",
                    )
                    try:
                        return await svc.commit(
                            db,
                            draft_id=facts["draft_id"],
                            request=AssessmentScopeCommitRequest(
                                preview_token=facts["preview_token"],
                                expected_version=facts["expected_version"],
                                effective_from_period=f"{_YEAR}-01",
                            ),
                            actor_id=facts["actor_id"],
                            scope=scope,
                            idempotency_key=key,
                        )
                    except Exception as error:  # noqa: BLE001 - 竞争双方都回收
                        await db.rollback()
                        return error
            finally:
                await engine.dispose()

        return asyncio.run(run())

    keys = [f"race-{uuid4().hex}", f"race-{uuid4().hex}"]
    blocker_ready = Event()

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

    outcomes = [
        result
        if isinstance(result, BaseBusinessError)
        else ("ok", result)
        for result in results
    ]
    successes = [r for r in outcomes if isinstance(r, tuple)]
    failures = [r for r in outcomes if isinstance(r, BaseBusinessError)]
    assert len(successes) == 1, outcomes
    assert len(failures) == 1, outcomes
    failure = failures[0]
    assert isinstance(
        failure, AssetOperationsPreviewStaleError | AssetOperationsVersionConflictError
    ), outcomes
    assert successes[0][1].version_number == 1, outcomes

    async def verify():
        engine = create_async_engine(async_url, poolclass=NullPool)
        try:
            maker = async_sessionmaker(engine)
            async with maker() as db:
                active = await db.execute(
                    sql_text(
                        "SELECT count(*) FROM assessment_scope_versions "
                        "WHERE operator_party_id = :p AND year = :y "
                        "AND status = 'active'"
                    ),
                    {"p": facts["operator_id"], "y": _YEAR},
                )
                receipts = await db.execute(
                    sql_text(
                        "SELECT count(*) FROM asset_contract_write_receipts "
                        "WHERE actor_id = :a AND command_kind = "
                        "'commit_assessment_scope' AND idempotency_key = ANY(:ks)"
                    ),
                    {"a": facts["actor_id"], "ks": keys},
                )
                return active.scalar_one(), receipts.scalar_one()
        finally:
            await engine.dispose()

    active_count, receipt_count = asyncio.run(verify())
    assert active_count == 1
    assert receipt_count == 1


def test_assessment_scope_readonly_user_cannot_write_e2e(
    client,
    db_session,
) -> None:
    """A user with only asset_ops:read cannot save, submit or withdraw (T10)."""
    from src.models.auth import AccountType, User
    from src.models.rbac import (
        Permission,
        Role,
        UserRoleAssignment,
        role_permissions,
    )
    from src.services.core.password_service import PasswordService

    db = db_session
    suffix = uuid4().hex[:10]

    read_permission = (
        db.query(Permission)
        .filter(Permission.resource == "asset_ops", Permission.action == "read")
        .first()
    )
    assert read_permission is not None
    role = Role(
        name=f"scope-readonly-{suffix}",
        display_name="考核只读",
        is_system_role=False,
        is_active=True,
    )
    db.add(role)
    db.flush()
    db.execute(
        role_permissions.insert().values(
            role_id=role.id, permission_id=read_permission.id
        )
    )
    from tests.e2e.conftest import ensure_test_organization

    organization_id = ensure_test_organization(db).id
    password_service = PasswordService()
    user = User(
        id=str(uuid4()),
        username=f"scope-ro-{suffix}",
        email=f"scope-ro-{suffix}@example.com",
        phone=f"13{uuid4().int % 10**9:09d}",
        full_name="考核只读用户",
        password_hash=password_service.get_password_hash("Ro!Only-2026"),
        is_active=True,
        account_type=AccountType.HUMAN,
        organization_id=organization_id,
    )
    db.add(user)
    db.flush()
    db.add(UserRoleAssignment(user_id=user.id, role_id=role.id, assigned_by="e2e-fixture"))
    db.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": f"scope-ro-{suffix}", "password": "Ro!Only-2026"},
    )
    assert login.status_code == 200, login.text
    for cookie_name in ("auth_token", "csrf_token"):
        value = login.cookies.get(cookie_name)
        if value is not None:
            client.cookies.set(cookie_name, value)
    csrf_token = login.cookies.get("csrf_token")
    read_headers = (
        {"X-CSRF-Token": csrf_token} if csrf_token is not None else {}
    )

    # The read-only user has no party binding: reads and writes both fail
    # closed with 403 PARTY_SCOPE_MISSING before any data is exposed.
    overview = client.get(
        f"/api/v1/assessment-scopes/{_YEAR}",
        params={"operator_party_id": str(uuid4())},
    )
    assert overview.status_code == 403, overview.text
    assert overview.json()["error"]["code"] == "PARTY_SCOPE_MISSING"

    denied_cases = [
        (
            "post",
            f"/api/v1/assessment-scopes/{_YEAR}/drafts",
            {"operator_party_id": str(uuid4()), "source": "current"},
        ),
        (
            "put",
            f"/api/v1/occupancy-reports/{datetime.now(UTC).astimezone(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m')}/draft-note",
            {"operator_party_id": str(uuid4()), "change_note": "只读用户"},
        ),
    ]
    for method, path, payload in denied_cases:
        response = getattr(client, method)(path, json=payload, headers=read_headers)
        assert response.status_code == 403, (method, path, response.text)
        assert (
            response.json()["error"]["code"] == "ASSET_OPS_PERMISSION_DENIED"
        ), (method, path)

    # Snapshot read of a non-existent report stays authorised-but-missing:
    # the read permission covers it, the write endpoints stay forbidden.
