"""
CRUD helpers for ContractGroup（合同组）。

单表操作，业务逻辑由 Service 层保证。
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, TypedDict

from sqlalchemy import Select, and_, case, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.attributes import set_committed_value

from ..models.asset import Asset
from ..models.associations import contract_assets, contract_group_assets
from ..models.contract_group import (
    Contract,
    ContractAuditLog,
    ContractGroup,
    ContractLedgerEntry,
    ContractLifecycleStatus,
    ContractRentTerm,
    OperationalPaymentFlow,
    PaymentAllocation,
    ServiceFeeLedger,
)
from ..models.project_asset import ProjectAsset
from .query_builder import PartyFilter


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _today() -> date:
    return datetime.now(UTC).date()


class ContractAssetIdsByGroupRow(TypedDict):
    contract_id: str
    asset_ids: list[str]


class CRUDContractGroup:
    """ContractGroup CRUD 操作。"""

    @staticmethod
    def _attribution_scope_clause(model: Any, party_filter: PartyFilter) -> Any:
        general_ids = {
            normalized
            for value in party_filter.party_ids
            if (normalized := str(value).strip()) != ""
        }
        owner_ids = (
            {
                normalized
                for value in party_filter.owner_party_ids
                if (normalized := str(value).strip()) != ""
            }
            if party_filter.owner_party_ids is not None
            else general_ids
        )
        manager_ids = (
            {
                normalized
                for value in party_filter.manager_party_ids
                if (normalized := str(value).strip()) != ""
            }
            if party_filter.manager_party_ids is not None
            else general_ids
        )
        conditions: list[Any] = []
        if party_filter.filter_mode in {"owner", "any"} and owner_ids:
            conditions.append(model.attributed_owner_party_id.in_(sorted(owner_ids)))
        if party_filter.filter_mode in {"manager", "any"} and manager_ids:
            conditions.append(
                model.attributed_operator_party_id.in_(sorted(manager_ids))
            )
        if not conditions:
            return false()
        if len(conditions) == 1:
            return conditions[0]
        return or_(*conditions)

    @staticmethod
    def _ledger_allocation_totals_subquery() -> Any:
        return (
            select(
                PaymentAllocation.target_id.label("target_id"),
                func.coalesce(func.sum(PaymentAllocation.amount), 0).label(
                    "paid_amount"
                ),
                func.count(PaymentAllocation.allocation_id).label("allocation_count"),
                func.array_agg(func.distinct(OperationalPaymentFlow.occurred_on)).label(
                    "flow_occurred_on_dates"
                ),
            )
            .join(
                OperationalPaymentFlow,
                OperationalPaymentFlow.flow_id == PaymentAllocation.flow_id,
            )
            .where(
                PaymentAllocation.target_type == "contract_ledger_entry",
                OperationalPaymentFlow.status == "active",
            )
            .group_by(PaymentAllocation.target_id)
            .subquery()
        )

    @staticmethod
    def _ledger_payment_status_expr(paid_amount: Any) -> Any:
        return case(
            (ContractLedgerEntry._payment_status == "voided", "voided"),
            (paid_amount <= 0, "unpaid"),
            (paid_amount < ContractLedgerEntry.amount_due, "partial"),
            else_="paid",
        )

    @staticmethod
    def _apply_ledger_payment_facts(
        entry: ContractLedgerEntry,
        *,
        paid_amount: Any,
        payment_status: Any,
        allocation_count: Any = 0,
        flow_occurred_on_dates: Any = None,
    ) -> ContractLedgerEntry:
        set_committed_value(
            entry,
            "paid_amount",
            Decimal(str(paid_amount if paid_amount is not None else 0)),
        )
        set_committed_value(entry, "_payment_status", str(payment_status))
        setattr(
            entry,
            "active_allocation_count",
            int(allocation_count if allocation_count is not None else 0),
        )
        if flow_occurred_on_dates is None:
            normalized_flow_dates: list[Any] = []
        elif isinstance(flow_occurred_on_dates, (list, tuple, set)):
            normalized_flow_dates = list(flow_occurred_on_dates)
        else:
            normalized_flow_dates = [flow_occurred_on_dates]
        setattr(entry, "flow_occurred_on_dates", normalized_flow_dates)
        return entry

    @classmethod
    def _apply_ledger_payment_facts_from_row(cls, row: Any) -> ContractLedgerEntry:
        allocation_count = row[3] if len(row) > 3 else 0
        flow_occurred_on_dates = row[4] if len(row) > 4 else None
        return cls._apply_ledger_payment_facts(
            row[0],
            paid_amount=row[1],
            payment_status=row[2],
            allocation_count=allocation_count,
            flow_occurred_on_dates=flow_occurred_on_dates,
        )

    @staticmethod
    def _ledger_flow_date_exists_clause(
        *,
        flow_occurred_on_start: date | None,
        flow_occurred_on_end: date | None,
    ) -> Any:
        stmt = (
            select(PaymentAllocation.allocation_id)
            .join(
                OperationalPaymentFlow,
                OperationalPaymentFlow.flow_id == PaymentAllocation.flow_id,
            )
            .where(
                PaymentAllocation.target_type == "contract_ledger_entry",
                PaymentAllocation.target_id == ContractLedgerEntry.entry_id,
                OperationalPaymentFlow.status == "active",
            )
        )
        if flow_occurred_on_start is not None:
            stmt = stmt.where(
                OperationalPaymentFlow.occurred_on >= flow_occurred_on_start
            )
        if flow_occurred_on_end is not None:
            stmt = stmt.where(
                OperationalPaymentFlow.occurred_on <= flow_occurred_on_end
            )
        return stmt.exists()

    @staticmethod
    def _ownership_contracts_stmt(ownership_id: str) -> Select[tuple[str]]:
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
    ) -> ContractGroup | None:
        stmt = select(ContractGroup).where(ContractGroup.contract_group_id == group_id)
        if load_contracts:
            stmt = stmt.options(selectinload(ContractGroup.contracts))
        return (await db.execute(stmt)).scalars().first()

    async def get_with_assets(
        self,
        db: AsyncSession,
        group_id: str,
    ) -> ContractGroup | None:
        stmt = (
            select(ContractGroup)
            .where(ContractGroup.contract_group_id == group_id)
            .options(selectinload(ContractGroup.assets))
        )
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
        operator_party_ids: list[str] | None = None,
        owner_party_id: str | None = None,
        owner_party_ids: list[str] | None = None,
        revenue_mode: str | None = None,
        data_status: str = "正常",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ContractGroup], int]:
        """分页查询合同组，返回 (items, total)。"""
        stmt = (
            select(ContractGroup)
            .options(selectinload(ContractGroup.project))
            .where(ContractGroup.data_status == data_status)
        )

        if operator_party_id is not None:
            stmt = stmt.where(ContractGroup.operator_party_id == operator_party_id)
        if operator_party_ids:
            stmt = stmt.where(ContractGroup.operator_party_id.in_(operator_party_ids))
        if owner_party_id is not None:
            stmt = stmt.where(ContractGroup.owner_party_id == owner_party_id)
        if owner_party_ids:
            stmt = stmt.where(ContractGroup.owner_party_id.in_(owner_party_ids))
        if revenue_mode is not None:
            stmt = stmt.where(ContractGroup.revenue_mode == revenue_mode)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await db.execute(count_stmt)).scalar_one()

        items_stmt = (
            stmt.order_by(ContractGroup.created_at.desc()).offset(offset).limit(limit)
        )
        items = list((await db.execute(items_stmt)).scalars().all())
        return items, total

    async def list_by_project(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        data_status: str = "正常",
    ) -> list[ContractGroup]:
        """查询项目下的合同关系聚合。"""
        stmt = (
            select(ContractGroup)
            .options(selectinload(ContractGroup.assets))
            .where(
                ContractGroup.project_id == project_id,
                ContractGroup.data_status == data_status,
            )
            .order_by(ContractGroup.created_at.desc())
        )
        return list((await db.execute(stmt)).scalars().all())

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
            .where(
                ContractLedgerEntry.attributed_owner_party_id == ownership_id,
                Contract.data_status == "正常",
            )
        )
        return float((await db.execute(stmt)).scalar() or 0)

    async def sum_paid_amount_by_ownership_async(
        self,
        db: AsyncSession,
        ownership_id: str,
    ) -> float:
        allocation_totals = self._ledger_allocation_totals_subquery()
        allocated_paid_amount = func.coalesce(allocation_totals.c.paid_amount, 0)
        stmt = (
            select(func.coalesce(func.sum(allocated_paid_amount), 0))
            .select_from(ContractLedgerEntry)
            .join(Contract, ContractLedgerEntry.contract_id == Contract.contract_id)
            .outerjoin(
                allocation_totals,
                allocation_totals.c.target_id == ContractLedgerEntry.entry_id,
            )
            .where(
                ContractLedgerEntry.attributed_owner_party_id == ownership_id,
                Contract.data_status == "正常",
            )
        )
        return float((await db.execute(stmt)).scalar() or 0)

    async def sum_overdue_amount_by_ownership_async(
        self,
        db: AsyncSession,
        ownership_id: str,
    ) -> float:
        allocation_totals = self._ledger_allocation_totals_subquery()
        allocated_paid_amount = func.coalesce(allocation_totals.c.paid_amount, 0)
        overdue_amount = func.greatest(
            ContractLedgerEntry.amount_due - allocated_paid_amount,
            0,
        )
        stmt = (
            select(func.coalesce(func.sum(overdue_amount), 0))
            .select_from(ContractLedgerEntry)
            .join(Contract, ContractLedgerEntry.contract_id == Contract.contract_id)
            .outerjoin(
                allocation_totals,
                allocation_totals.c.target_id == ContractLedgerEntry.entry_id,
            )
            .where(
                ContractLedgerEntry.attributed_owner_party_id == ownership_id,
                Contract.data_status == "正常",
                ContractLedgerEntry._payment_status != "voided",
                ContractLedgerEntry.due_date < _today(),
                allocated_paid_amount < ContractLedgerEntry.amount_due,
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

    async def list_contract_audit_logs(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> list[ContractAuditLog]:
        stmt = (
            select(ContractAuditLog)
            .where(ContractAuditLog.contract_id == contract_id)
            .order_by(
                ContractAuditLog.created_at.desc(), ContractAuditLog.log_id.desc()
            )
        )
        return list((await db.execute(stmt)).scalars().all())

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
        allocation_totals = self._ledger_allocation_totals_subquery()
        allocated_paid_amount = func.coalesce(allocation_totals.c.paid_amount, 0)
        allocation_payment_status = self._ledger_payment_status_expr(
            allocated_paid_amount
        ).label("allocation_payment_status")
        stmt = (
            select(
                ContractLedgerEntry,
                allocated_paid_amount.label("allocation_paid_amount"),
                allocation_payment_status,
                allocation_totals.c.allocation_count,
                allocation_totals.c.flow_occurred_on_dates,
            )
            .outerjoin(
                allocation_totals,
                allocation_totals.c.target_id == ContractLedgerEntry.entry_id,
            )
            .where(ContractLedgerEntry.contract_id == contract_id)
            .order_by(ContractLedgerEntry.year_month.asc())
        )
        rows = (await db.execute(stmt)).all()
        return [self._apply_ledger_payment_facts_from_row(row) for row in rows]

    async def list_ledger_entries_by_attributed_project(
        self,
        db: AsyncSession,
        *,
        project_id: str,
    ) -> list[ContractLedgerEntry]:
        allocation_totals = self._ledger_allocation_totals_subquery()
        allocated_paid_amount = func.coalesce(allocation_totals.c.paid_amount, 0)
        allocation_payment_status = self._ledger_payment_status_expr(
            allocated_paid_amount
        ).label("allocation_payment_status")
        stmt = (
            select(
                ContractLedgerEntry,
                allocated_paid_amount.label("allocation_paid_amount"),
                allocation_payment_status,
                allocation_totals.c.allocation_count,
                allocation_totals.c.flow_occurred_on_dates,
            )
            .join(Contract, ContractLedgerEntry.contract_id == Contract.contract_id)
            .outerjoin(
                allocation_totals,
                allocation_totals.c.target_id == ContractLedgerEntry.entry_id,
            )
            .options(
                joinedload(ContractLedgerEntry.contract).joinedload(
                    Contract.contract_group
                )
            )
            .where(
                ContractLedgerEntry.attributed_project_id == project_id,
                Contract.data_status == "正常",
            )
            .order_by(
                ContractLedgerEntry.year_month.asc(),
                ContractLedgerEntry.contract_id.asc(),
                ContractLedgerEntry.entry_id.asc(),
            )
        )
        rows = (await db.execute(stmt)).all()
        return [self._apply_ledger_payment_facts_from_row(row) for row in rows]

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
        allocation_totals = self._ledger_allocation_totals_subquery()
        allocated_paid_amount = func.coalesce(allocation_totals.c.paid_amount, 0)
        allocation_payment_status = self._ledger_payment_status_expr(
            allocated_paid_amount
        ).label("allocation_payment_status")

        stmt = (
            select(
                ContractLedgerEntry,
                allocated_paid_amount.label("allocation_paid_amount"),
                allocation_payment_status,
                allocation_totals.c.allocation_count,
                allocation_totals.c.flow_occurred_on_dates,
            )
            .outerjoin(
                allocation_totals,
                allocation_totals.c.target_id == ContractLedgerEntry.entry_id,
            )
            .where(ContractLedgerEntry.contract_id == contract_id)
        )
        if year_month_start is not None:
            stmt = stmt.where(ContractLedgerEntry.year_month >= year_month_start)
        if year_month_end is not None:
            stmt = stmt.where(ContractLedgerEntry.year_month <= year_month_end)

        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total: int = (await db.execute(count_stmt)).scalar_one()

        items_stmt = (
            stmt.order_by(ContractLedgerEntry.year_month.asc())
            .offset(offset)
            .limit(limit)
        )
        rows = (await db.execute(items_stmt)).all()
        items = [self._apply_ledger_payment_facts_from_row(row) for row in rows]
        return items, total

    async def query_ledger_entries(
        self,
        db: AsyncSession,
        *,
        ledger_view: str | None = None,
        project_id: str | None = None,
        asset_id: str | None = None,
        party_id: str | None = None,
        contract_id: str | None = None,
        year_month_start: str | None = None,
        year_month_end: str | None = None,
        flow_occurred_on_start: date | None = None,
        flow_occurred_on_end: date | None = None,
        payment_status: str | None = None,
        include_voided: bool = False,
        party_filter: PartyFilter | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ContractLedgerEntry], int]:
        allocation_totals = self._ledger_allocation_totals_subquery()
        allocated_paid_amount = func.coalesce(allocation_totals.c.paid_amount, 0)
        allocation_payment_status = self._ledger_payment_status_expr(
            allocated_paid_amount
        ).label("allocation_payment_status")

        stmt = (
            select(
                ContractLedgerEntry,
                allocated_paid_amount.label("allocation_paid_amount"),
                allocation_payment_status,
                allocation_totals.c.allocation_count,
                allocation_totals.c.flow_occurred_on_dates,
            )
            .join(Contract, ContractLedgerEntry.contract_id == Contract.contract_id)
            .outerjoin(
                allocation_totals,
                allocation_totals.c.target_id == ContractLedgerEntry.entry_id,
            )
        )

        if ledger_view is not None:
            stmt = stmt.where(ContractLedgerEntry.ledger_views.contains([ledger_view]))
        if project_id is not None:
            stmt = stmt.where(ContractLedgerEntry.attributed_project_id == project_id)
        if asset_id is not None:
            stmt = stmt.where(
                ContractLedgerEntry.attributed_asset_ids.contains([asset_id])
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
        if flow_occurred_on_start is not None or flow_occurred_on_end is not None:
            stmt = stmt.where(
                self._ledger_flow_date_exists_clause(
                    flow_occurred_on_start=flow_occurred_on_start,
                    flow_occurred_on_end=flow_occurred_on_end,
                )
            )
        if payment_status is not None:
            stmt = stmt.where(allocation_payment_status == payment_status)
        if not include_voided:
            stmt = stmt.where(ContractLedgerEntry._payment_status != "voided")
        if party_filter is not None:
            stmt = stmt.where(
                self._attribution_scope_clause(ContractLedgerEntry, party_filter)
            )

        stmt = stmt.where(Contract.data_status == "正常")

        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
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
        rows = (await db.execute(items_stmt)).all()
        items = [self._apply_ledger_payment_facts_from_row(row) for row in rows]
        return items, total

    async def get_overdue_with_contract_async(
        self,
        db: AsyncSession,
        *,
        today: Any,
    ) -> list[ContractLedgerEntry]:
        allocation_totals = self._ledger_allocation_totals_subquery()
        allocated_paid_amount = func.coalesce(allocation_totals.c.paid_amount, 0)
        allocation_payment_status = self._ledger_payment_status_expr(
            allocated_paid_amount
        ).label("allocation_payment_status")
        stmt = (
            select(
                ContractLedgerEntry,
                allocated_paid_amount.label("allocation_paid_amount"),
                allocation_payment_status,
                allocation_totals.c.allocation_count,
                allocation_totals.c.flow_occurred_on_dates,
            )
            .join(Contract, ContractLedgerEntry.contract_id == Contract.contract_id)
            .outerjoin(
                allocation_totals,
                allocation_totals.c.target_id == ContractLedgerEntry.entry_id,
            )
            .where(
                ContractLedgerEntry._payment_status != "voided",
                ContractLedgerEntry.ledger_views.contains(["terminal_collection"]),
                ContractLedgerEntry.due_date < today,
                allocated_paid_amount < ContractLedgerEntry.amount_due,
                Contract.data_status == "正常",
            )
            .options(
                selectinload(ContractLedgerEntry.contract).options(
                    selectinload(Contract.contract_group),
                    selectinload(Contract.lease_detail),
                    selectinload(Contract.lessee_party),
                )
            )
            .order_by(ContractLedgerEntry.due_date.asc())
        )
        rows = (await db.execute(stmt)).all()
        return [self._apply_ledger_payment_facts_from_row(row) for row in rows]

    async def get_due_soon_with_contract_async(
        self,
        db: AsyncSession,
        *,
        today: Any,
        warning_date: Any,
    ) -> list[ContractLedgerEntry]:
        allocation_totals = self._ledger_allocation_totals_subquery()
        allocated_paid_amount = func.coalesce(allocation_totals.c.paid_amount, 0)
        allocation_payment_status = self._ledger_payment_status_expr(
            allocated_paid_amount
        ).label("allocation_payment_status")
        stmt = (
            select(
                ContractLedgerEntry,
                allocated_paid_amount.label("allocation_paid_amount"),
                allocation_payment_status,
                allocation_totals.c.allocation_count,
                allocation_totals.c.flow_occurred_on_dates,
            )
            .join(Contract, ContractLedgerEntry.contract_id == Contract.contract_id)
            .outerjoin(
                allocation_totals,
                allocation_totals.c.target_id == ContractLedgerEntry.entry_id,
            )
            .where(
                ContractLedgerEntry._payment_status != "voided",
                ContractLedgerEntry.ledger_views.contains(["terminal_collection"]),
                ContractLedgerEntry.due_date <= warning_date,
                ContractLedgerEntry.due_date >= today,
                allocated_paid_amount <= 0,
                Contract.data_status == "正常",
            )
            .options(
                selectinload(ContractLedgerEntry.contract).options(
                    selectinload(Contract.contract_group),
                    selectinload(Contract.lease_detail),
                    selectinload(Contract.lessee_party),
                )
            )
            .order_by(ContractLedgerEntry.due_date.asc())
        )
        rows = (await db.execute(stmt)).all()
        return [self._apply_ledger_payment_facts_from_row(row) for row in rows]

    async def get_ledger_entry_by_id(
        self,
        db: AsyncSession,
        *,
        entry_id: str,
    ) -> ContractLedgerEntry | None:
        stmt = select(ContractLedgerEntry).where(
            ContractLedgerEntry.entry_id == entry_id
        )
        return (await db.execute(stmt)).scalars().first()

    async def update_ledger_follow_up(
        self,
        db: AsyncSession,
        *,
        entry: ContractLedgerEntry,
        follow_up_status: str | None,
        next_follow_up_date: date | None,
        follow_up_note: str | None,
        commit: bool = True,
    ) -> ContractLedgerEntry:
        entry.follow_up_status = follow_up_status
        entry.next_follow_up_date = next_follow_up_date
        entry.follow_up_note = follow_up_note
        entry.updated_at = _utcnow()
        db.add(entry)
        if commit:
            await db.commit()
        return entry

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

    async def list_service_fee_entries_by_group(
        self,
        db: AsyncSession,
        *,
        group_id: str,
    ) -> list[ServiceFeeLedger]:
        stmt = (
            select(ServiceFeeLedger)
            .where(ServiceFeeLedger.contract_group_id == group_id)
            .order_by(ServiceFeeLedger.year_month.asc())
        )
        return list((await db.execute(stmt)).scalars().all())

    async def list_service_fee_entries_by_attributed_project(
        self,
        db: AsyncSession,
        *,
        project_id: str,
    ) -> list[ServiceFeeLedger]:
        stmt = (
            select(ServiceFeeLedger)
            .join(Contract, ServiceFeeLedger.agency_contract_id == Contract.contract_id)
            .options(
                joinedload(ServiceFeeLedger.agency_contract).joinedload(
                    Contract.contract_group
                ),
            )
            .where(
                ServiceFeeLedger.attributed_project_id == project_id,
                Contract.data_status == "正常",
            )
            .order_by(
                ServiceFeeLedger.year_month.asc(),
                ServiceFeeLedger.agency_contract_id.asc(),
                ServiceFeeLedger.service_fee_entry_id.asc(),
            )
        )
        return list((await db.execute(stmt)).scalars().all())

    async def create_service_fee_entry(
        self,
        db: AsyncSession,
        *,
        data: dict[str, Any],
        commit: bool = True,
    ) -> ServiceFeeLedger:
        entry = ServiceFeeLedger(**data)
        db.add(entry)
        await db.flush()
        if commit:
            await db.commit()
            await db.refresh(entry)
        return entry

    async def create_payment_flow(
        self,
        db: AsyncSession,
        *,
        data: dict[str, Any],
        commit: bool = True,
    ) -> OperationalPaymentFlow:
        flow = OperationalPaymentFlow(**data)
        db.add(flow)
        await db.flush()
        if commit:
            await db.commit()
            await db.refresh(flow)
        return flow

    async def get_payment_flow(
        self,
        db: AsyncSession,
        *,
        flow_id: str,
        for_update: bool = False,
    ) -> OperationalPaymentFlow | None:
        stmt = select(OperationalPaymentFlow).where(
            OperationalPaymentFlow.flow_id == flow_id
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await db.execute(stmt)).scalars().first()

    async def list_payment_allocations_by_flow(
        self,
        db: AsyncSession,
        *,
        flow_id: str,
    ) -> list[PaymentAllocation]:
        stmt = select(PaymentAllocation).where(PaymentAllocation.flow_id == flow_id)
        return list((await db.execute(stmt)).scalars().all())

    async def list_payment_flows_by_target(
        self,
        db: AsyncSession,
        *,
        target_type: str,
        target_id: str,
    ) -> list[OperationalPaymentFlow]:
        stmt = (
            select(OperationalPaymentFlow)
            .join(
                PaymentAllocation,
                PaymentAllocation.flow_id == OperationalPaymentFlow.flow_id,
            )
            .where(
                PaymentAllocation.target_type == target_type,
                PaymentAllocation.target_id == target_id,
            )
            .options(selectinload(OperationalPaymentFlow.allocations))
            .distinct()
            .order_by(
                OperationalPaymentFlow.created_at.desc(),
                OperationalPaymentFlow.flow_id.desc(),
            )
        )
        return list((await db.execute(stmt)).scalars().all())

    async def replace_payment_allocations(
        self,
        db: AsyncSession,
        *,
        flow_id: str,
        rows: list[dict[str, Any]],
        commit: bool = False,
    ) -> list[PaymentAllocation]:
        await db.execute(
            PaymentAllocation.__table__.delete().where(
                PaymentAllocation.flow_id == flow_id
            )
        )
        allocations: list[PaymentAllocation] = []
        for row in rows:
            allocation = PaymentAllocation()
            allocation.flow_id = flow_id
            allocation.target_type = str(row["target_type"])
            allocation.target_id = str(row["target_id"])
            allocation.year_month = str(row["year_month"])
            allocation.amount = row["amount"]
            allocations.append(allocation)
            db.add(allocation)
        await db.flush()
        if commit:
            await db.commit()
            for allocation in allocations:
                await db.refresh(allocation)
        return allocations

    async def get_ledger_entries_by_ids(
        self,
        db: AsyncSession,
        *,
        entry_ids: list[str],
        for_update: bool = False,
    ) -> list[ContractLedgerEntry]:
        if not entry_ids:
            return []
        stmt = select(ContractLedgerEntry).where(
            ContractLedgerEntry.entry_id.in_(entry_ids)
        )
        if for_update:
            stmt = stmt.with_for_update()
        return list((await db.execute(stmt)).scalars().all())

    async def get_service_fee_entries_by_ids(
        self,
        db: AsyncSession,
        *,
        entry_ids: list[str],
        for_update: bool = False,
    ) -> list[ServiceFeeLedger]:
        if not entry_ids:
            return []
        stmt = select(ServiceFeeLedger).where(
            ServiceFeeLedger.service_fee_entry_id.in_(entry_ids)
        )
        if for_update:
            stmt = stmt.with_for_update()
        return list((await db.execute(stmt)).scalars().all())

    async def sum_active_allocations_by_target(
        self,
        db: AsyncSession,
        *,
        target_type: str,
        target_id: str,
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
            .join(
                OperationalPaymentFlow,
                OperationalPaymentFlow.flow_id == PaymentAllocation.flow_id,
            )
            .where(
                PaymentAllocation.target_type == target_type,
                PaymentAllocation.target_id == target_id,
                OperationalPaymentFlow.status == "active",
            )
        )
        return Decimal(str((await db.execute(stmt)).scalar() or 0))

    async def _replace_assets(
        self,
        db: AsyncSession,
        group_id: str,
        asset_ids: list[str],
    ) -> None:
        """整体替换合同组的资产关联（先删后插）。"""
        await db.execute(
            contract_group_assets.delete().where(
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
            await db.execute(contract_group_assets.insert(), rows)

    async def list_active_group_bindings_for_assets(
        self,
        db: AsyncSession,
        *,
        group_id: str | None,
        asset_ids: list[str],
    ) -> list[dict[str, str | None]]:
        if not asset_ids:
            return []

        stmt = (
            select(
                contract_group_assets.c.asset_id,
                ContractGroup.project_id,
                ContractGroup.contract_group_id,
                ContractGroup.group_code,
            )
            .join(
                ContractGroup,
                ContractGroup.contract_group_id
                == contract_group_assets.c.contract_group_id,
            )
            .where(
                contract_group_assets.c.asset_id.in_(asset_ids),
                ContractGroup.data_status == "正常",
            )
        )
        if group_id is not None:
            stmt = stmt.where(ContractGroup.contract_group_id != group_id)

        rows = (await db.execute(stmt)).all()
        return [
            {
                "asset_id": str(asset_id),
                "project_id": str(project_id) if project_id is not None else None,
                "contract_group_id": str(conflict_group_id),
                "group_code": str(group_code),
            }
            for asset_id, project_id, conflict_group_id, group_code in rows
        ]

    async def list_current_project_bindings_for_assets(
        self,
        db: AsyncSession,
        *,
        asset_ids: list[str],
    ) -> list[dict[str, str | None]]:
        if not asset_ids:
            return []

        stmt = (
            select(Asset.id, ProjectAsset.project_id)
            .outerjoin(
                ProjectAsset,
                and_(
                    ProjectAsset.asset_id == Asset.id,
                    ProjectAsset.valid_to.is_(None),
                ),
            )
            .where(Asset.id.in_(asset_ids))
        )
        rows = (await db.execute(stmt)).all()
        return [
            {
                "asset_id": str(asset_id),
                "project_id": str(project_id) if project_id is not None else None,
            }
            for asset_id, project_id in rows
        ]

    async def list_asset_ids_for_group(
        self,
        db: AsyncSession,
        *,
        group_id: str,
    ) -> list[str]:
        stmt = select(contract_group_assets.c.asset_id).where(
            contract_group_assets.c.contract_group_id == group_id
        )
        return [str(asset_id) for asset_id in (await db.execute(stmt)).scalars().all()]

    async def list_contract_asset_ids_by_group(
        self,
        db: AsyncSession,
        *,
        group_id: str,
    ) -> list[ContractAssetIdsByGroupRow]:
        stmt = (
            select(Contract.contract_id, contract_assets.c.asset_id)
            .join(
                contract_assets,
                contract_assets.c.contract_id == Contract.contract_id,
            )
            .where(
                Contract.contract_group_id == group_id,
                Contract.data_status == "正常",
            )
            .order_by(Contract.contract_id.asc(), contract_assets.c.asset_id.asc())
        )
        rows = (await db.execute(stmt)).all()
        grouped: dict[str, list[str]] = {}
        for contract_id, asset_id in rows:
            grouped.setdefault(str(contract_id), []).append(str(asset_id))
        return [
            {"contract_id": contract_id, "asset_ids": asset_ids}
            for contract_id, asset_ids in grouped.items()
        ]


contract_group_crud = CRUDContractGroup()
