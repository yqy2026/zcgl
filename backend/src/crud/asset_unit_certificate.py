"""Read and maintain certificate facts through the v5 temporal unit link."""

from datetime import date, datetime

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from ..models.asset_unit import AssetUnit, PropertyCertificateAssetUnit
from ..models.certificate_party_relation import (
    CertificatePartyRelation,
    CertificateRelationRole,
)
from ..models.property_certificate import PropertyCertificate
from ..services.party_scope_resolver import EffectivePartyScope
from .asset_unit import AssetUnitRepository


class AssetUnitCertificateRepository:
    @staticmethod
    def _known_units(
        certificate_id: str | InstrumentedAttribute[str],
        scope: EffectivePartyScope,
        as_of: date,
    ) -> Select[tuple[AssetUnit]]:
        link = PropertyCertificateAssetUnit
        statement = (
            select(AssetUnit)
            .join(link, link.asset_unit_id == AssetUnit.id)
            .where(link.certificate_id == certificate_id, link.effective_from <= as_of)
        )
        return AssetUnitRepository._apply_scope(statement, scope=scope)

    @staticmethod
    def _holder_conditions(
        certificate_id: str | InstrumentedAttribute[str], party_id: str, at: datetime
    ) -> tuple[ColumnElement[bool], ...]:
        relation = CertificatePartyRelation
        return (
            relation.certificate_id == certificate_id,
            relation.party_id == party_id,
            relation.relation_role.in_(
                [CertificateRelationRole.OWNER, CertificateRelationRole.CO_OWNER]
            ),
            relation.valid_from <= at,
            or_(relation.valid_to.is_(None), relation.valid_to >= at),
        )

    async def is_known_certificate(
        self,
        db: AsyncSession,
        *,
        certificate_id: str,
        scope: EffectivePartyScope,
        as_of: date,
    ) -> bool:
        statement = self._known_units(certificate_id, scope, as_of)
        return (
            await db.execute(statement.with_only_columns(AssetUnit.id).limit(1))
        ).scalar_one_or_none() is not None

    async def has_current_holder(
        self, db: AsyncSession, *, certificate_id: str, party_id: str, at: datetime
    ) -> bool:
        return bool(
            (
                await db.execute(
                    select(
                        exists().where(
                            *self._holder_conditions(certificate_id, party_id, at)
                        )
                    )
                )
            ).scalar_one()
        )

    async def list_options(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        owner_party_id: str,
        scope: EffectivePartyScope,
        as_of: date,
        at: datetime,
        query: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[PropertyCertificate], int]:
        certificate = PropertyCertificate
        link = PropertyCertificateAssetUnit
        statement = select(certificate).where(
            ~exists().where(
                link.asset_unit_id == unit_id, link.certificate_id == certificate.id
            )
        )
        if scope.scope_mode != "unrestricted":
            known = exists(
                self._known_units(certificate.id, scope, as_of)
                .with_only_columns(AssetUnit.id)
                .correlate(certificate)
            )
            holder = exists().where(
                *self._holder_conditions(certificate.id, owner_party_id, at)
            )
            statement = statement.where(or_(known, holder))
        if query is not None and query != "":
            escaped = (
                query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            pattern = f"%{escaped}%"
            statement = statement.where(
                or_(
                    certificate.certificate_number.ilike(pattern, escape="\\"),
                    certificate.property_address.ilike(pattern, escape="\\"),
                )
            )
        total = int(
            (
                await db.execute(select(func.count()).select_from(statement.subquery()))
            ).scalar_one()
        )
        items = list(
            (
                await db.execute(
                    statement.order_by(certificate.certificate_number, certificate.id)
                    .offset(offset)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return items, total

    async def has_links_for_certificate(
        self, db: AsyncSession, *, certificate_id: str
    ) -> bool:
        return bool(
            (
                await db.execute(
                    select(
                        exists().where(
                            PropertyCertificateAssetUnit.certificate_id
                            == certificate_id
                        )
                    )
                )
            ).scalar_one()
        )

    async def list(
        self, db: AsyncSession, *, unit_id: str, as_of: date
    ) -> list[PropertyCertificate]:
        link = PropertyCertificateAssetUnit
        statement = (
            select(PropertyCertificate)
            .where(
                exists().where(
                    link.certificate_id == PropertyCertificate.id,
                    link.asset_unit_id == unit_id,
                    link.effective_from <= as_of,
                    or_(link.effective_to.is_(None), link.effective_to >= as_of),
                )
            )
            .order_by(PropertyCertificate.certificate_number, PropertyCertificate.id)
        )
        return list((await db.execute(statement)).scalars().unique().all())

    async def find_link(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        certificate_id: str,
    ) -> PropertyCertificateAssetUnit | None:
        """Return the single link row for the pair (composite primary key)."""
        link = PropertyCertificateAssetUnit
        return (
            await db.execute(
                select(link).where(
                    link.asset_unit_id == unit_id,
                    link.certificate_id == certificate_id,
                )
            )
        ).scalar_one_or_none()

    async def find_active(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        certificate_id: str,
        on: date,
    ) -> PropertyCertificateAssetUnit | None:
        link = PropertyCertificateAssetUnit
        return (
            await db.execute(
                select(link).where(
                    link.asset_unit_id == unit_id,
                    link.certificate_id == certificate_id,
                    link.effective_from <= on,
                    or_(link.effective_to.is_(None), link.effective_to >= on),
                )
            )
        ).scalar_one_or_none()

    async def add(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        certificate_id: str,
        effective_from: date,
        effective_to: date | None,
    ) -> PropertyCertificateAssetUnit:
        link = PropertyCertificateAssetUnit(  # type: ignore[call-arg]
            asset_unit_id=unit_id,
            certificate_id=certificate_id,
            effective_from=effective_from,
            effective_to=effective_to,
        )
        db.add(link)
        await db.flush()
        return link

    async def close_interval(
        self,
        db: AsyncSession,
        *,
        link: PropertyCertificateAssetUnit,
        effective_to: date,
    ) -> None:
        link.effective_to = effective_to
        await db.flush()

    async def remove(
        self, db: AsyncSession, *, link: PropertyCertificateAssetUnit
    ) -> None:
        await db.delete(link)
        await db.flush()


asset_unit_certificate_repository = AssetUnitCertificateRepository()
