"""Persistence adapter for asset-unit boundary preview and commit flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TypeVar

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset_contract import (
    ContractLifecycleEvent,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from ..models.asset_unit import (
    AssetUnit,
    AssetUnitBoundaryChange,
    AssetUnitBoundarySource,
)
from ..services.party_scope_resolver import EffectivePartyScope
from .asset_unit import asset_unit_repository

TContract = TypeVar("TContract", UpstreamContract, TerminalContract)


@dataclass(frozen=True)
class AssetUnitSplitContext:
    source: AssetUnit | None
    existing_boundary_change_id: str | None = None
    existing_result_unit_codes: tuple[str, ...] = ()
    upstream_coverages: tuple[UpstreamContractAssetUnit, ...] = ()
    upstream_contracts: tuple[UpstreamContract, ...] = ()
    terminal_coverages: tuple[TerminalContractAssetUnit, ...] = ()
    terminal_contracts: tuple[TerminalContract, ...] = ()
    lifecycle_events: tuple[ContractLifecycleEvent, ...] = ()


@dataclass(frozen=True)
class AssetUnitMergeContext:
    sources: tuple[AssetUnit, ...]
    existing_boundary_source_unit_ids: tuple[str, ...] = ()
    result_unit_code_exists: bool = False
    upstream_coverages: tuple[UpstreamContractAssetUnit, ...] = ()
    upstream_contracts: tuple[UpstreamContract, ...] = ()
    terminal_coverages: tuple[TerminalContractAssetUnit, ...] = ()
    terminal_contracts: tuple[TerminalContract, ...] = ()
    lifecycle_events: tuple[ContractLifecycleEvent, ...] = ()


class AssetUnitBoundaryRepository:
    """Load and persist one locked boundary-change aggregate."""

    async def load_split_context(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        scope: EffectivePartyScope,
        effective_date: date,
        result_unit_codes: tuple[str, ...],
        for_update: bool,
    ) -> AssetUnitSplitContext:
        if for_update:
            locked_sources = await asset_unit_repository.lock_for_write(
                db,
                unit_ids=(unit_id,),
                scope=scope,
            )
            source = locked_sources[0] if len(locked_sources) == 1 else None
        else:
            source = await asset_unit_repository.get(
                db,
                unit_id=unit_id,
                scope=scope,
            )
        if source is None:
            return AssetUnitSplitContext(source=None)

        boundary_source_statement = select(AssetUnitBoundarySource).where(
            AssetUnitBoundarySource.asset_unit_id == unit_id
        )
        if for_update:
            boundary_source_statement = boundary_source_statement.with_for_update()
        existing_boundary_source = (
            (await db.execute(boundary_source_statement)).scalars().one_or_none()
        )

        code_statement = select(AssetUnit.unit_code).where(
            AssetUnit.unit_code.in_(result_unit_codes)
        )
        if for_update:
            code_statement = code_statement.with_for_update()
        existing_result_unit_codes = tuple(
            (await db.execute(code_statement)).scalars().all()
        )

        upstream_statement = select(UpstreamContractAssetUnit).where(
            UpstreamContractAssetUnit.asset_unit_id == unit_id,
            or_(
                UpstreamContractAssetUnit.effective_to.is_(None),
                UpstreamContractAssetUnit.effective_to >= effective_date,
            ),
        )
        terminal_statement = select(TerminalContractAssetUnit).where(
            TerminalContractAssetUnit.asset_unit_id == unit_id,
            or_(
                TerminalContractAssetUnit.effective_to.is_(None),
                TerminalContractAssetUnit.effective_to >= effective_date,
            ),
        )
        if for_update:
            upstream_statement = upstream_statement.with_for_update()
            terminal_statement = terminal_statement.with_for_update()
        upstream_coverages = tuple(
            (await db.execute(upstream_statement)).scalars().all()
        )
        terminal_coverages = tuple(
            (await db.execute(terminal_statement)).scalars().all()
        )

        upstream_ids = {
            coverage.upstream_contract_id for coverage in upstream_coverages
        }
        terminal_ids = {
            coverage.terminal_contract_id for coverage in terminal_coverages
        }
        upstream_contracts = await self._load_by_ids(
            db,
            model=UpstreamContract,
            ids=upstream_ids,
            for_update=for_update,
        )
        terminal_contracts = await self._load_by_ids(
            db,
            model=TerminalContract,
            ids=terminal_ids,
            for_update=for_update,
        )
        lifecycle_ids = upstream_ids | terminal_ids
        lifecycle_events: tuple[ContractLifecycleEvent, ...] = ()
        if len(lifecycle_ids) > 0:
            event_statement = select(ContractLifecycleEvent).where(
                ContractLifecycleEvent.contract_id.in_(lifecycle_ids),
                ContractLifecycleEvent.effective_date <= effective_date,
            )
            if for_update:
                event_statement = event_statement.with_for_update()
            lifecycle_events = tuple(
                (await db.execute(event_statement)).scalars().all()
            )
        return AssetUnitSplitContext(
            source=source,
            existing_boundary_change_id=(
                existing_boundary_source.boundary_change_id
                if existing_boundary_source is not None
                else None
            ),
            existing_result_unit_codes=existing_result_unit_codes,
            upstream_coverages=upstream_coverages,
            upstream_contracts=tuple(upstream_contracts),
            terminal_coverages=terminal_coverages,
            terminal_contracts=tuple(terminal_contracts),
            lifecycle_events=lifecycle_events,
        )

    async def get_boundary_change_by_idempotency(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        idempotency_key: str,
    ) -> AssetUnitBoundaryChange | None:
        statement = select(AssetUnitBoundaryChange).where(
            AssetUnitBoundaryChange.created_by == actor_id,
            AssetUnitBoundaryChange.idempotency_key == idempotency_key,
        )
        return (await db.execute(statement)).scalars().one_or_none()

    async def load_merge_context(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        scope: EffectivePartyScope,
        effective_date: date,
        result_unit_code: str,
        for_update: bool,
    ) -> AssetUnitMergeContext:
        normalized_ids = tuple(sorted(set(unit_ids)))
        if for_update:
            sources = await asset_unit_repository.lock_for_write(
                db,
                unit_ids=normalized_ids,
                scope=scope,
            )
        else:
            loaded_sources: list[AssetUnit] = []
            for unit_id in normalized_ids:
                source = await asset_unit_repository.get(
                    db,
                    unit_id=unit_id,
                    scope=scope,
                )
                if source is not None:
                    loaded_sources.append(source)
            sources = tuple(loaded_sources)

        boundary_source_statement = select(AssetUnitBoundarySource).where(
            AssetUnitBoundarySource.asset_unit_id.in_(normalized_ids)
        )
        code_statement = select(AssetUnit.id).where(
            AssetUnit.unit_code == result_unit_code
        )
        upstream_statement = select(UpstreamContractAssetUnit).where(
            UpstreamContractAssetUnit.asset_unit_id.in_(normalized_ids),
            or_(
                UpstreamContractAssetUnit.effective_to.is_(None),
                UpstreamContractAssetUnit.effective_to >= effective_date,
            ),
        )
        terminal_statement = select(TerminalContractAssetUnit).where(
            TerminalContractAssetUnit.asset_unit_id.in_(normalized_ids),
            or_(
                TerminalContractAssetUnit.effective_to.is_(None),
                TerminalContractAssetUnit.effective_to >= effective_date,
            ),
        )
        if for_update:
            boundary_source_statement = boundary_source_statement.with_for_update()
            code_statement = code_statement.with_for_update()
            upstream_statement = upstream_statement.with_for_update()
            terminal_statement = terminal_statement.with_for_update()

        existing_boundary_sources = tuple(
            (await db.execute(boundary_source_statement)).scalars().all()
        )
        result_unit_code_exists = (
            await db.execute(code_statement)
        ).scalars().first() is not None
        upstream_coverages = tuple(
            (await db.execute(upstream_statement)).scalars().all()
        )
        terminal_coverages = tuple(
            (await db.execute(terminal_statement)).scalars().all()
        )
        upstream_ids = {
            coverage.upstream_contract_id for coverage in upstream_coverages
        }
        terminal_ids = {
            coverage.terminal_contract_id for coverage in terminal_coverages
        }
        upstream_contracts = await self._load_by_ids(
            db,
            model=UpstreamContract,
            ids=upstream_ids,
            for_update=for_update,
        )
        terminal_contracts = await self._load_by_ids(
            db,
            model=TerminalContract,
            ids=terminal_ids,
            for_update=for_update,
        )
        lifecycle_ids = upstream_ids | terminal_ids
        lifecycle_events: tuple[ContractLifecycleEvent, ...] = ()
        if len(lifecycle_ids) > 0:
            event_statement = select(ContractLifecycleEvent).where(
                ContractLifecycleEvent.contract_id.in_(lifecycle_ids),
                ContractLifecycleEvent.effective_date <= effective_date,
            )
            if for_update:
                event_statement = event_statement.with_for_update()
            lifecycle_events = tuple(
                (await db.execute(event_statement)).scalars().all()
            )
        return AssetUnitMergeContext(
            sources=tuple(sources),
            existing_boundary_source_unit_ids=tuple(
                sorted(source.asset_unit_id for source in existing_boundary_sources)
            ),
            result_unit_code_exists=result_unit_code_exists,
            upstream_coverages=upstream_coverages,
            upstream_contracts=tuple(upstream_contracts),
            terminal_coverages=terminal_coverages,
            terminal_contracts=tuple(terminal_contracts),
            lifecycle_events=lifecycle_events,
        )

    async def get_asset_unit_version(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
    ) -> int | None:
        statement = select(AssetUnit.version).where(AssetUnit.id == unit_id)
        return (await db.execute(statement)).scalar_one_or_none()

    async def persist_split(
        self,
        db: AsyncSession,
        *,
        source: AssetUnit,
        results: list[AssetUnit],
        boundary_change: AssetUnitBoundaryChange,
        active_upstream_contract_ids: tuple[str, ...],
        effective_date: date,
    ) -> AssetUnitBoundaryChange:
        statement = (
            select(UpstreamContractAssetUnit)
            .where(
                UpstreamContractAssetUnit.asset_unit_id == source.id,
                UpstreamContractAssetUnit.upstream_contract_id.in_(
                    active_upstream_contract_ids
                ),
                UpstreamContractAssetUnit.effective_from <= effective_date,
                or_(
                    UpstreamContractAssetUnit.effective_to.is_(None),
                    UpstreamContractAssetUnit.effective_to >= effective_date,
                ),
            )
            .with_for_update()
        )
        source_coverages = tuple((await db.execute(statement)).scalars().all())
        new_coverages: list[UpstreamContractAssetUnit] = []
        for coverage in source_coverages:
            previous_end = coverage.effective_to
            if coverage.effective_from == effective_date:
                await db.delete(coverage)
            else:
                coverage.effective_to = effective_date - timedelta(days=1)
            new_coverages.extend(
                UpstreamContractAssetUnit(  # type: ignore[call-arg]
                    upstream_contract_id=coverage.upstream_contract_id,
                    asset_unit_id=result.id,
                    effective_from=effective_date,
                    effective_to=previous_end,
                )
                for result in results
            )
        boundary_source = AssetUnitBoundarySource(  # type: ignore[call-arg]
            asset_unit_id=source.id,
            boundary_change_id=boundary_change.id,
        )
        db.add_all([*results, *new_coverages, boundary_change, boundary_source])
        await db.flush()
        return boundary_change

    async def persist_merge(
        self,
        db: AsyncSession,
        *,
        sources: tuple[AssetUnit, ...],
        result: AssetUnit,
        boundary_change: AssetUnitBoundaryChange,
        active_upstream_contract_ids: tuple[str, ...],
        effective_date: date,
    ) -> AssetUnitBoundaryChange:
        source_ids = tuple(source.id for source in sources)
        statement = (
            select(UpstreamContractAssetUnit)
            .where(
                UpstreamContractAssetUnit.asset_unit_id.in_(source_ids),
                UpstreamContractAssetUnit.upstream_contract_id.in_(
                    active_upstream_contract_ids
                ),
                UpstreamContractAssetUnit.effective_from <= effective_date,
                or_(
                    UpstreamContractAssetUnit.effective_to.is_(None),
                    UpstreamContractAssetUnit.effective_to >= effective_date,
                ),
            )
            .with_for_update()
        )
        source_coverages = tuple((await db.execute(statement)).scalars().all())
        coverage_end_by_contract: dict[str, date | None] = {}
        for coverage in source_coverages:
            previous_end = coverage.effective_to
            existing_end = coverage_end_by_contract.setdefault(
                coverage.upstream_contract_id,
                previous_end,
            )
            if existing_end != previous_end:
                raise RuntimeError(
                    "merge source upstream coverage boundaries changed while locked"
                )
            if coverage.effective_from == effective_date:
                await db.delete(coverage)
            else:
                coverage.effective_to = effective_date - timedelta(days=1)

        new_coverages = [
            UpstreamContractAssetUnit(  # type: ignore[call-arg]
                upstream_contract_id=contract_id,
                asset_unit_id=result.id,
                effective_from=effective_date,
                effective_to=coverage_end_by_contract[contract_id],
            )
            for contract_id in active_upstream_contract_ids
        ]
        boundary_sources = [
            AssetUnitBoundarySource(  # type: ignore[call-arg]
                asset_unit_id=source.id,
                boundary_change_id=boundary_change.id,
            )
            for source in sources
        ]
        db.add_all([result, boundary_change])
        await db.flush()
        db.add_all([*new_coverages, *boundary_sources])
        await db.flush()
        return boundary_change

    @staticmethod
    async def _load_by_ids(
        db: AsyncSession,
        *,
        model: type[TContract],
        ids: set[str],
        for_update: bool,
    ) -> tuple[TContract, ...]:
        if len(ids) == 0:
            return ()
        statement = select(model).where(model.id.in_(ids))
        if for_update:
            statement = statement.with_for_update()
        return tuple((await db.execute(statement)).scalars().all())


asset_unit_boundary_repository = AssetUnitBoundaryRepository()


__all__ = [
    "AssetUnitBoundaryRepository",
    "AssetUnitMergeContext",
    "AssetUnitSplitContext",
    "asset_unit_boundary_repository",
]
