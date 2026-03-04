"""
联系人 CRUD 操作 - 支持敏感字段加密
"""

from typing import Any, cast

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.asset_support import SensitiveDataHandler
from ..models.contact import Contact, ContactType


def _set_attr(obj: Any, attr: str, value: Any) -> None:
    object.__setattr__(obj, attr, value)


class ContactCRUD:
    """联系人 CRUD 操作类 - 支持敏感字段加密"""

    def __init__(self) -> None:
        self.sensitive_data_handler = SensitiveDataHandler(
            searchable_fields={
                "phone",
                "office_phone",
            }
        )

    def _decrypt_contact(self, obj: Contact | None) -> Contact | None:
        if obj is not None:
            self.sensitive_data_handler.decrypt_data(obj.__dict__)
        return obj

    def _decrypt_contacts(self, results: list[Contact]) -> list[Contact]:
        for contact in results:
            self.sensitive_data_handler.decrypt_data(contact.__dict__)
        return results

    async def get_async(self, db: AsyncSession, id: str) -> Contact | None:
        result = await db.execute(select(Contact).where(Contact.id == id))
        obj = result.scalars().first()
        return self._decrypt_contact(obj)

    async def get_multi_async(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Contact], int]:
        base: Select[Any] = select(Contact).where(
            and_(
                Contact.entity_type == entity_type,
                Contact.entity_id == entity_id,
                Contact.is_active.is_(True),
            )
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = int((await db.execute(count_stmt)).scalar() or 0)
        list_stmt = (
            base.order_by(Contact.is_primary.desc(), Contact.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = list((await db.execute(list_stmt)).scalars().all())
        return self._decrypt_contacts(items), total

    async def get_primary_async(
        self, db: AsyncSession, entity_type: str, entity_id: str
    ) -> Contact | None:
        stmt = select(Contact).where(
            and_(
                Contact.entity_type == entity_type,
                Contact.entity_id == entity_id,
                Contact.is_active.is_(True),
                Contact.is_primary.is_(True),
            )
        )
        obj = (await db.execute(stmt)).scalars().first()
        return self._decrypt_contact(obj)

    async def create_async(self, db: AsyncSession, obj_in: dict[str, Any]) -> Contact:
        encrypted_data = cast(
            dict[str, Any], self.sensitive_data_handler.encrypt_data(obj_in.copy())
        )
        if encrypted_data.get("is_primary", False):
            await db.execute(
                select(Contact)
                .where(
                    and_(
                        Contact.entity_type == encrypted_data["entity_type"],
                        Contact.entity_id == encrypted_data["entity_id"],
                        Contact.is_primary.is_(True),
                    )
                )
                .with_for_update()
            )
            await db.execute(
                Contact.__table__.update()
                .where(
                    and_(
                        Contact.entity_type == encrypted_data["entity_type"],
                        Contact.entity_id == encrypted_data["entity_id"],
                        Contact.is_primary.is_(True),
                    )
                )
                .values(is_primary=False)
            )
        db_obj = Contact(**encrypted_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        self.sensitive_data_handler.decrypt_data(db_obj.__dict__)
        return db_obj

    async def create_many_async(
        self, db: AsyncSession, objects_in: list[dict[str, Any]]
    ) -> list[Contact]:
        if len(objects_in) == 0:
            return []

        encrypted_batch: list[dict[str, Any]] = [
            cast(dict[str, Any], self.sensitive_data_handler.encrypt_data(obj.copy()))
            for obj in objects_in
        ]

        last_primary_index_by_entity: dict[tuple[str, str], int] = {}
        for index, encrypted_data in enumerate(encrypted_batch):
            if encrypted_data.get("is_primary", False):
                entity_key = (
                    str(encrypted_data.get("entity_type") or ""),
                    str(encrypted_data.get("entity_id") or ""),
                )
                last_primary_index_by_entity[entity_key] = index

        for entity_type, entity_id in last_primary_index_by_entity:
            if entity_type == "" or entity_id == "":
                continue
            await db.execute(
                select(Contact)
                .where(
                    and_(
                        Contact.entity_type == entity_type,
                        Contact.entity_id == entity_id,
                        Contact.is_primary.is_(True),
                    )
                )
                .with_for_update()
            )
            await db.execute(
                Contact.__table__.update()
                .where(
                    and_(
                        Contact.entity_type == entity_type,
                        Contact.entity_id == entity_id,
                        Contact.is_primary.is_(True),
                    )
                )
                .values(is_primary=False)
            )

        for index, encrypted_data in enumerate(encrypted_batch):
            if not encrypted_data.get("is_primary", False):
                continue
            entity_key = (
                str(encrypted_data.get("entity_type") or ""),
                str(encrypted_data.get("entity_id") or ""),
            )
            if last_primary_index_by_entity.get(entity_key) != index:
                encrypted_data["is_primary"] = False

        db_objects = [Contact(**encrypted_data) for encrypted_data in encrypted_batch]
        db.add_all(db_objects)
        await db.commit()
        for obj in db_objects:
            self.sensitive_data_handler.decrypt_data(obj.__dict__)
        return db_objects

    async def update_async(
        self, db: AsyncSession, db_obj: Contact, obj_in: dict[str, Any]
    ) -> Contact:
        encrypted_data: dict[str, Any] = {}
        for field_name, value in obj_in.items():
            if field_name in self.sensitive_data_handler.ALL_PII_FIELDS:
                encrypted_data[field_name] = self.sensitive_data_handler.encrypt_field(
                    field_name, value
                )
            else:
                encrypted_data[field_name] = value
        if encrypted_data.get("is_primary", False) and not db_obj.is_primary:
            await db.execute(
                Contact.__table__.update()
                .where(
                    and_(
                        Contact.entity_type == db_obj.entity_type,
                        Contact.entity_id == db_obj.entity_id,
                        Contact.is_primary.is_(True),
                    )
                )
                .values(is_primary=False)
            )
        for field, value in encrypted_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        await db.commit()
        await db.refresh(db_obj)
        self.sensitive_data_handler.decrypt_data(db_obj.__dict__)
        return db_obj

    async def delete_async(self, db: AsyncSession, id: str) -> Contact | None:
        obj = await self.get_async(db, id)
        if obj:
            _set_attr(obj, "is_active", False)
            await db.commit()
            await db.refresh(obj)
        return obj

    async def get_multi_by_type_async(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_ids: list[str],
        contact_type: ContactType | None = None,
    ) -> list[Contact]:
        stmt = select(Contact).where(
            and_(
                Contact.entity_type == entity_type,
                Contact.entity_id.in_(entity_ids),
                Contact.is_active.is_(True),
            )
        )
        if contact_type is not None:
            stmt = stmt.where(Contact.contact_type == contact_type)
        results = list((await db.execute(stmt)).scalars().all())
        return self._decrypt_contacts(results)


contact_crud = ContactCRUD()
