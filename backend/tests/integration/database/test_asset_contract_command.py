"""PostgreSQL integration coverage for signed-contract confirmation writes."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.database import get_async_database_url
from src.models.asset_contract import (
    AssetContractWriteReceipt,
    ContractLifecycleEvent,
    ContractRentSchedule,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from src.models.asset_unit import AssetUnit
from src.models.attachment import Attachment
from src.models.auth import AccountType, User
from src.models.business_change_event import BusinessChangeEvent
from src.models.party import Party, PartyReviewStatus, PartyType
from src.models.project import Project
from src.schemas.asset_operations import (
    ContractLifecycleEventResponse,
    TerminalContractCreate,
    TerminalContractTerminationProposal,
    UpstreamContractCreate,
    UpstreamContractResponse,
    UpstreamContractUpdate,
)
from src.services.asset_operations.contract_command_service import (
    AssetContractCommandService,
)
from src.services.asset_operations.contract_lifecycle_command_service import (
    ContractLifecycleCommandService,
)
from src.services.asset_operations.errors import (
    AssetUnitPeriodOverlapError,
    ScanDocumentAlreadyBoundError,
)
from src.services.party_scope_resolver import EffectivePartyScope
from tests.fixtures.fake_credentials import fake_bcrypt_hash

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.asyncio]

ACTOR_ID = "asset-contract-integration-actor"
OWNER_ID = "asset-contract-integration-owner"
TENANT_ID = "asset-contract-integration-tenant"
PROJECT_ID = "asset-contract-integration-project"
UNIT_ID = "asset-contract-integration-unit"
UPSTREAM_SCAN_ID = "asset-contract-integration-upstream-scan"
TERMINAL_SCAN_ID = "asset-contract-integration-terminal-scan"


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(get_async_database_url(), poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def reset_facts() -> None:
        async with factory() as session:
            await session.execute(
                delete(BusinessChangeEvent).where(
                    BusinessChangeEvent.actor_id == ACTOR_ID
                )
            )
            await session.execute(
                delete(AssetContractWriteReceipt).where(
                    AssetContractWriteReceipt.actor_id == ACTOR_ID
                )
            )
            terminal_ids = select(TerminalContract.id).where(
                TerminalContract.contract_number.like("TM-ASSET-CONTRACT-INT%")
            )
            upstream_ids = select(UpstreamContract.id).where(
                UpstreamContract.contract_number == "UP-ASSET-CONTRACT-INT"
            )
            await session.execute(
                delete(ContractLifecycleEvent).where(
                    ContractLifecycleEvent.contract_kind == "terminal",
                    ContractLifecycleEvent.contract_id.in_(terminal_ids),
                )
            )
            await session.execute(
                delete(TerminalContractAssetUnit).where(
                    TerminalContractAssetUnit.terminal_contract_id.in_(terminal_ids)
                )
            )
            await session.execute(
                delete(UpstreamContractAssetUnit).where(
                    UpstreamContractAssetUnit.upstream_contract_id.in_(upstream_ids)
                )
            )
            await session.execute(
                delete(ContractRentSchedule).where(
                    (
                        (ContractRentSchedule.contract_kind == "terminal")
                        & ContractRentSchedule.contract_id.in_(terminal_ids)
                    )
                    | (
                        (ContractRentSchedule.contract_kind == "upstream")
                        & ContractRentSchedule.contract_id.in_(upstream_ids)
                    )
                )
            )
            await session.execute(
                delete(TerminalContract).where(TerminalContract.id.in_(terminal_ids))
            )
            await session.execute(
                delete(UpstreamContract).where(UpstreamContract.id.in_(upstream_ids))
            )
            await session.execute(delete(AssetUnit).where(AssetUnit.id == UNIT_ID))
            await session.execute(
                delete(Attachment).where(
                    Attachment.id.in_((UPSTREAM_SCAN_ID, TERMINAL_SCAN_ID))
                )
            )
            await session.execute(delete(Project).where(Project.id == PROJECT_ID))
            await session.execute(
                delete(Party).where(Party.id.in_((OWNER_ID, TENANT_ID)))
            )
            await session.execute(delete(User).where(User.id == ACTOR_ID))
            await session.commit()

    await reset_facts()
    try:
        yield factory
    finally:
        await reset_facts()
        await engine.dispose()


async def _seed(factory: async_sessionmaker[AsyncSession]) -> EffectivePartyScope:
    async with factory() as session:
        session.add_all(
            [
                User(
                    id=ACTOR_ID,
                    username="asset_contract_integration_actor",
                    email="asset-contract-integration@example.test",
                    phone="13900009002",
                    full_name="合同集成测试操作者",
                    password_hash=fake_bcrypt_hash(),
                    account_type=AccountType.SYSTEM,
                ),
                Party(
                    id=OWNER_ID,
                    party_type=PartyType.LEGAL_ENTITY,
                    name="合同集成测试产权方",
                    code="LE-990002",
                    status="active",
                    review_status=PartyReviewStatus.APPROVED,
                ),
                Party(
                    id=TENANT_ID,
                    party_type=PartyType.LEGAL_ENTITY,
                    name="合同集成测试租户",
                    code="LE-990003",
                    status="active",
                    review_status=PartyReviewStatus.APPROVED,
                ),
            ]
        )
        await session.flush()
        session.add(
            Project(
                id=PROJECT_ID,
                project_name="合同集成测试项目",
                project_code="PRJ-ASSET-CONTRACT-INTEGRATION",
                status="active",
                manager_party_id=OWNER_ID,
            )
        )
        await session.flush()
        session.add_all(
            [
                AssetUnit(
                    id=UNIT_ID,
                    unit_code="AU-CONTRACT-INT",
                    name="合同集成测试单元",
                    project_id=PROJECT_ID,
                    owner_party_id=OWNER_ID,
                    address="集成测试地址 2 号",
                    usage_type="commercial",
                    acquisition_mode="leased",
                    is_operating=True,
                    land_area=Decimal("0"),
                    building_area=Decimal("100"),
                    rentable_area=Decimal("80"),
                    managed_from=date(2026, 1, 1),
                    managed_to=date(2027, 12, 31),
                    predecessor_unit_ids=[],
                    version=1,
                ),
                Attachment(
                    id=UPSTREAM_SCAN_ID,
                    owner_type="contract",
                    owner_id="contract-intake-upstream",
                    file_name="upstream.pdf",
                    file_type="pdf",
                    file_size=1,
                    storage_key="asset-contract/integration/upstream.pdf",
                    created_by=ACTOR_ID,
                ),
                Attachment(
                    id=TERMINAL_SCAN_ID,
                    owner_type="contract",
                    owner_id="contract-intake-terminal",
                    file_name="terminal.pdf",
                    file_type="pdf",
                    file_size=1,
                    storage_key="asset-contract/integration/terminal.pdf",
                    created_by=ACTOR_ID,
                ),
            ]
        )
        await session.commit()
    return EffectivePartyScope(
        user_id=ACTOR_ID,
        source="explicit",
        scope_mode="owner",
        owner_party_ids=[OWNER_ID],
    )


async def test_confirmed_contracts_persist_atomically_warn_and_replay(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await _seed(session_factory)
    service = AssetContractCommandService(
        clock=lambda: datetime(2026, 10, 24, 4, 0, tzinfo=UTC),
        business_today=lambda: date(2026, 10, 24),
    )
    upstream_request = UpstreamContractCreate.model_validate(
        {
            "contract_number": "UP-ASSET-CONTRACT-INT",
            "contract_type": "lease",
            "name": "合同集成测试上游合同",
            "owner_party_id": OWNER_ID,
            "operator_party_id": OWNER_ID,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "payment_cycle": "monthly",
            "payment_day": 15,
            "scan_document_id": UPSTREAM_SCAN_ID,
            "asset_unit_ids": [UNIT_ID],
            "rent_schedules": [],
        }
    )

    async def create_upstream_once() -> UpstreamContractResponse:
        async with session_factory() as session:
            return await service.create_upstream(
                session,
                request=upstream_request,
                actor_id=ACTOR_ID,
                scope=scope,
                idempotency_key="asset-contract-upstream-001",
                attachment_owner_id="contract-intake-upstream",
            )

    first, second = await asyncio.gather(create_upstream_once(), create_upstream_once())
    upstream = first if not first.idempotent else second
    replayed = second if not first.idempotent else first

    assert {first.idempotent, second.idempotent} == {False, True}
    assert replayed.id == upstream.id

    reused_scan_request = upstream_request.model_copy(
        update={"contract_number": "UP-ASSET-CONTRACT-INT-REUSED-SCAN"}
    )
    async with session_factory() as session:
        with pytest.raises(ScanDocumentAlreadyBoundError):
            await service.create_upstream(
                session,
                request=reused_scan_request,
                actor_id=ACTOR_ID,
                scope=scope,
                idempotency_key="asset-contract-upstream-reused-scan",
                attachment_owner_id="contract-intake-upstream",
            )

    terminal_request = TerminalContractCreate.model_validate(
        {
            "contract_number": "TM-ASSET-CONTRACT-INT-001",
            "contract_mode": "sublease",
            "tenant_party_id": TENANT_ID,
            "lessor_party_id": OWNER_ID,
            "upstream_contract_id": upstream.id,
            "start_date": "2026-02-01",
            "end_date": "2027-03-31",
            "deposit_months": "2",
            "deposit_amount": "2000",
            "rent_collector": "operator",
            "scan_document_id": TERMINAL_SCAN_ID,
            "asset_unit_ids": [UNIT_ID],
            "rent_schedules": [],
        }
    )
    async with session_factory() as session:
        terminal = await service.create_terminal(
            session,
            request=terminal_request,
            actor_id=ACTOR_ID,
            scope=scope,
            idempotency_key="asset-contract-terminal-001",
            attachment_owner_id="contract-intake-terminal",
        )

    assert [warning.code for warning in terminal.warnings] == [
        "TERMINAL_TERM_EXCEEDS_UPSTREAM"
    ]

    overlapping = terminal_request.model_copy(
        update={"contract_number": "TM-ASSET-CONTRACT-INT-002"}
    )
    async with session_factory() as session:
        with pytest.raises(AssetUnitPeriodOverlapError):
            await service.create_terminal(
                session,
                request=overlapping,
                actor_id=ACTOR_ID,
                scope=scope,
                idempotency_key="asset-contract-terminal-002",
                attachment_owner_id="contract-intake-terminal",
            )
        await session.rollback()

    lifecycle_service = ContractLifecycleCommandService(
        clock=lambda: datetime(2026, 10, 25, 1, 0, tzinfo=UTC)
    )
    termination_proposal = TerminalContractTerminationProposal.model_validate(
        {
            "effective_date": "2026-06-30",
            "termination_type": "early",
            "handover_status": "pending",
            "deposit_settlement_status": "pending",
            "reason": "集成测试提前退租",
        }
    )

    async def terminate_once() -> ContractLifecycleEventResponse:
        async with session_factory() as session:
            return await lifecycle_service.terminate_terminal(
                session,
                contract_id=terminal.id,
                proposal=termination_proposal,
                actor_id=ACTOR_ID,
                scope=scope,
                idempotency_key="asset-contract-terminal-termination-001",
            )

    first_termination, replayed_termination = await asyncio.gather(
        terminate_once(), terminate_once()
    )
    assert {first_termination.idempotent, replayed_termination.idempotent} == {
        False,
        True,
    }
    assert first_termination.id == replayed_termination.id

    async with session_factory() as session:
        upstream_count = await session.scalar(
            select(func.count())
            .select_from(UpstreamContract)
            .where(UpstreamContract.contract_number.like("UP-ASSET-CONTRACT-INT%"))
        )
        terminal_count = await session.scalar(
            select(func.count())
            .select_from(TerminalContract)
            .where(TerminalContract.contract_number.like("TM-ASSET-CONTRACT-INT%"))
        )
        receipt_count = await session.scalar(
            select(func.count())
            .select_from(AssetContractWriteReceipt)
            .where(AssetContractWriteReceipt.actor_id == ACTOR_ID)
        )
        upstream_coverage_count = await session.scalar(
            select(func.count())
            .select_from(UpstreamContractAssetUnit)
            .where(UpstreamContractAssetUnit.upstream_contract_id == upstream.id)
        )
        terminal_coverage_count = await session.scalar(
            select(func.count())
            .select_from(TerminalContractAssetUnit)
            .where(TerminalContractAssetUnit.terminal_contract_id == terminal.id)
        )
        upstream_scan = await session.get(Attachment, UPSTREAM_SCAN_ID)
        terminal_scan = await session.get(Attachment, TERMINAL_SCAN_ID)
        lifecycle_event_count = await session.scalar(
            select(func.count())
            .select_from(ContractLifecycleEvent)
            .where(
                ContractLifecycleEvent.contract_id == terminal.id,
                ContractLifecycleEvent.event_type == "terminated",
            )
        )

    assert upstream_count == 1
    assert terminal_count == 1
    assert receipt_count == 2
    assert upstream_coverage_count == 1
    assert terminal_coverage_count == 1
    assert upstream_scan is not None and upstream_scan.owner_id == upstream.id
    assert terminal_scan is not None and terminal_scan.owner_id == terminal.id
    assert lifecycle_event_count == 1

    from src.services.asset_operations.business_change_service import (
        BusinessChangeService,
    )

    async with session_factory() as session:
        changes, total = await BusinessChangeService().list_events(session, scope=scope)
        assert total == 3  # two confirmations + termination, despite concurrent replay
        assert {change.action for change in changes} == {"confirmed", "terminated"}
        assert all(change.actor_id == ACTOR_ID for change in changes)
        outside = EffectivePartyScope(
            user_id=ACTOR_ID,
            source="explicit",
            scope_mode="owner",
            owner_party_ids=["outside-owner"],
        )
        assert await BusinessChangeService().list_events(session, scope=outside) == (
            [],
            0,
        )

    async with session_factory() as session:
        updated = await service.update_upstream(
            session,
            contract_id=upstream.id,
            request=UpstreamContractUpdate(
                expected_version=upstream.version, name="修改后的合同名称"
            ),
            actor_id=ACTOR_ID,
            scope=scope,
        )
    async with session_factory() as session:
        change = await session.scalar(
            select(BusinessChangeEvent).where(
                BusinessChangeEvent.target_id == upstream.id,
                BusinessChangeEvent.action == "updated",
            )
        )
        assert change is not None
        assert change.before["name"] == upstream_request.name
        assert change.after["name"] == updated.name
        assert change.before["version"] == upstream.version
        assert change.after["version"] == updated.version
        assert updated.version == upstream.version + 1


async def test_audit_and_contract_rollback_together(session_factory, monkeypatch):
    scope = await _seed(session_factory)
    service = AssetContractCommandService()
    request = UpstreamContractCreate.model_validate(
        {
            "contract_number": "UP-ASSET-CONTRACT-INT",
            "contract_type": "lease",
            "name": "事务回滚",
            "owner_party_id": OWNER_ID,
            "operator_party_id": OWNER_ID,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "payment_cycle": "monthly",
            "payment_day": 15,
            "scan_document_id": UPSTREAM_SCAN_ID,
            "asset_unit_ids": [UNIT_ID],
        }
    )

    async def fail_after_audit(db, **kwargs):
        await db.flush()  # persist pending business event inside the doomed transaction
        raise RuntimeError("receipt write failed")

    monkeypatch.setattr(service.repository, "add_write_receipt", fail_after_audit)
    async with session_factory() as session:
        with pytest.raises(RuntimeError, match="receipt write failed"):
            await service.create_upstream(
                session,
                request=request,
                actor_id=ACTOR_ID,
                scope=scope,
                idempotency_key="audit-rollback",
                attachment_owner_id="contract-intake-upstream",
            )
    async with session_factory() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(BusinessChangeEvent)
                .where(BusinessChangeEvent.actor_id == ACTOR_ID)
            )
            == 0
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(UpstreamContract)
                .where(UpstreamContract.contract_number == request.contract_number)
            )
            == 0
        )
