# -*- coding: utf-8 -*-
"""Fix single-entity select destructuring bug (E2E 500 root cause)."""
import io


def fix(path, pairs):
    src = io.open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert old in src, path + ': missing ' + repr(old[:70])
        src = src.replace(old, new)
    io.open(path, 'w', encoding='utf-8').write(src)
    print('fixed ' + path)


# crud: 两个单实体批量方法改为 scalars().all()，返回类型改为 link 元组
fix(
    'src/crud/asset_contract.py',
    [
        (
            '''    ) -> tuple[tuple[str, TerminalContractAssetUnit], ...]:
        """Batched terminal coverage read: (contract_id, link) rows."""
        if len(contract_ids) == 0:
            return ()
        statement = (
            select(TerminalContractAssetUnit)
            .where(TerminalContractAssetUnit.terminal_contract_id.in_(contract_ids))
            .order_by(
                TerminalContractAssetUnit.terminal_contract_id,
                TerminalContractAssetUnit.asset_unit_id,
            )
        )
        return tuple((row[0], row[1]) for row in (await db.execute(statement)).all())''',
            '''    ) -> tuple[TerminalContractAssetUnit, ...]:
        """Batched terminal coverage read (link carries terminal_contract_id)."""
        if len(contract_ids) == 0:
            return ()
        statement = (
            select(TerminalContractAssetUnit)
            .where(TerminalContractAssetUnit.terminal_contract_id.in_(contract_ids))
            .order_by(
                TerminalContractAssetUnit.terminal_contract_id,
                TerminalContractAssetUnit.asset_unit_id,
            )
        )
        return tuple((await db.execute(statement)).scalars().all())''',
        ),
        (
            '''    ) -> tuple[tuple[str, UpstreamContractAssetUnit], ...]:
        """Batched upstream coverage read: (contract_id, link) rows."""
        if len(contract_ids) == 0:
            return ()
        statement = (
            select(UpstreamContractAssetUnit)
            .where(UpstreamContractAssetUnit.upstream_contract_id.in_(contract_ids))
            .order_by(
                UpstreamContractAssetUnit.upstream_contract_id,
                UpstreamContractAssetUnit.asset_unit_id,
            )
        )
        return tuple((row[0], row[1]) for row in (await db.execute(statement)).all())''',
            '''    ) -> tuple[UpstreamContractAssetUnit, ...]:
        """Batched upstream coverage read (link carries upstream_contract_id)."""
        if len(contract_ids) == 0:
            return ()
        statement = (
            select(UpstreamContractAssetUnit)
            .where(UpstreamContractAssetUnit.upstream_contract_id.in_(contract_ids))
            .order_by(
                UpstreamContractAssetUnit.upstream_contract_id,
                UpstreamContractAssetUnit.asset_unit_id,
            )
        )
        return tuple((await db.execute(statement)).scalars().all())''',
        ),
    ],
)

# query_service: 调用方改按 link 属性分组
fix(
    'src/services/asset_operations/query_service.py',
    [
        (
            '''        covered_by_contract: dict[str, list[TerminalContractAssetUnit]] = defaultdict(
            list
        )
        for _contract_id, link in covered_rows:
            covered_by_contract[link.terminal_contract_id].append(link)''',
            '''        covered_by_contract: dict[str, list[TerminalContractAssetUnit]] = defaultdict(
            list
        )
        for link in covered_rows:
            covered_by_contract[link.terminal_contract_id].append(link)''',
        ),
        # Protocol 返回类型同步
        (
            '''    async def list_terminal_coverages_by_ids(
        self,
        db: AsyncSession,
        *,
        contract_ids: tuple[str, ...],
    ) -> tuple[tuple[str, TerminalContractAssetUnit], ...]: ...''',
            '''    async def list_terminal_coverages_by_ids(
        self,
        db: AsyncSession,
        *,
        contract_ids: tuple[str, ...],
    ) -> tuple[TerminalContractAssetUnit, ...]: ...''',
        ),
        (
            '''    async def list_upstream_coverages_batched(
        self,
        db: AsyncSession,
        *,
        contract_ids: tuple[str, ...],
    ) -> tuple[tuple[str, UpstreamContractAssetUnit], ...]: ...''',
            '''    async def list_upstream_coverages_batched(
        self,
        db: AsyncSession,
        *,
        contract_ids: tuple[str, ...],
    ) -> tuple[UpstreamContractAssetUnit, ...]: ...''',
        ),
    ],
)

# monthly_workbench: 调用方改按 link 属性分组
fix(
    'src/services/asset_operations/monthly_workbench_service.py',
    [
        (
            '''        for upstream_id, link in (
            await asset_contract_repository.list_upstream_coverages_batched(
                db,
                contract_ids=tuple(sorted(contract.id for contract, _ in flagged)),
            )
        ):
            coverages_by_contract[upstream_id].append(link)''',
            '''        for link in (
            await asset_contract_repository.list_upstream_coverages_batched(
                db,
                contract_ids=tuple(sorted(contract.id for contract, _ in flagged)),
            )
        ):
            coverages_by_contract[link.upstream_contract_id].append(link)''',
        ),
    ],
)

print('single-entity fix done')
