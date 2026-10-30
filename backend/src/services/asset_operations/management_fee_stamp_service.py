"""Bind an already stored, statement-owned stamped attachment atomically."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from ...core.exception_handler import ResourceNotFoundError
from ...crud.attachment import attachment_crud
from ...crud.business_change_event import business_change_repository
from ...crud.management_fee_statement import management_fee_statement_repository
from ...models.business_change_event import BusinessChangeEvent
from ...schemas.management_fee_commands import (
    ManagementFeeStampRequest,
    ManagementFeeStampResponse,
)
from ..party_scope_resolver import EffectivePartyScope
from .errors import AssetOperationsVersionConflictError
from .management_fee_query_service import management_fee_query_service
from .rent_command_support import check_version, require_scope
from .rent_errors import rent_error


class ManagementFeeStampService:
    async def bind_document(
        self,
        db: AsyncSession,
        *,
        statement_id: str,
        request: ManagementFeeStampRequest,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> ManagementFeeStampResponse:
        require_scope(scope, actor_id)
        try:
            detail = await management_fee_query_service.detail(
                db, statement_id=statement_id, scope=scope
            )
            await management_fee_statement_repository.lock_owner(
                db, owner_party_id=detail.statement.owner_party_id
            )
            statement = await management_fee_statement_repository.get_statement(
                db, statement_id=statement_id, for_update=True
            )
            if statement is None:
                raise ResourceNotFoundError("ManagementFeeStatement", statement_id)
            if statement.status is not None:
                raise rent_error(
                    "MANAGEMENT_FEE_STATEMENT_LOCKED", "已确认或已更正的对账单不可修改"
                )
            check_version(statement.id, statement.version, request.expected_version)
            detail = await management_fee_query_service.detail(
                db, statement_id=statement_id, scope=scope
            )
            document = await attachment_crud.get_for_owner(
                db,
                attachment_id=request.document_id,
                owner_type="management_fee_statement",
                owner_id=statement_id,
            )
            if document is None:
                raise ResourceNotFoundError("Attachment", request.document_id)
            previous = statement.stamped_document_id
            statement.stamped_document_id = document.id
            statement.version += 1
            await db.flush()
            await business_change_repository.add(
                db,
                event=BusinessChangeEvent(  # type: ignore[call-arg]
                    id=str(uuid4()),
                    target_type="management_fee_statement",
                    target_id=statement_id,
                    action="management_fee_stamp_bound",
                    actor_id=actor_id,
                    before={"stamped_document_id": previous},
                    after={"stamped_document_id": document.id},
                    occurred_at=datetime.now(UTC),
                    correlation_id=str(uuid4()),
                ),
            )
            if detail.projection is None:
                raise rent_error("MANAGEMENT_FEE_STATEMENT_LOCKED", "对账单已锁定")
            result = ManagementFeeStampResponse(
                statement_id=statement_id,
                version=statement.version,
                document_id=document.id,
                fee_amount=detail.projection.fee_amount,
            )
            await db.commit()
            return result
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


management_fee_stamp_service = ManagementFeeStampService()
