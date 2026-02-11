"""
Property Certificate CRUD Operations
产权证CRUD操作
"""

from typing import Any

from sqlalchemy import false, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset import Asset
from ..models.property_certificate import (
    PropertyCertificate,
    PropertyOwner,
    property_certificate_owners,
)
from ..schemas.property_certificate import (
    PropertyCertificateCreate,
    PropertyCertificateUpdate,
    PropertyOwnerCreate,
    PropertyOwnerUpdate,
)
from .asset import SensitiveDataHandler
from .base import CRUDBase
from .query_builder import TenantFilter


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

    async def create_multi_async(
        self,
        db: AsyncSession,
        *,
        objects_in: list[PropertyOwnerCreate | dict[str, Any]],
        commit: bool = True,
    ) -> list[PropertyOwner]:
        if len(objects_in) == 0:
            return []

        encrypted_rows: list[dict[str, Any]] = []
        for obj_in in objects_in:
            if isinstance(obj_in, dict):
                obj_data = obj_in
            else:
                obj_data = obj_in.model_dump()
            encrypted_rows.append(self.sensitive_data_handler.encrypt_data(obj_data))

        owners = [PropertyOwner(**row) for row in encrypted_rows]
        db.add_all(owners)
        if commit:
            await db.commit()
        else:
            await db.flush()
        for owner in owners:
            self.sensitive_data_handler.decrypt_data(owner.__dict__)
        return owners

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

    async def get(
        self,
        db: AsyncSession,
        id: Any,
        use_cache: bool = True,
        tenant_filter: TenantFilter | None = None,
    ) -> PropertyCertificate | None:
        if tenant_filter is not None and not hasattr(
            PropertyCertificate,
            "organization_id",
        ):
            org_ids = [
                str(org_id).strip()
                for org_id in tenant_filter.organization_ids
                if str(org_id).strip() != ""
            ]
            stmt = select(PropertyCertificate).where(PropertyCertificate.id == id)
            if not org_ids:
                stmt = stmt.where(false())
                return (await db.execute(stmt)).scalars().first()
            stmt = (
                stmt.join(
                    property_certificate_owners,
                    property_certificate_owners.c.certificate_id
                    == PropertyCertificate.id,
                )
                .join(
                    PropertyOwner,
                    property_certificate_owners.c.owner_id == PropertyOwner.id,
                )
                .where(PropertyOwner.organization_id.in_(org_ids))
                .distinct()
            )
            return (await db.execute(stmt)).scalars().first()

        return await super().get(
            db=db,
            id=id,
            use_cache=use_cache,
            tenant_filter=tenant_filter,
        )

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        use_cache: bool = False,
        tenant_filter: TenantFilter | None = None,
        **kwargs: Any,
    ) -> list[PropertyCertificate]:
        if tenant_filter is not None and not hasattr(
            PropertyCertificate,
            "organization_id",
        ):
            org_ids = [
                str(org_id).strip()
                for org_id in tenant_filter.organization_ids
                if str(org_id).strip() != ""
            ]
            stmt = select(PropertyCertificate)
            if not org_ids:
                stmt = stmt.where(false()).offset(skip).limit(limit)
                return list((await db.execute(stmt)).scalars().all())
            stmt = (
                stmt
                .join(
                    property_certificate_owners,
                    property_certificate_owners.c.certificate_id
                    == PropertyCertificate.id,
                )
                .join(
                    PropertyOwner,
                    property_certificate_owners.c.owner_id == PropertyOwner.id,
                )
                .where(PropertyOwner.organization_id.in_(org_ids))
                .distinct()
                .offset(skip)
                .limit(limit)
            )
            return list((await db.execute(stmt)).scalars().all())

        return await super().get_multi(
            db=db,
            skip=skip,
            limit=limit,
            use_cache=use_cache,
            tenant_filter=tenant_filter,
            **kwargs,
        )

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
        organization_id: str | None = None,
        commit: bool = True,
    ) -> PropertyCertificate:
        payload = obj_in.model_dump()
        if organization_id is not None and organization_id.strip() != "":
            payload["organization_id"] = organization_id
        db_obj = PropertyCertificate(**payload)
        db.add(db_obj)
        await db.flush()

        if owner_ids:
            owner_result = await db.execute(
                select(PropertyOwner).where(PropertyOwner.id.in_(owner_ids))
            )
            owners: list[PropertyOwner] = list(owner_result.scalars().all())
            if owners:
                db_obj.owners.extend(owners)

        if asset_ids:
            asset_result = await db.execute(select(Asset).where(Asset.id.in_(asset_ids)))
            assets: list[Asset] = list(asset_result.scalars().all())
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
