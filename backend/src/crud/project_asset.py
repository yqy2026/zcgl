"""CRUD helpers for project-asset bindings."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.project_asset import ProjectAsset


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CRUDProjectAsset:
    """Project-asset binding CRUD methods."""

    async def bind_asset(
        self,
        db: AsyncSession,
        *,
        obj_in: dict[str, Any],
        commit: bool = True,
    ) -> ProjectAsset:
        relation = ProjectAsset(**obj_in)
        db.add(relation)
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(relation)
        return relation

    async def unbind_asset(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        asset_id: str,
        unbind_reason: str | None = None,
        commit: bool = True,
    ) -> ProjectAsset | None:
        project_id_column = getattr(ProjectAsset, "project_id")
        asset_id_column = getattr(ProjectAsset, "asset_id")
        stmt = (
            select(ProjectAsset)
            .where(project_id_column == project_id, asset_id_column == asset_id)
            .where(ProjectAsset.valid_to.is_(None))
            .order_by(ProjectAsset.valid_from.desc())
            .limit(1)
        )
        relation = (await db.execute(stmt)).scalars().first()
        if relation is None:
            return None

        relation.valid_to = _utcnow_naive()
        relation.unbind_reason = unbind_reason

        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(relation)
        return relation

    async def get_project_assets(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        active_only: bool = True,
    ) -> list[ProjectAsset]:
        project_id_column = getattr(ProjectAsset, "project_id")
        stmt = select(ProjectAsset).where(project_id_column == project_id)
        if active_only:
            stmt = stmt.where(ProjectAsset.valid_to.is_(None))
        return list((await db.execute(stmt)).scalars().all())

    async def get_asset_projects(
        self,
        db: AsyncSession,
        *,
        asset_id: str,
        active_only: bool = True,
    ) -> list[ProjectAsset]:
        stmt = select(ProjectAsset).where(ProjectAsset.asset_id == asset_id)
        if active_only:
            stmt = stmt.where(ProjectAsset.valid_to.is_(None))
        return list((await db.execute(stmt)).scalars().all())


project_asset_crud = CRUDProjectAsset()


__all__ = ["CRUDProjectAsset", "project_asset_crud"]
