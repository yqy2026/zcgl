from typing import Any, cast

"""
枚举字段管理CRUD操作
"""

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ..core.exception_handler import OperationNotAllowedError
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


def _set_attr(obj: Any, attr: str, value: Any) -> None:
    """安全地设置 ORM 对象属性，避免 mypy 类型错误"""
    object.__setattr__(obj, attr, value)


class EnumFieldTypeCRUD:
    """枚举字段类型CRUD操作"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _type_query(self) -> Any:
        return self.db.query(EnumFieldType).filter(EnumFieldType.is_deleted.is_(False))

    def _value_query(
        self, *, enum_type_id: str, is_active: bool | None = None
    ) -> Any:
        query = self.db.query(EnumFieldValue).filter(
            and_(
                EnumFieldValue.enum_type_id == enum_type_id,
                EnumFieldValue.is_deleted.is_(False),
            )
        )
        if is_active is not None:
            query = query.filter(EnumFieldValue.is_active.is_(is_active))
        return query

    def _load_enum_values(self, enum_type: EnumFieldType) -> None:
        enum_type.enum_values = cast(
            list[EnumFieldValue],
            self._value_query(enum_type_id=str(enum_type.id), is_active=True)
            .order_by(EnumFieldValue.sort_order.asc())
            .all(),
        )

    def get(self, enum_type_id: str) -> EnumFieldType | None:
        """根据ID获取枚举类型"""
        enum_type = cast(
            EnumFieldType | None,
            self._type_query().filter(EnumFieldType.id == enum_type_id).first(),
        )

        if enum_type:
            # 加载关联的枚举值
            self._load_enum_values(enum_type)

        return enum_type

    def get_by_code(self, code: str) -> EnumFieldType | None:
        """根据编码获取枚举类型"""
        return cast(
            EnumFieldType | None,
            self._type_query().filter(EnumFieldType.code == code).first(),
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
        query = self._type_query()

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

        enum_types = cast(
            list[EnumFieldType],
            query.order_by(EnumFieldType.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all(),
        )

        # 为每个枚举类型加载关联的枚举值
        for enum_type in enum_types:
            self._load_enum_values(enum_type)

        return enum_types

    def create(self, obj_in: EnumFieldTypeCreate) -> EnumFieldType:
        """创建枚举类型"""
        db_obj = EnumFieldType(**obj_in.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)

        # 记录历史
        self._create_history(
            enum_type_id=str(db_obj.id),
            action="create",
            target_type="type",
            new_value=f"创建枚举类型: {db_obj.name}",
            created_by=obj_in.created_by,
        )
        self.db.flush()  # Flush history to make it visible in tests

        return db_obj

    def update(
        self, db_obj: EnumFieldType, obj_in: EnumFieldTypeUpdate
    ) -> EnumFieldType:
        """更新枚举类型"""
        update_data = obj_in.model_dump(exclude_unset=True)

        # 记录变更历史
        for field, new_value in update_data.items():
            if field == "updated_by":
                continue
            old_value = getattr(db_obj, field, None)
            if old_value != new_value:
                self._create_history(
                    enum_type_id=str(db_obj.id),
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
        value_count = self._value_query(enum_type_id=enum_type_id).count()

        if value_count > 0:
            raise OperationNotAllowedError("无法删除包含枚举值的枚举类型")

        # 检查是否有使用记录
        usage_count = (
            self.db.query(EnumFieldUsage)
            .filter(
                and_(
                    EnumFieldUsage.enum_type_id == enum_type_id,
                    EnumFieldUsage.is_active.is_(True),
                )
            )
            .count()
        )

        if usage_count > 0:
            raise OperationNotAllowedError("无法删除正在使用的枚举类型")

        # 安全设置属性
        _set_attr(db_obj, "is_deleted", True)
        _set_attr(db_obj, "updated_by", deleted_by)

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
                EnumFieldType.is_deleted.is_(False),
                EnumFieldType.category.isnot(None),
            )
            .distinct()
            .all()
        )
        return [r[0] for r in result if r[0]]

    def get_statistics(self) -> dict[str, Any]:
        """获取枚举类型统计信息"""
        total_types = self._type_query().count()
        active_types = (
            self._type_query().filter(EnumFieldType.status == "active").count()
        )

        # 按类别统计
        categories = (
            self.db.query(
                EnumFieldType.category, func.count(EnumFieldType.id).label("count")
            )
            .filter(EnumFieldType.is_deleted.is_(False))
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
    ) -> None:
        """创建历史记录"""
        history = EnumFieldHistory()
        _set_attr(history, "enum_type_id", enum_type_id)
        _set_attr(history, "action", action)
        _set_attr(history, "target_type", target_type)
        _set_attr(history, "field_name", field_name)
        _set_attr(history, "old_value", old_value)
        _set_attr(history, "new_value", new_value)
        _set_attr(history, "created_by", created_by)
        self.db.add(history)


class EnumFieldValueCRUD:
    """枚举字段值CRUD操作"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _value_query(self) -> Any:
        return self.db.query(EnumFieldValue).filter(
            EnumFieldValue.is_deleted.is_(False)
        )

    def count_all(self) -> int:
        return int(self._value_query().count())

    def count_active(self) -> int:
        return int(
            self._value_query().filter(EnumFieldValue.is_active.is_(True)).count()
        )

    def get(self, enum_value_id: str) -> EnumFieldValue | None:
        """根据ID获取枚举值"""
        return cast(
            EnumFieldValue | None,
            self._value_query().filter(EnumFieldValue.id == enum_value_id).first(),
        )

    def get_by_type_and_value(
        self, enum_type_id: str, value: str
    ) -> EnumFieldValue | None:
        """根据类型ID和值获取枚举值"""
        return cast(
            EnumFieldValue | None,
            self._value_query()
            .filter(
                and_(
                    EnumFieldValue.enum_type_id == enum_type_id,
                    EnumFieldValue.value == value,
                )
            )
            .first(),
        )

    def get_by_type(
        self,
        enum_type_id: str,
        parent_id: str | None = None,
        is_active: bool | None = None,
    ) -> list[EnumFieldValue]:
        """根据类型ID获取枚举值列表"""
        query = self._value_query().filter(EnumFieldValue.enum_type_id == enum_type_id)

        if parent_id is None:
            # Get top-level items (parent_id is NULL)
            query = query.filter(EnumFieldValue.parent_id.is_(None))
        else:
            query = query.filter(EnumFieldValue.parent_id == parent_id)

        if is_active is not None:
            query = query.filter(EnumFieldValue.is_active == is_active)

        return cast(
            list[EnumFieldValue],
            query.order_by(EnumFieldValue.sort_order, EnumFieldValue.created_at).all(),
        )

    def get_tree(self, enum_type_id: str) -> list[EnumFieldValue]:
        """获取枚举值树形结构"""

        def build_tree(parent_id: str | None = None) -> list[EnumFieldValue]:
            values = self.get_by_type(enum_type_id, parent_id=parent_id, is_active=True)
            for value in values:
                value.children = build_tree(parent_id=str(value.id))
            return values

        return build_tree()

    def create(self, obj_in: EnumFieldValueCreate) -> EnumFieldValue:
        """创建枚举值"""
        # 计算层级和路径
        level: int = 1
        path: str = ""

        if obj_in.parent_id:
            parent = self.get(obj_in.parent_id)
            if parent:
                parent_level = parent.level if parent.level is not None else 0
                level = int(parent_level) + 1
                parent_path = str(parent.path) if parent.path else ""
                parent_id = str(parent.id) if parent.id else ""
                path = f"{parent_path}/{parent_id}" if parent_path else parent_id

        db_obj = EnumFieldValue(**obj_in.model_dump())
        _set_attr(db_obj, "level", level)
        _set_attr(db_obj, "path", path)

        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)

        # 记录历史
        self._create_history(
            enum_type_id=str(db_obj.enum_type_id),
            enum_value_id=str(db_obj.id),
            action="create",
            target_type="value",
            new_value=f"创建枚举值: {db_obj.label}",
            created_by=obj_in.created_by,
        )
        self.db.flush()  # Flush history to make it visible in tests

        return db_obj

    def update(
        self, db_obj: EnumFieldValue, obj_in: EnumFieldValueUpdate
    ) -> EnumFieldValue:
        """更新枚举值"""
        update_data = obj_in.model_dump(exclude_unset=True)

        # 记录变更历史
        for field, new_value in update_data.items():
            if field == "updated_by":
                continue
            old_value = getattr(db_obj, field, None)
            if old_value != new_value:
                self._create_history(
                    enum_type_id=str(db_obj.enum_type_id),
                    enum_value_id=str(db_obj.id),
                    action="update",
                    target_type="value",
                    field_name=field,
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(new_value) if new_value is not None else None,
                    created_by=obj_in.updated_by,
                )

        # 如果更新了父级，重新计算层级和路径
        if "parent_id" in update_data:
            level: int = 1
            path: str = ""

            if update_data["parent_id"]:
                parent = self.get(update_data["parent_id"])
                if parent:
                    parent_level = parent.level if parent.level is not None else 0
                    level = int(parent_level) + 1
                    parent_path = str(parent.path) if parent.path else ""
                    parent_id = str(parent.id) if parent.id else ""
                    path = f"{parent_path}/{parent_id}" if parent_path else parent_id

            update_data["level"] = level
            update_data["path"] = path

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, enum_value_id: str, deleted_by: str | None = None) -> bool:
        """软删除枚举值"""
        db_obj = self._value_query().filter(EnumFieldValue.id == enum_value_id).first()
        if not db_obj:
            return False

        # 检查是否有子枚举值
        children_count = (
            self._value_query()
            .filter(EnumFieldValue.parent_id == enum_value_id)
            .count()
        )

        if children_count > 0:
            raise OperationNotAllowedError("无法删除包含子枚举值的枚举值")

        # 记录历史
        self._create_history(
            enum_type_id=str(db_obj.enum_type_id),
            enum_value_id=enum_value_id,
            action="delete",
            target_type="value",
            new_value=f"删除枚举值: {db_obj.label}",
            created_by=deleted_by,
        )

        _set_attr(db_obj, "is_deleted", True)
        _set_attr(db_obj, "updated_by", deleted_by)

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
    ) -> None:
        """创建历史记录"""
        history = EnumFieldHistory()
        _set_attr(history, "enum_type_id", enum_type_id)
        _set_attr(history, "enum_value_id", enum_value_id)
        _set_attr(history, "action", action)
        _set_attr(history, "target_type", target_type)
        _set_attr(history, "field_name", field_name)
        _set_attr(history, "old_value", old_value)
        _set_attr(history, "new_value", new_value)
        _set_attr(history, "created_by", created_by)
        self.db.add(history)


