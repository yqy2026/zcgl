from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.contract_supplement import ContractSupplement


class ContractSupplementRepository:
    async def list(
        self, db: AsyncSession, *, kind: str, contract_id: str
    ) -> list[ContractSupplement]:
        return list(
            (
                await db.execute(
                    select(ContractSupplement)
                    .where(
                        ContractSupplement.contract_kind == kind,
                        ContractSupplement.contract_id == contract_id,
                    )
                    .order_by(ContractSupplement.created_at, ContractSupplement.id)
                )
            )
            .scalars()
            .all()
        )

    async def get(
        self, db: AsyncSession, identity: str, *, lock: bool = False
    ) -> ContractSupplement | None:
        query = select(ContractSupplement).where(ContractSupplement.id == identity)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return (await db.execute(query)).scalar_one_or_none()

    async def add(self, db: AsyncSession, row: ContractSupplement) -> None:
        db.add(row)
        await db.flush()

    async def withdraw(
        self, db: AsyncSession, row: ContractSupplement, *, actor_id: str, reason: str
    ) -> None:
        row.withdrawn_at = datetime.now(UTC)
        row.withdrawn_by = actor_id
        row.withdrawal_reason = reason
        await db.flush()


contract_supplement_repository = ContractSupplementRepository()
