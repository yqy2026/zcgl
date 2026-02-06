from typing import Any

"""
枚举字段管理CRUD操作
"""

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

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

    def _type_query_async(self) -> Any:
        return select(EnumFieldType).where(EnumFieldType.is_deleted.is_(False))

    def _value_query_async(
        self, *, enum_type_id: str, is_active: bool | None = None
    ) -> Any:
        stmt = select(EnumFieldValue).where(
            and_(
                EnumFieldValue.enum_type_id == enum_type_id,
                EnumFieldValue.is_deleted.is_(False),
            )
        )
        if is_active is not None:
            stmt = stmt.where(EnumFieldValue.is_active.is_(is_active))
        return stmt

    async def _load_enum_values_async(
        self, db: AsyncSession, enum_type: EnumFieldType
    ) -> None:
        stmt = self._value_query_async(enum_type_id=str(enum_type.id), is_active=True)
        result = await db.execute(stmt.order_by(EnumFieldValue.sort_order.asc()))
        enum_values = list(result.scalars().all())
        set_committed_value(enum_type, "enum_values", enum_values)

    async def get_async(
        self, db: AsyncSession, enum_type_id: str
    ) -> EnumFieldType | None:
        stmt = self._type_query_async().where(EnumFieldType.id == enum_type_id)
        enum_type = (await db.execute(stmt)).scalars().first()
        if enum_type:
            await self._load_enum_values_async(db, enum_type)
        return enum_type

    async def get_by_code_async(
        self, db: AsyncSession, code: str
    ) -> EnumFieldType | None:
        stmt = self._type_query_async().where(EnumFieldType.code == code)
        return (await db.execute(stmt)).scalars().first()

    async def get_multi_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        category: str | None = None,
        status: str | None = None,
        is_system: bool | None = None,
        keyword: str | None = None,
    ) -> list[EnumFieldType]:
        stmt = self._type_query_async()

        if category:
            stmt = stmt.where(EnumFieldType.category == category)

        if status:
            stmt = stmt.where(EnumFieldType.status == status)

        if is_system is not None:
            stmt = stmt.where(EnumFieldType.is_system == is_system)

        if keyword:
            stmt = stmt.where(
                or_(
                    EnumFieldType.name.contains(keyword),
                    EnumFieldType.code.contains(keyword),
                    EnumFieldType.description.contains(keyword),
                )
            )

        result = await db.execute(
            stmt.order_by(EnumFieldType.created_at.desc()).offset(skip).limit(limit)
        )
        enum_types = list(result.scalars().all())

        for enum_type in enum_types:
            await self._load_enum_values_async(db, enum_type)

        return enum_types

    async def create_async(
        self, db: AsyncSession, obj_in: EnumFieldTypeCreate
    ) -> EnumFieldType:
        db_obj = EnumFieldType(**obj_in.model_dump())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await self._create_history_async(
            db,
            enum_type_id=str(db_obj.id),
            action="create",
            target_type="type",
            new_value=f"创建枚举类型: {db_obj.name}",
            created_by=obj_in.created_by,
        )
        await db.flush()
        return db_obj

    async def update_async(
        self, db: AsyncSession, db_obj: EnumFieldType, obj_in: EnumFieldTypeUpdate
    ) -> EnumFieldType:
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, new_value in update_data.items():
            if field == "updated_by":
                continue
            old_value = getattr(db_obj, field, None)
            if old_value != new_value:
                await self._create_history_async(
                    db,
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

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete_async(
        self, db: AsyncSession, enum_type_id: str, deleted_by: str | None = None
    ) -> bool:
        db_obj = await self.get_async(db, enum_type_id)
        if not db_obj:
            return False

        value_count_stmt = select(func.count()).select_from(EnumFieldValue).where(
            and_(
                EnumFieldValue.enum_type_id == enum_type_id,
                EnumFieldValue.is_deleted.is_(False),
            )
        )
        value_count = int((await db.execute(value_count_stmt)).scalar() or 0)

        if value_count > 0:
            raise OperationNotAllowedError("无法删除包含枚举值的枚举类型")

        usage_count_stmt = select(func.count()).select_from(EnumFieldUsage).where(
            and_(
                EnumFieldUsage.enum_type_id == enum_type_id,
                EnumFieldUsage.is_active.is_(True),
            )
        )
        usage_count = int((await db.execute(usage_count_stmt)).scalar() or 0)

        if usage_count > 0:
            raise OperationNotAllowedError("无法删除正在使用的枚举类型")

        _set_attr(db_obj, "is_deleted", True)
        _set_attr(db_obj, "updated_by", deleted_by)

        await self._create_history_async(
            db,
            enum_type_id=enum_type_id,
            action="delete",
            target_type="type",
            new_value=f"删除枚举类型: {db_obj.name}",
            created_by=deleted_by,
        )

        await db.commit()
        return True

    async def get_categories_async(self, db: AsyncSession) -> list[str]:
        stmt = (
            select(EnumFieldType.category)
            .where(
                EnumFieldType.is_deleted.is_(False),
                EnumFieldType.category.isnot(None),
            )
            .distinct()
        )
        result = await db.execute(stmt)
        return [r[0] for r in result.all() if r[0]]

    async def get_statistics_async(self, db: AsyncSession) -> dict[str, Any]:
        total_stmt = select(func.count()).select_from(EnumFieldType).where(
            EnumFieldType.is_deleted.is_(False)
        )
        total_types = int((await db.execute(total_stmt)).scalar() or 0)
        active_stmt = select(func.count()).select_from(EnumFieldType).where(
            EnumFieldType.is_deleted.is_(False),
            EnumFieldType.status == "active",
        )
        active_types = int((await db.execute(active_stmt)).scalar() or 0)

        categories_stmt = (
            select(EnumFieldType.category, func.count(EnumFieldType.id).label("count"))
            .where(EnumFieldType.is_deleted.is_(False))
            .group_by(EnumFieldType.category)
        )
        categories = (await db.execute(categories_stmt)).all()

        return {
            "total_types": total_types,
            "active_types": active_types,
            "categories": [
                {"name": cat[0] or "未分类", "count": cat[1]} for cat in categories
            ],
        }

    async def _create_history_async(
        self,
        db: AsyncSession,
        *,
        enum_type_id: str,
        action: str,
        target_type: str,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        created_by: str | None = None,
    ) -> None:
        history = EnumFieldHistory()
        _set_attr(history, "enum_type_id", enum_type_id)
        _set_attr(history, "action", action)
        _set_attr(history, "target_type", target_type)
        _set_attr(history, "field_name", field_name)
        _set_attr(history, "old_value", old_value)
        _set_attr(history, "new_value", new_value)
        _set_attr(history, "created_by", created_by)
        db.add(history)


class EnumFieldValueCRUD:
    """枚举字段值CRUD操作"""

    def _value_query_async(self) -> Any:
        return select(EnumFieldValue).where(EnumFieldValue.is_deleted.is_(False))

    async def count_all_async(self, db: AsyncSession) -> int:
        stmt = select(func.count()).select_from(EnumFieldValue).where(
            EnumFieldValue.is_deleted.is_(False)
        )
        return int((await db.execute(stmt)).scalar() or 0)

    async def count_active_async(self, db: AsyncSession) -> int:
        stmt = select(func.count()).select_from(EnumFieldValue).where(
            EnumFieldValue.is_deleted.is_(False),
            EnumFieldValue.is_active.is_(True),
        )
        return int((await db.execute(stmt)).scalar() or 0)

    async def get_async(
        self, db: AsyncSession, enum_value_id: str
    ) -> EnumFieldValue | None:
        stmt = self._value_query_async().where(EnumFieldValue.id == enum_value_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_by_type_and_value_async(
        self, db: AsyncSession, enum_type_id: str, value: str
    ) -> EnumFieldValue | None:
        stmt = self._value_query_async().where(
            and_(
                EnumFieldValue.enum_type_id == enum_type_id,
                EnumFieldValue.value == value,
            )
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_by_type_async(
        self,
        db: AsyncSession,
        enum_type_id: str,
        parent_id: str | None = None,
        is_active: bool | None = None,
    ) -> list[EnumFieldValue]:
        stmt = self._value_query_async().where(
            EnumFieldValue.enum_type_id == enum_type_id
        )

        if parent_id is None:
            stmt = stmt.where(EnumFieldValue.parent_id.is_(None))
        else:
            stmt = stmt.where(EnumFieldValue.parent_id == parent_id)

        if is_active is not None:
            stmt = stmt.where(EnumFieldValue.is_active.is_(is_active))

        result = await db.execute(
            stmt.order_by(EnumFieldValue.sort_order, EnumFieldValue.created_at)
        )
        return list(result.scalars().all())

    async def get_tree_async(self, db: AsyncSession, enum_type_id: str) -> list[Any]:
        async def build_tree(parent_id: str | None = None) -> list[EnumFieldValue]:
            values = await self.get_by_type_async(
                db, enum_type_id, parent_id=parent_id, is_active=True
            )
            for value in values:
                value.children = await build_tree(parent_id=str(value.id))
            return values

        return await build_tree()

    async def create_async(
        self, db: AsyncSession, obj_in: EnumFieldValueCreate
    ) -> EnumFieldValue:
        level: int = 1
        path: str = ""

        if obj_in.parent_id:
            parent = await self.get_async(db, obj_in.parent_id)
            if parent:
                parent_level = parent.level if parent.level is not None else 0
                level = int(parent_level) + 1
                parent_path = str(parent.path) if parent.path else ""
                parent_id = str(parent.id) if parent.id else ""
                path = f"{parent_path}/{parent_id}" if parent_path else parent_id

        db_obj = EnumFieldValue(**obj_in.model_dump())
        _set_attr(db_obj, "level", level)
        _set_attr(db_obj, "path", path)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        await self._create_history_async(
            db,
            enum_type_id=str(db_obj.enum_type_id),
            enum_value_id=str(db_obj.id),
            action="create",
            target_type="value",
            new_value=f"创建枚举值: {db_obj.label}",
            created_by=obj_in.created_by,
        )
        await db.flush()

        return db_obj

    async def update_async(
        self, db: AsyncSession, db_obj: EnumFieldValue, obj_in: EnumFieldValueUpdate
    ) -> EnumFieldValue:
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, new_value in update_data.items():
            if field == "updated_by":
                continue
            old_value = getattr(db_obj, field, None)
            if old_value != new_value:
                await self._create_history_async(
                    db,
                    enum_type_id=str(db_obj.enum_type_id),
                    enum_value_id=str(db_obj.id),
                    action="update",
                    target_type="value",
                    field_name=field,
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(new_value) if new_value is not None else None,
                    created_by=obj_in.updated_by,
                )

        if "parent_id" in update_data:
            level: int = 1
            path: str = ""

            if update_data["parent_id"]:
                parent = await self.get_async(db, update_data["parent_id"])
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

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete_async(
        self, db: AsyncSession, enum_value_id: str, deleted_by: str | None = None
    ) -> bool:
        db_obj = await self.get_async(db, enum_value_id)
        if not db_obj:
            return False

        children_count_stmt = select(func.count()).select_from(EnumFieldValue).where(
            and_(
                EnumFieldValue.parent_id == enum_value_id,
                EnumFieldValue.is_deleted.is_(False),
            )
        )
        children_count = int((await db.execute(children_count_stmt)).scalar() or 0)

        if children_count > 0:
            raise OperationNotAllowedError("无法删除包含子枚举值的枚举值")

        await self._create_history_async(
            db,
            enum_type_id=str(db_obj.enum_type_id),
            enum_value_id=enum_value_id,
            action="delete",
            target_type="value",
            new_value=f"删除枚举值: {db_obj.label}",
            created_by=deleted_by,
        )

        _set_attr(db_obj, "is_deleted", True)
        _set_attr(db_obj, "updated_by", deleted_by)

        await db.commit()
        return True

    async def batch_create_async(
        self,
        db: AsyncSession,
        enum_type_id: str,
        values_data: list[dict[str, Any]],
        created_by: str | None = None,
    ) -> list[EnumFieldValue]:
        created_values = []

        for value_data in values_data:
            value_data["enum_type_id"] = enum_type_id
            value_data["created_by"] = created_by
            obj_in = EnumFieldValueCreate(**value_data)
            db_obj = await self.create_async(db, obj_in)
            created_values.append(db_obj)

        return created_values

    async def _create_history_async(
        self,
        db: AsyncSession,
        *,
        enum_type_id: str,
        enum_value_id: str,
        action: str,
        target_type: str,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        created_by: str | None = None,
    ) -> None:
        history = EnumFieldHistory()
        _set_attr(history, "enum_type_id", enum_type_id)
        _set_attr(history, "enum_value_id", enum_value_id)
        _set_attr(history, "action", action)
        _set_attr(history, "target_type", target_type)
        _set_attr(history, "field_name", field_name)
        _set_attr(history, "old_value", old_value)
        _set_attr(history, "new_value", new_value)
        _set_attr(history, "created_by", created_by)
        db.add(history)


class EnumFieldUsageCRUD:
    """枚举字段使用记录CRUD操作"""

    def _usage_query_async(self) -> Any:
        return select(EnumFieldUsage)

    async def count_active_async(self, db: AsyncSession) -> int:
        stmt = select(func.count()).select_from(EnumFieldUsage).where(
            EnumFieldUsage.is_active.is_(True)
        )
        return int((await db.execute(stmt)).scalar() or 0)

    async def get_async(
        self, db: AsyncSession, usage_id: str
    ) -> EnumFieldUsage | None:
        stmt = self._usage_query_async().where(EnumFieldUsage.id == usage_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_by_field_async(
        self, db: AsyncSession, table_name: str, field_name: str
    ) -> EnumFieldUsage | None:
        stmt = self._usage_query_async().where(
            and_(
                EnumFieldUsage.table_name == table_name,
                EnumFieldUsage.field_name == field_name,
            )
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_by_enum_type_async(
        self, db: AsyncSession, enum_type_id: str
    ) -> list[EnumFieldUsage]:
        stmt = self._usage_query_async().where(EnumFieldUsage.enum_type_id == enum_type_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_async(
        self, db: AsyncSession, obj_in: EnumFieldUsageCreate
    ) -> EnumFieldUsage:
        db_obj = EnumFieldUsage(**obj_in.model_dump())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_async(
        self, db: AsyncSession, db_obj: EnumFieldUsage, obj_in: EnumFieldUsageUpdate
    ) -> EnumFieldUsage:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete_async(self, db: AsyncSession, usage_id: str) -> bool:
        db_obj = await self.get_async(db, usage_id)
        if not db_obj:
            return False

        await db.delete(db_obj)
        await db.commit()
        return True


class EnumFieldHistoryCRUD:
    """枚举字段历史记录CRUD操作"""

    def _history_query_async(self) -> Any:
        return select(EnumFieldHistory)

    async def get_multi_async(
        self,
        db: AsyncSession,
        *,
        enum_type_id: str | None = None,
        enum_value_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EnumFieldHistory]:
        stmt = self._history_query_async()
        if enum_type_id:
            stmt = stmt.where(EnumFieldHistory.enum_type_id == enum_type_id)
        if enum_value_id:
            stmt = stmt.where(EnumFieldHistory.enum_value_id == enum_value_id)
        result = await db.execute(
            stmt.order_by(EnumFieldHistory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


def get_enum_field_type_crud(db: AsyncSession) -> EnumFieldTypeCRUD:
    """获取枚举字段类型CRUD实例"""
    _ = db
    return EnumFieldTypeCRUD()


def get_enum_field_value_crud(db: AsyncSession) -> EnumFieldValueCRUD:
    """获取枚举字段值CRUD实例"""
    _ = db
    return EnumFieldValueCRUD()


def get_enum_field_usage_crud(db: AsyncSession) -> EnumFieldUsageCRUD:
    """获取枚举字段使用记录CRUD实例"""
    _ = db
    return EnumFieldUsageCRUD()


def get_enum_field_history_crud(db: AsyncSession) -> EnumFieldHistoryCRUD:
    """获取枚举字段历史记录CRUD实例"""
    _ = db
    return EnumFieldHistoryCRUD()
