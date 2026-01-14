from typing import Any, Generic, TypeVar

"""
增强的基础CRUD操作类
提供统一的数据访问模式和通用功能
"""

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import asc, desc
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=DeclarativeMeta)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class FilterOperator:
    """查询过滤器操作符"""

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    LIKE = "like"
    ILIKE = "ilike"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class QueryFilter:
    """查询过滤器"""

    def __init__(
        self,
        field: str,
        operator: str,
        value: Any = None,
        model_class: type | None = None,
    ):
        self.field = field
        self.operator = operator
        self.value = value
        self.model_class = model_class

    def apply(self, query: Any, model_class: type[ModelType]) -> Any:
        """应用过滤器到查询"""
        actual_model = self.model_class or model_class

        field_attr = getattr(actual_model, self.field)

        if self.operator == FilterOperator.EQ:
            return query.filter(field_attr == self.value)
        elif self.operator == FilterOperator.NE:
            return query.filter(field_attr != self.value)
        elif self.operator == FilterOperator.GT:
            return query.filter(field_attr > self.value)
        elif self.operator == FilterOperator.GTE:
            return query.filter(field_attr >= self.value)
        elif self.operator == FilterOperator.LT:
            return query.filter(field_attr < self.value)
        elif self.operator == FilterOperator.LTE:
            return query.filter(field_attr <= self.value)
        elif self.operator == FilterOperator.IN:
            return query.filter(field_attr.in_(self.value))
        elif self.operator == FilterOperator.NOT_IN:
            return query.filter(field_attr.notin_(self.value))
        elif self.operator == FilterOperator.LIKE:
            return query.filter(field_attr.like(f"%{self.value}%"))
        elif self.operator == FilterOperator.ILIKE:
            return query.filter(field_attr.ilike(f"%{self.value}%"))
        elif self.operator == FilterOperator.IS_NULL:
            return query.filter(field_attr.is_(None))
        elif self.operator == FilterOperator.IS_NOT_NULL:
            return query.filter(field_attr.isnot(None))
        else:
            raise ValueError(f"Unsupported operator: {self.operator}")


class SortOrder:
    """排序顺序"""

    ASC = "asc"
    DESC = "desc"


class QuerySort:
    """查询排序"""

    def __init__(
        self, field: str, order: str = SortOrder.ASC, model_class: type | None = None
    ):
        self.field = field
        self.order = order
        self.model_class = model_class

    def apply(self, query: Any, model_class: type[ModelType]) -> Any:
        """应用排序到查询"""
        actual_model = self.model_class or model_class

        field_attr = getattr(actual_model, self.field)

        if self.order == SortOrder.ASC:
            return query.order_by(asc(field_attr))
        else:
            return query.order_by(desc(field_attr))


class EnhancedCRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """增强的基础CRUD操作类"""

    def __init__(self, model: type[ModelType]):
        """
        初始化CRUD对象

        Args:
            model: SQLAlchemy模型类
        """
        self.model = model

    # ==================== 基础CRUD操作 ====================

    def get(
        self,
        db: Session,
        id: Any,
        *,
        include_deleted: bool = False,
        eager_loads: list[str] | None = None,
    ) -> ModelType | None:
        """
        根据ID获取单个记录

        Args:
            db: 数据库会话
            id: 记录ID
            include_deleted: 是否包含已删除记录
            eager_loads: 预加载的字段列表

        Returns:
            模型实例或None
        """
        query = db.query(self.model)

        # 应用预加载
        if eager_loads:
            for field in eager_loads:
                if hasattr(self.model, field):
                    query = query.options(joinedload(getattr(self.model, field)))

        # 应用删除过滤器
        if not include_deleted and hasattr(self.model, "is_deleted"):
            query = query.filter(self.model.is_deleted.is_(False))  # type: ignore[attr-defined]

        result = query.filter(self.model.id == id).first()  # type: ignore[attr-defined]
        return result

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: list[QueryFilter] | None = None,
        sorts: list[QuerySort] | None = None,
        include_deleted: bool = False,
        eager_loads: list[str] | None = None,
    ) -> list[ModelType]:
        """
        获取多个记录

        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 限制记录数
            filters: 过滤器列表
            sorts: 排序列表
            include_deleted: 是否包含已删除记录
            eager_loads: 预加载的字段列表

        Returns:
            模型实例列表
        """
        query = self._build_query(
            db=db,
            filters=filters,
            sorts=sorts,
            include_deleted=include_deleted,
            eager_loads=eager_loads,
        )

        return query.offset(skip).limit(limit).all()  # type: ignore[no-any-return]

    def count(
        self,
        db: Session,
        *,
        filters: list[QueryFilter] | None = None,
        include_deleted: bool = False,
    ) -> int:
        """
        获取记录总数

        Args:
            db: 数据库会话
            filters: 过滤器列表
            include_deleted: 是否包含已删除记录

        Returns:
            记录总数
        """
        query = self._build_query(
            db=db, filters=filters, include_deleted=include_deleted
        )

        return query.count()  # type: ignore[no-any-return]

    def create(
        self,
        db: Session,
        *,
        obj_in: CreateSchemaType | dict[str, Any],
        created_by: str | None = None,
        **kwargs: Any,
    ) -> ModelType:
        """
        创建新记录

        Args:
            db: 数据库会话
            obj_in: 创建数据
            created_by: 创建者ID
            **kwargs: 额外字段

        Returns:
            创建的模型实例
        """
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            # obj_in is a CreateSchemaType (Pydantic model)
            obj_in_data = obj_in.model_dump(exclude_unset=True)

        # 添加创建者信息
        if created_by and hasattr(self.model, "created_by"):
            obj_in_data["created_by"] = created_by

        # 添加创建时间
        if hasattr(self.model, "created_at"):
            obj_in_data["created_at"] = datetime.now(UTC)

        # 添加额外字段
        obj_in_data.update(kwargs)

        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        # Safely extract ID for logging (handles SQLAlchemy Columns in tests)
        obj_id = getattr(db_obj, "id", None)
        try:
            # Try to get the actual value (not the Column object)
            if hasattr(obj_id, "__clause_element__"):
                # It's a SQLAlchemy Column, try to get the value from instance
                obj_id = getattr(db_obj, "_id", getattr(db_obj, "id", "N/A"))
        except Exception:
            obj_id = "N/A"

        logger.info(f"Created {self.model.__name__} with ID: {obj_id}")
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
        updated_by: str | None = None,
        **kwargs: Any,
    ) -> ModelType:
        """
        更新记录

        Args:
            db: 数据库会话
            db_obj: 要更新的数据库对象
            obj_in: 更新数据
            updated_by: 更新者ID
            **kwargs: 额外字段

        Returns:
            更新后的模型实例
        """
        update_data = (
            obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
        )

        # 添加更新者信息
        if updated_by and hasattr(self.model, "updated_by"):
            update_data["updated_by"] = updated_by

        # 添加更新时间
        if hasattr(self.model, "updated_at"):
            update_data["updated_at"] = datetime.now(UTC)

        # 添加额外字段
        update_data.update(kwargs)

        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        # Safely extract ID for logging (handles SQLAlchemy Columns in tests)
        obj_id = getattr(db_obj, "id", None)
        try:
            # Try to get the actual value (not the Column object)
            if hasattr(obj_id, "__clause_element__"):
                # It's a SQLAlchemy Column, try to get the value from instance
                obj_id = getattr(db_obj, "_id", getattr(db_obj, "id", "N/A"))
        except Exception:
            obj_id = "N/A"

        logger.info(f"Updated {self.model.__name__} with ID: {obj_id}")
        return db_obj

    def delete(
        self,
        db: Session,
        *,
        id: Any,
        deleted_by: str | None = None,
        soft_delete: bool = True,
    ) -> ModelType | None:
        """
        删除记录

        Args:
            db: 数据库会话
            id: 记录ID
            deleted_by: 删除者ID
            soft_delete: 是否软删除

        Returns:
            被删除的模型实例或None
        """
        obj = self.get(db, id=id, include_deleted=True)
        if not obj:
            return None

        if soft_delete and hasattr(obj, "is_deleted"):
            # 软删除
            obj.is_deleted = True
            if deleted_by and hasattr(obj, "deleted_by"):
                obj.deleted_by = deleted_by
            if hasattr(obj, "deleted_at"):
                obj.deleted_at = datetime.now(UTC)
        else:
            # 硬删除
            db.delete(obj)

        db.commit()
        logger.info(f"Deleted {self.model.__name__} with ID: {id}")
        return obj

    def restore(
        self, db: Session, *, id: Any, restored_by: str | None = None
    ) -> ModelType | None:
        """
        恢复软删除的记录

        Args:
            db: 数据库会话
            id: 记录ID
            restored_by: 恢复者ID

        Returns:
            恢复的模型实例或None
        """
        obj = self.get(db, id=id, include_deleted=True)
        if not obj:
            return None

        if hasattr(obj, "is_deleted"):
            obj.is_deleted = False
            if restored_by and hasattr(obj, "restored_by"):
                obj.restored_by = restored_by
            if hasattr(obj, "restored_at"):
                obj.restored_at = datetime.now(UTC)

        db.commit()
        db.refresh(obj)
        logger.info(f"Restored {self.model.__name__} with ID: {id}")
        return obj

    # ==================== 查询构建方法 ====================

    def _build_query(
        self,
        db: Session,
        *,
        filters: list[QueryFilter] | None = None,
        sorts: list[QuerySort] | None = None,
        include_deleted: bool = False,
        eager_loads: list[str] | None = None,
    ) -> Any:
        """
        构建查询

        Args:
            db: 数据库会话
            filters: 过滤器列表
            sorts: 排序列表
            include_deleted: 是否包含已删除记录
            eager_loads: 预加载的字段列表

        Returns:
            构建的查询对象
        """
        query = db.query(self.model)

        # 应用预加载
        if eager_loads:
            for field in eager_loads:
                if hasattr(self.model, field):
                    query = query.options(joinedload(getattr(self.model, field)))

        # 应用删除过滤器
        if not include_deleted and hasattr(self.model, "is_deleted"):
            query = query.filter(self.model.is_deleted.is_(False))  # type: ignore[attr-defined]

        # 应用过滤器
        if filters:
            for filter_obj in filters:
                query = filter_obj.apply(query, self.model)

        # 应用排序
        if sorts:
            for sort_obj in sorts:
                query = sort_obj.apply(query, self.model)

        return query

    # ==================== 便捷方法 ====================

    def get_by_field(
        self, db: Session, field_name: str, value: Any, *, include_deleted: bool = False
    ) -> ModelType | None:
        """
        根据字段值获取记录

        Args:
            db: 数据库会话
            field_name: 字段名
            value: 字段值
            include_deleted: 是否包含已删除记录

        Returns:
            模型实例或None
        """
        if not hasattr(self.model, field_name):
            raise ValueError(
                f"Model {self.model.__name__} does not have field {field_name}"
            )

        filter_obj = QueryFilter(field_name, FilterOperator.EQ, value)
        results = self.get_multi(
            db=db, filters=[filter_obj], limit=1, include_deleted=include_deleted
        )
        return results[0] if results else None

    def exists(
        self,
        db: Session,
        *,
        filters: list[QueryFilter] | None = None,
        include_deleted: bool = False,
    ) -> bool:
        """
        检查记录是否存在

        Args:
            db: 数据库会话
            filters: 过滤器列表
            include_deleted: 是否包含已删除记录

        Returns:
            是否存在记录
        """
        count = self.count(db=db, filters=filters, include_deleted=include_deleted)
        return count > 0

    def bulk_create(
        self,
        db: Session,
        *,
        objects_in: list[CreateSchemaType | dict[str, Any]],
        created_by: str | None = None,
    ) -> list[ModelType]:
        """
        批量创建记录

        Args:
            db: 数据库会话
            objects_in: 创建数据列表
            created_by: 创建者ID

        Returns:
            创建的模型实例列表
        """
        db_objects = []
        for obj_in in objects_in:
            if isinstance(obj_in, dict):
                obj_in_data = obj_in
            else:
                # obj_in is a CreateSchemaType (Pydantic model)
                obj_in_data = obj_in.model_dump(exclude_unset=True)

            if created_by and hasattr(self.model, "created_by"):
                obj_in_data["created_by"] = created_by
            if hasattr(self.model, "created_at"):
                obj_in_data["created_at"] = datetime.now(UTC)

            db_obj = self.model(**obj_in_data)
            db_objects.append(db_obj)

        db.add_all(db_objects)
        db.commit()

        for obj in db_objects:
            db.refresh(obj)

        logger.info(f"Bulk created {len(db_objects)} {self.model.__name__} records")
        return db_objects

    # ==================== 抽象方法 ====================

    @abstractmethod
    def get_resource_name(self) -> str:
        """获取资源名称，用于错误消息"""
        pass

    @abstractmethod
    def validate_create_data(self, db: Session, obj_in: CreateSchemaType) -> None:
        """验证创建数据"""
        pass

    @abstractmethod
    def validate_update_data(
        self, db: Session, db_obj: ModelType, obj_in: UpdateSchemaType
    ) -> None:
        """验证更新数据"""
        pass
