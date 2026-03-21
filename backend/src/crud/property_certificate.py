"""Property certificate CRUD operations."""

from __future__ import annotations

from typing import Any

from sqlalchemy import false, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset import Asset
from ..models.certificate_party_relation import (
    CertificatePartyRelation,
    CertificateRelationRole,
)
from ..models.property_certificate import PropertyCertificate
from ..schemas.property_certificate import (
    PropertyCertificateCreate,
    PropertyCertificateUpdate,
)
from .base import CRUDBase
from .query_builder import PartyFilter


class CRUDPropertyCertificate(
    CRUDBase[PropertyCertificate, PropertyCertificateCreate, PropertyCertificateUpdate]
):
    """产权证 CRUD。"""

    async def get(
        self,
        db: AsyncSession,
        id: Any,
        use_cache: bool = True,
        party_filter: PartyFilter | None = None,
    ) -> PropertyCertificate | None:
        if party_filter is not None:
            party_ids = [
                str(party_id).strip()
                for party_id in party_filter.party_ids
                if str(party_id).strip() != ""
            ]
            stmt = select(PropertyCertificate).where(PropertyCertificate.id == id)
            if len(party_ids) == 0:
                stmt = stmt.where(false())
                return (await db.execute(stmt)).scalars().first()
            stmt = (
                stmt.join(
                    CertificatePartyRelation,
                    CertificatePartyRelation.certificate_id == PropertyCertificate.id,
                )
                .where(CertificatePartyRelation.party_id.in_(party_ids))
                .distinct()
            )
            return (await db.execute(stmt)).scalars().first()

        return await super().get(
            db=db,
            id=id,
            use_cache=use_cache,
            party_filter=party_filter,
        )

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        use_cache: bool = False,
        party_filter: PartyFilter | None = None,
        **kwargs: Any,
    ) -> list[PropertyCertificate]:
        if party_filter is not None:
            party_ids = [
                str(party_id).strip()
                for party_id in party_filter.party_ids
                if str(party_id).strip() != ""
            ]
            stmt = select(PropertyCertificate)
            if len(party_ids) == 0:
                stmt = stmt.where(false()).offset(skip).limit(limit)
                return list((await db.execute(stmt)).scalars().all())
            stmt = (
                stmt.join(
                    CertificatePartyRelation,
                    CertificatePartyRelation.certificate_id == PropertyCertificate.id,
                )
                .where(CertificatePartyRelation.party_id.in_(party_ids))
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
            party_filter=party_filter,
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
        organization_id: str | None = None,  # DEPRECATED alias
        commit: bool = True,
    ) -> PropertyCertificate:
        payload = obj_in.model_dump()
        payload.pop("organization_id", None)
        if organization_id is not None and organization_id.strip() != "":
            # Step4 后 organization_id 不再落库，兼容透传但忽略写入。
            pass

        db_obj = PropertyCertificate(**payload)
        db.add(db_obj)
        await db.flush()

        if owner_ids:
            normalized_owner_ids = [
                owner_id.strip() for owner_id in owner_ids if owner_id.strip() != ""
            ]
            for index, owner_id in enumerate(normalized_owner_ids):
                relation = CertificatePartyRelation()
                relation.certificate_id = db_obj.id
                relation.party_id = owner_id
                relation.relation_role = CertificateRelationRole.OWNER
                relation.is_primary = index == 0
                db.add(relation)

        if asset_ids:
            asset_result = await db.execute(
                select(Asset).where(Asset.id.in_(asset_ids))
            )
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
