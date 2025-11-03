"""
枚举字段管理CRUD操作
"""

from typing import Any

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ..models.enum_field import (
    EnumFieldHistory,
    EnumFieldType,
    EnumFieldUsage,
    EnumFieldValue,
)
from ..schemas.enum_field import (
    EnumFieldTypeCreate,
    EnumFieldTypeUpdate,
    EnumFieldUsageCreate,
    EnumFieldUsageUpdate,
    EnumFieldValueCreate,
    EnumFieldValueUpdate,
)


class EnumFieldTypeCRUD:
    """枚举字段类型CRUD操作"""

    def __init__(self, db: Session):
        self.db = db

    def get(self, enum_type_id: str) -> EnumFieldType | None:
        """根据ID获取枚举类型"""
        enum_type = (
            self.db.query(EnumFieldType)
            .filter(
                and_(EnumFieldType.id == enum_type_id, not EnumFieldType.is_deleted)
            )
            .first()
        )

        if enum_type:
            # 加载关联的枚举值
            enum_values = (
                self.db.query(EnumFieldValue)
                .filter(
                    and_(
                        EnumFieldValue.enum_type_id == enum_type.id,
                        not EnumFieldValue.is_deleted,
                        EnumFieldValue.is_active,
                    )
                )
                .order_by(EnumFieldValue.sort_order.asc())
                .all()
            )
            enum_type.enum_values = enum_values

        return enum_type

    def get_by_code(self, code: str) -> EnumFieldType | None:
        """根据编码获取枚举类型"""
        return (
            self.db.query(EnumFieldType)
            .filter(and_(EnumFieldType.code == code, not EnumFieldType.is_deleted))
            .first()
        )

    def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        category: str | None = None,
        status: str | None = None,
        is_system: bool | None = None,
        keyword: str | None = None,
    ) -> list[EnumFieldType]:
        """获取枚举类型列表"""
        query = self.db.query(EnumFieldType).filter(not EnumFieldType.is_deleted)

        if category:
            query = query.filter(EnumFieldType.category == category)

        if status:
            query = query.filter(EnumFieldType.status == status)

        if is_system is not None:
            query = query.filter(EnumFieldType.is_system == is_system)

        if keyword:
            query = query.filter(
                or_(
                    EnumFieldType.name.contains(keyword),
                    EnumFieldType.code.contains(keyword),
                    EnumFieldType.description.contains(keyword),
                )
            )

        enum_types = (
            query.order_by(EnumFieldType.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        # 为每个枚举类型加载关联的枚举值
        for enum_type in enum_types:
            enum_values = (
                self.db.query(EnumFieldValue)
                .filter(
                    and_(
                        EnumFieldValue.enum_type_id == enum_type.id,
                        not EnumFieldValue.is_deleted,
                        EnumFieldValue.is_active,
                    )
                )
                .order_by(EnumFieldValue.sort_order.asc())
                .all()
            )
            enum_type.enum_values = enum_values

        return enum_types

    def create(self, obj_in: EnumFieldTypeCreate) -> EnumFieldType:
        """创建枚举类型"""
        db_obj = EnumFieldType(**obj_in.dict())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)

        # 记录历史
        self._create_history(
            enum_type_id=db_obj.id,
            action="create",
            target_type="type",
            new_value=f"创建枚举类型: {db_obj.name}",
            created_by=obj_in.created_by,
        )

        return db_obj

    def update(
        self, db_obj: EnumFieldType, obj_in: EnumFieldTypeUpdate
    ) -> EnumFieldType:
        """更新枚举类型"""
        update_data = obj_in.dict(exclude_unset=True)

        # 记录变更历史
        for field, new_value in update_data.items():
            if field == "updated_by":
                continue
            old_value = getattr(db_obj, field, None)
            if old_value != new_value:
                self._create_history(
                    enum_type_id=db_obj.id,
                    action="update",
                    target_type="type",
                    field_name=field,
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(new_value) if new_value is not None else None,
                    created_by=obj_in.updated_by,
                )

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, enum_type_id: str, deleted_by: str | None = None) -> bool:
        """软删除枚举类型"""
        db_obj = self.get(enum_type_id)
        if not db_obj:
            return False

        # 检查是否有关联的枚举值
        value_count = (
            self.db.query(EnumFieldValue)
            .filter(
                and_(
                    EnumFieldValue.enum_type_id == enum_type_id,
                    not EnumFieldValue.is_deleted,
                )
            )
            .count()
        )

        if value_count > 0:
            raise ValueError("无法删除包含枚举值的枚举类型")

        # 检查是否有使用记录
        usage_count = (
            self.db.query(EnumFieldUsage)
            .filter(
                and_(
                    EnumFieldUsage.enum_type_id == enum_type_id,
                    EnumFieldUsage.is_active,
                )
            )
            .count()
        )

        if usage_count > 0:
            raise ValueError("无法删除正在使用的枚举类型")

        db_obj.is_deleted = True
        db_obj.updated_by = deleted_by

        # 记录历史
        self._create_history(
            enum_type_id=enum_type_id,
            action="delete",
            target_type="type",
            new_value=f"删除枚举类型: {db_obj.name}",
            created_by=deleted_by,
        )

        self.db.commit()
        return True

    def get_categories(self) -> list[str]:
        """获取所有枚举类别"""
        result = (
            self.db.query(EnumFieldType.category)
            .filter(
                and_(
                    EnumFieldType.category.isnot(None),
                    not EnumFieldType.is_deleted,
                )
            )
            .distinct()
            .all()
        )
        return [r[0] for r in result if r[0]]

    def get_statistics(self) -> dict[str, Any]:
        """获取枚举类型统计信息"""
        total_types = (
            self.db.query(EnumFieldType).filter(not EnumFieldType.is_deleted).count()
        )
        active_types = (
            self.db.query(EnumFieldType)
            .filter(
                and_(not EnumFieldType.is_deleted, EnumFieldType.status == "active")
            )
            .count()
        )

        # 按类别统计
        categories = (
            self.db.query(
                EnumFieldType.category, func.count(EnumFieldType.id).label("count")
            )
            .filter(not EnumFieldType.is_deleted)
            .group_by(EnumFieldType.category)
            .all()
        )

        return {
            "total_types": total_types,
            "active_types": active_types,
            "categories": [
                {"name": cat[0] or "未分类", "count": cat[1]} for cat in categories
            ],
        }

    def _create_history(
        self,
        enum_type_id: str,
        action: str,
        target_type: str,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        created_by: str | None = None,
    ):
        """创建历史记录"""
        history = EnumFieldHistory(
            enum_type_id=enum_type_id,
            action=action,
            target_type=target_type,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            created_by=created_by,
        )
        self.db.add(history)


