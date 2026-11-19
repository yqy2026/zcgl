# -*- coding: utf-8 -*-
"""Mypy fixes batch 2: query_service + crud + export service."""
import io


def fix(path, pairs):
    src = io.open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert old in src, path + ': missing ' + repr(old[:70])
        src = src.replace(old, new)
    io.open(path, 'w', encoding='utf-8').write(src)
    print('fixed ' + path)


# ---- query_service.py ----
fix(
    'src/services/asset_operations/query_service.py',
    [
        # kwargs dicts → Any so **unpack matches the protocol signature
        (
            '''        base_kwargs: dict[str, object] = {''',
            '''        base_kwargs: dict[str, Any] = {''',
        ),
        (
            '''        def restricted(**extra: object) -> dict[str, object]:''',
            '''        def restricted(**extra: Any) -> dict[str, Any]:''',
        ),
        (
            '''    def _unit_filter_kwargs(
        filter: str | None,
        *,
        today: date,
        rented_ids: set[str],
        included_ids: frozenset[str],
    ) -> dict[str, object]:''',
            '''    def _unit_filter_kwargs(
        filter: str | None,
        *,
        today: date,
        rented_ids: set[str],
        included_ids: frozenset[str],
    ) -> dict[str, Any]:''',
        ),
        # view_for expects tuple
        (
            '''        view = view_for(version, items, candidates)
        decided = {item.asset_unit_id: item.included for item in view.items}''',
            '''        view = view_for(version, tuple(items), candidates)
        decided = {item.asset_unit_id: item.included for item in view.items}''',
        ),
        # terminal_by_unit default (None, None) → widen dict value type
        (
            '''        terminal_by_unit: dict[str, tuple[TerminalContract, date]] = {}''',
            '''        terminal_by_unit: dict[str, tuple[TerminalContract | None, date | None]] = {}''',
        ),
        # setdefault list append on tuple-typed dict
        (
            '''        events_by_id: dict[str, tuple[ContractLifecycleEvent, ...]] = {}
        for event in events:
            events_by_id.setdefault(event.contract_id, []).append(event)
        events_by_id = {key: tuple(value) for key, value in events_by_id.items()}

        statuses: dict[str, str] = {}''',
            '''        grouped_events: dict[str, list[ContractLifecycleEvent]] = {}
        for event in events:
            grouped_events.setdefault(event.contract_id, []).append(event)
        events_by_id: dict[str, tuple[ContractLifecycleEvent, ...]] = {
            key: tuple(value) for key, value in grouped_events.items()
        }

        statuses: dict[str, str] = {}''',
        ),
        # SimpleNamespace → real RentQueryFacts
        (
            '''        from types import SimpleNamespace

        facts = SimpleNamespace(
            contracts=(contract,),
            entries=entries,
            records=records,
            schedules=schedules,
            events=events,
        )
        views, _ = rent_ledger_query_service._views(facts, today=today)''',
            '''        from ...crud.rent_ledger_queries import RentQueryFacts

        facts = RentQueryFacts((contract,), entries, records, schedules, events)
        views, _ = rent_ledger_query_service._views(facts, today=today)''',
        ),
    ],
)

# ---- Protocol additions in query_service ----
src = io.open('src/services/asset_operations/query_service.py', encoding='utf-8').read()
old = '''    async def distinct_usage_types(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
    ) -> Sequence[str]: ...'''
new = '''    async def distinct_usage_types(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
    ) -> Sequence[str]: ...

    async def get_units_by_ids(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        scope: EffectivePartyScope,
    ) -> tuple[AssetUnit, ...]: ...

    async def project_names(
        self,
        db: AsyncSession,
        *,
        project_ids: Iterable[str],
    ) -> dict[str, str]: ...

    async def active_certificate_counts(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        as_of: date,
    ) -> dict[str, int]: ...'''
assert old in src
src = src.replace(old, new, 1)

old = '''    async def list_terminal_by_upstream(
        self,
        db: AsyncSession,
        *,
        upstream_contract_id: str,
    ) -> tuple[TerminalContract, ...]: ...'''
new = '''    async def list_terminal_by_upstream(
        self,
        db: AsyncSession,
        *,
        upstream_contract_id: str,
    ) -> tuple[TerminalContract, ...]: ...

    async def list_terminal_unit_labels(
        self,
        db: AsyncSession,
        *,
        contract_ids: tuple[str, ...],
    ) -> dict[str, tuple[str, ...]]: ...

    async def list_active_terminals_by_units(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        as_of: date,
    ) -> tuple[tuple[str, TerminalContract], ...]: ...

    async def coverage_history_for_unit(
        self,
        db: AsyncSession,
        *,
        asset_unit_id: str,
    ) -> tuple[tuple[TerminalContract, ...], tuple[UpstreamContract, ...]]: ...'''
assert old in src
src = src.replace(old, new, 1)

# Any import check
if 'from typing import Any' not in src:
    src = src.replace(
        'from typing import Protocol',
        'from typing import Any, Protocol',
        1,
    )
io.open('src/services/asset_operations/query_service.py', 'w', encoding='utf-8').write(src)
print('query_service protocols patched')

# ---- crud/party.py ----
fix(
    'src/crud/party.py',
    [
        (
            '''        statement = select(Party.id, Party.name).where(Party.id.in_(party_ids))
        return dict((await db.execute(statement)).all())''',
            '''        statement = select(Party.id, Party.name).where(Party.id.in_(party_ids))
        return {row[0]: row[1] for row in (await db.execute(statement)).all()}''',
        ),
    ],
)

# ---- crud/asset_contract.py ----
fix(
    'src/crud/asset_contract.py',
    [
        (
            '''        rows = (await db.execute(statement)).all()
        return tuple((await db.execute(statement)).scalars().all())''',
            '''        rows = (await db.execute(statement)).scalars().all()
        return tuple(rows)''',
        ),
    ],
)

# ---- crud/asset_unit.py ---- (Project has project_name, not name)
fix(
    'src/crud/asset_unit.py',
    [
        (
            '''        statement = select(Project.id, Project.name).where(
            Project.id.in_(normalized_ids)
        )''',
            '''        statement = select(Project.id, Project.project_name).where(
            Project.id.in_(normalized_ids)
        )''',
        ),
    ],
)

# ---- asset_unit_export_service.py ----
fix(
    'src/services/asset_operations/asset_unit_export_service.py',
    [
        (
            '                _ASSESSMENT_LABELS.get(item.assessment, "—"),',
            '                _ASSESSMENT_LABELS.get(item.assessment or "", "—"),',
        ),
    ],
)

print('batch 2 done')
