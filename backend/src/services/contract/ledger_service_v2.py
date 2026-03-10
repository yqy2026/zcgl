"""
合同台账 V2 Service（REQ-RNT-003 M2）。
"""

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import ResourceNotFoundError
from src.crud.contract import contract_crud
from src.crud.contract_group import contract_group_crud
from src.models.contract_group import ContractLedgerEntry, ContractRentTerm

logger = logging.getLogger(__name__)


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


class ContractLedgerServiceV2:
    """合同月度台账服务。"""

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

            amount_due = (
                rent_term.total_monthly_amount
                if rent_term.total_monthly_amount is not None
                else rent_term.monthly_rent
            )
            entry = await contract_group_crud.create_ledger_entry(
                db,
                data={
                    "entry_id": str(uuid.uuid4()),
                    "contract_id": contract_id,
                    "year_month": year_month,
                    "due_date": _calculate_due_date(month_date, payment_cycle),
                    "amount_due": amount_due,
                    "currency_code": contract.currency_code,
                    "is_tax_included": contract.is_tax_included,
                    "tax_rate": contract.tax_rate,
                    "payment_status": "unpaid",
                    "paid_amount": Decimal("0"),
                    "notes": None,
                    "created_at": now,
                    "updated_at": now,
                },
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
        return await contract_group_crud.batch_update_ledger_status(
            db,
            contract_id=contract_id,
            entry_ids=entry_ids,
            payment_status=payment_status,
            paid_amount=paid_amount,
            notes=notes,
        )


ledger_service_v2 = ContractLedgerServiceV2()
