"""Serialize whole-owner authorized fee projections and confirmation snapshots."""

import re
from decimal import Decimal
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import BaseBusinessError
from ...crud.management_fee_statement import management_fee_statement_repository
from ...schemas.management_fee_responses import (
    ManagementFeeLineResponse,
    ManagementFeeListResponse,
    ManagementFeeStatementResponse,
    ManagementFeeStatementStatus,
)
from ..party_scope_resolver import EffectivePartyScope
from .management_fee_query_service import management_fee_query_service
from .management_fee_rules import deadline_for
from .rent_command_support import require_scope


class ManagementFeeResponseService:
    async def get(
        self, db: AsyncSession, *, statement_id: str, scope: EffectivePartyScope
    ) -> ManagementFeeStatementResponse:
        detail = await management_fee_query_service.detail(
            db, statement_id=statement_id, scope=scope
        )
        row, projection = detail.statement, detail.projection
        identity: dict[str, Any] = {
            "id": row.id,
            "owner_party_id": row.owner_party_id,
            "period": row.period,
            "statement_number": row.statement_number,
            "version": row.version,
            "stamped_document_id": row.stamped_document_id,
            "confirmed_at": row.confirmed_at,
            "confirmed_by": row.confirmed_by,
            "predecessor_statement_id": row.predecessor_statement_id,
            "successor_statement_id": row.successor_statement_id,
        }
        if projection is not None:
            return ManagementFeeStatementResponse(
                **identity,
                status=projection.status,
                deadline=projection.deadline,
                upstream_contract_ids=list(projection.upstream_contract_ids),
                base_amount=projection.base_amount,
                fee_amount=projection.fee_amount,
                lines=[
                    ManagementFeeLineResponse.model_validate(line)
                    for line in projection.lines
                ],
                carried_waiting_hint=projection.carried_waiting_hint,
                upstream_missing_entry_ids=list(projection.upstream_missing_entry_ids),
                upstream_missing_warning=projection.upstream_missing_warning,
            )
        # Snapshot reads only happen for confirmed/superseded rows, whose status
        # and amounts were persisted at confirmation (see query service detail()).
        return ManagementFeeStatementResponse(
            **identity,
            status=cast(ManagementFeeStatementStatus, row.status),
            deadline=deadline_for(row.period),
            upstream_contract_ids=list(row.upstream_contract_ids or ()),
            base_amount=cast(Decimal, row.base_amount),
            fee_amount=cast(Decimal, row.fee_amount),
            lines=[
                ManagementFeeLineResponse.model_validate(line)
                for line in detail.snapshot_lines
            ],
            carried_waiting_hint=False,
            upstream_missing_entry_ids=[],
            upstream_missing_warning=None,
        )

    async def list(
        self, db: AsyncSession, *, period: str, scope: EffectivePartyScope
    ) -> ManagementFeeListResponse:
        require_scope(scope, scope.user_id)
        try:
            if re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", period) is None:
                raise ValueError("Invalid year-month")
            deadline_for(period)
        except ValueError as error:
            raise BaseBusinessError(
                message="月份格式无效", code="INVALID_PERIOD", status_code=400
            ) from error
        rows = await management_fee_statement_repository.list_for_period(
            db, period=period, scope=scope
        )
        items = [await self.get(db, statement_id=row.id, scope=scope) for row in rows]
        return ManagementFeeListResponse(items=items, total=len(items))


management_fee_response_service = ManagementFeeResponseService()
