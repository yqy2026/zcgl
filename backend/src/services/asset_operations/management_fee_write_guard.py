"""Synchronize fee versions while the rent writer holds contract/entry locks."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.management_fee_statement import (
    ManagementFeeStatementRepository,
    management_fee_statement_repository,
)
from ...models.asset_ledger import RentLedgerEntry
from .rent_errors import rent_error
from .rent_obligation_rules import add_months


class ManagementFeeWriteGuard:
    def __init__(self, *, repository: ManagementFeeStatementRepository | None = None):
        self.repository = (
            repository
            if repository is not None
            else management_fee_statement_repository
        )

    async def before_change(
        self,
        db: AsyncSession,
        *,
        entry: RentLedgerEntry,
        reversing_record_id: str | None = None,
    ) -> None:
        """Reject locked reversals, then invalidate the statement receiving facts.

        Caller owns contract and rent entry locks, transaction and audit. Replay
        checks must precede this hook so retries do not advance fee versions.
        """
        owner = await self.repository.bound_owner(
            db, terminal_contract_id=entry.contract_id
        )
        if owner is None:
            return
        await self.repository.lock_owner(db, owner_party_id=owner)
        rows = await self.repository.list_statements(
            db, owner_party_id=owner, for_update=True
        )
        confirmed = [row for row in rows if row.status == "confirmed"]
        if reversing_record_id is not None:
            lines = await self.repository.list_lines(
                db, statement_ids=[row.id for row in confirmed]
            )
            if any(reversing_record_id in line.counted_record_ids for line in lines):
                raise rent_error(
                    "MANAGEMENT_FEE_STATEMENT_LOCKED",
                    "到账记录已计入确认对账单，请先更正对账单",
                )
        active = {row.period: row for row in rows if row.status != "superseded"}
        current = active.get(entry.period)
        target = None
        if current is not None and current.status is None:
            target = current
        elif current is not None and current.status == "confirmed":
            target = min(
                (
                    row
                    for row in rows
                    if row.status is None and row.period > entry.period
                ),
                key=lambda row: row.period,
                default=None,
            )
        if target is not None:
            target.version += 1
            return
        period = entry.period
        if current is not None and current.status == "confirmed":
            latest = max(row.period for row in confirmed)
            period = add_months(date.fromisoformat(f"{latest}-01"), 1).strftime("%Y-%m")
        await self.repository.ensure_draft(db, owner_party_id=owner, period=period)


management_fee_write_guard = ManagementFeeWriteGuard()
