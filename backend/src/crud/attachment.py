"""Data access for generic attachment metadata."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.attachment import Attachment


class AttachmentCRUD:
    async def create(
        self,
        db: AsyncSession,
        *,
        data: dict[str, object],
        commit: bool = False,
    ) -> Attachment:
        attachment = Attachment(**data)
        db.add(attachment)
        await db.flush()
        if commit:
            await db.commit()
            await db.refresh(attachment)
        return attachment

    async def get_for_owner(
        self,
        db: AsyncSession,
        *,
        attachment_id: str,
        owner_type: str,
        owner_id: str,
    ) -> Attachment | None:
        stmt = select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.owner_type == owner_type,
            Attachment.owner_id == owner_id,
        )
        return (await db.execute(stmt)).scalars().first()

    async def list_for_owner(
        self,
        db: AsyncSession,
        *,
        owner_type: str,
        owner_id: str,
    ) -> list[Attachment]:
        stmt = (
            select(Attachment)
            .where(
                Attachment.owner_type == owner_type,
                Attachment.owner_id == owner_id,
            )
            .order_by(Attachment.created_at.asc(), Attachment.id.asc())
        )
        return list((await db.execute(stmt)).scalars().all())


attachment_crud = AttachmentCRUD()
