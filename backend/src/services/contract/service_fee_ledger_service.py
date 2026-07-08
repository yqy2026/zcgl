"""Agency service-fee ledger derivation service."""

from __future__ import annotations

import logging
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import BusinessValidationError, ResourceNotFoundError
from src.crud.contract import contract_crud
from src.crud.contract_group import contract_group_crud
from src.models.contract_group import (
    GroupRelationType,
    RevenueMode,
    derive_ledger_payment_status,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _as_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _as_date(value: Any, *, default: date) -> date:
    if value is None:
        return default
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise BusinessValidationError(
            "entrusted contract effective date must be an ISO date"
        ) from exc


def _month_range(year_month: str) -> tuple[date, date]:
    try:
        year_text, month_text = year_month.split("-", maxsplit=1)
        year = int(year_text)
        month = int(month_text)
        return date(year, month, 1), date(year, month, monthrange(year, month)[1])
    except (TypeError, ValueError) as exc:
        raise BusinessValidationError(
            "service fee source ledger year_month must use YYYY-MM"
        ) from exc


@dataclass
class _MonthlyFeeBucket:
    year_month: str
    agency_contract_id: str
    agency_agreement_contract_id: str
    service_fee_ratio: Decimal
    attributed_project_id: str | None
    attributed_owner_party_id: str | None
    attributed_operator_party_id: str | None
    attributed_asset_ids: list[str] | None
    currency_code: str
    calculation_base_amount: Decimal = Decimal("0")
    source_ledger_ids: list[str] = field(default_factory=list)

    def add_source(self, source_entry: Any, agency_contract_id: str) -> None:
        if not self.agency_contract_id:
            self.agency_contract_id = agency_contract_id
        self.calculation_base_amount += _as_decimal(
            getattr(source_entry, "paid_amount", Decimal("0"))
        )
        self.source_ledger_ids.append(str(source_entry.entry_id))


class ServiceFeeLedgerService:
    """Generate monthly service-fee receivables from direct-lease rent receipts."""

    async def sync_contract_group(
        self,
        db: AsyncSession,
        *,
        group_id: str,
        commit: bool = True,
    ) -> dict[str, int]:
        group = await contract_group_crud.get(db, group_id)
        if group is None:
            raise ResourceNotFoundError("contract group", group_id)
        if getattr(group, "revenue_mode", None) != RevenueMode.AGENCY:
            return {"created": 0, "updated": 0, "voided": 0, "source_mismatches": 0}

        contracts = await contract_crud.list_by_group(
            db,
            group_id=group_id,
            load_details=True,
        )
        entrusted_contracts = [
            contract
            for contract in contracts
            if getattr(contract, "group_relation_type", None)
            == GroupRelationType.ENTRUSTED
            and getattr(contract, "agency_detail", None) is not None
        ]
        if not entrusted_contracts:
            raise BusinessValidationError(
                "Agency group requires at least one entrusted contract with service fee ratio"
            )

        direct_lease_contracts = [
            contract
            for contract in contracts
            if getattr(contract, "group_relation_type", None)
            == GroupRelationType.DIRECT_LEASE
        ]

        buckets = await self._collect_monthly_buckets(
            db,
            direct_lease_contracts=direct_lease_contracts,
            entrusted_contracts=entrusted_contracts,
        )
        existing_entries = await contract_group_crud.list_service_fee_entries_by_group(
            db,
            group_id=group_id,
        )
        existing_by_key = {self._entry_key(entry): entry for entry in existing_entries}

        created = 0
        updated = 0
        voided = 0
        source_mismatches = 0
        seen_keys: set[tuple[str, str, str | None, str]] = set()
        now = _utcnow()

        for key, bucket in buckets.items():
            seen_keys.add(key)
            ratio = bucket.service_fee_ratio
            amount_due = _quantize_money(bucket.calculation_base_amount * ratio)
            existing_entry = existing_by_key.get(key)
            source_ledger_ids = sorted(bucket.source_ledger_ids)
            payment_status = derive_ledger_payment_status(
                amount_due=amount_due,
                paid_amount=getattr(existing_entry, "paid_amount", Decimal("0"))
                if existing_entry is not None
                else Decimal("0"),
                stored_status=getattr(existing_entry, "payment_status", None),
            )

            data = {
                "contract_group_id": group_id,
                "agency_contract_id": bucket.agency_contract_id,
                "agency_agreement_contract_id": bucket.agency_agreement_contract_id,
                "source_ledger_ids": source_ledger_ids,
                "year_month": bucket.year_month,
                "amount_due": amount_due,
                "payment_status": payment_status,
                "currency_code": bucket.currency_code,
                "service_fee_ratio": ratio,
                "calculation_base_amount": _quantize_money(
                    bucket.calculation_base_amount
                ),
                "attributed_project_id": bucket.attributed_project_id,
                "attributed_owner_party_id": bucket.attributed_owner_party_id,
                "attributed_operator_party_id": bucket.attributed_operator_party_id,
                "attributed_asset_ids": bucket.attributed_asset_ids,
            }

            if existing_entry is None:
                await contract_group_crud.create_service_fee_entry(
                    db,
                    data={
                        **data,
                        "paid_amount": Decimal("0"),
                        "created_at": now,
                        "updated_at": now,
                    },
                    commit=False,
                )
                created += 1
                continue

            if self._requires_update(existing_entry, data):
                source_mismatches += 1
                logger.warning(
                    "service fee ledger source mismatch preserved",
                    extra={
                        "service_fee_entry_id": getattr(
                            existing_entry,
                            "service_fee_entry_id",
                            None,
                        ),
                        "contract_group_id": group_id,
                        "year_month": bucket.year_month,
                        "attributed_owner_party_id": bucket.attributed_owner_party_id,
                    },
                )

        for existing_entry in existing_entries:
            if self._entry_key(existing_entry) in seen_keys:
                continue
            if existing_entry.payment_status != "voided":
                source_mismatches += 1
                logger.warning(
                    "service fee ledger without current source preserved",
                    extra={
                        "service_fee_entry_id": getattr(
                            existing_entry,
                            "service_fee_entry_id",
                            None,
                        ),
                        "contract_group_id": group_id,
                        "year_month": getattr(existing_entry, "year_month", None),
                        "attributed_owner_party_id": getattr(
                            existing_entry,
                            "attributed_owner_party_id",
                            None,
                        ),
                    },
                )

        await db.flush()
        if commit:
            await db.commit()

        return {
            "created": created,
            "updated": updated,
            "voided": voided,
            "source_mismatches": source_mismatches,
        }

    async def _collect_monthly_buckets(
        self,
        db: AsyncSession,
        *,
        direct_lease_contracts: list[Any],
        entrusted_contracts: list[Any],
    ) -> dict[tuple[str, str, str | None, str], _MonthlyFeeBucket]:
        buckets: dict[tuple[str, str, str | None, str], _MonthlyFeeBucket] = {}
        for contract in direct_lease_contracts:
            source_entries = await contract_group_crud.list_ledger_entries_by_contract(
                db,
                contract_id=str(contract.contract_id),
            )
            for source_entry in source_entries:
                if getattr(source_entry, "payment_status", None) == "voided":
                    continue
                if _as_decimal(getattr(source_entry, "paid_amount", None)) <= 0:
                    continue
                agreement = self._resolve_agreement_for_source(
                    source_entry,
                    entrusted_contracts=entrusted_contracts,
                )
                agreement_id = str(agreement.contract_id)
                ratio = _as_decimal(
                    getattr(agreement.agency_detail, "service_fee_ratio", Decimal("0"))
                )
                key = (
                    str(source_entry.year_month),
                    agreement_id,
                    getattr(source_entry, "attributed_owner_party_id", None),
                    str(getattr(source_entry, "currency_code", "CNY")),
                )
                bucket = buckets.get(key)
                if bucket is None:
                    bucket = _MonthlyFeeBucket(
                        year_month=str(source_entry.year_month),
                        agency_contract_id=str(contract.contract_id),
                        agency_agreement_contract_id=agreement_id,
                        service_fee_ratio=ratio,
                        attributed_project_id=getattr(
                            source_entry,
                            "attributed_project_id",
                            None,
                        ),
                        attributed_owner_party_id=getattr(
                            source_entry,
                            "attributed_owner_party_id",
                            None,
                        ),
                        attributed_operator_party_id=getattr(
                            source_entry,
                            "attributed_operator_party_id",
                            None,
                        ),
                        attributed_asset_ids=getattr(
                            source_entry,
                            "attributed_asset_ids",
                            None,
                        ),
                        currency_code=str(
                            getattr(source_entry, "currency_code", "CNY")
                        ),
                    )
                    buckets[key] = bucket
                bucket.add_source(source_entry, str(contract.contract_id))
        return buckets

    @classmethod
    def _resolve_agreement_for_source(
        cls,
        source_entry: Any,
        *,
        entrusted_contracts: list[Any],
    ) -> Any:
        month_start, month_end = _month_range(str(source_entry.year_month))
        full_matches = [
            contract
            for contract in entrusted_contracts
            if cls._contract_covers_month(contract, month_start, month_end)
        ]
        if len(full_matches) == 1:
            return full_matches[0]
        if len(full_matches) > 1:
            raise BusinessValidationError(
                "rent ledger period must match exactly one entrusted service fee agreement"
            )
        if any(
            cls._contract_overlaps_month(contract, month_start, month_end)
            for contract in entrusted_contracts
        ):
            raise BusinessValidationError(
                "split rent ledger period before generating service fee: rent ledger period "
                "crosses service fee ratio interval"
            )
        raise BusinessValidationError(
            "rent ledger period must match exactly one entrusted service fee agreement"
        )

    @staticmethod
    def _contract_covers_month(
        contract: Any,
        month_start: date,
        month_end: date,
    ) -> bool:
        effective_from = _as_date(
            getattr(contract, "effective_from", None), default=date.min
        )
        effective_to = _as_date(
            getattr(contract, "effective_to", None), default=date.max
        )
        return effective_from <= month_start and effective_to >= month_end

    @staticmethod
    def _contract_overlaps_month(
        contract: Any,
        month_start: date,
        month_end: date,
    ) -> bool:
        effective_from = _as_date(
            getattr(contract, "effective_from", None), default=date.min
        )
        effective_to = _as_date(
            getattr(contract, "effective_to", None), default=date.max
        )
        return effective_from <= month_end and effective_to >= month_start

    @staticmethod
    def _entry_key(entry: Any) -> tuple[str, str, str | None, str]:
        return (
            str(getattr(entry, "year_month")),
            str(getattr(entry, "agency_agreement_contract_id")),
            getattr(entry, "attributed_owner_party_id", None),
            str(getattr(entry, "currency_code", "CNY")),
        )

    @staticmethod
    def _requires_update(entry: Any, data: dict[str, Any]) -> bool:
        return any(
            getattr(entry, field_name, None) != value
            for field_name, value in data.items()
        )


service_fee_ledger_service = ServiceFeeLedgerService()
