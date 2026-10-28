"""Data access for the explicit, administrative rent backfill command."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset_contract import TerminalContract, UpstreamContract


class RentBackfillRepository:
    async def list_contracts(
        self, db: AsyncSession
    ) -> list[tuple[str, UpstreamContract | TerminalContract]]:
        upstreams = (
            (await db.execute(select(UpstreamContract).order_by(UpstreamContract.id)))
            .scalars()
            .all()
        )
        terminals = (
            (await db.execute(select(TerminalContract).order_by(TerminalContract.id)))
            .scalars()
            .all()
        )
        return [
            *(("upstream", row) for row in upstreams),
            *(("terminal", row) for row in terminals),
        ]

    async def lock_contract(
        self, db: AsyncSession, contract: UpstreamContract | TerminalContract
    ) -> None:
        await db.refresh(contract, with_for_update=True)


rent_backfill_repository = RentBackfillRepository()
