"""Operational payment flow service for receipts, payments, and allocations."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import BusinessValidationError, ResourceNotFoundError
from src.crud.attachment import attachment_crud
from src.crud.contract_group import contract_group_crud
from src.crud.query_builder import PartyFilter
from src.models.contract_group import (
    LedgerView,
    OperationalPaymentFlowStatus,
    OperationalPaymentFlowType,
    PaymentAllocationTargetType,
    derive_ledger_payment_status,
)
from src.services.contract.ledger_scope import (
    assert_resource_in_scope,
    resolve_ledger_party_filter,
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
        registered_by: str,
        commit: bool = True,
    ) -> Any:
        flow_type = _enum_value(data.get("flow_type"))
        self._expected_target_type(flow_type)

        amount = _as_decimal(data.get("amount"))
        if amount <= 0:
            raise BusinessValidationError("payment flow amount must be greater than 0")
        normalized_registered_by = registered_by.strip()
        if normalized_registered_by == "":
            raise BusinessValidationError("payment flow registered_by is required")

        now = _utcnow()
        payload = {
            **data,
            "registered_by": normalized_registered_by,
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

    async def get_flow_in_scope(
        self,
        db: AsyncSession,
        *,
        flow_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
        for_update: bool = False,
    ) -> Any:
        """Resolve a flow only after its frozen allocation scope is authorized."""
        flow = await contract_group_crud.get_payment_flow(
            db,
            flow_id=flow_id,
            for_update=for_update,
        )
        if flow is None:
            raise ResourceNotFoundError("PaymentFlow", flow_id)
        allocations = await contract_group_crud.list_payment_allocations_by_flow(
            db,
            flow_id=flow_id,
        )
        if not allocations:
            raise ResourceNotFoundError("PaymentFlow", flow_id)
        target_type = self._expected_target_type(_enum_value(flow.flow_type))
        rows = self._existing_allocation_rows(
            allocations,
            expected_target_type=target_type,
        )
        targets = await self._load_targets(
            db,
            target_type=target_type,
            rows=rows,
        )
        resolved_party_filter = await resolve_ledger_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        for target_id, target in targets.items():
            assert_resource_in_scope(
                target,
                party_filter=resolved_party_filter,
                resource_type="收付流水",
                resource_id=target_id,
            )
        return flow

    async def list_flows_by_target(
        self,
        db: AsyncSession,
        *,
        target_type: str,
        target_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> list[Any]:
        allowed_target_types = {
            PaymentAllocationTargetType.CONTRACT_LEDGER_ENTRY.value,
            PaymentAllocationTargetType.SERVICE_FEE_LEDGER.value,
        }
        if target_type not in allowed_target_types:
            raise BusinessValidationError("unsupported payment allocation target type")
        normalized_target_id = target_id.strip()
        if normalized_target_id == "":
            raise BusinessValidationError("payment allocation target id is required")

        targets = await self._load_targets(
            db,
            target_type=target_type,
            rows=[{"target_id": normalized_target_id}],
        )
        resolved_party_filter = await resolve_ledger_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        target = targets[normalized_target_id]
        assert_resource_in_scope(
            target,
            party_filter=resolved_party_filter,
            resource_type="台账分摊目标",
            resource_id=normalized_target_id,
        )

        flows = await contract_group_crud.list_payment_flows_by_target(
            db,
            target_type=target_type,
            target_id=normalized_target_id,
        )
        for flow in flows:
            attachments = await attachment_crud.list_for_owner(
                db,
                owner_type="payment_flow",
                owner_id=str(flow.flow_id),
            )
            linked_ids = {str(value) for value in flow.voucher_attachment_ids or []}
            setattr(
                flow,
                "voucher_attachments",
                [attachment for attachment in attachments if attachment.id in linked_ids],
            )
        return flows

    async def save_allocations(
        self,
        db: AsyncSession,
        *,
        flow_id: str,
        allocations: list[dict[str, Any]],
        commit: bool = True,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> list[Any]:
        flow = await contract_group_crud.get_payment_flow(
            db,
            flow_id=flow_id,
            for_update=True,
        )
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
        resolved_party_filter = await resolve_ledger_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        for target_id, target in targets.items():
            assert_resource_in_scope(
                target,
                party_filter=resolved_party_filter,
                resource_type="台账分摊目标",
                resource_id=target_id,
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

    async def void_flow(
        self,
        db: AsyncSession,
        *,
        flow_id: str,
        reason: str,
        actor_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> Any:
        """Void one active flow and refresh every affected ledger target."""
        normalized_reason = reason.strip()
        normalized_actor_id = actor_id.strip()
        if normalized_reason == "":
            raise BusinessValidationError("payment flow lifecycle reason is required")
        if normalized_actor_id == "":
            raise BusinessValidationError("payment flow lifecycle actor is required")
        try:
            flow = await contract_group_crud.get_payment_flow(
                db,
                flow_id=flow_id,
                for_update=True,
            )
            if flow is None:
                raise ResourceNotFoundError("PaymentFlow", flow_id)
            if _enum_value(getattr(flow, "status", None)) != (
                OperationalPaymentFlowStatus.ACTIVE.value
            ):
                raise BusinessValidationError("only active payment flows can be voided")

            allocations = await contract_group_crud.list_payment_allocations_by_flow(
                db,
                flow_id=flow_id,
            )
            if not allocations:
                raise BusinessValidationError(
                    "payment flow must have allocations before it can be voided"
                )
            target_type = self._expected_target_type(_enum_value(flow.flow_type))
            rows = self._existing_allocation_rows(
                allocations,
                expected_target_type=target_type,
            )
            targets = await self._load_targets(
                db,
                target_type=target_type,
                rows=rows,
            )
            resolved_party_filter = await resolve_ledger_party_filter(
                db,
                current_user_id=current_user_id,
                party_filter=party_filter,
            )
            for target_id, target in targets.items():
                assert_resource_in_scope(
                    target,
                    party_filter=resolved_party_filter,
                    resource_type="收付流水",
                    resource_id=target_id,
                )

            now = _utcnow()
            flow.status = OperationalPaymentFlowStatus.VOIDED.value
            flow.status_changed_by = normalized_actor_id
            flow.status_changed_at = now
            flow.status_change_reason = normalized_reason
            flow.updated_at = now
            await db.flush()
            await self._sync_target_paid_amounts(
                db,
                target_type=target_type,
                targets=targets,
            )
            await db.flush()
            await db.commit()
            return flow
        except Exception:
            await db.rollback()
            raise

    async def correct_flow(
        self,
        db: AsyncSession,
        *,
        flow_id: str,
        reason: str,
        actor_id: str,
        replacement_data: dict[str, Any],
        allocations: list[dict[str, Any]],
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> Any:
        """Replace one active flow while retaining the original audit record."""
        normalized_reason = reason.strip()
        normalized_actor_id = actor_id.strip()
        if normalized_reason == "":
            raise BusinessValidationError("payment flow lifecycle reason is required")
        if normalized_actor_id == "":
            raise BusinessValidationError("payment flow lifecycle actor is required")
        if replacement_data.get("voucher_attachment_ids"):
            raise BusinessValidationError(
                "replacement voucher attachments must be uploaded after correction"
            )

        try:
            original = await contract_group_crud.get_payment_flow(
                db,
                flow_id=flow_id,
                for_update=True,
            )
            if original is None:
                raise ResourceNotFoundError("PaymentFlow", flow_id)
            if _enum_value(getattr(original, "status", None)) != (
                OperationalPaymentFlowStatus.ACTIVE.value
            ):
                raise BusinessValidationError("only active payment flows can be corrected")

            original_flow_type = _enum_value(original.flow_type)
            replacement_flow_type = _enum_value(replacement_data.get("flow_type"))
            if replacement_flow_type != original_flow_type:
                raise BusinessValidationError(
                    "replacement payment flow type must match original payment flow type"
                )

            replacement_amount = _as_decimal(replacement_data.get("amount"))
            if replacement_amount <= 0:
                raise BusinessValidationError(
                    "payment flow amount must be greater than 0"
                )
            replacement_rows = self._normalize_allocations(allocations)
            replacement_total = sum(
                (row["amount"] for row in replacement_rows),
                Decimal("0"),
            )
            if replacement_total != replacement_amount:
                raise BusinessValidationError(
                    "allocation amount total must equal payment flow amount"
                )
            original_target_type = self._expected_target_type(original_flow_type)
            if any(
                row["target_type"] != original_target_type
                for row in replacement_rows
            ):
                raise BusinessValidationError(
                    "payment flow type does not match allocation target type"
                )

            original_allocations = (
                await contract_group_crud.list_payment_allocations_by_flow(
                    db,
                    flow_id=flow_id,
                )
            )
            if not original_allocations:
                raise BusinessValidationError(
                    "payment flow must have allocations before it can be corrected"
                )
            original_rows = self._existing_allocation_rows(
                original_allocations,
                expected_target_type=original_target_type,
            )
            if not original_rows:
                raise BusinessValidationError(
                    "payment flow allocations do not match payment flow type"
                )
            targets = await self._load_targets(
                db,
                target_type=original_target_type,
                rows=[*original_rows, *replacement_rows],
            )
            resolved_party_filter = await resolve_ledger_party_filter(
                db,
                current_user_id=current_user_id,
                party_filter=party_filter,
            )
            for target_id, target in targets.items():
                assert_resource_in_scope(
                    target,
                    party_filter=resolved_party_filter,
                    resource_type="收付流水",
                    resource_id=target_id,
                )

            original_targets = {
                row["target_id"]: targets[row["target_id"]] for row in original_rows
            }
            replacement_targets = {
                row["target_id"]: targets[row["target_id"]]
                for row in replacement_rows
            }
            self._validate_target_periods(
                rows=replacement_rows,
                targets=replacement_targets,
            )
            self._validate_target_views(
                flow_type=replacement_flow_type,
                targets=replacement_targets,
            )
            self._validate_target_scope(targets=original_targets)
            self._validate_target_scope(targets=replacement_targets)
            if self._target_scope_identity(original_targets) != (
                self._target_scope_identity(replacement_targets)
            ):
                raise BusinessValidationError(
                    "replacement allocations must remain in original project, owner, "
                    "operator, and currency scope"
                )

            now = _utcnow()
            original.status = OperationalPaymentFlowStatus.CORRECTED.value
            original.status_changed_by = normalized_actor_id
            original.status_changed_at = now
            original.status_change_reason = normalized_reason
            original.updated_at = now
            await db.flush()

            replacement = await self.create_flow(
                db,
                data={
                    **replacement_data,
                    "corrected_from_flow_id": flow_id,
                    "status": OperationalPaymentFlowStatus.ACTIVE.value,
                },
                registered_by=normalized_actor_id,
                commit=False,
            )
            await contract_group_crud.replace_payment_allocations(
                db,
                flow_id=str(replacement.flow_id),
                rows=replacement_rows,
                commit=False,
            )
            await self._sync_target_paid_amounts(
                db,
                target_type=original_target_type,
                targets=targets,
            )
            await db.flush()
            await db.commit()
            return replacement
        except Exception:
            await db.rollback()
            raise

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
                for_update=True,
            )
        else:
            entries = await contract_group_crud.get_ledger_entries_by_ids(
                db,
                entry_ids=target_ids,
                for_update=True,
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

    @staticmethod
    def _target_scope_identity(targets: dict[str, Any]) -> tuple[Any, ...]:
        if not targets:
            raise BusinessValidationError("payment flow scope requires allocations")
        return tuple(
            getattr(next(iter(targets.values())), field, None)
            for field in _SCOPE_FIELDS
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
