from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.base import CRUDBase
from ..models.ownership import Ownership
from ..schemas.ownership import OwnershipCreate, OwnershipUpdate
from .query_builder import TenantFilter


class CRUDOwnership(CRUDBase[Ownership, OwnershipCreate, OwnershipUpdate]):
    """权属方CRUD操作类"""

    async def get(
        self,
        db: AsyncSession,
        id: Any,
        use_cache: bool = True,
        tenant_filter: TenantFilter | None = None,
    ) -> Ownership | None:
        """获取单个权属方"""
        ownership_obj = await super().get(
            db,
            id=id,
            use_cache=use_cache,
            tenant_filter=tenant_filter,
        )
        if ownership_obj:
            # 临时禁用项目关联数据查询
            setattr(ownership_obj, "project_relations_data", [])

        return ownership_obj

    async def get_by_name(self, db: AsyncSession, name: str) -> Ownership | None:
        """通过名称获取权属方"""
        stmt = select(Ownership).where(Ownership.name == name)
        return (await db.execute(stmt)).scalars().first()

    async def get_by_code(self, db: AsyncSession, code: str) -> Ownership | None:
        """通过编码获取权属方"""
        stmt = select(Ownership).where(Ownership.code == code)
        return (await db.execute(stmt)).scalars().first()

    async def get_multi_with_filters(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
        keyword: str | None = None,
        tenant_filter: TenantFilter | None = None,
    ) -> list[Ownership]:
        """获取多个权属方"""
        filters = {}

        # 构造过滤条件
        if is_active is not None:
            filters["is_active"] = is_active

        # 构建基础查询
        stmt = self.query_builder.build_query(
            filters=filters,
            search_query=keyword,
            search_fields=["name", "short_name", "code"],
            sort_by="created_at",
            sort_desc=True,
            skip=skip,
            limit=limit,
            tenant_filter=tenant_filter,
        )

        # 执行查询
        result = (await db.execute(stmt)).scalars().all()
        items = list(result)

        # 临时禁用项目关联数据查询
        for item in items:
            item.project_relations_data = []

        return items

    async def search(self, db: AsyncSession, search_params: Any) -> dict[str, Any]:
        """搜索权属方"""
        # 使用QueryBuilder通过get_multi_with_filters逻辑，或直接构建查询
        # 这里为了兼容性保持返回 dict 结构
        # 但 logic should use query_builder logic

        skip = (search_params.page - 1) * search_params.page_size
        limit = search_params.page_size

        filters = {}
        if search_params.is_active is not None:
            filters["is_active"] = search_params.is_active

        items, total = await self.get_multi_with_count(
            db,
            filters=filters,
            search=search_params.keyword,
            search_fields=["name", "short_name", "code"],
            order_by="created_at",
            order_desc=True,
            skip=skip,
            limit=limit,
            tenant_filter=getattr(search_params, "tenant_filter", None),
        )

        pages = (total + limit - 1) // limit

        return {
            "items": items,
            "total": total,
            "page": search_params.page,
            "page_size": limit,
            "pages": pages,
        }

    async def get_names_by_status_async(
        self, db: AsyncSession, data_status: str = "正常"
    ) -> list[str]:
        """获取指定状态的权属方名称列表（用于下拉选择）"""
        stmt = (
            select(Ownership.name)
            .where(
                Ownership.data_status == data_status,
                Ownership.name.is_not(None),
                Ownership.name != "",
            )
            .distinct()
            .order_by(Ownership.name.asc())
        )
        result = await db.execute(stmt)
        names = result.scalars().all()
        return [str(name) for name in names if name]

    async def get_by_ids_async(
        self, db: AsyncSession, ids: list[str]
    ) -> list[Ownership]:
        """批量获取权属方（按ID列表）"""
        if not ids:
            return []
        stmt = select(Ownership).where(Ownership.id.in_(ids))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_names_async(
        self, db: AsyncSession, names: list[str]
    ) -> list[Ownership]:
        """批量获取权属方（按名称列表）"""
        if not names:
            return []
        stmt = select(Ownership).where(Ownership.name.in_(names))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_codes_by_prefix_async(
        self, db: AsyncSession, prefix: str
    ) -> list[str]:
        """查询指定前缀的所有编码（用于去重检查）"""
        stmt = (
            select(Ownership.code)
            .where(Ownership.code.like(f"{prefix}%"))
            .order_by(Ownership.code.desc())
        )
        result = await db.execute(stmt)
        codes = result.scalars().all()
        return [str(code) for code in codes if code]

    async def get_statistics_async(self, db: AsyncSession) -> dict[str, Any]:
        """获取权属方统计信息（总数/活跃数/不活跃数）"""
        from sqlalchemy import case, func

        stmt = select(
            func.count(Ownership.id),
            func.sum(case((Ownership.is_active.is_(True), 1), else_=0)),
        )
        result = await db.execute(stmt)
        total_count, active_count = result.one()
        total = int(total_count or 0)
        active = int(active_count or 0)
        return {
            "total_count": total,
            "active_count": active,
            "inactive_count": total - active,
        }

    async def get_recent_created_async(
        self, db: AsyncSession, limit: int = 5
    ) -> list[Ownership]:
        """获取最近创建的权属方列表"""
        from sqlalchemy import desc

        stmt = select(Ownership).order_by(desc(Ownership.created_at)).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count_projects_async(self, db: AsyncSession, ownership_id: str) -> int:
        """统计权属方关联的项目数量"""
        from sqlalchemy import func

        from ..models.project_relations import ProjectOwnershipRelation

        stmt = select(func.count(ProjectOwnershipRelation.id)).where(
            ProjectOwnershipRelation.ownership_id == ownership_id,
            ProjectOwnershipRelation.is_active.is_(True),
        )
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    async def get_multi_for_select_async(
        self, db: AsyncSession, is_active: bool | None = None, limit: int = 1000
    ) -> list[Ownership]:
        """获取权属方下拉选项列表（带 LIMIT）"""
        stmt = select(Ownership).where(Ownership.data_status == "正常")
        if is_active is not None and hasattr(Ownership, "is_active"):
            stmt = stmt.where(Ownership.is_active == is_active)
        stmt = stmt.order_by(Ownership.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def delete_project_relations_async(
        self, db: AsyncSession, ownership_id: str
    ) -> None:
        """删除权属方的所有项目关联"""
        from sqlalchemy import delete

        from ..models.project_relations import ProjectOwnershipRelation

        stmt = delete(ProjectOwnershipRelation).where(
            ProjectOwnershipRelation.ownership_id == ownership_id
        )
        await db.execute(stmt)

    async def get_project_counts_by_ownerships_async(
        self, db: AsyncSession, ownership_ids: list[str]
    ) -> dict[str, int]:
        """按权属方分组统计项目数量（返回 dict）"""
        if not ownership_ids:
            return {}
        from sqlalchemy import func

        from ..models.project_relations import ProjectOwnershipRelation

        stmt = (
            select(
                ProjectOwnershipRelation.ownership_id,
                func.count(ProjectOwnershipRelation.id),
            )
            .where(
                ProjectOwnershipRelation.ownership_id.in_(ownership_ids),
                ProjectOwnershipRelation.is_active.is_(True),
            )
            .group_by(ProjectOwnershipRelation.ownership_id)
        )
        result = await db.execute(stmt)
        return {
            str(ownership_id): int(count or 0)
            for ownership_id, count in result.all()
            if ownership_id is not None
        }


# 创建CRUD实例
ownership = CRUDOwnership(Ownership)
