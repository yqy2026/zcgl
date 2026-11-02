"""Monthly occupancy-report draft derivation and note persistence."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import ResourceNotFoundError
from ...crud.assessment_scope import assessment_scope_repository
from ...crud.asset_contract import asset_contract_repository
from ...crud.occupancy_report import occupancy_report_repository
from ...models.assessment_scope import AssessmentScopeItem, AssessmentScopeVersion
from ...models.asset_unit import AssetUnit
from ...models.occupancy_report import MonthlyOccupancyReport
from ...schemas.asset_operations import (
    OccupancyReportDraftResponse,
    OccupancyReportFieldChange,
    OccupancyReportFullScopeUnit,
    OccupancyReportLineResponse,
    OccupancyReportNoteResponse,
    OccupancyReportPendingUnit,
    OccupancyReportProjectCounts,
    OccupancyReportTotals,
    SaveOccupancyReportNoteRequest,
)
from ..party_scope_resolver import EffectivePartyScope
from .assessment_scope_command_service import (
    require_operator_access,
    summarize_version,
    view_for,
)
from .errors import (
    OccupancyReportAlreadySubmittedError,
    OccupancyReportPeriodInvalidError,
    OccupancyReportScopeMissingError,
)
from .occupancy_report_draft_rules import (
    FieldChange,
    FullScopeUnitFact,
    ReportAggregates,
    ReportLine,
    ReportLineFact,
    aggregates_from_lines,
    aggregates_with_full_scope,
    build_report_lines,
    compare_with_baseline,
    full_scope_project_counts,
    month_end,
)
from .rent_command_support import require_scope

_BUSINESS_TIMEZONE = ZoneInfo("Asia/Shanghai")
_PERIOD_PATTERN = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")


class OccupancyReportDraftService:
    """Derive the real-time monthly draft and persist its change note."""

    async def get_draft(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        period: str,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> OccupancyReportDraftResponse:
        """Real-time totals, lines, pending units, gates and baseline diff."""
        require_scope(scope, actor_id)
        require_operator_access(scope, operator_party_id=operator_party_id)
        await self._require_party(db, operator_party_id)
        self._validate_period(period)
        scope_version = await self._require_scope_version(
            db, operator_party_id=operator_party_id, period=period
        )
        existing = await occupancy_report_repository.get_active_chain_report(
            db,
            operator_party_id=operator_party_id,
            period=period,
        )
        if existing is not None and existing.status == "submitted":
            raise OccupancyReportAlreadySubmittedError(
                report_id=existing.id, period=period
            )

        items = tuple(
            await assessment_scope_repository.list_items(
                db, version_id=scope_version.id
            )
        )
        candidates = await assessment_scope_repository.list_managed_units(
            db,
            operator_party_id=operator_party_id,
            as_of=month_end(period),
            year=int(period[:4]),
            operating_only=False,
        )
        current_view = view_for(
            scope_version, items, [u for u in candidates if u.is_operating]
        )
        derived = await derive_report_lines(
            db,
            scope_version=scope_version,
            items=items,
            candidates=candidates,
            period=period,
        )
        lines = derived.lines
        aggregates = derived.aggregates
        baseline_row = await self._baseline_report(
            db,
            operator_party_id=operator_party_id,
            period=period,
        )
        if baseline_row is None:
            first_report = True
            changes: tuple[FieldChange, ...] = ()
        else:
            first_report = False
            changes = compare_with_baseline(
                aggregates,
                ReportAggregates(
                    unit_count=baseline_row.unit_count or 0,
                    rented_unit_count=baseline_row.rented_unit_count or 0,
                    occupancy_rate=baseline_row.occupancy_rate,
                    land_area=baseline_row.land_area or Decimal("0"),
                    building_area=baseline_row.building_area or Decimal("0"),
                    rentable_area=baseline_row.rentable_area or Decimal("0"),
                    rented_area=baseline_row.rented_area or Decimal("0"),
                    scope_version_id=baseline_row.scope_version_id,
                ),
            )
        change_note = existing.change_note if existing is not None else None
        gate_reasons: list[str] = []
        if len(current_view.pending) > 0:
            gate_reasons.append("pending_units_unconfirmed")
        if len(changes) > 0 and not (change_note or "").strip():
            gate_reasons.append("change_note_required")
        total_projects, operating_projects, non_operating_projects = (
            full_scope_project_counts(derived.full_scope)
        )
        return OccupancyReportDraftResponse(
            full_scope_snapshot=[
                OccupancyReportFullScopeUnit.model_validate(asdict(row))
                for row in derived.full_scope
            ],
            project_counts=OccupancyReportProjectCounts(
                project_count=total_projects,
                operating_project_count=operating_projects,
                non_operating_project_count=non_operating_projects,
            ),
            operator_party_id=operator_party_id,
            period=period,
            first_report=first_report,
            scope_version=summarize_version(scope_version),
            totals=OccupancyReportTotals(
                unit_count=aggregates.unit_count,
                rented_unit_count=aggregates.rented_unit_count,
                occupancy_rate=aggregates.occupancy_rate,
                land_area=aggregates.land_area,
                building_area=aggregates.building_area,
                rentable_area=aggregates.rentable_area,
                rented_area=aggregates.rented_area,
            ),
            lines=[
                OccupancyReportLineResponse(
                    asset_unit_id=line.asset_unit_id,
                    owner_name_snapshot=line.owner_name_snapshot,
                    usage_type_snapshot=line.usage_type_snapshot,
                    project_name_snapshot=line.project_name_snapshot,
                    address_snapshot=line.address_snapshot,
                    land_area=line.land_area,
                    building_area=line.building_area,
                    rentable_area=line.rentable_area,
                    rented_area=line.rented_area,
                    unit_count=line.unit_count,  # type: ignore[arg-type]
                    rented_unit_count=line.rented_unit_count,  # type: ignore[arg-type]
                    rental_status=line.rental_status,  # type: ignore[arg-type]
                    terminal_contract_ids=line.terminal_contract_ids,
                )
                for line in lines
            ],
            pending=[
                OccupancyReportPendingUnit(asset_unit_id=unit_id, reason=reason)  # type: ignore[arg-type]
                for unit_id, reason in current_view.pending
            ],
            changes=[
                OccupancyReportFieldChange(
                    field_name=change.field_name,
                    previous=change.previous,
                    current=change.current,
                )
                for change in changes
            ],
            change_note=change_note,
            can_submit=len(gate_reasons) == 0,
            gate_reasons=gate_reasons,
        )

    async def save_note(
        self,
        db: AsyncSession,
        *,
        period: str,
        request: SaveOccupancyReportNoteRequest,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> OccupancyReportNoteResponse:
        """Persist the draft change note; no snapshot is produced."""
        require_scope(scope, actor_id)
        operator_party_id = request.operator_party_id
        require_operator_access(scope, operator_party_id=operator_party_id)
        await self._require_party(db, operator_party_id)
        self._validate_period(period)
        # Reporting stays closed without an active scope, matching the draft
        # read path; note editing must not create orphan chain rows.
        await self._require_scope_version(
            db, operator_party_id=operator_party_id, period=period
        )
        await occupancy_report_repository.lock_serialization(
            db, operator_party_id=operator_party_id, period=period
        )
        # Re-read under the serialization lock so a concurrent submission
        # cannot slip between the earlier check and this upsert.
        chain = await occupancy_report_repository.get_active_chain_report(
            db,
            operator_party_id=operator_party_id,
            period=period,
            for_update=True,
        )
        if chain is not None and chain.status == "submitted":
            raise OccupancyReportAlreadySubmittedError(
                report_id=chain.id, period=period
            )
        normalized_note = (
            request.change_note.strip() if request.change_note is not None else None
        )
        if normalized_note == "":
            normalized_note = None
        draft = await occupancy_report_repository.upsert_draft_for_note(
            db,
            operator_party_id=operator_party_id,
            period=period,
            change_note=normalized_note,
            actor_id=actor_id,
        )
        await db.commit()
        return OccupancyReportNoteResponse(
            operator_party_id=operator_party_id,
            period=period,
            change_note=draft.change_note,
            draft_id=draft.id,
            version=draft.version,
        )

    async def _require_scope_version(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        period: str,
    ) -> AssessmentScopeVersion:
        version = await assessment_scope_repository.get_active_version(
            db,
            operator_party_id=operator_party_id,
            year=int(period[:4]),
        )
        if version is None:
            raise OccupancyReportScopeMissingError(
                operator_party_id=operator_party_id,
                year=int(period[:4]),
            )
        return version

    async def _baseline_report(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        period: str,
    ) -> MonthlyOccupancyReport | None:
        """Previous calendar month's submitted snapshot, if any."""
        year, month = int(period[:4]), int(period[5:7])
        if month == 1:
            previous_period = f"{year - 1}-12"
        else:
            previous_period = f"{year}-{month - 1:02d}"
        return await occupancy_report_repository.get_submitted_report(
            db,
            operator_party_id=operator_party_id,
            period=previous_period,
        )

    async def _require_party(self, db: AsyncSession, operator_party_id: str) -> None:
        if not await assessment_scope_repository.party_exists(
            db, party_id=operator_party_id
        ):
            raise ResourceNotFoundError("Party", operator_party_id)

    @staticmethod
    def _validate_period(period: str) -> None:
        if _PERIOD_PATTERN.fullmatch(period) is None:
            raise OccupancyReportPeriodInvalidError(period=period, reason="format")
        if month_end(period) > _business_today():
            raise OccupancyReportPeriodInvalidError(period=period, reason="future")


