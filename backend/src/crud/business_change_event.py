"""Business change persistence and current Party-scoped audit reads."""

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset_contract import TerminalContract, UpstreamContract
from ..models.business_change_event import BusinessChangeEvent
from ..services.party_scope_resolver import EffectivePartyScope
from .asset_contract import AssetContractRepository


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
