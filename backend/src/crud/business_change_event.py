"""Business change persistence and current Party-scoped audit reads."""

from datetime import datetime

from sqlalchemy import (
    ColumnElement,
    Select,
    String,
    and_,
    exists,
    false,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.assessment_scope import AssessmentScopeVersion
from ..models.asset_contract import TerminalContract, UpstreamContract
from ..models.asset_unit import AssetUnit, AssetUnitBoundaryChange
from ..models.business_change_event import BusinessChangeEvent
from ..models.management_fee_statement import ManagementFeeStatement
from ..models.occupancy_report import MonthlyOccupancyReport
from ..services.party_scope_resolver import EffectivePartyScope
from .asset_contract import AssetContractRepository
from .asset_unit import AssetUnitRepository


def fee_statement_ids_for_scope(scope: EffectivePartyScope) -> Select[tuple[str]]:
    """Audit uses the same whole-owner boundary as management fee detail.

    Keep the manager "covers every agreement of the owner" rule in sync with
    the Python twin in services/asset_operations/management_fee_query_service.
    """
    query = select(ManagementFeeStatement.id)
    if scope.scope_mode == "unrestricted":
        return query
    if scope.error_code is not None:
        return query.where(false())
    conditions: list[ColumnElement[bool]] = []
    if scope.scope_mode in {"owner", "all"} and scope.owner_party_ids:
        conditions.append(
            ManagementFeeStatement.owner_party_id.in_(scope.owner_party_ids)
        )
    if scope.scope_mode in {"manager", "all"} and scope.manager_party_ids:
        agreement = select(UpstreamContract.id).where(
            UpstreamContract.owner_party_id == ManagementFeeStatement.owner_party_id,
            UpstreamContract.contract_type == "management_agreement",
        )
        conditions.append(
            and_(
                exists(agreement),
                ~exists(
                    agreement.where(
                        UpstreamContract.operator_party_id.not_in(
                            scope.manager_party_ids
                        )
                    )
                ),
            )
        )
    return query.where(or_(*conditions) if conditions else false())


class BusinessChangeRepository:
    async def add(self, db: AsyncSession, *, event: BusinessChangeEvent) -> None:
        db.add(event)

    async def list_events(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        target_type: str | None,
        target_id: str | None,
        since: datetime | None,
        until: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[BusinessChangeEvent, ...], int]:
        upstream_ids = AssetContractRepository._apply_upstream_scope(
            select(UpstreamContract.id), scope=scope
        )
        terminal_ids = AssetContractRepository._apply_terminal_scope(
            select(TerminalContract.id), scope=scope
        )
        # Unit maintenance and boundary events follow the unit's own
        # visibility: owner axis on owner_party_id, manager axis through the
        # project, matching AssetUnitRepository._apply_scope.
        unit_ids = AssetUnitRepository._apply_scope(select(AssetUnit.id), scope=scope)
        query = select(BusinessChangeEvent).where(
            or_(
                and_(
                    BusinessChangeEvent.target_type == "upstream_contract",
                    BusinessChangeEvent.target_id.in_(upstream_ids),
                ),
                and_(
                    BusinessChangeEvent.target_type == "terminal_contract",
                    BusinessChangeEvent.target_id.in_(terminal_ids),
                ),
                and_(
                    BusinessChangeEvent.target_type == "management_fee_statement",
                    BusinessChangeEvent.target_id.in_(
                        fee_statement_ids_for_scope(scope)
                    ),
                ),
                and_(
                    BusinessChangeEvent.target_type == "asset_unit",
                    BusinessChangeEvent.target_id.in_(unit_ids),
                ),
                and_(
                    BusinessChangeEvent.target_type == "asset_unit_boundary_change",
                    BusinessChangeEvent.target_id.in_(
                        boundary_change_ids_for_scope(scope)
                    ),
                ),
                and_(
                    BusinessChangeEvent.target_type == "assessment_scope_version",
                    BusinessChangeEvent.target_id.in_(
                        reporting_object_ids_for_scope(
                            scope, "assessment_scope_versions"
                        )
                    ),
                ),
                and_(
                    BusinessChangeEvent.target_type == "monthly_occupancy_report",
                    BusinessChangeEvent.target_id.in_(
                        reporting_object_ids_for_scope(
                            scope, "monthly_occupancy_reports"
                        )
                    ),
                ),
            )
        )
        if target_type is not None:
            query = query.where(BusinessChangeEvent.target_type == target_type)
        if target_id is not None:
            query = query.where(BusinessChangeEvent.target_id == target_id)
        if since is not None:
            query = query.where(BusinessChangeEvent.occurred_at >= since)
        if until is not None:
            query = query.where(BusinessChangeEvent.occurred_at < until)
        total = int(
            (await db.scalar(select(func.count()).select_from(query.subquery()))) or 0
        )
        result = await db.execute(
            query.order_by(
                BusinessChangeEvent.occurred_at.desc(), BusinessChangeEvent.id.desc()
            )
            .offset(offset)
            .limit(limit)
        )
        return tuple(result.scalars().all()), total


def reporting_object_ids_for_scope(
    scope: EffectivePartyScope, table_name: str
) -> Select[tuple[str]]:
    """Reporting objects follow the operator-party identity.

    Assessment-scope versions and monthly report chain rows both carry the
    operator party they belong to; a caller sees them when the manager axis
    covers that operator. Unrestricted sees everything.
    """
    if table_name == "monthly_occupancy_reports":
        model: type[MonthlyOccupancyReport] | type[AssessmentScopeVersion] = (
            MonthlyOccupancyReport
        )
    elif table_name == "assessment_scope_versions":
        model = AssessmentScopeVersion
    else:  # pragma: no cover - caller contract
        raise ValueError(f"Unsupported reporting table: {table_name}")
    statement = select(model.id)
    if scope.scope_mode == "unrestricted":
        return statement
    operator_ids: list[str]
    if scope.scope_mode in {"manager", "all"} and len(scope.manager_party_ids) > 0:
        operator_ids = scope.manager_party_ids
    elif scope.scope_mode == "all" and len(scope.effective_party_ids) > 0:
        operator_ids = scope.effective_party_ids
    else:
        operator_ids = []
    return statement.where(model.operator_party_id.in_(operator_ids))


def boundary_change_ids_for_scope(
    scope: EffectivePartyScope,
) -> Select[tuple[str]]:
    """Boundary events are visible when any source unit is visible.

    source_unit_ids is a JSONB array; the EXISTS form expands each element
    back into asset_units and applies the same owner/manager scope as unit
    reads. Unrestricted scope keeps the visibility predicate empty.
    """
    unit_visibility = AssetUnitRepository._apply_scope(
        select(AssetUnit.id), scope=scope
    )
    visibility = unit_visibility.whereclause
    source_element = select(
        func.jsonb_array_elements_text(AssetUnitBoundaryChange.source_unit_ids).cast(
            String
        )
    )
    conditions: list[ColumnElement[bool]] = [
        AssetUnit.id.in_(source_element.scalar_subquery())
    ]
    if visibility is not None:
        conditions.append(visibility)
    return select(AssetUnitBoundaryChange.id).where(
        exists(select(1).select_from(AssetUnit).where(*conditions))
    )


business_change_repository = BusinessChangeRepository()
