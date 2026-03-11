"""
合同台账 V2 Service（REQ-RNT-003 M2）。
"""

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import BusinessValidationError, ResourceNotFoundError
from src.crud.contract import contract_crud
from src.crud.contract_group import contract_group_crud
from src.models.contract_group import (
    ContractLedgerEntry,
    ContractLifecycleStatus,
    ContractRentTerm,
)

logger = logging.getLogger(__name__)
_MANUAL_LEDGER_PAYMENT_STATUSES = frozenset({"unpaid", "paid", "overdue", "partial"})


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _month_end(value: date) -> date:
    return _next_month(value) - timedelta(days=1)


def _expand_year_months(rent_terms: list[ContractRentTerm]) -> list[str]:
    year_months: list[str] = []
    seen: set[str] = set()
    for term in sorted(rent_terms, key=lambda item: item.sort_order):
        current = _month_start(term.start_date)
        end = _month_start(term.end_date)
        while current <= end:
            year_month = current.strftime("%Y-%m")
            if year_month not in seen:
                year_months.append(year_month)
                seen.add(year_month)
            current = _next_month(current)
    return year_months


def _get_rent_term_for_month(
    rent_terms: list[ContractRentTerm],
    month_date: date,
) -> ContractRentTerm | None:
    month_end = _month_end(month_date)
    for term in sorted(rent_terms, key=lambda item: item.sort_order):
        if term.start_date <= month_end and month_date <= term.end_date:
            return term
    return None


