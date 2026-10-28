"""PostgreSQL integration coverage for contract lifecycle commands."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.database import get_async_database_url
from src.models.asset_contract import (
    AssetContractWriteReceipt,
    ContractLifecycleEvent,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from src.models.asset_ledger import RentLedgerEntry, RentPaymentRecord
from src.models.asset_unit import AssetUnit
from src.models.attachment import Attachment
from src.models.auth import AccountType, User
from src.models.business_change_event import BusinessChangeEvent
from src.models.party import Party, PartyReviewStatus, PartyType
from src.models.project import Project
from src.schemas.asset_operations import (
    AssetUnitUpdate,
    AssetUnitVacancyNoteUpdate,
    TerminalContractRenewalRequest,
    TerminalContractTerminationCommitRequest,
    TerminalContractTerminationProposal,
    TerminalContractTerminationReversalProposal,
    TerminalContractUpdate,
    UpstreamContractExitCommitRequest,
    UpstreamContractExitProposal,
    UpstreamContractExitReversalProposal,
    UpstreamContractRenewalRequest,
)
from src.services.asset_operations.contract_command_service import (
    AssetContractCommandService,
)
from src.services.asset_operations.contract_lifecycle_command_service import (
    ContractLifecycleCommandService,
)
from src.services.asset_operations.errors import (
    ActiveTerminalContractsBlockExitError,
    AssetContractCoverageInvalidError,
    AssetOperationsPreviewStaleError,
    AssetOperationsVersionConflictError,
    AssetUnitAreaInvalidError,
    AssetUnitPeriodOverlapError,
    ContractAlreadyRenewedError,
    TerminalContractAlreadyTerminatedError,
    TerminationReversalBlockedError,
    UpstreamExitReversalTargetInvalidError,
)
from src.services.party_scope_resolver import EffectivePartyScope
from tests.fixtures.fake_credentials import fake_bcrypt_hash

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.asyncio]

ACTOR_ID = "lifecycle-int-actor"
OWNER_ID = "lifecycle-int-owner"
TENANT_ID = "lifecycle-int-tenant"
PROJECT_ID = "lifecycle-int-project"
UNIT_ID = "lifecycle-int-unit"
SCAN_ID = "lifecycle-int-scan"
CONTRACT_ID = "lifecycle-int-terminal"
SUCCESSOR_ID = "lifecycle-int-terminal-successor"
OVERLAP_ID = "lifecycle-int-terminal-overlap"
UPSTREAM_ID = "lifecycle-int-upstream"
RENEWAL_UPSTREAM_SCAN_ID = "lifecycle-int-renewal-upstream-scan"
RENEWAL_TERMINAL_SCAN_ID = "lifecycle-int-renewal-terminal-scan"
CONTRACT_NUMBER = "TM-LIFECYCLE-INT-01"

SCOPE = EffectivePartyScope(
    user_id=ACTOR_ID,
    source="explicit",
    scope_mode="owner",
    owner_party_ids=[OWNER_ID],
)


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
            terminal_ids = select(TerminalContract.id).where(
                TerminalContract.contract_number.like("TM-LIFECYCLE-INT%")
            )
            upstream_ids = select(UpstreamContract.id).where(
                UpstreamContract.contract_number.like("UP-LIFECYCLE-INT%")
            )
            await session.execute(
                delete(AssetContractWriteReceipt).where(
                    AssetContractWriteReceipt.actor_id == ACTOR_ID
                )
            )
            record_ids = select(RentPaymentRecord.id).where(
                RentPaymentRecord.created_by == ACTOR_ID
            )
            await session.execute(
                delete(RentPaymentRecord).where(
                    RentPaymentRecord.reverses_record_id.in_(record_ids)
                )
            )
            await session.execute(
                delete(RentPaymentRecord).where(
                    RentPaymentRecord.created_by == ACTOR_ID
                )
            )
            await session.execute(
                delete(RentLedgerEntry).where(
                    RentLedgerEntry.contract_id.in_(terminal_ids.union(upstream_ids))
                )
            )
            await session.execute(
                delete(ContractLifecycleEvent).where(
                    ContractLifecycleEvent.contract_id.in_(
                        terminal_ids.union(upstream_ids)
                    )
                )
            )
            await session.execute(
                delete(TerminalContractAssetUnit).where(
                    TerminalContractAssetUnit.terminal_contract_id.in_(terminal_ids)
                )
            )
            await session.execute(
                delete(TerminalContract).where(TerminalContract.id.in_(terminal_ids))
            )
            await session.execute(
                delete(UpstreamContractAssetUnit).where(
                    UpstreamContractAssetUnit.upstream_contract_id.in_(upstream_ids)
                )
            )
            await session.execute(
                delete(UpstreamContract).where(UpstreamContract.id.in_(upstream_ids))
            )
            await session.execute(delete(AssetUnit).where(AssetUnit.id == UNIT_ID))
            await session.execute(
                delete(Attachment).where(
                    Attachment.id.in_(
                        (
                            SCAN_ID,
                            RENEWAL_UPSTREAM_SCAN_ID,
                            RENEWAL_TERMINAL_SCAN_ID,
                        )
                    )
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


async def _seed(factory: async_sessionmaker[AsyncSession]) -> None:
    async with factory() as session:
        session.add_all(
            [
                User(
                    id=ACTOR_ID,
                    username="lifecycle_integration_actor",
                    email="lifecycle-integration@example.test",
                    phone="13900009003",
                    full_name="终止集成测试操作者",
                    password_hash=fake_bcrypt_hash(),
                    account_type=AccountType.SYSTEM,
                ),
                Party(
                    id=OWNER_ID,
                    party_type=PartyType.LEGAL_ENTITY,
                    name="终止集成测试产权方",
                    code="LE-990004",
                    status="active",
                    review_status=PartyReviewStatus.APPROVED,
                ),
                Party(
                    id=TENANT_ID,
                    party_type=PartyType.LEGAL_ENTITY,
                    name="终止集成测试租户",
                    code="LE-990005",
                    status="active",
                    review_status=PartyReviewStatus.APPROVED,
                ),
            ]
        )
        await session.flush()
        session.add(
            Project(
                id=PROJECT_ID,
                project_name="终止集成测试项目",
                project_code="PRJ-LIFECYCLE-INTEGRATION",
                status="active",
                manager_party_id=OWNER_ID,
            )
        )
        await session.flush()
        session.add_all(
            [
                AssetUnit(
                    id=UNIT_ID,
                    unit_code="AU-LIFECYCLE-INT",
                    name="终止集成测试单元",
                    project_id=PROJECT_ID,
                    owner_party_id=OWNER_ID,
                    address="终止集成测试地址 3 号",
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
                    id=SCAN_ID,
                    owner_type="contract",
                    owner_id="lifecycle-intake-terminal",
                    file_name="terminal.pdf",
                    file_type="pdf",
                    file_size=1,
                    storage_key="lifecycle/integration/terminal.pdf",
                    created_by=ACTOR_ID,
                ),
            ]
        )
        await session.flush()
        session.add(
            TerminalContract(  # type: ignore[call-arg]
                id=CONTRACT_ID,
                contract_number=CONTRACT_NUMBER,
                contract_mode="sublease",
                tenant_party_id=TENANT_ID,
                lessor_party_id=OWNER_ID,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                deposit_amount=Decimal("20000"),
                rent_collector="operator",
                scan_document_id=SCAN_ID,
            )
        )
        await session.flush()
        session.add(
            TerminalContractAssetUnit(  # type: ignore[call-arg]
                terminal_contract_id=CONTRACT_ID,
                asset_unit_id=UNIT_ID,
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
            )
        )
        await session.commit()


def _proposal() -> TerminalContractTerminationProposal:
    return TerminalContractTerminationProposal.model_validate(
        {
            "effective_date": "2026-06-30",
            "termination_type": "early",
            "handover_status": "pending",
            "deposit_settlement_status": "pending",
            "reason": "集成测试提前退租",
        }
    )


def _service() -> ContractLifecycleCommandService:
    return ContractLifecycleCommandService(
        clock=lambda: datetime(2026, 10, 25, 1, 0, tzinfo=UTC)
    )


async def test_termination_closes_coverage_and_allows_successor(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed(session_factory)
    service = _service()

    async with session_factory() as session:
        preview = await service.preview_terminal_termination(
            session,
            contract_id=CONTRACT_ID,
            proposal=_proposal(),
            actor_id=ACTOR_ID,
            scope=SCOPE,
        )
    assert preview.contract_version == 1
    assert preview.last_valid_day == date(2026, 6, 29)
    assert len(preview.coverage_impact) == 1
    assert preview.coverage_impact[0].new_effective_to == date(2026, 6, 29)
    assert list(preview.warnings) == ["deposit_unsettled", "RENT_SCHEDULE_GAP"]

    request = TerminalContractTerminationCommitRequest.model_validate(
        {"preview_token": preview.preview_token, "expected_version": 1}
    )
    async with session_factory() as session:
        committed = await service.commit_terminal_termination(
            session,
            contract_id=CONTRACT_ID,
            request=request,
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-termination-001",
        )
    assert committed.idempotent is False

    async with session_factory() as session:
        replayed = await service.commit_terminal_termination(
            session,
            contract_id=CONTRACT_ID,
            request=request,
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-termination-001",
        )
    assert replayed.idempotent is True
    assert replayed.id == committed.id

    async with session_factory() as session:
        with pytest.raises(TerminalContractAlreadyTerminatedError):
            await service.preview_terminal_termination(
                session,
                contract_id=CONTRACT_ID,
                proposal=_proposal(),
                actor_id=ACTOR_ID,
                scope=SCOPE,
            )
        await session.rollback()

    async with session_factory() as session:
        coverage = await session.get(TerminalContractAssetUnit, (CONTRACT_ID, UNIT_ID))
        assert coverage is not None
        assert coverage.effective_to == date(2026, 6, 29)
        contract = await session.get(TerminalContract, CONTRACT_ID)
        assert contract is not None
        assert contract.version == 1
        event_count = await session.scalar(
            select(ContractLifecycleEvent.id).where(
                ContractLifecycleEvent.contract_id == CONTRACT_ID,
                ContractLifecycleEvent.event_type == "terminated",
            )
        )
        assert event_count is not None

    async with session_factory() as session:
        session.add(
            TerminalContract(  # type: ignore[call-arg]
                id=SUCCESSOR_ID,
                contract_number="TM-LIFECYCLE-INT-02",
                contract_mode="direct_lease",
                tenant_party_id=TENANT_ID,
                lessor_party_id=OWNER_ID,
                start_date=date(2026, 6, 30),
                end_date=date(2027, 6, 29),
                deposit_amount=Decimal("0"),
                rent_collector="owner",
                scan_document_id=SCAN_ID,
            )
        )
        await session.flush()
        session.add(
            TerminalContractAssetUnit(  # type: ignore[call-arg]
                terminal_contract_id=SUCCESSOR_ID,
                asset_unit_id=UNIT_ID,
                effective_from=date(2026, 6, 30),
                effective_to=date(2027, 6, 29),
            )
        )
        await session.commit()

    async with session_factory() as session:
        session.add(
            TerminalContract(  # type: ignore[call-arg]
                id=OVERLAP_ID,
                contract_number="TM-LIFECYCLE-INT-03",
                contract_mode="direct_lease",
                tenant_party_id=TENANT_ID,
                lessor_party_id=OWNER_ID,
                start_date=date(2026, 6, 29),
                end_date=date(2027, 6, 29),
                deposit_amount=Decimal("0"),
                rent_collector="owner",
                scan_document_id=SCAN_ID,
            )
        )
        await session.flush()
        session.add(
            TerminalContractAssetUnit(  # type: ignore[call-arg]
                terminal_contract_id=OVERLAP_ID,
                asset_unit_id=UNIT_ID,
                effective_from=date(2026, 6, 29),
                effective_to=date(2027, 6, 29),
            )
        )
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


async def test_commit_rejects_preview_when_state_changed(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed(session_factory)
    service = _service()

    async with session_factory() as session:
        preview = await service.preview_terminal_termination(
            session,
            contract_id=CONTRACT_ID,
            proposal=_proposal(),
            actor_id=ACTOR_ID,
            scope=SCOPE,
        )
    async with session_factory() as session:
        await service.terminate_terminal(
            session,
            contract_id=CONTRACT_ID,
            proposal=_proposal(),
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-termination-direct-001",
        )

    request = TerminalContractTerminationCommitRequest.model_validate(
        {"preview_token": preview.preview_token, "expected_version": 1}
    )
    async with session_factory() as session:
        with pytest.raises(AssetOperationsPreviewStaleError) as error:
            await service.commit_terminal_termination(
                session,
                contract_id=CONTRACT_ID,
                request=request,
                actor_id=ACTOR_ID,
                scope=SCOPE,
                idempotency_key="lifecycle-termination-002",
            )
    assert error.value.details["reason"] == "state_changed"

    async with session_factory() as session:
        rows = await session.scalars(
            select(ContractLifecycleEvent).where(
                ContractLifecycleEvent.contract_id == CONTRACT_ID,
                ContractLifecycleEvent.event_type == "terminated",
            )
        )
        assert len(list(rows)) == 1


async def test_termination_reversal_restores_coverage_and_blocks_on_successor(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed(session_factory)
    service = _service()

    async with session_factory() as session:
        terminated = await service.terminate_terminal(
            session,
            contract_id=CONTRACT_ID,
            proposal=_proposal(),
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-termination-reverse-001",
        )
    async with session_factory() as session:
        coverage = await session.get(TerminalContractAssetUnit, (CONTRACT_ID, UNIT_ID))
        assert coverage is not None
        assert coverage.effective_to == date(2026, 6, 29)

    reversal_proposal = TerminalContractTerminationReversalProposal.model_validate(
        {
            "target_event_id": terminated.id,
            "effective_date": "2026-07-01",
            "reason": "终止日期录入错误",
        }
    )
    async with session_factory() as session:
        reversal = await service.reverse_terminal_termination(
            session,
            contract_id=CONTRACT_ID,
            proposal=reversal_proposal,
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-reversal-001",
        )
        replayed = await service.reverse_terminal_termination(
            session,
            contract_id=CONTRACT_ID,
            proposal=reversal_proposal,
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-reversal-001",
        )
    assert reversal.idempotent is False
    assert reversal.reversed_event_id == terminated.id
    assert replayed.id == reversal.id
    assert replayed.idempotent is True

    async with session_factory() as session:
        coverage = await session.get(TerminalContractAssetUnit, (CONTRACT_ID, UNIT_ID))
        assert coverage is not None
        assert coverage.effective_to == date(2026, 12, 31)

    async with session_factory() as session:
        reterminated = await service.terminate_terminal(
            session,
            contract_id=CONTRACT_ID,
            proposal=_proposal(),
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-termination-reverse-002",
        )
    async with session_factory() as session:
        coverage = await session.get(TerminalContractAssetUnit, (CONTRACT_ID, UNIT_ID))
        assert coverage is not None
        assert coverage.effective_to == date(2026, 6, 29)

    async with session_factory() as session:
        session.add(
            TerminalContract(  # type: ignore[call-arg]
                id=SUCCESSOR_ID,
                contract_number="TM-LIFECYCLE-INT-02",
                contract_mode="direct_lease",
                tenant_party_id=TENANT_ID,
                lessor_party_id=OWNER_ID,
                start_date=date(2026, 6, 30),
                end_date=date(2027, 6, 29),
                deposit_amount=Decimal("0"),
                rent_collector="owner",
                scan_document_id=SCAN_ID,
            )
        )
        await session.flush()
        session.add(
            TerminalContractAssetUnit(  # type: ignore[call-arg]
                terminal_contract_id=SUCCESSOR_ID,
                asset_unit_id=UNIT_ID,
                effective_from=date(2026, 6, 30),
                effective_to=date(2027, 6, 29),
            )
        )
        await session.commit()

    second_reversal = TerminalContractTerminationReversalProposal.model_validate(
        {
            "target_event_id": reterminated.id,
            "effective_date": "2026-07-02",
            "reason": "再次尝试撤销",
        }
    )
    async with session_factory() as session:
        with pytest.raises(TerminationReversalBlockedError) as error:
            await service.reverse_terminal_termination(
                session,
                contract_id=CONTRACT_ID,
                proposal=second_reversal,
                actor_id=ACTOR_ID,
                scope=SCOPE,
                idempotency_key="lifecycle-reversal-002",
            )
        await session.rollback()
    assert error.value.details["blocking_contract_ids"] == [SUCCESSOR_ID]

    async with session_factory() as session:
        coverage = await session.get(TerminalContractAssetUnit, (CONTRACT_ID, UNIT_ID))
        assert coverage is not None
        assert coverage.effective_to == date(2026, 6, 29)


async def test_upstream_exit_blocks_on_active_terminal_then_commits_and_reverses(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed(session_factory)
    async with session_factory() as session:
        session.add(
            UpstreamContract(  # type: ignore[call-arg]
                id=UPSTREAM_ID,
                contract_number="UP-LIFECYCLE-INT-01",
                contract_type="lease",
                name="终止集成测试上游合同",
                owner_party_id=OWNER_ID,
                operator_party_id=OWNER_ID,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                payment_cycle="monthly",
                payment_day=15,
                scan_document_id=SCAN_ID,
            )
        )
        await session.flush()
        session.add(
            UpstreamContractAssetUnit(  # type: ignore[call-arg]
                upstream_contract_id=UPSTREAM_ID,
                asset_unit_id=UNIT_ID,
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
            )
        )
        terminal = await session.get(TerminalContract, CONTRACT_ID)
        assert terminal is not None
        terminal.upstream_contract_id = UPSTREAM_ID
        await session.commit()

    service = _service()
    exit_proposal = UpstreamContractExitProposal.model_validate(
        {"effective_date": "2026-06-30", "reason": "提前解除承租合同"}
    )

    async with session_factory() as session:
        with pytest.raises(ActiveTerminalContractsBlockExitError):
            await service.preview_upstream_exit(
                session,
                contract_id=UPSTREAM_ID,
                proposal=exit_proposal,
                actor_id=ACTOR_ID,
                scope=SCOPE,
            )
        await session.rollback()

    async with session_factory() as session:
        await service.terminate_terminal(
            session,
            contract_id=CONTRACT_ID,
            proposal=TerminalContractTerminationProposal.model_validate(
                {
                    "effective_date": "2026-06-15",
                    "termination_type": "early",
                    "handover_status": "completed",
                    "deposit_settlement_status": "settled",
                    "reason": "退出前先终止终端合同",
                }
            ),
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-exit-terminal-termination-001",
        )

    async with session_factory() as session:
        preview = await service.preview_upstream_exit(
            session,
            contract_id=UPSTREAM_ID,
            proposal=exit_proposal,
            actor_id=ACTOR_ID,
            scope=SCOPE,
        )
    assert preview.contract_version == 1
    assert preview.last_valid_day == date(2026, 6, 29)
    assert len(preview.coverage_impact) == 1
    assert preview.coverage_impact[0].new_effective_to == date(2026, 6, 29)

    request = UpstreamContractExitCommitRequest.model_validate(
        {"preview_token": preview.preview_token, "expected_version": 1}
    )
    async with session_factory() as session:
        exited = await service.commit_upstream_exit(
            session,
            contract_id=UPSTREAM_ID,
            request=request,
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-upstream-exit-001",
        )
        replayed = await service.commit_upstream_exit(
            session,
            contract_id=UPSTREAM_ID,
            request=request,
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-upstream-exit-001",
        )
    assert exited.idempotent is False
    assert exited.event_type == "exited"
    assert replayed.id == exited.id
    assert replayed.idempotent is True

    async with session_factory() as session:
        upstream_coverage = await session.get(
            UpstreamContractAssetUnit, (UPSTREAM_ID, UNIT_ID)
        )
        terminal_coverage = await session.get(
            TerminalContractAssetUnit, (CONTRACT_ID, UNIT_ID)
        )
        assert upstream_coverage is not None
        assert upstream_coverage.effective_to == date(2026, 6, 29)
        assert terminal_coverage is not None
        assert terminal_coverage.effective_to == date(2026, 6, 14)

    reversal_proposal = UpstreamContractExitReversalProposal.model_validate(
        {
            "target_event_id": exited.id,
            "effective_date": "2026-07-01",
            "reason": "退出日期录入错误",
        }
    )
    async with session_factory() as session:
        reversal = await service.reverse_upstream_exit(
            session,
            contract_id=UPSTREAM_ID,
            proposal=reversal_proposal,
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-upstream-exit-reversal-001",
        )
        with pytest.raises(UpstreamExitReversalTargetInvalidError):
            await service.reverse_upstream_exit(
                session,
                contract_id=UPSTREAM_ID,
                proposal=reversal_proposal,
                actor_id=ACTOR_ID,
                scope=SCOPE,
                idempotency_key="lifecycle-upstream-exit-reversal-002",
            )
        await session.rollback()
    assert reversal.reversed_event_id == exited.id

    async with session_factory() as session:
        upstream_coverage = await session.get(
            UpstreamContractAssetUnit, (UPSTREAM_ID, UNIT_ID)
        )
        assert upstream_coverage is not None
        assert upstream_coverage.effective_to == date(2026, 12, 31)


async def test_renewals_chain_successors_atomically(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed(session_factory)
    async with session_factory() as session:
        session.add(
            UpstreamContract(  # type: ignore[call-arg]
                id=UPSTREAM_ID,
                contract_number="UP-LIFECYCLE-INT-01",
                contract_type="lease",
                name="续签集成测试上游合同",
                owner_party_id=OWNER_ID,
                operator_party_id=OWNER_ID,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                payment_cycle="monthly",
                payment_day=15,
                scan_document_id=SCAN_ID,
            )
        )
        await session.flush()
        session.add(
            UpstreamContractAssetUnit(  # type: ignore[call-arg]
                upstream_contract_id=UPSTREAM_ID,
                asset_unit_id=UNIT_ID,
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
            )
        )
        terminal = await session.get(TerminalContract, CONTRACT_ID)
        assert terminal is not None
        terminal.upstream_contract_id = UPSTREAM_ID
        unit = await session.get(AssetUnit, UNIT_ID)
        assert unit is not None
        unit.managed_to = date(2030, 12, 31)
        session.add_all(
            [
                Attachment(
                    id=RENEWAL_UPSTREAM_SCAN_ID,
                    owner_type="contract",
                    owner_id="lifecycle-intake-renewal-upstream",
                    file_name="renewal-upstream.pdf",
                    file_type="pdf",
                    file_size=1,
                    storage_key="lifecycle/integration/renewal-upstream.pdf",
                    created_by=ACTOR_ID,
                ),
                Attachment(
                    id=RENEWAL_TERMINAL_SCAN_ID,
                    owner_type="contract",
                    owner_id="lifecycle-intake-renewal-terminal",
                    file_name="renewal-terminal.pdf",
                    file_type="pdf",
                    file_size=1,
                    storage_key="lifecycle/integration/renewal-terminal.pdf",
                    created_by=ACTOR_ID,
                ),
            ]
        )
        await session.commit()

    service = _service()
    renewal_request = UpstreamContractRenewalRequest.model_validate(
        {
            "contract_number": "UP-LIFECYCLE-INT-02",
            "name": "续签后的上游合同",
            "start_date": "2027-01-01",
            "end_date": "2029-12-31",
            "payment_cycle": "monthly",
            "payment_day": 15,
            "deposit_amount": "50000",
            "scan_document_id": RENEWAL_UPSTREAM_SCAN_ID,
            "scan_owner_id": "lifecycle-intake-renewal-upstream",
        }
    )
    async with session_factory() as session:
        renewed = await service.renew_upstream(
            session,
            contract_id=UPSTREAM_ID,
            request=renewal_request,
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-renew-upstream-001",
        )
        replayed = await service.renew_upstream(
            session,
            contract_id=UPSTREAM_ID,
            request=renewal_request,
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-renew-upstream-001",
        )
    successor_id = renewed.id
    assert successor_id != UPSTREAM_ID
    assert renewed.renewed_from_id == UPSTREAM_ID
    assert replayed.id == renewed.id
    assert replayed.idempotent is True

    async with session_factory() as session:
        with pytest.raises(ContractAlreadyRenewedError):
            await service.renew_upstream(
                session,
                contract_id=UPSTREAM_ID,
                request=renewal_request.model_copy(
                    update={"contract_number": "UP-LIFECYCLE-INT-03"}
                ),
                actor_id=ACTOR_ID,
                scope=SCOPE,
                idempotency_key="lifecycle-renew-upstream-002",
            )
        await session.rollback()

    async with session_factory() as session:
        old_coverage = await session.get(
            UpstreamContractAssetUnit, (UPSTREAM_ID, UNIT_ID)
        )
        successor_coverage = await session.get(
            UpstreamContractAssetUnit, (successor_id, UNIT_ID)
        )
        renewed_event = await session.scalar(
            select(ContractLifecycleEvent).where(
                ContractLifecycleEvent.contract_kind == "upstream",
                ContractLifecycleEvent.contract_id == UPSTREAM_ID,
                ContractLifecycleEvent.event_type == "renewed",
            )
        )
        receipt = await session.scalar(
            select(AssetContractWriteReceipt).where(
                AssetContractWriteReceipt.actor_id == ACTOR_ID,
                AssetContractWriteReceipt.idempotency_key
                == "lifecycle-renew-upstream-001",
            )
        )
        scan = await session.get(Attachment, RENEWAL_UPSTREAM_SCAN_ID)
        assert old_coverage is not None
        assert old_coverage.effective_to == date(2026, 12, 31)
        assert successor_coverage is not None
        assert successor_coverage.effective_from == date(2027, 1, 1)
        assert successor_coverage.effective_to == date(2029, 12, 31)
        assert renewed_event is not None
        assert renewed_event.successor_contract_id == successor_id
        assert receipt is not None
        assert scan is not None
        assert scan.owner_id == successor_id

    terminal_renewal_request = TerminalContractRenewalRequest.model_validate(
        {
            "contract_number": "TM-LIFECYCLE-INT-02",
            "upstream_contract_id": successor_id,
            "start_date": "2027-01-01",
            "end_date": "2027-12-31",
            "deposit_amount": "20000",
            "scan_document_id": RENEWAL_TERMINAL_SCAN_ID,
            "scan_owner_id": "lifecycle-intake-renewal-terminal",
        }
    )
    stale_upstream_request = TerminalContractRenewalRequest.model_validate(
        {
            "contract_number": "TM-LIFECYCLE-INT-03",
            "start_date": "2027-01-01",
            "end_date": "2027-12-31",
            "deposit_amount": "20000",
            "scan_document_id": RENEWAL_TERMINAL_SCAN_ID,
            "scan_owner_id": "lifecycle-intake-renewal-terminal",
        }
    )
    async with session_factory() as session:
        with pytest.raises(AssetContractCoverageInvalidError):
            await service.renew_terminal(
                session,
                contract_id=CONTRACT_ID,
                request=stale_upstream_request,
                actor_id=ACTOR_ID,
                scope=SCOPE,
                idempotency_key="lifecycle-renew-terminal-002",
            )
        await session.rollback()

    async with session_factory() as session:
        terminal_renewed = await service.renew_terminal(
            session,
            contract_id=CONTRACT_ID,
            request=terminal_renewal_request,
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-renew-terminal-001",
        )
    assert terminal_renewed.renewed_from_id == CONTRACT_ID
    assert terminal_renewed.upstream_contract_id == successor_id

    async with session_factory() as session:
        changes = (
            (
                await session.execute(
                    select(BusinessChangeEvent).where(
                        BusinessChangeEvent.actor_id == ACTOR_ID,
                        BusinessChangeEvent.target_type == "upstream_contract",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(changes) == 3
        assert {change.action for change in changes} == {
            "confirmed",
            "renewed",
            "rent_obligations_replanned",
        }
        assert len({change.correlation_id for change in changes}) == 1
        assert {change.target_id for change in changes} == {UPSTREAM_ID, successor_id}

    async with session_factory() as session:
        with pytest.raises(ContractAlreadyRenewedError):
            await service.renew_terminal(
                session,
                contract_id=CONTRACT_ID,
                request=terminal_renewal_request.model_copy(
                    update={"contract_number": "TM-LIFECYCLE-INT-04"}
                ),
                actor_id=ACTOR_ID,
                scope=SCOPE,
                idempotency_key="lifecycle-renew-terminal-003",
            )
        await session.rollback()


async def test_query_views_replay_events_over_real_postgresql(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed(session_factory)
    async with session_factory() as session:
        session.add(
            UpstreamContract(  # type: ignore[call-arg]
                id=UPSTREAM_ID,
                contract_number="UP-LIFECYCLE-INT-01",
                contract_type="lease",
                name="查询集成测试上游合同",
                owner_party_id=OWNER_ID,
                operator_party_id=OWNER_ID,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 20),
                payment_cycle="monthly",
                payment_day=15,
                scan_document_id=SCAN_ID,
            )
        )
        await session.flush()
        session.add(
            UpstreamContractAssetUnit(  # type: ignore[call-arg]
                upstream_contract_id=UPSTREAM_ID,
                asset_unit_id=UNIT_ID,
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 20),
            )
        )
        terminal = await session.get(TerminalContract, CONTRACT_ID)
        assert terminal is not None
        terminal.upstream_contract_id = UPSTREAM_ID
        await session.commit()

    lifecycle_service = _service()
    async with session_factory() as session:
        await lifecycle_service.terminate_terminal(
            session,
            contract_id=CONTRACT_ID,
            proposal=TerminalContractTerminationProposal.model_validate(
                {
                    "effective_date": "2026-06-30",
                    "termination_type": "early",
                    "handover_status": "completed",
                    "deposit_settlement_status": "settled",
                    "reason": "查询集成测试终止",
                }
            ),
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-query-termination-001",
        )

    from src.crud.asset_contract import asset_contract_repository
    from src.services.asset_operations.query_service import (
        AssetOperationsQueryService,
    )

    query_service = AssetOperationsQueryService(
        asset_contract_repository=asset_contract_repository,
        business_today=lambda: date(2026, 10, 25),
    )

    async with session_factory() as session:
        terminal_rows, terminal_total = await query_service.list_terminal_contracts(
            session, scope=SCOPE
        )
        upstream_rows, upstream_total = await query_service.list_upstream_contracts(
            session, scope=SCOPE
        )
        terminal_detail = await query_service.get_terminal_contract(
            session, CONTRACT_ID, scope=SCOPE
        )
        upstream_detail = await query_service.get_upstream_contract(
            session, UPSTREAM_ID, scope=SCOPE
        )

    assert terminal_total == 1
    assert terminal_rows[0].status == "ended"
    assert "TERMINAL_TERM_EXCEEDS_UPSTREAM" in [
        warning.code for warning in terminal_rows[0].warnings
    ]
    assert upstream_total == 1
    assert upstream_rows[0].status == "expiring"

    assert terminal_detail is not None
    assert terminal_detail.status == "ended"
    assert len(terminal_detail.coverages) == 1
    assert terminal_detail.coverages[0].effective_to == date(2026, 6, 29)
    assert [item.relation for item in terminal_detail.renewal_chain] == ["current"]
    assert [event.event_type for event in terminal_detail.lifecycle_events] == [
        "terminated"
    ]

    assert upstream_detail is not None
    assert upstream_detail.terminal_contract_ids == [CONTRACT_ID]
    assert len(upstream_detail.coverages) == 1
    assert [item.relation for item in upstream_detail.renewal_chain] == ["current"]


async def test_contract_updates_follow_coverage_and_enforce_locks(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed(session_factory)
    command_service = AssetContractCommandService(
        clock=lambda: datetime(2026, 10, 25, 1, 0, tzinfo=UTC),
        business_today=lambda: date(2026, 10, 25),
    )
    async with session_factory() as session:
        with pytest.raises(AssetOperationsVersionConflictError):
            await command_service.update_terminal(
                session,
                contract_id=CONTRACT_ID,
                request=TerminalContractUpdate.model_validate(
                    {"expected_version": 99, "deposit_amount": "1"}
                ),
                actor_id=ACTOR_ID,
                scope=SCOPE,
            )
        await session.rollback()

    async with session_factory() as session:
        with pytest.raises(AssetContractCoverageInvalidError) as error:
            await command_service.update_terminal(
                session,
                contract_id=CONTRACT_ID,
                request=TerminalContractUpdate.model_validate(
                    {"expected_version": 1, "end_date": "2025-06-30"}
                ),
                actor_id=ACTOR_ID,
                scope=SCOPE,
            )
        await session.rollback()
    assert error.value.details["reason"] == "end_date_before_start"

    async with session_factory() as session:
        updated = await command_service.update_terminal(
            session,
            contract_id=CONTRACT_ID,
            request=TerminalContractUpdate.model_validate(
                {
                    "expected_version": 1,
                    "end_date": "2027-06-30",
                    "deposit_amount": "26000",
                }
            ),
            actor_id=ACTOR_ID,
            scope=SCOPE,
        )
    assert updated.end_date == date(2027, 6, 30)
    assert updated.version == 2

    async with session_factory() as session:
        coverage = await session.get(TerminalContractAssetUnit, (CONTRACT_ID, UNIT_ID))
        contract = await session.get(TerminalContract, CONTRACT_ID)
        assert coverage is not None
        assert coverage.effective_to == date(2027, 6, 30)
        assert contract is not None
        assert contract.deposit_amount == Decimal("26000")
        assert contract.version == 2

    async with session_factory() as session:
        with pytest.raises(AssetContractCoverageInvalidError) as period_error:
            await command_service.update_terminal(
                session,
                contract_id=CONTRACT_ID,
                request=TerminalContractUpdate.model_validate(
                    {"expected_version": 2, "end_date": "2028-12-31"}
                ),
                actor_id=ACTOR_ID,
                scope=SCOPE,
            )
        await session.rollback()
    assert period_error.value.details["reason"] == "outside_asset_unit_managed_period"

    async with session_factory() as session:
        session.add(
            TerminalContract(  # type: ignore[call-arg]
                id=OVERLAP_ID,
                contract_number="TM-LIFECYCLE-INT-09",
                contract_mode="sublease",
                tenant_party_id=TENANT_ID,
                lessor_party_id=OWNER_ID,
                start_date=date(2027, 7, 1),
                end_date=date(2027, 12, 31),
                deposit_amount=Decimal("0"),
                rent_collector="operator",
                scan_document_id=SCAN_ID,
            )
        )
        await session.flush()
        session.add(
            TerminalContractAssetUnit(  # type: ignore[call-arg]
                terminal_contract_id=OVERLAP_ID,
                asset_unit_id=UNIT_ID,
                effective_from=date(2027, 7, 1),
                effective_to=date(2027, 12, 31),
            )
        )
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(AssetContractCoverageInvalidError) as overlap_error:
            await command_service.update_terminal(
                session,
                contract_id=CONTRACT_ID,
                request=TerminalContractUpdate.model_validate(
                    {"expected_version": 2, "end_date": "2027-12-31"}
                ),
                actor_id=ACTOR_ID,
                scope=SCOPE,
            )
        await session.rollback()
    assert overlap_error.value.details["reason"] == "coverage_overlap_after_extension"

    async with session_factory() as session:
        coverage = await session.get(TerminalContractAssetUnit, (CONTRACT_ID, UNIT_ID))
        assert coverage is not None
        assert coverage.effective_to == date(2027, 6, 30)


async def test_asset_unit_reads_and_updates_over_real_postgresql(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed(session_factory)
    from src.crud.asset_contract import asset_contract_repository
    from src.crud.asset_unit import asset_unit_repository
    from src.services.asset_operations.asset_unit_command_service import (
        AssetUnitCommandService,
    )
    from src.services.asset_operations.query_service import (
        AssetOperationsQueryService,
    )

    query_service = AssetOperationsQueryService(
        asset_unit_repository=asset_unit_repository,
        asset_contract_repository=asset_contract_repository,
        business_today=lambda: date(2026, 10, 25),
    )
    command_service = AssetUnitCommandService(
        repository=asset_unit_repository,
        contract_repository=asset_contract_repository,
        business_today=lambda: date(2026, 10, 25),
    )

    async with session_factory() as session:
        items, total = await query_service.list_asset_units(session, scope=SCOPE)
        detail = await query_service.get_asset_unit_detail(
            session, UNIT_ID, scope=SCOPE
        )
    assert total == 1
    assert items[0].rental_status == "rented"
    assert items[0].occupancy_rate == Decimal("1")
    assert detail is not None
    assert detail.terminal_contract_ids == [CONTRACT_ID]

    async with session_factory() as session:
        updated = await command_service.update_asset_unit(
            session,
            unit_id=UNIT_ID,
            request=AssetUnitUpdate.model_validate(
                {"expected_version": 1, "name": "改名后的集成单元"}
            ),
            actor_id=ACTOR_ID,
            scope=SCOPE,
        )
    assert updated.name == "改名后的集成单元"
    assert updated.rental_status == "rented"

    async with session_factory() as session:
        unit = await session.get(AssetUnit, UNIT_ID)
        assert unit is not None
        assert unit.version == 2

    async with session_factory() as session:
        with pytest.raises(AssetOperationsVersionConflictError):
            await command_service.update_asset_unit(
                session,
                unit_id=UNIT_ID,
                request=AssetUnitUpdate.model_validate(
                    {"expected_version": 1, "name": "旧版本"}
                ),
                actor_id=ACTOR_ID,
                scope=SCOPE,
            )
        await session.rollback()

    async with session_factory() as session:
        with pytest.raises(AssetUnitAreaInvalidError):
            await command_service.update_asset_unit(
                session,
                unit_id=UNIT_ID,
                request=AssetUnitUpdate.model_validate(
                    {"expected_version": 2, "rentable_area": "999"}
                ),
                actor_id=ACTOR_ID,
                scope=SCOPE,
            )
        await session.rollback()

    async with session_factory() as session:
        noted = await command_service.update_vacancy_note(
            session,
            unit_id=UNIT_ID,
            request=AssetUnitVacancyNoteUpdate.model_validate(
                {
                    "expected_version": 2,
                    "vacancy_reason": "renovation",
                    "expected_lease_start": "2027-03-01",
                }
            ),
            actor_id=ACTOR_ID,
            scope=SCOPE,
        )
    assert noted.vacancy_reason == "renovation"

    async with session_factory() as session:
        with pytest.raises(AssetUnitPeriodOverlapError) as overlap_error:
            await command_service.update_asset_unit(
                session,
                unit_id=UNIT_ID,
                request=AssetUnitUpdate.model_validate(
                    {"expected_version": 3, "managed_from": "2026-06-01"}
                ),
                actor_id=ACTOR_ID,
                scope=SCOPE,
            )
        await session.rollback()
    assert overlap_error.value.details["terminal_contract_ids"] == [CONTRACT_ID]


async def test_future_reversal_does_not_restore_rented_status(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed(session_factory)
    lifecycle_service = _service()
    async with session_factory() as session:
        terminated = await lifecycle_service.terminate_terminal(
            session,
            contract_id=CONTRACT_ID,
            proposal=TerminalContractTerminationProposal.model_validate(
                {
                    "effective_date": "2026-06-30",
                    "termination_type": "early",
                    "handover_status": "completed",
                    "deposit_settlement_status": "settled",
                    "reason": "未来撤销前先终止",
                }
            ),
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-query-future-reversal-term-001",
        )

    from src.crud.asset_contract import asset_contract_repository
    from src.crud.asset_unit import asset_unit_repository
    from src.services.asset_operations.query_service import (
        AssetOperationsQueryService,
    )

    query_service = AssetOperationsQueryService(
        asset_unit_repository=asset_unit_repository,
        asset_contract_repository=asset_contract_repository,
        business_today=lambda: date(2026, 10, 25),
    )
    async with session_factory() as session:
        items, _ = await query_service.list_asset_units(session, scope=SCOPE)
    assert items[0].rental_status == "vacant"

    async with session_factory() as session:
        await lifecycle_service.reverse_terminal_termination(
            session,
            contract_id=CONTRACT_ID,
            proposal=TerminalContractTerminationReversalProposal.model_validate(
                {
                    "target_event_id": terminated.id,
                    "effective_date": "2027-01-01",
                    "reason": "撤销登记在未来的复核",
                }
            ),
            actor_id=ACTOR_ID,
            scope=SCOPE,
            idempotency_key="lifecycle-query-future-reversal-rev-001",
        )

    async with session_factory() as session:
        items, _ = await query_service.list_asset_units(session, scope=SCOPE)
    assert items[0].rental_status == "vacant"