class EnumFieldUsageCRUD:
    """枚举字段使用记录CRUD操作"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _usage_query(self) -> Any:
        return self.db.query(EnumFieldUsage)

    def count_active(self) -> int:
        return int(
            self._usage_query().filter(EnumFieldUsage.is_active.is_(True)).count()
        )

    def get(self, usage_id: str) -> EnumFieldUsage | None:
        """根据ID获取使用记录"""
        return cast(
            EnumFieldUsage | None,
            self._usage_query().filter(EnumFieldUsage.id == usage_id).first(),
        )

    def get_by_field(self, table_name: str, field_name: str) -> EnumFieldUsage | None:
        """根据表名和字段名获取使用记录"""
        return cast(
            EnumFieldUsage | None,
            self._usage_query()
            .filter(
                and_(
                    EnumFieldUsage.table_name == table_name,
                    EnumFieldUsage.field_name == field_name,
                )
            )
            .first(),
        )

    def get_by_enum_type(self, enum_type_id: str) -> list[EnumFieldUsage]:
        """根据枚举类型ID获取使用记录"""
        return cast(
            list[EnumFieldUsage],
            self._usage_query()
            .filter(EnumFieldUsage.enum_type_id == enum_type_id)
            .all(),
        )

    def create(self, obj_in: EnumFieldUsageCreate) -> EnumFieldUsage:
        """创建使用记录"""
        db_obj = EnumFieldUsage(**obj_in.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(
        self, db_obj: EnumFieldUsage, obj_in: EnumFieldUsageUpdate
    ) -> EnumFieldUsage:
        """更新使用记录"""
        update_data = obj_in.model_dump(exclude_unset=True)
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


class EnumFieldHistoryCRUD:
    """枚举字段历史记录CRUD操作"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _history_query(self) -> Any:
        return self.db.query(EnumFieldHistory)

    def get_multi(
        self,
        *,
        enum_type_id: str | None = None,
        enum_value_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EnumFieldHistory]:
        query = self._history_query()
        if enum_type_id:
            query = query.filter(EnumFieldHistory.enum_type_id == enum_type_id)
        if enum_value_id:
            query = query.filter(EnumFieldHistory.enum_value_id == enum_value_id)
        return cast(
            list[EnumFieldHistory],
            query.order_by(EnumFieldHistory.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all(),
        )


def get_enum_field_type_crud(db: Session) -> EnumFieldTypeCRUD:
    """获取枚举字段类型CRUD实例"""
    return EnumFieldTypeCRUD(db)


def get_enum_field_value_crud(db: Session) -> EnumFieldValueCRUD:
    """获取枚举字段值CRUD实例"""
    return EnumFieldValueCRUD(db)


def get_enum_field_usage_crud(db: Session) -> EnumFieldUsageCRUD:
    """获取枚举字段使用记录CRUD实例"""
    return EnumFieldUsageCRUD(db)


def get_enum_field_history_crud(db: Session) -> EnumFieldHistoryCRUD:
    """获取枚举字段历史记录CRUD实例"""
    return EnumFieldHistoryCRUD(db)
