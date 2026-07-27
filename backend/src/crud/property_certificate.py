"""Property certificate persistence with Party and Asset relations only."""

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
    async def get(
        self,
        db: AsyncSession,
        id: Any,
        use_cache: bool = True,
        party_filter: PartyFilter | None = None,
    ) -> PropertyCertificate | None:
        if party_filter is None:
            return await super().get(
                db=db, id=id, use_cache=use_cache, party_filter=party_filter
            )
        party_ids = [
            str(value).strip() for value in party_filter.party_ids if str(value).strip()
        ]
        stmt = select(PropertyCertificate).where(PropertyCertificate.id == id)
        if not party_ids:
            return (await db.execute(stmt.where(false()))).scalars().first()
        stmt = (
            stmt.join(
                CertificatePartyRelation,
                CertificatePartyRelation.certificate_id == PropertyCertificate.id,
            )
            .where(CertificatePartyRelation.party_id.in_(party_ids))
            .distinct()
        )
        return (await db.execute(stmt)).scalars().first()

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
        if party_filter is None:
            return await super().get_multi(
                db,
                skip=skip,
                limit=limit,
                use_cache=use_cache,
                party_filter=party_filter,
                **kwargs,
            )
        party_ids = [
            str(value).strip() for value in party_filter.party_ids if str(value).strip()
        ]
        stmt = select(PropertyCertificate)
        if not party_ids:
            return list(
                (await db.execute(stmt.where(false()).offset(skip).limit(limit)))
                .scalars()
                .all()
            )
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
        created_by: str | None = None,
        organization_id: str | None = None,
        commit: bool = True,
    ) -> PropertyCertificate:
        payload = obj_in.model_dump(exclude={"asset_ids", "holder_party_ids"})
        if created_by:
            payload["created_by"] = created_by
        db_obj = PropertyCertificate(**payload)
        db.add(db_obj)
        await db.flush()
        self._add_owner_relations(db, certificate_id=db_obj.id, owner_ids=owner_ids)
        if asset_ids:
            db_obj.assets = list(
                (await db.execute(select(Asset).where(Asset.id.in_(asset_ids))))
                .scalars()
                .all()
            )
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_with_relations_async(
        self,
        db: AsyncSession,
        *,
        db_obj: PropertyCertificate,
        obj_in: PropertyCertificateUpdate,
        owner_ids: list[str] | None = None,
        asset_ids: list[str] | None = None,
        commit: bool = True,
    ) -> PropertyCertificate:
        payload = obj_in.model_dump(
            exclude_unset=True, exclude={"asset_ids", "holder_party_ids"}
        )
        for field_name, value in payload.items():
            setattr(db_obj, field_name, value)
        if owner_ids is not None:
            from sqlalchemy import delete

            await db.execute(
                delete(CertificatePartyRelation).where(
                    CertificatePartyRelation.certificate_id == db_obj.id,
                    CertificatePartyRelation.relation_role
                    == CertificateRelationRole.OWNER,
                )
            )
            self._add_owner_relations(db, certificate_id=db_obj.id, owner_ids=owner_ids)
        if asset_ids is not None:
            db_obj.assets = list(
                (await db.execute(select(Asset).where(Asset.id.in_(asset_ids))))
                .scalars()
                .all()
            )
        db.add(db_obj)
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    def _add_owner_relations(
        db: AsyncSession, *, certificate_id: str, owner_ids: list[str] | None
    ) -> None:
        for index, owner_id in enumerate(owner_ids or []):
            normalized = owner_id.strip()
            if normalized:
                relation = CertificatePartyRelation()
                relation.certificate_id = certificate_id
                relation.party_id = normalized
                relation.relation_role = CertificateRelationRole.OWNER
                relation.is_primary = index == 0
                db.add(relation)


property_certificate_crud = CRUDPropertyCertificate(PropertyCertificate)
