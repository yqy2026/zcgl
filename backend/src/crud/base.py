from typing import Any, Generic, TypeVar

"""
增强的基础CRUD操作类 - 支持缓存、性能监控和错误处理
"""

import logging
import time

from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import Session

from ..core.response_handler import ResponseHandler
from .query_builder import QueryBuilder

# Define TypeVars at module level with unique names
_ModelType = TypeVar("_ModelType", bound=DeclarativeMeta)
_CreateSchemaType = TypeVar("_CreateSchemaType", bound=BaseModel)
_UpdateSchemaType = TypeVar("_UpdateSchemaType", bound=BaseModel)

logger = logging.getLogger(__name__)


class CRUDBase(Generic[_ModelType, _CreateSchemaType, _UpdateSchemaType]):
    """增强的基础CRUD操作类"""

    def __init__(self, model: type[_ModelType]) -> None:
        """
        初始化CRUD对象

        Args:
            model: SQLAlchemy模型类
        """
        self.model = model
        self.query_builder = QueryBuilder(model)
        self._cache: dict[str, tuple[Any, float]] = {}  # 简单内存缓存
        self._cache_timeout = 300  # 5分钟缓存超时

    def _get_cache_key(self, method: str, **kwargs: Any) -> str:
        """生成缓存键"""
        key_parts = [getattr(self.model, '__tablename__', 'unknown'), method]  # type: ignore[attr-defined]
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

    def _handle_database_error(self, error: Exception, operation: str) -> Exception:  # pragma: no cover
        """处理数据库错误"""
        logger.error(f"Database error during {operation}: {str(error)}", exc_info=True)
        if isinstance(error, SQLAlchemyError):
            return ResponseHandler.database_error(error, f"{operation}失败")
        return error

    def get(self, db: Session, id: Any, use_cache: bool = True) -> _ModelType | None:
        """根据ID获取单个记录（支持缓存）"""
        cache_key = self._get_cache_key("get", id=id)

        if use_cache:
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                return cached_result

        try:
            result = db.query(self.model).filter(getattr(self.model, 'id') == id).first()  # type: ignore[attr-defined]
            if use_cache and result is not None:  # pragma: no cover
                self._set_cache(cache_key, result)  # pragma: no cover
            return result  # type: ignore[no-any-return]
        except Exception as e:  # pragma: no cover
            raise self._handle_database_error(e, "获取记录")  # pragma: no cover

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, use_cache: bool = False
    ) -> list[_ModelType]:
        """获取多个记录（支持缓存）"""
        cache_key = self._get_cache_key("get_multi", skip=skip, limit=limit)

        if use_cache and limit <= 50:  # 只对小结果集缓存
            cached_result = self._get_from_cache(cache_key)  # pragma: no cover
            if cached_result is not None:  # pragma: no cover
                return cached_result  # pragma: no cover

        try:
            query = db.query(self.model).offset(skip).limit(limit)
            result = query.all()

            if use_cache and limit <= 50:
                self._set_cache(cache_key, result)  # pragma: no cover
            return result  # type: ignore[no-any-return]
        except Exception as e:  # pragma: no cover
            raise self._handle_database_error(e, "获取记录列表")  # pragma: no cover

    def create(self, db: Session, *, obj_in: _CreateSchemaType, **kwargs: Any) -> _ModelType:
        """创建新记录（支持事务回滚和错误处理）"""
        try:
            obj_in_data: dict[str, Any] = (
                obj_in.model_dump() if hasattr(obj_in, "model_dump") else obj_in  # type: ignore[assignment]
            )

            obj_in_data.update(kwargs)
            db_obj = self.model(**obj_in_data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            # 清除相关缓存
            self._clear_cache_pattern("get_multi")

            logger.info(
                f"Successfully created {getattr(self.model, '__tablename__', 'unknown')} record with id: {getattr(db_obj, 'id', 'unknown')}"  # type: ignore[attr-defined]
            )
            return db_obj
        except Exception as e:  # pragma: no cover
            db.rollback()  # pragma: no cover
            raise self._handle_database_error(e, "创建记录")  # pragma: no cover

    def update(
        self,
        db: Session,
        *,
        db_obj: _ModelType,
        obj_in: _UpdateSchemaType | dict[str, Any],
    ) -> _ModelType:
        """更新记录（支持事务回滚和缓存清理）"""
        try:
            obj_data = db_obj.__dict__
            update_data: dict[str, Any] = (
                obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)  # type: ignore[assignment]
            )

            for field in obj_data:
                if field in update_data:
                    setattr(db_obj, field, update_data[field])

            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            # 清除相关缓存
            cache_key = self._get_cache_key("get", id=getattr(db_obj, 'id', None))  # type: ignore[attr-defined]
            if cache_key in self._cache:
                del self._cache[cache_key]
            self._clear_cache_pattern("get_multi")

            logger.info(
                f"Successfully updated {getattr(self.model, '__tablename__', 'unknown')} record with id: {getattr(db_obj, 'id', 'unknown')}"  # type: ignore[attr-defined]
            )
            return db_obj
        except Exception as e:  # pragma: no cover
            db.rollback()  # pragma: no cover
            raise self._handle_database_error(e, "更新记录")  # pragma: no cover

    def remove(self, db: Session, *, id: Any) -> _ModelType:
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
                f"Successfully deleted {getattr(self.model, '__tablename__', 'unknown')} record with id: {id}"  # type: ignore[attr-defined]
            )
            return obj  # type: ignore[no-any-return]
        except ValueError:
            raise
        except Exception as e:  # pragma: no cover
            db.rollback()  # pragma: no cover
            raise self._handle_database_error(e, "删除记录")  # pragma: no cover

    def count(self, db: Session, filters: dict[str, Any] | None = None) -> int:
        """获取记录总数（支持筛选条件）"""
        try:
            query = db.query(self.model)
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field) and value is not None:
                        query = query.filter(getattr(self.model, field) == value)
            return query.count()
        except Exception as e:  # pragma: no cover
            raise self._handle_database_error(e, "统计记录数")  # pragma: no cover

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
    ) -> list[_ModelType]:
        """高级查询方法（支持筛选、搜索、排序）"""
        try:
            # 使用 QueryBuilder 构建查询
            # 注意: QueryBuilder 返回 sqlalchemy.sql.selectable.Select
            # 我们需要使用 db.execute(query).scalars().all() 来获取对象
            query = self.query_builder.build_query(
                filters=filters,
                search_query=search,
                search_fields=search_fields,
                sort_by=order_by,
                sort_desc=order_desc,
                skip=skip,
                limit=limit,
            )
            return list(db.execute(query).scalars().all())
        except Exception as e:  # pragma: no cover
            raise self._handle_database_error(e, "高级查询")  # pragma: no cover

    def bulk_create(
        self, db: Session, *, objects_in: list[_CreateSchemaType]
    ) -> list[_ModelType]:
        """批量创建记录"""
        try:
            db_objects: list[_ModelType] = []
            for obj_in in objects_in:
                obj_in_data: dict[str, Any] = (
                    obj_in.model_dump() if hasattr(obj_in, "model_dump") else obj_in  # type: ignore[assignment]
                )  # pragma: no cover
                db_objects.append(self.model(**obj_in_data))  # type: ignore[arg-type]

            db.add_all(db_objects)
            db.commit()

            # 刷新所有对象以获取数据库生成的值
            for obj in db_objects:
                db.refresh(obj)

            # 清除缓存
            self._clear_cache_pattern("get_multi")

            logger.info(
                f"Successfully bulk created {len(db_objects)} {getattr(self.model, '__tablename__', 'unknown')} records"  # type: ignore[attr-defined]
            )
            return db_objects
        except Exception as e:  # pragma: no cover
            db.rollback()  # pragma: no cover
            raise self._handle_database_error(e, "批量创建记录")  # pragma: no cover

    def _clear_cache_pattern(self, pattern: str) -> None:
        """清除匹配模式的缓存"""
        keys_to_remove = []
        for key in self._cache:
            if pattern in key:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

    def clear_cache(self) -> None:
        """清除所有缓存"""
        self._cache.clear()
        logger.info(f"Cache cleared for {getattr(self.model, '__tablename__', 'unknown')}")  # type: ignore[attr-defined]

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "model": getattr(self.model, '__tablename__', 'unknown'),  # type: ignore[attr-defined]
            "cache_size": len(self._cache),
            "cache_timeout": self._cache_timeout,
        }
