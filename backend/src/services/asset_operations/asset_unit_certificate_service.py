"""Authorize current unit access before reading or maintaining dated links."""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    BaseBusinessError,
    PartyScopeForbiddenError,
    ResourceNotFoundError,
)
from ...crud.archive_document import archive_document_repository
from ...crud.asset_unit import asset_unit_repository
from ...crud.asset_unit_certificate import asset_unit_certificate_repository
from ...crud.property_certificate import property_certificate_crud
from ...models.asset_unit import AssetUnit, PropertyCertificateAssetUnit
from ...models.property_certificate import PropertyCertificate
from ..party_scope_resolver import EffectivePartyScope
from .asset_unit_command_service import record_unit_audit


class UnitReader(Protocol):
    async def get(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        scope: EffectivePartyScope,
        for_update: bool = False,
    ) -> AssetUnit | None: ...


class CertificateGetter(Protocol):
    async def get(
        self, db: AsyncSession, certificate_id: str
    ) -> PropertyCertificate | None: ...


class CertificateRepository(Protocol):
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
    ) -> tuple[list[PropertyCertificate], int]: ...

    async def is_known_certificate(
        self,
        db: AsyncSession,
        *,
        certificate_id: str,
        scope: EffectivePartyScope,
        as_of: date,
    ) -> bool: ...

    async def has_current_holder(
        self, db: AsyncSession, *, certificate_id: str, party_id: str, at: datetime
    ) -> bool: ...

    async def list(
        self, db: AsyncSession, *, unit_id: str, as_of: date
    ) -> list[PropertyCertificate]: ...

    async def find_link(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        certificate_id: str,
    ) -> PropertyCertificateAssetUnit | None: ...

    async def add(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        certificate_id: str,
        effective_from: date,
        effective_to: date | None,
    ) -> PropertyCertificateAssetUnit: ...

    async def find_active(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        certificate_id: str,
        on: date,
    ) -> PropertyCertificateAssetUnit | None: ...

    async def close_interval(
        self,
        db: AsyncSession,
        *,
        link: PropertyCertificateAssetUnit,
        effective_to: date,
    ) -> None: ...

    async def remove(
        self, db: AsyncSession, *, link: PropertyCertificateAssetUnit
    ) -> None: ...


class AuditWriter(Protocol):
    async def __call__(
        self,
        db: AsyncSession,
        *,
        unit: AssetUnit,
        action: str,
        actor_id: str,
        before: dict[str, object],
        after: dict[str, object],
    ) -> None: ...


def _link_payload(
    certificate_id: str, effective_from: date, effective_to: date | None
) -> dict[str, object]:
    return {
        "certificate_id": certificate_id,
        "effective_from": effective_from.isoformat(),
        "effective_to": effective_to.isoformat() if effective_to else None,
    }


