"""Property certificate persistence with Party and Asset relations only."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import exists, false, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.asset import Asset
from ..models.associations import property_cert_assets
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
    @staticmethod
    def _select_with_relations() -> Any:
        return (
            select(PropertyCertificate)
            .options(
                selectinload(PropertyCertificate.assets),
                selectinload(PropertyCertificate.party_relations),
            )
            .execution_options(populate_existing=True)
        )

    @staticmethod
    def _apply_party_scope(stmt: Any, party_filter: PartyFilter | None) -> Any:
        """Narrow to certificates holding at least one authorized party relation."""
        if party_filter is None:
            return stmt
        party_ids = [
            str(value).strip() for value in party_filter.party_ids if str(value).strip()
        ]
        if not party_ids:
            return stmt.where(false())
        return stmt.where(
            exists().where(
                CertificatePartyRelation.certificate_id == PropertyCertificate.id,
                CertificatePartyRelation.party_id.in_(party_ids),
            )
        )

    @staticmethod
    def _apply_asset_scope(stmt: Any, asset_id: str) -> Any:
        return stmt.where(
            exists().where(
                property_cert_assets.c.certificate_id == PropertyCertificate.id,
                property_cert_assets.c.asset_id == asset_id,
            )
        )

    async def get(
        self,
        db: AsyncSession,
        id: Any,
        use_cache: bool = True,
        party_filter: PartyFilter | None = None,
    ) -> PropertyCertificate | None:
        stmt = self._apply_party_scope(
            self._select_with_relations().where(PropertyCertificate.id == id),
            party_filter,
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
        asset_id: str | None = None,
        **kwargs: Any,
    ) -> list[PropertyCertificate]:
        stmt = self._apply_party_scope(self._select_with_relations(), party_filter)
        if asset_id is not None:
            stmt = self._apply_asset_scope(stmt, asset_id)
        stmt = stmt.order_by(PropertyCertificate.id).offset(skip).limit(limit)
        return list((await db.execute(stmt)).scalars().all())

    async def list_by_asset_ids(
        self,
        db: AsyncSession,
        *,
        asset_ids: Sequence[str],
    ) -> list[PropertyCertificate]:
        normalized_asset_ids = [
            str(asset_id).strip()
            for asset_id in asset_ids
            if str(asset_id).strip() != ""
        ]
        if not normalized_asset_ids:
            return []

        stmt = (
            self._select_with_relations()
            .where(
                exists().where(
                    property_cert_assets.c.certificate_id == PropertyCertificate.id,
                    property_cert_assets.c.asset_id.in_(normalized_asset_ids),
                )
            )
            .order_by(PropertyCertificate.id)
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
            # 直接写关联表而非 db_obj.assets = [...]：集合整体赋值会先懒加载未加载的
            # 关系（异步上下文 MissingGreenlet，2026-08-14 验收 ACC-009 回归修复），
            # 与 _add_owner_relations 的独立对象写法保持对称。
            rows = [
                {"certificate_id": db_obj.id, "asset_id": asset_id}
                for asset_id in asset_ids
                if str(asset_id).strip() != ""
            ]
            # 过滤后可能为空（如全空字符串入参）：空 values 列表会编译为非法
            # `INSERT INTO t () VALUES ()`（2026-08-14 复核收口），跳过写入。
            if rows:
                await db.execute(insert(property_cert_assets).values(rows))
        if commit:
            await db.commit()
        else:
            await db.flush()
        loaded = await self.get(db, db_obj.id, use_cache=False)
        if loaded is None:
            raise RuntimeError("created property certificate could not be reloaded")
        return loaded

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
        loaded = await self.get(db, db_obj.id, use_cache=False)
        if loaded is None:
            raise RuntimeError("updated property certificate could not be reloaded")
        return loaded

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
