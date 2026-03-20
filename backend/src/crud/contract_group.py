"""
CRUD helpers for ContractGroup（合同组）。

单表操作，业务逻辑由 Service 层保证。
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import exists, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..crud.query_builder import PartyFilter
from ..models.asset import Asset
from ..models.associations import contract_assets, contract_group_assets
from ..models.contract_group import (
    Contract,
    ContractAuditLog,
    ContractGroup,
    ContractLedgerEntry,
    ContractLifecycleStatus,
    ContractRentTerm,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CRUDContractGroup:
    """ContractGroup CRUD 操作。"""

    @staticmethod
    def _normalize_scope_ids(raw_ids: list[str] | tuple[str, ...] | None) -> list[str]:
        if raw_ids is None:
            return []
        return [str(raw_id).strip() for raw_id in raw_ids if str(raw_id).strip() != ""]

    def _apply_contract_group_party_filter(
        self,
        stmt: Any,
        *,
        party_filter: PartyFilter,
    ) -> Any:
        owner_party_ids = self._normalize_scope_ids(
            list(party_filter.owner_party_ids or [])
        )
        manager_party_ids = self._normalize_scope_ids(
            list(party_filter.manager_party_ids or [])
        )

        if len(owner_party_ids) == 0 and len(manager_party_ids) == 0:
            generic_party_ids = self._normalize_scope_ids(list(party_filter.party_ids))
            if len(generic_party_ids) == 0:
                return stmt.where(false())
            owner_party_ids = generic_party_ids
            manager_party_ids = generic_party_ids

        conditions: list[Any] = []
        if len(owner_party_ids) > 0:
            conditions.append(ContractGroup.owner_party_id.in_(owner_party_ids))
        if len(manager_party_ids) > 0:
            conditions.append(ContractGroup.operator_party_id.in_(manager_party_ids))

        if len(conditions) == 0:
            return stmt.where(false())
        if len(conditions) == 1:
            return stmt.where(conditions[0])
        return stmt.where(or_(*conditions))

    @staticmethod
    def _ownership_contracts_stmt(ownership_id: str):
        return (
            select(Contract.contract_id)
            .join(
                ContractGroup,
                Contract.contract_group_id == ContractGroup.contract_group_id,
            )
            .where(
                ContractGroup.owner_party_id == ownership_id,
                ContractGroup.data_status == "正常",
                Contract.data_status == "正常",
            )
        )

    async def create(
        self,
        db: AsyncSession,
        *,
        data: dict[str, Any],
        asset_ids: list[str] | None = None,
        commit: bool = True,
    ) -> ContractGroup:
        """创建合同组，可选关联资产。"""
        group = ContractGroup(**data)
        db.add(group)
        await db.flush()

        if asset_ids:
            await self._replace_assets(db, group.contract_group_id, asset_ids)

        if commit:
            await db.commit()
            await db.refresh(group)
        return group

    async def get(
        self,
        db: AsyncSession,
        group_id: str,
        *,
        load_contracts: bool = False,
        party_filter: PartyFilter | None = None,
    ) -> ContractGroup | None:
        stmt = select(ContractGroup).where(ContractGroup.contract_group_id == group_id)
        if party_filter is not None:
            normalized_scope_ids = self._normalize_scope_ids(list(party_filter.party_ids))
            if len(normalized_scope_ids) == 0:
                return None
            stmt = self._apply_contract_group_party_filter(
                stmt,
                party_filter=party_filter,
            )
        if load_contracts:
            stmt = stmt.options(selectinload(ContractGroup.contracts))
        return (await db.execute(stmt)).scalars().first()

    async def get_by_code(
        self, db: AsyncSession, group_code: str
    ) -> ContractGroup | None:
        stmt = select(ContractGroup).where(ContractGroup.group_code == group_code)
        return (await db.execute(stmt)).scalars().first()

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ContractGroup,
        data: dict[str, Any],
        asset_ids: list[str] | None = None,
        commit: bool = True,
    ) -> ContractGroup:
        """更新合同组字段，可选整体替换资产关联。"""
        for key, value in data.items():
            setattr(db_obj, key, value)
        db_obj.updated_at = _utcnow()
        db_obj.version = (db_obj.version or 0) + 1

        if asset_ids is not None:
            await self._replace_assets(db, db_obj.contract_group_id, asset_ids)

        if commit:
            await db.commit()
            await db.refresh(db_obj)
        return db_obj

    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        db_obj: ContractGroup,
        commit: bool = True,
    ) -> ContractGroup:
        """逻辑删除：data_status → '已删除'。"""
        db_obj.data_status = "已删除"
        db_obj.updated_at = _utcnow()
        if commit:
            await db.commit()
            await db.refresh(db_obj)
        return db_obj

    async def list_by_filters(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str | None = None,
        owner_party_id: str | None = None,
        revenue_mode: str | None = None,
        data_status: str = "正常",
        offset: int = 0,
        limit: int = 20,
        party_filter: PartyFilter | None = None,
    ) -> tuple[list[ContractGroup], int]:
        """分页查询合同组，返回 (items, total)。"""
        stmt = select(ContractGroup).where(ContractGroup.data_status == data_status)

        if party_filter is not None:
            normalized_scope_ids = self._normalize_scope_ids(list(party_filter.party_ids))
            if len(normalized_scope_ids) == 0:
                return [], 0
            stmt = self._apply_contract_group_party_filter(
                stmt,
                party_filter=party_filter,
            )

        if operator_party_id is not None:
            stmt = stmt.where(ContractGroup.operator_party_id == operator_party_id)
        if owner_party_id is not None:
            stmt = stmt.where(ContractGroup.owner_party_id == owner_party_id)
        if revenue_mode is not None:
            stmt = stmt.where(ContractGroup.revenue_mode == revenue_mode)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await db.execute(count_stmt)).scalar_one()

        items_stmt = (
            stmt.order_by(ContractGroup.created_at.desc()).offset(offset).limit(limit)
        )
        items = list((await db.execute(items_stmt)).scalars().all())
        return items, total

    async def count_by_operator_month(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        year_month: str,
    ) -> int:
        """统计指定运营方当月已有的合同组数量（用于 group_code SEQ 生成）。"""
        stmt = select(func.count()).where(
            ContractGroup.operator_party_id == operator_party_id,
            ContractGroup.group_code.like(f"%-{year_month}-%"),
        )
        return (await db.execute(stmt)).scalar_one()

    async def count_by_ownership_async(
        self,
        db: AsyncSession,
        ownership_id: str,
    ) -> int:
        stmt = select(func.count()).select_from(
            self._ownership_contracts_stmt(ownership_id).subquery()
        )
        return int((await db.execute(stmt)).scalar() or 0)

    async def count_active_by_ownership_async(
        self,
        db: AsyncSession,
        ownership_id: str,
    ) -> int:
        stmt = select(func.count()).select_from(
            self._ownership_contracts_stmt(ownership_id)
            .where(Contract.status == ContractLifecycleStatus.ACTIVE)
            .subquery()
        )
        return int((await db.execute(stmt)).scalar() or 0)

    async def sum_due_amount_by_ownership_async(
        self,
        db: AsyncSession,
        ownership_id: str,
    ) -> float:
        stmt = (
            select(func.coalesce(func.sum(ContractLedgerEntry.amount_due), 0))
            .join(Contract, ContractLedgerEntry.contract_id == Contract.contract_id)
            .join(
                ContractGroup,
                Contract.contract_group_id == ContractGroup.contract_group_id,
            )
            .where(
                ContractGroup.owner_party_id == ownership_id,
                ContractGroup.data_status == "正常",
                Contract.data_status == "正常",
            )
        )
        return float((await db.execute(stmt)).scalar() or 0)

    async def sum_paid_amount_by_ownership_async(
        self,
        db: AsyncSession,
        ownership_id: str,
    ) -> float:
        stmt = (
            select(func.coalesce(func.sum(ContractLedgerEntry.paid_amount), 0))
            .join(Contract, ContractLedgerEntry.contract_id == Contract.contract_id)
            .join(
                ContractGroup,
                Contract.contract_group_id == ContractGroup.contract_group_id,
            )
            .where(
                ContractGroup.owner_party_id == ownership_id,
                ContractGroup.data_status == "正常",
                Contract.data_status == "正常",
            )
        )
        return float((await db.execute(stmt)).scalar() or 0)

    async def sum_overdue_amount_by_ownership_async(
        self,
        db: AsyncSession,
        ownership_id: str,
    ) -> float:
        stmt = (
            select(
                func.coalesce(
                    func.sum(
                        func.greatest(
                            ContractLedgerEntry.amount_due
                            - ContractLedgerEntry.paid_amount,
                            0,
                        )
                    ),
                    0,
                )
            )
            .join(Contract, ContractLedgerEntry.contract_id == Contract.contract_id)
            .join(
                ContractGroup,
                Contract.contract_group_id == ContractGroup.contract_group_id,
            )
            .where(
                ContractGroup.owner_party_id == ownership_id,
                ContractGroup.data_status == "正常",
                Contract.data_status == "正常",
                ContractLedgerEntry.payment_status.in_(["unpaid", "partial", "overdue"]),
            )
        )
        return float((await db.execute(stmt)).scalar() or 0)

    async def create_audit_log(
        self,
        db: AsyncSession,
        *,
        data: dict[str, Any],
        commit: bool = False,
    ) -> ContractAuditLog:
        log = ContractAuditLog(**data)
        db.add(log)
        await db.flush()
        if commit:
            await db.commit()
            await db.refresh(log)
        return log

    async def create_rent_term(
        self,
        db: AsyncSession,
        *,
        data: dict[str, Any],
        commit: bool = True,
    ) -> ContractRentTerm:
        rent_term = ContractRentTerm(**data)
        db.add(rent_term)
        await db.flush()
        if commit:
            await db.commit()
            await db.refresh(rent_term)
        return rent_term

    async def list_rent_terms_by_contract(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> list[ContractRentTerm]:
        stmt = (
            select(ContractRentTerm)
            .where(ContractRentTerm.contract_id == contract_id)
            .order_by(ContractRentTerm.sort_order.asc())
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_rent_term(
        self,
        db: AsyncSession,
        *,
        rent_term_id: str,
    ) -> ContractRentTerm | None:
        stmt = select(ContractRentTerm).where(
            ContractRentTerm.rent_term_id == rent_term_id
        )
        return (await db.execute(stmt)).scalars().first()

    async def update_rent_term(
        self,
        db: AsyncSession,
        *,
        db_obj: ContractRentTerm,
        data: dict[str, Any],
        commit: bool = True,
    ) -> ContractRentTerm:
        for key, value in data.items():
            setattr(db_obj, key, value)
        db_obj.updated_at = _utcnow()
        if commit:
            await db.commit()
            await db.refresh(db_obj)
        return db_obj

    async def delete_rent_term(
        self,
        db: AsyncSession,
        *,
        db_obj: ContractRentTerm,
        commit: bool = True,
    ) -> None:
        await db.delete(db_obj)
        if commit:
            await db.commit()

    async def create_ledger_entry(
        self,
        db: AsyncSession,
        *,
        data: dict[str, Any],
        commit: bool = False,
    ) -> ContractLedgerEntry:
        entry = ContractLedgerEntry(**data)
        db.add(entry)
        await db.flush()
        if commit:
            await db.commit()
            await db.refresh(entry)
        return entry

    async def get_existing_ledger_year_months(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        year_months: list[str] | None = None,
    ) -> set[str]:
        stmt = select(ContractLedgerEntry.year_month).where(
            ContractLedgerEntry.contract_id == contract_id
        )
        if year_months:
            stmt = stmt.where(ContractLedgerEntry.year_month.in_(year_months))
        return set((await db.execute(stmt)).scalars().all())

    async def list_ledger_entries_by_contract(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> list[ContractLedgerEntry]:
        stmt = (
            select(ContractLedgerEntry)
            .where(ContractLedgerEntry.contract_id == contract_id)
            .order_by(ContractLedgerEntry.year_month.asc())
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_ledger_by_contract(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        year_month_start: str | None = None,
        year_month_end: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ContractLedgerEntry], int]:
        stmt = select(ContractLedgerEntry).where(
            ContractLedgerEntry.contract_id == contract_id
        )
        if year_month_start is not None:
            stmt = stmt.where(ContractLedgerEntry.year_month >= year_month_start)
        if year_month_end is not None:
            stmt = stmt.where(ContractLedgerEntry.year_month <= year_month_end)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await db.execute(count_stmt)).scalar_one()

        items_stmt = (
            stmt.order_by(ContractLedgerEntry.year_month.asc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await db.execute(items_stmt)).scalars().all())
        return items, total

    async def query_ledger_entries(
        self,
        db: AsyncSession,
        *,
        asset_id: str | None = None,
        party_id: str | None = None,
        contract_id: str | None = None,
        year_month_start: str | None = None,
        year_month_end: str | None = None,
        payment_status: str | None = None,
        include_voided: bool = False,
        offset: int = 0,
        limit: int = 20,
        party_filter: PartyFilter | None = None,
    ) -> tuple[list[ContractLedgerEntry], int]:
        stmt = select(ContractLedgerEntry).join(
            Contract, ContractLedgerEntry.contract_id == Contract.contract_id
        ).join(
            ContractGroup,
            Contract.contract_group_id == ContractGroup.contract_group_id,
        )

        if party_filter is not None:
            normalized_scope_ids = self._normalize_scope_ids(list(party_filter.party_ids))
            if len(normalized_scope_ids) == 0:
                return [], 0
            stmt = self._apply_contract_group_party_filter(
                stmt,
                party_filter=party_filter,
            )

        if asset_id is not None:
            stmt = stmt.where(
                exists(
                    select(1)
                    .select_from(contract_assets)
                    .where(
                        contract_assets.c.contract_id == Contract.contract_id,
                        contract_assets.c.asset_id == asset_id,
                    )
                )
            )
        if party_id is not None:
            stmt = stmt.where(
                (Contract.lessor_party_id == party_id)
                | (Contract.lessee_party_id == party_id)
            )
        if contract_id is not None:
            stmt = stmt.where(ContractLedgerEntry.contract_id == contract_id)
        if year_month_start is not None:
            stmt = stmt.where(ContractLedgerEntry.year_month >= year_month_start)
        if year_month_end is not None:
            stmt = stmt.where(ContractLedgerEntry.year_month <= year_month_end)
        if payment_status is not None:
            stmt = stmt.where(ContractLedgerEntry.payment_status == payment_status)
        if not include_voided:
            stmt = stmt.where(ContractLedgerEntry.payment_status != "voided")

        stmt = stmt.where(Contract.data_status == "正常")

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await db.execute(count_stmt)).scalar_one()

        items_stmt = (
            stmt.order_by(
                ContractLedgerEntry.year_month.asc(),
                ContractLedgerEntry.contract_id.asc(),
                ContractLedgerEntry.entry_id.asc(),
            )
            .offset(offset)
            .limit(limit)
        )
        items = list((await db.execute(items_stmt)).scalars().all())
        return items, total

    async def get_overdue_with_contract_async(
        self,
        db: AsyncSession,
        *,
        today: Any,
    ) -> list[ContractLedgerEntry]:
        stmt = (
            select(ContractLedgerEntry)
            .join(Contract, ContractLedgerEntry.contract_id == Contract.contract_id)
            .where(
                ContractLedgerEntry.payment_status.in_(["unpaid", "partial"]),
                ContractLedgerEntry.due_date < today,
                Contract.data_status == "正常",
            )
            .options(
                selectinload(ContractLedgerEntry.contract).options(
                    selectinload(Contract.lease_detail),
                    selectinload(Contract.lessee_party),
                )
            )
            .order_by(ContractLedgerEntry.due_date.asc())
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_due_soon_with_contract_async(
        self,
        db: AsyncSession,
        *,
        today: Any,
        warning_date: Any,
    ) -> list[ContractLedgerEntry]:
        stmt = (
            select(ContractLedgerEntry)
            .join(Contract, ContractLedgerEntry.contract_id == Contract.contract_id)
            .where(
                ContractLedgerEntry.payment_status == "unpaid",
                ContractLedgerEntry.due_date <= warning_date,
                ContractLedgerEntry.due_date >= today,
                Contract.data_status == "正常",
            )
            .options(
                selectinload(ContractLedgerEntry.contract).options(
                    selectinload(Contract.lease_detail),
                    selectinload(Contract.lessee_party),
                )
            )
            .order_by(ContractLedgerEntry.due_date.asc())
        )
        return list((await db.execute(stmt)).scalars().all())

    async def batch_update_ledger_status(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        entry_ids: list[str],
        payment_status: str,
        paid_amount: Any | None = None,
        notes: str | None = None,
        commit: bool = True,
    ) -> list[ContractLedgerEntry]:
        if not entry_ids:
            return []

        stmt = (
            select(ContractLedgerEntry)
            .where(
                ContractLedgerEntry.contract_id == contract_id,
                ContractLedgerEntry.entry_id.in_(entry_ids),
            )
            .order_by(ContractLedgerEntry.year_month.asc())
        )
        entries = list((await db.execute(stmt)).scalars().all())
        for entry in entries:
            entry.payment_status = payment_status
            if paid_amount is not None:
                entry.paid_amount = paid_amount
            if notes is not None:
                entry.notes = notes
            entry.updated_at = _utcnow()

        if commit:
            await db.commit()
        return entries

    async def has_contract_ledger_entries(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> bool:
        stmt = select(func.count()).where(
            ContractLedgerEntry.contract_id == contract_id
        )
        count = (await db.execute(stmt)).scalar_one()
        return count > 0

    async def _replace_assets(
        self,
        db: AsyncSession,
        group_id: str,
        asset_ids: list[str],
    ) -> None:
        """整体替换合同组的资产关联（先删后插）。"""
        await db.execute(
            contract_group_assets.delete().where(  # type: ignore[attr-defined]
                contract_group_assets.c.contract_group_id == group_id
            )
        )
        if not asset_ids:
            return
        # 验证资产存在
        exist_stmt = select(Asset.id).where(Asset.id.in_(asset_ids))
        existing_ids = set((await db.execute(exist_stmt)).scalars().all())
        rows = [
            {"contract_group_id": group_id, "asset_id": aid, "created_at": _utcnow()}
            for aid in asset_ids
            if aid in existing_ids
        ]
        if rows:
            await db.execute(contract_group_assets.insert(), rows)  # type: ignore[attr-defined]


contract_group_crud = CRUDContractGroup()
