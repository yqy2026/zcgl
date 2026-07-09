"""
合同台账 V2 Service（REQ-RNT-003 M2）。
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import (
    BusinessValidationError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from src.crud.contract import contract_crud
from src.crud.contract_group import contract_group_crud
from src.models.contract_group import (
    Contract,
    ContractGroup,
    ContractLedgerEntry,
    ContractLifecycleStatus,
    ContractRentTerm,
    GroupRelationType,
    LedgerView,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StalePaidLedgerEntry:
    """Paid or partially paid ledger entry that no longer matches rent terms."""

    entry_id: str
    year_month: str
    payment_status: str
    reason: str


@dataclass(frozen=True)
class LedgerAttributionSnapshot:
    """Frozen attribution stamped on newly generated ledger entries."""

    project_id: str | None
    owner_party_id: str | None
    operator_party_id: str | None
    asset_ids: list[str]

    def as_entry_data(self) -> dict[str, Any]:
        return {
            "attributed_project_id": self.project_id,
            "attributed_owner_party_id": self.owner_party_id,
            "attributed_operator_party_id": self.operator_party_id,
            "attributed_asset_ids": self.asset_ids,
        }


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


def compute_expected_year_months(rent_terms: list[ContractRentTerm]) -> list[str]:
    """公开给补偿任务复用的账期展开逻辑。"""
    return _expand_year_months(rent_terms)


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


def _as_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _has_registered_receipt(entry: Any) -> bool:
    return _as_decimal(getattr(entry, "paid_amount", Decimal("0"))) > 0


def _has_active_payment_allocation(entry: Any) -> bool:
    try:
        return int(getattr(entry, "active_allocation_count", 0) or 0) > 0
    except (TypeError, ValueError):
        return False


def has_recalculation_protected_payment_fact(entry: Any) -> bool:
    return _has_registered_receipt(entry) or _has_active_payment_allocation(entry)


def _manual_resolution_reason(
    entry: Any,
    *,
    outside_current_terms: bool = False,
) -> str:
    if _has_active_payment_allocation(entry) and not _has_registered_receipt(entry):
        if outside_current_terms:
            return "allocated_entry_outside_current_terms"
        return "allocated_entry_requires_manual_resolution"
    if outside_current_terms:
        return "paid_or_partial_entry_outside_current_terms"
    return "paid_or_partial_entry_requires_manual_resolution"


def _parse_year_month(year_month: str) -> date | None:
    try:
        return datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_optional_date(value: date | datetime | str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise BusinessValidationError("date filters must use ISO date format") from exc


def find_stale_paid_or_partial_ledger_entries(
    *,
    rent_terms: list[ContractRentTerm],
    ledger_entries: list[ContractLedgerEntry],
    payment_cycle: str,
) -> list[StalePaidLedgerEntry]:
    """Derive protected ledger entries that need manual correction after term changes."""
    stale_entries: list[StalePaidLedgerEntry] = []
    target_year_month_set = set(_expand_year_months(rent_terms))

    for entry in ledger_entries:
        if not has_recalculation_protected_payment_fact(entry):
            continue
        payment_status = str(getattr(entry, "payment_status", "") or "").strip()

        year_month = str(getattr(entry, "year_month", "") or "").strip()
        if year_month not in target_year_month_set:
            stale_entries.append(
                StalePaidLedgerEntry(
                    entry_id=str(getattr(entry, "entry_id", "")),
                    year_month=year_month,
                    payment_status=payment_status,
                    reason=_manual_resolution_reason(entry, outside_current_terms=True),
                )
            )
            continue

        month_date = _parse_year_month(year_month)
        if month_date is None:
            stale_entries.append(
                StalePaidLedgerEntry(
                    entry_id=str(getattr(entry, "entry_id", "")),
                    year_month=year_month,
                    payment_status=payment_status,
                    reason=_manual_resolution_reason(entry),
                )
            )
            continue

        rent_term = _get_rent_term_for_month(rent_terms, month_date)
        if rent_term is None:
            continue

        amount_due = _resolve_amount_due(rent_term)
        due_date = _calculate_due_date(month_date, payment_cycle)
        if (
            _as_decimal(getattr(entry, "amount_due", Decimal("0"))) != amount_due
            or getattr(entry, "due_date", None) != due_date
        ):
            stale_entries.append(
                StalePaidLedgerEntry(
                    entry_id=str(getattr(entry, "entry_id", "")),
                    year_month=year_month,
                    payment_status=payment_status,
                    reason=_manual_resolution_reason(entry),
                )
            )

    return stale_entries


def _asset_ids_from(items: list[Any] | None) -> list[str]:
    if items is None:
        return []
    asset_ids: list[str] = []
    for item in items:
        asset_id = getattr(item, "id", None)
        if asset_id is not None:
            asset_ids.append(str(asset_id))
    return asset_ids


def derive_ledger_views_for_contract(contract: Contract) -> list[str]:
    """Map contract business role to operations-ledger view memberships."""
    relation_type = getattr(contract, "group_relation_type", None)
    if relation_type in {GroupRelationType.DOWNSTREAM, "DOWNSTREAM", "??"}:
        return [
            LedgerView.TERMINAL_COLLECTION.value,
            LedgerView.OPERATOR_INCOME.value,
        ]
    if relation_type in {GroupRelationType.DIRECT_LEASE, "DIRECT_LEASE", "??"}:
        return [LedgerView.TERMINAL_COLLECTION.value]
    if relation_type in {GroupRelationType.UPSTREAM, "UPSTREAM", "??"}:
        return [LedgerView.OPERATOR_COST.value]
    return []


class ContractLedgerServiceV2:
    """合同月度台账服务。"""

    async def _resolve_attribution_snapshot(
        self,
        db: AsyncSession,
        *,
        contract: Contract,
    ) -> LedgerAttributionSnapshot:
        group = await contract_group_crud.get_with_assets(
            db,
            str(contract.contract_group_id),
        )
        if group is None:
            raise ResourceNotFoundError(
                "ContractGroup", str(contract.contract_group_id)
            )
        return self._build_attribution_snapshot(contract=contract, group=group)

    @staticmethod
    def _build_attribution_snapshot(
        *,
        contract: Contract,
        group: ContractGroup,
    ) -> LedgerAttributionSnapshot:
        asset_ids = _asset_ids_from(getattr(contract, "assets", None))
        if not asset_ids:
            asset_ids = _asset_ids_from(getattr(group, "assets", None))
        return LedgerAttributionSnapshot(
            project_id=getattr(group, "project_id", None),
            owner_party_id=getattr(group, "owner_party_id", None),
            operator_party_id=getattr(group, "operator_party_id", None),
            asset_ids=asset_ids,
        )

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
        attribution: LedgerAttributionSnapshot,
        ledger_views: list[str],
        now: datetime,
    ) -> dict[str, Any]:
        return {
            "entry_id": str(uuid.uuid4()),
            "contract_id": contract_id,
            "year_month": year_month,
            "due_date": due_date,
            "amount_due": amount_due,
            "ledger_views": ledger_views,
            "currency_code": currency_code,
            "is_tax_included": is_tax_included,
            "tax_rate": tax_rate,
            "payment_status": "unpaid",
            "paid_amount": Decimal("0"),
            **attribution.as_entry_data(),
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
        existing_year_months = (
            await contract_group_crud.get_existing_ledger_year_months(
                db,
                contract_id=contract_id,
                year_months=all_year_months,
            )
        )

        created_entries: list[ContractLedgerEntry] = []
        now = _utcnow()
        payment_cycle = lease_detail.payment_cycle or "月付"
        attribution: LedgerAttributionSnapshot | None = None
        ledger_views = derive_ledger_views_for_contract(contract)
        if not ledger_views:
            raise BusinessValidationError("??????????????")

        for year_month in all_year_months:
            if year_month in existing_year_months:
                continue

            month_date = datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
            rent_term = _get_rent_term_for_month(rent_terms, month_date)
            if rent_term is None:
                continue

            amount_due = _resolve_amount_due(rent_term)
            if attribution is None:
                attribution = await self._resolve_attribution_snapshot(
                    db,
                    contract=contract,
                )
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
                    attribution=attribution,
                    ledger_views=ledger_views,
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
        ledger_view: str | None = None,
        project_id: str | None = None,
        asset_id: str | None = None,
        party_id: str | None = None,
        contract_id: str | None = None,
        year_month_start: str | None = None,
        year_month_end: str | None = None,
        flow_occurred_on_start: date | datetime | str | None = None,
        flow_occurred_on_end: date | datetime | str | None = None,
        payment_status: str | None = None,
        include_voided: bool = False,
        offset: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        normalized_flow_occurred_on_start = _parse_optional_date(flow_occurred_on_start)
        normalized_flow_occurred_on_end = _parse_optional_date(flow_occurred_on_end)
        if not any(
            [
                project_id is not None,
                asset_id is not None,
                party_id is not None,
                contract_id is not None,
                year_month_start is not None,
                normalized_flow_occurred_on_start is not None,
                normalized_flow_occurred_on_end is not None,
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

        if (
            normalized_flow_occurred_on_start is not None
            and normalized_flow_occurred_on_end is not None
            and normalized_flow_occurred_on_start > normalized_flow_occurred_on_end
        ):
            raise BusinessValidationError(
                "flow occurred start date cannot be after end date"
            )

        items, total = await contract_group_crud.query_ledger_entries(
            db,
            ledger_view=ledger_view,
            project_id=project_id,
            asset_id=asset_id,
            party_id=party_id,
            contract_id=contract_id,
            year_month_start=year_month_start,
            year_month_end=year_month_end,
            flow_occurred_on_start=normalized_flow_occurred_on_start,
            flow_occurred_on_end=normalized_flow_occurred_on_end,
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
        attribution: LedgerAttributionSnapshot | None = None
        ledger_views = derive_ledger_views_for_contract(contract)
        if not ledger_views:
            raise BusinessValidationError("??????????????")
        existing_by_month = {entry.year_month: entry for entry in existing_entries}
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
                if attribution is None:
                    attribution = await self._resolve_attribution_snapshot(
                        db,
                        contract=contract,
                    )
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
                        attribution=attribution,
                        ledger_views=ledger_views,
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

            if has_recalculation_protected_payment_fact(existing_entry):
                skipped_entries.append(
                    {
                        "entry_id": existing_entry.entry_id,
                        "year_month": existing_entry.year_month,
                        "payment_status": existing_entry.payment_status,
                        "reason": _manual_resolution_reason(existing_entry),
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
            if has_recalculation_protected_payment_fact(existing_entry):
                skipped_entries.append(
                    {
                        "entry_id": existing_entry.entry_id,
                        "year_month": existing_entry.year_month,
                        "payment_status": existing_entry.payment_status,
                        "reason": _manual_resolution_reason(existing_entry),
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
        paid_amount: Decimal,
        notes: str | None = None,
    ) -> list[ContractLedgerEntry]:
        return await contract_group_crud.batch_update_ledger_status(
            db,
            contract_id=contract_id,
            entry_ids=entry_ids,
            paid_amount=paid_amount,
            notes=notes,
        )

    async def update_follow_up(
        self,
        db: AsyncSession,
        *,
        entry_id: str,
        follow_up_status: str | None,
        next_follow_up_date: date | None = None,
        follow_up_note: str | None = None,
    ) -> ContractLedgerEntry:
        entry = await contract_group_crud.get_ledger_entry_by_id(db, entry_id=entry_id)
        if entry is None:
            raise ResourceNotFoundError("台账条目不存在")

        ledger_views = set(getattr(entry, "ledger_views", []) or [])
        if LedgerView.TERMINAL_COLLECTION.value not in ledger_views:
            raise OperationNotAllowedError("仅终端租户收缴台账可维护跟进状态")

        return await contract_group_crud.update_ledger_follow_up(
            db,
            entry=entry,
            follow_up_status=follow_up_status,
            next_follow_up_date=next_follow_up_date,
            follow_up_note=follow_up_note,
        )

    async def reverse_correction_source_entries(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        year_month_start: str,
    ) -> list[str]:
        entries = await contract_group_crud.list_ledger_entries_by_contract(
            db,
            contract_id=contract_id,
        )
        voided_entry_ids: list[str] = []
        now = _utcnow()

        for entry in entries:
            if entry.year_month < year_month_start:
                continue
            if entry.payment_status == "voided":
                continue
            if has_recalculation_protected_payment_fact(entry):
                raise OperationNotAllowedError("存在已支付账期，需先人工处理")
            entry.payment_status = "voided"
            entry.updated_at = now
            voided_entry_ids.append(entry.entry_id)

        await db.flush()
        return voided_entry_ids


ledger_service_v2 = ContractLedgerServiceV2()
