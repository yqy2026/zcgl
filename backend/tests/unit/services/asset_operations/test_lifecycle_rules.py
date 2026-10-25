"""Lifecycle rules at the asset-operations service seam."""

from __future__ import annotations

from datetime import date

import pytest

from src.models.asset_contract import TerminalContract
from src.services.asset_operations.errors import ActiveTerminalContractsBlockExitError
from src.services.asset_operations.lifecycle_rules import validate_upstream_exit


def _terminal(contract_id: str, *, upstream_contract_id: str) -> TerminalContract:
    return TerminalContract(
        id=contract_id,
        contract_number=f"TM-{contract_id}",
        contract_mode="sublease",
        tenant_party_id="tenant-1",
        lessor_party_id="operator-1",
        upstream_contract_id=upstream_contract_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        deposit_amount=0,
        rent_collector="operator",
        scan_document_id="scan-1",
    )


def test_upstream_exit_is_blocked_by_active_terminal_contracts() -> None:
    with pytest.raises(ActiveTerminalContractsBlockExitError) as error:
        validate_upstream_exit(
            upstream_contract_id="upstream-1",
            effective_date=date(2026, 6, 30),
            terminal_contracts=[
                _terminal("terminal-1", upstream_contract_id="upstream-1"),
                _terminal("terminal-2", upstream_contract_id="upstream-1"),
                _terminal("other", upstream_contract_id="upstream-2"),
            ],
            lifecycle_events=[],
        )

    assert error.value.status_code == 409
    assert error.value.code == "ACTIVE_TERMINAL_CONTRACTS_BLOCK_EXIT"
    assert error.value.details["terminal_contract_ids"] == [
        "terminal-1",
        "terminal-2",
    ]
