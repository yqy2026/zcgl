"""Pure projections for signed terminal contracts and occupied asset units."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Literal

from ...models.asset_contract import (
    ContractLifecycleEvent,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
)
from ...schemas.asset_operations import ContractWarning

TerminalContractStatus = Literal[
    "scheduled",
    "active",
    "expiring",
    "ended",
    "historical",
]
UpstreamContractStatus = Literal[
    "scheduled",
    "active",
    "expiring",
    "expired_pending_action",
    "exited",
    "historical",
]
TerminalContractWarning = Literal[
    "upstream_missing",
    "term_exceeds_upstream",
    "scan_missing",
]


def _active_terminal_events(
    *,
    contract_id: str,
    as_of: date,
    lifecycle_events: Iterable[ContractLifecycleEvent],
) -> tuple[ContractLifecycleEvent, ...]:
    events = tuple(
        event
        for event in lifecycle_events
        if event.contract_kind == "terminal"
        and event.contract_id == contract_id
        and event.effective_date <= as_of
    )
    reversed_event_ids = {
        event.reversed_event_id
        for event in events
        if event.event_type == "reversed" and event.reversed_event_id is not None
    }
    return tuple(
        event
        for event in events
        if event.event_type != "reversed" and event.id not in reversed_event_ids
    )


def derive_terminal_contract_warnings(
    contract: TerminalContract,
    *,
    upstream: UpstreamContract | None,
) -> tuple[TerminalContractWarning, ...]:
    """Derive non-blocking relationship and document warnings."""
    warnings: list[TerminalContractWarning] = []
    if contract.upstream_contract_id is None or upstream is None:
        warnings.append("upstream_missing")
    elif (
        contract.start_date < upstream.start_date
        or contract.end_date > upstream.end_date
    ):
        warnings.append("term_exceeds_upstream")

    scan_document_id = contract.scan_document_id
    if scan_document_id is None or str(scan_document_id).strip() == "":
        warnings.append("scan_missing")
    return tuple(warnings)


_PUBLIC_WARNINGS: dict[str, tuple[str, str]] = {
    "RENT_SCHEDULE_GAP": (
        "RENT_SCHEDULE_GAP",
        "合同期限内存在未覆盖的租金阶段，请补录核对",
    ),
    "RENT_LEDGER_PLAN_MISMATCH": (
        "RENT_LEDGER_PLAN_MISMATCH",
        "已登记的租金义务与当前合同条款不一致，请核对登记",
    ),
    "upstream_missing": (
        "UPSTREAM_CONTRACT_MISSING",
        "尚未关联上游合同，已保留风险提示",
    ),
    "term_exceeds_upstream": (
        "TERMINAL_TERM_EXCEEDS_UPSTREAM",
        "终端合同期限超出上游合同期限，已保留风险提示",
    ),
    "scan_missing": (
        "ARCHIVE_DOCUMENT_MISSING",
        "合同扫描件缺失",
    ),
}


def public_warning(code: str) -> ContractWarning:
    """Map an internal warning code to its stable public form."""
    public_code, message = _PUBLIC_WARNINGS[code]
    return ContractWarning(code=public_code, severity="warning", message=message)


def derive_upstream_contract_status(
    contract: UpstreamContract,
    *,
    as_of: date,
    lifecycle_events: Iterable[ContractLifecycleEvent],
    successor_effective_from: date | None = None,
    expiring_within_days: int = 180,
) -> UpstreamContractStatus:
    """Derive the operational state of one signed upstream contract."""
    events = tuple(
        event
        for event in lifecycle_events
        if event.contract_kind == "upstream"
        and event.contract_id == contract.id
        and event.effective_date <= as_of
    )
    reversed_event_ids = {
        event.reversed_event_id
        for event in events
        if event.event_type == "reversed" and event.reversed_event_id is not None
    }
    active_events = tuple(
        event
        for event in events
        if event.event_type != "reversed" and event.id not in reversed_event_ids
    )
    if successor_effective_from is not None and successor_effective_from <= as_of:
        return "historical"
    if any(event.event_type == "exited" for event in active_events):
        return "exited"
    if as_of < contract.start_date:
        return "scheduled"
    if as_of > contract.end_date:
        return "expired_pending_action"
    if (contract.end_date - as_of).days <= expiring_within_days:
        return "expiring"
    return "active"


def derive_terminal_contract_status(
    contract: TerminalContract,
    *,
    as_of: date,
    lifecycle_events: Iterable[ContractLifecycleEvent],
    successor_effective_from: date | None = None,
    expiring_within_days: int = 180,
) -> TerminalContractStatus:
    """Replay append-only events and derive the terminal contract status."""
    active_events = _active_terminal_events(
        contract_id=contract.id,
        as_of=as_of,
        lifecycle_events=lifecycle_events,
    )
    if successor_effective_from is not None and successor_effective_from <= as_of:
        return "historical"
    if any(event.event_type == "terminated" for event in active_events):
        return "ended"
    if as_of < contract.start_date:
        return "scheduled"
    if as_of > contract.end_date:
        return "ended"
    if (contract.end_date - as_of).days <= expiring_within_days:
        return "expiring"
    return "active"


def rented_asset_unit_ids(
    *,
    as_of: date,
    contracts: Iterable[TerminalContract],
    coverages: Iterable[TerminalContractAssetUnit],
    lifecycle_events: Iterable[ContractLifecycleEvent],
) -> set[str]:
    """Return distinct rented unit IDs at a date, independent of upstream presence."""
    event_snapshot = tuple(lifecycle_events)
    active_contract_ids = {
        contract.id
        for contract in contracts
        if derive_terminal_contract_status(
            contract,
            as_of=as_of,
            lifecycle_events=event_snapshot,
        )
        in {"active", "expiring"}
    }
    return {
        coverage.asset_unit_id
        for coverage in coverages
        if coverage.terminal_contract_id in active_contract_ids
        and coverage.effective_from <= as_of
        and (coverage.effective_to is None or coverage.effective_to >= as_of)
    }


__all__ = [
    "UpstreamContractStatus",
    "derive_upstream_contract_status",
    "TerminalContractStatus",
    "TerminalContractWarning",
    "derive_terminal_contract_status",
    "derive_terminal_contract_warnings",
    "public_warning",
    "rented_asset_unit_ids",
]
