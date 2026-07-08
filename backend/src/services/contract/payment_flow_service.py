"""Operational payment flow service for receipts, payments, and allocations."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import BusinessValidationError, ResourceNotFoundError
from src.crud.contract_group import contract_group_crud
from src.models.contract_group import (
    LedgerView,
    OperationalPaymentFlowStatus,
    OperationalPaymentFlowType,
    PaymentAllocationTargetType,
    derive_ledger_payment_status,
)

_SCOPE_FIELDS = (
    "attributed_project_id",
    "attributed_owner_party_id",
    "attributed_operator_party_id",
    "currency_code",
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _as_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _entry_id(entry: Any, target_type: str) -> str:
    if target_type == PaymentAllocationTargetType.SERVICE_FEE_LEDGER.value:
        return str(getattr(entry, "service_fee_entry_id"))
    return str(getattr(entry, "entry_id"))


class PaymentFlowService:
    """Register operational payment flows and validate ledger allocations."""

    async def create_flow(
        self,
        db: AsyncSession,
        *,
        data: dict[str, Any],
        commit: bool = True,
    ) -> Any:
        flow_type = _enum_value(data.get("flow_type"))
        self._expected_target_type(flow_type)

        amount = _as_decimal(data.get("amount"))
        if amount <= 0:
            raise BusinessValidationError("payment flow amount must be greater than 0")

        now = _utcnow()
        payload = {
            **data,
            "flow_type": flow_type,
            "amount": amount,
            "status": _enum_value(
                data.get("status") or OperationalPaymentFlowStatus.ACTIVE.value
            ),
            "created_at": data.get("created_at") or now,
            "updated_at": data.get("updated_at") or now,
        }
        return await contract_group_crud.create_payment_flow(
            db,
            data=payload,
            commit=commit,
        )

    async def save_allocations(
        self,
        db: AsyncSession,
        *,
        flow_id: str,
        allocations: list[dict[str, Any]],
        commit: bool = True,
    ) -> list[Any]:
        flow = await contract_group_crud.get_payment_flow(db, flow_id=flow_id)
        if flow is None:
            raise ResourceNotFoundError("PaymentFlow", flow_id)
        if _enum_value(getattr(flow, "status", None)) != (
            OperationalPaymentFlowStatus.ACTIVE.value
        ):
            raise BusinessValidationError("only active payment flows can be allocated")

        rows = self._normalize_allocations(allocations)
        flow_amount = _as_decimal(getattr(flow, "amount", None))
        total_amount = sum((row["amount"] for row in rows), Decimal("0"))
        if total_amount != flow_amount:
            raise BusinessValidationError(
                "allocation amount total must equal payment flow amount"
            )

        flow_type = _enum_value(flow.flow_type)
        expected_target_type = self._expected_target_type(flow_type)
        if any(row["target_type"] != expected_target_type for row in rows):
            raise BusinessValidationError(
                "payment flow type does not match allocation target type"
            )

        existing_allocations = (
            await contract_group_crud.list_payment_allocations_by_flow(
                db,
                flow_id=flow_id,
            )
        )
        sync_rows = [
            *rows,
            *self._existing_allocation_rows(
                existing_allocations,
                expected_target_type=expected_target_type,
            ),
        ]
        targets = await self._load_targets(
            db,
            target_type=expected_target_type,
            rows=sync_rows,
        )
        allocation_targets = {
            row["target_id"]: targets[row["target_id"]] for row in rows
        }
        self._validate_target_periods(rows=rows, targets=allocation_targets)
        self._validate_target_views(flow_type=flow_type, targets=allocation_targets)
        self._validate_target_scope(targets=allocation_targets)

        saved = await contract_group_crud.replace_payment_allocations(
            db,
            flow_id=flow_id,
            rows=rows,
            commit=False,
        )
        await self._sync_target_paid_amounts(
            db,
            target_type=expected_target_type,
            targets=targets,
        )

        await db.flush()
        if commit:
            await db.commit()
        return saved

    @staticmethod
    def _normalize_allocations(
        allocations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for allocation in allocations:
            amount = _as_decimal(allocation.get("amount"))
            if amount <= 0:
                raise BusinessValidationError(
                    "payment flow amount must be greater than 0"
                )
            rows.append(
                {
                    "target_type": _enum_value(allocation.get("target_type")),
                    "target_id": str(allocation.get("target_id")),
                    "year_month": str(allocation.get("year_month")),
                    "amount": amount,
                }
            )
        return rows

    @staticmethod
    def _existing_allocation_rows(
        allocations: list[Any],
        *,
        expected_target_type: str,
    ) -> list[dict[str, Any]]:
        return [
            {
                "target_type": _enum_value(allocation.target_type),
                "target_id": str(allocation.target_id),
                "year_month": str(allocation.year_month),
                "amount": _as_decimal(allocation.amount),
            }
            for allocation in allocations
            if _enum_value(allocation.target_type) == expected_target_type
        ]

    @staticmethod
    def _expected_target_type(flow_type: str) -> str:
        if flow_type == OperationalPaymentFlowType.SERVICE_FEE_RECEIPT.value:
            return PaymentAllocationTargetType.SERVICE_FEE_LEDGER.value
        if flow_type in {
            OperationalPaymentFlowType.TERMINAL_RENT_RECEIPT.value,
            OperationalPaymentFlowType.UPSTREAM_COST_PAYMENT.value,
        }:
            return PaymentAllocationTargetType.CONTRACT_LEDGER_ENTRY.value
        raise BusinessValidationError("unsupported payment flow type")

    async def _load_targets(
        self,
        db: AsyncSession,
        *,
        target_type: str,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        target_ids = sorted({row["target_id"] for row in rows})
        entries: list[Any]
        if target_type == PaymentAllocationTargetType.SERVICE_FEE_LEDGER.value:
            entries = await contract_group_crud.get_service_fee_entries_by_ids(
                db,
                entry_ids=target_ids,
            )
        else:
            entries = await contract_group_crud.get_ledger_entries_by_ids(
                db,
                entry_ids=target_ids,
            )
        targets = {_entry_id(entry, target_type): entry for entry in entries}
        missing = sorted(set(target_ids) - set(targets))
        if missing:
            raise ResourceNotFoundError("PaymentAllocationTarget", ",".join(missing))
        return targets

    @staticmethod
    def _validate_target_periods(
        *,
        rows: list[dict[str, Any]],
        targets: dict[str, Any],
    ) -> None:
        for row in rows:
            target = targets[row["target_id"]]
            if str(getattr(target, "year_month", "")) != row["year_month"]:
                raise BusinessValidationError(
                    "allocation period must match target ledger period"
                )

    @staticmethod
    def _validate_target_views(
        *,
        flow_type: str,
        targets: dict[str, Any],
    ) -> None:
        required_view: str | None = None
        error_message: str | None = None
        if flow_type == OperationalPaymentFlowType.TERMINAL_RENT_RECEIPT.value:
            required_view = LedgerView.TERMINAL_COLLECTION.value
            error_message = (
                "terminal rent receipt can only allocate to terminal collection "
                "ledger entries"
            )
        elif flow_type == OperationalPaymentFlowType.UPSTREAM_COST_PAYMENT.value:
            required_view = LedgerView.OPERATOR_COST.value
            error_message = "upstream cost payment can only allocate to operator cost ledger entries"

        if required_view is None or error_message is None:
            return

        for target in targets.values():
            if required_view not in PaymentFlowService._target_ledger_views(target):
                raise BusinessValidationError(error_message)

    @staticmethod
    def _target_ledger_views(target: Any) -> set[str]:
        raw_views = getattr(target, "ledger_views", []) or []
        if isinstance(raw_views, str):
            raw_views = [raw_views]
        return {_enum_value(view) for view in raw_views}

    @staticmethod
    def _validate_target_scope(*, targets: dict[str, Any]) -> None:
        scopes = {
            tuple(getattr(target, field, None) for field in _SCOPE_FIELDS)
            for target in targets.values()
        }
        if len(scopes) > 1:
            raise BusinessValidationError(
                "allocations must share the same project, owner, operator, and "
                "currency scope"
            )

    async def _sync_target_paid_amounts(
        self,
        db: AsyncSession,
        *,
        target_type: str,
        targets: dict[str, Any],
    ) -> None:
        now = _utcnow()
        for target_id, target in targets.items():
            paid_amount = await contract_group_crud.sum_active_allocations_by_target(
                db,
                target_type=target_type,
                target_id=target_id,
            )
            target.paid_amount = paid_amount
            target.payment_status = derive_ledger_payment_status(
                amount_due=getattr(target, "amount_due", Decimal("0")),
                paid_amount=paid_amount,
                stored_status=getattr(target, "payment_status", None),
            )
            target.updated_at = now


payment_flow_service = PaymentFlowService()
