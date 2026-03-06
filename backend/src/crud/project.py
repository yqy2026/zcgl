from typing import Any

from sqlalchemy import Select, desc, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.auth import User
from ..models.party import Party, PartyType
from ..models.project import Project
from ..models.project_asset import ProjectAsset
from ..models.project_relations import ProjectOwnershipRelation
from ..schemas.project import ProjectCreate, ProjectSearchRequest, ProjectUpdate
from .base import CRUDBase
from .query_builder import PartyFilter


class CRUDProject(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    """项目管理CRUD操作类"""

    @staticmethod
    def _normalized_org_ids(party_filter: PartyFilter) -> list[str]:
        return [
            str(org_id).strip()
            for org_id in party_filter.party_ids
            if str(org_id).strip() != ""
        ]

    async def _resolve_creator_principals(
        self,
        db: AsyncSession,
        party_filter: PartyFilter,
    ) -> set[str]:
        org_ids = self._normalized_org_ids(party_filter)
        if not org_ids:
            return set()

        stmt = select(User.id, User.username).where(
            User.default_organization_id.in_(org_ids)  # DEPRECATED legacy org scope fallback
        )
        rows = (await db.execute(stmt)).all()
        principals: set[str] = set()
        for user_id, username in rows:
            if user_id is not None and str(user_id).strip() != "":
                principals.add(str(user_id).strip())
            if username is not None and str(username).strip() != "":
                principals.add(str(username).strip())
        return principals

    @staticmethod
    def _apply_creator_scope(
        stmt: Select[Any],
        principals: set[str],
    ) -> Select[Any]:
        if not principals:
            return stmt.where(false())
        return stmt.where(Project.created_by.in_(principals))

    @staticmethod
    def _supports_party_scope_columns() -> bool:
        return any(
            hasattr(Project, column_name)
            for column_name in (
                "owner_party_id",
                "manager_party_id",
                "party_id",
                "organization_id",
            )
        )

    async def _apply_project_party_filter(
        self,
        db: AsyncSession,
        stmt: Select[Any],
        party_filter: PartyFilter,
    ) -> Select[Any]:
        if self._supports_party_scope_columns():
            return self.query_builder.apply_party_filter(stmt, party_filter)

        principals = await self._resolve_creator_principals(db, party_filter)
        return self._apply_creator_scope(stmt, principals)

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: ProjectCreate | dict[str, Any],
        commit: bool = True,
        **kwargs: Any,
    ) -> Project:
        """创建项目（过滤关系字段）"""
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()

        # 移除关系字段（这些字段通过 SQLAlchemy relationship 管理）
        obj_in_data.pop("assets", None)
        obj_in_data.pop("ownership_relations", None)
        obj_in_data.pop("party_relations", None)
        obj_in_data.pop("ownership_ids", None)

        return await super().create(db, obj_in=obj_in_data, commit=commit, **kwargs)

    async def get_by_code(self, db: AsyncSession, code: str) -> Project | None:
        """通过编码获取项目"""
        stmt = select(Project).where(Project.project_code == code)
        return (await db.execute(stmt)).scalars().first()

    async def get_by_name(self, db: AsyncSession, name: str) -> Project | None:
        """通过名称获取项目"""
        stmt = select(Project).where(Project.project_name == name)
        return (await db.execute(stmt)).scalars().first()

    async def get_latest_by_code_prefix(
        self, db: AsyncSession, *, prefix: str
    ) -> Project | None:
        stmt = (
            select(Project)
            .where(Project.project_code.like(f"{prefix}%"))
            .order_by(Project.project_code.desc())
            .limit(1)
        )
        return (await db.execute(stmt)).scalars().first()

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Project,
        obj_in: ProjectUpdate | dict[str, Any],
        commit: bool = True,
    ) -> Project:
        """更新项目（过滤关系字段）"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # 移除关系字段
        update_data.pop("assets", None)
        update_data.pop("ownership_relations", None)
        update_data.pop("party_relations", None)
        update_data.pop("ownership_ids", None)

        return await super().update(
            db, db_obj=db_obj, obj_in=update_data, commit=commit
        )

    async def get(
        self,
        db: AsyncSession,
        id: Any,
        use_cache: bool = True,
        party_filter: PartyFilter | None = None,
    ) -> Project | None:
        """按 ID 获取项目（租户过滤回退到创建人范围）。"""
        if party_filter is None:
            return await super().get(
                db,
                id=id,
                use_cache=use_cache,
                party_filter=party_filter,
            )

        stmt = select(Project).where(Project.id == id)
        stmt = await self._apply_project_party_filter(db, stmt, party_filter)

        return (await db.execute(stmt)).scalars().first()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        keyword: str | None = None,
        party_filter: PartyFilter | None = None,
        **kwargs: Any,  # 扩展参数，与基类兼容
    ) -> list[Project]:
        """获取多个项目"""
        stmt = select(Project)

        if party_filter is not None:
            stmt = await self._apply_project_party_filter(db, stmt, party_filter)

        stmt = self._apply_project_filters(stmt, keyword=keyword, status=status)
        result = await db.execute(stmt.offset(skip).limit(limit))
        return list(result.scalars().all())

    def _apply_project_filters(
        self,
        stmt: Select[Any],
        *,
        keyword: str | None = None,
        status: str | None = None,
    ) -> Select[Any]:
        if keyword:
            like_keyword = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    Project.project_name.ilike(like_keyword),
                    Project.project_code.ilike(like_keyword),
                )
            )

        if status:
            stmt = stmt.where(Project.status == status)

        return stmt

    async def search(
        self,
        db: AsyncSession,
        search_params: ProjectSearchRequest,
        party_filter: PartyFilter | None = None,
    ) -> tuple[list[Project], int]:
        """搜索项目"""
        query = self._apply_project_filters(
            select(Project),
            keyword=search_params.keyword,
            status=search_params.status,
        )
        if party_filter is not None:
            query = await self._apply_project_party_filter(db, query, party_filter)

        if search_params.owner_party_id:
            owner_party_id = str(search_params.owner_party_id).strip()
            if owner_party_id != "":
                mapped_ownership_ids = select(Party.external_ref).where(
                    Party.id == owner_party_id,
                    Party.party_type == PartyType.LEGAL_ENTITY.value,
                    Party.external_ref.is_not(None),
                    Party.external_ref != "",
                )
                relation_project_ids = select(ProjectOwnershipRelation.project_id).where(
                    ProjectOwnershipRelation.is_active.is_(True),
                    or_(
                        ProjectOwnershipRelation.ownership_id == owner_party_id,
                        ProjectOwnershipRelation.ownership_id.in_(mapped_ownership_ids),
                    ),
                )
                query = query.where(Project.id.in_(relation_project_ids))
            else:
                query = query.where(false())

        # 计算总数
        total_stmt = select(func.count()).select_from(query.subquery())
        total = int((await db.execute(total_stmt)).scalar() or 0)

        # 排序 - Not in schema request, defaulted
        query = query.order_by(desc(Project.created_at))

        # 分页
        skip = (search_params.page - 1) * search_params.page_size
        result = await db.execute(query.offset(skip).limit(search_params.page_size))
        items = list(result.scalars().all())

        return items, total

    async def get_asset_count(self, db: AsyncSession, project_id: str) -> int:
        """获取项目关联的资产数量"""
        project_id_column = getattr(ProjectAsset, "project_id")
        stmt = select(func.count(ProjectAsset.id)).where(
            project_id_column == project_id,
            ProjectAsset.valid_to.is_(None),
        )
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    async def get_dropdown_options(self, db: AsyncSession) -> list[dict[str, Any]]:
        """获取下拉选项"""
        stmt = select(Project.id, Project.project_name).where(
            Project.data_status == "正常"
        )
        projects = (await db.execute(stmt)).all()
        return [{"value": p.id, "label": p.project_name} for p in projects]

    async def get_statistics(
        self,
        db: AsyncSession,
        party_filter: PartyFilter | None = None,
    ) -> dict[str, Any]:
        """获取统计信息"""
        total_query = select(Project.id)
        active_query = select(Project.id).where(Project.status == "active")

        if party_filter is not None:
            total_query = await self._apply_project_party_filter(
                db,
                total_query,
                party_filter,
            )
            active_query = await self._apply_project_party_filter(
                db,
                active_query,
                party_filter,
            )

        total_stmt = select(func.count()).select_from(total_query.subquery())
        active_stmt = select(func.count()).select_from(active_query.subquery())
        total = int((await db.execute(total_stmt)).scalar() or 0)
        active = int((await db.execute(active_stmt)).scalar() or 0)
        return {"total_projects": total, "active_projects": active}

    async def get_ids_by_filter_async(
        self, db: AsyncSession, ids: list[str]
    ) -> list[str]:
        """验证项目ID是否存在，返回有效的ID列表"""
        if not ids:
            return []
        stmt = select(Project.id).where(Project.id.in_(ids))
        result = await db.execute(stmt)
        return [str(project_id) for project_id in result.scalars().all()]

    # Removed: generate_project_code, _generate_name_code, _calculate_checksum -> Moved to Service
    # Removed: create (standard) -> Service calls base create
    # Removed: toggle_status -> Service logic


# 创建CRUD实例
project_crud = CRUDProject(Project)
