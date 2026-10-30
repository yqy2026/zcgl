"""Create statement identities in the surrounding rent-replanning transaction.

Lock order is asset units, contracts, rent entries, owner, statements. Future
confirmation writers must use the same order before checking projections.
"""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.asset_ledger import asset_ledger_repository
from ...crud.management_fee_statement import (
    ManagementFeeStatementRepository,
    management_fee_statement_repository,
)
from .management_fee_rules import deadline_for
from .rent_obligation_rules import add_months


class ManagementFeeEntryService:
    def __init__(self, *, repository: ManagementFeeStatementRepository | None = None):
        self.repository = (
            repository
            if repository is not None
            else management_fee_statement_repository
        )

    async def ensure_bound_contract(
        self, db: AsyncSession, *, terminal_contract_id: str
    ) -> None:
        """Binding an upstream must also discover already-paid obligations.

        The caller holds the terminal contract lock. Rent source snapshots and
        amounts remain untouched; a confirmed snapshot membership is not new.
        """
        entries = await asset_ledger_repository.list_entries(
            db,
            contract_kind="terminal",
            contract_id=terminal_contract_id,
            for_update=True,
        )
        owner = await self.repository.bound_owner(
            db, terminal_contract_id=terminal_contract_id
        )
        if owner is None:
            return
        statements = await self.repository.list_statements(db, owner_party_id=owner)
        lines = await self.repository.list_lines(
            db,
            statement_ids=[row.id for row in statements if row.status == "confirmed"],
        )
        listed = {line.rent_ledger_entry_id for line in lines}
        periods = tuple(
            sorted(
                {
                    entry.period
                    for entry in entries
                    if entry.entry_type == "owner_receipt_expected"
                    and entry.voided_at is None
                    and entry.id not in listed
                }
            )
        )
        if periods:
            await self.reconcile(
                db, owner_party_id=owner, new_periods=periods, changed_periods=()
            )

    async def reconcile(
        self,
        db: AsyncSession,
        *,
        owner_party_id: str,
        new_periods: tuple[str, ...],
        changed_periods: tuple[str, ...],
    ) -> None:
        """Ensure identities for new rows; invalidate only affected open versions.

        The owner row serializes concurrent contracts of the same owner. No
        commit, rollback or nested transaction: failures roll back rent too.
        """
        for period in {*new_periods, *changed_periods}:
            deadline_for(period)
        await self.repository.lock_owner(db, owner_party_id=owner_party_id)
        rows = await self.repository.list_statements(
            db, owner_party_id=owner_party_id, for_update=True
        )
        active = {row.period: row for row in rows if row.status != "superseded"}
        drafts = sorted(
            (row for row in active.values() if row.status is None),
            key=lambda row: row.period,
        )
        latest = max(
            (row.period for row in active.values() if row.status == "confirmed"),
            default=None,
        )
        destinations: dict[str, str] = {}
        created_ids: set[str] = set()
        for period in sorted(set(new_periods)):
            if period in active and active[period].status == "confirmed":
                later_drafts = [row for row in drafts if row.period > period]
                target = (
                    later_drafts[0].period
                    if later_drafts
                    else add_months(date.fromisoformat(f"{latest}-01"), 1).strftime(
                        "%Y-%m"
                    )
                )
            else:
                target = period
            destinations[period] = target
            if target not in active:
                row = await self.repository.ensure_draft(
                    db, owner_party_id=owner_party_id, period=target
                )
                active[target] = row
                drafts.append(row)
                drafts.sort(key=lambda row: row.period)
                created_ids.add(row.id)
        affected: set[str] = set(destinations.values())
        for period in changed_periods:
            current = active.get(period)
            if current is not None and current.status is None:
                affected.add(period)
            elif drafts and period < drafts[0].period:
                affected.add(drafts[0].period)
        for period in affected:
            row = active[period]
            if row.status is None and row.id not in created_ids:
                row.version += 1


management_fee_entry_service = ManagementFeeEntryService()
