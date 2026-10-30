"""Unconfirmed management fee projections over owner-scoped rent facts.

Callers supply owner-reported receipts only, confirmed snapshot membership,
and obligations routed to this statement (late rows to the earliest open one).
Confirmed statements must be read from their snapshots, never reprojected.
"""

from __future__ import annotations

import calendar
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from src.services.asset_operations.rent_obligation_rules import (
    MONEY_QUANTUM,
    add_months,
)


@dataclass(frozen=True)
class AgreementFact:
    upstream_contract_id: str
    fee_rate: Decimal


@dataclass(frozen=True)
class ObligationFact:
    rent_ledger_entry_id: str
    terminal_contract_id: str
    upstream_contract_id: str | None
    period: str
    due_amount: Decimal
    voided: bool
    tenant_name: str
    asset_unit_ids: tuple[str, ...]


@dataclass(frozen=True)
class ReceiptFact:
    record_id: str
    rent_ledger_entry_id: str
    amount: Decimal
    occurred_on: date
    reversed_: bool = False


@dataclass(frozen=True)
class PriorDeferredRow:
    rent_ledger_entry_id: str
    prior_statement_id: str
    deferred_amount: Decimal


@dataclass(frozen=True)
class ManagementFeeLineProjection:
    line_kind: str
    upstream_contract_id: str
    terminal_contract_id: str
    rent_ledger_entry_id: str
    asset_unit_ids: tuple[str, ...]
    tenant_name_snapshot: str
    rent_period: str
    scheduled_rent: Decimal
    owner_received_amount: Decimal
    counted_record_ids: tuple[str, ...]
    received_on: date | None
    fee_rate: Decimal
    fee_amount: Decimal
    deferred_amount: Decimal
    deferral_reason: str | None
    carried_from_statement_id: str | None
    processed: bool


@dataclass(frozen=True)
class ManagementFeeStatementProjection:
    statement_period: str
    lines: tuple[ManagementFeeLineProjection, ...]
    upstream_contract_ids: tuple[str, ...]
    base_amount: Decimal
    fee_amount: Decimal
    status: Literal["collecting", "pending_stamp"]
    deadline: date
    carried_waiting_hint: bool
    upstream_missing_entry_ids: tuple[str, ...]
    upstream_missing_warning: str | None


def deadline_for(period: str) -> date:
    first = date.fromisoformat(f"{period}-01")
    following = add_months(first, 1)
    return following.replace(
        day=calendar.monthrange(following.year, following.month)[1]
    )


def project_statement(
    *,
    statement_period: str,
    agreements: Sequence[AgreementFact],
    obligations: Sequence[ObligationFact],
    receipts: Sequence[ReceiptFact],
    already_counted_record_ids: frozenset[str],
    confirmed_periods: frozenset[str],
    prior_statement_id: str | None,
    prior_statement_confirmed: bool,
    prior_deferred_rows: Sequence[PriorDeferredRow],
    deferral_marks: Mapping[str, str],
    today: date,
    already_listed_entry_ids: frozenset[str] = frozenset(),
) -> ManagementFeeStatementProjection:
    """Project current and carried rows; receipt membership prevents double fees.

    Previously listed obligations enter only through the prior deferral chain.
    Scheduled rent always uses the current obligation less previously counted
    receipts, so a prior deferred amount is a routing fact, not a balance source.
    """
    deadline = deadline_for(statement_period)
    rates = {row.upstream_contract_id: row.fee_rate for row in agreements}
    for rate in rates.values():
        if not rate.is_finite() or not 0 <= rate <= 1:
            raise ValueError("Management fee rate must be between zero and one")
    for mark_reason in deferral_marks.values():
        if not mark_reason.strip():
            raise ValueError("Deferral reason is required")
    prior = {
        row.rent_ledger_entry_id: row
        for row in prior_deferred_rows
        if row.deferred_amount > 0
        and prior_statement_confirmed
        and row.prior_statement_id == prior_statement_id
    }
    by_entry: dict[str, list[ReceiptFact]] = {}
    for record in receipts:
        if not record.amount.is_finite() or record.amount < 0:
            raise ValueError("Receipt amount must be finite and nonnegative")
        if not record.reversed_:
            by_entry.setdefault(record.rent_ledger_entry_id, []).append(record)
    lines: list[ManagementFeeLineProjection] = []
    missing: list[str] = []
    for entry in sorted(
        obligations, key=lambda row: (row.period, row.rent_ledger_entry_id)
    ):
        entry_id = entry.rent_ledger_entry_id
        if entry.voided:
            continue
        if entry.upstream_contract_id is None:
            missing.append(entry_id)
            continue
        if entry.upstream_contract_id not in rates:
            raise ValueError(
                "Bound management agreement is missing from projection facts"
            )
        carried = prior.get(entry_id)
        current = entry.period == statement_period
        late = (
            entry.period < statement_period
            and entry.period in confirmed_periods
            and entry_id not in already_listed_entry_ids
        )
        if not (current or carried is not None or late):
            continue
        records = by_entry.get(entry_id, [])
        counted = [r for r in records if r.record_id in already_counted_record_ids]
        pending = sorted(
            (r for r in records if r.record_id not in already_counted_record_ids),
            key=lambda row: row.record_id,
        )
        scheduled = entry.due_amount - sum((r.amount for r in counted), Decimal("0"))
        if not scheduled.is_finite() or scheduled < 0:
            raise ValueError(
                "Previously counted receipts exceed current rent obligation"
            )
        received = sum((r.amount for r in pending), Decimal("0"))
        remaining = max(scheduled - received, Decimal("0"))
        reason = deferral_marks.get(entry_id)
        if remaining > 0 and reason is None and today > deadline:
            reason = "截止日未到账，自动顺延"
        processed = remaining == 0 or reason is not None
        rate = rates[entry.upstream_contract_id]
        lines.append(
            ManagementFeeLineProjection(
                line_kind="carried"
                if carried is not None or not current
                else "current",
                upstream_contract_id=entry.upstream_contract_id,
                terminal_contract_id=entry.terminal_contract_id,
                rent_ledger_entry_id=entry_id,
                asset_unit_ids=entry.asset_unit_ids,
                tenant_name_snapshot=entry.tenant_name,
                rent_period=entry.period,
                scheduled_rent=scheduled,
                owner_received_amount=received,
                counted_record_ids=tuple(r.record_id for r in pending),
                received_on=max((r.occurred_on for r in pending), default=None),
                fee_rate=rate,
                fee_amount=(received * rate).quantize(
                    MONEY_QUANTUM, rounding=ROUND_HALF_UP
                ),
                deferred_amount=remaining,
                deferral_reason=reason if remaining > 0 else None,
                carried_from_statement_id=carried.prior_statement_id
                if carried
                else None,
                processed=processed,
            )
        )
    return ManagementFeeStatementProjection(
        statement_period=statement_period,
        lines=tuple(lines),
        upstream_contract_ids=tuple(
            sorted({line.upstream_contract_id for line in lines})
        ),
        base_amount=sum((line.owner_received_amount for line in lines), Decimal("0")),
        fee_amount=sum((line.fee_amount for line in lines), Decimal("0")),
        status="pending_stamp"
        if all(line.processed for line in lines)
        else "collecting",
        deadline=deadline,
        carried_waiting_hint=prior_statement_id is not None
        and not prior_statement_confirmed,
        upstream_missing_entry_ids=tuple(missing),
        upstream_missing_warning="UPSTREAM_CONTRACT_MISSING" if missing else None,
    )
