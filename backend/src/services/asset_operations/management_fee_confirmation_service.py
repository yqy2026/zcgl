"""Atomic management fee confirmation snapshots and append-only corrections."""

from dataclasses import asdict
from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from ...core.exception_handler import ResourceNotFoundError
from ...crud.asset_contract import asset_contract_repository
from ...crud.business_change_event import business_change_repository
from ...crud.management_fee_statement import management_fee_statement_repository
from ...models.business_change_event import BusinessChangeEvent
from ...models.management_fee_statement import (
    ManagementFeeStatement,
    ManagementFeeStatementLine,
)
from ...schemas.management_fee_commands import (
    ManagementFeeCommandResponse,
    ManagementFeeConfirmationRequest,
    ManagementFeeSuccessorRequest,
    ManagementFeeSuccessorResponse,
)
from ..party_scope_resolver import EffectivePartyScope
from .errors import AssetOperationsVersionConflictError
from .management_fee_query_service import management_fee_query_service
from .rent_command_support import (
    check_version,
    fingerprint,
    receipt,
    replay_receipt,
    require_scope,
)
from .rent_errors import rent_error
from .rent_obligation_rules import add_months


class ManagementFeeConfirmationService:
    async def confirm(
        self,
        db: AsyncSession,
        *,
        statement_id: str,
        request: ManagementFeeConfirmationRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> ManagementFeeCommandResponse:
        return await self._execute(
            db,
            statement_id=statement_id,
            request=request,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key,
            correcting=False,
            reason=None,
        )

    async def supersede(
        self,
        db: AsyncSession,
        *,
        statement_id: str,
        request: ManagementFeeSuccessorRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> ManagementFeeSuccessorResponse:
        if request.reason.strip() == "":
            raise rent_error("CORRECTION_REASON_REQUIRED", "更正原因必填", status=422)
        result = await self._execute(
            db,
            statement_id=statement_id,
            request=request,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key,
            correcting=True,
            reason=request.reason,
        )
        return ManagementFeeSuccessorResponse.model_validate(result.model_dump())

    async def _execute(
        self,
        db: AsyncSession,
        *,
        statement_id: str,
        request: ManagementFeeConfirmationRequest | ManagementFeeSuccessorRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
        correcting: bool,
        reason: str | None,
    ) -> ManagementFeeCommandResponse:
        require_scope(scope, actor_id)
        action = (
            "supersede_management_fee_statement"
            if correcting
            else "confirm_management_fee_statement"
        )
        digest = fingerprint(action, statement_id, request)
        response_type = (
            ManagementFeeSuccessorResponse
            if correcting
            else ManagementFeeCommandResponse
        )
        try:
            detail = await management_fee_query_service.detail(
                db, statement_id=statement_id, scope=scope
            )
            owner = detail.statement.owner_party_id
            await management_fee_statement_repository.lock_owner(
                db, owner_party_id=owner
            )
            rows = await management_fee_statement_repository.list_statements(
                db, owner_party_id=owner, for_update=True
            )
            statement = next((row for row in rows if row.id == statement_id), None)
            if statement is None:
                raise ResourceNotFoundError("ManagementFeeStatement", statement_id)
            saved = await asset_contract_repository.get_write_receipt(
                db, actor_id=actor_id, idempotency_key=idempotency_key
            )
            if saved is not None:
                return response_type.model_validate(replay_receipt(saved, digest))
            check_version(statement_id, statement.version, request.expected_version)
            # Only owner and statement rows are locked; no contract lock is
            # acquired after owner. All fact writers serialize on this owner.
            detail = await management_fee_query_service.detail(
                db, statement_id=statement_id, scope=scope
            )
            event_id = str(uuid4())
            now = datetime.now(UTC)
            result: ManagementFeeCommandResponse
            if correcting:
                confirmed = [row for row in rows if row.status == "confirmed"]
                if statement.status != "confirmed" or any(
                    row.period > statement.period for row in confirmed
                ):
                    raise rent_error(
                        "MANAGEMENT_FEE_SEQUENCE_CONFLICT", "只能更正最近一张已确认单"
                    )
                statement.status = "superseded"
                statement.version += 1
                await db.flush()  # Release the active owner/month unique key.
                successor_id = str(uuid4())
                successor = ManagementFeeStatement(  # type: ignore[call-arg]
                    id=successor_id,
                    owner_party_id=owner,
                    period=statement.period,
                    statement_number=f"MF-{statement.period}-{successor_id}",
                    predecessor_statement_id=statement.id,
                    version=1,
                )
                await management_fee_statement_repository.add_statement(
                    db, statement=successor
                )
                await db.flush()  # Self-FK target must exist before linking back.
                statement.successor_statement_id = successor.id
                for row in rows:
                    if row.status is None and row.period > statement.period:
                        row.version += 1
                result = ManagementFeeSuccessorResponse(
                    statement_id=statement.id,
                    successor_statement_id=successor.id,
                    version=statement.version,
                )
            else:
                if statement.status is not None:
                    raise rent_error(
                        "MANAGEMENT_FEE_STATEMENT_LOCKED",
                        "已确认或已更正的对账单不可修改",
                    )
                if statement.stamped_document_id is None:
                    raise rent_error(
                        "STAMPED_DOCUMENT_REQUIRED", "请先上传盖章件", status=422
                    )
                if any(
                    row.status is None and row.period < statement.period for row in rows
                ):
                    raise rent_error(
                        "MANAGEMENT_FEE_SEQUENCE_CONFLICT", "请先确认更早月份的对账单"
                    )
                projection = detail.projection
                if projection is None or any(
                    not line.processed for line in projection.lines
                ):
                    raise rent_error(
                        "MANAGEMENT_FEE_LINES_UNRESOLVED", "仍有未处理的到账明细"
                    )
                following = add_months(
                    date.fromisoformat(f"{statement.period}-01"), 1
                ).strftime("%Y-%m")
                if any(line.deferred_amount > 0 for line in projection.lines) and any(
                    row.period == following and row.status == "confirmed"
                    for row in rows
                ):
                    raise rent_error(
                        "MANAGEMENT_FEE_SEQUENCE_CONFLICT",
                        "请先更正后续已确认单再带出顺延余额",
                    )
                snapshots = []
                for line in projection.lines:
                    values = asdict(line)
                    values.pop("processed")
                    for field in ("asset_unit_ids", "counted_record_ids"):
                        values[field] = list(values[field])
                    snapshots.append(
                        ManagementFeeStatementLine(  # type: ignore[call-arg]
                            id=str(uuid4()), statement_id=statement.id, **values
                        )
                    )
                await management_fee_statement_repository.add_lines(db, lines=snapshots)
                statement.base_amount = projection.base_amount
                statement.fee_amount = projection.fee_amount
                statement.upstream_contract_ids = list(projection.upstream_contract_ids)
                statement.confirmed_at, statement.confirmed_by = now, actor_id
                statement.status = "confirmed"
                statement.version += 1
                await db.flush()
                if any(line.deferred_amount > 0 for line in projection.lines):
                    next_row = next(
                        (
                            row
                            for row in rows
                            if row.period == following and row.status is None
                        ),
                        None,
                    )
                    if next_row is None:
                        await management_fee_statement_repository.ensure_draft(
                            db, owner_party_id=owner, period=following
                        )
                    else:
                        next_row.version += 1
                result = ManagementFeeCommandResponse(
                    statement_id=statement.id, version=statement.version
                )
            await db.flush()
            result.version = statement.version
            await business_change_repository.add(
                db,
                event=BusinessChangeEvent(  # type: ignore[call-arg]
                    id=event_id,
                    target_type="management_fee_statement",
                    target_id=statement.id,
                    action=action,
                    before={"version": request.expected_version},
                    after=result.model_dump(mode="json"),
                    actor_id=actor_id,
                    reason=reason,
                    correlation_id=event_id,
                    occurred_at=now,
                ),
            )
            await receipt(
                db,
                actor_id=actor_id,
                key=idempotency_key,
                action=action,
                request_fingerprint=digest,
                result=result,
            )
            await db.commit()
            return result
        except IntegrityError:
            await db.rollback()
            # Replay only if the statement is still visible in scope after the
            # rollback; detail() raises otherwise.
            await management_fee_query_service.detail(
                db, statement_id=statement_id, scope=scope
            )
            saved = await asset_contract_repository.get_write_receipt(
                db, actor_id=actor_id, idempotency_key=idempotency_key
            )
            if saved is None:
                raise
            return response_type.model_validate(replay_receipt(saved, digest))
        except StaleDataError as error:
            await db.rollback()
            raise AssetOperationsVersionConflictError(
                unit_id=statement_id,
                expected_version=request.expected_version,
                actual_version=None,
            ) from error
        except Exception:
            await db.rollback()
            raise


management_fee_confirmation_service = ManagementFeeConfirmationService()
