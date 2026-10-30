"""Invalidate fee projections within the upstream agreement transaction."""

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.management_fee_statement import (
    ManagementFeeStatementRepository,
    management_fee_statement_repository,
)


class ManagementFeeRateService:
    def __init__(self, *, repository: ManagementFeeStatementRepository | None = None):
        self.repository = (
            repository
            if repository is not None
            else management_fee_statement_repository
        )

    async def invalidate(self, db: AsyncSession, *, owner_party_id: str) -> None:
        """Conservatively invalidate all owner drafts; confirmed fees stay frozen.

        Caller holds asset-unit and upstream-contract locks. Owner then statement
        locks serialize this input change with fee commands, without committing.
        """
        await self.repository.lock_owner(db, owner_party_id=owner_party_id)
        rows = await self.repository.list_statements(
            db, owner_party_id=owner_party_id, for_update=True
        )
        for row in rows:
            if row.status is None:
                row.version += 1


management_fee_rate_service = ManagementFeeRateService()
