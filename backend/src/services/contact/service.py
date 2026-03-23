"""联系人服务层。"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.contact import contact_crud
from ...models.contact import Contact


class ContactService:
    """联系人服务。"""

    async def create_contact(
        self, db: AsyncSession, *, contact_data: dict[str, Any]
    ) -> Contact:
        return await contact_crud.create_async(db=db, obj_in=contact_data)

    async def get_contact(self, db: AsyncSession, *, contact_id: str) -> Contact | None:
        return await contact_crud.get_async(db, id=contact_id)

    async def get_entity_contacts(
        self,
        db: AsyncSession,
        *,
        entity_type: str,
        entity_id: str,
        skip: int,
        limit: int,
    ) -> tuple[list[Contact], int]:
        return await contact_crud.get_multi_async(
            db=db,
            entity_type=entity_type,
            entity_id=entity_id,
            skip=skip,
            limit=limit,
        )

    async def get_primary_contact(
        self, db: AsyncSession, *, entity_type: str, entity_id: str
    ) -> Contact | None:
        return await contact_crud.get_primary_async(
            db=db,
            entity_type=entity_type,
            entity_id=entity_id,
        )

    async def update_contact(
        self, db: AsyncSession, *, contact_id: str, update_data: dict[str, Any]
    ) -> Contact | None:
        contact = await self.get_contact(db=db, contact_id=contact_id)
        if not contact:
            return None
        return await contact_crud.update_async(
            db=db,
            db_obj=contact,
            obj_in=update_data,
        )

    async def delete_contact(
        self, db: AsyncSession, *, contact_id: str
    ) -> Contact | None:
        return await contact_crud.delete_async(db, id=contact_id)

    async def create_contacts_batch(
        self, db: AsyncSession, *, contacts_data: list[dict[str, Any]]
    ) -> list[Contact]:
        return await contact_crud.create_many_async(db=db, objects_in=contacts_data)


contact_service = ContactService()


def get_contact_service() -> ContactService:
    return contact_service
