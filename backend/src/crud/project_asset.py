"""CRUD helpers for project-asset bindings."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset import Asset
from ..models.project_asset import ProjectAsset


class CRUDProjectAsset:
    """Project-asset binding CRUD methods."""

    async def get_asset_ids_grouped_by_project_name(
        self,
        db: AsyncSession,
    ) -> dict[str, list[str]]:
        stmt = (
            select(Asset.project_name, Asset.id)
            .where(Asset.project_name.isnot(None), Asset.project_name != "")
            .order_by(Asset.project_name, Asset.id)
        )
        grouped: dict[str, list[str]] = {}
        for project_name, asset_id in (await db.execute(stmt)).all():
            grouped.setdefault(str(project_name), []).append(str(asset_id))
        return grouped

    async def get_active_by_asset_id(
        self,
        db: AsyncSession,
        *,
        asset_id: str,
    ) -> ProjectAsset | None:
        stmt = select(ProjectAsset).where(
            ProjectAsset.asset_id == asset_id,
            ProjectAsset.valid_to.is_(None),
        )
        return (await db.execute(stmt)).scalars().first()

    async def create_active(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        asset_id: str,
    ) -> ProjectAsset:
        binding = ProjectAsset()
        binding.project_id = project_id
        binding.asset_id = asset_id
        db.add(binding)
        await db.flush()
        return binding

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
