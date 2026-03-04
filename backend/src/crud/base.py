"""
增强的基础CRUD操作类 - 支持缓存、性能监控和错误处理
"""

import json
import logging
import time
from collections.abc import Sequence
from typing import Any, Literal, Protocol, TypeVar, cast

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import DeclarativeMeta

from ..constants.performance_constants import CacheLimits, CacheTTL
from ..core.exception_handler import (
    BaseBusinessError,
    InvalidRequestError,
    ResourceNotFoundError,
)
from ..core.response_handler import ResponseHandler
from .query_builder import PartyFilter, QueryBuilder


class HasModelDump(Protocol):
    """Pydantic model protocol with model_dump method"""

    def model_dump(
        self, *, exclude_unset: bool = False, **kwargs: Any
    ) -> dict[str, Any]:
        """Dump model to dictionary"""
        ...


# Define TypeVars at module level with unique names
ModelType = TypeVar("ModelType", bound=DeclarativeMeta)
CreateSchemaType = TypeVar("CreateSchemaType", bound=HasModelDump)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=HasModelDump)

logger = logging.getLogger(__name__)


class CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]:
    """增强的基础CRUD操作类"""

    def __init__(self, model: type[ModelType]) -> None:
        """
        初始化CRUD对象

        Args:
            model: SQLAlchemy模型类
        """
        self.model = model
        self.query_builder = QueryBuilder(model)
        self._cache: dict[str, tuple[Any, float]] = {}  # 简单内存缓存
        self._cache_timeout = CacheTTL.SHORT_SECONDS  # 5分钟缓存超时

    @staticmethod
    def _serialize_party_filter(party_filter: PartyFilter | None) -> str | None:
        """序列化主体过滤上下文用于缓存隔离。"""
        if party_filter is None:
            return None

        def _normalize_scope(
            party_ids: Sequence[Any] | None,
        ) -> list[str] | None:
            if party_ids is None:
                return None
            return sorted(
                {
                    str(party_id).strip()
                    for party_id in party_ids
                    if str(party_id).strip() != ""
                }
            )

        serialized_filter = {
            "mode": party_filter.mode,
            "filter_mode": party_filter.filter_mode,
            "allow_null": int(party_filter.allow_null),
            "party_ids": _normalize_scope(party_filter.party_ids) or [],
            "legacy_org_ids": _normalize_scope(party_filter.legacy_org_ids),
            "owner_party_ids": _normalize_scope(party_filter.owner_party_ids),
            "manager_party_ids": _normalize_scope(party_filter.manager_party_ids),
            "owner_legacy_org_ids": _normalize_scope(party_filter.owner_legacy_org_ids),
            "manager_legacy_org_ids": _normalize_scope(
                party_filter.manager_legacy_org_ids
            ),
        }
        return json.dumps(
            serialized_filter,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )

    def _get_cache_key(self, method: str, **kwargs: Any) -> str:
        """生成缓存键"""
        key_parts = [getattr(self.model, "__tablename__", "unknown"), method]
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}:{self._serialize_cache_value(v)}")
        return "|".join(key_parts)

    @classmethod
    def _serialize_cache_value(cls, value: Any) -> str:
        """将缓存键值稳定序列化，避免复杂对象顺序差异导致的键漂移。"""
        normalized = cls._normalize_cache_value(value)
        return json.dumps(
            normalized,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def _normalize_cache_value(cls, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {
                str(key): cls._normalize_cache_value(nested_value)
                for key, nested_value in sorted(
                    value.items(), key=lambda item: str(item[0])
                )
            }
        if isinstance(value, (list, tuple)):
            return [cls._normalize_cache_value(item) for item in value]
        if isinstance(value, set):
            return sorted(
                cls._normalize_cache_value(item)
                for item in value
            )

        return repr(value)

    def _get_from_cache(self, cache_key: str) -> Any:
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
        if len(self._cache) > CacheLimits.MAX_CRUD_ENTRIES:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

    def _handle_database_error(
        self, error: Exception, operation: str
    ) -> Exception:  # pragma: no cover
        """处理数据库错误"""
        logger.error(f"Database error during {operation}: {str(error)}", exc_info=True)
        if isinstance(error, SQLAlchemyError):
            return ResponseHandler.database_error(error, f"{operation}失败")
        return error

    async def get(
        self,
        db: AsyncSession,
        id: Any,
        use_cache: bool = True,
        party_filter: PartyFilter | None = None,
    ) -> ModelType | None:
        """根据ID获取单个记录（支持缓存）"""
        cache_key = self._get_cache_key(
            "get",
            id=id,
            party_filter=self._serialize_party_filter(party_filter),
        )

        if use_cache:
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                return cast(ModelType, cached_result)

        try:
            stmt = select(self.model).where(getattr(self.model, "id") == id)
            if party_filter is not None:
                stmt = self.query_builder.apply_party_filter(stmt, party_filter)
            result = (await db.execute(stmt)).scalars().first()
            if use_cache and result is not None:  # pragma: no cover
                self._set_cache(cache_key, result)  # pragma: no cover
            return result
        except Exception as e:  # pragma: no cover
            raise self._handle_database_error(e, "获取记录")  # pragma: no cover

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        use_cache: bool = False,
        party_filter: PartyFilter | None = None,
        **kwargs: Any,  # 允许子类传递额外参数（如 task_type, status 等）
    ) -> list[ModelType]:
        """获取多个记录（支持缓存）

        子类可以通过 **kwargs 传递额外的筛选参数，例如：
            task_crud.get_multi(db, skip=0, limit=10, task_type="import")
        """
        cache_key = self._get_cache_key(
            "get_multi",
            skip=skip,
            limit=limit,
            party_filter=self._serialize_party_filter(party_filter),
        )

        if use_cache and limit <= 50:  # 只对小结果集缓存
            cached_result = self._get_from_cache(cache_key)  # pragma: no cover
            if cached_result is not None:  # pragma: no cover
                return cast(list[ModelType], cached_result)
        try:
            stmt = select(self.model)
            if party_filter is not None:
                stmt = self.query_builder.apply_party_filter(stmt, party_filter)
            stmt = stmt.offset(skip).limit(limit)
            result = (await db.execute(stmt)).scalars().all()
            records = list(result)

            if use_cache and limit <= 50:
                self._set_cache(cache_key, records)  # pragma: no cover
            return records
        except Exception as e:  # pragma: no cover
            raise self._handle_database_error(e, "获取记录列表")  # pragma: no cover

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: CreateSchemaType | dict[str, Any],
        commit: bool = True,
        **kwargs: Any,
    ) -> ModelType:
        """创建新记录（支持事务回滚和错误处理）"""
        try:
            if isinstance(obj_in, dict):
                obj_in_data = obj_in
            else:
                # obj_in is CreateSchemaType which has model_dump() per the Protocol
                # Use cast(Any) to bypass MyPy's type narrowing limitations
                obj_any = cast(Any, obj_in)
                obj_in_data = obj_any.model_dump()

            obj_in_data.update(kwargs)
            db_obj = self.model(**obj_in_data)
            db.add(db_obj)
            if commit:
                await db.commit()
                await db.refresh(db_obj)
            else:
                await db.flush()
                await db.refresh(db_obj)

            # 清除相关缓存
            self._clear_cache_pattern("get_multi")

            logger.info(
                f"Successfully created {getattr(self.model, '__tablename__', 'unknown')} record with id: {getattr(db_obj, 'id', 'unknown')}"
            )
            return db_obj
        except Exception as e:  # pragma: no cover
            if commit:
                await db.rollback()
            raise self._handle_database_error(e, "创建记录")  # pragma: no cover

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
        commit: bool = True,
    ) -> ModelType:
        """更新记录（支持事务回滚和缓存清理）"""
        try:
            obj_data = db_obj.__dict__
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                # obj_in is UpdateSchemaType which has model_dump() per the Protocol
                # Use cast(Any) to bypass MyPy's type narrowing limitations
                obj_any = cast(Any, obj_in)
                update_data = obj_any.model_dump(exclude_unset=True)

            for field in obj_data:
                if field in update_data:
                    setattr(db_obj, field, update_data[field])

            db.add(db_obj)
            if commit:
                await db.commit()
                await db.refresh(db_obj)
            else:
                await db.flush()
                await db.refresh(db_obj)

            # 清除相关缓存
            self._clear_get_cache_for_id(getattr(db_obj, "id", None))
            self._clear_cache_pattern("get_multi")

            logger.info(
                f"Successfully updated {getattr(self.model, '__tablename__', 'unknown')} record with id: {getattr(db_obj, 'id', 'unknown')}"
            )
            return db_obj
        except Exception as e:  # pragma: no cover
            if commit:
                await db.rollback()
            raise self._handle_database_error(e, "更新记录")  # pragma: no cover

    async def remove(
        self, db: AsyncSession, *, id: Any, commit: bool = True
    ) -> ModelType:
        """删除记录（支持事务回滚和缓存清理）"""
        try:
            obj = await db.get(self.model, id)
            if obj is None:
                raise ResourceNotFoundError(self.model.__name__, str(id))

            await db.delete(obj)
            if commit:
                await db.commit()
            else:
                await db.flush()

            # 清除相关缓存
            self._clear_get_cache_for_id(id)
            self._clear_cache_pattern("get_multi")

            logger.info(
                f"Successfully deleted {getattr(self.model, '__tablename__', 'unknown')} record with id: {id}"
            )
            return obj
        except BaseBusinessError:
            raise
        except Exception as e:  # pragma: no cover
            if commit:
                await db.rollback()
            raise self._handle_database_error(e, "删除记录")  # pragma: no cover

    async def count(
        self,
        db: AsyncSession,
        filters: dict[str, Any] | None = None,
        party_filter: PartyFilter | None = None,
        **kwargs: Any,
    ) -> int:
        """获取记录总数（支持筛选条件）

        子类可以通过 **kwargs 传递额外的筛选参数，例如：
            task_crud.count(db, task_type="import")
        """
        try:
            stmt = select(func.count()).select_from(self.model)
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field) and value is not None:
                        stmt = stmt.where(getattr(self.model, field) == value)
            if party_filter is not None:
                stmt = self.query_builder.apply_party_filter(stmt, party_filter)
            result = await db.execute(stmt)
            return int(result.scalar() or 0)
        except Exception as e:  # pragma: no cover
            raise self._handle_database_error(e, "统计记录数")  # pragma: no cover

    async def get_with_filters(
        self,
        db: AsyncSession,
        *,
        filters: dict[str, Any] | None = None,
        search: str | None = None,
        search_fields: list[str] | None = None,
        search_conditions: list[Any] | None = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        order_desc: bool = False,
        base_query: Select[Any] | None = None,
        party_filter: PartyFilter | None = None,
    ) -> list[ModelType]:
        """高级查询方法（支持筛选、搜索、排序）"""
        try:
            # 使用 QueryBuilder 构建查询
            # 注意: QueryBuilder 返回 sqlalchemy.sql.selectable.Select
            # 我们需要使用 db.execute(query).scalars().all() 来获取对象
            query: Select[Any] = self.query_builder.build_query(
                filters=filters,
                search_query=search,
                search_fields=search_fields,
                search_conditions=search_conditions,
                sort_by=order_by,
                sort_desc=order_desc,
                skip=skip,
                limit=limit,
                base_query=base_query,
                party_filter=party_filter,
            )
            result = (await db.execute(query)).scalars().all()
            return list(result)
        except Exception as e:  # pragma: no cover
            raise self._handle_database_error(e, "高级查询")  # pragma: no cover

    async def get_multi_with_count(
        self,
        db: AsyncSession,
        *,
        filters: dict[str, Any] | None = None,
        search: str | None = None,
        search_fields: list[str] | None = None,
        search_conditions: list[Any] | None = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        order_desc: bool = True,
        party_filter: PartyFilter | None = None,
    ) -> tuple[list[ModelType], int]:
        """基于 QueryBuilder 获取列表与总数"""
        try:
            stmt = self.query_builder.build_query(
                filters=filters,
                search_query=search,
                search_fields=search_fields,
                search_conditions=search_conditions,
                sort_by=order_by,
                sort_desc=order_desc,
                skip=skip,
                limit=limit,
                party_filter=party_filter,
            )
            count_stmt = self.query_builder.build_count_query(
                filters=filters,
                search_query=search,
                search_fields=search_fields,
                search_conditions=search_conditions,
                party_filter=party_filter,
            )

            result = (await db.execute(stmt)).scalars().all()
            total = int((await db.execute(count_stmt)).scalar() or 0)
            return list(result), total
        except Exception as e:  # pragma: no cover
            raise self._handle_database_error(e, "高级查询统计")  # pragma: no cover

    async def bulk_create(
        self, db: AsyncSession, *, objects_in: list[CreateSchemaType | dict[str, Any]]
    ) -> list[ModelType]:
        """批量创建记录"""
        try:
            db_objects: list[ModelType] = []
            for obj_in in objects_in:
                if isinstance(obj_in, dict):
                    obj_in_data = obj_in
                else:
                    # obj_in is CreateSchemaType which has model_dump() per the Protocol
                    # Use cast(Any) to bypass MyPy's type narrowing limitations
                    obj_any = cast(Any, obj_in)
                    obj_in_data = obj_any.model_dump()
                db_objects.append(self.model(**obj_in_data))

            db.add_all(db_objects)
            await db.commit()

            # 刷新所有对象以获取数据库生成的值
            for obj in db_objects:
                await db.refresh(obj)

            # 清除缓存
            self._clear_cache_pattern("get_multi")

            logger.info(
                f"Successfully bulk created {len(db_objects)} {getattr(self.model, '__tablename__', 'unknown')} records"
            )
            return db_objects
        except Exception as e:  # pragma: no cover
            await db.rollback()  # pragma: no cover
            raise self._handle_database_error(e, "批量创建记录")  # pragma: no cover

    def _clear_cache_pattern(self, pattern: str) -> None:
        """清除匹配模式的缓存"""
        keys_to_remove = []
        for key in self._cache:
            if pattern in key:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

    def _clear_get_cache_for_id(self, id_value: Any) -> None:
        """清理指定ID相关的 get 缓存（含租户隔离键）。"""
        if id_value is None:
            return
        id_token = f"id:{self._serialize_cache_value(id_value)}"
        keys_to_remove = []
        for cache_key in self._cache:
            segments = cache_key.split("|")
            if len(segments) < 2 or segments[1] != "get":
                continue
            if id_token in segments[2:]:
                keys_to_remove.append(cache_key)

        for cache_key in keys_to_remove:
            del self._cache[cache_key]

    def clear_cache(self) -> None:
        """清除所有缓存"""
        self._cache.clear()
        logger.info(
            f"Cache cleared for {getattr(self.model, '__tablename__', 'unknown')}"
        )

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "model": getattr(self.model, "__tablename__", "unknown"),
            "cache_size": len(self._cache),
            "cache_timeout": self._cache_timeout,
        }

    async def get_distinct_field_values(
        self,
        db: AsyncSession,
        field_name: str,
        *,
        filters: dict[str, Any] | None = None,
        sort_order: Literal["asc", "desc"] = "asc",
        use_cache: bool = True,
        exclude_empty: bool = True,
        party_filter: PartyFilter | None = None,
    ) -> list[Any]:
        """
        获取模型字段的不重复值列表,用于下拉框/筛选器UI组件

        Args:
            db: 数据库会话
            field_name: 要获取不重复值的字段名
            filters: 可选的额外筛选条件
            sort_order: 排序方向 ('asc' 或 'desc')
            use_cache: 是否使用缓存 (默认: True)
            exclude_empty: 是否排除 None 和空字符串 (默认: True)

        Returns:
            字段的不重复值列表

        Raises:
            AttributeError: 如果字段名在模型上不存在
            InvalidRequestError: 如果 sort_order 不是 'asc' 或 'desc'

        Examples:
            >>> # 获取所有不重复的业态类别
            >>> values = asset_crud.get_distinct_field_values(db, "business_category")
            >>> # 降序排列的使用状态
            >>> values = asset_crud.get_distinct_field_values(
            ...     db, "usage_status", sort_order="desc"
            ... )
            >>> # 带额外筛选条件的使用状态
            >>> values = asset_crud.get_distinct_field_values(
            ...     db, "usage_status", filters={"is_active": True}
            ... )
        """
        # 验证字段存在
        if not hasattr(self.model, field_name):
            raise AttributeError(
                f"Field '{field_name}' does not exist on model {self.model.__name__}"
            )

        # 验证排序参数
        if sort_order not in ("asc", "desc"):
            raise InvalidRequestError(
                f"sort_order must be 'asc' or 'desc', got '{sort_order}'",
                field="sort_order",
            )

        # 检查缓存
        cache_key = None
        if use_cache:
            cache_key = self._get_cache_key(
                "distinct_values",
                field=field_name,
                filters=filters,
                sort=sort_order,
                exclude_empty=exclude_empty,
                party_filter=self._serialize_party_filter(party_filter),
            )
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                return cast(list[Any], cached_result)

        # 构建查询
        field_attr = getattr(self.model, field_name)
        stmt = select(field_attr)

        # 应用空值筛选
        if exclude_empty:
            stmt = stmt.where(field_attr.isnot(None), field_attr != "")

        # 应用额外筛选条件
        if filters:
            for filter_key, filter_value in filters.items():
                if hasattr(self.model, filter_key):
                    stmt = stmt.where(getattr(self.model, filter_key) == filter_value)

        if party_filter is not None:
            stmt = self.query_builder.apply_party_filter(stmt, party_filter)

        # 应用去重和排序
        stmt = stmt.distinct()
        if sort_order == "asc":
            stmt = stmt.order_by(field_attr.asc())
        else:
            stmt = stmt.order_by(field_attr.desc())

        # 执行查询
        result = (await db.execute(stmt)).all()

        # 从结果元组中提取值
        values = [row[0] for row in result if row[0]]

        # 缓存结果
        if use_cache and cache_key:
            self._set_cache(cache_key, values)

        return values
