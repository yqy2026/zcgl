"""Manual asset-unit edits: basic info and vacancy note under optimistic locks."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Protocol
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import ResourceNotFoundError
from ...models.asset_unit import AssetUnit
from ...schemas.asset_operations import (
    AssetUnitResponse,
    AssetUnitUpdate,
    AssetUnitVacancyNoteUpdate,
)
from ..party_scope_resolver import EffectivePartyScope
from .errors import (
    AssetOperationsVersionConflictError,
    AssetUnitAreaInvalidError,
    AssetUnitFieldNotEditableError,
    AssetUnitPeriodOverlapError,
)


class AssetUnitEditor(Protocol):
    async def get(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        scope: EffectivePartyScope,
        for_update: bool = False,
    ) -> AssetUnit | None: ...

    async def list_lifecycle_events(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_id: str,
    ) -> tuple[object, ...]: ...


class AssetUnitContractReader(Protocol):
    async def find_terminal_overlaps(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[str, ...]: ...


def _default_today() -> date:
    from datetime import UTC
    from zoneinfo import ZoneInfo

    return datetime.now(UTC).astimezone(ZoneInfo("Asia/Shanghai")).date()


class AssetUnitCommandService:
    """Apply manual unit edits without touching derived rental facts."""

    def __init__(
        self,
        *,
        repository: AssetUnitEditor | None = None,
        contract_repository: AssetUnitContractReader | None = None,
        clock: Callable[[], datetime] | None = None,
        business_today: Callable[[], date] = _default_today,
        id_factory: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        from ...crud.asset_contract import (
            asset_contract_repository as default_contract_repository,
        )
        from ...crud.asset_unit import (
            asset_unit_repository as default_unit_repository,
        )

        self.repository = repository or default_unit_repository
        self.contract_repository = contract_repository or default_contract_repository
        self.clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))
        self.business_today = business_today
        self.id_factory = id_factory

    async def update_asset_unit(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        request: AssetUnitUpdate,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> AssetUnitResponse:
        unit = await self.repository.get(
            db,
            unit_id=unit_id,
            scope=scope,
            for_update=True,
        )
        if unit is None:
            raise ResourceNotFoundError("AssetUnit", unit_id)
        if unit.version != request.expected_version:
            raise AssetOperationsVersionConflictError(
                unit_id=unit_id,
                expected_version=request.expected_version,
                actual_version=unit.version,
            )
        new_rentable = (
            request.rentable_area
            if request.rentable_area is not None
            else unit.rentable_area
        )
        new_building = (
            request.building_area
            if request.building_area is not None
            else unit.building_area
        )
        if new_rentable > new_building:
            raise AssetUnitAreaInvalidError(unit_id=unit_id)
        changes_managed_period = (
            request.managed_from is not None
            and request.managed_from != unit.managed_from
        ) or (request.managed_to is not None and request.managed_to != unit.managed_to)
        if changes_managed_period:
            new_from = (
                request.managed_from
                if request.managed_from is not None
                else unit.managed_from
            )
            new_to = (
                request.managed_to
                if request.managed_to is not None
                else unit.managed_to or date.max
            )
            overlapping = await self.contract_repository.find_terminal_overlaps(
                db,
                unit_ids=(unit.id,),
                start_date=new_from,
                end_date=new_to,
            )
            if overlapping:
                raise AssetUnitPeriodOverlapError(
                    asset_unit_ids=[unit_id],
                    terminal_contract_ids=sorted(overlapping),
                )
        provided_owned_fields = [
            field
            for field in ("project_id", "owner_party_id")
            if getattr(request, field) is not None
        ]
        if provided_owned_fields:
            raise AssetUnitFieldNotEditableError(field_names=provided_owned_fields)
        for field in (
            "name",
            "address",
            "usage_type",
            "acquisition_mode",
            "is_operating",
            "land_area",
            "building_area",
            "rentable_area",
            "managed_from",
            "managed_to",
        ):
            value = getattr(request, field)
            if value is not None:
                setattr(unit, field, value)
        await db.flush()
        await db.commit()
        return await self._response(db, unit, today=self.business_today())

    async def update_vacancy_note(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        request: AssetUnitVacancyNoteUpdate,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> AssetUnitResponse:
        unit = await self.repository.get(
            db,
            unit_id=unit_id,
            scope=scope,
            for_update=True,
        )
        if unit is None:
            raise ResourceNotFoundError("AssetUnit", unit_id)
        if unit.version != request.expected_version:
            raise AssetOperationsVersionConflictError(
                unit_id=unit_id,
                expected_version=request.expected_version,
                actual_version=unit.version,
            )
        for field in ("vacancy_reason", "expected_lease_start"):
            value = getattr(request, field)
            if value is not None:
                setattr(unit, field, value)
        await db.flush()
        await db.commit()
        return await self._response(db, unit, today=self.business_today())

    async def _response(
        self,
        db: AsyncSession,
        unit: AssetUnit,
        *,
        today: date,
    ) -> AssetUnitResponse:
        overlapping = await self.contract_repository.find_terminal_overlaps(
            db,
            unit_ids=(unit.id,),
            start_date=today,
            end_date=today,
        )
        rented = len(overlapping) > 0
        from .query_service import AssetOperationsQueryService

        detail = AssetOperationsQueryService._unit_detail(unit, rented=rented)
        return AssetUnitResponse.model_validate(
            detail.model_dump(exclude={"terminal_contract_ids"})
        )


asset_unit_command_service = AssetUnitCommandService()


__all__ = [
    "AssetUnitCommandService",
    "asset_unit_command_service",
]
