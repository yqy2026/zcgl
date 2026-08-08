"""CRUD helpers for project-asset bindings."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.project_asset import ProjectAsset


class CRUDProjectAsset:
    """Project-asset binding CRUD methods."""

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
