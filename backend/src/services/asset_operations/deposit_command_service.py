"""Append-only deposit commands; rent offsets share the caller's transaction."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from ...core.exception_handler import ResourceNotFoundError
from ...crud.asset_contract import asset_contract_repository
from ...crud.asset_ledger import asset_ledger_repository
from ...crud.asset_unit import asset_unit_repository
from ...crud.attachment import attachment_crud
from ...crud.deposit_ledger import deposit_ledger_repository
from ...crud.deposit_pairs import deposit_pair_repository
from ...crud.deposit_queries import deposit_query_repository
from ...crud.rent_commands import rent_command_repository
from ...models.asset_ledger import RentLedgerEntry, RentPaymentRecord
from ...models.deposit_ledger import DepositLedgerEntry, DepositRecord
from ...schemas.deposit_commands import (
    DepositRecordCommandResponse,
    DepositRecordRequest,
    DepositReversalRequest,
)
from ...services.party_scope_resolver import EffectivePartyScope
from .deposit_query_service import active_deposit_events, deposit_query_service
from .errors import (
    AssetOperationsIdempotencyConflictError,
    AssetOperationsVersionConflictError,
)
from .rent_command_support import audit, check_version, require_scope, scoped_contract
from .rent_errors import rent_error
from .rent_ledger_projections import effective_paid
from .rent_ledger_query_service import business_today
from .rent_obligation_service import rent_obligation_service


def validate_deposit_record(
    *,
    kind: str,
    collector: str,
    record_type: str,
    amount: Decimal,
    held: Decimal,
    outstanding: Decimal,
    direction: str,
    ended: bool,
    read_only: bool,
    reason: str,
    offset_id: str | None,
) -> None:
    if read_only:
        raise rent_error("DEPOSIT_ENTRY_CARRIED_FORWARD", "押金已随续签结转，只能查看")
    allowed = (
        {"pay", "recover", "forfeit"}
        if kind == "upstream"
        else (
            {"collect", "refund", "deduct", "forfeit"}
            if collector == "operator"
            else {"owner_reported_collect", "owner_reported_refund", "forfeit"}
        )
    )
    if record_type not in allowed:
        raise rent_error(
            "DEPOSIT_RECORD_TYPE_MISMATCH", "登记类型与押金收取方不匹配", status=422
        )
    if record_type == "forfeit" and reason.strip() == "":
        raise rent_error("FORFEIT_REASON_REQUIRED", "没收原因必填", status=422)
    if record_type in {"deduct", "forfeit"} and not ended:
        raise rent_error("DEPOSIT_OFFSET_NOT_ALLOWED", "合同押金尚未进入结算阶段")
    if (record_type == "deduct") != (offset_id is not None):
        raise rent_error("DEPOSIT_OFFSET_TARGET_INVALID", "抵扣必须选择有效租金义务")
    income = record_type in {"collect", "owner_reported_collect", "pay"}
    limit = (
        outstanding
        if income and direction in {"receivable", "payable"}
        else (Decimal("0") if income else held)
    )
    if amount > limit:
        raise rent_error(
            "DEPOSIT_AMOUNT_EXCEEDS_REMAINING", "登记金额超过剩余押金义务或持有金额"
        )


class DepositCommandService:
    async def _lock(
        self,
        db: AsyncSession,
        *,
        entry_id: str,
        scope: EffectivePartyScope,
        offset_id: str | None = None,
    ) -> tuple[DepositLedgerEntry, RentLedgerEntry | None]:
        entry = await deposit_ledger_repository.get_entry(db, entry_id=entry_id)
        if entry is None:
            raise ResourceNotFoundError("DepositLedgerEntry", entry_id)
        targets = {(entry.contract_kind, entry.contract_id)}
        rent = None
        if offset_id is not None:
            rent = await asset_ledger_repository.get_entry(db, entry_id=offset_id)
            if rent is None:
                raise ResourceNotFoundError("RentLedgerEntry", offset_id)
            targets.add((rent.contract_kind, rent.contract_id))
        # All units precede all contracts, including a renewal ancestor's contract.
        unit_ids: set[str] = set()
        for kind, contract_id in sorted(targets):
            await scoped_contract(db, kind=kind, contract_id=contract_id, scope=scope)
            coverages = (
                await asset_contract_repository.list_upstream_coverages(
                    db, contract_id=contract_id
                )
                if kind == "upstream"
                else await asset_contract_repository.list_terminal_coverages(
                    db, contract_id=contract_id
                )
            )
            unit_ids.update(row.asset_unit_id for row in coverages)
        units = await asset_unit_repository.lock_for_write(
            db, unit_ids=sorted(unit_ids), scope=scope
        )
        if {unit.id for unit in units} != unit_ids:
            raise ResourceNotFoundError("Contract", entry.contract_id)
        for kind, contract_id in sorted(targets):
            getter = (
                asset_contract_repository.get_upstream
                if kind == "upstream"
                else asset_contract_repository.get_terminal
            )
            if (
                await getter(db, contract_id=contract_id, scope=scope, for_update=True)
                is None
            ):
                raise ResourceNotFoundError("Contract", contract_id)
        if offset_id is not None:
            rent = await asset_ledger_repository.get_entry(
                db, entry_id=offset_id, for_update=True
            )
        locked = await deposit_ledger_repository.get_entry(
            db, entry_id=entry_id, for_update=True
        )
        if locked is None:
            raise ResourceNotFoundError("DepositLedgerEntry", entry_id)
        return locked, rent

    @staticmethod
    def _response(
        record: DepositRecord, entry: DepositLedgerEntry, *, idempotent: bool = False
    ) -> DepositRecordCommandResponse:
        from ...schemas.deposit_commands import DepositRecordResponse

        return DepositRecordCommandResponse(
            **DepositRecordResponse.model_validate(record).model_dump(),
            version=entry.version,
            idempotent=idempotent,
        )

    async def _validate_target(
        self,
        db: AsyncSession,
        *,
        entry: DepositLedgerEntry,
        rent: RentLedgerEntry,
        amount: Decimal,
        scope: EffectivePartyScope,
    ) -> None:
        facts = await deposit_query_repository.load_facts(
            db,
            scope=scope,
            contract_kind=entry.contract_kind,
            contract_id=entry.contract_id,
        )
        contracts = {row.id: row for row in facts.contracts}
        events = active_deposit_events(facts.events)
        allowed = {entry.contract_id}
        current = contracts.get(entry.contract_id)
        while current is not None and current.renewed_from_id is not None:
            parent = current.renewed_from_id
            if parent in allowed or not any(
                e.contract_id == parent
                and e.event_type == "renewed"
                and e.successor_contract_id == current.id
                for e in events
            ):
                break
            allowed.add(parent)
            current = contracts.get(parent)
        if (
            entry.contract_kind != "terminal"
            or rent.contract_kind != "terminal"
            or rent.contract_id not in allowed
            or rent.entry_type != "terminal_receivable"
            or rent.voided_at is not None
        ):
            raise rent_error(
                "DEPOSIT_OFFSET_TARGET_INVALID",
                "只能抵扣本合同或有效续签前序合同的未结租金",
            )
        records = await asset_ledger_repository.list_records(db, entry_ids=(rent.id,))
        if amount > rent.due_amount - effective_paid(records):
            raise rent_error("DEPOSIT_OFFSET_TARGET_INVALID", "抵扣金额超过剩余租金")

    async def register(
        self,
        db: AsyncSession,
        *,
        entry_id: str,
        request: DepositRecordRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
        commit: bool = True,
        lifecycle_event_id: str | None = None,
    ) -> DepositRecordCommandResponse:
        require_scope(scope, actor_id)
        try:
            entry, rent = await self._lock(
                db,
                entry_id=entry_id,
                scope=scope,
                offset_id=request.offset_ledger_entry_id,
            )
            existing = await deposit_ledger_repository.get_record_by_idempotency(
                db, key=idempotency_key
            )
            if existing is not None:
                self._check_replay(
                    existing,
                    entry_id=entry_id,
                    actor_id=actor_id,
                    request=request,
                    lifecycle_event_id=lifecycle_event_id,
                )
                return self._response(existing, entry, idempotent=True)
            check_version(entry.id, entry.version, request.expected_version)
            view = await deposit_query_service.get(db, entry_id=entry.id, scope=scope)
            validate_deposit_record(
                kind=entry.contract_kind,
                collector=entry.collector,
                record_type=request.record_type,
                amount=request.amount,
                held=view.held_amount,
                outstanding=view.outstanding_amount,
                direction=view.direction,
                ended=view.ended,
                read_only=view.read_only,
                reason=request.reason,
                offset_id=request.offset_ledger_entry_id,
            )
            if lifecycle_event_id is not None and request.record_type != "deduct":
                raise rent_error(
                    "DEPOSIT_RECORD_TYPE_MISMATCH", "结算事件只关联押金抵扣", status=422
                )
            if rent is not None:
                await self._validate_target(
                    db, entry=entry, rent=rent, amount=request.amount, scope=scope
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
                        owner_type="deposit_ledger_entry",
                        owner_id=entry.id,
                    )
                if document is None:
                    raise ResourceNotFoundError("Attachment", request.document_id)
            record = DepositRecord(  # type: ignore[call-arg]
                id=str(uuid4()),
                deposit_entry_id=entry.id,
                record_type=request.record_type,
                amount=request.amount,
                occurred_on=request.occurred_on,
                document_id=request.document_id,
                offset_ledger_entry_id=request.offset_ledger_entry_id,
                lifecycle_event_id=lifecycle_event_id,
                reason=request.reason,
                created_by=actor_id,
                created_at=datetime.now(UTC),
                idempotency_key=idempotency_key,
            )
            await deposit_ledger_repository.add_record(db, record=record)
            await db.flush()
            if rent is not None:
                paired = RentPaymentRecord(  # type: ignore[call-arg]
                    id=str(uuid4()),
                    ledger_entry_id=rent.id,
                    record_type="deposit_offset",
                    amount=request.amount,
                    occurred_on=request.occurred_on,
                    paired_deposit_record_id=record.id,
                    created_by=actor_id,
                    created_at=datetime.now(UTC),
                    idempotency_key=f"deposit:{record.id}",
                )
                await asset_ledger_repository.add_record(db, record=paired)
                rent.version += 1
            entry.version += 1
            await db.flush()
            await audit(
                db,
                kind=entry.contract_kind,
                contract_id=entry.contract_id,
                action="deposit_record_registered",
                actor_id=actor_id,
                correlation_id=record.id,
                before={"held_amount": str(view.held_amount)},
                after={
                    "record_id": record.id,
                    "record_type": record.record_type,
                    "amount": str(record.amount),
                },
                reason=request.reason,
            )
            result = self._response(record, entry)
            if commit:
                await db.commit()
            return result
        except IntegrityError:
            if not commit:
                raise
            await db.rollback()
            existing = await deposit_ledger_repository.get_record_by_idempotency(
                db, key=idempotency_key
            )
            if existing is None:
                raise
            entry, _ = await self._lock(db, entry_id=entry_id, scope=scope)
            self._check_replay(
                existing,
                entry_id=entry_id,
                actor_id=actor_id,
                request=request,
                lifecycle_event_id=lifecycle_event_id,
            )
            return self._response(existing, entry, idempotent=True)
        except StaleDataError as error:
            if commit:
                await db.rollback()
            raise AssetOperationsVersionConflictError(
                unit_id=entry_id,
                expected_version=request.expected_version,
                actual_version=None,
            ) from error
        except Exception:
            if commit:
                await db.rollback()
            raise

    @staticmethod
    def _check_replay(
        record: DepositRecord,
        *,
        entry_id: str,
        actor_id: str,
        request: DepositRecordRequest,
        lifecycle_event_id: str | None,
    ) -> None:
        if (
            record.deposit_entry_id != entry_id
            or record.created_by != actor_id
            or record.lifecycle_event_id != lifecycle_event_id
            or any(
                getattr(record, field) != getattr(request, field)
                for field in (
                    "record_type",
                    "amount",
                    "occurred_on",
                    "document_id",
                    "offset_ledger_entry_id",
                    "reason",
                )
            )
        ):
            raise AssetOperationsIdempotencyConflictError()

    async def reverse(
        self,
        db: AsyncSession,
        *,
        record_id: str,
        request: DepositReversalRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
        commit: bool = True,
    ) -> DepositRecordCommandResponse:
        require_scope(scope, actor_id)
        if request.reason.strip() == "":
            raise rent_error("REVERSAL_REASON_REQUIRED", "撤销原因必填", status=422)
        try:
            original = await deposit_ledger_repository.get_record(
                db, record_id=record_id
            )
            if original is None:
                raise ResourceNotFoundError("DepositRecord", record_id)
            entry, rent = await self._lock(
                db,
                entry_id=original.deposit_entry_id,
                scope=scope,
                offset_id=original.offset_ledger_entry_id,
            )
            existing = await deposit_ledger_repository.get_record_by_idempotency(
                db, key=idempotency_key
            )
            if existing is not None:
                if (
                    existing.deposit_entry_id != entry.id
                    or existing.created_by != actor_id
                    or existing.reverses_record_id != record_id
                    or existing.reason != request.reason
                ):
                    raise AssetOperationsIdempotencyConflictError()
                return self._response(existing, entry, idempotent=True)
            check_version(entry.id, entry.version, request.expected_version)
            view = await deposit_query_service.get(db, entry_id=entry.id, scope=scope)
            if view.read_only:
                raise rent_error(
                    "DEPOSIT_ENTRY_CARRIED_FORWARD", "押金已随续签结转，只能查看"
                )
            if (
                original.record_type == "reversal"
                or await deposit_ledger_repository.find_reversal(
                    db, record_id=record_id
                )
                is not None
            ):
                raise rent_error("DEPOSIT_RECORD_ALREADY_REVERSED", "该押金登记已撤销")
            if (
                original.record_type in {"collect", "owner_reported_collect", "pay"}
                and original.amount > view.held_amount
            ):
                raise rent_error(
                    "DEPOSIT_AMOUNT_EXCEEDS_REMAINING", "押金已使用，须先撤销对应支出"
                )
            record = DepositRecord(  # type: ignore[call-arg]
                id=str(uuid4()),
                deposit_entry_id=entry.id,
                record_type="reversal",
                amount=original.amount,
                occurred_on=business_today(),
                reverses_record_id=original.id,
                reason=request.reason,
                created_by=actor_id,
                created_at=datetime.now(UTC),
                idempotency_key=idempotency_key,
            )
            await deposit_ledger_repository.add_record(db, record=record)
            if rent is not None:
                pair = await deposit_pair_repository.rent_record(
                    db, deposit_record_id=original.id
                )
                if pair is None:
                    raise rent_error(
                        "DEPOSIT_OFFSET_TARGET_INVALID", "押金抵扣缺少租金登记对账记录"
                    )
                if (
                    await rent_command_repository.find_reversal(db, record_id=pair.id)
                    is not None
                ):
                    raise rent_error(
                        "DEPOSIT_RECORD_ALREADY_REVERSED", "成对租金登记已撤销"
                    )
                await asset_ledger_repository.add_record(
                    db,
                    record=RentPaymentRecord(  # type: ignore[call-arg]
                        id=str(uuid4()),
                        ledger_entry_id=rent.id,
                        record_type="reversal",
                        amount=pair.amount,
                        occurred_on=business_today(),
                        reverses_record_id=pair.id,
                        reason=request.reason,
                        created_by=actor_id,
                        created_at=datetime.now(UTC),
                        idempotency_key=f"deposit:{record.id}",
                    ),
                )
                rent.version += 1
            entry.version += 1
            await db.flush()
            if rent is not None:
                await rent_obligation_service.replan(
                    db,
                    contract_kind=rent.contract_kind,
                    contract_id=rent.contract_id,
                    actor_id=actor_id,
                    correlation_id=record.id,
                )
            await audit(
                db,
                kind=entry.contract_kind,
                contract_id=entry.contract_id,
                action="deposit_record_reversed",
                actor_id=actor_id,
                correlation_id=record.id,
                before={"record_id": original.id},
                after={"record_id": record.id},
                reason=request.reason,
            )
            result = self._response(record, entry)
            if commit:
                await db.commit()
            return result
        except IntegrityError:
            if not commit:
                raise
            await db.rollback()
            existing = await deposit_ledger_repository.get_record_by_idempotency(
                db, key=idempotency_key
            )
            if existing is None:
                raise
            original = await deposit_ledger_repository.get_record(
                db, record_id=record_id
            )
            if original is None:
                raise ResourceNotFoundError("DepositRecord", record_id)
            entry, _ = await self._lock(
                db, entry_id=original.deposit_entry_id, scope=scope
            )
            if (
                existing.deposit_entry_id != entry.id
                or existing.created_by != actor_id
                or existing.reverses_record_id != record_id
                or existing.reason != request.reason
            ):
                raise AssetOperationsIdempotencyConflictError()
            return self._response(existing, entry, idempotent=True)
        except StaleDataError as error:
            if commit:
                await db.rollback()
            raise AssetOperationsVersionConflictError(
                unit_id=record_id,
                expected_version=request.expected_version,
                actual_version=None,
            ) from error
        except Exception:
            if commit:
                await db.rollback()
            raise


deposit_command_service = DepositCommandService()
