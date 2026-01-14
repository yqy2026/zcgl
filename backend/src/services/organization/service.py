from datetime import datetime
from typing import Any

from sqlalchemy import and_, not_
from sqlalchemy.orm import Session

from ...crud.organization import organization as organization_crud
from ...models.organization import Organization, OrganizationHistory
from ...schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationService:
    """组织架构服务层"""

    def create_organization(
        self, db: Session, *, obj_in: OrganizationCreate
    ) -> Organization:
        """创建组织"""
        # 计算层级和路径
        level = 1
        parent = None

        if obj_in.parent_id:
            parent = organization_crud.get(db, obj_in.parent_id)
            if not parent:
                raise ValueError(f"上级组织 {obj_in.parent_id} 不存在")
            level = parent.level + 1
            # path will be set after ID is generated or we need to generate ID first?
            # Organization model ID is UUID default.
            # We can let DB generate or generate here?
            # Existing CRUD used: db.add(db_obj); db.flush() -> got ID -> set path.

        # Create object
        db_obj = Organization(**obj_in.model_dump())
        object.__setattr__(db_obj, "level", level)
        # Temporary path until flush
        object.__setattr__(db_obj, "path", "/")

        db.add(db_obj)
        db.flush()  # Get ID

        # Now set path
        if parent:
            object.__setattr__(
                db_obj,
                "path",
                f"{parent.path}/{db_obj.id}"
                if parent.path
                else f"/{parent.id}/{db_obj.id}",
            )
        else:
            object.__setattr__(db_obj, "path", f"/{db_obj.id}")

        db.commit()
        db.refresh(db_obj)

        # 记录创建历史
        org_id_value: str = getattr(db_obj, "id")
        self._create_history(db, org_id_value, "create", created_by=obj_in.created_by)

        return db_obj

    def update_organization(
        self, db: Session, *, org_id: str, obj_in: OrganizationUpdate
    ) -> Organization:
        """更新组织"""
        db_obj: Organization | None = organization_crud.get(db, org_id)
        if not db_obj:
            raise ValueError(f"组织ID {org_id} 不存在")

        # 记录变更前的值
        old_values = {}
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, new_value in update_data.items():
            if field == "updated_by":
                continue
            old_value = getattr(db_obj, field)
            if old_value != new_value:
                old_values[field] = {"old": str(old_value), "new": str(new_value)}

        # 特殊处理上级组织变更
        if "parent_id" in update_data:
            new_parent_id = update_data["parent_id"]
            if new_parent_id != db_obj.parent_id:
                if new_parent_id:
                    # 检查是否会形成循环引用
                    if self._would_create_cycle(db, org_id, new_parent_id):
                        raise ValueError("不能将组织移动到其子组织下")

                    parent = organization_crud.get(db, new_parent_id)
                    if parent:
                        object.__setattr__(db_obj, "level", parent.level + 1)
                        object.__setattr__(
                            db_obj,
                            "path",
                            f"{parent.path}/{db_obj.id}"
                            if parent.path
                            else f"/{parent.id}/{db_obj.id}",
                        )
                    else:
                        raise ValueError(f"上级组织 {new_parent_id} 不存在")
                else:
                    object.__setattr__(db_obj, "level", 1)
                    object.__setattr__(db_obj, "path", f"/{db_obj.id}")

                # 更新所有子组织的层级和路径
                self._update_children_path(db, db_obj)

        # 应用更新
        for field, value in update_data.items():
            if field != "updated_by":
                setattr(db_obj, field, value)

        db_obj.updated_at = datetime.now()
        db.commit()
        db.refresh(db_obj)

        # 记录变更历史
        for field, values in old_values.items():
            org_id_value: str = getattr(db_obj, "id")
            self._create_history(
                db,
                org_id_value,
                "update",
                field,
                values["old"],
                values["new"],
                created_by=obj_in.updated_by,
            )

        return db_obj

    def delete_organization(
        self, db: Session, *, org_id: str, deleted_by: str | None = None
    ) -> bool:
        """软删除组织"""
        db_obj = organization_crud.get(db, org_id)
        if not db_obj:
            return False

        # 检查是否有子组织
        children = organization_crud.get_children(db, org_id)
        if children:
            raise ValueError("不能删除有子组织的组织，请先删除或移动子组织")

        db_obj.is_deleted = True
        db_obj.updated_at = datetime.now()
        db.commit()

        # 记录删除历史
        self._create_history(db, org_id, "delete", created_by=deleted_by)

        return True

    def get_statistics(self, db: Session) -> dict[str, Any]:
        """获取组织统计信息"""
        total = db.query(Organization).filter(not_(Organization.is_deleted)).count()
        active = total  # 由于删除了status字段，所有未删除的组织都视为活跃
        inactive = 0

        # 按层级统计
        level_stats = {}
        levels = (
            db.query(Organization.level)
            .filter(not_(Organization.is_deleted))
            .distinct()
            .all()
        )
        for level_row in levels:
            level = level_row[0]
            count = (
                db.query(Organization)
                .filter(
                    and_(not_(Organization.is_deleted), Organization.level == level)
                )
                .count()
            )
            level_stats[f"level_{level}"] = count

        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "by_type": {},
            "by_level": level_stats,
        }

    def get_history(
        self, db: Session, org_id: str, skip: int = 0, limit: int = 100
    ) -> list[OrganizationHistory]:
        """获取组织变更历史"""
        return (
            db.query(OrganizationHistory)
            .filter(OrganizationHistory.organization_id == org_id)
            .order_by(OrganizationHistory.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def _would_create_cycle(self, db: Session, org_id: str, new_parent_id: str) -> bool:
        """检查是否会创建循环引用"""
        current_id: str | None = new_parent_id
        while current_id:
            if current_id == org_id:
                return True
            parent = organization_crud.get(db, current_id)
            if parent:
                parent_id_value: str | None = getattr(parent, "parent_id")
                current_id = parent_id_value if parent_id_value else None
            else:
                current_id = None
        return False

    def _update_children_path(self, db: Session, parent_org: Organization) -> None:
        """更新子组织路径"""
        parent_org_id: str = getattr(parent_org, "id")
        parent_level: int = getattr(parent_org, "level")
        parent_path: str = getattr(parent_org, "path")
        children = organization_crud.get_children(db, parent_org_id)
        for child in children:
            setattr(child, "level", parent_level + 1)
            child_id: str = getattr(child, "id")
            setattr(child, "path", f"{parent_path}/{child_id}")
            db.commit()
            # 递归更新子组织的子组织
            self._update_children_path(db, child)

    def _create_history(
        self,
        db: Session,
        org_id: str,
        action: str,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        created_by: str | None = None,
    ) -> None:
        """创建历史记录"""
        history = OrganizationHistory(
            organization_id=org_id,
            action=action,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            created_by=created_by,
        )
        db.add(history)
        db.commit()


organization_service = OrganizationService()
