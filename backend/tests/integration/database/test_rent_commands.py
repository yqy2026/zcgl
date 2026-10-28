"""PostgreSQL rent writes, corrections and rollback boundaries."""

from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.exception_handler import BaseBusinessError, ResourceNotFoundError
from src.models.asset_contract import ContractRentSchedule, UpstreamContract
from src.models.asset_ledger import RentLedgerEntry, RentPaymentRecord
from src.schemas.asset_operations import (
    UpstreamContractCreate,
)
from src.schemas.rent_commands import (
    RentPaymentRequest,
    RentReversalRequest,
    RentScheduleCorrectionCommit,
    RentScheduleCorrectionProposal,
)
from src.services.asset_operations.contract_command_service import (
    AssetContractCommandService,
)
from src.services.asset_operations.rent_ledger_projections import effective_paid
from src.services.asset_operations.rent_payment_command_service import (
    RentPaymentCommandService,
)
from src.services.asset_operations.rent_schedule_correction_service import (
    RentScheduleCorrectionService,
)
from src.services.party_scope_resolver import EffectivePartyScope
from tests.integration.database import test_asset_contract_command as contract_fixtures
from tests.integration.database.test_asset_contract_command import (
    ACTOR_ID,
    OWNER_ID,
    UNIT_ID,
    UPSTREAM_SCAN_ID,
    _seed,
)

session_factory = contract_fixtures.session_factory

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.asyncio]


@pytest.fixture
async def ledger_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    yield session_factory
    async with session_factory() as db:
        record_ids = select(RentPaymentRecord.id).where(
            RentPaymentRecord.created_by == ACTOR_ID
        )
        await db.execute(
            delete(RentPaymentRecord).where(
                RentPaymentRecord.reverses_record_id.in_(record_ids)
            )
        )
        await db.execute(
            delete(RentPaymentRecord).where(RentPaymentRecord.created_by == ACTOR_ID)
        )
        await db.execute(
            delete(RentLedgerEntry).where(
                RentLedgerEntry.contract_id.in_(
                    select(UpstreamContract.id).where(
                        UpstreamContract.contract_number == "UP-ASSET-CONTRACT-INT"
                    )
                )
            )
        )
        await db.commit()


async def create_contract(
    factory: async_sessionmaker[AsyncSession],
    *,
    with_schedule: bool = True,
    cycle: str = "monthly",
):
    scope = await _seed(factory)
    request = UpstreamContractCreate.model_validate(
        {
            "contract_number": "UP-ASSET-CONTRACT-INT",
            "contract_type": "lease",
            "name": "租金命令测试",
            "owner_party_id": OWNER_ID,
            "operator_party_id": OWNER_ID,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "payment_cycle": "monthly",
            "scan_document_id": UPSTREAM_SCAN_ID,
            "asset_unit_ids": [UNIT_ID],
            "rent_schedules": [
                {
                    "stage_start": "2026-01-01",
                    "stage_end": "2026-12-31",
                    "base_monthly_rent": "100",
                    "actual_monthly_rent": "100",
                    "payment_cycle": cycle,
                    "due_day": 25,
                }
            ]
            if with_schedule
            else [],
        }
    )
    async with factory() as db:
        contract = await AssetContractCommandService().create_upstream(
            db,
            request=request,
            actor_id=ACTOR_ID,
            scope=scope,
            idempotency_key="rent-create",
            attachment_owner_id="contract-intake-upstream",
        )
    return contract, scope


