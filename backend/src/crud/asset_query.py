"""
资产CRUD操作 — 查询/聚合方法 (mixin).

从 asset.py 拆分，用于可维护性。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, cast

from sqlalchemy import Float, Select, case, func, or_, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.ext.asyncio import AsyncSession

from ..constants.business_constants import DataStatusValues, DateTimeFields
from ..core.search_index import build_asset_id_subquery
from ..models.asset import Asset
from ..models.party import Party
from .asset_support import (
    AssetFilterData,
    _result_all,
    _result_first,
    _result_scalar,
    _scalars_all,
    _scalars_first,
)

if TYPE_CHECKING:
    from .asset import (
        AreaSummaryAggregationRow,
        OccupancyAggregationRow,
        OccupancyCategoryAggregationRow,
    )
    from .query_builder import PartyFilter

TSelectRow = TypeVar("TSelectRow", bound=tuple[Any, ...])


class AssetQueryMixin:
    """资产查询/聚合方法 mixin — 列表查询、分析统计、has_* 检查、批量查找。"""

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

    async def get_by_name_async(
        self,
        db: AsyncSession,
        asset_name: str,
        include_deleted: bool = False,
    ) -> Asset | None:
        stmt = (
            select(Asset)
            .options(
                *self._asset_projection_load_options()  # type: ignore[attr-defined]
            )
            .filter(Asset.asset_name == asset_name)
        )
        if not include_deleted:
            stmt = stmt.filter(
                self._not_deleted_clause(Asset.data_status)  # type: ignore[attr-defined]
            )

        result = await db.execute(stmt)
        asset: Asset | None = await _scalars_first(result)
        if asset is not None:
            self._decrypt_asset_object(asset)  # type: ignore[attr-defined]
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
        qb_filters = self._normalize_filters(filters)  # type: ignore[attr-defined]
        normalized_sort_field = self._normalize_sort_field(sort_field)  # type: ignore[attr-defined]

        non_pii_search_fields = ["asset_name", "business_category"]
        pii_search_fields = ["address"]
        search_conditions: list[Any] | None = None
        if search:
            search_conditions = []
            for field in non_pii_search_fields:
                if self.query_builder.whitelist.can_search(field) and hasattr(  # type: ignore[attr-defined]
                    Asset, field
                ):
                    search_conditions.append(getattr(Asset, field).ilike(f"%{search}%"))

            for field in pii_search_fields:
                if self.query_builder.whitelist.can_search(field) and hasattr(  # type: ignore[attr-defined]
                    Asset, field
                ):
                    if self.sensitive_data_handler.encryption_enabled:  # type: ignore[attr-defined]
                        subquery = build_asset_id_subquery(
                            field_name=field,
                            search_text=search,
                            key_manager=self.sensitive_data_handler.encryptor.key_manager,  # type: ignore[attr-defined]
                        )
                        if subquery is not None:
                            search_conditions.append(Asset.id.in_(subquery))
                        else:
                            encrypted = self.sensitive_data_handler.encrypt_field(  # type: ignore[attr-defined]
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
            self._asset_base_query_with_relations(  # type: ignore[attr-defined]
                include_contract_projection=include_contract_projection
            )
            if include_relations
            else select(Asset).options(
                *self._asset_projection_load_options(  # type: ignore[attr-defined]
                    include_contract_projection=include_contract_projection
                )
            )
        )
        if search_conditions:
            base_query = base_query.join(
                Party, Asset.owner_party_id == Party.id, isouter=True
            )
        if party_filter is not None:
            base_query = await self._apply_asset_party_filter(  # type: ignore[attr-defined]
                db,
                base_query,
                party_filter,
            )
        query: Select[Any] = self.query_builder.build_query(  # type: ignore[attr-defined]
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
            count_base_query = await self._apply_asset_party_filter(  # type: ignore[attr-defined]
                db,
                count_base_query,
                party_filter,
            )

        cnt_query = self.query_builder.build_count_query(  # type: ignore[attr-defined]
            filters=qb_filters,
            search_conditions=search_conditions,
            base_query=count_base_query,
            distinct_column=Asset.id,
        )
        total_result = await db.execute(cnt_query)
        total_raw = await _result_scalar(total_result)
        total = int(cast(int | float | str, total_raw)) if total_raw is not None else 0

        for asset in assets:
            self._decrypt_asset_object(asset)  # type: ignore[attr-defined]

        return assets, total

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
            self._asset_base_query_with_relations()  # type: ignore[attr-defined]
            if include_relations
            else select(Asset).options(
                *self._asset_projection_load_options()  # type: ignore[attr-defined]
            )
        )
        query = base_query.where(Asset.id.in_(ids))
        if not include_deleted:
            query = query.where(
                self._not_deleted_clause(Asset.data_status)  # type: ignore[attr-defined]
            )

        result = await db.execute(query)
        assets: list[Asset] = await _scalars_all(result)
        if decrypt:
            for asset in assets:
                self._decrypt_asset_object(asset)  # type: ignore[attr-defined]
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
            stmt = stmt.where(
                self._not_deleted_clause(Asset.data_status)  # type: ignore[attr-defined]
            )

        result = await db.execute(stmt.limit(limit))
        assets: list[Asset] = await _scalars_all(result)
        if decrypt:
            for asset in assets:
                self._decrypt_asset_object(asset)  # type: ignore[attr-defined]
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

        handler = self.sensitive_data_handler  # type: ignore[attr-defined]
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
            stmt = stmt.where(
                self._not_deleted_clause(Asset.data_status)  # type: ignore[attr-defined]
            )

        result = await db.execute(stmt.limit(limit))
        assets: list[Asset] = await _scalars_all(result)
        if decrypt:
            for asset in assets:
                self._decrypt_asset_object(asset)  # type: ignore[attr-defined]
        return assets, used_blind_index

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
        agg_stmt = stmt.with_only_columns(
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
            sql_cast(
                func.sum(func.coalesce(Asset.non_commercial_area, 0)), Float
            ).label("total_non_commercial_area"),
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

    async def has_property_certs_async(self, db: AsyncSession, asset_id: str) -> bool:
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
                self._decrypt_asset_object(asset)  # type: ignore[attr-defined]
        return assets

    async def count_by_ownership_async(
        self, db: AsyncSession, ownership_id: str
    ) -> int:
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
