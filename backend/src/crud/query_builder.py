import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

from sqlalchemy import Select, and_, false, or_, select
from sqlalchemy.orm import DeclarativeMeta

from ..core.exception_handler import InvalidRequestError
from .field_whitelist import EmptyWhitelist, get_whitelist_for_model

ModelType = TypeVar("ModelType", bound=DeclarativeMeta)
PartyIdentifier = str | int

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PartyFilter:
    """主体维度过滤上下文。"""

    party_ids: Sequence[PartyIdentifier]
    legacy_org_ids: Sequence[PartyIdentifier] | None = None
    filter_mode: Literal["owner", "manager", "any"] = "any"
    owner_party_ids: Sequence[PartyIdentifier] | None = None
    manager_party_ids: Sequence[PartyIdentifier] | None = None
    owner_legacy_org_ids: Sequence[PartyIdentifier] | None = None
    manager_legacy_org_ids: Sequence[PartyIdentifier] | None = None
    mode: Literal["strict"] = "strict"
    allow_null: bool = False


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
        base_query: Select[Any] | None = None,
        distinct_column: Any | None = None,
        party_filter: PartyFilter | None = None,
    ) -> Select[Any]:
        """
        Builds a query to count records matching criteria.
        """
        from sqlalchemy import func

        query = base_query if base_query is not None else select(self.model)

        if self._should_apply_soft_delete_filter(filters):
            query = self._apply_soft_delete_filter(query)

        if party_filter is not None:
            query = self._apply_party_filter(query, party_filter)

        if filters:
            query = self._apply_filters(query, filters)

        if search_conditions:
            query = query.where(or_(*search_conditions))
        elif search_query and search_fields:
            query = self._apply_search(query, search_query, search_fields)

        query = query.order_by(None)

        if distinct_column is not None:
            distinct_subquery = (
                query.with_only_columns(distinct_column).distinct().subquery()
            )
            return select(func.count()).select_from(distinct_subquery)

        return select(func.count()).select_from(query.subquery())

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
        party_filter: PartyFilter | None = None,
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

        # 0.5 Apply Party Filter (可选主体隔离)
        if party_filter is not None:
            query = self._apply_party_filter(query, party_filter)

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

    def _apply_party_filter(
        self, query: Select[Any], party_filter: PartyFilter
    ) -> Select[Any]:
        """
        Apply party isolation filter.

        Rules:
        - If party_ids is empty, fail-closed with FALSE condition.
        - filter_mode controls which columns are considered.
        - If model has no applicable party column, skip filtering.
        """
        if party_filter.mode != "strict":
            logger.warning(
                "Unsupported party_filter mode '%s' for %s, fallback to strict",
                party_filter.mode,
                self.model.__name__,
            )

        owner_column = getattr(self.model, "owner_party_id", None)
        manager_column = getattr(self.model, "manager_party_id", None)
        generic_column = getattr(self.model, "party_id", None)
        legacy_org_column = getattr(self.model, "organization_id", None)

        relation_aware_filter = (
            party_filter.owner_party_ids is not None
            or party_filter.manager_party_ids is not None
            or party_filter.owner_legacy_org_ids is not None
            or party_filter.manager_legacy_org_ids is not None
        )
        if relation_aware_filter:
            return self._apply_relation_aware_party_filter(
                query,
                owner_party_ids=self._normalize_party_ids(party_filter.owner_party_ids),
                manager_party_ids=self._normalize_party_ids(
                    party_filter.manager_party_ids
                ),
                owner_legacy_org_ids=self._normalize_party_ids(
                    party_filter.owner_legacy_org_ids
                ),
                manager_legacy_org_ids=self._normalize_party_ids(
                    party_filter.manager_legacy_org_ids
                ),
                owner_column=owner_column,
                manager_column=manager_column,
                generic_column=generic_column,
                legacy_org_column=legacy_org_column,
                allow_null=party_filter.allow_null,
            )

        party_ids = self._normalize_party_ids(party_filter.party_ids)
        if not party_ids:
            logger.warning(
                "Applying fail-closed party filter for %s: empty party_ids",
                self.model.__name__,
            )
            return query.where(false())
        legacy_org_ids = self._normalize_party_ids(party_filter.legacy_org_ids)

        columns: list[Any] = []
        if party_filter.filter_mode == "owner":
            if owner_column is not None:
                columns.append(owner_column)
            elif generic_column is not None:
                columns.append(generic_column)
            elif legacy_org_column is not None:
                columns.append(legacy_org_column)
        elif party_filter.filter_mode == "manager":
            if manager_column is not None:
                columns.append(manager_column)
            elif generic_column is not None:
                columns.append(generic_column)
            elif legacy_org_column is not None:
                columns.append(legacy_org_column)
        else:
            for column in (
                owner_column,
                manager_column,
                generic_column,
                legacy_org_column,
            ):
                if column is None:
                    continue
                if any(column is existing for existing in columns):
                    continue
                columns.append(column)

        if not columns:
            logger.debug(
                "Skipping party filter for %s: no party-compatible column",
                self.model.__name__,
            )
            return query

        legacy_org_only_filter = (
            legacy_org_column is not None
            and len(columns) == 1
            and columns[0] is legacy_org_column
        )
        if legacy_org_only_filter and len(legacy_org_ids) == 0:
            logger.warning(
                "Applying fail-closed party filter for %s: legacy organization mapping is missing",
                self.model.__name__,
            )
            return query.where(false())

        conditions: list[Any] = []
        for column in columns:
            scope_ids = party_ids
            if (
                legacy_org_column is not None
                and column is legacy_org_column
                and len(legacy_org_ids) > 0
            ):
                scope_ids = legacy_org_ids
            conditions.append(column.in_(scope_ids))

        if party_filter.allow_null:
            conditions = [
                or_(column.is_(None), condition)
                for column, condition in zip(columns, conditions, strict=False)
            ]

        if len(conditions) == 1:
            return query.where(conditions[0])
        return query.where(or_(*conditions))

    def _apply_relation_aware_party_filter(
        self,
        query: Select[Any],
        *,
        owner_party_ids: list[PartyIdentifier],
        manager_party_ids: list[PartyIdentifier],
        owner_legacy_org_ids: list[PartyIdentifier],
        manager_legacy_org_ids: list[PartyIdentifier],
        owner_column: Any,
        manager_column: Any,
        generic_column: Any,
        legacy_org_column: Any,
        allow_null: bool,
    ) -> Select[Any]:
        available_columns = [
            column
            for column in (
                owner_column,
                manager_column,
                generic_column,
                legacy_org_column,
            )
            if column is not None
        ]
        if not available_columns:
            logger.debug(
                "Skipping relation-aware party filter for %s: no party-compatible column",
                self.model.__name__,
            )
            return query

        if (
            len(owner_party_ids) == 0
            and len(manager_party_ids) == 0
            and len(owner_legacy_org_ids) == 0
            and len(manager_legacy_org_ids) == 0
        ):
            logger.warning(
                "Applying fail-closed relation-aware party filter for %s: empty owner/manager scope",
                self.model.__name__,
            )
            return query.where(false())

        @dataclass
        class _ScopedRelationCondition:
            column: Any
            party_ids: set[PartyIdentifier]
            legacy_org_ids: set[PartyIdentifier]
            fallback_to_legacy_org_when_null: bool = False

        scoped_columns: dict[int, _ScopedRelationCondition] = {}

        def _bind_scope(
            column: Any | None,
            party_ids: list[PartyIdentifier],
            legacy_org_ids: list[PartyIdentifier] | None = None,
            *,
            fallback_to_legacy_org_when_null: bool = False,
        ) -> None:
            normalized_legacy_org_ids = legacy_org_ids or []
            if column is None or (
                len(party_ids) == 0 and len(normalized_legacy_org_ids) == 0
            ):
                return
            column_key = id(column)
            if column_key not in scoped_columns:
                scoped_columns[column_key] = _ScopedRelationCondition(
                    column=column,
                    party_ids=set(),
                    legacy_org_ids=set(),
                    fallback_to_legacy_org_when_null=fallback_to_legacy_org_when_null,
                )
            scoped_scope = scoped_columns[column_key]
            scoped_scope.party_ids.update(party_ids)
            scoped_scope.legacy_org_ids.update(normalized_legacy_org_ids)
            if fallback_to_legacy_org_when_null:
                scoped_scope.fallback_to_legacy_org_when_null = True

        owner_target_column = owner_column or generic_column or legacy_org_column
        manager_target_column = manager_column or generic_column or legacy_org_column
        _bind_scope(
            owner_target_column,
            owner_party_ids,
            legacy_org_ids=owner_legacy_org_ids,
            fallback_to_legacy_org_when_null=(
                legacy_org_column is not None and owner_target_column is owner_column
            ),
        )
        _bind_scope(
            manager_target_column,
            manager_party_ids,
            legacy_org_ids=manager_legacy_org_ids,
            fallback_to_legacy_org_when_null=(
                legacy_org_column is not None
                and manager_target_column is manager_column
            ),
        )

        if len(scoped_columns) == 0:
            logger.warning(
                "Applying fail-closed relation-aware party filter for %s: relation scope has no matching columns",
                self.model.__name__,
            )
            return query.where(false())

        conditions: list[Any] = []
        for scoped_scope in scoped_columns.values():
            scoped_legacy_org_ids = scoped_scope.legacy_org_ids
            if (
                legacy_org_column is not None
                and scoped_scope.column is legacy_org_column
            ):
                primary_scope_ids = (
                    scoped_legacy_org_ids
                    if len(scoped_legacy_org_ids) > 0
                    else scoped_scope.party_ids
                )
            else:
                primary_scope_ids = scoped_scope.party_ids

            condition: Any | None = None
            if len(primary_scope_ids) > 0:
                sorted_primary_scope_ids = sorted(
                    primary_scope_ids, key=lambda value: str(value)
                )
                condition = scoped_scope.column.in_(sorted_primary_scope_ids)

            if (
                scoped_scope.fallback_to_legacy_org_when_null
                and legacy_org_column is not None
                and len(scoped_legacy_org_ids) > 0
            ):
                sorted_legacy_scope_ids = sorted(
                    scoped_legacy_org_ids, key=lambda value: str(value)
                )
                legacy_condition = and_(
                    scoped_scope.column.is_(None),
                    legacy_org_column.in_(sorted_legacy_scope_ids),
                )
                condition = (
                    legacy_condition
                    if condition is None
                    else or_(condition, legacy_condition)
                )

            if condition is None:
                continue

            if allow_null:
                condition = or_(scoped_scope.column.is_(None), condition)
            conditions.append(condition)

        if len(conditions) == 0:
            logger.warning(
                "Applying fail-closed relation-aware party filter for %s: empty scoped conditions",
                self.model.__name__,
            )
            return query.where(false())

        if len(conditions) == 1:
            return query.where(conditions[0])
        return query.where(or_(*conditions))

    @staticmethod
    def _normalize_party_ids(
        party_ids: Sequence[PartyIdentifier] | None,
    ) -> list[PartyIdentifier]:
        if party_ids is None:
            return []

        normalized: list[PartyIdentifier] = []
        seen: set[str] = set()
        for party_id in party_ids:
            if party_id is None:
                continue
            identifier = str(party_id).strip()
            if identifier == "" or identifier in seen:
                continue
            seen.add(identifier)
            normalized.append(party_id)
        return normalized

    def apply_party_filter(
        self, query: Select[Any], party_filter: PartyFilter
    ) -> Select[Any]:
        """Public wrapper for applying party filter on custom queries."""
        return self._apply_party_filter(query, party_filter)

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
            query = query.where(
                or_(
                    data_status_column.is_(None),
                    data_status_column != "已删除",
                )
            )
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

    def _should_apply_soft_delete_filter(self, filters: dict[str, Any] | None) -> bool:
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
