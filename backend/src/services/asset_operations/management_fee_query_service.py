"""Whole-owner fee reads; a partially visible statement must never be recomputed.

Owner/unrestricted scope sees the whole statement; manager scope must cover
every management agreement of the owner, including for confirmed snapshots.
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import Decimal
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import ResourceNotFoundError
from ...crud.asset_contract import asset_contract_repository
from ...crud.management_fee_deferral import management_fee_deferral_repository
from ...crud.management_fee_queries import (
    ManagementFeeQueryFacts,
    management_fee_query_repository,
)
from ...crud.management_fee_statement import management_fee_statement_repository
from ...models.management_fee_statement import (
    ManagementFeeStatement,
    ManagementFeeStatementLine,
)
from ..party_scope_resolver import EffectivePartyScope
from .management_fee_rules import (
    AgreementFact,
    ManagementFeeStatementProjection,
    ObligationFact,
    PriorDeferredRow,
    ReceiptFact,
    project_statement,
)
from .rent_command_support import require_scope
from .rent_ledger_query_service import business_today


@dataclass(frozen=True)
class ManagementFeeDetail:
    statement: ManagementFeeStatement
    projection: ManagementFeeStatementProjection | None
    snapshot_lines: tuple[ManagementFeeStatementLine, ...]


def project_fee_facts(
    facts: ManagementFeeQueryFacts,
    *,
    statement: ManagementFeeStatement,
    today: date,
    deferral_marks: Mapping[str, str] | None = None,
) -> ManagementFeeStatementProjection:
    confirmed = {
        row.id
        for row in facts.statements
        if row.status == "confirmed" and row.period < statement.period
    }
    counted_lines = [row for row in facts.lines if row.statement_id in confirmed]
    listed_entry_ids = frozenset(row.rent_ledger_entry_id for row in counted_lines)
    periods = frozenset(row.period for row in facts.statements if row.id in confirmed)
    prior_period = (
        date.fromisoformat(f"{statement.period}-01") - timedelta(days=1)
    ).strftime("%Y-%m")
    prior = next(
        (
            row
            for row in facts.statements
            if row.period == prior_period and row.status != "superseded"
        ),
        None,
    )
    open_periods = [row.period for row in facts.statements if row.status is None]
    contracts = {row.id: row for row in facts.contracts}
    reversed_ids = {
        row.reverses_record_id for row in facts.records if row.record_type == "reversal"
    }
    return project_statement(
        statement_period=statement.period,
        agreements=tuple(
            # Table CHECK pins management_fee_rate non-null on management agreements.
            AgreementFact(row.id, cast(Decimal, row.management_fee_rate))
            for row in facts.agreements
        ),
        obligations=tuple(
            ObligationFact(
                row.id,
                row.contract_id,
                contracts[row.contract_id].upstream_contract_id,
                row.period,
                row.due_amount,
                row.voided_at is not None,
                facts.tenant_names[contracts[row.contract_id].tenant_party_id],
                facts.unit_ids.get(row.contract_id, ()),
            )
            for row in facts.obligations
            if row.id in listed_entry_ids
            or row.period not in periods
            or row.period >= statement.period
            or statement.period
            == min(
                (period for period in open_periods if period > row.period),
                default=statement.period,
            )
        ),
        receipts=tuple(
            ReceiptFact(
                row.id,
                row.ledger_entry_id,
                row.amount,
                row.occurred_on,
                row.id in reversed_ids,
            )
            for row in facts.records
            if row.record_type == "owner_reported_receipt"
        ),
        already_counted_record_ids=frozenset(
            record_id for row in counted_lines for record_id in row.counted_record_ids
        ),
        confirmed_periods=periods,
        already_listed_entry_ids=listed_entry_ids,
        prior_statement_id=prior.id if prior is not None else None,
        prior_statement_confirmed=prior is not None and prior.status == "confirmed",
        prior_deferred_rows=tuple(
            PriorDeferredRow(
                row.rent_ledger_entry_id, row.statement_id, row.deferred_amount
            )
            for row in facts.lines
            if prior is not None and row.statement_id == prior.id
        ),
        deferral_marks={} if deferral_marks is None else deferral_marks,
        today=today,
    )


class ManagementFeeQueryService:
    async def detail(
        self,
        db: AsyncSession,
        *,
        statement_id: str,
        scope: EffectivePartyScope,
    ) -> ManagementFeeDetail:
        require_scope(scope, scope.user_id)
        statement = await management_fee_statement_repository.get_statement(
            db, statement_id=statement_id
        )
        if statement is None:
            raise ResourceNotFoundError("ManagementFeeStatement", statement_id)
        facts = await management_fee_query_repository.load_facts(
            db, owner_party_id=statement.owner_party_id
        )
        owner_access = (
            scope.scope_mode in {"owner", "all"}
            and statement.owner_party_id in scope.owner_party_ids
        )
        # Python twin of the SQL boundary in
        # crud/business_change_event.fee_statement_ids_for_scope; keep in sync.
        manager_access = (
            scope.scope_mode in {"manager", "all"}
            and len(facts.agreements) > 0
            and all(
                row.operator_party_id in scope.manager_party_ids
                for row in facts.agreements
            )
        )
        if (
            scope.scope_mode != "unrestricted"
            and not owner_access
            and not manager_access
        ):
            raise ResourceNotFoundError("ManagementFeeStatement", statement_id)
        if statement.status is not None:
            return ManagementFeeDetail(
                statement,
                None,
                tuple(row for row in facts.lines if row.statement_id == statement.id),
            )
        # Agreement-level access grants the whole fee calculation, but missing
        # upstream warnings still require visibility of each terminal contract.
        if scope.scope_mode != "unrestricted" and not owner_access:
            visible = set()
            for contract in facts.contracts:
                if (
                    contract.upstream_contract_id is not None
                    or await asset_contract_repository.get_terminal(
                        db, contract_id=contract.id, scope=scope
                    )
                    is not None
                ):
                    visible.add(contract.id)
            contracts = tuple(row for row in facts.contracts if row.id in visible)
            obligations = tuple(
                row for row in facts.obligations if row.contract_id in visible
            )
            entry_ids = {row.id for row in obligations}
            tenant_ids = {row.tenant_party_id for row in contracts}
            facts = replace(
                facts,
                contracts=contracts,
                obligations=obligations,
                records=tuple(
                    row for row in facts.records if row.ledger_entry_id in entry_ids
                ),
                tenant_names={
                    key: value
                    for key, value in facts.tenant_names.items()
                    if key in tenant_ids
                },
                unit_ids={
                    key: value
                    for key, value in facts.unit_ids.items()
                    if key in visible
                },
            )
        marks = await management_fee_deferral_repository.list_marks(
            db, statement_id=statement.id
        )
        return ManagementFeeDetail(
            statement,
            project_fee_facts(
                facts,
                statement=statement,
                today=business_today(),
                deferral_marks={
                    mark.rent_ledger_entry_id: mark.reason for mark in marks
                },
            ),
            (),
        )


management_fee_query_service = ManagementFeeQueryService()
