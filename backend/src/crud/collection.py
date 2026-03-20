"""
Collection CRUD operations.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import and_, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.collection import CollectionRecord, CollectionStatus
from ..models.contract_group import Contract, ContractGroup, ContractLedgerEntry
from ..schemas.collection import CollectionRecordCreate, CollectionRecordUpdate
from .base import CRUDBase
from .query_builder import PartyFilter


class CRUDCollectionRecord(
    CRUDBase[CollectionRecord, CollectionRecordCreate, CollectionRecordUpdate]
):
    """CRUD for CollectionRecord."""

    @staticmethod
    def _normalize_scope_ids(raw_ids: list[str] | tuple[str, ...] | None) -> list[str]:
        if raw_ids is None:
            return []
        return [str(raw_id).strip() for raw_id in raw_ids if str(raw_id).strip() != ""]

    def _apply_collection_party_filter(self, stmt, *, party_filter: PartyFilter):
        owner_party_ids = self._normalize_scope_ids(list(party_filter.owner_party_ids or []))
        manager_party_ids = self._normalize_scope_ids(list(party_filter.manager_party_ids or []))
        if len(owner_party_ids) == 0 and len(manager_party_ids) == 0:
            generic_party_ids = self._normalize_scope_ids(list(party_filter.party_ids))
            if len(generic_party_ids) == 0:
                return stmt.where(false())
            owner_party_ids = generic_party_ids
            manager_party_ids = generic_party_ids

        conditions = []
        if len(owner_party_ids) > 0:
            conditions.append(ContractGroup.owner_party_id.in_(owner_party_ids))
        if len(manager_party_ids) > 0:
            conditions.append(ContractGroup.operator_party_id.in_(manager_party_ids))
        if len(conditions) == 0:
            return stmt.where(false())
        if len(conditions) == 1:
            return stmt.where(conditions[0])
        return stmt.where(or_(*conditions))

    async def get_overdue_ledger_stats_async(
        self,
        db: AsyncSession,
        *,
        today: date,
        party_filter: PartyFilter | None = None,
    ) -> tuple[int, Decimal]:
        stmt = (
            select(
                func.count(ContractLedgerEntry.entry_id).label("total_count"),
                func.coalesce(
                    func.sum(
                        func.greatest(
                            ContractLedgerEntry.amount_due
                            - ContractLedgerEntry.paid_amount,
                            0,
                        )
                    ),
                    0,
                ).label("total_amount"),
            )
            .where(
                and_(
                    ContractLedgerEntry.payment_status.in_(
                        ["unpaid", "partial", "overdue"]
                    ),
                    ContractLedgerEntry.due_date < today,
                )
            )
            .select_from(ContractLedgerEntry)
            .join(Contract, ContractLedgerEntry.contract_id == Contract.contract_id)
            .join(ContractGroup, Contract.contract_group_id == ContractGroup.contract_group_id)
        )
        if party_filter is not None:
            normalized_scope_ids = self._normalize_scope_ids(list(party_filter.party_ids))
            if len(normalized_scope_ids) == 0:
                return 0, Decimal("0")
            stmt = self._apply_collection_party_filter(stmt, party_filter=party_filter)
        stats = (await db.execute(stmt)).first()
        total_count = int(stats.total_count) if stats and stats.total_count else 0
        total_amount = stats.total_amount if stats and stats.total_amount else Decimal("0")
        return total_count, total_amount

    async def count_by_statuses_async(
        self,
        db: AsyncSession,
        *,
        statuses: list[CollectionStatus],
        party_filter: PartyFilter | None = None,
    ) -> int:
        stmt = (
            select(func.count(CollectionRecord.id))
            .select_from(CollectionRecord)
            .join(Contract, CollectionRecord.contract_id == Contract.contract_id)
            .join(ContractGroup, Contract.contract_group_id == ContractGroup.contract_group_id)
        )
        if statuses:
            stmt = stmt.where(CollectionRecord.collection_status.in_(statuses))
        if party_filter is not None:
            normalized_scope_ids = self._normalize_scope_ids(list(party_filter.party_ids))
            if len(normalized_scope_ids) == 0:
                return 0
            stmt = self._apply_collection_party_filter(stmt, party_filter=party_filter)
        return int((await db.execute(stmt)).scalar() or 0)

    async def count_since_date_async(
        self,
        db: AsyncSession,
        *,
        collection_date: date,
        party_filter: PartyFilter | None = None,
    ) -> int:
        stmt = (
            select(func.count(CollectionRecord.id))
            .select_from(CollectionRecord)
            .join(Contract, CollectionRecord.contract_id == Contract.contract_id)
            .join(ContractGroup, Contract.contract_group_id == ContractGroup.contract_group_id)
            .where(CollectionRecord.collection_date >= collection_date)
        )
        if party_filter is not None:
            normalized_scope_ids = self._normalize_scope_ids(list(party_filter.party_ids))
            if len(normalized_scope_ids) == 0:
                return 0
            stmt = self._apply_collection_party_filter(stmt, party_filter=party_filter)
        return int((await db.execute(stmt)).scalar() or 0)

    async def count_total_async(
        self,
        db: AsyncSession,
        *,
        party_filter: PartyFilter | None = None,
    ) -> int:
        stmt = (
            select(func.count(CollectionRecord.id))
            .select_from(CollectionRecord)
            .join(Contract, CollectionRecord.contract_id == Contract.contract_id)
            .join(ContractGroup, Contract.contract_group_id == ContractGroup.contract_group_id)
        )
        if party_filter is not None:
            normalized_scope_ids = self._normalize_scope_ids(list(party_filter.party_ids))
            if len(normalized_scope_ids) == 0:
                return 0
            stmt = self._apply_collection_party_filter(stmt, party_filter=party_filter)
        return int((await db.execute(stmt)).scalar() or 0)

    async def get_multi_with_filters_async(
        self,
        db: AsyncSession,
        *,
        ledger_id: str | None = None,
        contract_id: str | None = None,
        collection_status: CollectionStatus | None = None,
        page: int = 1,
        page_size: int = 20,
        party_filter: PartyFilter | None = None,
    ) -> tuple[list[CollectionRecord], int]:
        conditions = []
        if ledger_id:
            conditions.append(CollectionRecord.ledger_id == ledger_id)
        if contract_id:
            conditions.append(CollectionRecord.contract_id == contract_id)
        if collection_status:
            conditions.append(CollectionRecord.collection_status == collection_status)

        count_stmt = (
            select(func.count(CollectionRecord.id))
            .select_from(CollectionRecord)
            .join(Contract, CollectionRecord.contract_id == Contract.contract_id)
            .join(ContractGroup, Contract.contract_group_id == ContractGroup.contract_group_id)
        )
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        if party_filter is not None:
            normalized_scope_ids = self._normalize_scope_ids(list(party_filter.party_ids))
            if len(normalized_scope_ids) == 0:
                return [], 0
            count_stmt = self._apply_collection_party_filter(count_stmt, party_filter=party_filter)
        total = int((await db.execute(count_stmt)).scalar() or 0)

        offset = (page - 1) * page_size
        stmt = (
            select(CollectionRecord)
            .join(Contract, CollectionRecord.contract_id == Contract.contract_id)
            .join(ContractGroup, Contract.contract_group_id == ContractGroup.contract_group_id)
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        if party_filter is not None:
            stmt = self._apply_collection_party_filter(stmt, party_filter=party_filter)
        stmt = (
            stmt.order_by(CollectionRecord.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list((await db.execute(stmt)).scalars().all())
        return items, total

    async def get_by_id_async(
        self,
        db: AsyncSession,
        *,
        record_id: str,
        party_filter: PartyFilter | None = None,
    ) -> CollectionRecord | None:
        stmt = (
            select(CollectionRecord)
            .join(Contract, CollectionRecord.contract_id == Contract.contract_id)
            .join(ContractGroup, Contract.contract_group_id == ContractGroup.contract_group_id)
            .where(CollectionRecord.id == record_id)
        )
        if party_filter is not None:
            normalized_scope_ids = self._normalize_scope_ids(list(party_filter.party_ids))
            if len(normalized_scope_ids) == 0:
                return None
            stmt = self._apply_collection_party_filter(stmt, party_filter=party_filter)
        return (await db.execute(stmt)).scalars().first()

    async def get_ledger_by_id_async(
        self,
        db: AsyncSession,
        *,
        ledger_id: str,
        party_filter: PartyFilter | None = None,
    ) -> ContractLedgerEntry | None:
        stmt = (
            select(ContractLedgerEntry)
            .join(Contract, ContractLedgerEntry.contract_id == Contract.contract_id)
            .join(ContractGroup, Contract.contract_group_id == ContractGroup.contract_group_id)
            .where(ContractLedgerEntry.entry_id == ledger_id)
        )
        if party_filter is not None:
            normalized_scope_ids = self._normalize_scope_ids(list(party_filter.party_ids))
            if len(normalized_scope_ids) == 0:
                return None
            stmt = self._apply_collection_party_filter(stmt, party_filter=party_filter)
        return (await db.execute(stmt)).scalars().first()


collection_crud = CRUDCollectionRecord(CollectionRecord)
