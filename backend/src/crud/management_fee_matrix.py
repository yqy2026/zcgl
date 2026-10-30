"""Batch identities and owner labels for the annual management fee ledger."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.management_fee_statement import ManagementFeeStatement
from ..models.party import Party
from ..services.party_scope_resolver import EffectivePartyScope
from .business_change_event import fee_statement_ids_for_scope


class ManagementFeeMatrixRepository:
    async def list_year(
        self, db: AsyncSession, *, scope: EffectivePartyScope, year: int
    ) -> tuple[tuple[ManagementFeeStatement, str], ...]:
        query = (
            select(ManagementFeeStatement, Party.name)
            .join(Party, Party.id == ManagementFeeStatement.owner_party_id)
            .where(
                ManagementFeeStatement.period >= f"{year:04d}-01",
                ManagementFeeStatement.period <= f"{year:04d}-12",
                ManagementFeeStatement.id.in_(fee_statement_ids_for_scope(scope)),
                or_(
                    ManagementFeeStatement.status.is_(None),
                    ManagementFeeStatement.status != "superseded",
                ),
            )
            .order_by(Party.name, Party.id, ManagementFeeStatement.period)
            .execution_options(populate_existing=True)
        )
        return tuple((row, name) for row, name in (await db.execute(query)).all())


management_fee_matrix_repository = ManagementFeeMatrixRepository()
