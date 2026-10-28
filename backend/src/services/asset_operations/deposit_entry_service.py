"""Create the single deposit identity alongside a confirmed contract.

Amounts and renewal transfers remain projections of contracts and records.
The caller owns the contract lock and transaction, including rollback.
"""

from typing import Protocol, cast
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.deposit_ledger import deposit_ledger_repository
from ...models.asset_contract import TerminalContract, UpstreamContract
from ...models.deposit_ledger import DepositLedgerEntry


class DepositEntryRepository(Protocol):
    async def get_by_contract(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_id: str,
        for_update: bool = False,
    ) -> DepositLedgerEntry | None: ...
    async def add_entry(
        self, db: AsyncSession, *, entry: DepositLedgerEntry
    ) -> None: ...


class DepositEntryService:
    def __init__(self, *, repository: DepositEntryRepository | None = None) -> None:
        self.repository = (
            repository if repository is not None else deposit_ledger_repository
        )

    @staticmethod
    def collector_for(
        contract_kind: str, contract: UpstreamContract | TerminalContract
    ) -> str | None:
        if contract_kind == "upstream":
            contract_type = cast(UpstreamContract, contract).contract_type
            if contract_type == "management_agreement":
                return None
            if contract_type == "lease":
                return "owner"
        elif contract_kind == "terminal":
            mode = cast(TerminalContract, contract).contract_mode
            if mode == "sublease":
                return "operator"
            if mode == "direct_lease":
                return "owner"
        raise ValueError("Unknown deposit contract kind or mode")

    async def ensure_entry(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract: UpstreamContract | TerminalContract,
    ) -> DepositLedgerEntry | None:
        collector = self.collector_for(contract_kind, contract)
        if collector is None:
            return None
        existing = await self.repository.get_by_contract(
            db,
            contract_kind=contract_kind,
            contract_id=contract.id,
        )
        if existing is not None:
            return existing
        entry = DepositLedgerEntry(  # type: ignore[call-arg]
            id=str(uuid4()),
            contract_kind=contract_kind,
            contract_id=contract.id,
            collector=collector,
            version=1,
        )
        await self.repository.add_entry(db, entry=entry)
        return entry


deposit_entry_service = DepositEntryService()
