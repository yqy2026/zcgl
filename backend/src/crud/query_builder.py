import logging
from typing import Any, TypeVar

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import DeclarativeMeta

from ..core.exception_handler import InvalidRequestError
from .field_whitelist import EmptyWhitelist, get_whitelist_for_model

ModelType = TypeVar("ModelType", bound=DeclarativeMeta)

logger = logging.getLogger(__name__)


class QueryBuilder[ModelType]:
    """
    Unified Query Builder with Field Whitelist Validation.

    Security Enhancement:
    - Validates all filter, search, and sort fields against model whitelists
    - Logs blocked field access attempts for security monitoring
    - Provides clear error messages for unauthorized field access

    Supports dynamic filtering, searching, sorting, and pagination.
    """

    def __init__(self, model: type[ModelType]):
        self.model = model
        self.whitelist = get_whitelist_for_model(model)

        # Log if using empty whitelist (no fields allowed)
        if isinstance(self.whitelist, EmptyWhitelist):
            logging.getLogger().info(
                f"QueryBuilder using EMPTY whitelist for {model.__name__}. "
                "No fields allowed for filtering/searching/sorting. "
                "Define explicit whitelist to enable field access."
            )

    def build_count_query(
        self,
        filters: dict[str, Any] | None = None,
        search_query: str | None = None,
        search_fields: list[str] | None = None,
        search_conditions: list[Any] | None = None,
    ) -> Select[Any]:
        """
        Builds a query to count records matching criteria.
        """
        from sqlalchemy import func

        query = select(func.count()).select_from(self.model)

        if self._should_apply_soft_delete_filter(filters):
            query = self._apply_soft_delete_filter(query)

        if filters:
            query = self._apply_filters(query, filters)

        if search_conditions:
            query = query.where(or_(*search_conditions))
        elif search_query and search_fields:
            query = self._apply_search(query, search_query, search_fields)

        return query

    def build_query(
        self,
        filters: dict[str, Any] | None = None,
        search_query: str | None = None,
        search_fields: list[str] | None = None,
        search_conditions: list[Any] | None = None,
        sort_by: str | None = None,
        sort_desc: bool = True,
        skip: int = 0,
        limit: int = 100,
        base_query: Select[Any] | None = None,
    ) -> Select[Any]:
        """
        Builds a SQLAlchemy query with whitelist validation.

        Args:
            filters: Dictionary of filters.
                     Simple key-value pairs are treated as equality defaults.
                     Can also support more complex structures if needed (future extension).
                     Special keys:
                     - 'min_{field}': field >= value
                     - 'max_{field}': field <= value
                     - '{field}__in': field IN [values]
                     - '{field}__like': field LIKE %value%
                     - '{field}__ilike': field ILIKE %value%
                     - '{field}__ne': field != value
            search_query: Text to search for.
            search_fields: List of model field names to search against.
            sort_by: Field name to sort by.
            sort_desc: Sort descending/ascending.
            skip: Offset.
            limit: Limit.
            base_query: Optional existing query to build upon.

        Raises:
            InvalidRequestError: If blocked field is used in filters or sort

        Security: All field access is validated against model whitelist.
        """
        query = base_query if base_query is not None else select(self.model)

        # 0. Apply Soft Delete Filter (自动过滤已删除记录)
        if self._should_apply_soft_delete_filter(filters):
            query = self._apply_soft_delete_filter(query)

        # 1. Apply Filters (with validation)
        if filters:
            query = self._apply_filters(query, filters)

        # 2. Apply Search (with validation)
        if search_conditions:
            query = query.where(or_(*search_conditions))
        elif search_query and search_fields:
            query = self._apply_search(query, search_query, search_fields)

        # 3. Apply Sorting (with validation)
        if sort_by:
            query = self._apply_sorting(query, sort_by, sort_desc)
        else:
            # Default sort by id desc if available and allowed
            if hasattr(self.model, "id") and self.whitelist.can_sort("id"):
                id_column = getattr(self.model, "id")
                query = query.order_by(id_column.desc())

        # 4. Apply Pagination
        query = query.offset(skip).limit(limit)

        return query

    def _validate_filter_field(self, field_name: str) -> None:
        """
        Validate filter field against whitelist.

        Args:
            field_name: The field name to validate

        Raises:
            InvalidRequestError: If field is blocked for filtering

        Security: Logs all blocked access attempts for monitoring.
        """
        if not self.whitelist.can_filter(field_name):
            logger.error(
                f"Blocked filter on '{field_name}' for {self.model.__name__}. "
                f"Field not in filter whitelist or explicitly blocked."
            )
            raise InvalidRequestError(
                f"Filtering by field '{field_name}' is not allowed for {self.model.__name__}. "
                f"Field is either blocked or not in the filter whitelist."
            )

    def _apply_soft_delete_filter(self, query: Select[Any]) -> Select[Any]:
        """
        自动过滤已软删除的记录

        检查模型是否有 data_status 字段，如果有则自动添加过滤条件。
        这确保了所有查询默认排除已删除的数据。

        Returns:
            添加了软删除过滤条件的查询对象
        """
        if hasattr(self.model, "data_status"):
            data_status_column = getattr(self.model, "data_status")
            query = query.where(data_status_column != "已删除")
        return query

    @staticmethod
    def _has_data_status_filter(filters: dict[str, Any]) -> bool:
        for key, value in filters.items():
            if value is None:
                continue
            field_name = key
            if key.startswith("min_") or key.startswith("max_"):
                field_name = key[4:]
            elif "__" in key:
                field_name = key.rsplit("__", 1)[0]
            if field_name == "data_status":
                return True
        return False

    def _should_apply_soft_delete_filter(
        self, filters: dict[str, Any] | None
    ) -> bool:
        """
        Apply soft delete filter unless caller explicitly filters by data_status.
        """
        if not hasattr(self.model, "data_status"):
            return False
        if not filters:
            return True
        return not self._has_data_status_filter(filters)

    def _apply_filters(
        self, query: Select[Any], filters: dict[str, Any]
    ) -> Select[Any]:
        """
        Apply filters with whitelist validation.

        Security: Validates each field against filter whitelist before use.
        """
        conditions = []
        for key, value in filters.items():
            if value is None:
                continue

            # Parse special operators
            if key.startswith("min_"):
                field_name = key[4:]
                self._validate_filter_field(field_name)

                if hasattr(self.model, field_name):
                    conditions.append(getattr(self.model, field_name) >= value)
            elif key.startswith("max_"):
                field_name = key[4:]
                self._validate_filter_field(field_name)

                if hasattr(self.model, field_name):
                    conditions.append(getattr(self.model, field_name) <= value)
            elif "__" in key:
                field_name, op = key.rsplit("__", 1)
                self._validate_filter_field(field_name)

                if hasattr(self.model, field_name):
                    column = getattr(self.model, field_name)
                    if op == "in":
                        conditions.append(column.in_(value))
                    elif op == "like":
                        conditions.append(column.like(f"%{value}%"))
                    elif op == "ilike":
                        conditions.append(column.ilike(f"%{value}%"))
                    elif op == "ne":
                        conditions.append(column != value)
                    elif op == "gt":
                        conditions.append(column > value)
                    elif op == "lt":
                        conditions.append(column < value)
                    elif op == "ge":
                        conditions.append(column >= value)
                    elif op == "le":
                        conditions.append(column <= value)
                    else:
                        # Unknown operator, skip
                        pass
            else:
                # Direct equality
                self._validate_filter_field(key)

                if hasattr(self.model, key):
                    conditions.append(getattr(self.model, key) == value)

        if conditions:
            query = query.where(and_(*conditions))

        return query

    def _apply_search(
        self, query: Select[Any], search_term: str, search_fields: list[str]
    ) -> Select[Any]:
        """
        Apply search with whitelist validation.

        Security: Validates each search field against search whitelist.
        Blocked fields are skipped with a warning.
        """
        search_conditions = []
        for field in search_fields:
            # Validate search field
            if not self.whitelist.can_search(field):
                logger.warning(
                    f"Blocked search on '{field}' for {self.model.__name__}. "
                    f"Field not in search whitelist. Skipping."
                )
                continue  # Skip this field silently

            if hasattr(self.model, field):
                column = getattr(self.model, field)
                # Check column type to ensure it's text-compatible if needed, or just try ilike
                # For simplicity, assuming these are string types or casting might be needed for others.
                # In generic implementation, we usually rely on the caller to provide valid string fields.
                search_conditions.append(column.ilike(f"%{search_term}%"))

        if search_conditions:
            query = query.where(or_(*search_conditions))

        return query

    def _apply_sorting(
        self, query: Select[Any], sort_by: str, sort_desc: bool
    ) -> Select[Any]:
        """
        Apply sorting with whitelist validation.

        Args:
            query: The SQLAlchemy query
            sort_by: Field name to sort by
            sort_desc: Sort descending if True, ascending if False

        Returns:
            The modified query with sorting applied

        Raises:
            InvalidRequestError: If field is blocked for sorting

        Security: Validates sort field against sort whitelist.
        """
        # Validate sort field
        if not self.whitelist.can_sort(sort_by):
            logger.error(
                f"Blocked sort on '{sort_by}' for {self.model.__name__}. "
                f"Field not in sort whitelist or explicitly blocked."
            )
            raise InvalidRequestError(
                f"Sorting by field '{sort_by}' is not allowed for {self.model.__name__}. "
                f"Field is either blocked or not in the sort whitelist."
            )

        if hasattr(self.model, sort_by):
            column = getattr(self.model, sort_by)
            if sort_desc:
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        return query