class EnumFieldValueCRUD:
    """枚举字段值CRUD操作"""

    def __init__(self, db: Session):
        self.db = db

    def get(self, enum_value_id: str) -> EnumFieldValue | None:
        """根据ID获取枚举值"""
        return (
            self.db.query(EnumFieldValue)
            .filter(
                and_(
                    EnumFieldValue.id == enum_value_id,
                    not EnumFieldValue.is_deleted,
                )
            )
            .first()
        )

    def get_by_type_and_value(
        self, enum_type_id: str, value: str
    ) -> EnumFieldValue | None:
        """根据类型ID和值获取枚举值"""
        return (
            self.db.query(EnumFieldValue)
            .filter(
                and_(
                    EnumFieldValue.enum_type_id == enum_type_id,
                    EnumFieldValue.value == value,
                    not EnumFieldValue.is_deleted,
                )
            )
            .first()
        )

    def get_by_type(
        self,
        enum_type_id: str,
        parent_id: str | None = None,
        is_active: bool | None = None,
    ) -> list[EnumFieldValue]:
        """根据类型ID获取枚举值列表"""
        query = self.db.query(EnumFieldValue).filter(
            and_(
                EnumFieldValue.enum_type_id == enum_type_id,
                not EnumFieldValue.is_deleted,
            )
        )

        if parent_id is not None:
            query = query.filter(EnumFieldValue.parent_id == parent_id)

        if is_active is not None:
            query = query.filter(EnumFieldValue.is_active == is_active)

        return query.order_by(
            EnumFieldValue.sort_order, EnumFieldValue.created_at
        ).all()

    def get_tree(self, enum_type_id: str) -> list[EnumFieldValue]:
        """获取枚举值树形结构"""

        def build_tree(parent_id: str | None = None) -> list[EnumFieldValue]:
            values = self.get_by_type(enum_type_id, parent_id=parent_id, is_active=True)
            for value in values:
                value.children = build_tree(value.id)
            return values

        return build_tree()

    def create(self, obj_in: EnumFieldValueCreate) -> EnumFieldValue:
        """创建枚举值"""
        # 计算层级和路径
        level = 1
        path = ""

        if obj_in.parent_id:
            parent = self.get(obj_in.parent_id)
            if parent:
                level = parent.level + 1
                path = f"{parent.path}/{parent.id}" if parent.path else parent.id

        db_obj = EnumFieldValue(**obj_in.dict())
        db_obj.level = level
        db_obj.path = path

        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)

        # 记录历史
        self._create_history(
            enum_type_id=db_obj.enum_type_id,
            enum_value_id=db_obj.id,
            action="create",
            target_type="value",
            new_value=f"创建枚举值: {db_obj.label}",
            created_by=obj_in.created_by,
        )

        return db_obj

    def update(
        self, db_obj: EnumFieldValue, obj_in: EnumFieldValueUpdate
    ) -> EnumFieldValue:
        """更新枚举值"""
        update_data = obj_in.dict(exclude_unset=True)

        # 记录变更历史
        for field, new_value in update_data.items():
            if field == "updated_by":
                continue
            old_value = getattr(db_obj, field, None)
            if old_value != new_value:
                self._create_history(
                    enum_type_id=db_obj.enum_type_id,
                    enum_value_id=db_obj.id,
                    action="update",
                    target_type="value",
                    field_name=field,
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(new_value) if new_value is not None else None,
                    created_by=obj_in.updated_by,
                )

        # 如果更新了父级，重新计算层级和路径
        if "parent_id" in update_data:
            level = 1
            path = ""

            if update_data["parent_id"]:
                parent = self.get(update_data["parent_id"])
                if parent:
                    level = parent.level + 1
                    path = f"{parent.path}/{parent.id}" if parent.path else parent.id

            update_data["level"] = level
            update_data["path"] = path

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, enum_value_id: str, deleted_by: str | None = None) -> bool:
        """软删除枚举值"""
        db_obj = self.get(enum_value_id)
        if not db_obj:
            return False

        # 检查是否有子枚举值
        children_count = (
            self.db.query(EnumFieldValue)
            .filter(
                and_(
                    EnumFieldValue.parent_id == enum_value_id,
                    not EnumFieldValue.is_deleted,
                )
            )
            .count()
        )

        if children_count > 0:
            raise ValueError("无法删除包含子枚举值的枚举值")

        db_obj.is_deleted = True
        db_obj.updated_by = deleted_by

        # 记录历史
        self._create_history(
            enum_type_id=db_obj.enum_type_id,
            enum_value_id=enum_value_id,
            action="delete",
            target_type="value",
            new_value=f"删除枚举值: {db_obj.label}",
            created_by=deleted_by,
        )

        self.db.commit()
        return True

    def batch_create(
        self,
        enum_type_id: str,
        values_data: list[dict[str, Any]],
        created_by: str | None = None,
    ) -> list[EnumFieldValue]:
        """批量创建枚举值"""
        created_values = []

        for value_data in values_data:
            value_data["enum_type_id"] = enum_type_id
            value_data["created_by"] = created_by
            obj_in = EnumFieldValueCreate(**value_data)
            db_obj = self.create(obj_in)
            created_values.append(db_obj)

        return created_values

    def _create_history(
        self,
        enum_type_id: str,
        enum_value_id: str,
        action: str,
        target_type: str,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        created_by: str | None = None,
    ):
        """创建历史记录"""
        history = EnumFieldHistory(
            enum_type_id=enum_type_id,
            enum_value_id=enum_value_id,
            action=action,
            target_type=target_type,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            created_by=created_by,
        )
        self.db.add(history)


