"""Agency service-fee ledger derivation service."""

from __future__ import annotations

import logging
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import BusinessValidationError, ResourceNotFoundError
from src.crud.contract import contract_crud
from src.crud.contract_group import contract_group_crud
from src.crud.query_builder import PartyFilter
from src.models.contract_group import (
    GroupRelationType,
    PaymentAllocationTargetType,
    RevenueMode,
    derive_ledger_payment_status,
)
from src.services.contract.ledger_scope import (
    assert_attribution_in_scope,
    assert_resource_in_scope,
    is_resource_in_scope,
    resolve_ledger_party_filter,
)
from src.services.contract.ledger_service_v2 import (
    find_stale_paid_or_partial_ledger_entries,
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


class ServiceFeeSourceMismatchReason(str, Enum):
    MISSING_AGREEMENT = "service_fee_source_missing_agreement"
    SOURCE_CHANGED = "service_fee_source_changed"
    SOURCE_WITHOUT_CURRENT_SOURCE = "service_fee_source_without_current_source"
    SOURCE_LEDGER_STALE_AFTER_CORRECTION = (
        "service_fee_source_ledger_stale_after_correction"
    )


@dataclass(frozen=True)
class ServiceFeeSourceMismatch:
    """Existing service-fee ledger whose frozen source no longer matches current rent receipts."""

    service_fee_entry_id: str
    year_month: str
    reason: str


class ServiceFeeLedgerService:
    """Generate monthly service-fee receivables from direct-lease rent receipts."""

    async def list_entries(
        self,
        db: AsyncSession,
        *,
        group_id: str | None = None,
        project_id: str | None = None,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> list[Any]:
        if group_id is None and project_id is None:
            raise BusinessValidationError(
                "contract_group_id or project_id is required for service fee query"
            )
        resolved_party_filter = await resolve_ledger_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )

        if group_id is not None:
            group = await contract_group_crud.get(db, group_id)
            if group is None:
                raise ResourceNotFoundError("contract group", group_id)
            assert_resource_in_scope(
                group,
                party_filter=resolved_party_filter,
                resource_type="合同组",
                resource_id=group_id,
            )
            if project_id is not None and str(group.project_id) != project_id:
                return []
            if getattr(group, "revenue_mode", None) != RevenueMode.AGENCY:
                return []
            entries = await contract_group_crud.list_service_fee_entries_by_group(
                db,
                group_id=group_id,
            )
            return [
                entry
                for entry in entries
                if is_resource_in_scope(entry, party_filter=resolved_party_filter)
            ]

        entries = (
            await contract_group_crud.list_service_fee_entries_by_attributed_project(
                db,
                project_id=str(project_id),
            )
        )
        return [
            entry
            for entry in entries
            if is_resource_in_scope(entry, party_filter=resolved_party_filter)
        ]

    async def sync_contract_group(
        self,
        db: AsyncSession,
        *,
        group_id: str,
        commit: bool = True,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> dict[str, int]:
        group = await contract_group_crud.get(db, group_id)
        if group is None:
            raise ResourceNotFoundError("contract group", group_id)
        resolved_party_filter = await resolve_ledger_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        assert_resource_in_scope(
            group,
            party_filter=resolved_party_filter,
            resource_type="合同组",
            resource_id=group_id,
        )
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
            party_filter=resolved_party_filter,
        )
        buckets = {
            key: bucket
            for key, bucket in buckets.items()
            if is_resource_in_scope(bucket, party_filter=resolved_party_filter)
        }
        all_existing_entries = (
            await contract_group_crud.list_service_fee_entries_by_group(
                db,
                group_id=group_id,
            )
        )
        existing_entries = [
            entry
            for entry in all_existing_entries
            if is_resource_in_scope(entry, party_filter=resolved_party_filter)
        ]
        existing_by_key = {self._entry_key(entry): entry for entry in existing_entries}

        created = 0
        updated = 0
        voided = 0
        source_mismatches = 0
        seen_keys: set[tuple[str, str, str | None, str]] = set()
        preserved_rekey_ids: set[str] = set()
        now = _utcnow()

        for key, bucket in buckets.items():
            seen_keys.add(key)
            existing_entry = existing_by_key.get(key)
            if existing_entry is None:
                rekey_candidate = self._find_rekey_candidate(
                    bucket=bucket,
                    buckets=buckets,
                    existing_entries=all_existing_entries,
                    excluded_entry_ids=preserved_rekey_ids,
                )
                if rekey_candidate is not None:
                    if not is_resource_in_scope(
                        rekey_candidate,
                        party_filter=resolved_party_filter,
                    ):
                        raise BusinessValidationError(
                            "service fee owner key change requires unrestricted service fee reconciliation"
                        )
                    candidate_id = self._required_text(
                        rekey_candidate,
                        "service_fee_entry_id",
                    )
                    preserved_rekey_ids.add(candidate_id)
                    source_mismatches += 1
                    logger.warning(
                        "service fee ledger source key mismatch preserved",
                        extra={
                            "service_fee_entry_id": candidate_id,
                            "contract_group_id": group_id,
                            "year_month": bucket.year_month,
                            "attributed_owner_party_id": (
                                bucket.attributed_owner_party_id
                            ),
                        },
                    )
                    continue
            data = self._bucket_entry_data(
                group_id=group_id,
                bucket=bucket,
                paid_amount=getattr(existing_entry, "paid_amount", Decimal("0"))
                if existing_entry is not None
                else Decimal("0"),
                stored_status=getattr(existing_entry, "payment_status", None),
            )

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

            if self._requires_update(
                existing_entry,
                self._bucket_source_data(group_id=group_id, bucket=bucket),
            ):
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
            existing_entry_id = str(
                getattr(existing_entry, "service_fee_entry_id", "") or ""
            )
            if existing_entry_id != "" and existing_entry_id in preserved_rekey_ids:
                continue
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

    async def find_source_mismatches(
        self,
        db: AsyncSession,
        *,
        group_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> list[ServiceFeeSourceMismatch]:
        group = await contract_group_crud.get(db, group_id)
        if group is None:
            raise ResourceNotFoundError("contract group", group_id)
        resolved_party_filter = await resolve_ledger_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        assert_resource_in_scope(
            group,
            party_filter=resolved_party_filter,
            resource_type="contract group",
            resource_id=group_id,
        )
        if getattr(group, "revenue_mode", None) != RevenueMode.AGENCY:
            return []

        contracts = await contract_crud.list_by_group(
            db,
            group_id=group_id,
            load_details=True,
        )
        existing_entries = await contract_group_crud.list_service_fee_entries_by_group(
            db,
            group_id=group_id,
        )
        existing_entries = [
            entry
            for entry in existing_entries
            if is_resource_in_scope(entry, party_filter=resolved_party_filter)
        ]
        entrusted_contracts = [
            contract
            for contract in contracts
            if getattr(contract, "group_relation_type", None)
            == GroupRelationType.ENTRUSTED
            and getattr(contract, "agency_detail", None) is not None
        ]
        if not entrusted_contracts:
            return [
                self._source_mismatch_item(
                    entry,
                    reason=ServiceFeeSourceMismatchReason.MISSING_AGREEMENT.value,
                )
                for entry in existing_entries
                if getattr(entry, "payment_status", None) != "voided"
            ]

        direct_lease_contracts = [
            contract
            for contract in contracts
            if getattr(contract, "group_relation_type", None)
            == GroupRelationType.DIRECT_LEASE
        ]
        stale_source_entry_ids = await self._collect_stale_source_entry_ids(
            db,
            direct_lease_contracts=direct_lease_contracts,
            party_filter=resolved_party_filter,
        )
        buckets = await self._collect_monthly_buckets(
            db,
            direct_lease_contracts=direct_lease_contracts,
            entrusted_contracts=entrusted_contracts,
            party_filter=resolved_party_filter,
        )
        return self._find_source_mismatches(
            existing_entries=existing_entries,
            buckets=buckets,
            group_id=group_id,
            stale_source_entry_ids=stale_source_entry_ids,
        )

    async def reconcile_source(
        self,
        db: AsyncSession,
        *,
        entry_id: str,
        reason: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
        commit: bool = True,
    ) -> Any:
        """Replace a preserved mismatch with the current uniquely derived source."""
        normalized_reason = reason.strip()
        if normalized_reason == "":
            raise BusinessValidationError(
                "service fee reconciliation reason is required"
            )

        entries = await contract_group_crud.get_service_fee_entries_by_ids(
            db,
            entry_ids=[entry_id],
            for_update=True,
        )
        if len(entries) != 1:
            raise ResourceNotFoundError("service fee ledger", entry_id)
        entry = entries[0]
        resolved_party_filter = await resolve_ledger_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        assert_resource_in_scope(
            entry,
            party_filter=resolved_party_filter,
            resource_type="service fee ledger",
            resource_id=entry_id,
        )

        group_id = self._required_text(entry, "contract_group_id")
        group = await contract_group_crud.get(db, group_id)
        if group is None:
            raise ResourceNotFoundError("contract group", group_id)
        assert_resource_in_scope(
            group,
            party_filter=resolved_party_filter,
            resource_type="contract group",
            resource_id=group_id,
        )
        if getattr(group, "revenue_mode", None) != RevenueMode.AGENCY:
            raise BusinessValidationError(
                "service fee source reconciliation requires an agency contract group"
            )

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
                "service fee source cannot be reconciled without an entrusted agreement"
            )
        direct_lease_contracts = [
            contract
            for contract in contracts
            if getattr(contract, "group_relation_type", None)
            == GroupRelationType.DIRECT_LEASE
        ]
        stale_source_entry_ids = await self._collect_stale_source_entry_ids(
            db,
            direct_lease_contracts=direct_lease_contracts,
            party_filter=resolved_party_filter,
        )
        buckets = await self._collect_monthly_buckets(
            db,
            direct_lease_contracts=direct_lease_contracts,
            entrusted_contracts=entrusted_contracts,
            party_filter=resolved_party_filter,
        )
        mismatches = self._find_source_mismatches(
            existing_entries=[entry],
            buckets=buckets,
            group_id=group_id,
            stale_source_entry_ids=stale_source_entry_ids,
        )
        mismatch = next(
            (item for item in mismatches if item.service_fee_entry_id == entry_id),
            None,
        )
        if mismatch is None:
            raise BusinessValidationError(
                "service fee ledger source already matches the current source"
            )
        if mismatch.reason == ServiceFeeSourceMismatchReason.SOURCE_CHANGED.value:
            bucket = buckets.get(self._entry_key(entry))
        elif mismatch.reason == (
            ServiceFeeSourceMismatchReason.SOURCE_WITHOUT_CURRENT_SOURCE.value
        ):
            bucket = self._find_rekey_candidate(
                bucket=None,
                buckets=buckets,
                existing_entries=[entry],
            )
        else:
            raise BusinessValidationError(
                "service fee source cannot be reconciled until the underlying source issue is resolved"
            )

        if bucket is None:
            raise BusinessValidationError(
                "service fee source cannot be reconciled without a unique current source"
            )
        source_data = self._bucket_source_data(group_id=group_id, bucket=bucket)
        assert_attribution_in_scope(
            owner_party_id=source_data["attributed_owner_party_id"],
            operator_party_id=source_data["attributed_operator_party_id"],
            party_filter=resolved_party_filter,
            resource_type="service fee ledger",
            resource_id=entry_id,
        )
        paid_amount = await contract_group_crud.sum_active_allocations_by_target(
            db,
            target_type=PaymentAllocationTargetType.SERVICE_FEE_LEDGER.value,
            target_id=entry_id,
        )
        if source_data["amount_due"] < paid_amount:
            raise BusinessValidationError(
                "reconciled service fee amount cannot be below active allocated receipts"
            )

        for field_name, value in source_data.items():
            setattr(entry, field_name, value)
        entry.paid_amount = paid_amount
        entry.payment_status = derive_ledger_payment_status(
            amount_due=source_data["amount_due"],
            paid_amount=paid_amount,
            stored_status=getattr(entry, "payment_status", None),
        )
        entry.updated_at = _utcnow()
        await db.flush()
        if commit:
            await db.commit()
        logger.info(
            "service fee ledger source reconciled",
            extra={
                "service_fee_entry_id": entry_id,
                "contract_group_id": group_id,
                "year_month": source_data["year_month"],
                "reconciled_by": current_user_id,
                "reconciliation_reason": normalized_reason,
            },
        )
        return entry

    def _find_source_mismatches(
        self,
        *,
        existing_entries: list[Any],
        buckets: dict[tuple[str, str, str | None, str], _MonthlyFeeBucket],
        group_id: str,
        stale_source_entry_ids: set[str],
    ) -> list[ServiceFeeSourceMismatch]:
        active_existing_entries = [
            entry
            for entry in existing_entries
            if getattr(entry, "payment_status", None) != "voided"
        ]
        existing_by_key = {
            self._entry_key(entry): entry for entry in active_existing_entries
        }
        seen_keys: set[tuple[str, str, str | None, str]] = set()
        mismatches: list[ServiceFeeSourceMismatch] = []

        for key, bucket in buckets.items():
            seen_keys.add(key)
            existing_entry = existing_by_key.get(key)
            if existing_entry is None:
                continue
            if self._entry_has_stale_source(existing_entry, stale_source_entry_ids):
                mismatches.append(
                    self._source_mismatch_item(
                        existing_entry,
                        reason=ServiceFeeSourceMismatchReason.SOURCE_LEDGER_STALE_AFTER_CORRECTION.value,
                    )
                )
                continue
            if self._requires_update(
                existing_entry,
                self._bucket_source_data(
                    group_id=group_id,
                    bucket=bucket,
                ),
            ):
                mismatches.append(
                    self._source_mismatch_item(
                        existing_entry,
                        reason=ServiceFeeSourceMismatchReason.SOURCE_CHANGED.value,
                    )
                )

        for existing_entry in active_existing_entries:
            if self._entry_key(existing_entry) in seen_keys:
                continue
            mismatches.append(
                self._source_mismatch_item(
                    existing_entry,
                    reason=ServiceFeeSourceMismatchReason.SOURCE_WITHOUT_CURRENT_SOURCE.value,
                )
            )

        return mismatches

    @staticmethod
    def _required_text(entry: Any, field_name: str) -> str:
        value = getattr(entry, field_name, None)
        text = str(value).strip() if value is not None else ""
        if text == "":
            raise BusinessValidationError(
                f"service fee ledger missing required {field_name}"
            )
        return text

    @classmethod
    def _source_mismatch_item(
        cls,
        entry: Any,
        *,
        reason: str,
    ) -> ServiceFeeSourceMismatch:
        return ServiceFeeSourceMismatch(
            service_fee_entry_id=cls._required_text(entry, "service_fee_entry_id"),
            year_month=cls._required_text(entry, "year_month"),
            reason=reason,
        )

    @staticmethod
    def _entry_has_stale_source(entry: Any, stale_source_entry_ids: set[str]) -> bool:
        source_ledger_ids = getattr(entry, "source_ledger_ids", None)
        if not isinstance(source_ledger_ids, list):
            raise BusinessValidationError(
                "service fee ledger source_ledger_ids must be a list"
            )
        return any(
            str(source_id) in stale_source_entry_ids for source_id in source_ledger_ids
        )

    @staticmethod
    def _bucket_source_data(
        *,
        group_id: str,
        bucket: _MonthlyFeeBucket,
    ) -> dict[str, Any]:
        amount_due = _quantize_money(
            bucket.calculation_base_amount * bucket.service_fee_ratio
        )
        return {
            "contract_group_id": group_id,
            "agency_contract_id": bucket.agency_contract_id,
            "agency_agreement_contract_id": bucket.agency_agreement_contract_id,
            "source_ledger_ids": sorted(bucket.source_ledger_ids),
            "year_month": bucket.year_month,
            "amount_due": amount_due,
            "currency_code": bucket.currency_code,
            "service_fee_ratio": bucket.service_fee_ratio,
            "calculation_base_amount": _quantize_money(bucket.calculation_base_amount),
            "attributed_project_id": bucket.attributed_project_id,
            "attributed_owner_party_id": bucket.attributed_owner_party_id,
            "attributed_operator_party_id": bucket.attributed_operator_party_id,
            "attributed_asset_ids": bucket.attributed_asset_ids,
        }

    @classmethod
    def _bucket_entry_data(
        cls,
        *,
        group_id: str,
        bucket: _MonthlyFeeBucket,
        paid_amount: Decimal,
        stored_status: str | None,
    ) -> dict[str, Any]:
        data = cls._bucket_source_data(group_id=group_id, bucket=bucket)
        data["payment_status"] = derive_ledger_payment_status(
            amount_due=data["amount_due"],
            paid_amount=paid_amount,
            stored_status=stored_status,
        )
        return data

    async def _collect_stale_source_entry_ids(
        self,
        db: AsyncSession,
        *,
        direct_lease_contracts: list[Any],
        party_filter: PartyFilter | None = None,
    ) -> set[str]:
        stale_source_entry_ids: set[str] = set()
        for contract in direct_lease_contracts:
            source_entries = await contract_group_crud.list_ledger_entries_by_contract(
                db,
                contract_id=str(contract.contract_id),
            )
            source_entries = [
                entry
                for entry in source_entries
                if is_resource_in_scope(entry, party_filter=party_filter)
            ]
            rent_terms = await contract_group_crud.list_rent_terms_by_contract(
                db,
                contract_id=str(contract.contract_id),
            )
            payment_cycle = str(
                getattr(getattr(contract, "lease_detail", None), "payment_cycle", "")
                or ""
            ).strip()
            stale_entries = find_stale_paid_or_partial_ledger_entries(
                rent_terms=rent_terms,
                ledger_entries=source_entries,
                payment_cycle=payment_cycle or "monthly",
            )
            stale_source_entry_ids.update(item.entry_id for item in stale_entries)
        return stale_source_entry_ids

    async def _collect_monthly_buckets(
        self,
        db: AsyncSession,
        *,
        direct_lease_contracts: list[Any],
        entrusted_contracts: list[Any],
        party_filter: PartyFilter | None = None,
    ) -> dict[tuple[str, str, str | None, str], _MonthlyFeeBucket]:
        buckets: dict[tuple[str, str, str | None, str], _MonthlyFeeBucket] = {}
        for contract in direct_lease_contracts:
            source_entries = await contract_group_crud.list_ledger_entries_by_contract(
                db,
                contract_id=str(contract.contract_id),
            )
            for source_entry in source_entries:
                if not is_resource_in_scope(
                    source_entry,
                    party_filter=party_filter,
                ):
                    continue
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

    @classmethod
    def _find_rekey_candidate(
        cls,
        *,
        bucket: _MonthlyFeeBucket | None,
        buckets: dict[tuple[str, str, str | None, str], _MonthlyFeeBucket],
        existing_entries: list[Any],
        excluded_entry_ids: set[str] | None = None,
    ) -> Any | None:
        excluded_ids = excluded_entry_ids or set()
        candidates: list[tuple[Any, _MonthlyFeeBucket]] = []
        candidate_buckets = [bucket] if bucket is not None else list(buckets.values())

        for existing_entry in existing_entries:
            if getattr(existing_entry, "payment_status", None) == "voided":
                continue
            entry_id = cls._required_text(
                existing_entry,
                "service_fee_entry_id",
            )
            if entry_id in excluded_ids or cls._entry_key(existing_entry) in buckets:
                continue
            source_ids = getattr(existing_entry, "source_ledger_ids", None)
            if not isinstance(source_ids, list):
                raise BusinessValidationError(
                    "service fee ledger source_ledger_ids must be a list"
                )
            frozen_source_ids = {str(source_id) for source_id in source_ids}
            for current_bucket in candidate_buckets:
                if current_bucket is None:
                    continue
                if str(getattr(existing_entry, "year_month", "")) != (
                    current_bucket.year_month
                ):
                    continue
                if str(getattr(existing_entry, "currency_code", "CNY")) != (
                    current_bucket.currency_code
                ):
                    continue
                if frozen_source_ids.intersection(current_bucket.source_ledger_ids):
                    candidates.append((existing_entry, current_bucket))

        if len(candidates) > 1:
            raise BusinessValidationError(
                "service fee source key change matches multiple current sources"
            )
        if not candidates:
            return None
        if bucket is not None:
            return candidates[0][0]
        return candidates[0][1]

    @staticmethod
    def _requires_update(entry: Any, data: dict[str, Any]) -> bool:
        return any(
            getattr(entry, field_name, None) != value
            for field_name, value in data.items()
        )


service_fee_ledger_service = ServiceFeeLedgerService()