def _business_today() -> date:
    return datetime.now(UTC).astimezone(_BUSINESS_TIMEZONE).date()


occupancy_report_draft_service = OccupancyReportDraftService()


@dataclass(frozen=True)
class DerivedReportFacts:
    """Month-end line derivation shared by the draft and submission paths."""

    included_units: tuple[AssetUnit, ...]
    lines: tuple[ReportLine, ...]
    aggregates: ReportAggregates
    rented_unit_ids: frozenset[str]
    terminal_contract_map: dict[str, tuple[str, ...]]
    full_scope: tuple[FullScopeUnitFact, ...] = ()


async def derive_report_lines(
    db: AsyncSession,
    *,
    scope_version: AssessmentScopeVersion,
    items: tuple[AssessmentScopeItem, ...],
    candidates: list[AssetUnit] | tuple[AssetUnit, ...],
    period: str,
) -> DerivedReportFacts:
    """Derive month-end report lines from explicit decisions and live facts."""
    included_ids = {item.asset_unit_id for item in items if item.included}
    units_by_id = {unit.id: unit for unit in candidates}
    end_of_month = month_end(period)
    included_units = tuple(
        units_by_id[unit_id]
        for unit_id in sorted(included_ids)
        if unit_id in units_by_id
    )
    if len(included_units) > 0:
        included_unit_ids = {unit.id for unit in included_units}
        rented_ids = await asset_contract_repository.list_rented_unit_ids_by_units(
            db,
            unit_ids=included_unit_ids,
            as_of=end_of_month,
        )
        terminal_map = (
            await asset_contract_repository.map_live_terminal_contract_ids_by_units(
                db,
                unit_ids=included_unit_ids,
                as_of=end_of_month,
            )
        )
    else:
        rented_ids = set()
        terminal_map = {}
    line_context = await occupancy_report_repository.get_line_display_names(
        db,
        owner_party_ids={unit.owner_party_id for unit in included_units},
        project_ids={unit.project_id for unit in included_units},
    )
    # build_report_lines applies the same month-end window, so the extra
    # facts fetched above for out-of-window units are simply never read.
    lines = build_report_lines(
        period,
        (
            ReportLineFact(
                unit_id=unit.id,
                managed_from=unit.managed_from,
                managed_to=unit.managed_to,
                is_operating=unit.is_operating,
                included=True,
                rented=unit.id in rented_ids,
                land_area=unit.land_area,
                building_area=unit.building_area,
                rentable_area=unit.rentable_area,
                owner_name=line_context["owner"].get(unit.owner_party_id, ""),
                usage_type=unit.usage_type,
                project_name=line_context["project"].get(unit.project_id, ""),
                address=unit.address,
                terminal_contract_ids=terminal_map.get(unit.id, ()),
            )
            for unit in included_units
        ),
    )
    full_scope = await derive_full_scope(db, candidates=candidates, period=period)
    aggregates = aggregates_with_full_scope(aggregates_from_lines(lines), full_scope)
    aggregates = replace(aggregates, scope_version_id=scope_version.id)
    return DerivedReportFacts(
        included_units=included_units,
        lines=lines,
        aggregates=aggregates,
        rented_unit_ids=frozenset(rented_ids),
        terminal_contract_map=terminal_map,
        full_scope=full_scope,
    )


async def derive_full_scope(
    db: AsyncSession,
    *,
    candidates: list[AssetUnit] | tuple[AssetUnit, ...],
    period: str,
) -> tuple[FullScopeUnitFact, ...]:
    """Derive the full month-end identity and area source without rental queries."""
    end_of_month = month_end(period)
    full_set = tuple(
        unit
        for unit in candidates
        if unit.managed_from <= end_of_month
        and (unit.managed_to is None or unit.managed_to >= end_of_month)
    )
    projects = await occupancy_report_repository.get_line_display_names(
        db, owner_party_ids=set(), project_ids={unit.project_id for unit in full_set}
    )
    return tuple(
        FullScopeUnitFact(
            unit.id,
            unit.name,
            unit.project_id,
            projects["project"].get(unit.project_id, ""),
            unit.is_operating,
            unit.land_area,
            unit.building_area,
        )
        for unit in sorted(full_set, key=lambda row: row.id)
    )


__all__ = [
    "DerivedReportFacts",
    "OccupancyReportDraftService",
    "derive_report_lines",
    "derive_full_scope",
    "occupancy_report_draft_service",
]
