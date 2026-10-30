"""Management fee deferrals commit their mark, audit and receipt together."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from ...core.exception_handler import ResourceNotFoundError
from ...crud.asset_contract import asset_contract_repository
from ...crud.management_fee_deferral import management_fee_deferral_repository
from ...crud.management_fee_statement import management_fee_statement_repository
from ...models.management_fee_deferral import ManagementFeeDeferral
from ...schemas.management_fee_commands import (
    ManagementFeeCommandResponse,
    ManagementFeeDeferralRequest,
)
from ..party_scope_resolver import EffectivePartyScope
from .errors import AssetOperationsVersionConflictError
from .management_fee_query_service import management_fee_query_service
from .rent_command_support import (
    audit,
    check_version,
    fingerprint,
    receipt,
    replay_receipt,
    require_scope,
)
from .rent_errors import rent_error


class ManagementFeeCommandService:
    async def defer_line(
        self,
        db: AsyncSession,
        *,
        statement_id: str,
        request: ManagementFeeDeferralRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> ManagementFeeCommandResponse:
        require_scope(scope, actor_id)
        if request.reason.strip() == "":
            raise rent_error("DEFERRAL_REASON_REQUIRED", "顺延原因必填", status=422)
        action = "defer_management_fee_line"
        request_fingerprint = fingerprint(action, statement_id, request)
        try:
            detail = await management_fee_query_service.detail(
                db, statement_id=statement_id, scope=scope
            )
            # This command never locks contracts after owner/statement locks.
            # Rent writers serialize on the same owner after their entry locks.
            await management_fee_statement_repository.lock_owner(
                db, owner_party_id=detail.statement.owner_party_id
            )
            statement = await management_fee_statement_repository.get_statement(
                db, statement_id=statement_id, for_update=True
            )
            if statement is None:
                raise ResourceNotFoundError("ManagementFeeStatement", statement_id)
            existing = await asset_contract_repository.get_write_receipt(
                db, actor_id=actor_id, idempotency_key=idempotency_key
            )
            if existing is not None:
                return ManagementFeeCommandResponse.model_validate(
                    replay_receipt(existing, request_fingerprint)
                )
            check_version(statement.id, statement.version, request.expected_version)
            if statement.status is not None:
                raise rent_error(
                    "MANAGEMENT_FEE_STATEMENT_LOCKED", "已确认或已更正的对账单不可修改"
                )
            detail = await management_fee_query_service.detail(
                db, statement_id=statement_id, scope=scope
            )
            projection = detail.projection
            line = (
                next(
                    (
                        row
                        for row in projection.lines
                        if row.rent_ledger_entry_id == request.rent_ledger_entry_id
                    ),
                    None,
                )
                if projection is not None
                else None
            )
            if line is None:
                raise ResourceNotFoundError(
                    "ManagementFeeStatementLine", request.rent_ledger_entry_id
                )
            if line.deferred_amount <= 0:
                raise rent_error(
                    "MANAGEMENT_FEE_LINE_NOT_DEFERRABLE", "该户已收足，无需顺延"
                )
            marks = await management_fee_deferral_repository.list_marks(
                db, statement_id=statement_id
            )
            if any(
                mark.rent_ledger_entry_id == request.rent_ledger_entry_id
                for mark in marks
            ):
                raise rent_error(
                    "MANAGEMENT_FEE_LINE_ALREADY_DEFERRED", "该户已标记顺延"
                )
            mark = ManagementFeeDeferral(  # type: ignore[call-arg]
                id=str(uuid4()),
                statement_id=statement_id,
                rent_ledger_entry_id=request.rent_ledger_entry_id,
                reason=request.reason,
                created_by=actor_id,
                created_at=datetime.now(UTC),
            )
            await management_fee_deferral_repository.add_mark(db, mark=mark)
            statement.version += 1
            await db.flush()
            await audit(
                db,
                kind="terminal",
                contract_id=line.terminal_contract_id,
                action=action,
                actor_id=actor_id,
                correlation_id=mark.id,
                before={},
                after={
                    "statement_id": statement_id,
                    "rent_ledger_entry_id": request.rent_ledger_entry_id,
                },
                reason=request.reason,
            )
            result = ManagementFeeCommandResponse(
                statement_id=statement_id, version=statement.version
            )
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
            # Replay only if the statement is still visible in scope after the
            # rollback; detail() raises otherwise.
            await management_fee_query_service.detail(
                db, statement_id=statement_id, scope=scope
            )
            existing = await asset_contract_repository.get_write_receipt(
                db, actor_id=actor_id, idempotency_key=idempotency_key
            )
            if existing is None:
                raise
            return ManagementFeeCommandResponse.model_validate(
                replay_receipt(existing, request_fingerprint)
            )
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


management_fee_command_service = ManagementFeeCommandService()
