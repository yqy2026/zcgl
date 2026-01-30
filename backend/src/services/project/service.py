from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

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

    def create_project(
        self, db: Session, *, obj_in: ProjectCreate, created_by: str | None = None
    ) -> Project:
        """创建项目"""
        try:
            # 1. 生成项目编码 (如果未提供)
            if not obj_in.code:
                obj_in.code = self.generate_project_code(db, obj_in.name)

            # 2. 检查编码唯一性
            existing_project = project_crud.get_by_code(db, code=obj_in.code)
            if existing_project:
                raise DuplicateResourceError("项目", "code", obj_in.code)

            # 3. 创建项目
            project: Project = project_crud.create(
                db, obj_in=obj_in, created_by=created_by
            )
            return project

        except Exception as e:
            if isinstance(e, BaseBusinessError):
                raise
            raise InternalServerError("创建项目失败", original_error=e) from e

    def update_project(
        self,
        db: Session,
        *,
        project_id: str,
        obj_in: ProjectUpdate,
        updated_by: str | None = None,
    ) -> Project:
        """更新项目"""
        project: Project | None = project_crud.get(db, project_id)
        if not project:
            raise ResourceNotFoundError("项目", project_id)

        result: Project = project_crud.update(db, db_obj=project, obj_in=obj_in)
        return result

    def toggle_status(
        self, db: Session, *, project_id: str, updated_by: str | None = None
    ) -> Project:
        """切换项目状态"""
        project: Project | None = project_crud.get(db, project_id)
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
        project.updated_at = datetime.now()
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    def delete_project(self, db: Session, *, project_id: str) -> None:
        """删除项目"""
        count = project_crud.get_asset_count(db, project_id)
        if count > 0:
            raise OperationNotAllowedError(
                f"项目包含 {count} 个资产，无法删除",
                reason="project_has_assets",
            )

        # Use remove instead of delete
        project = project_crud.get(db, project_id)
        if project:
            db.delete(project)
            db.commit()

    def generate_project_code(self, db: Session, name: str | None = None) -> str:
        """生成项目编码"""
        # 1. 尝试从名称生成语义化编码
        if name:
            code = self._generate_name_code(name)
            if code and not project_crud.get_by_code(db, code):
                return code

        # 2. 生成顺序编码 PJ + YYMM + NNN
        prefix = f"PJ{datetime.now().strftime('%y%m')}"

        last_project = (
            db.query(Project)
            .filter(Project.code.like(f"{prefix}%"))
            .order_by(Project.code.desc())
            .first()
        )

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

    def search_projects(
        self, db: Session, search_params: ProjectSearchRequest
    ) -> dict[str, Any]:
        items, total = project_crud.search(db, search_params)
        return {
            "items": items,
            "total": total,
            "page": search_params.page,
            "page_size": search_params.page_size,
            "pages": (total + search_params.page_size - 1) // search_params.page_size,
        }

    def get_project_dropdown_options(
        self, db: Session, is_active: bool | None = True
    ) -> list[dict[str, Any]]:
        """获取项目下拉选项列表"""
        from ...models.asset import Project as AssetProject

        query = db.query(AssetProject)
        if is_active is not None:
            query = query.filter(AssetProject.is_active == is_active)

        projects = query.order_by(AssetProject.name.asc()).all()
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


project_service = ProjectService()
