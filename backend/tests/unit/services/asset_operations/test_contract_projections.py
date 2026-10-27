"""Business projections for the v5 asset-unit and terminal-contract chain."""

from __future__ import annotations

from datetime import date

from src.models.asset_contract import (
    ContractLifecycleEvent,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
)
from src.services.asset_operations.contract_projections import (
    derive_terminal_contract_status,
    derive_terminal_contract_warnings,
    derive_upstream_contract_status,
    rented_asset_unit_ids,
)


def _terminal(
    *,
    contract_id: str = "terminal-1",
    contract_mode: str = "sublease",
    upstream_contract_id: str | None = "upstream-1",
    start_date: date = date(2026, 1, 1),
    end_date: date = date(2026, 12, 31),
) -> TerminalContract:
    return TerminalContract(
        id=contract_id,
        contract_number=f"TM-{contract_id}",
        contract_mode=contract_mode,
        tenant_party_id="tenant-1",
        lessor_party_id=(
            "operator-1" if contract_mode == "sublease" else "owner-1"
        ),
        upstream_contract_id=upstream_contract_id,
        start_date=start_date,
        end_date=end_date,
        deposit_amount=0,
        rent_collector="operator" if contract_mode == "sublease" else "owner",
        scan_document_id="scan-1",
    )


def test_one_terminal_contract_covering_three_units_counts_three_rented_units() -> None:
    contract = _terminal()
    coverages = [
        TerminalContractAssetUnit(
            terminal_contract_id=contract.id,
            asset_unit_id=f"unit-{index}",
            effective_from=date(2026, 1, 1),
        )
        for index in range(1, 4)
    ]

    rented = rented_asset_unit_ids(
        as_of=date(2026, 6, 30),
        contracts=[contract],
        coverages=coverages,
        lifecycle_events=[],
    )

    assert rented == {"unit-1", "unit-2", "unit-3"}


def test_missing_upstream_is_warning_but_unit_remains_rented() -> None:
    contract = _terminal(upstream_contract_id=None)
    coverage = TerminalContractAssetUnit(
        terminal_contract_id=contract.id,
        asset_unit_id="unit-1",
        effective_from=date(2026, 1, 1),
    )

    warnings = derive_terminal_contract_warnings(contract, upstream=None)
    rented = rented_asset_unit_ids(
        as_of=date(2026, 6, 30),
        contracts=[contract],
        coverages=[coverage],
        lifecycle_events=[],
    )

    assert warnings == ("upstream_missing",)
    assert rented == {"unit-1"}


def test_term_exceeding_upstream_is_warning_without_changing_active_status() -> None:
    contract = _terminal(end_date=date(2027, 3, 31))
    upstream = UpstreamContract(
        id="upstream-1",
        contract_number="UP-001",
        contract_type="lease",
        name="承租合同",
        owner_party_id="owner-1",
        operator_party_id="operator-1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        payment_cycle="monthly",
        deposit_amount=0,
        scan_document_id="scan-upstream",
    )

    warnings = derive_terminal_contract_warnings(contract, upstream=upstream)
    status = derive_terminal_contract_status(
        contract,
        as_of=date(2026, 6, 30),
        lifecycle_events=[],
    )

    assert warnings == ("term_exceeds_upstream",)
    assert status == "active"


def test_term_starting_before_upstream_is_also_an_out_of_range_warning() -> None:
    contract = _terminal(start_date=date(2025, 12, 1))
    upstream = UpstreamContract(
        id="upstream-1",
        contract_number="UP-001",
        contract_type="lease",
        name="承租合同",
        owner_party_id="owner-1",
        operator_party_id="operator-1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        payment_cycle="monthly",
        deposit_amount=0,
        scan_document_id="scan-upstream",
    )

    assert derive_terminal_contract_warnings(contract, upstream=upstream) == (
        "term_exceeds_upstream",
    )


def test_direct_lease_exceeding_management_term_is_also_a_warning() -> None:
    contract = _terminal(
        contract_mode="direct_lease",
        end_date=date(2027, 3, 31),
    )
    upstream = UpstreamContract(
        id="upstream-1",
        contract_number="MGMT-001",
        contract_type="management_agreement",
        name="委托管理协议",
        owner_party_id="owner-1",
        operator_party_id="operator-1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        management_fee_rate=0,
        deposit_amount=0,
        scan_document_id="scan-upstream",
    )

    assert derive_terminal_contract_warnings(contract, upstream=upstream) == (
        "term_exceeds_upstream",
    )


def test_upstream_status_exposes_expired_pending_action_until_exit() -> None:
    contract = UpstreamContract(
        id="upstream-1",
        contract_number="UP-001",
        contract_type="lease",
        name="承租合同",
        owner_party_id="owner-1",
        operator_party_id="operator-1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        payment_cycle="monthly",
        deposit_amount=0,
        scan_document_id="scan-upstream",
    )

    assert (
        derive_upstream_contract_status(
            contract,
            as_of=date(2026, 1, 1),
            lifecycle_events=[],
        )
        == "expired_pending_action"
    )


def test_termination_and_its_reversal_are_replayed_append_only() -> None:
    contract = _terminal()
    termination = ContractLifecycleEvent(
        id="event-1",
        contract_kind="terminal",
        contract_id=contract.id,
        event_type="terminated",
        effective_date=date(2026, 5, 31),
        termination_type="early",
        reason="提前退租",
        created_by="user-1",
        idempotency_key="idem-1",
    )
    reversal = ContractLifecycleEvent(
        id="event-2",
        contract_kind="terminal",
        contract_id=contract.id,
        event_type="reversed",
        effective_date=date(2026, 6, 1),
        reversed_event_id=termination.id,
        reason="撤销误操作",
        created_by="user-1",
        idempotency_key="idem-2",
    )

    assert (
        derive_terminal_contract_status(
            contract,
            as_of=date(2026, 6, 30),
            lifecycle_events=[termination],
        )
        == "ended"
    )
    assert (
        derive_terminal_contract_status(
            contract,
            as_of=date(2026, 6, 30),
            lifecycle_events=[termination, reversal],
        )
        == "active"
    )


def test_coverage_period_filters_rented_units_at_statistical_date() -> None:
    contract = _terminal()
    ended_coverage = TerminalContractAssetUnit(
        terminal_contract_id=contract.id,
        asset_unit_id="unit-old",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 5, 31),
    )
    current_coverage = TerminalContractAssetUnit(
        terminal_contract_id=contract.id,
        asset_unit_id="unit-current",
        effective_from=date(2026, 6, 1),
    )

    rented = rented_asset_unit_ids(
        as_of=date(2026, 6, 30),
        contracts=[contract],
        coverages=[ended_coverage, current_coverage],
        lifecycle_events=[],
    )

    assert rented == {"unit-current"}
