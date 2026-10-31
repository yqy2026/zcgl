"""Data access for asset-operations v5 signed contracts."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import (
    Select,
    exists,
    false,
    func,
    join,
    or_,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset_contract import (
    AssetContractWriteReceipt,
    ContractLifecycleEvent,
    ContractRentSchedule,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from ..models.asset_unit import AssetUnit
from ..models.attachment import Attachment
from ..models.project import Project
from ..services.party_scope_resolver import EffectivePartyScope


class AssetContractRepository:
    """Read signed contracts through explicit owner and manager scope axes."""

    @staticmethod
    def _scope_is_empty(scope: EffectivePartyScope) -> bool:
        return scope.scope_mode != "unrestricted" and (
            scope.error_code is not None or len(scope.effective_party_ids) == 0
        )

    @staticmethod
    def _apply_upstream_scope(
        statement: Select[tuple[UpstreamContract]],
        *,
        scope: EffectivePartyScope,
    ) -> Select[tuple[UpstreamContract]]:
        if scope.scope_mode == "unrestricted":
            return statement
        conditions = []
        if scope.scope_mode in {"owner", "all"} and len(scope.owner_party_ids) > 0:
            conditions.append(
                UpstreamContract.owner_party_id.in_(scope.owner_party_ids)
            )
        if scope.scope_mode in {"manager", "all"} and len(scope.manager_party_ids) > 0:
            conditions.append(
                UpstreamContract.operator_party_id.in_(scope.manager_party_ids)
            )
        return statement.where(or_(*conditions) if conditions else false())

    @staticmethod
    def _apply_terminal_scope(
        statement: Select[tuple[TerminalContract]],
        *,
        scope: EffectivePartyScope,
    ) -> Select[tuple[TerminalContract]]:
        if scope.scope_mode == "unrestricted":
            return statement
        conditions = []
        if scope.scope_mode in {"owner", "all"} and len(scope.owner_party_ids) > 0:
            conditions.append(AssetUnit.owner_party_id.in_(scope.owner_party_ids))
        if scope.scope_mode in {"manager", "all"} and len(scope.manager_party_ids) > 0:
            conditions.append(Project.manager_party_id.in_(scope.manager_party_ids))
        if len(conditions) == 0:
            return statement.where(false())
        return statement.where(
            exists(
                select(1)
                .select_from(TerminalContractAssetUnit)
                .join(
                    AssetUnit,
                    AssetUnit.id == TerminalContractAssetUnit.asset_unit_id,
                )
                .join(Project, Project.id == AssetUnit.project_id)
                .where(
                    TerminalContractAssetUnit.terminal_contract_id
                    == TerminalContract.id,
                    or_(*conditions),
                )
            )
        )

    async def list_upstream(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        contract_type: str | None = None,
        owner_party_id: str | None = None,
        query: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[UpstreamContract], int]:
        if self._scope_is_empty(scope):
            return [], 0
        statement = self._apply_upstream_scope(
            select(UpstreamContract),
            scope=scope,
        )
        if contract_type is not None:
            statement = statement.where(UpstreamContract.contract_type == contract_type)
        if owner_party_id is not None:
            statement = statement.where(
                UpstreamContract.owner_party_id == owner_party_id
            )
        normalized_query = query.strip() if query is not None else ""
        if normalized_query != "":
            pattern = f"%{normalized_query}%"
            statement = statement.where(
                or_(
                    UpstreamContract.contract_number.ilike(pattern),
                    UpstreamContract.name.ilike(pattern),
                    UpstreamContract.oa_reference.ilike(pattern),
                )
            )

        total_statement = select(func.count()).select_from(
            statement.order_by(None).subquery()
        )
        total = int((await db.execute(total_statement)).scalar_one())
        rows = (
            (
                await db.execute(
                    statement.order_by(UpstreamContract.contract_number)
                    .offset(offset)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get_upstream(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        scope: EffectivePartyScope,
        for_update: bool = False,
    ) -> UpstreamContract | None:
        if self._scope_is_empty(scope):
            return None
        statement = self._apply_upstream_scope(
            select(UpstreamContract),
            scope=scope,
        ).where(UpstreamContract.id == contract_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return (await db.execute(statement)).scalars().one_or_none()

    async def list_terminal(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        contract_mode: str | None = None,
        upstream_contract_id: str | None = None,
        query: str | None = None,
        offset: int = 0,
        limit: int = 50,
        contract_ids: set[str] | None = None,
    ) -> tuple[list[TerminalContract], int]:
        if self._scope_is_empty(scope):
            return [], 0
        statement = self._apply_terminal_scope(
            select(TerminalContract),
            scope=scope,
        )
        if contract_ids is not None:
            statement = statement.where(TerminalContract.id.in_(contract_ids))
        if contract_mode is not None:
            statement = statement.where(TerminalContract.contract_mode == contract_mode)
        if upstream_contract_id is not None:
            statement = statement.where(
                TerminalContract.upstream_contract_id == upstream_contract_id
            )
        normalized_query = query.strip() if query is not None else ""
        if normalized_query != "":
            statement = statement.where(
                TerminalContract.contract_number.ilike(f"%{normalized_query}%")
            )

        total_statement = select(func.count()).select_from(
            statement.order_by(None).subquery()
        )
        total = int((await db.execute(total_statement)).scalar_one())
        rows = (
            (
                await db.execute(
                    statement.order_by(TerminalContract.contract_number)
                    .offset(offset)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def list_terminal_by_upstream(
        self,
        db: AsyncSession,
        *,
        upstream_contract_id: str,
    ) -> tuple[TerminalContract, ...]:
        """List every terminal contract referencing this upstream, scope-free.

        Exit blocking is a fail-closed global check: an active terminal the
        exiting operator cannot see must still stop the exit.
        """
        statement = (
            select(TerminalContract)
            .where(TerminalContract.upstream_contract_id == upstream_contract_id)
            .order_by(TerminalContract.contract_number)
        )
        return tuple((await db.execute(statement)).scalars().all())

    async def list_terminal_lifecycle_events(
        self,
        db: AsyncSession,
        *,
        contract_ids: tuple[str, ...],
    ) -> tuple[ContractLifecycleEvent, ...]:
        return await self.list_lifecycle_events_by_contract_ids(
            db,
            contract_kind="terminal",
            contract_ids=contract_ids,
        )

    async def get_terminal(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        scope: EffectivePartyScope,
        for_update: bool = False,
    ) -> TerminalContract | None:
        if self._scope_is_empty(scope):
            return None
        statement = self._apply_terminal_scope(
            select(TerminalContract),
            scope=scope,
        ).where(TerminalContract.id == contract_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return (await db.execute(statement)).scalars().one_or_none()

    async def get_upstreams_by_ids(
        self,
        db: AsyncSession,
        *,
        contract_ids: tuple[str, ...],
        scope: EffectivePartyScope,
    ) -> tuple[UpstreamContract, ...]:
        if self._scope_is_empty(scope) or len(contract_ids) == 0:
            return ()
        statement = self._apply_upstream_scope(
            select(UpstreamContract), scope=scope
        ).where(UpstreamContract.id.in_(contract_ids))
        return tuple((await db.execute(statement)).scalars().all())

    async def list_lifecycle_events_by_contract_ids(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_ids: tuple[str, ...],
    ) -> tuple[ContractLifecycleEvent, ...]:
        if len(contract_ids) == 0:
            return ()
        statement = (
            select(ContractLifecycleEvent)
            .where(
                ContractLifecycleEvent.contract_kind == contract_kind,
                ContractLifecycleEvent.contract_id.in_(contract_ids),
            )
            .order_by(
                ContractLifecycleEvent.contract_id,
                ContractLifecycleEvent.effective_date,
                ContractLifecycleEvent.created_at,
                ContractLifecycleEvent.id,
            )
        )
        return tuple((await db.execute(statement)).scalars().all())

    async def list_rent_schedules(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_ids: tuple[str, ...],
    ) -> tuple[ContractRentSchedule, ...]:
        if len(contract_ids) == 0:
            return ()
        statement = (
            select(ContractRentSchedule)
            .where(
                ContractRentSchedule.contract_kind == contract_kind,
                ContractRentSchedule.contract_id.in_(contract_ids),
                ContractRentSchedule.superseded_at.is_(None),
            )
            .order_by(
                ContractRentSchedule.contract_id,
                ContractRentSchedule.stage_start,
            )
        )
        return tuple((await db.execute(statement)).scalars().all())

    async def get_write_receipt(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        idempotency_key: str,
    ) -> AssetContractWriteReceipt | None:
        statement = select(AssetContractWriteReceipt).where(
            AssetContractWriteReceipt.actor_id == actor_id,
            AssetContractWriteReceipt.idempotency_key == idempotency_key,
        )
        return (await db.execute(statement)).scalars().one_or_none()

    async def get_lifecycle_event_by_idempotency_key(
        self,
        db: AsyncSession,
        *,
        idempotency_key: str,
    ) -> ContractLifecycleEvent | None:
        statement = select(ContractLifecycleEvent).where(
            ContractLifecycleEvent.idempotency_key == idempotency_key
        )
        return (await db.execute(statement)).scalars().one_or_none()

    async def get_lifecycle_event_by_id(
        self,
        db: AsyncSession,
        *,
        event_id: str,
    ) -> ContractLifecycleEvent | None:
        statement = select(ContractLifecycleEvent).where(
            ContractLifecycleEvent.id == event_id
        )
        return (await db.execute(statement)).scalars().one_or_none()

    async def require_contract_attachment(
        self,
        db: AsyncSession,
        *,
        attachment_id: str,
    ) -> Attachment | None:
        statement = select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.owner_type == "contract",
        )
        return (await db.execute(statement)).scalars().one_or_none()

    async def bind_contract_attachment(
        self,
        db: AsyncSession,
        *,
        attachment_id: str,
        contract_id: str,
        expected_owner_id: str,
    ) -> bool:
        statement = (
            select(Attachment)
            .where(
                Attachment.id == attachment_id,
                Attachment.owner_type == "contract",
            )
            .with_for_update()
        )
        attachment = (await db.execute(statement)).scalars().one_or_none()
        if attachment is None or attachment.owner_id != expected_owner_id:
            return False
        attachment.owner_id = contract_id
        await db.flush()
        return True

    async def get_upstream_for_terminal(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        unit_ids: tuple[str, ...],
        scope: EffectivePartyScope,
    ) -> UpstreamContract | None:
        if self._scope_is_empty(scope):
            return None
        statement = self._apply_upstream_scope(
            select(UpstreamContract), scope=scope
        ).where(
            UpstreamContract.id == contract_id,
            exists(
                select(1)
                .select_from(UpstreamContractAssetUnit)
                .where(
                    UpstreamContractAssetUnit.upstream_contract_id
                    == UpstreamContract.id,
                    UpstreamContractAssetUnit.asset_unit_id.in_(unit_ids),
                )
            ),
        )
        return (await db.execute(statement)).scalars().one_or_none()

    async def list_upstream_coverages(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> tuple[UpstreamContractAssetUnit, ...]:
        statement = (
            select(UpstreamContractAssetUnit)
            .where(UpstreamContractAssetUnit.upstream_contract_id == contract_id)
            .order_by(UpstreamContractAssetUnit.asset_unit_id)
        )
        return tuple((await db.execute(statement)).scalars().all())

    async def list_terminal_coverages(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> tuple[TerminalContractAssetUnit, ...]:
        statement = (
            select(TerminalContractAssetUnit)
            .where(TerminalContractAssetUnit.terminal_contract_id == contract_id)
            .order_by(TerminalContractAssetUnit.asset_unit_id)
        )
        return tuple((await db.execute(statement)).scalars().all())

    async def find_upstream_overlaps(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[str, ...]:
        statement = (
            select(UpstreamContractAssetUnit.upstream_contract_id)
            .where(
                UpstreamContractAssetUnit.asset_unit_id.in_(unit_ids),
                UpstreamContractAssetUnit.effective_from <= end_date,
                or_(
                    UpstreamContractAssetUnit.effective_to.is_(None),
                    UpstreamContractAssetUnit.effective_to >= start_date,
                ),
            )
            .distinct()
            .order_by(UpstreamContractAssetUnit.upstream_contract_id)
        )
        return tuple((await db.execute(statement)).scalars().all())

    async def truncate_upstream_coverages(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        effective_date: date,
    ) -> int:
        """Close upstream coverage rows extending beyond an exit date.

        The cutoff is the day before ``effective_date``, mirroring terminal
        termination.
        """
        cutoff = effective_date - timedelta(days=1)
        result = await db.execute(
            update(UpstreamContractAssetUnit)
            .where(
                UpstreamContractAssetUnit.upstream_contract_id == contract_id,
                or_(
                    UpstreamContractAssetUnit.effective_to.is_(None),
                    UpstreamContractAssetUnit.effective_to > cutoff,
                ),
            )
            .values(effective_to=cutoff)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def restore_upstream_coverages(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        cutoff: date,
        until: date,
    ) -> int:
        """Reopen exactly the upstream rows an exit closed at ``cutoff``."""
        result = await db.execute(
            update(UpstreamContractAssetUnit)
            .where(
                UpstreamContractAssetUnit.upstream_contract_id == contract_id,
                UpstreamContractAssetUnit.effective_to == cutoff,
            )
            .values(effective_to=until)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def list_lifecycle_events(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_id: str,
    ) -> tuple[ContractLifecycleEvent, ...]:
        statement = (
            select(ContractLifecycleEvent)
            .where(
                ContractLifecycleEvent.contract_kind == contract_kind,
                ContractLifecycleEvent.contract_id == contract_id,
            )
            .order_by(
                ContractLifecycleEvent.effective_date,
                ContractLifecycleEvent.created_at,
                ContractLifecycleEvent.id,
            )
        )
        return tuple((await db.execute(statement)).scalars().all())

    async def truncate_terminal_coverages(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        effective_date: date,
    ) -> int:
        """Close coverage rows that still extend beyond a termination date.

        The cutoff is the day before ``effective_date``: the termination
        effective date is the first day the contract is no longer in force.
        """
        cutoff = effective_date - timedelta(days=1)
        result = await db.execute(
            update(TerminalContractAssetUnit)
            .where(
                TerminalContractAssetUnit.terminal_contract_id == contract_id,
                or_(
                    TerminalContractAssetUnit.effective_to.is_(None),
                    TerminalContractAssetUnit.effective_to > cutoff,
                ),
            )
            .values(effective_to=cutoff)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def restore_terminal_coverages(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        cutoff: date,
        until: date,
    ) -> int:
        """Reopen exactly the coverage rows a termination closed at ``cutoff``.

        Rows already ending before the cutoff belong to earlier facts and
        must not be extended.
        """
        result = await db.execute(
            update(TerminalContractAssetUnit)
            .where(
                TerminalContractAssetUnit.terminal_contract_id == contract_id,
                TerminalContractAssetUnit.effective_to == cutoff,
            )
            .values(effective_to=until)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def find_terminal_overlaps(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[str, ...]:
        statement = (
            select(TerminalContractAssetUnit.terminal_contract_id)
            .where(
                TerminalContractAssetUnit.asset_unit_id.in_(unit_ids),
                TerminalContractAssetUnit.effective_from <= end_date,
                or_(
                    TerminalContractAssetUnit.effective_to.is_(None),
                    TerminalContractAssetUnit.effective_to >= start_date,
                ),
            )
            .distinct()
            .order_by(TerminalContractAssetUnit.terminal_contract_id)
        )
        return tuple((await db.execute(statement)).scalars().all())

    async def list_rented_unit_ids(
        self,
        db: AsyncSession,
        *,
        as_of: date,
        scope: EffectivePartyScope,
    ) -> set[str]:
        """Return units under live terminal coverage at ``as_of``.

        Live = coverage period contains the date, contract started on or
        before it, and the contract has neither an unreversed termination
        nor an effective renewal successor.
        """
        if self._scope_is_empty(scope):
            return set()
        closed_ids = await self._lifecycle_closed_terminal_ids(db, as_of=as_of)
        scoped_contracts = self._apply_terminal_scope(
            select(TerminalContract.id), scope=scope
        )
        statement = (
            select(TerminalContractAssetUnit.asset_unit_id)
            .select_from(
                join(
                    TerminalContractAssetUnit,
                    TerminalContract,
                    TerminalContract.id
                    == TerminalContractAssetUnit.terminal_contract_id,
                )
            )
            .where(
                TerminalContract.id.in_(scoped_contracts),
                TerminalContract.start_date <= as_of,
                TerminalContractAssetUnit.effective_from <= as_of,
                or_(
                    TerminalContractAssetUnit.effective_to.is_(None),
                    TerminalContractAssetUnit.effective_to >= as_of,
                ),
            )
        )
        if closed_ids:
            statement = statement.where(TerminalContract.id.not_in(closed_ids))
        rows = (await db.execute(statement)).scalars().all()
        return set(rows)

    @staticmethod
    def _live_terminal_coverage_statement(
        columns: tuple[Any, ...],
        *,
        unit_ids: set[str] | None,
        as_of: date,
        closed_ids: set[str],
    ) -> Select[tuple[object, ...]]:
        """Select live terminal coverage at ``as_of`` for an optional unit set.

        Live = coverage contains the date, contract started on or before it,
        and the contract has neither an unreversed termination nor an
        effective renewal successor.
        """
        statement = (
            select(*columns)
            .select_from(
                join(
                    TerminalContractAssetUnit,
                    TerminalContract,
                    TerminalContract.id
                    == TerminalContractAssetUnit.terminal_contract_id,
                )
            )
            .where(
                TerminalContract.start_date <= as_of,
                TerminalContractAssetUnit.effective_from <= as_of,
                or_(
                    TerminalContractAssetUnit.effective_to.is_(None),
                    TerminalContractAssetUnit.effective_to >= as_of,
                ),
            )
        )
        if unit_ids is not None:
            statement = statement.where(
                TerminalContractAssetUnit.asset_unit_id.in_(unit_ids)
            )
        if closed_ids:
            statement = statement.where(TerminalContract.id.not_in(closed_ids))
        return statement

    async def list_rented_unit_ids_by_units(
        self,
        db: AsyncSession,
        *,
        unit_ids: set[str],
        as_of: date,
    ) -> set[str]:
        """Rented subset of the given already-authorized units at ``as_of``.

        Reporting facts follow the operator-party identity, not the caller's
        visible slice: callers pass a whole-unit candidate set that ownership
        checks have already resolved, so no user scope is applied here.
        """
        if not unit_ids:
            return set()
        closed_ids = await self._lifecycle_closed_terminal_ids(db, as_of=as_of)
        statement = self._live_terminal_coverage_statement(
            (TerminalContractAssetUnit.asset_unit_id,),
            unit_ids=unit_ids,
            as_of=as_of,
            closed_ids=closed_ids,
        )
        rows = (await db.execute(statement)).scalars().all()
        return set(rows)

    async def map_live_terminal_contract_ids_by_units(
        self,
        db: AsyncSession,
        *,
        unit_ids: set[str],
        as_of: date,
    ) -> dict[str, tuple[str, ...]]:
        """Live terminal-contract ids per unit at ``as_of`` for report lines.

        Same liveness semantics as ``list_rented_unit_ids_by_units``; callers
        pass an already-authorized unit set, so no user scope applies here.
        """
        if not unit_ids:
            return {}
        closed_ids = await self._lifecycle_closed_terminal_ids(db, as_of=as_of)
        statement = self._live_terminal_coverage_statement(
            (
                TerminalContractAssetUnit.asset_unit_id,
                TerminalContractAssetUnit.terminal_contract_id,
            ),
            unit_ids=unit_ids,
            as_of=as_of,
            closed_ids=closed_ids,
        )
        rows = (await db.execute(statement)).all()
        grouped: dict[str, list[str]] = {}
        for unit_id, contract_id in rows:
            grouped.setdefault(unit_id, []).append(contract_id)
        return {
            unit_id: tuple(sorted(contract_ids))
            for unit_id, contract_ids in grouped.items()
        }

    async def _lifecycle_closed_terminal_ids(
        self,
        db: AsyncSession,
        *,
        as_of: date,
    ) -> set[str]:
        reversed_ids = (
            select(ContractLifecycleEvent.reversed_event_id)
            .where(
                ContractLifecycleEvent.event_type == "reversed",
                ContractLifecycleEvent.reversed_event_id.is_not(None),
                ContractLifecycleEvent.effective_date <= as_of,
            )
            .scalar_subquery()
        )
        closed = select(ContractLifecycleEvent.contract_id).where(
            ContractLifecycleEvent.contract_kind == "terminal",
            ContractLifecycleEvent.effective_date <= as_of,
            ContractLifecycleEvent.event_type.in_(("terminated", "renewed")),
            ContractLifecycleEvent.id.not_in(reversed_ids),
        )
        rows = (await db.execute(closed)).scalars().all()
        return set(rows)

    async def retarget_upstream_coverage_ends(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        old_end: date,
        new_end: date,
    ) -> int:
        """Follow an end-date change for rows still at the signed end date.

        Rows already closed by a lifecycle fact keep their cutoff; this
        maintains the creation invariant that coverage ends with the contract.
        """
        result = await db.execute(
            update(UpstreamContractAssetUnit)
            .where(
                UpstreamContractAssetUnit.upstream_contract_id == contract_id,
                UpstreamContractAssetUnit.effective_to == old_end,
            )
            .values(effective_to=new_end)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def retarget_terminal_coverage_ends(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        old_end: date,
        new_end: date,
    ) -> int:
        """Follow an end-date change for rows still at the signed end date."""
        result = await db.execute(
            update(TerminalContractAssetUnit)
            .where(
                TerminalContractAssetUnit.terminal_contract_id == contract_id,
                TerminalContractAssetUnit.effective_to == old_end,
            )
            .values(effective_to=new_end)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def add_upstream(
        self,
        db: AsyncSession,
        *,
        contract: UpstreamContract,
        coverages: tuple[UpstreamContractAssetUnit, ...],
        schedules: tuple[ContractRentSchedule, ...],
    ) -> None:
        db.add(contract)
        db.add_all([*coverages, *schedules])
        await db.flush()

    async def add_terminal(
        self,
        db: AsyncSession,
        *,
        contract: TerminalContract,
        coverages: tuple[TerminalContractAssetUnit, ...],
        schedules: tuple[ContractRentSchedule, ...],
    ) -> None:
        db.add(contract)
        db.add_all([*coverages, *schedules])
        await db.flush()

    async def add_write_receipt(
        self,
        db: AsyncSession,
        *,
        receipt: AssetContractWriteReceipt,
    ) -> None:
        db.add(receipt)
        await db.flush()

    async def add_lifecycle_event(
        self,
        db: AsyncSession,
        *,
        event: ContractLifecycleEvent,
    ) -> None:
        db.add(event)
        await db.flush()


asset_contract_repository = AssetContractRepository()


__all__ = ["AssetContractRepository", "asset_contract_repository"]
