"""
Property Certificate CRUD Operations
产权证CRUD操作
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset import Asset
from ..models.property_certificate import PropertyCertificate, PropertyOwner
from ..schemas.property_certificate import (
    PropertyCertificateCreate,
    PropertyCertificateUpdate,
    PropertyOwnerCreate,
    PropertyOwnerUpdate,
)
from .asset import SensitiveDataHandler
from .base import CRUDBase


class CRUDPropertyOwner(
    CRUDBase[PropertyOwner, PropertyOwnerCreate, PropertyOwnerUpdate]
):
    """权利人CRUD操作 - 支持敏感字段加密"""

    def __init__(self, model: type[PropertyOwner]) -> None:
        super().__init__(model)
        # 🔒 安全修复: PropertyOwner 敏感字段处理（使用确定性加密以支持搜索）
        self.sensitive_data_handler = SensitiveDataHandler(
            searchable_fields={
                "id_number",  # 证件号码 - 高度敏感PII，需要搜索
                "phone",  # 联系电话 - 敏感PII，需要搜索
            }
        )

    async def create_async(
        self,
        db: AsyncSession,
        *,
        obj_in: PropertyOwnerCreate | dict[str, Any],
        commit: bool = True,
        **kwargs: Any,
    ) -> PropertyOwner:
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()

        encrypted_data = self.sensitive_data_handler.encrypt_data(obj_in_data)
        return await super().create(
            db=db, obj_in=encrypted_data, commit=commit, **kwargs
        )

    async def get_async(
        self, db: AsyncSession, id: Any, use_cache: bool = True
    ) -> PropertyOwner | None:
        result = await super().get(db=db, id=id, use_cache=use_cache)
        if result is not None:
            self.sensitive_data_handler.decrypt_data(result.__dict__)
        return result

    async def get_multi_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        use_cache: bool = False,
        **kwargs: Any,
    ) -> list[PropertyOwner]:
        results = await super().get_multi(
            db=db, skip=skip, limit=limit, use_cache=use_cache, **kwargs
        )
        for item in results:
            self.sensitive_data_handler.decrypt_data(item.__dict__)
        return results

    async def update_async(
        self,
        db: AsyncSession,
        *,
        db_obj: PropertyOwner,
        obj_in: PropertyOwnerUpdate | dict[str, Any],
        commit: bool = True,
    ) -> PropertyOwner:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        encrypted_data = self.sensitive_data_handler.encrypt_data(update_data)
        return await super().update(
            db=db, db_obj=db_obj, obj_in=encrypted_data, commit=commit
        )

    async def search_by_id_number_async(
        self, db: AsyncSession, id_number: str, skip: int = 0, limit: int = 100
    ) -> list[PropertyOwner]:
        encrypted_id_number = self.sensitive_data_handler.encrypt_field(
            "id_number", id_number
        )
        stmt = (
            select(self.model)
            .where(self.model.id_number == encrypted_id_number)
            .offset(skip)
            .limit(limit)
        )
        results = list((await db.execute(stmt)).scalars().all())
        for item in results:
            self.sensitive_data_handler.decrypt_data(item.__dict__)
        return results


class CRUDPropertyCertificate(
    CRUDBase[PropertyCertificate, PropertyCertificateCreate, PropertyCertificateUpdate]
):
    """产权证CRUD操作类"""

    async def get_by_certificate_number_async(
        self, db: AsyncSession, certificate_number: str
    ) -> PropertyCertificate | None:
        stmt = select(PropertyCertificate).where(
            PropertyCertificate.certificate_number == certificate_number
        )
        return (await db.execute(stmt)).scalars().first()

    async def create_with_owners_async(
        self,
        db: AsyncSession,
        *,
        obj_in: PropertyCertificateCreate,
        owner_ids: list[str] | None = None,
        asset_ids: list[str] | None = None,
        commit: bool = True,
    ) -> PropertyCertificate:
        db_obj = PropertyCertificate(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()

        if owner_ids:
            result = await db.execute(
                select(PropertyOwner).where(PropertyOwner.id.in_(owner_ids))
            )
            owners = list(result.scalars().all())
            if owners:
                db_obj.owners.extend(owners)

        if asset_ids:
            result = await db.execute(select(Asset).where(Asset.id.in_(asset_ids)))
            assets = list(result.scalars().all())
            if assets:
                db_obj.assets.extend(assets)

        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(db_obj)
        return db_obj


property_certificate_crud = CRUDPropertyCertificate(PropertyCertificate)
property_owner_crud = CRUDPropertyOwner(PropertyOwner)
