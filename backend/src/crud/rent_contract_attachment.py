from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.rent_contract import RentContractAttachment


class RentContractAttachmentCRUD:
    """合同附件 CRUD 操作"""

    async def get_by_contract_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> list[RentContractAttachment]:
        stmt = (
            select(RentContractAttachment)
            .where(RentContractAttachment.contract_id == contract_id)
            .order_by(desc(RentContractAttachment.created_at))
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_async(
        self,
        db: AsyncSession,
        *,
        attachment_id: str,
        contract_id: str | None = None,
    ) -> RentContractAttachment | None:
        stmt = select(RentContractAttachment).where(
            RentContractAttachment.id == attachment_id
        )
        if contract_id:
            stmt = stmt.where(RentContractAttachment.contract_id == contract_id)
        return (await db.execute(stmt)).scalars().first()


rent_contract_attachment_crud = RentContractAttachmentCRUD()
