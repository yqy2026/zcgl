"""Statement entry point for the existing owner-reported rent receipt command."""

from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.management_fee_commands import ManagementFeeOwnerReceiptRequest
from ...schemas.rent_commands import RentPaymentRequest, RentRecordCommandResponse
from ..party_scope_resolver import EffectivePartyScope
from .management_fee_query_service import management_fee_query_service
from .rent_command_support import require_scope
from .rent_payment_command_service import rent_payment_command_service


class ManagementFeeOwnerReceiptService:
    async def register(
        self,
        db: AsyncSession,
        *,
        statement_id: str,
        request: ManagementFeeOwnerReceiptRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> RentRecordCommandResponse:
        require_scope(scope, actor_id)
        await management_fee_query_service.detail(
            db, statement_id=statement_id, scope=scope
        )
        # Rent owns the transaction and rechecks statement membership after its
        # replay check and contract/entry/owner locks. A line that disappeared
        # after a successful write must not prevent the original receipt replay.
        return await rent_payment_command_service.register(
            db,
            entry_id=request.rent_ledger_entry_id,
            request=RentPaymentRequest(
                record_type="owner_reported_receipt",
                **request.model_dump(exclude={"rent_ledger_entry_id"}),
            ),
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key,
            management_fee_statement_id=statement_id,
        )


management_fee_owner_receipt_service = ManagementFeeOwnerReceiptService()
