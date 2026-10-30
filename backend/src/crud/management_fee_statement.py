"""Management fee persistence without policy or transaction ownership."""

from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy import or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset_contract import TerminalContract, UpstreamContract
from ..models.management_fee_statement import (
    ManagementFeeStatement,
    ManagementFeeStatementLine,
)
from ..models.party import Party
from ..services.party_scope_resolver import EffectivePartyScope


class ManagementFeeStatementRepository:
    async def list_for_period(
        self, db: AsyncSession, *, period: str, scope: EffectivePartyScope
    ) -> tuple[ManagementFeeStatement, ...]:
        from .business_change_event import fee_statement_ids_for_scope

        query = (
            select(ManagementFeeStatement)
            .where(
                ManagementFeeStatement.period == period,
                ManagementFeeStatement.id.in_(fee_statement_ids_for_scope(scope)),
                or_(
                    ManagementFeeStatement.status.is_(None),
                    ManagementFeeStatement.status != "superseded",
                ),
            )
            .order_by(ManagementFeeStatement.owner_party_id, ManagementFeeStatement.id)
            .execution_options(populate_existing=True)
        )
        return tuple((await db.execute(query)).scalars().all())

    async def get_statement(
        self, db: AsyncSession, *, statement_id: str, for_update: bool = False
    ) -> ManagementFeeStatement | None:
        query = select(ManagementFeeStatement).where(
            ManagementFeeStatement.id == statement_id
        )
        if for_update:
            query = query.with_for_update().execution_options(populate_existing=True)
        return (await db.execute(query)).scalar_one_or_none()

    async def list_statements(
        self, db: AsyncSession, *, owner_party_id: str, for_update: bool = False
    ) -> tuple[ManagementFeeStatement, ...]:
        query = (
            select(ManagementFeeStatement)
            .where(ManagementFeeStatement.owner_party_id == owner_party_id)
            .order_by(ManagementFeeStatement.period, ManagementFeeStatement.id)
        )
        if for_update:
            query = query.with_for_update().execution_options(populate_existing=True)
        return tuple((await db.execute(query)).scalars().all())

    async def list_lines(
        self, db: AsyncSession, *, statement_ids: Sequence[str]
    ) -> tuple[ManagementFeeStatementLine, ...]:
        if not statement_ids:
            return ()
        query = (
            select(ManagementFeeStatementLine)
            .where(ManagementFeeStatementLine.statement_id.in_(statement_ids))
            .order_by(
                ManagementFeeStatementLine.statement_id, ManagementFeeStatementLine.id
            )
        )
        return tuple((await db.execute(query)).scalars().all())

    async def add_statement(
        self, db: AsyncSession, *, statement: ManagementFeeStatement
    ) -> None:
        db.add(statement)

    async def add_lines(
        self, db: AsyncSession, *, lines: Sequence[ManagementFeeStatementLine]
    ) -> None:
        db.add_all(list(lines))

    async def ensure_draft(
        self, db: AsyncSession, *, owner_party_id: str, period: str
    ) -> ManagementFeeStatement:
        """Ensure an active identity; an existing confirmed row remains confirmed.

        Caller serializes owner commands via lock_owner and owns the transaction.
        The partial unique index also protects creation across contract writers.
        """
        statement_id = str(uuid4())
        query = (
            insert(ManagementFeeStatement)
            .values(
                id=statement_id,
                owner_party_id=owner_party_id,
                period=period,
                statement_number=f"MF-{period}-{statement_id}",
                version=1,
            )
            .on_conflict_do_nothing(
                index_elements=["owner_party_id", "period"],
                index_where=text("status IS NULL OR status <> 'superseded'"),
            )
        )
        await db.execute(query)
        active = select(ManagementFeeStatement).where(
            ManagementFeeStatement.owner_party_id == owner_party_id,
            ManagementFeeStatement.period == period,
            or_(
                ManagementFeeStatement.status.is_(None),
                ManagementFeeStatement.status != "superseded",
            ),
        )
        return (await db.execute(active)).scalar_one()

    async def lock_owner(
        self, db: AsyncSession, *, owner_party_id: str
    ) -> Party | None:
        query = (
            select(Party)
            .where(Party.id == owner_party_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return (await db.execute(query)).scalar_one_or_none()

    async def bound_owner(
        self, db: AsyncSession, *, terminal_contract_id: str
    ) -> str | None:
        query = (
            select(UpstreamContract.owner_party_id)
            .join(
                TerminalContract,
                TerminalContract.upstream_contract_id == UpstreamContract.id,
            )
            .where(
                TerminalContract.id == terminal_contract_id,
                TerminalContract.contract_mode == "direct_lease",
                UpstreamContract.contract_type == "management_agreement",
                TerminalContract.lessor_party_id == UpstreamContract.owner_party_id,
            )
        )
        return (await db.execute(query)).scalar_one_or_none()


management_fee_statement_repository = ManagementFeeStatementRepository()