class EnumFieldUsageCRUD:
    """枚举字段使用记录CRUD操作"""

    def __init__(self, db: Session):
        self.db = db

    def get(self, usage_id: str) -> EnumFieldUsage | None:
        """根据ID获取使用记录"""
        return (
            self.db.query(EnumFieldUsage).filter(EnumFieldUsage.id == usage_id).first()
        )

    def get_by_field(self, table_name: str, field_name: str) -> EnumFieldUsage | None:
        """根据表名和字段名获取使用记录"""
        return (
            self.db.query(EnumFieldUsage)
            .filter(
                and_(
                    EnumFieldUsage.table_name == table_name,
                    EnumFieldUsage.field_name == field_name,
                )
            )
            .first()
        )

    def get_by_enum_type(self, enum_type_id: str) -> list[EnumFieldUsage]:
        """根据枚举类型ID获取使用记录"""
        return (
            self.db.query(EnumFieldUsage)
            .filter(EnumFieldUsage.enum_type_id == enum_type_id)
            .all()
        )

    def create(self, obj_in: EnumFieldUsageCreate) -> EnumFieldUsage:
        """创建使用记录"""
        db_obj = EnumFieldUsage(**obj_in.dict())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(
        self, db_obj: EnumFieldUsage, obj_in: EnumFieldUsageUpdate
    ) -> EnumFieldUsage:
        """更新使用记录"""
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, usage_id: str) -> bool:
        """删除使用记录"""
        db_obj = self.get(usage_id)
        if not db_obj:
            return False

        self.db.delete(db_obj)
        self.db.commit()
        return True


def get_enum_field_type_crud(db: Session) -> EnumFieldTypeCRUD:
    """获取枚举字段类型CRUD实例"""
    return EnumFieldTypeCRUD(db)


def get_enum_field_value_crud(db: Session) -> EnumFieldValueCRUD:
    """获取枚举字段值CRUD实例"""
    return EnumFieldValueCRUD(db)


def get_enum_field_usage_crud(db: Session) -> EnumFieldUsageCRUD:
    """获取枚举字段使用记录CRUD实例"""
    return EnumFieldUsageCRUD(db)
