"""Append-only rent payment facts and explicitly justified manual obligations."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from ...core.exception_handler import ResourceNotFoundError
from ...crud.asset_contract import asset_contract_repository
from ...crud.asset_ledger import asset_ledger_repository
from ...crud.attachment import attachment_crud
from ...crud.rent_commands import rent_command_repository
from ...models.asset_contract import TerminalContract, UpstreamContract
from ...models.asset_ledger import RentLedgerEntry, RentPaymentRecord
from ...schemas.rent_commands import (
    ManualRentEntryRequest,
    RentEntryCommandResponse,
    RentPaymentRequest,
    RentRecordCommandResponse,
    RentReversalRequest,
    VoidRentEntryRequest,
)
from ..party_scope_resolver import EffectivePartyScope
from .business_change_service import contract_snapshot
from .errors import (
    AssetOperationsIdempotencyConflictError,
    AssetOperationsVersionConflictError,
)
from .rent_command_support import (
    audit,
    check_version,
    fingerprint,
    receipt,
    replay_receipt,
    require_scope,
    scoped_contract,
)
from .rent_errors import rent_error
from .rent_ledger_projections import effective_paid
from .rent_obligation_service import rent_obligation_service


def validate_payment(
    *,
    entry_type: str,
    record_type: str,
    amount: Decimal,
    remaining: Decimal,
    voided: bool,
) -> None:
    if voided:
        raise rent_error("RENT_LEDGER_ENTRY_VOIDED", "已作废的租金义务不能登记")
    expected = {
        "upstream_payable": "payment",
        "terminal_receivable": "receipt",
        "owner_receipt_expected": "owner_reported_receipt",
    }
    if expected.get(entry_type) != record_type:
        raise rent_error(
            "RENT_RECORD_TYPE_MISMATCH", "登记类型与租金义务不匹配", status=422
        )
    if amount > remaining:
        raise rent_error("PAYMENT_AMOUNT_EXCEEDS_REMAINING", "登记金额超过剩余义务")


class RentPaymentCommandService:
    async def _entry(
        self, db: AsyncSession, *, entry_id: str, scope: EffectivePartyScope, lock: bool
    ) -> RentLedgerEntry:
        row = await asset_ledger_repository.get_entry(db, entry_id=entry_id)
        if row is None:
            raise ResourceNotFoundError("RentLedgerEntry", entry_id)
        await scoped_contract(
            db,
            kind=row.contract_kind,
            contract_id=row.contract_id,
            scope=scope,
            lock=lock,
        )
        if lock:
            row = await asset_ledger_repository.get_entry(
                db, entry_id=entry_id, for_update=True
            )
            if row is None:
                raise ResourceNotFoundError("RentLedgerEntry", entry_id)
        return row

    @staticmethod
    def _result(
        record: RentPaymentRecord, entry: RentLedgerEntry, *, idempotent: bool = False
    ) -> RentRecordCommandResponse:
        return RentRecordCommandResponse(
            id=record.id,
            ledger_entry_id=entry.id,
            record_type=record.record_type,
            amount=record.amount,
            occurred_on=record.occurred_on,
            reverses_record_id=record.reverses_record_id,
            reason=record.reason,
            version=entry.version,
            idempotent=idempotent,
        )

    async def _replay_payment(
        self,
        db: AsyncSession,
        *,
        value: RentPaymentRecord,
        entry: RentLedgerEntry,
        actor_id: str,
        request: RentPaymentRequest,
    ) -> RentRecordCommandResponse:
        if (
            value.ledger_entry_id != entry.id
            or value.created_by != actor_id
            or value.record_type != request.record_type
            or value.amount != request.amount
            or value.occurred_on != request.occurred_on
            or value.document_id != request.document_id
        ):
            raise AssetOperationsIdempotencyConflictError()
        return self._result(value, entry, idempotent=True)

    async def register(
        self,
        db: AsyncSession,
        *,
        entry_id: str,
        request: RentPaymentRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> RentRecordCommandResponse:
        require_scope(scope, actor_id)
        try:
            entry = await self._entry(db, entry_id=entry_id, scope=scope, lock=True)
            existing = await asset_ledger_repository.get_record_by_idempotency(
                db, key=idempotency_key
            )
            if existing is not None:
                return await self._replay_payment(
                    db, value=existing, entry=entry, actor_id=actor_id, request=request
                )
            check_version(entry.id, entry.version, request.expected_version)
            records = await asset_ledger_repository.list_records(
                db, entry_ids=(entry.id,)
            )
            paid = effective_paid(records)
            validate_payment(
                entry_type=entry.entry_type,
                record_type=request.record_type,
                amount=request.amount,
                remaining=entry.due_amount - paid,
                voided=entry.voided_at is not None,
            )
            if request.document_id is not None:
                document = await attachment_crud.get_for_owner(
                    db,
                    attachment_id=request.document_id,
                    owner_type="contract",
                    owner_id=entry.contract_id,
                )
                if document is None:
                    document = await attachment_crud.get_for_owner(
                        db,
                        attachment_id=request.document_id,
                        owner_type="rent_ledger_entry",
                        owner_id=entry.id,
                    )
                if document is None:
                    raise ResourceNotFoundError("Attachment", request.document_id)
            record = RentPaymentRecord(  # type: ignore[call-arg]
                id=str(uuid4()),
                ledger_entry_id=entry.id,
                record_type=request.record_type,
                amount=request.amount,
                occurred_on=request.occurred_on,
                document_id=request.document_id,
                created_by=actor_id,
                created_at=datetime.now(UTC),
                idempotency_key=idempotency_key,
            )
            await asset_ledger_repository.add_record(db, record=record)
            entry.version += 1
            await db.flush()
            await audit(
                db,
                kind=entry.contract_kind,
                contract_id=entry.contract_id,
                action="rent_payment_registered",
                actor_id=actor_id,
                correlation_id=record.id,
                before={"entry_id": entry.id, "effective_paid_amount": str(paid)},
                after={
                    "record_id": record.id,
                    "effective_paid_amount": str(paid + record.amount),
                },
            )
            result = self._result(record, entry)
            await db.commit()
            return result
        except IntegrityError:
            await db.rollback()
            entry = await self._entry(db, entry_id=entry_id, scope=scope, lock=False)
            existing = await asset_ledger_repository.get_record_by_idempotency(
                db, key=idempotency_key
            )
            if existing is None:
                raise
            return await self._replay_payment(
                db, value=existing, entry=entry, actor_id=actor_id, request=request
            )
        except StaleDataError as error:
            await db.rollback()
            raise AssetOperationsVersionConflictError(
                unit_id=entry_id,
                expected_version=request.expected_version,
                actual_version=None,
            ) from error
        except Exception:
            await db.rollback()
            raise

    async def reverse(
        self,
        db: AsyncSession,
        *,
        record_id: str,
        request: RentReversalRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> RentRecordCommandResponse:
        require_scope(scope, actor_id)
        if request.reason.strip() == "":
            raise rent_error("REVERSAL_REASON_REQUIRED", "撤销原因必填", status=422)
        try:
            original = await asset_ledger_repository.get_record(db, record_id=record_id)
            if original is None:
                raise ResourceNotFoundError("RentPaymentRecord", record_id)
            if original.record_type == "deposit_offset":
                return await self._reverse_deposit_offset(
                    db,
                    original=original,
                    request=request,
                    actor_id=actor_id,
                    scope=scope,
                    idempotency_key=idempotency_key,
                )
            entry = await self._entry(
                db, entry_id=original.ledger_entry_id, scope=scope, lock=True
            )
            existing = await asset_ledger_repository.get_record_by_idempotency(
                db, key=idempotency_key
            )
            if existing is not None:
                if (
                    existing.created_by != actor_id
                    or existing.reverses_record_id != record_id
                    or existing.reason != request.reason
                ):
                    raise AssetOperationsIdempotencyConflictError()
                return self._result(existing, entry, idempotent=True)
            check_version(entry.id, entry.version, request.expected_version)
            if (
                original.record_type == "reversal"
                or await rent_command_repository.find_reversal(db, record_id=record_id)
                is not None
            ):
                raise rent_error("PAYMENT_RECORD_ALREADY_REVERSED", "该登记已撤销")
            record = RentPaymentRecord(  # type: ignore[call-arg]
                id=str(uuid4()),
                ledger_entry_id=entry.id,
                record_type="reversal",
                amount=original.amount,
                occurred_on=datetime.now(ZoneInfo("Asia/Shanghai")).date(),
                reverses_record_id=original.id,
                reason=request.reason,
                created_by=actor_id,
                created_at=datetime.now(UTC),
                idempotency_key=idempotency_key,
            )
            await asset_ledger_repository.add_record(db, record=record)
            entry.version += 1
            await db.flush()
            await rent_obligation_service.replan(
                db,
                contract_kind=entry.contract_kind,
                contract_id=entry.contract_id,
                actor_id=actor_id,
                correlation_id=record.id,
            )
            await audit(
                db,
                kind=entry.contract_kind,
                contract_id=entry.contract_id,
                action="rent_payment_reversed",
                actor_id=actor_id,
                correlation_id=record.id,
                before={"record_id": original.id},
                after={"reversal_record_id": record.id},
                reason=request.reason,
            )
            result = self._result(record, entry)
            await db.commit()
            return result
        except IntegrityError:
            await db.rollback()
            existing = await asset_ledger_repository.get_record_by_idempotency(
                db, key=idempotency_key
            )
            if existing is None:
                raise
            if (
                existing.created_by != actor_id
                or existing.reverses_record_id != record_id
                or existing.reason != request.reason
            ):
                raise AssetOperationsIdempotencyConflictError()
            entry = await self._entry(
                db, entry_id=existing.ledger_entry_id, scope=scope, lock=False
            )
            return self._result(existing, entry, idempotent=True)
        except StaleDataError as error:
            await db.rollback()
            raise AssetOperationsVersionConflictError(
                unit_id=record_id,
                expected_version=request.expected_version,
                actual_version=None,
            ) from error
        except Exception:
            await db.rollback()
            raise

    async def _reverse_deposit_offset(
        self,
        db: AsyncSession,
        *,
        original: RentPaymentRecord,
        request: RentReversalRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> RentRecordCommandResponse:
        from ...crud.deposit_ledger import deposit_ledger_repository
        from ...schemas.deposit_commands import DepositReversalRequest
        from .deposit_command_service import deposit_command_service

        deposit_record_id = original.paired_deposit_record_id
        if deposit_record_id is None:
            raise rent_error("DEPOSIT_OFFSET_TARGET_INVALID", "租金抵扣缺少押金登记关联")
        deposit = await deposit_ledger_repository.get_record(
            db, record_id=deposit_record_id
        )
        if deposit is None:
            raise ResourceNotFoundError("DepositRecord", deposit_record_id)
        deposit_entry, rent = await deposit_command_service._lock(
            db,
            entry_id=deposit.deposit_entry_id,
            scope=scope,
            offset_id=original.ledger_entry_id,
        )
        if rent is None:
            raise ResourceNotFoundError("RentLedgerEntry", original.ledger_entry_id)
        # Check replay before the optimistic version: a successful retry keeps its original version.
        existing = await asset_ledger_repository.get_record_by_idempotency(
            db, key=idempotency_key
        )
        if existing is not None:
            if (
                existing.reverses_record_id != original.id
                or existing.created_by != actor_id
                or existing.reason != request.reason
            ):
                raise AssetOperationsIdempotencyConflictError()
            return self._result(existing, rent, idempotent=True)
        check_version(rent.id, rent.version, request.expected_version)
        result = await deposit_command_service.reverse(
            db,
            record_id=deposit.id,
            request=DepositReversalRequest(
                reason=request.reason, expected_version=deposit_entry.version
            ),
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key,
            commit=False,
        )
        paired = await asset_ledger_repository.get_record_by_idempotency(
            db, key=f"deposit:{result.id}"
        )
        if paired is None:
            raise ResourceNotFoundError("RentPaymentRecord", result.id)
        # The public rent key belongs to this rent-side reversal as well.
        paired.idempotency_key = idempotency_key
        await db.flush()
        response = self._result(paired, rent, idempotent=result.idempotent)
        await db.commit()
        return response

    async def create_manual(
        self,
        db: AsyncSession,
        *,
        request: ManualRentEntryRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> RentEntryCommandResponse:
        require_scope(scope, actor_id)
        action = "create_manual_rent_entry"
        request_fingerprint = fingerprint(action, request.contract_id, request)
        try:
            contract = await scoped_contract(
                db,
                kind=request.contract_kind,
                contract_id=request.contract_id,
                scope=scope,
                lock=True,
            )
            existing = await asset_contract_repository.get_write_receipt(
                db, actor_id=actor_id, idempotency_key=idempotency_key
            )
            if existing is not None:
                return RentEntryCommandResponse.model_validate(
                    replay_receipt(existing, request_fingerprint)
                )
            if request.basis_note.strip() == "":
                raise rent_error(
                    "MANUAL_ENTRY_BASIS_REQUIRED", "依据说明必填", status=422
                )
            if (
                isinstance(contract, UpstreamContract)
                and contract.contract_type != "lease"
            ):
                raise rent_error(
                    "RENT_LEDGER_MANUAL_ENTRY_NOT_ALLOWED", "委托管理协议没有租金义务"
                )
            schedules = await asset_contract_repository.list_rent_schedules(
                db,
                contract_kind=request.contract_kind,
                contract_ids=(request.contract_id,),
            )
            events = await asset_contract_repository.list_lifecycle_events(
                db, contract_kind=request.contract_kind, contract_id=request.contract_id
            )
            reversed_ids = {
                event.reversed_event_id
                for event in events
                if event.event_type == "reversed"
            }
            active_events = [event for event in events if event.id not in reversed_ids]
            early = None
            if request.origin == "clawback":
                early = next(
                    (
                        event
                        for event in active_events
                        if event.event_type == "terminated"
                        and event.termination_type == "early"
                    ),
                    None,
                )
                if (
                    not isinstance(contract, TerminalContract)
                    or contract.contract_mode != "sublease"
                    or early is None
                    or any(
                        value is not None
                        for value in (
                            request.period_start,
                            request.period_end,
                            request.due_date,
                        )
                    )
                ):
                    raise rent_error(
                        "RENT_LEDGER_MANUAL_ENTRY_NOT_ALLOWED",
                        "补收免租只适用于已提前终止的转租合同",
                    )
                start = end = due = early.effective_date
            else:
                if (
                    request.period_start is None
                    or request.period_end is None
                    or request.due_date is None
                ):
                    raise rent_error(
                        "RENT_LEDGER_MANUAL_ENTRY_NOT_ALLOWED",
                        "手工义务需完整账期与到期日",
                    )
                start, end, due = (
                    request.period_start,
                    request.period_end,
                    request.due_date,
                )
                cutoff = min(
                    (
                        event.effective_date
                        for event in active_events
                        if event.event_type in {"terminated", "exited"}
                    ),
                    default=None,
                )
                if (
                    start < contract.start_date
                    or end > contract.end_date
                    or end < start
                    or (cutoff is not None and end >= cutoff)
                ):
                    raise rent_error(
                        "RENT_LEDGER_MANUAL_ENTRY_NOT_ALLOWED",
                        "手工义务账期超出合同有效期间",
                    )
                cursor = start
                for schedule in sorted(schedules, key=lambda row: row.stage_start):
                    if (
                        schedule.payment_cycle == "custom"
                        and schedule.stage_start <= cursor <= schedule.stage_end
                    ):
                        cursor = min(end, schedule.stage_end) + timedelta(days=1)
                if cursor <= end:
                    raise rent_error(
                        "RENT_LEDGER_MANUAL_ENTRY_NOT_ALLOWED",
                        "手工义务仅适用于自定义账期",
                    )
            entry_type = (
                "upstream_payable"
                if isinstance(contract, UpstreamContract)
                else (
                    "terminal_receivable"
                    if contract.contract_mode == "sublease"
                    else "owner_receipt_expected"
                )
            )
            correlation_id = str(uuid4())
            entry = RentLedgerEntry(  # type: ignore[call-arg]
                id=str(uuid4()),
                entry_type=entry_type,
                contract_kind=request.contract_kind,
                contract_id=request.contract_id,
                period=start.strftime("%Y-%m"),
                period_start=start,
                period_end=end,
                due_date=due,
                due_amount=request.amount,
                currency="CNY",
                origin=request.origin,
                basis_note=request.basis_note,
                locked_source={
                    "contract_version": contract.version,
                    "contract": contract_snapshot(contract),
                    "rent_schedules": [contract_snapshot(stage) for stage in schedules],
                    "lifecycle_event_id": early.id
                    if request.origin == "clawback" and early is not None
                    else None,
                },
                version=1,
            )
            await asset_ledger_repository.add_entry(db, entry=entry)
            await db.flush()
            await audit(
                db,
                kind=request.contract_kind,
                contract_id=request.contract_id,
                action="manual_rent_created",
                actor_id=actor_id,
                correlation_id=correlation_id,
                before={},
                after={"entry_id": entry.id, "amount": str(entry.due_amount)},
                reason=request.basis_note,
            )
            result = RentEntryCommandResponse(entry_id=entry.id, version=entry.version)
            await receipt(
                db,
                actor_id=actor_id,
                key=idempotency_key,
                action=action,
                request_fingerprint=request_fingerprint,
                result=result,
            )
            await db.commit()
            return result
        except IntegrityError:
            await db.rollback()
            await scoped_contract(
                db,
                kind=request.contract_kind,
                contract_id=request.contract_id,
                scope=scope,
            )
            existing = await asset_contract_repository.get_write_receipt(
                db, actor_id=actor_id, idempotency_key=idempotency_key
            )
            if existing is None:
                raise
            return RentEntryCommandResponse.model_validate(
                replay_receipt(existing, request_fingerprint)
            )
        except Exception:
            await db.rollback()
            raise

    async def void_manual(
        self,
        db: AsyncSession,
        *,
        entry_id: str,
        request: VoidRentEntryRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> RentEntryCommandResponse:
        require_scope(scope, actor_id)
        if request.reason.strip() == "":
            raise rent_error("REVERSAL_REASON_REQUIRED", "作废原因必填", status=422)
        action = "void_manual_rent_entry"
        request_fingerprint = fingerprint(action, entry_id, request)
        try:
            entry = await self._entry(db, entry_id=entry_id, scope=scope, lock=True)
            existing = await asset_contract_repository.get_write_receipt(
                db, actor_id=actor_id, idempotency_key=idempotency_key
            )
            if existing is not None:
                return RentEntryCommandResponse.model_validate(
                    replay_receipt(existing, request_fingerprint)
                )
            check_version(entry.id, entry.version, request.expected_version)
            if entry.origin == "generated" or entry.voided_at is not None:
                raise rent_error(
                    "RENT_LEDGER_MANUAL_ENTRY_NOT_ALLOWED", "该义务不能手工作废"
                )
            records = await asset_ledger_repository.list_records(
                db, entry_ids=(entry.id,)
            )
            if effective_paid(records) > 0:
                raise rent_error("RENT_LEDGER_ENTRY_LOCKED", "存在有效登记，不能作废")
            correlation_id = str(uuid4())
            entry.voided_at = datetime.now(UTC)
            entry.void_correlation_id = correlation_id
            await db.flush()
            await audit(
                db,
                kind=entry.contract_kind,
                contract_id=entry.contract_id,
                action="manual_rent_voided",
                actor_id=actor_id,
                correlation_id=correlation_id,
                before={"entry_id": entry.id, "voided": False},
                after={"entry_id": entry.id, "voided": True},
                reason=request.reason,
            )
            result = RentEntryCommandResponse(entry_id=entry.id, version=entry.version)
            await receipt(
                db,
                actor_id=actor_id,
                key=idempotency_key,
                action=action,
                request_fingerprint=request_fingerprint,
                result=result,
            )
            await db.commit()
            return result
        except IntegrityError:
            await db.rollback()
            await self._entry(db, entry_id=entry_id, scope=scope, lock=False)
            existing = await asset_contract_repository.get_write_receipt(
                db, actor_id=actor_id, idempotency_key=idempotency_key
            )
            if existing is None:
                raise
            return RentEntryCommandResponse.model_validate(
                replay_receipt(existing, request_fingerprint)
            )
        except Exception:
            await db.rollback()
            raise


rent_payment_command_service = RentPaymentCommandService()
