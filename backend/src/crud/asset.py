"""
资产CRUD操作 - 优化版本

注意: 此层为纯数据访问层，不包含业务逻辑。
资产计算逻辑（AssetCalculator）应在 API 或 Service 层调用。
"""

from typing import Any, NamedTuple, TypeVar, cast

from sqlalchemy import Float, Select, case, delete, false, func, insert, or_, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, load_only, selectinload, with_loader_criteria
from sqlalchemy.sql.base import ExecutableOption

from ..constants.business_constants import DataStatusValues, DateTimeFields
from ..core.exception_handler import ResourceNotFoundError
from ..core.search_index import (
    SEARCH_INDEX_FIELDS,
    build_asset_id_subquery,
    build_search_index_entries,
)
from ..models.asset import Asset
from ..models.asset_history import AssetHistory
from ..models.asset_search_index import AssetSearchIndex
from ..models.auth import User
from ..models.contract_group import Contract, LeaseContractDetail
from ..models.party import Party
from ..schemas.asset import AssetCreate, AssetUpdate
from .asset_support import (
    AssetFilterData,
    AssetIdentifier,
    AssetMutationData,
    SensitiveDataHandler,
    _result_all,
    _result_first,
    _result_scalar,
    _scalars_all,
    _scalars_first,
)
from .base import CRUDBase
from .query_builder import PartyFilter

TSelectRow = TypeVar("TSelectRow", bound=tuple[Any, ...])


class OccupancyAggregationRow(NamedTuple):
    total_assets: int | None
    total_rentable_area: float | None
    total_rented_area: float | None
    rentable_assets_count: int | None


class OccupancyCategoryAggregationRow(NamedTuple):
    category: str | None
    total_rentable_area: float | None
    total_rented_area: float | None
    total_assets: int | None
    rentable_assets_count: int | None


class AreaSummaryAggregationRow(NamedTuple):
    total_assets: int | None
    total_land_area: float | None
    total_rentable_area: float | None
    total_rented_area: float | None
    total_non_commercial_area: float | None
    assets_with_area_data: int | None


