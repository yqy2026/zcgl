from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...core.exception_handler import (
    BusinessValidationError,
    DuplicateResourceError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from ...crud.ownership import ownership as ownership_crud
from ...models.asset import Asset, Ownership, Project, ProjectOwnershipRelation
from ...schemas.ownership import OwnershipCreate, OwnershipUpdate


class OwnershipService:
    """权属方服务层"""

    def generate_ownership_code(self, db: Session) -> str:
        """生成权属方编码

        编码规则：[前缀][年月][序号]
        示例：OW2501001（2025年1月第001个权属方）
        """
        # 固定前缀
        prefix = "OW"

        # 获取当前年月
        current_date = datetime.now()
        year_month = current_date.strftime("%y%m")  # 如：2501

        # 构建基础编码格式
        base_format = f"{prefix}{year_month}"

        # 查询所有已存在的编码（包括新格式和旧格式）
        existing_codes = (
            db.query(Ownership.code)
            .filter(Ownership.code.like(f"{prefix}%"))
            .order_by(Ownership.code.desc())
            .all()
        )

        # 找到新格式的最大序列号
        max_sequence = 0
        for existing_code in existing_codes:
            code_str = existing_code[0]
            # 新格式：OW2501001 (9位)
            if (
                len(code_str) == 9
                and code_str[:2] == prefix
                and code_str[2:6].isdigit()
            ):
                try:
                    sequence = int(code_str[6:])
                    if sequence > max_sequence:
                        max_sequence = sequence
                except ValueError:
                    continue

        # 生成下一个序列号
        next_sequence = max_sequence + 1

        # 尝试生成唯一编码（通常不需要循环，但为了安全保留逻辑）
        attempts = 0
        max_attempts = 100

        while attempts < max_attempts:
            sequence_str = f"{next_sequence:03d}"
            code = f"{base_format}{sequence_str}"

            # 检查编码是否已存在
            if not ownership_crud.get_by_code(db, code):
                return code

            next_sequence += 1
            attempts += 1

        # 兜底：使用时间戳
        return f"{base_format}{int(datetime.now().timestamp() % 1000):03d}"

    def create_ownership(self, db: Session, *, obj_in: OwnershipCreate) -> Ownership:
        """创建权属方"""
        # 检查名称是否已存在
        if ownership_crud.get_by_name(db, obj_in.name):
            raise DuplicateResourceError("权属方", "name", obj_in.name)

        # 自动生成编码
        code = self.generate_ownership_code(db)

        # 创建数据对象
        create_data = obj_in.model_dump()
        create_data["code"] = code

        db_obj = Ownership(**create_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_ownership(
        self, db: Session, *, db_obj: Ownership, obj_in: OwnershipUpdate
    ) -> Ownership:
        """更新权属方"""
        # 检查名称是否已被其他权属方使用
        if obj_in.name and obj_in.name != db_obj.name:
            existing = ownership_crud.get_by_name(db, obj_in.name)
            if existing and existing.id != db_obj.id:
                raise DuplicateResourceError("权属方", "name", obj_in.name)

        update_data = obj_in.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(UTC)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_statistics(self, db: Session) -> dict[str, Any]:
        """获取权属方统计信息"""
        total_count = db.query(Ownership).count()
        active_count = db.query(Ownership).filter(Ownership.is_active).count()
        inactive_count = total_count - active_count

        recent_created = (
            db.query(Ownership).order_by(desc(Ownership.created_at)).limit(5).all()
        )

        return {
            "total_count": total_count,
            "active_count": active_count,
            "inactive_count": inactive_count,
            "recent_created": recent_created,
        }

    def update_related_projects(
        self, db: Session, *, ownership_id: str, project_ids: list[str]
    ) -> None:
        """更新权属方关联的项目"""
        # 验证权属方是否存在
        ownership_obj = ownership_crud.get(db, id=ownership_id)
        if not ownership_obj:
            raise ResourceNotFoundError("权属方", ownership_id)

        # 验证项目是否存在
        valid_projects = db.query(Project).filter(Project.id.in_(project_ids)).all()
        valid_project_ids = [p.id for p in valid_projects]

        if len(valid_project_ids) != len(project_ids):
            invalid_ids = set(project_ids) - {str(p.id) for p in valid_projects}
            raise BusinessValidationError(
                f"以下项目ID不存在: {invalid_ids}",
                field_errors={"project_ids": [str(i) for i in invalid_ids]},
            )

        # 删除现有关联
        db.query(ProjectOwnershipRelation).filter(
            ProjectOwnershipRelation.ownership_id == ownership_id
        ).delete()

        # 创建新关联
        for project_id in project_ids:
            relation = ProjectOwnershipRelation()
            relation.project_id = project_id
            relation.ownership_id = ownership_id
            relation.is_active = True
            db.add(relation)

        db.commit()

    def get_project_count(self, db: Session, ownership_id: str) -> int:
        """获取权属方关联的项目数量"""
        return (
            db.query(ProjectOwnershipRelation)
            .filter(
                ProjectOwnershipRelation.ownership_id == ownership_id,
                ProjectOwnershipRelation.is_active,
            )
            .count()
        )

    def get_asset_count(self, db: Session, ownership_id: str) -> int:
        """获取权属方关联的资产数量"""
        return db.query(Asset).filter(Asset.ownership_id == ownership_id).count()

    def delete_ownership(self, db: Session, *, id: str) -> Ownership:
        """删除权属方"""
        db_obj = ownership_crud.get(db, id=id)
        if not db_obj:
            raise ResourceNotFoundError("权属方", id)

        # 检查是否有关联的资产
        asset_count = (
            db.query(Asset).filter(Asset.ownership_entity == db_obj.name).count()
        )

        if asset_count > 0:
            raise OperationNotAllowedError(
                f"该权属方还有 {asset_count} 个关联资产，无法删除",
                reason="ownership_has_assets",
            )

        ownership_crud.remove(db, id=id)
        return db_obj

    def toggle_status(
        self, db: Session, *, id: str, name: str | None = None, code: str | None = None
    ) -> Ownership:
        """切换权属方状态"""
        db_obj = ownership_crud.get(db, id=id)
        if not db_obj:
            raise ResourceNotFoundError("权属方", id)

        # Convert Column[str] to str using getattr
        obj_name: str | None = name or getattr(db_obj, "name", None)
        obj_code: str | None = code or getattr(db_obj, "code", None)
        obj_short_name: str | None = getattr(db_obj, "short_name", None)

        update_in = OwnershipUpdate(
            name=obj_name,
            code=obj_code,
            short_name=obj_short_name,
            is_active=not db_obj.is_active,
        )
        return self.update_ownership(db, db_obj=db_obj, obj_in=update_in)

    def get_ownership_dropdown_options(
        self, db: Session, is_active: bool | None = True
    ) -> list[dict[str, Any]]:
        """获取权属方下拉选项列表"""
        query = db.query(Ownership).filter(Ownership.data_status == "正常")
        if is_active is not None:
            # 使用is_active字段过滤（如果存在）或通过data_status推断
            if hasattr(Ownership, "is_active"):
                query = query.filter(Ownership.is_active == is_active)

        ownerships = query.order_by(Ownership.created_at.desc()).limit(1000).all()

        # 为下拉选项添加关联计数
        responses = []
        for item in ownerships:
            # 获取关联资产数量
            asset_count = self.get_asset_count(db, item.id)
            # 获取关联项目数量
            project_count = self.get_project_count(db, item.id)
            responses.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "code": item.code,
                    "short_name": item.short_name,
                    "is_active": item.is_active,
                    "data_status": item.data_status,
                    "asset_count": asset_count,
                    "project_count": project_count,
                }
            )
        return responses


ownership_service = OwnershipService()
