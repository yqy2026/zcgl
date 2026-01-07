from typing import Any, TypeVar

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import DeclarativeMeta

ModelType = TypeVar("ModelType", bound=DeclarativeMeta)


class QueryBuilder[ModelType: DeclarativeMeta]:
    """
    Unified Query Builder for SQLAlchemy models.
    Supports dynamic filtering, searching, sorting, and pagination.
    """

    def __init__(self, model: type[ModelType]):
        self.model = model

    def build_count_query(
        self,
        filters: dict[str, Any] | None = None,
        search_query: str | None = None,
        search_fields: list[str] | None = None,
    ) -> Select:
        """
        Builds a query to count records matching criteria.
        """
        from sqlalchemy import func

        query = select(func.count()).select_from(self.model)

        if filters:
            query = self._apply_filters(query, filters)

        if search_query and search_fields:
            query = self._apply_search(query, search_query, search_fields)

        return query

    def build_query(
        self,
        filters: dict[str, Any] | None = None,
        search_query: str | None = None,
        search_fields: list[str] | None = None,
        sort_by: str | None = None,
        sort_desc: bool = True,
        skip: int = 0,
        limit: int = 100,
        base_query: Select | None = None,
    ) -> Select:
        """
        Builds a SQLAlchemy query with the given parameters.

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
        """
        query = base_query if base_query is not None else select(self.model)

        # 1. Apply Filters
        if filters:
            query = self._apply_filters(query, filters)

        # 2. Apply Search
        if search_query and search_fields:
            query = self._apply_search(query, search_query, search_fields)

        # 3. Apply Sorting
        if sort_by:
            query = self._apply_sorting(query, sort_by, sort_desc)
        else:
            # Default sort by id desc if available, closely matching standard expectations
            if hasattr(self.model, "id"):
                query = query.order_by(self.model.id.desc())

        # 4. Apply Pagination
        query = query.offset(skip).limit(limit)

        return query

    def _apply_filters(self, query: Select, filters: dict[str, Any]) -> Select:
        conditions = []
        for key, value in filters.items():
            if value is None:
                continue

            # Parse special operators
            if key.startswith("min_"):
                field_name = key[4:]
                if hasattr(self.model, field_name):
                    conditions.append(getattr(self.model, field_name) >= value)
            elif key.startswith("max_"):
                field_name = key[4:]
                if hasattr(self.model, field_name):
                    conditions.append(getattr(self.model, field_name) <= value)
            elif "__" in key:
                field_name, op = key.rsplit("__", 1)
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
                        # Fallback to equality if op is unknown but potentially part of name?
                        # Ideally shouldn't happen with this convention.
                        pass
            else:
                # Direct equality
                if hasattr(self.model, key):
                    conditions.append(getattr(self.model, key) == value)

        if conditions:
            query = query.where(and_(*conditions))

        return query

    def _apply_search(
        self, query: Select, search_term: str, search_fields: list[str]
    ) -> Select:
        search_conditions = []
        for field in search_fields:
            if hasattr(self.model, field):
                column = getattr(self.model, field)
                # Check column type to ensure it's text-compatible if needed, or just try ilike
                # For simplicity, assuming these are string types or casting might be needed for others.
                # In generic implementation, we usually rely on the caller to provide valid string fields.
                search_conditions.append(column.ilike(f"%{search_term}%"))

        if search_conditions:
            query = query.where(or_(*search_conditions))

        return query

    def _apply_sorting(self, query: Select, sort_by: str, sort_desc: bool) -> Select:
        if hasattr(self.model, sort_by):
            column = getattr(self.model, sort_by)
            if sort_desc:
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        return query