async def test_two_payments_reversal_scope_and_idempotency(ledger_factory):
    factory = ledger_factory
    contract, scope = await create_contract(factory)
    async with factory() as db:
        entry = (
            (
                await db.execute(
                    select(RentLedgerEntry)
                    .where(RentLedgerEntry.contract_id == contract.id)
                    .order_by(RentLedgerEntry.period_start)
                )
            )
            .scalars()
            .first()
        )
        assert entry is not None
        entry_id, version = entry.id, entry.version
    service = RentPaymentCommandService()

    def request(amount, expected):
        return RentPaymentRequest(
            record_type="payment",
            amount=amount,
            occurred_on=date(2026, 1, 25),
            expected_version=expected,
        )

    async with factory() as db:
        first = await service.register(
            db,
            entry_id=entry_id,
            request=request("40", version),
            actor_id=ACTOR_ID,
            scope=scope,
            idempotency_key="rent-pay-1",
        )
    async with factory() as db:
        second = await service.register(
            db,
            entry_id=entry_id,
            request=request("60", first.version),
            actor_id=ACTOR_ID,
            scope=scope,
            idempotency_key="rent-pay-2",
        )
    async with factory() as db:
        replay = await service.register(
            db,
            entry_id=entry_id,
            request=request("60", first.version),
            actor_id=ACTOR_ID,
            scope=scope,
            idempotency_key="rent-pay-2",
        )
        assert replay.id == second.id and replay.idempotent
    async with factory() as db:
        with pytest.raises(BaseBusinessError) as error:
            await service.register(
                db,
                entry_id=entry_id,
                request=request("61", first.version),
                actor_id=ACTOR_ID,
                scope=scope,
                idempotency_key="rent-pay-2",
            )
        assert error.value.code == "IDEMPOTENCY_CONFLICT"
    async with factory() as db:
        reversal = await service.reverse(
            db,
            record_id=second.id,
            request=RentReversalRequest(
                reason="更正重复登记", expected_version=second.version
            ),
            actor_id=ACTOR_ID,
            scope=scope,
            idempotency_key="rent-reverse-2",
        )
    async with factory() as db:
        records = (
            (
                await db.execute(
                    select(RentPaymentRecord).where(
                        RentPaymentRecord.ledger_entry_id == entry_id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(records) == 3
        assert effective_paid(records) == Decimal("40")
        assert reversal.reverses_record_id == second.id
        with pytest.raises(BaseBusinessError) as error:
            await service.register(
                db,
                entry_id=entry_id,
                request=request("61", reversal.version),
                actor_id=ACTOR_ID,
                scope=scope,
                idempotency_key="rent-overpay",
            )
        assert error.value.code == "PAYMENT_AMOUNT_EXCEEDS_REMAINING"
    outside = EffectivePartyScope(
        user_id=ACTOR_ID,
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["outside"],
    )
    async with factory() as db:
        with pytest.raises(ResourceNotFoundError):
            await service.register(
                db,
                entry_id=entry_id,
                request=request("10", reversal.version),
                actor_id=ACTOR_ID,
                scope=outside,
                idempotency_key="rent-outside",
            )


class PreviewStore:
    def __init__(self):
        self.items = {}

    def issue(self, payload):
        from datetime import UTC, datetime

        self.items["correction-token"] = payload
        return "correction-token", datetime(2027, 1, 1, tzinfo=UTC)

    def peek(self, token):
        return self.items.get(token)

    def delete(self, token):
        return self.items.pop(token, None) is not None


async def test_correction_backfills_old_gap_and_retains_superseded_stage(
    ledger_factory,
):
    factory = ledger_factory
    contract, scope = await create_contract(factory, with_schedule=False)
    service = RentScheduleCorrectionService(
        preview_store=PreviewStore(), business_today=lambda: date(2026, 3, 3)
    )
    proposal = RentScheduleCorrectionProposal.model_validate(
        {
            "reason": "补录往月遗漏阶段",
            "rent_schedules": [
                {
                    "stage_start": "2026-01-01",
                    "stage_end": "2026-12-31",
                    "base_monthly_rent": "100",
                    "actual_monthly_rent": "100",
                    "payment_cycle": "monthly",
                    "due_day": 25,
                },
            ],
        }
    )
    async with factory() as db:
        preview = await service.preview(
            db,
            contract_kind="upstream",
            contract_id=contract.id,
            request=proposal,
            actor_id=ACTOR_ID,
            scope=scope,
        )
        assert preview.impact["created_count"] == 12
        assert [(s.stage_start, s.stage_end) for s in preview.rent_schedules] == [
            (date(2026, 1, 1), date(2026, 2, 28)),
            (date(2026, 3, 1), date(2026, 12, 31)),
        ]
    async with factory() as db:
        first = await service.commit(
            db,
            contract_kind="upstream",
            contract_id=contract.id,
            request=RentScheduleCorrectionCommit(
                preview_token=preview.preview_token,
                expected_version=preview.contract_version,
            ),
            actor_id=ACTOR_ID,
            scope=scope,
            idempotency_key="correct-gap",
        )
    updated = proposal.model_copy(
        update={
            "rent_schedules": [
                proposal.rent_schedules[0].model_copy(
                    update={"stage_end": date(2026, 2, 28)}
                ),
                proposal.rent_schedules[0].model_copy(
                    update={
                        "stage_start": date(2026, 3, 1),
                        "actual_monthly_rent": Decimal("110"),
                    }
                ),
            ]
        }
    )
    async with factory() as db:
        preview = await service.preview(
            db,
            contract_kind="upstream",
            contract_id=contract.id,
            request=updated,
            actor_id=ACTOR_ID,
            scope=scope,
        )
    async with factory() as db:
        await service.commit(
            db,
            contract_kind="upstream",
            contract_id=contract.id,
            request=RentScheduleCorrectionCommit(
                preview_token=preview.preview_token, expected_version=first.version
            ),
            actor_id=ACTOR_ID,
            scope=scope,
            idempotency_key="correct-current",
        )
    async with factory() as db:
        schedules = (
            (
                await db.execute(
                    select(ContractRentSchedule).where(
                        ContractRentSchedule.contract_id == contract.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(schedules) == 4
        assert sum(row.superseded_at is not None for row in schedules) == 2
        january = (
            (
                await db.execute(
                    select(RentLedgerEntry).where(
                        RentLedgerEntry.contract_id == contract.id,
                        RentLedgerEntry.period == "2026-01",
                    )
                )
            )
            .scalars()
            .one()
        )
        march = (
            (
                await db.execute(
                    select(RentLedgerEntry).where(
                        RentLedgerEntry.contract_id == contract.id,
                        RentLedgerEntry.period == "2026-03",
                    )
                )
            )
            .scalars()
            .one()
        )
        assert january.due_amount == Decimal("100")
        assert march.due_amount == Decimal("110")