class AssetCRUD(CRUDBase[Asset, AssetCreate, AssetUpdate]):
    """资产CRUD操作类 - 优化版本"""

    SORT_FIELD_ALIASES = {
        "occupancy_rate": "cached_occupancy_rate",
    }
    FILTER_FIELD_ALIASES = {
        "min_occupancy_rate": "min_cached_occupancy_rate",
        "max_occupancy_rate": "max_cached_occupancy_rate",
        "occupancy_rate": "cached_occupancy_rate",
    }
    IMMUTABLE_MUTATION_FIELDS = (
        "version",
        "tenant_name",
        "lease_contract_number",
        "contract_start_date",
        "contract_end_date",
        "monthly_rent",
        "deposit",
        "wuyang_project_name",
        "description",
    )
    COMPUTED_MUTATION_FIELDS = ("unrented_area", "occupancy_rate")
    RELATION_MUTATION_FIELDS = ("ownership_entity",)

    @staticmethod
    def _not_deleted_clause(column: Any) -> Any:
        return or_(column.is_(None), column != DataStatusValues.ASSET_DELETED)

    @staticmethod
    def _asset_projection_load_options(
        *,
        include_contract_projection: bool = True,
    ) -> tuple[ExecutableOption, ...]:
        """资产投影字段所需的关系预加载选项。"""
        options: list[ExecutableOption] = [
            joinedload(Asset.owner_party),
            joinedload(Asset.manager_party),
            joinedload(Asset.project),
        ]
        if include_contract_projection:
            options.append(
                selectinload(Asset.contracts).options(
                    load_only(
                        Contract.contract_id,
                        Contract.status,
                        Contract.contract_number,
                        Contract.effective_from,
                        Contract.effective_to,
                        Contract.created_at,
                        Contract.data_status,
                    ),
                    joinedload(Contract.lease_detail).load_only(
                        LeaseContractDetail.tenant_name,
                        LeaseContractDetail.monthly_rent_base,
                        LeaseContractDetail.total_deposit,
                    ),
                )
            )
            options.append(
                with_loader_criteria(
                    Contract,
                    lambda cls: or_(
                        cls.data_status.is_(None),
                        cls.data_status != DataStatusValues.ASSET_DELETED,
                    ),
                    include_aliases=True,
                )
            )
        return tuple(options)

    def __init__(self) -> None:
        super().__init__(Asset)
        # Asset 模型的敏感字段（需要加密的PII字段）
        self.sensitive_data_handler = SensitiveDataHandler(
            # 可搜索字段（需要精确匹配查询）
            searchable_fields={
                "address",  # 地址
            },
            # 不可搜索字段（只需要保护）
            non_searchable_fields={
                "manager_name",  # 经理姓名
                "project_phone",  # 项目电话
            },
        )

    @classmethod
    def _clean_asset_data(
        cls,
        data: AssetMutationData,
        *,
        remove_immutable_fields: bool = True,
        remove_computed_fields: bool = True,
        remove_relation_fields: bool = True,
    ) -> AssetMutationData:
        if remove_immutable_fields:
            for field in cls.IMMUTABLE_MUTATION_FIELDS:
                data.pop(field, None)
        if remove_computed_fields:
            for field in cls.COMPUTED_MUTATION_FIELDS:
                data.pop(field, None)
        if remove_relation_fields:
            for field in cls.RELATION_MUTATION_FIELDS:
                data.pop(field, None)
        return data

    async def _refresh_search_index_entries(
        self, db: AsyncSession, *, asset_id: str, data: AssetMutationData
    ) -> None:
        fields_to_refresh = [
            field_name for field_name in SEARCH_INDEX_FIELDS if field_name in data
        ]
        if not fields_to_refresh:
            return

        await db.execute(
            delete(AssetSearchIndex).where(
                AssetSearchIndex.asset_id == asset_id,
                AssetSearchIndex.field_name.in_(fields_to_refresh),
            )
        )

        key_manager = self.sensitive_data_handler.encryptor.key_manager
        entries = []
        for field_name in fields_to_refresh:
            entries.extend(
                build_search_index_entries(
                    asset_id=asset_id,
                    field_name=field_name,
                    value=data.get(field_name),
                    key_manager=key_manager,
                )
            )

        if not entries:
            return

        await db.execute(
            insert(AssetSearchIndex),
            [
                {
                    "asset_id": entry.asset_id,
                    "field_name": entry.field_name,
                    "token_hash": entry.token_hash,
                    "key_version": entry.key_version,
                }
                for entry in entries
            ],
        )

    def _asset_base_query_with_relations(
        self,
        *,
        include_contract_projection: bool = True,
    ) -> Select[tuple[Asset]]:
        """
        资产列表/批量查询的基础查询（预加载高频关系，避免 N+1）

        注意：集合关系使用 selectinload，避免 joinedload 导致的行膨胀。
        """
        return select(Asset).options(
            *self._asset_projection_load_options(
                include_contract_projection=include_contract_projection
            ),
        )

    def _normalize_sort_field(self, sort_field: str) -> str:
        return self.SORT_FIELD_ALIASES.get(sort_field, sort_field)

    def _normalize_filters(self, filters: AssetFilterData | None) -> AssetFilterData:
        qb_filters: AssetFilterData = {}
        if not filters:
            return qb_filters

        for key, value in filters.items():
            normalized_key = self.FILTER_FIELD_ALIASES.get(key, key)
            if normalized_key == "is_litigated" and isinstance(value, str):
                normalized_bool = value.strip().lower()
                if normalized_bool in {"true", "1", "yes", "y", "是"}:
                    value = True
                elif normalized_bool in {"false", "0", "no", "n", "否"}:
                    value = False
            if normalized_key == "min_area":
                qb_filters["min_actual_property_area"] = value
            elif normalized_key == "max_area":
                qb_filters["max_actual_property_area"] = value
            elif normalized_key == "ids":
                qb_filters["id__in"] = value
            else:
                qb_filters[normalized_key] = value

        return qb_filters

    @staticmethod
    def _normalized_org_ids(party_filter: PartyFilter) -> list[str]:
        return [
            str(org_id).strip()
            for org_id in party_filter.party_ids
            if str(org_id).strip() != ""
        ]

    async def _resolve_creator_principals(
        self,
        db: AsyncSession,
        party_filter: PartyFilter,
    ) -> set[str]:
        org_ids = self._normalized_org_ids(party_filter)
        if not org_ids:
            return set()

        stmt = select(User.id, User.username).where(
            User.default_organization_id.in_(org_ids)  # DEPRECATED legacy org scope fallback
        )
        result = await db.execute(stmt)
        rows: list[tuple[object, object]] = await _result_all(result)
        principals: set[str] = set()
        for user_id, username in rows:
            if user_id is not None and str(user_id).strip() != "":
                principals.add(str(user_id).strip())
            if username is not None and str(username).strip() != "":
                principals.add(str(username).strip())
        return principals

    @staticmethod
    def _apply_creator_scope(
        stmt: Select[TSelectRow],
        principals: set[str],
    ) -> Select[TSelectRow]:
        if not principals:
            return stmt.where(false())
        return stmt.where(Asset.created_by.in_(principals))

    @staticmethod
    def _supports_party_scope_columns() -> bool:
        return any(
            hasattr(Asset, column_name)
            for column_name in (
                "owner_party_id",
                "manager_party_id",
                "party_id",
                "organization_id",
            )
        )

    async def _apply_asset_party_filter(
        self,
        db: AsyncSession,
        stmt: Select[Any],
        party_filter: PartyFilter,
    ) -> Select[Any]:
        if self._supports_party_scope_columns():
            return self.query_builder.apply_party_filter(stmt, party_filter)

        principals = await self._resolve_creator_principals(db, party_filter)
        return self._apply_creator_scope(stmt, principals)

    async def create_async(
        self,
        db: AsyncSession,
        *,
        obj_in: AssetCreate | AssetMutationData,
        commit: bool = True,
        **kwargs: object,
    ) -> Asset:
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()

        obj_in_data.update(kwargs)
        self._clean_asset_data(obj_in_data)

        encrypted_data = cast(
            AssetMutationData,
            self.sensitive_data_handler.encrypt_data(obj_in_data.copy()),
        )
        db_obj = Asset(**encrypted_data)
        db.add(db_obj)
        await db.flush()

        await self._refresh_search_index_entries(
            db, asset_id=db_obj.id, data=obj_in_data
        )

        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_async(
        self,
        db: AsyncSession,
        id: AssetIdentifier,
        use_cache: bool = False,
        include_deleted: bool = False,
        party_filter: PartyFilter | None = None,
    ) -> Asset | None:
        stmt = select(Asset).options(*self._asset_projection_load_options()).filter(
            getattr(self.model, "id") == id
        )
        if party_filter is not None:
            stmt = await self._apply_asset_party_filter(db, stmt, party_filter)
        if not include_deleted:
            stmt = stmt.filter(self._not_deleted_clause(Asset.data_status))

        result = await db.execute(stmt)
        asset: Asset | None = await _scalars_first(result)
        if asset is not None:
            self._decrypt_asset_object(asset)
        return asset

    def _decrypt_asset_object(self, asset: Asset) -> None:
        """
        解密资产对象的PII字段（原地修改）

        Args:
            asset: SQLAlchemy模型对象
        """
        for field_name in self.sensitive_data_handler.ALL_PII_FIELDS:
            if hasattr(asset, field_name):
                value = getattr(asset, field_name)
                if value is not None:
                    decrypted_value = self.sensitive_data_handler.decrypt_field(
                        field_name, value
                    )
                    setattr(asset, field_name, decrypted_value)

    def _encrypt_update_data(self, update_data: AssetMutationData) -> AssetMutationData:
        """
        加密更新数据中的PII字段

        Args:
            update_data: 更新数据字典

        Returns:
            加密后的更新数据
        """
        encrypted_data = {}
        for field_name, value in update_data.items():
            if field_name in self.sensitive_data_handler.ALL_PII_FIELDS:
                encrypted_data[field_name] = self.sensitive_data_handler.encrypt_field(
                    field_name, value
                )
            else:
                encrypted_data[field_name] = value
        return encrypted_data

    async def get_by_name_async(
        self,
        db: AsyncSession,
        asset_name: str,
        include_deleted: bool = False,
    ) -> Asset | None:
        stmt = select(Asset).options(*self._asset_projection_load_options()).filter(
            Asset.asset_name == asset_name
        )
        if not include_deleted:
            stmt = stmt.filter(self._not_deleted_clause(Asset.data_status))

        result = await db.execute(stmt)
        asset: Asset | None = await _scalars_first(result)
        if asset is not None:
            self._decrypt_asset_object(asset)
        return asset

    async def get_multi_with_search_async(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        filters: AssetFilterData | None = None,
        sort_field: str = DateTimeFields.CREATED_AT,
        sort_order: str = "desc",
        include_relations: bool = True,
        include_contract_projection: bool = True,
        party_filter: PartyFilter | None = None,
    ) -> tuple[list[Asset], int]:
        qb_filters = self._normalize_filters(filters)
        normalized_sort_field = self._normalize_sort_field(sort_field)

        non_pii_search_fields = ["asset_name", "business_category"]
        pii_search_fields = ["address"]
        search_conditions: list[Any] | None = None
        if search:
            search_conditions = []
            for field in non_pii_search_fields:
                if self.query_builder.whitelist.can_search(field) and hasattr(
                    Asset, field
                ):
                    search_conditions.append(getattr(Asset, field).ilike(f"%{search}%"))

            for field in pii_search_fields:
                if self.query_builder.whitelist.can_search(field) and hasattr(
                    Asset, field
                ):
                    if self.sensitive_data_handler.encryption_enabled:
                        subquery = build_asset_id_subquery(
                            field_name=field,
                            search_text=search,
                            key_manager=self.sensitive_data_handler.encryptor.key_manager,
                        )
                        if subquery is not None:
                            search_conditions.append(Asset.id.in_(subquery))
                        else:
                            encrypted = self.sensitive_data_handler.encrypt_field(
                                field, search
                            )
                            if encrypted is not None:
                                search_conditions.append(
                                    getattr(Asset, field) == encrypted
                                )
                    else:
                        search_conditions.append(
                            getattr(Asset, field).ilike(f"%{search}%")
                        )

            search_conditions.append(Party.name.ilike(f"%{search}%"))

            if not search_conditions:
                search_conditions = None

        base_query: Select[tuple[Asset]] = (
            self._asset_base_query_with_relations(
                include_contract_projection=include_contract_projection
            )
            if include_relations
            else select(Asset).options(
                *self._asset_projection_load_options(
                    include_contract_projection=include_contract_projection
                )
            )
        )
        if search_conditions:
            base_query = base_query.join(
                Party, Asset.owner_party_id == Party.id, isouter=True
            )
        if party_filter is not None:
            base_query = await self._apply_asset_party_filter(
                db,
                base_query,
                party_filter,
            )
        query: Select[Any] = self.query_builder.build_query(
            filters=qb_filters,
            search_conditions=search_conditions,
            sort_by=normalized_sort_field,
            sort_desc=(sort_order.lower() == "desc"),
            skip=skip,
            limit=limit,
            base_query=base_query,
        )
        result = await db.execute(query)
        assets: list[Asset] = await _scalars_all(result)

        count_base_query: Select[tuple[str]] = select(Asset.id)
        if search_conditions:
            count_base_query = count_base_query.join(
                Party, Asset.owner_party_id == Party.id, isouter=True
            )
        if party_filter is not None:
            count_base_query = await self._apply_asset_party_filter(
                db,
                count_base_query,
                party_filter,
            )

        cnt_query = self.query_builder.build_count_query(
            filters=qb_filters,
            search_conditions=search_conditions,
            base_query=count_base_query,
            distinct_column=Asset.id,
        )
        total_result = await db.execute(cnt_query)
        total_raw = await _result_scalar(total_result)
        total = int(cast(int | float | str, total_raw)) if total_raw is not None else 0

        for asset in assets:
            self._decrypt_asset_object(asset)

        return assets, total

    async def create_with_history_async(
        self,
        db: AsyncSession,
        obj_in: AssetCreate,
        commit: bool = True,
        operator: str | None = None,
        organization_id: str | None = None,  # DEPRECATED alias
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> Asset:
        obj_in_data = obj_in.model_dump()
        self._clean_asset_data(obj_in_data, remove_relation_fields=False)
        if (
            organization_id is not None
            and organization_id.strip() != ""
            and obj_in_data.get("manager_party_id") in (None, "")
        ):
            # 仅保留最小兼容：旧 organization_id 输入不再写库列，按 manager_party_id 别名处理。
            obj_in_data["manager_party_id"] = organization_id
        encrypted_data = cast(
            AssetMutationData,
            self.sensitive_data_handler.encrypt_data(obj_in_data.copy()),
        )

        db_obj = Asset(**encrypted_data)
        db.add(db_obj)
        await db.flush()

        await self._refresh_search_index_entries(
            db, asset_id=db_obj.id, data=obj_in_data
        )

        history = AssetHistory()
        history.asset_id = db_obj.id
        history.operation_type = "CREATE"
        history.description = f"创建资产: {db_obj.asset_name}"
        history.operator = operator
        history.ip_address = ip_address
        history.user_agent = user_agent
        history.session_id = session_id
        db.add(history)

        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_async(
        self,
        db: AsyncSession,
        *,
        db_obj: Asset,
        obj_in: AssetUpdate | AssetMutationData,
        commit: bool = True,
    ) -> Asset:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        self._clean_asset_data(update_data)

        encrypted_data = self._encrypt_update_data(update_data)
        result: Asset = await super().update(
            db=db, db_obj=db_obj, obj_in=encrypted_data, commit=False
        )

        await self._refresh_search_index_entries(
            db, asset_id=result.id, data=update_data
        )

        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(result)
        return result

    async def update_with_history_async(
        self,
        db: AsyncSession,
        db_obj: Asset,
        obj_in: AssetUpdate,
        commit: bool = True,
        operator: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> Asset:
        update_data = obj_in.model_dump(exclude_unset=True)
        self._clean_asset_data(
            update_data,
            remove_computed_fields=False,
            remove_relation_fields=False,
        )

        for field, new_value in update_data.items():
            if hasattr(db_obj, field):
                old_value = getattr(db_obj, field)
                if old_value != new_value:
                    history = AssetHistory()
                    history.asset_id = db_obj.id
                    history.operation_type = "UPDATE"
                    history.field_name = field
                    history.old_value = (
                        str(old_value) if old_value is not None else None
                    )
                    history.new_value = (
                        str(new_value) if new_value is not None else None
                    )
                    history.description = (
                        f"更新字段 {field}: {old_value} -> {new_value}"
                    )
                    history.operator = operator
                    history.ip_address = ip_address
                    history.user_agent = user_agent
                    history.session_id = session_id
                    db.add(history)

        self._clean_asset_data(
            update_data,
            remove_immutable_fields=False,
            remove_relation_fields=False,
        )
        encrypted_data = self._encrypt_update_data(update_data)

        for field, value in encrypted_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await self._refresh_search_index_entries(
            db, asset_id=db_obj.id, data=update_data
        )
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def remove_async(
        self, db: AsyncSession, *, id: AssetIdentifier, commit: bool = True
    ) -> Asset:
        obj = await db.get(self.model, id)
        if obj is None:
            raise ResourceNotFoundError(self.model.__name__, str(id))
        await db.delete(obj)
        if commit:
            await db.commit()
        else:
            await db.flush()
        return obj

    async def get_multi_by_ids_async(
        self,
        db: AsyncSession,
        ids: list[str],
        include_relations: bool = False,
        include_deleted: bool = False,
        decrypt: bool = True,
    ) -> list[Asset]:
        if not ids:
            return []

        base_query: Select[tuple[Asset]] = (
            self._asset_base_query_with_relations()
            if include_relations
            else select(Asset).options(*self._asset_projection_load_options())
        )
        query = base_query.where(Asset.id.in_(ids))
        if not include_deleted:
            query = query.where(self._not_deleted_clause(Asset.data_status))

        result = await db.execute(query)
        assets: list[Asset] = await _scalars_all(result)
        if decrypt:
            for asset in assets:
                self._decrypt_asset_object(asset)
        return assets

    async def get_by_ownership_name_like_async(
        self,
        db: AsyncSession,
        *,
        ownership_name: str,
        limit: int = 20,
        include_deleted: bool = False,
        decrypt: bool = True,
    ) -> list[Asset]:
        stmt = (
            select(Asset)
            .join(Party, Asset.owner_party_id == Party.id, isouter=True)
            .where(Party.name.ilike(f"%{ownership_name}%"))
        )
        if not include_deleted:
            stmt = stmt.where(self._not_deleted_clause(Asset.data_status))

        result = await db.execute(stmt.limit(limit))
        assets: list[Asset] = await _scalars_all(result)
        if decrypt:
            for asset in assets:
                self._decrypt_asset_object(asset)
        return assets

    async def search_by_field_with_candidates_async(
        self,
        db: AsyncSession,
        *,
        field_name: str,
        candidates: list[str],
        limit: int = 20,
        include_deleted: bool = False,
        decrypt: bool = True,
    ) -> tuple[list[Asset], bool]:
        if len(candidates) == 0 or not hasattr(Asset, field_name):
            return [], False

        handler = self.sensitive_data_handler
        model_field = getattr(Asset, field_name)
        used_blind_index = False

        if handler.encryption_enabled and field_name in handler.SEARCHABLE_FIELDS:
            conditions = []
            for candidate in candidates:
                subquery = build_asset_id_subquery(
                    field_name=field_name,
                    search_text=candidate,
                    key_manager=handler.encryptor.key_manager,
                )
                if subquery is not None:
                    conditions.append(Asset.id.in_(subquery))
                    used_blind_index = True
                else:
                    encrypted = handler.encrypt_field(field_name, candidate)
                    if encrypted is not None:
                        conditions.append(model_field == encrypted)
            if not conditions:
                return [], used_blind_index
            stmt = select(Asset).where(or_(*conditions))
        else:
            query_value = candidates[0]
            stmt = select(Asset).where(model_field.ilike(f"%{query_value}%"))

        if not include_deleted:
            stmt = stmt.where(self._not_deleted_clause(Asset.data_status))

        result = await db.execute(stmt.limit(limit))
        assets: list[Asset] = await _scalars_all(result)
        if decrypt:
            for asset in assets:
                self._decrypt_asset_object(asset)
        return assets, used_blind_index

    def _apply_simple_asset_filters(
        self, stmt: Select[TSelectRow], filters: AssetFilterData | None
    ) -> Select[TSelectRow]:
        """应用 analytics 场景下的简单等值过滤。"""
        if not filters:
            return stmt

        for key, value in filters.items():
            if hasattr(Asset, key) and value is not None:
                stmt = stmt.where(getattr(Asset, key) == value)

        return stmt

    async def get_occupancy_aggregation_async(
        self, db: AsyncSession, *, filters: AssetFilterData | None = None
    ) -> OccupancyAggregationRow | None:
        stmt = self._apply_simple_asset_filters(select(Asset), filters)
        agg_stmt = stmt.with_only_columns(
            func.count(Asset.id).label("total_assets"),
            sql_cast(func.sum(func.coalesce(Asset.rentable_area, 0)), Float).label(
                "total_rentable_area"
            ),
            sql_cast(func.sum(func.coalesce(Asset.rented_area, 0)), Float).label(
                "total_rented_area"
            ),
            func.count(case((Asset.rentable_area > 0, 1))).label(
                "rentable_assets_count"
            ),
        )
        result = await db.execute(agg_stmt)
        aggregation_row: OccupancyAggregationRow | None = await _result_first(result)
        return aggregation_row

    async def get_occupancy_by_category_aggregation_async(
        self,
        db: AsyncSession,
        *,
        category_field: str,
        filters: AssetFilterData | None = None,
    ) -> list[OccupancyCategoryAggregationRow]:
        if not hasattr(Asset, category_field):
            return []

        stmt = self._apply_simple_asset_filters(select(Asset), filters)
        category_column = getattr(Asset, category_field)
        agg_stmt = (
            stmt.with_only_columns(
                category_column.label("category"),
                sql_cast(func.sum(func.coalesce(Asset.rentable_area, 0)), Float).label(
                    "total_rentable_area"
                ),
                sql_cast(func.sum(func.coalesce(Asset.rented_area, 0)), Float).label(
                    "total_rented_area"
                ),
                func.count(Asset.id).label("total_assets"),
                func.count(case((Asset.rentable_area > 0, 1))).label(
                    "rentable_assets_count"
                ),
            ).group_by(category_column)
        )
        result = await db.execute(agg_stmt)
        rows: list[OccupancyCategoryAggregationRow] = await _result_all(result)
        return rows

    async def get_area_summary_aggregation_async(
        self, db: AsyncSession, *, filters: AssetFilterData | None = None
    ) -> AreaSummaryAggregationRow | None:
        stmt = self._apply_simple_asset_filters(select(Asset), filters)
        agg_stmt = stmt.with_only_columns(
            func.count(Asset.id).label("total_assets"),
            sql_cast(func.sum(func.coalesce(Asset.land_area, 0)), Float).label(
                "total_land_area"
            ),
            sql_cast(func.sum(func.coalesce(Asset.rentable_area, 0)), Float).label(
                "total_rentable_area"
            ),
            sql_cast(func.sum(func.coalesce(Asset.rented_area, 0)), Float).label(
                "total_rented_area"
            ),
            sql_cast(func.sum(func.coalesce(Asset.non_commercial_area, 0)), Float).label(
                "total_non_commercial_area"
            ),
            func.count(case((Asset.land_area.isnot(None), 1))).label(
                "assets_with_area_data"
            ),
        )
        result = await db.execute(agg_stmt)
        summary_row: AreaSummaryAggregationRow | None = await _result_first(result)
        return summary_row

    async def has_contracts_async(self, db: AsyncSession, asset_id: str) -> bool:
        """检查资产是否关联合同（通过新合同关联表）"""
        from ..models.associations import contract_assets

        stmt = (
            select(contract_assets.c.asset_id)
            .where(contract_assets.c.asset_id == asset_id)
            .limit(1)
        )
        result = await db.execute(stmt)
        first_row: tuple[str] | None = await _result_first(result)
        return first_row is not None

    async def has_property_certs_async(
        self, db: AsyncSession, asset_id: str
    ) -> bool:
        """检查资产是否关联产权证（通过关联表）"""
        from ..models.associations import property_cert_assets

        stmt = (
            select(property_cert_assets.c.asset_id)
            .where(property_cert_assets.c.asset_id == asset_id)
            .limit(1)
        )
        result = await db.execute(stmt)
        first_row: tuple[str] | None = await _result_first(result)
        return first_row is not None

    async def has_contract_ledger_entries_async(
        self, db: AsyncSession, asset_id: str
    ) -> bool:
        """检查资产是否有关联合同台账记录"""
        from ..models.associations import contract_assets
        from ..models.contract_group import ContractLedgerEntry

        stmt = (
            select(ContractLedgerEntry.entry_id)
            .join(
                contract_assets,
                ContractLedgerEntry.contract_id == contract_assets.c.contract_id,
            )
            .where(contract_assets.c.asset_id == asset_id)
            .limit(1)
        )
        result = await db.execute(stmt)
        first_row: tuple[str] | None = await _result_first(result)
        return first_row is not None

    async def get_assets_with_contracts_async(
        self, db: AsyncSession, asset_ids: list[str]
    ) -> list[str]:
        """批量获取有关联合同的资产 ID 列表"""
        if not asset_ids:
            return []
        from ..models.associations import contract_assets

        stmt = select(contract_assets.c.asset_id).where(
            contract_assets.c.asset_id.in_(asset_ids)
        )
        result = await db.execute(stmt)
        matched_asset_ids: list[str] = await _scalars_all(result)
        return [str(asset_id) for asset_id in matched_asset_ids]

    async def get_assets_with_property_certs_async(
        self, db: AsyncSession, asset_ids: list[str]
    ) -> list[str]:
        """批量获取有产权证关联的资产ID列表"""
        if not asset_ids:
            return []
        from ..models.associations import property_cert_assets

        stmt = select(property_cert_assets.c.asset_id).where(
            property_cert_assets.c.asset_id.in_(asset_ids)
        )
        result = await db.execute(stmt)
        matched_asset_ids: list[str] = await _scalars_all(result)
        return [str(asset_id) for asset_id in matched_asset_ids]

    async def get_assets_with_contract_ledger_entries_async(
        self, db: AsyncSession, asset_ids: list[str]
    ) -> list[str]:
        """批量获取有关联合同台账记录的资产 ID 列表"""
        if not asset_ids:
            return []
        from ..models.associations import contract_assets
        from ..models.contract_group import ContractLedgerEntry

        stmt = (
            select(contract_assets.c.asset_id)
            .distinct()
            .join(
                ContractLedgerEntry,
                ContractLedgerEntry.contract_id == contract_assets.c.contract_id,
            )
            .where(contract_assets.c.asset_id.in_(asset_ids))
        )
        result = await db.execute(stmt)
        matched_asset_ids: list[str] = await _scalars_all(result)
        return [str(asset_id) for asset_id in matched_asset_ids]

    async def get_by_asset_names_async(
        self,
        db: AsyncSession,
        asset_names: list[str],
        exclude_deleted: bool = True,
        decrypt: bool = False,
    ) -> list[Asset]:
        """批量获取资产（按属性名列表），用于导入去重检查"""
        if not asset_names:
            return []
        stmt = select(Asset).where(Asset.asset_name.in_(asset_names))
        if exclude_deleted:
            stmt = stmt.where(Asset.data_status != DataStatusValues.ASSET_DELETED)
        result = await db.execute(stmt)
        assets: list[Asset] = await _scalars_all(result)
        if decrypt:
            for asset in assets:
                self._decrypt_asset_object(asset)
        return assets

    async def count_by_ownership_async(self, db: AsyncSession, ownership_id: str) -> int:
        """统计权属方的资产数量"""
        stmt = select(func.count(Asset.id)).where(Asset.owner_party_id == ownership_id)
        result = await db.execute(stmt)
        count_raw = await _result_scalar(result)
        return int(cast(int | float | str, count_raw)) if count_raw is not None else 0

    async def get_counts_by_ownerships_async(
        self, db: AsyncSession, ownership_ids: list[str]
    ) -> dict[str, int]:
        """按权属方分组统计资产数量（返回 dict）"""
        if not ownership_ids:
            return {}
        stmt = (
            select(Asset.owner_party_id, func.count(Asset.id))
            .where(Asset.owner_party_id.in_(ownership_ids))
            .group_by(Asset.owner_party_id)
        )
        result = await db.execute(stmt)
        rows: list[tuple[object, object]] = await _result_all(result)
        return {
            str(ownership_id): (
                int(cast(int | float | str, count)) if count is not None else 0
            )
            for ownership_id, count in rows
            if ownership_id is not None
        }

    # remove is inherited
    # create is inherited (check notes about calculation)


# 创建全局实例
asset_crud = AssetCRUD()

__all__ = ["AssetCRUD", "SensitiveDataHandler", "asset_crud"]
