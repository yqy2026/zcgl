"""Contract tests for the asset-operations v5 contract fact models."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import ExcludeConstraint

from src.models.asset_contract import (
    AssetContractWriteReceipt,
    ContractLifecycleEvent,
    ContractRentSchedule,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)


def _constraint_names(model: type[object]) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints  # type: ignore[attr-defined]
        if constraint.name is not None
    }


def test_upstream_contract_keeps_status_derived_and_terms_constrained() -> None:
    columns = set(UpstreamContract.__table__.c.keys())
    names = _constraint_names(UpstreamContract)

    assert {
        "id",
        "contract_number",
        "contract_type",
        "name",
        "owner_party_id",
        "operator_party_id",
        "start_date",
        "end_date",
        "payment_cycle",
        "payment_day",
        "management_fee_rate",
        "deposit_amount",
        "oa_reference",
        "renewed_from_id",
        "scan_document_id",
        "version",
        "created_at",
        "updated_at",
    } <= columns
    assert columns.isdisjoint({"status", "risk_tags", "days_to_expiry"})
    assert {
        "uq_upstream_contracts_contract_number",
        "ck_upstream_contracts_type",
        "ck_upstream_contracts_date_range",
        "ck_upstream_contracts_payment_terms",
        "ck_upstream_contracts_payment_day",
        "ck_upstream_contracts_management_fee_rate",
        "ck_upstream_contracts_deposit_nonnegative",
    } <= names
    assert (
        UpstreamContract.__mapper__.version_id_col
        is UpstreamContract.__table__.c.version
    )


def test_terminal_contract_allows_missing_upstream_but_not_stored_risks() -> None:
    columns = set(TerminalContract.__table__.c.keys())
    names = _constraint_names(TerminalContract)

    assert TerminalContract.__table__.c.upstream_contract_id.nullable is True
    assert columns.isdisjoint(
        {"status", "upstream_missing", "term_exceeds_upstream", "scan_missing"}
    )
    assert {
        "uq_terminal_contracts_contract_number",
        "ck_terminal_contracts_mode",
        "ck_terminal_contracts_date_range",
        "ck_terminal_contracts_rent_collector",
        "ck_terminal_contracts_deposit_months_nonnegative",
        "ck_terminal_contracts_deposit_nonnegative",
    } <= names
    assert (
        TerminalContract.__mapper__.version_id_col
        is TerminalContract.__table__.c.version
    )


def test_contract_asset_unit_links_are_temporal_and_terminal_periods_exclude_overlap() -> (
    None
):
    upstream_table = UpstreamContractAssetUnit.__table__
    terminal_table = TerminalContractAssetUnit.__table__

    assert tuple(upstream_table.primary_key.columns.keys()) == (
        "upstream_contract_id",
        "asset_unit_id",
    )
    assert tuple(terminal_table.primary_key.columns.keys()) == (
        "terminal_contract_id",
        "asset_unit_id",
    )
    assert "ck_upstream_contract_asset_units_effective_range" in _constraint_names(
        UpstreamContractAssetUnit
    )
    assert "ck_terminal_contract_asset_units_effective_range" in _constraint_names(
        TerminalContractAssetUnit
    )
    assert any(
        isinstance(constraint, ExcludeConstraint)
        and constraint.name == "ex_terminal_contract_asset_units_unit_period"
        for constraint in terminal_table.constraints
    )


def test_rent_schedule_has_one_polymorphic_target_and_valid_money_constraints() -> None:
    columns = set(ContractRentSchedule.__table__.c.keys())
    names = _constraint_names(ContractRentSchedule)

    assert {
        "contract_kind",
        "contract_id",
        "stage_start",
        "stage_end",
        "base_monthly_rent",
        "increase_rate",
        "free_rent_months",
        "discount_amount",
        "actual_monthly_rent",
        "payment_cycle",
        "due_day",
    } <= columns
    assert {
        "ck_contract_rent_schedules_kind",
        "ck_contract_rent_schedules_stage_range",
        "ck_contract_rent_schedules_amounts_nonnegative",
        "ck_contract_rent_schedules_payment_cycle",
        "ck_contract_rent_schedules_due_day",
        "uq_contract_rent_schedules_target_stage",
    } <= names
    assert any(
        isinstance(constraint, UniqueConstraint)
        and tuple(constraint.columns.keys())
        == ("contract_kind", "contract_id", "stage_start")
        for constraint in ContractRentSchedule.__table__.constraints
    )


def test_lifecycle_event_is_append_only_idempotent_and_reversal_is_explicit() -> None:
    columns = set(ContractLifecycleEvent.__table__.c.keys())
    names = _constraint_names(ContractLifecycleEvent)

    assert {
        "contract_kind",
        "contract_id",
        "event_type",
        "effective_date",
        "termination_type",
        "handover_status",
        "deposit_settlement_status",
        "successor_contract_id",
        "reversed_event_id",
        "reason",
        "created_by",
        "created_at",
        "idempotency_key",
    } <= columns
    assert {
        "ck_contract_lifecycle_events_kind",
        "ck_contract_lifecycle_events_type",
        "ck_contract_lifecycle_events_target_compatibility",
        "ck_contract_lifecycle_events_successor",
        "ck_contract_lifecycle_events_reversal",
        "ck_contract_lifecycle_events_reason",
        "uq_contract_lifecycle_events_idempotency_key",
    } <= names
    assert all(
        isinstance(constraint, (CheckConstraint, UniqueConstraint))
        for constraint in ContractLifecycleEvent.__table__.constraints
        if constraint.name is not None
        and constraint.name.startswith(
            ("ck_contract_lifecycle_events_", "uq_contract_lifecycle_events_")
        )
    )


def test_contract_write_receipt_persists_idempotent_response_snapshot() -> None:
    assert AssetContractWriteReceipt.__tablename__ == "asset_contract_write_receipts"
    assert {
        "actor_id",
        "command_kind",
        "idempotency_key",
        "request_fingerprint",
        "result_data",
    } <= set(AssetContractWriteReceipt.__table__.columns.keys())
