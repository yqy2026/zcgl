"""
增强的基础CRUD操作类 - 支持缓存、性能监控和错误处理
"""

import logging
import time
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import Session

from ..core.response_handler import ResponseHandler

ModelType = TypeVar("ModelType", bound=DeclarativeMeta)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

logger = logging.getLogger(__name__)


class CRUDBase[
    ModelType: DeclarativeMeta,
    CreateSchemaType: BaseModel,
    UpdateSchemaType: BaseModel,
]:
    """增强的基础CRUD操作类"""

    def __init__(self, model: type[ModelType]):
        """
        初始化CRUD对象

        Args:
            model: SQLAlchemy模型类
        """
        self.model = model
        self._cache = {}  # 简单内存缓存
        self._cache_timeout = 300  # 5分钟缓存超时

    def _get_cache_key(self, method: str, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [self.model.__tablename__, method]
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}:{v}")
        return "|".join(key_parts)

    def _get_from_cache(self, cache_key: str) -> Any | None:
        """从缓存获取数据"""
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_timeout:
                return data
            else:
                del self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, data: Any) -> None:
        """设置缓存数据"""
        self._cache[cache_key] = (data, time.time())
        # 限制缓存大小
        if len(self._cache) > 100:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

    def _handle_database_error(self, error: Exception, operation: str) -> Exception:
        """处理数据库错误"""
        logger.error(f"Database error during {operation}: {str(error)}", exc_info=True)
        if isinstance(error, SQLAlchemyError):
            return ResponseHandler.database_error(error, f"{operation}失败")
        return error

    def get(self, db: Session, id: Any, use_cache: bool = True) -> ModelType | None:
        """根据ID获取单个记录（支持缓存）"""
        cache_key = self._get_cache_key("get", id=id)

        if use_cache:
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                return cached_result

        try:
            result = db.query(self.model).filter(self.model.id == id).first()
            if use_cache and result is not None:
                self._set_cache(cache_key, result)
            return result
        except Exception as e:
            raise self._handle_database_error(e, "获取记录")

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, use_cache: bool = False
    ) -> list[ModelType]:
        """获取多个记录（支持缓存）"""
        cache_key = self._get_cache_key("get_multi", skip=skip, limit=limit)

        if use_cache and limit <= 50:  # 只对小结果集缓存
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                return cached_result

        try:
            query = db.query(self.model).offset(skip).limit(limit)
            result = query.all()

            if use_cache and limit <= 50:
                self._set_cache(cache_key, result)
            return result
        except Exception as e:
            raise self._handle_database_error(e, "获取记录列表")

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """创建新记录（支持事务回滚和错误处理）"""
        try:
            if hasattr(obj_in, "dict"):
                obj_in_data = obj_in.dict()
            else:
                obj_in_data = obj_in

            db_obj = self.model(**obj_in_data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            # 清除相关缓存
            self._clear_cache_pattern("get_multi")

            logger.info(
                f"Successfully created {self.model.__tablename__} record with id: {db_obj.id}"
            )
            return db_obj
        except Exception as e:
            db.rollback()
            raise self._handle_database_error(e, "创建记录")

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        """更新记录（支持事务回滚和缓存清理）"""
        try:
            obj_data = db_obj.__dict__
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.dict(exclude_unset=True)

            for field in obj_data:
                if field in update_data:
                    setattr(db_obj, field, update_data[field])

            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            # 清除相关缓存
            cache_key = self._get_cache_key("get", id=db_obj.id)
            if cache_key in self._cache:
                del self._cache[cache_key]
            self._clear_cache_pattern("get_multi")

            logger.info(
                f"Successfully updated {self.model.__tablename__} record with id: {db_obj.id}"
            )
            return db_obj
        except Exception as e:
            db.rollback()
            raise self._handle_database_error(e, "更新记录")

    def remove(self, db: Session, *, id: Any) -> ModelType:
        """删除记录（支持事务回滚和缓存清理）"""
        try:
            obj = db.query(self.model).get(id)
            if obj is None:
                raise ValueError(f"Record with id {id} not found")

            db.delete(obj)
            db.commit()

            # 清除相关缓存
            cache_key = self._get_cache_key("get", id=id)
            if cache_key in self._cache:
                del self._cache[cache_key]
            self._clear_cache_pattern("get_multi")

            logger.info(
                f"Successfully deleted {self.model.__tablename__} record with id: {id}"
            )
            return obj
        except ValueError:
            raise
        except Exception as e:
            db.rollback()
            raise self._handle_database_error(e, "删除记录")

    def count(self, db: Session, filters: dict[str, Any] | None = None) -> int:
        """获取记录总数（支持筛选条件）"""
        try:
            query = db.query(self.model)
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field) and value is not None:
                        query = query.filter(getattr(self.model, field) == value)
            return query.count()
        except Exception as e:
            raise self._handle_database_error(e, "统计记录数")

    def get_with_filters(
        self,
        db: Session,
        *,
        filters: dict[str, Any] | None = None,
        search: str | None = None,
        search_fields: list[str] | None = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        order_desc: bool = False,
    ) -> list[ModelType]:
        """高级查询方法（支持筛选、搜索、排序）"""
        try:
            query = db.query(self.model)

            # 应用筛选条件
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field) and value is not None:
                        if isinstance(value, list):
                            query = query.filter(getattr(self.model, field).in_(value))
                        else:
                            query = query.filter(getattr(self.model, field) == value)

            # 应用搜索条件
            if search and search_fields:
                search_conditions = []
                for field in search_fields:
                    if hasattr(self.model, field):
                        search_conditions.append(
                            getattr(self.model, field).contains(search)
                        )
                if search_conditions:
                    query = query.filter(or_(*search_conditions))

            # 应用排序
            if order_by and hasattr(self.model, order_by):
                order_field = getattr(self.model, order_by)
                if order_desc:
                    query = query.order_by(order_field.desc())
                else:
                    query = query.order_by(order_field)

            # 应用分页
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            raise self._handle_database_error(e, "高级查询")

    def bulk_create(
        self, db: Session, *, objects_in: list[CreateSchemaType]
    ) -> list[ModelType]:
        """批量创建记录"""
        try:
            db_objects = []
            for obj_in in objects_in:
                if hasattr(obj_in, "dict"):
                    obj_in_data = obj_in.dict()
                else:
                    obj_in_data = obj_in
                db_objects.append(self.model(**obj_in_data))

            db.add_all(db_objects)
            db.commit()

            # 刷新所有对象以获取数据库生成的值
            for obj in db_objects:
                db.refresh(obj)

            # 清除缓存
            self._clear_cache_pattern("get_multi")

            logger.info(
                f"Successfully bulk created {len(db_objects)} {self.model.__tablename__} records"
            )
            return db_objects
        except Exception as e:
            db.rollback()
            raise self._handle_database_error(e, "批量创建记录")

    def _clear_cache_pattern(self, pattern: str) -> None:
        """清除匹配模式的缓存"""
        keys_to_remove = []
        for key in self._cache.keys():
            if pattern in key:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

    def clear_cache(self) -> None:
        """清除所有缓存"""
        self._cache.clear()
        logger.info(f"Cache cleared for {self.model.__tablename__}")

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "model": self.model.__tablename__,
            "cache_size": len(self._cache),
            "cache_timeout": self._cache_timeout,
        }
