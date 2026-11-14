"""Whole-owner fee reads; a partially visible statement must never be recomputed.

Owner/unrestricted scope sees the whole statement; manager scope must cover
every management agreement of the owner, including for confirmed snapshots.
Authorization has a single home: the SQL boundary in
crud/business_change_event (visible_fee_statement_ids).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import Decimal
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import ResourceNotFoundError
from ...crud.asset_contract import asset_contract_repository
from ...crud.business_change_event import visible_fee_statement_ids
from ...crud.management_fee_deferral import management_fee_deferral_repository
from ...crud.management_fee_queries import (
    ManagementFeeQueryFacts,
    management_fee_query_repository,
)
from ...crud.management_fee_statement import management_fee_statement_repository
from ...models.management_fee_deferral import ManagementFeeDeferral
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

    @property
    def status(self) -> str | None:
        if self.projection is not None:
            return self.projection.status
        return self.statement.status

    @property
    def fee_amount(self) -> Decimal | None:
        if self.projection is not None:
            return self.projection.fee_amount
        return self.statement.fee_amount


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
        details = await self.details(db, statements=(statement,), scope=scope)
        return details[statement.id]

    async def details(
        self,
        db: AsyncSession,
        *,
        statements: Sequence[ManagementFeeStatement],
        scope: EffectivePartyScope,
    ) -> dict[str, ManagementFeeDetail]:
        """Read a batch without amplifying queries per statement.

        Whole-owner authorization, owner facts, terminal visibility and
        deferral marks are each resolved once for the whole batch; statements
        of one owner share the same facts. Any hidden statement fails the
        whole batch with the same 404 as the single-statement read.
        """
        require_scope(scope, scope.user_id)
        rows = tuple(statements)
        visible = await visible_fee_statement_ids(
            db, statement_ids=tuple(row.id for row in rows), scope=scope
        )
        for row in rows:
            if row.id not in visible:
                raise ResourceNotFoundError("ManagementFeeStatement", row.id)
        facts_by_owner: dict[str, ManagementFeeQueryFacts] = {}
        for owner_party_id in dict.fromkeys(row.owner_party_id for row in rows):
            facts_by_owner[owner_party_id] = (
                await management_fee_query_repository.load_facts(
                    db, owner_party_id=owner_party_id
                )
            )
        marks: Mapping[str, tuple[ManagementFeeDeferral, ...]] = {}
        draft_ids = tuple(row.id for row in rows if row.status is None)
        if draft_ids:
            marks = await management_fee_deferral_repository.list_marks_for_statements(
                db, statement_ids=draft_ids
            )
        today = business_today()
        manager_facts: dict[str, ManagementFeeQueryFacts] = {}
        details: dict[str, ManagementFeeDetail] = {}
        for row in rows:
            facts = facts_by_owner[row.owner_party_id]
            if row.status is not None:
                # Immutable snapshot: status and amounts were persisted at
                # confirmation; lines come from the owner's stored snapshot.
                details[row.id] = ManagementFeeDetail(
                    row,
                    None,
                    tuple(line for line in facts.lines if line.statement_id == row.id),
                )
                continue
            owner_access = (
                scope.scope_mode in {"owner", "all"}
                and row.owner_party_id in scope.owner_party_ids
            )
            if scope.scope_mode != "unrestricted" and not owner_access:
                if row.owner_party_id not in manager_facts:
                    manager_facts[row.owner_party_id] = await self._manager_visible_facts(
                        db, facts=facts, scope=scope
                    )
                facts = manager_facts[row.owner_party_id]
            details[row.id] = ManagementFeeDetail(
                row,
                project_fee_facts(
                    facts,
                    statement=row,
                    today=today,
                    deferral_marks={
                        mark.rent_ledger_entry_id: mark.reason
                        for mark in marks.get(row.id, ())
                    },
                ),
                (),
            )
        return details

    async def _manager_visible_facts(
        self,
        db: AsyncSession,
        *,
        facts: ManagementFeeQueryFacts,
        scope: EffectivePartyScope,
    ) -> ManagementFeeQueryFacts:
        # Agreement-level access grants the whole fee calculation, but missing
        # upstream warnings still require visibility of each terminal contract.
        unbound_ids = tuple(
            row.id for row in facts.contracts if row.upstream_contract_id is None
        )
        visible_contracts = await asset_contract_repository.terminal_ids_in_scope(
            db, contract_ids=unbound_ids, scope=scope
        )
        visible = {
            row.id
            for row in facts.contracts
            if row.upstream_contract_id is not None or row.id in visible_contracts
        }
        contracts = tuple(row for row in facts.contracts if row.id in visible)
        obligations = tuple(
            row for row in facts.obligations if row.contract_id in visible
        )
        entry_ids = {row.id for row in obligations}
        tenant_ids = {row.tenant_party_id for row in contracts}
        return replace(
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
                key: value for key, value in facts.unit_ids.items() if key in visible
            },
        )


management_fee_query_service = ManagementFeeQueryService()
