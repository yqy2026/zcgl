"""Project monthly statements into a whole-owner annual fee matrix."""

from datetime import date
from decimal import Decimal
from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.management_fee_matrix import management_fee_matrix_repository
from ...schemas.management_fee_matrix import (
    ManagementFeeMatrixView,
    ManagementFeeMonthView,
    ManagementFeeOwnerRow,
)
from ..party_scope_resolver import EffectivePartyScope
from .management_fee_response_service import management_fee_response_service
from .rent_command_support import require_scope
from .rent_ledger_query_service import business_today


class ManagementFeeMatrixService:
    repository = management_fee_matrix_repository
    responses = management_fee_response_service

    async def matrix(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        year: int,
        today: date | None = None,
    ) -> ManagementFeeMatrixView:
        require_scope(scope, scope.user_id)
        current = today or business_today()
        facts = await self.repository.list_year(db, scope=scope, year=year)
        rows: dict[str, ManagementFeeOwnerRow] = {}
        for statement, owner_name in facts:
            # Reuse the detail boundary, including fresh whole-owner authorization
            # and immutable snapshots for confirmed statements.
            detail = await self.responses.get(
                db, statement_id=statement.id, scope=scope
            )
            row = rows.get(statement.owner_party_id)
            if row is None:
                row = ManagementFeeOwnerRow(
                    owner_party_id=statement.owner_party_id,
                    owner_name=owner_name,
                    months=[
                        ManagementFeeMonthView(
                            month=month,
                            status="upcoming"
                            if (year, month) > (current.year, current.month)
                            else "missing",
                        )
                        for month in range(1, 13)
                    ],
                    total_confirmed_amount=Decimal("0"),
                )
                rows[statement.owner_party_id] = row
            month = int(statement.period[5:7])
            row.months[month - 1] = ManagementFeeMonthView(
                month=month,
                statement_id=statement.id,
                # list_year() already filters superseded rows out of the year.
                status=cast(
                    Literal["collecting", "pending_stamp", "confirmed"],
                    detail.status,
                ),
                fee_amount=detail.fee_amount,
            )
            if detail.status == "confirmed":
                row.total_confirmed_amount += detail.fee_amount
        return ManagementFeeMatrixView(
            year=year,
            current_month=current.month if year == current.year else 0,
            rows=list(rows.values()),
            total_confirmed_amount=sum(
                (row.total_confirmed_amount for row in rows.values()), Decimal("0")
            ),
        )


management_fee_matrix_service = ManagementFeeMatrixService()
