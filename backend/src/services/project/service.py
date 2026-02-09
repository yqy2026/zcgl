from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from pinyin import get as get_pinyin
except ImportError:

    def get_pinyin(*args: Any, **kwargs: Any) -> Any:
        return None


from ...core.exception_handler import (
    BaseBusinessError,
    DuplicateResourceError,
    InternalServerError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from ...crud.project import project_crud
from ...models import Project
from ...schemas.project import ProjectCreate, ProjectSearchRequest, ProjectUpdate


class ProjectService:
    """项目服务层"""

    @staticmethod
    def _utcnow_naive() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    async def create_project(
        self,
        db: AsyncSession,
        *,
        obj_in: ProjectCreate,
        created_by: str | None = None,
    ) -> Project:
        """创建项目"""
        try:
            # 1. 生成项目编码 (如果未提供)
            if not obj_in.code:
                obj_in.code = await self.generate_project_code(db, obj_in.name)

            # 2. 检查编码唯一性
            existing_project = await project_crud.get_by_code(db, code=obj_in.code)
            if existing_project:
                raise DuplicateResourceError("项目", "code", obj_in.code)

            # 3. 创建项目
            project: Project = await project_crud.create(
                db, obj_in=obj_in, created_by=created_by
            )
            return project

        except Exception as e:
            if isinstance(e, BaseBusinessError):
                raise
            raise InternalServerError("创建项目失败", original_error=e) from e

    async def update_project(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        obj_in: ProjectUpdate,
        updated_by: str | None = None,
    ) -> Project:
        """更新项目"""
        project: Project | None = await project_crud.get(db, id=project_id)
        if not project:
            raise ResourceNotFoundError("项目", project_id)

        result: Project = await project_crud.update(db, db_obj=project, obj_in=obj_in)
        return result

    async def toggle_status(
        self, db: AsyncSession, *, project_id: str, updated_by: str | None = None
    ) -> Project:
        """切换项目状态"""
        project: Project | None = await project_crud.get(db, id=project_id)
        if not project:
            raise ResourceNotFoundError("项目", project_id)

        # Toggle logic: 规划中/进行中 <-> 暂停
        if project.project_status in ["规划中", "进行中"]:
            project.project_status = "暂停"
        elif project.project_status == "暂停":
            project.project_status = "进行中"  # Resume to active
        else:
            # Default to active if unknown
            project.project_status = "进行中"

        project.updated_by = updated_by
        project.updated_at = self._utcnow_naive()
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project

    async def delete_project(self, db: AsyncSession, *, project_id: str) -> None:
        """删除项目"""
        count = await project_crud.get_asset_count(db, project_id)
        if count > 0:
            raise OperationNotAllowedError(
                f"项目包含 {count} 个资产，无法删除",
                reason="project_has_assets",
            )

        # Use remove instead of delete
        project = await project_crud.get(db, id=project_id)
        if project:
            await project_crud.remove(db, id=project_id)

    async def generate_project_code(
        self, db: AsyncSession, name: str | None = None
    ) -> str:
        """生成项目编码"""
        # 1. 尝试从名称生成语义化编码
        if name:
            code = self._generate_name_code(name)
            if code and not await project_crud.get_by_code(db, code):
                return code

        # 2. 生成顺序编码 PJ + YYMM + NNN
        prefix = f"PJ{datetime.now().strftime('%y%m')}"

        stmt = (
            select(Project)
            .where(Project.code.like(f"{prefix}%"))
            .order_by(Project.code.desc())
            .limit(1)
        )
        last_project = (await db.execute(stmt)).scalars().first()

        if last_project:
            try:
                # PJ2501001 -> 001. Assume code format length 9 (PJ+4+3)
                # But actual format might vary. Just take last 3 if length fits
                if len(last_project.code) >= 3:
                    seq = int(last_project.code[-3:])
                    next_seq = seq + 1
                else:
                    next_seq = 1
            except ValueError:
                next_seq = 1
        else:
            next_seq = 1

        return f"{prefix}{next_seq:03d}"

    def _generate_name_code(self, name: str) -> str | None:
        """从名称生成语义化编码"""
        try:
            if get_pinyin:
                "".join(
                    [
                        c[0]
                        for c in get_pinyin(name, format="strip", delimiter=" ").split()
                    ]
                )
                # Need to match Schema validation: PJ + 2509 + 001 ?
                # Wait, schema validation says: 2字母前缀 + 4位年月 + 3位序号
                # If Validation is strict, then pinyin initials won't work unless they follow that format!
                # Schema: pattern = r"^[A-Z]{2}\d{7,8}$"
                # My pinyin logic produces "TEST" (e.g. 4 chars) which fails regex.
                # So I CANNOT use pinyin initials as is. logic must produce compatible code.
                # Actually I should disable pinyin name logic if schema enforces specific format.
                # I will fallback to standard generation logic inside `generate_project_code` and drop `_generate_name_code` logic
                # OR adapt it to use initials as prefix? PJ is hardcoded in example.
                # Let's just use the standard format PJ+YYMM+NNN to be safe and consistent.
                return None  # Disabled
            else:
                return None
        except Exception:
            return None

    async def search_projects(
        self, db: AsyncSession, search_params: ProjectSearchRequest
    ) -> dict[str, Any]:
        items, total = await project_crud.search(db, search_params)
        return {
            "items": items,
            "total": total,
            "page": search_params.page,
            "page_size": search_params.page_size,
            "pages": (total + search_params.page_size - 1) // search_params.page_size,
        }

    async def get_project_dropdown_options(
        self, db: AsyncSession, is_active: bool | None = True
    ) -> list[dict[str, Any]]:
        """获取项目下拉选项列表"""
        from ...models.project import Project as AssetProject

        stmt = select(AssetProject)
        if is_active is not None:
            stmt = stmt.where(AssetProject.is_active == is_active)

        projects = (
            (await db.execute(stmt.order_by(AssetProject.name.asc()))).scalars().all()
        )
        return [
            {
                "id": p.id,
                "name": p.name,
                "code": p.code,
                "short_name": p.short_name,
                "is_active": p.is_active,
            }
            for p in projects
        ]

    async def get_project_statistics(self, db: AsyncSession) -> dict[str, Any]:
        """获取项目统计信息。"""
        return await project_crud.get_statistics(db=db)

    async def get_project_by_id(
        self, db: AsyncSession, project_id: str
    ) -> Project | None:
        """根据 ID 获取项目。"""
        return await project_crud.get(db=db, id=project_id)


project_service = ProjectService()
