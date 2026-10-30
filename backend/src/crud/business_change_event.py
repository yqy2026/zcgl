"""Business change persistence and current Party-scoped audit reads."""

from datetime import datetime

from sqlalchemy import (
    ColumnElement,
    Select,
    and_,
    exists,
    false,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset_contract import TerminalContract, UpstreamContract
from ..models.business_change_event import BusinessChangeEvent
from ..models.management_fee_statement import ManagementFeeStatement
from ..services.party_scope_resolver import EffectivePartyScope
from .asset_contract import AssetContractRepository


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


business_change_repository = BusinessChangeRepository()
