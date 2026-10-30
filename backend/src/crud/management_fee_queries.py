"""Batch owner facts for whole-statement authorization and fee projections."""

from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset_contract import (
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
)
from ..models.asset_ledger import RentLedgerEntry, RentPaymentRecord
from ..models.management_fee_statement import (
    ManagementFeeStatement,
    ManagementFeeStatementLine,
)
from ..models.party import Party


@dataclass
class ManagementFeeQueryFacts:
    agreements: tuple[UpstreamContract, ...]
    contracts: tuple[TerminalContract, ...]
    obligations: tuple[RentLedgerEntry, ...]
    records: tuple[RentPaymentRecord, ...]
    tenant_names: dict[str, str]
    unit_ids: dict[str, tuple[str, ...]]
    statements: tuple[ManagementFeeStatement, ...]
    lines: tuple[ManagementFeeStatementLine, ...]


class ManagementFeeQueryRepository:
    async def load_facts(
        self, db: AsyncSession, *, owner_party_id: str
    ) -> ManagementFeeQueryFacts:
        agreements = tuple(
            (
                await db.execute(
                    select(UpstreamContract)
                    .execution_options(populate_existing=True)
                    .where(
                        UpstreamContract.owner_party_id == owner_party_id,
                        UpstreamContract.contract_type == "management_agreement",
                    )
                )
            )
            .scalars()
            .all()
        )
        agreement_ids = tuple(row.id for row in agreements)
        contracts = tuple(
            (
                await db.execute(
                    select(TerminalContract)
                    .execution_options(populate_existing=True)
                    .where(
                        TerminalContract.contract_mode == "direct_lease",
                        TerminalContract.rent_collector == "owner",
                        TerminalContract.lessor_party_id == owner_party_id,
                        or_(
                            TerminalContract.upstream_contract_id.in_(agreement_ids),
                            (TerminalContract.upstream_contract_id.is_(None))
                            & (TerminalContract.lessor_party_id == owner_party_id),
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )
        contract_ids = tuple(row.id for row in contracts)
        obligations = (
            tuple(
                (
                    await db.execute(
                        select(RentLedgerEntry)
                        .execution_options(populate_existing=True)
                        .where(
                            RentLedgerEntry.contract_kind == "terminal",
                            RentLedgerEntry.contract_id.in_(contract_ids),
                            RentLedgerEntry.entry_type == "owner_receipt_expected",
                        )
                    )
                )
                .scalars()
                .all()
            )
            if contract_ids
            else ()
        )
        entry_ids = tuple(row.id for row in obligations)
        records = (
            tuple(
                (
                    await db.execute(
                        select(RentPaymentRecord)
                        .execution_options(populate_existing=True)
                        .where(
                            RentPaymentRecord.ledger_entry_id.in_(entry_ids),
                            RentPaymentRecord.record_type.in_(
                                ("owner_reported_receipt", "reversal")
                            ),
                        )
                    )
                )
                .scalars()
                .all()
            )
            if entry_ids
            else ()
        )
        tenants = (
            (
                await db.execute(
                    select(Party.id, Party.name).where(
                        Party.id.in_(tuple(row.tenant_party_id for row in contracts))
                    )
                )
            ).all()
            if contracts
            else ()
        )
        coverages = (
            (
                await db.execute(
                    select(
                        TerminalContractAssetUnit.terminal_contract_id,
                        TerminalContractAssetUnit.asset_unit_id,
                    ).where(
                        TerminalContractAssetUnit.terminal_contract_id.in_(contract_ids)
                    )
                )
            ).all()
            if contracts
            else ()
        )
        units: dict[str, set[str]] = {}
        for contract_id, unit_id in coverages:
            units.setdefault(contract_id, set()).add(unit_id)
        statements = tuple(
            (
                await db.execute(
                    select(ManagementFeeStatement)
                    .execution_options(populate_existing=True)
                    .where(ManagementFeeStatement.owner_party_id == owner_party_id)
                    .order_by(ManagementFeeStatement.period, ManagementFeeStatement.id)
                )
            )
            .scalars()
            .all()
        )
        statement_ids = tuple(row.id for row in statements)
        lines = (
            tuple(
                (
                    await db.execute(
                        select(ManagementFeeStatementLine)
                        .execution_options(populate_existing=True)
                        .where(
                            ManagementFeeStatementLine.statement_id.in_(statement_ids)
                        )
                        .order_by(ManagementFeeStatementLine.id)
                    )
                )
                .scalars()
                .all()
            )
            if statements
            else ()
        )
        return ManagementFeeQueryFacts(
            agreements,
            contracts,
            obligations,
            records,
            {key: value for key, value in tenants},
            {key: tuple(sorted(values)) for key, values in units.items()},
            statements,
            lines,
        )


management_fee_query_repository = ManagementFeeQueryRepository()