def _calculate_due_date(month_date: date, payment_cycle: str) -> date:
    if payment_cycle == "季付":
        quarter_start_month = ((month_date.month - 1) // 3) * 3 + 1
        return date(month_date.year, quarter_start_month, 1)
    if payment_cycle == "半年付":
        half_year_start_month = 1 if month_date.month <= 6 else 7
        return date(month_date.year, half_year_start_month, 1)
    if payment_cycle == "年付":
        return date(month_date.year, 1, 1)
    return _month_start(month_date)


def _resolve_amount_due(rent_term: ContractRentTerm) -> Decimal:
    if rent_term.total_monthly_amount is not None:
        return rent_term.total_monthly_amount
    return rent_term.monthly_rent


class ContractLedgerServiceV2:
    """合同月度台账服务。"""

    @staticmethod
    def _build_ledger_entry_data(
        *,
        contract_id: str,
        year_month: str,
        due_date: date,
        amount_due: Decimal,
        currency_code: str,
        is_tax_included: bool,
        tax_rate: Decimal | None,
        now: datetime,
    ) -> dict[str, Any]:
        return {
            "entry_id": str(uuid.uuid4()),
            "contract_id": contract_id,
            "year_month": year_month,
            "due_date": due_date,
            "amount_due": amount_due,
            "currency_code": currency_code,
            "is_tax_included": is_tax_included,
            "tax_rate": tax_rate,
            "payment_status": "unpaid",
            "paid_amount": Decimal("0"),
            "notes": None,
            "created_at": now,
            "updated_at": now,
        }

    async def generate_ledger_on_activation(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> list[ContractLedgerEntry]:
        contract = await contract_crud.get(db, contract_id)
        if contract is None:
            raise ResourceNotFoundError("合同", contract_id)

        lease_detail = getattr(contract, "lease_detail", None)
        if lease_detail is None:
            logger.info("合同缺少 lease_detail，跳过台账生成: %s", contract_id)
            return []

        rent_terms = await contract_group_crud.list_rent_terms_by_contract(
            db,
            contract_id=contract_id,
        )
        if not rent_terms:
            logger.warning("合同未配置 RentTerm，跳过台账生成: %s", contract_id)
            return []

        all_year_months = _expand_year_months(rent_terms)
        existing_year_months = await contract_group_crud.get_existing_ledger_year_months(
            db,
            contract_id=contract_id,
            year_months=all_year_months,
        )

        created_entries: list[ContractLedgerEntry] = []
        now = _utcnow()
        payment_cycle = lease_detail.payment_cycle or "月付"

        for year_month in all_year_months:
            if year_month in existing_year_months:
                continue

            month_date = datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
            rent_term = _get_rent_term_for_month(rent_terms, month_date)
            if rent_term is None:
                continue

            amount_due = _resolve_amount_due(rent_term)
            entry = await contract_group_crud.create_ledger_entry(
                db,
                data=self._build_ledger_entry_data(
                    contract_id=contract_id,
                    year_month=year_month,
                    due_date=_calculate_due_date(month_date, payment_cycle),
                    amount_due=amount_due,
                    currency_code=contract.currency_code,
                    is_tax_included=contract.is_tax_included,
                    tax_rate=contract.tax_rate,
                    now=now,
                ),
                commit=False,
            )
            created_entries.append(entry)

        return created_entries

    async def query_ledger(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        year_month_start: str | None = None,
        year_month_end: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        items, total = await contract_group_crud.get_ledger_by_contract(
            db,
            contract_id=contract_id,
            year_month_start=year_month_start,
            year_month_end=year_month_end,
            offset=offset,
            limit=limit,
        )
        return {
            "items": items,
            "total": total,
            "offset": offset,
            "limit": limit,
        }

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
    ) -> dict[str, Any]:
        if not any(
            [
                asset_id is not None,
                party_id is not None,
                contract_id is not None,
                year_month_start is not None,
            ]
        ):
            raise BusinessValidationError(
                "asset_id、party_id、contract_id、year_month_start 至少需要一个筛选条件"
            )
        if (
            year_month_start is not None
            and year_month_end is not None
            and year_month_start > year_month_end
        ):
            raise BusinessValidationError("开始账期不能晚于结束账期")

        items, total = await contract_group_crud.query_ledger_entries(
            db,
            asset_id=asset_id,
            party_id=party_id,
            contract_id=contract_id,
            year_month_start=year_month_start,
            year_month_end=year_month_end,
            payment_status=payment_status,
            include_voided=include_voided,
            offset=offset,
            limit=limit,
        )
        return {
            "items": items,
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    async def recalculate_ledger(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        commit: bool = True,
    ) -> dict[str, Any]:
        contract = await contract_crud.get(db, contract_id)
        if contract is None:
            raise ResourceNotFoundError("合同", contract_id)
        if contract.status != ContractLifecycleStatus.ACTIVE:
            raise BusinessValidationError("仅生效合同允许重算台账")

        rent_terms = await contract_group_crud.list_rent_terms_by_contract(
            db,
            contract_id=contract_id,
        )
        existing_entries = await contract_group_crud.list_ledger_entries_by_contract(
            db,
            contract_id=contract_id,
        )

        lease_detail = getattr(contract, "lease_detail", None)
        payment_cycle = getattr(lease_detail, "payment_cycle", None) or "月付"
        now = _utcnow()
        existing_by_month = {
            entry.year_month: entry for entry in existing_entries
        }
        target_year_months = _expand_year_months(rent_terms)
        target_year_month_set = set(target_year_months)

        created = 0
        updated = 0
        voided = 0
        skipped_entries: list[dict[str, str]] = []

        for year_month in target_year_months:
            month_date = datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
            rent_term = _get_rent_term_for_month(rent_terms, month_date)
            if rent_term is None:
                continue

            amount_due = _resolve_amount_due(rent_term)
            due_date = _calculate_due_date(month_date, payment_cycle)
            existing_entry = existing_by_month.get(year_month)

            if existing_entry is None:
                await contract_group_crud.create_ledger_entry(
                    db,
                    data=self._build_ledger_entry_data(
                        contract_id=contract_id,
                        year_month=year_month,
                        due_date=due_date,
                        amount_due=amount_due,
                        currency_code=contract.currency_code,
                        is_tax_included=contract.is_tax_included,
                        tax_rate=contract.tax_rate,
                        now=now,
                    ),
                    commit=False,
                )
                created += 1
                continue

            if existing_entry.payment_status == "voided":
                existing_entry.amount_due = amount_due
                existing_entry.due_date = due_date
                existing_entry.payment_status = "unpaid"
                existing_entry.paid_amount = Decimal("0")
                existing_entry.updated_at = now
                updated += 1
                continue

            requires_update = (
                existing_entry.amount_due != amount_due
                or existing_entry.due_date != due_date
            )
            if not requires_update:
                continue

            if existing_entry.payment_status in {"paid", "partial"}:
                skipped_entries.append(
                    {
                        "entry_id": existing_entry.entry_id,
                        "year_month": existing_entry.year_month,
                        "payment_status": existing_entry.payment_status,
                        "reason": "paid_or_partial_entry_requires_manual_resolution",
                    }
                )
                continue

            existing_entry.amount_due = amount_due
            existing_entry.due_date = due_date
            existing_entry.updated_at = now
            updated += 1

        for existing_entry in existing_entries:
            if existing_entry.year_month in target_year_month_set:
                continue
            if existing_entry.payment_status == "voided":
                continue
            if existing_entry.payment_status in {"paid", "partial"}:
                skipped_entries.append(
                    {
                        "entry_id": existing_entry.entry_id,
                        "year_month": existing_entry.year_month,
                        "payment_status": existing_entry.payment_status,
                        "reason": "paid_or_partial_entry_requires_manual_resolution",
                    }
                )
                continue

            existing_entry.payment_status = "voided"
            existing_entry.updated_at = now
            voided += 1

        await db.flush()
        if commit:
            await db.commit()

        return {
            "created": created,
            "updated": updated,
            "voided": voided,
            "skipped_entries": skipped_entries,
        }

    async def batch_update_status(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        entry_ids: list[str],
        payment_status: str,
        paid_amount: Decimal | None = None,
        notes: str | None = None,
    ) -> list[ContractLedgerEntry]:
        if payment_status == "voided":
            raise BusinessValidationError("voided 为系统保留状态，不允许人工批量更新")
        if payment_status not in _MANUAL_LEDGER_PAYMENT_STATUSES:
            raise BusinessValidationError(
                "payment_status 必须为 "
                f"{sorted(_MANUAL_LEDGER_PAYMENT_STATUSES)} 之一"
            )

        return await contract_group_crud.batch_update_ledger_status(
            db,
            contract_id=contract_id,
            entry_ids=entry_ids,
            payment_status=payment_status,
            paid_amount=paid_amount,
            notes=notes,
        )


ledger_service_v2 = ContractLedgerServiceV2()
