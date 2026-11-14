"""Handover target eligibility follows append-only lifecycle events."""

from collections.abc import Iterable
from datetime import date

from ...models.asset_contract import ContractLifecycleEvent


def unavailable_reason(
    event: ContractLifecycleEvent, events: Iterable[ContractLifecycleEvent], today: date
) -> str | None:
    if any(
        r.event_type == "reversed"
        and r.reversed_event_id == event.id
        and r.effective_date <= today
        for r in events
    ):
        return "HANDOVER_EVENT_REVERSED"
    if event.effective_date > today:
        return "HANDOVER_NOT_EFFECTIVE"
    if event.handover_status not in {"pending", "completed"}:
        return "HANDOVER_NOT_REQUIRED"
    return None
