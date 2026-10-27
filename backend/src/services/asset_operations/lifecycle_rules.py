"""Lifecycle validation rules for asset-operations v5 contracts."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from ...models.asset_contract import ContractLifecycleEvent, TerminalContract
from .contract_projections import derive_terminal_contract_status
from .errors import ActiveTerminalContractsBlockExitError


def validate_upstream_exit(
    *,
    upstream_contract_id: str,
    effective_date: date,
    terminal_contracts: Iterable[TerminalContract],
    lifecycle_events: Iterable[ContractLifecycleEvent],
) -> None:
    """Raise a stable conflict when an upstream exit would orphan active leases."""
    events = tuple(lifecycle_events)
    blocking_ids = sorted(
        contract.id
        for contract in terminal_contracts
        if contract.upstream_contract_id == upstream_contract_id
        and derive_terminal_contract_status(
            contract,
            as_of=effective_date,
            lifecycle_events=events,
        )
        in {"active", "expiring"}
    )
    if len(blocking_ids) > 0:
        raise ActiveTerminalContractsBlockExitError(terminal_contract_ids=blocking_ids)


__all__ = ["validate_upstream_exit"]
