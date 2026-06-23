"""Property certificate CRUD operations."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, false, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset import Asset
from ..models.certificate_party_relation import (
    CertificatePartyRelation,
    CertificateRelationRole,
)
from ..models.property_certificate import (
    PropertyCertificate,
    PropertyCertificateAttachment,
)
from ..schemas.property_certificate import (
    PropertyCertificateAttachmentInput,
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
        attachments: list[PropertyCertificateAttachmentInput] | None = None,
        created_by: str | None = None,
        organization_id: str | None = None,  # DEPRECATED alias
        commit: bool = True,
    ) -> PropertyCertificate:
        payload = obj_in.model_dump()
        payload.pop("organization_id", None)
        payload.pop("asset_ids", None)
        payload.pop("holder_party_ids", None)
        payload.pop("attachments", None)
        if created_by is not None and created_by.strip() != "":
            payload["created_by"] = created_by
        if organization_id is not None and organization_id.strip() != "":
            pass

        db_obj = PropertyCertificate(**payload)
        db.add(db_obj)
        await db.flush()

        self._add_owner_relations(db, certificate_id=db_obj.id, owner_ids=owner_ids)

        if asset_ids:
            asset_result = await db.execute(select(Asset).where(Asset.id.in_(asset_ids)))
            assets: list[Asset] = list(asset_result.scalars().all())
            if assets:
                db_obj.assets.extend(assets)

        self._add_attachments(
            db,
            certificate_id=db_obj.id,
            attachments=attachments,
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
        attachments: list[PropertyCertificateAttachmentInput] | None = None,
        commit: bool = True,
    ) -> PropertyCertificate:
        payload = obj_in.model_dump(exclude_unset=True)
        payload.pop("organization_id", None)
        payload.pop("asset_ids", None)
        payload.pop("holder_party_ids", None)
        payload.pop("attachments", None)

        for field_name, value in payload.items():
            setattr(db_obj, field_name, value)

        if owner_ids is not None:
            await db.execute(
                delete(CertificatePartyRelation).where(
                    CertificatePartyRelation.certificate_id == db_obj.id,
                    CertificatePartyRelation.relation_role
                    == CertificateRelationRole.OWNER,
                )
            )
            self._add_owner_relations(
                db,
                certificate_id=db_obj.id,
                owner_ids=owner_ids,
            )

        if asset_ids is not None:
            asset_result = await db.execute(select(Asset).where(Asset.id.in_(asset_ids)))
            db_obj.assets = list(asset_result.scalars().all())

        if attachments is not None:
            await db.execute(
                delete(PropertyCertificateAttachment).where(
                    PropertyCertificateAttachment.certificate_id == db_obj.id
                )
            )
            self._add_attachments(
                db,
                certificate_id=db_obj.id,
                attachments=attachments,
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
        db: AsyncSession,
        *,
        certificate_id: str,
        owner_ids: list[str] | None,
    ) -> None:
        if not owner_ids:
            return
        normalized_owner_ids = [
            owner_id.strip() for owner_id in owner_ids if owner_id.strip() != ""
        ]
        for index, owner_id in enumerate(normalized_owner_ids):
            relation = CertificatePartyRelation()
            relation.certificate_id = certificate_id
            relation.party_id = owner_id
            relation.relation_role = CertificateRelationRole.OWNER
            relation.is_primary = index == 0
            db.add(relation)

    @staticmethod
    def _add_attachments(
        db: AsyncSession,
        *,
        certificate_id: str,
        attachments: list[PropertyCertificateAttachmentInput] | None,
    ) -> None:
        if not attachments:
            return
        for attachment in attachments:
            payload = attachment.model_dump()
            payload["certificate_id"] = certificate_id
            db.add(PropertyCertificateAttachment(**payload))


property_certificate_crud = CRUDPropertyCertificate(PropertyCertificate)
