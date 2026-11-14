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
from .management_fee_query_service import management_fee_query_service
from .rent_command_support import require_scope
from .rent_ledger_query_service import business_today


class ManagementFeeMatrixService:
    repository = management_fee_matrix_repository
    query_service = management_fee_query_service

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
        # One batched read: whole-owner authorization, owner facts and marks
        # resolve once for the year instead of per statement.
        details = await self.query_service.details(
            db, statements=tuple(row for row, _ in facts), scope=scope
        )
        rows: dict[str, ManagementFeeOwnerRow] = {}
        for statement, owner_name in facts:
            detail = details[statement.id]
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
                # Confirmed rows persist non-null amounts (snapshot CHECK).
                row.total_confirmed_amount += cast(Decimal, detail.fee_amount)
        return ManagementFeeMatrixView(
            year=year,
            current_month=current.month if year == current.year else 0,
            rows=list(rows.values()),
            total_confirmed_amount=sum(
                (row.total_confirmed_amount for row in rows.values()), Decimal("0")
            ),
        )


management_fee_matrix_service = ManagementFeeMatrixService()
