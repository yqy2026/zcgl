"""Data access for asset-operations v5 asset units."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import Any, TypeVar

from sqlalchemy import Select, exists, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from ..models.asset_contract import TerminalContract, TerminalContractAssetUnit
from ..models.asset_unit import AssetUnit, PropertyCertificateAssetUnit
from ..models.party import Party
from ..models.project import Project
from ..models.property_certificate import PropertyCertificate
from ..services.party_scope_resolver import EffectivePartyScope

_T = TypeVar("_T", bound=tuple[Any, ...])


class AssetUnitRepository:
    """Read asset units through an explicit, fail-closed Party scope."""

    async def add(self, db: AsyncSession, *, unit: AssetUnit) -> AssetUnit:
        """Insert a new unit in the caller's open transaction."""
        db.add(unit)
        await db.flush()
        return unit

    @staticmethod
    def _apply_scope(
        statement: Select[_T],
        *,
        scope: EffectivePartyScope,
    ) -> Select[_T]:
        if scope.scope_mode == "unrestricted":
            return statement

        conditions: list[ColumnElement[bool]] = []
        if scope.scope_mode in {"owner", "all"} and len(scope.owner_party_ids) > 0:
            conditions.append(AssetUnit.owner_party_id.in_(scope.owner_party_ids))
        if scope.scope_mode in {"manager", "all"} and len(scope.manager_party_ids) > 0:
            conditions.append(
                exists(
                    select(1)
                    .select_from(Project)
                    .where(
                        Project.id == AssetUnit.project_id,
                        Project.manager_party_id.in_(scope.manager_party_ids),
                    )
                )
            )
        if len(conditions) == 0:
            return statement.where(false())
        return statement.where(or_(*conditions))

    async def list(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        project_id: str | None = None,
        owner_party_id: str | None = None,
        usage_type: str | None = None,
        query: str | None = None,
        non_rentable_only: bool = False,
        rentable_only: bool = False,
        unit_ids: tuple[str, ...] | None = None,
        exclude_unit_ids: tuple[str, ...] | None = None,
        missing_certificate_only: bool = False,
        as_of: date | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[AssetUnit], int]:
        if scope.scope_mode != "unrestricted" and (
            scope.error_code is not None or len(scope.effective_party_ids) == 0
        ):
            return [], 0
        statement = self._apply_scope(select(AssetUnit), scope=scope)
        if non_rentable_only:
            statement = statement.where(
                or_(
                    AssetUnit.is_operating.is_(False),
                    AssetUnit.rentable_area <= 0,
                )
            )
        if rentable_only:
            statement = statement.where(
                AssetUnit.is_operating.is_(True), AssetUnit.rentable_area > 0
            )
        if unit_ids is not None:
            if len(unit_ids) == 0:
                return [], 0
            statement = statement.where(AssetUnit.id.in_(unit_ids))
        if exclude_unit_ids is not None and len(exclude_unit_ids) > 0:
            statement = statement.where(~AssetUnit.id.in_(exclude_unit_ids))
        if missing_certificate_only and as_of is not None:
            # 契约：走该筛选必须携带统计日（service 层传业务当天）；None 时
            # 跳过过滤而非误判全部缺证（effective_from <= NULL 恒 False）。
            statement = statement.where(
                ~exists(
                    select(1)
                    .select_from(PropertyCertificateAssetUnit)
                    .where(
                        PropertyCertificateAssetUnit.asset_unit_id == AssetUnit.id,
                        PropertyCertificateAssetUnit.effective_from <= as_of,
                        or_(
                            PropertyCertificateAssetUnit.effective_to.is_(None),
                            PropertyCertificateAssetUnit.effective_to >= as_of,
                        ),
                    )
                )
            )
        if project_id is not None:
            statement = statement.where(AssetUnit.project_id == project_id)
        if owner_party_id is not None:
            statement = statement.where(AssetUnit.owner_party_id == owner_party_id)
        if usage_type is not None:
            statement = statement.where(AssetUnit.usage_type == usage_type)
        normalized_query = query.strip() if query is not None else ""
        if normalized_query != "":
            pattern = f"%{normalized_query}%"
            # 原型物业页搜索范围：地址、单元、租户、产权证号。
            tenant_name_match = exists(
                select(1)
                .select_from(TerminalContractAssetUnit)
                .join(
                    TerminalContract,
                    TerminalContract.id
                    == TerminalContractAssetUnit.terminal_contract_id,
                )
                .join(
                    Party,
                    Party.id == TerminalContract.tenant_party_id,
                )
                .where(
                    TerminalContractAssetUnit.asset_unit_id == AssetUnit.id,
                    Party.name.ilike(pattern),
                )
            )
            certificate_number_match = exists(
                select(1)
                .select_from(PropertyCertificateAssetUnit)
                .join(
                    PropertyCertificate,
                    PropertyCertificate.id
                    == PropertyCertificateAssetUnit.certificate_id,
                )
                .where(
                    PropertyCertificateAssetUnit.asset_unit_id == AssetUnit.id,
                    PropertyCertificate.certificate_number.ilike(pattern),
                )
            )
            statement = statement.where(
                or_(
                    AssetUnit.unit_code.ilike(pattern),
                    AssetUnit.name.ilike(pattern),
                    AssetUnit.address.ilike(pattern),
                    tenant_name_match,
                    certificate_number_match,
                )
            )

        total_statement = select(func.count()).select_from(
            statement.order_by(None).subquery()
        )
        total = int((await db.execute(total_statement)).scalar_one())
        rows = (
            (
                await db.execute(
                    statement.order_by(AssetUnit.unit_code).offset(offset).limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def distinct_usage_types(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
    ) -> Sequence[str]:
        """Distinct usage_type values within scope, for list filter options."""
        if scope.scope_mode != "unrestricted" and (
            scope.error_code is not None or len(scope.effective_party_ids) == 0
        ):
            return []
        statement = self._apply_scope(
            select(AssetUnit.usage_type).distinct(), scope=scope
        )
        rows = await db.execute(statement.order_by(AssetUnit.usage_type))
        return [value for (value,) in rows.all() if value]

    async def get(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        scope: EffectivePartyScope,
        for_update: bool = False,
    ) -> AssetUnit | None:
        if scope.scope_mode != "unrestricted" and (
            scope.error_code is not None or len(scope.effective_party_ids) == 0
        ):
            return None
        statement = self._apply_scope(select(AssetUnit), scope=scope).where(
            AssetUnit.id == unit_id
        )
        if for_update:
            statement = statement.with_for_update()
        return (await db.execute(statement)).scalars().one_or_none()

    async def get_units_by_ids(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        scope: EffectivePartyScope,
    ) -> tuple[AssetUnit, ...]:
        """Batched scoped read for detail enrichment (units matrix)."""
        if len(unit_ids) == 0 or (
            scope.scope_mode != "unrestricted"
            and (scope.error_code is not None or len(scope.effective_party_ids) == 0)
        ):
            return ()
        statement = (
            self._apply_scope(select(AssetUnit), scope=scope)
            .where(AssetUnit.id.in_(unit_ids))
            .order_by(AssetUnit.unit_code)
        )
        return tuple((await db.execute(statement)).scalars().all())

    async def lock_for_write(
        self,
        db: AsyncSession,
        *,
        unit_ids: Iterable[str],
        scope: EffectivePartyScope,
    ) -> tuple[AssetUnit, ...]:
        """Lock scoped units in one stable order before boundary-dependent writes.

        Boundary changes and contract-coverage mutations must both enter through
        this row-lock contract so neither can validate against stale unit facts.
        """
        normalized_ids = tuple(sorted(set(unit_ids)))
        if len(normalized_ids) == 0 or (
            scope.scope_mode != "unrestricted"
            and (scope.error_code is not None or len(scope.effective_party_ids) == 0)
        ):
            return ()
        statement = (
            self._apply_scope(select(AssetUnit), scope=scope)
            .where(AssetUnit.id.in_(normalized_ids))
            .order_by(AssetUnit.id)
            .with_for_update()
        )
        return tuple((await db.execute(statement)).scalars().all())

    async def get_project_manager_party_ids(
        self,
        db: AsyncSession,
        *,
        project_ids: Iterable[str],
    ) -> dict[str, str | None]:
        """Return the current operating Party for each referenced project."""
        normalized_ids = tuple(sorted(set(project_ids)))
        if len(normalized_ids) == 0:
            return {}
        statement = (
            select(Project.id, Project.manager_party_id)
            .where(Project.id.in_(normalized_ids))
            .order_by(Project.id)
        )
        rows = (await db.execute(statement)).all()
        return {project_id: manager_party_id for project_id, manager_party_id in rows}

    async def project_names(
        self,
        db: AsyncSession,
        *,
        project_ids: Iterable[str],
    ) -> dict[str, str]:
        """Batched project id → name read for list enrichment."""
        normalized_ids = tuple(sorted(set(project_ids)))
        if len(normalized_ids) == 0:
            return {}
        statement = select(Project.id, Project.project_name).where(
            Project.id.in_(normalized_ids)
        )
        return {row[0]: row[1] for row in (await db.execute(statement)).all()}

    async def project_options(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
    ) -> Sequence[tuple[str, str]]:
        """Distinct (project_id, project_name) within scope, for filter options."""
        if scope.scope_mode != "unrestricted" and (
            scope.error_code is not None or len(scope.effective_party_ids) == 0
        ):
            return []
        statement = (
            self._apply_scope(select(AssetUnit), scope=scope)
            .join(Project, Project.id == AssetUnit.project_id)
            .with_only_columns(AssetUnit.project_id, Project.project_name)
            .distinct()
            .order_by(AssetUnit.project_id)
        )
        return [
            (row[0], row[1])
            for row in (await db.execute(statement)).all()
            if row[0] and row[1]
        ]

    async def active_certificate_counts(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        as_of: date,
    ) -> dict[str, int]:
        """Count today-active certificate links per unit, page-sized batches."""
        if len(unit_ids) == 0:
            return {}
        statement = (
            select(
                PropertyCertificateAssetUnit.asset_unit_id,
                func.count(),
            )
            .where(
                PropertyCertificateAssetUnit.asset_unit_id.in_(unit_ids),
                PropertyCertificateAssetUnit.effective_from <= as_of,
                or_(
                    PropertyCertificateAssetUnit.effective_to.is_(None),
                    PropertyCertificateAssetUnit.effective_to >= as_of,
                ),
            )
            .group_by(PropertyCertificateAssetUnit.asset_unit_id)
        )
        rows = (await db.execute(statement)).all()
        return {unit_id: int(count) for unit_id, count in rows}


asset_unit_repository = AssetUnitRepository()


__all__ = ["AssetUnitRepository", "asset_unit_repository"]