class AssetUnitCertificateService:
    def __init__(
        self,
        *,
        units: UnitReader = asset_unit_repository,
        certificates: CertificateGetter = property_certificate_crud,
        repository: CertificateRepository = asset_unit_certificate_repository,
        audit: AuditWriter = record_unit_audit,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.units = units
        self.certificates = certificates
        self.repository = repository
        self.audit = audit
        self.clock = clock

    def _require_scope(self, scope: EffectivePartyScope) -> None:
        if scope.scope_mode != "unrestricted":
            has_required_axis = (
                scope.scope_mode == "owner"
                and len(scope.owner_party_ids) > 0
                or scope.scope_mode == "manager"
                and len(scope.manager_party_ids) > 0
                or scope.scope_mode == "all"
                and len(scope.effective_party_ids) > 0
            )
            if scope.error_code is not None or not has_required_axis:
                raise PartyScopeForbiddenError(
                    code=scope.error_code or "PARTY_SCOPE_MISSING"
                )

    async def _locked_visible_unit(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        certificate_id: str,
        scope: EffectivePartyScope,
    ) -> AssetUnit:
        if not await archive_document_repository.lock_certificate(
            db, certificate_id=certificate_id
        ):
            raise ResourceNotFoundError("PropertyCertificate", certificate_id)
        unit = await self.units.get(db, unit_id=unit_id, scope=scope, for_update=True)
        if unit is None:
            raise ResourceNotFoundError("AssetUnit", unit_id)
        return unit

    async def list_for_unit(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        scope: EffectivePartyScope,
        as_of: date | None = None,
    ) -> list[PropertyCertificate]:
        self._require_scope(scope)
        unit = await self.units.get(db, unit_id=unit_id, scope=scope)
        if unit is None:
            raise ResourceNotFoundError("AssetUnit", unit_id)
        effective_date = (
            as_of
            if as_of is not None
            else self.clock().astimezone(ZoneInfo("Asia/Shanghai")).date()
        )
        return await self.repository.list(db, unit_id=unit_id, as_of=effective_date)

    async def list_options_for_unit(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        scope: EffectivePartyScope,
        query: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[PropertyCertificate], int]:
        self._require_scope(scope)
        unit = await self.units.get(db, unit_id=unit_id, scope=scope)
        if unit is None:
            raise ResourceNotFoundError("AssetUnit", unit_id)
        now = self.clock().astimezone(UTC)
        return await self.repository.list_options(
            db,
            unit_id=unit_id,
            owner_party_id=unit.owner_party_id,
            scope=scope,
            as_of=now.astimezone(ZoneInfo("Asia/Shanghai")).date(),
            at=now.replace(tzinfo=None),
            query=query.strip() if query is not None else None,
            offset=offset,
            limit=limit,
        )

    async def link_certificate(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        certificate_id: str,
        effective_from: date,
        effective_to: date | None,
        scope: EffectivePartyScope,
        actor_id: str,
    ) -> list[PropertyCertificate]:
        """Bind a registered certificate over an inclusive range.

        The pair has a single link row (composite PK): an open or overlapping
        row conflicts; an ended row is preserved until multiple intervals are supported.
        """
        self._require_scope(scope)
        unit = await self._locked_visible_unit(
            db, unit_id=unit_id, certificate_id=certificate_id, scope=scope
        )
        if scope.scope_mode != "unrestricted":
            now = self.clock().astimezone(UTC)
            known = await self.repository.is_known_certificate(
                db,
                certificate_id=certificate_id,
                scope=scope,
                as_of=now.astimezone(ZoneInfo("Asia/Shanghai")).date(),
            )
            if not known and not await self.repository.has_current_holder(
                db,
                certificate_id=certificate_id,
                party_id=unit.owner_party_id,
                at=now.replace(tzinfo=None),
            ):
                raise ResourceNotFoundError("PropertyCertificate", certificate_id)
        certificate = await self.certificates.get(db, certificate_id)
        if certificate is None:
            raise ResourceNotFoundError("PropertyCertificate", certificate_id)
        if effective_to is not None and effective_to < effective_from:
            raise BaseBusinessError(
                "关联截止日不能早于起始日",
                code="CERTIFICATE_LINK_RANGE_INVALID",
                status_code=400,
            )
        existing = await self.repository.find_link(
            db, unit_id=unit_id, certificate_id=certificate_id
        )
        if existing is not None and (
            existing.effective_to is None or existing.effective_to >= effective_from
        ):
            raise BaseBusinessError(
                "该证照已关联此物业且区间未结束",
                code="CERTIFICATE_LINK_OVERLAP",
                status_code=409,
            )
        if existing is not None:
            raise BaseBusinessError(
                "既有关联区间需保留历史，暂不支持重新关联",
                code="CERTIFICATE_LINK_HISTORY_PROTECTED",
                status_code=409,
            )
        after = _link_payload(certificate_id, effective_from, effective_to)
        await self.repository.add(
            db,
            unit_id=unit_id,
            certificate_id=certificate_id,
            effective_from=effective_from,
            effective_to=effective_to,
        )
        before: dict[str, object] = {}
        await self.audit(
            db,
            unit=unit,
            action="certificate_link_added",
            actor_id=actor_id,
            before=before,
            after=after,
        )
        await db.commit()
        return await self.repository.list(db, unit_id=unit_id, as_of=effective_from)

    async def unlink_certificate(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        certificate_id: str,
        effective_from: date,
        scope: EffectivePartyScope,
        actor_id: str,
    ) -> list[PropertyCertificate]:
        """End the link covering effective_from; the range closes the day before."""
        self._require_scope(scope)
        unit = await self._locked_visible_unit(
            db, unit_id=unit_id, certificate_id=certificate_id, scope=scope
        )
        link = await self.repository.find_active(
            db, unit_id=unit_id, certificate_id=certificate_id, on=effective_from
        )
        if link is None:
            raise ResourceNotFoundError("PropertyCertificate", certificate_id)
        today = self.clock().astimezone(ZoneInfo("Asia/Shanghai")).date()
        if effective_from < today or (
            effective_from == link.effective_from and link.effective_from <= today
        ):
            raise BaseBusinessError(
                "不能通过解绑删除已生效的关联历史",
                code="CERTIFICATE_LINK_HISTORY_PROTECTED",
                status_code=409,
            )
        before = _link_payload(certificate_id, link.effective_from, link.effective_to)
        if link.effective_from >= effective_from:
            # The interval never took effect; removing the row keeps no dead ranges.
            await self.repository.remove(db, link=link)
            after: dict[str, object] = {}
        else:
            effective_to = effective_from - timedelta(days=1)
            await self.repository.close_interval(
                db, link=link, effective_to=effective_to
            )
            after = _link_payload(certificate_id, link.effective_from, effective_to)
        await self.audit(
            db,
            unit=unit,
            action="certificate_link_removed",
            actor_id=actor_id,
            before=before,
            after=after,
        )
        await db.commit()
        return await self.repository.list(db, unit_id=unit_id, as_of=effective_from)


asset_unit_certificate_service = AssetUnitCertificateService()
