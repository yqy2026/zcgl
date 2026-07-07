"""Operational payment flow service for receipts, payments, and allocations."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import BusinessValidationError, ResourceNotFoundError
from src.crud.contract_group import contract_group_crud
from src.models.contract_group import (
    OperationalPaymentFlowStatus,
    OperationalPaymentFlowType,
    PaymentAllocationTargetType,
    derive_ledger_payment_status,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _as_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


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
        amount = _as_decimal(data.get("amount"))
        if amount <= 0:
            raise BusinessValidationError("payment flow amount must be greater than 0")

        now = _utcnow()
        payload = {
            **data,
            "amount": amount,
            "status": data.get("status") or OperationalPaymentFlowStatus.ACTIVE.value,
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
        if getattr(flow, "status", None) != OperationalPaymentFlowStatus.ACTIVE.value:
            raise BusinessValidationError("only active payment flows can be allocated")

        rows = self._normalize_allocations(allocations)
        flow_amount = _as_decimal(getattr(flow, "amount", None))
        total_amount = sum((row["amount"] for row in rows), Decimal("0"))
        if total_amount != flow_amount:
            raise BusinessValidationError(
                "allocation amount total must equal payment flow amount"
            )

        expected_target_type = self._expected_target_type(str(flow.flow_type))
        if any(row["target_type"] != expected_target_type for row in rows):
            raise BusinessValidationError(
                "payment flow type does not match allocation target type"
            )

        targets = await self._load_targets(
            db, target_type=expected_target_type, rows=rows
        )
        self._validate_target_periods(rows=rows, targets=targets)

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
                    "target_type": str(allocation.get("target_type")),
                    "target_id": str(allocation.get("target_id")),
                    "year_month": str(allocation.get("year_month")),
                    "amount": amount,
                }
            )
        return rows

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
