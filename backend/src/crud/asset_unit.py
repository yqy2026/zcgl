"""Data access for asset-operations v5 asset units."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import Select, exists, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from ..models.asset_unit import AssetUnit
from ..models.project import Project
from ..services.party_scope_resolver import EffectivePartyScope


class AssetUnitRepository:
    """Read asset units through an explicit, fail-closed Party scope."""

    @staticmethod
    def _apply_scope(
        statement: Select[tuple[AssetUnit]],
        *,
        scope: EffectivePartyScope,
    ) -> Select[tuple[AssetUnit]]:
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
        if project_id is not None:
            statement = statement.where(AssetUnit.project_id == project_id)
        if owner_party_id is not None:
            statement = statement.where(AssetUnit.owner_party_id == owner_party_id)
        if usage_type is not None:
            statement = statement.where(AssetUnit.usage_type == usage_type)
        normalized_query = query.strip() if query is not None else ""
        if normalized_query != "":
            pattern = f"%{normalized_query}%"
            statement = statement.where(
                or_(
                    AssetUnit.unit_code.ilike(pattern),
                    AssetUnit.name.ilike(pattern),
                    AssetUnit.address.ilike(pattern),
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


asset_unit_repository = AssetUnitRepository()


__all__ = ["AssetUnitRepository", "asset_unit_repository"]
