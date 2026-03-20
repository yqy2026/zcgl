"""
资产查询服务

资产列表查询、单条获取、租赁汇总、变更历史、审核日志等只读查询逻辑。
"""

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...constants.business_constants import DataStatusValues
from ...core.exception_handler import ResourceNotFoundError
from ...crud.asset_management_history import asset_management_history_crud
from ...crud.contract import contract_crud
from ...crud.history import history_crud
from ...crud.ownership import ownership
from ...crud.project_asset import project_asset_crud
from ...crud.query_builder import PartyFilter
from ...models.asset import Asset
from ...models.asset_history import AssetHistory
from ...models.asset_review_log import AssetReviewLog
from ...models.contract_group import (
    ContractLifecycleStatus,
    GroupRelationType,
)
from ...schemas.asset import (
    AssetLeaseSummaryResponse,
    ContractPartyItem,
    ContractTypeSummary,
)
from ...services.party_scope import resolve_user_party_filter
from .asset_validation import _as_decimal, normalize_summary_period

logger = logging.getLogger(__name__)
ACTIVE_CONTRACT_STATUSES = {ContractLifecycleStatus.ACTIVE}


def _get_default_asset_crud() -> Any:
    from ...crud import asset as asset_module

    return asset_module.asset_crud


class AssetQueryService:
    """资产查询服务 — 所有只读查询方法。"""

    def __init__(
        self,
        db: AsyncSession,
        *,
        asset_crud_override: Any | None = None,
    ) -> None:
        self.db = db
        self.asset_crud = (
            asset_crud_override
            if asset_crud_override is not None
            else _get_default_asset_crud()
        )

    async def _resolve_party_filter(
        self,
        *,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> PartyFilter | None:
        return await resolve_user_party_filter(
            self.db,
            current_user_id=current_user_id,
            party_filter=party_filter,
            logger=logger,
            allow_legacy_default_organization_fallback=False,
        )

    @staticmethod
    def _is_fail_closed_party_filter(party_filter: PartyFilter | None) -> bool:
        if party_filter is None:
            return False
        return (
            len(
                [
                    org_id
                    for org_id in party_filter.party_ids
                    if str(org_id).strip() != ""
                ]
            )
            == 0
        )

    async def get_assets(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        filters: dict[str, Any] | None = None,
        sort_field: str = "created_at",
        sort_order: str = "desc",
        include_relations: bool = False,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> tuple[list[Asset], int]:
        asset_crud = self.asset_crud
        resolved_party_filter = await self._resolve_party_filter(
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            return ([], 0)
        query_kwargs: dict[str, Any] = {
            "skip": skip,
            "limit": limit,
            "search": search,
            "filters": filters,
            "sort_field": sort_field,
            "sort_order": sort_order,
            "include_relations": include_relations,
        }
        if resolved_party_filter is not None:
            query_kwargs["party_filter"] = resolved_party_filter
        result = cast(
            tuple[list[Asset], int],
            await asset_crud.get_multi_with_search_async(
                self.db,
                **query_kwargs,
            ),
        )
        return result

    async def get_assets_by_ids(
        self,
        ids: list[str],
        *,
        include_relations: bool = False,
    ) -> list[Asset]:
        """根据 ID 列表批量获取资产。"""
        asset_crud = self.asset_crud
        assets = cast(
            list[Asset],
            await asset_crud.get_multi_by_ids_async(
                db=self.db,
                ids=ids,
                include_relations=include_relations,
            ),
        )
        return assets

    async def get_asset(
        self,
        asset_id: str,
        *,
        use_cache: bool = True,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> Asset:
        asset_crud = self.asset_crud
        resolved_party_filter = await self._resolve_party_filter(
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            raise ResourceNotFoundError("Asset", asset_id)

        query_kwargs: dict[str, Any] = {
            "db": self.db,
            "id": asset_id,
            "use_cache": use_cache,
        }
        if resolved_party_filter is not None:
            query_kwargs["party_filter"] = resolved_party_filter
        asset = cast(
            Asset | None,
            await asset_crud.get_async(**query_kwargs),
        )
        if not asset or asset.data_status == DataStatusValues.ASSET_DELETED:
            raise ResourceNotFoundError("Asset", asset_id)
        return asset

    async def get_asset_lease_summary(
        self,
        asset_id: str,
        *,
        period_start: date | None = None,
        period_end: date | None = None,
        current_user_id: str | None = None,
    ) -> AssetLeaseSummaryResponse:
        period_start, period_end = normalize_summary_period(period_start, period_end)

        asset = await self.get_asset(asset_id, current_user_id=current_user_id)
        contracts = await contract_crud.get_active_by_asset_id(
            self.db,
            asset_id=asset_id,
            active_statuses=ACTIVE_CONTRACT_STATUSES,
        )

        type_buckets: dict[str, list[Any]] = defaultdict(list)
        for contract in contracts:
            relation_type = getattr(contract, "group_relation_type", None)
            key = (
                relation_type.value
                if isinstance(relation_type, GroupRelationType)
                else str(relation_type)
            )
            type_buckets[key].append(contract)

        by_type: list[ContractTypeSummary] = []
        for relation_type, label in (
            ("上游", "上游承租"),
            ("下游", "下游转租"),
            ("委托", "委托协议"),
            ("直租", "直租合同"),
        ):
            bucket = type_buckets.get(relation_type, [])
            monthly_amount = sum(
                (
                    _as_decimal(
                        getattr(contract.lease_detail, "monthly_rent_base", None)
                    )
                    for contract in bucket
                    if getattr(contract, "lease_detail", None) is not None
                ),
                start=Decimal("0"),
            )
            by_type.append(
                ContractTypeSummary(
                    group_relation_type=relation_type,
                    label=label,
                    contract_count=len(bucket),
                    total_area=0.0,
                    monthly_amount=float(monthly_amount),
                )
            )

        party_counter: dict[tuple[str, str], tuple[str | None, int]] = {}
        outbound_types = {
            GroupRelationType.DOWNSTREAM.value,
            GroupRelationType.DIRECT_LEASE.value,
        }
        for contract in contracts:
            relation_type = getattr(contract, "group_relation_type", None)
            relation_value = (
                relation_type.value
                if isinstance(relation_type, GroupRelationType)
                else str(relation_type)
            )
            if relation_value not in outbound_types:
                continue

            lease_detail = getattr(contract, "lease_detail", None)
            lessee_party = getattr(contract, "lessee_party", None)
            lessee_name = (
                getattr(lease_detail, "tenant_name", None)
                or getattr(lessee_party, "name", None)
                or "未知租户"
            )
            party_id = str(getattr(contract, "lessee_party_id", "")).strip() or None
            key = (lessee_name, relation_value)
            prev_party_id, prev_count = party_counter.get(key, (party_id, 0))
            party_counter[key] = (prev_party_id or party_id, prev_count + 1)

        customer_summary = [
            ContractPartyItem(
                party_id=party_id,
                party_name=party_name,
                group_relation_type=relation_type,
                contract_count=contract_count,
            )
            for (party_name, relation_type), (
                party_id,
                contract_count,
            ) in party_counter.items()
        ]

        rentable_area = _as_decimal(getattr(asset, "rentable_area", None))

        return AssetLeaseSummaryResponse(
            asset_id=str(getattr(asset, "id")),
            period_start=period_start,
            period_end=period_end,
            total_contracts=len(contracts),
            total_rented_area=0.0,
            rentable_area=float(rentable_area),
            occupancy_rate=0.0,
            by_type=by_type,
            customer_summary=customer_summary,
        )

    async def get_asset_history_records(
        self,
        asset_id: str,
        *,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> list[AssetHistory]:
        await self.get_asset(
            asset_id,
            party_filter=party_filter,
            current_user_id=current_user_id,
        )
        history_records = await history_crud.get_by_asset_id_async(
            self.db,
            asset_id=asset_id,
        )
        return history_records

    async def get_asset_management_history(
        self,
        asset_id: str,
        *,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> list:
        """获取资产经营方变更历史。"""
        await self.get_asset(
            asset_id,
            party_filter=party_filter,
            current_user_id=current_user_id,
        )
        return await asset_management_history_crud.get_by_asset_id(
            self.db,
            asset_id=asset_id,
        )

    async def get_asset_project_history(
        self,
        asset_id: str,
        *,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> list:
        """获取资产项目关联历史（含当前有效和已终止绑定）。"""
        await self.get_asset(
            asset_id,
            party_filter=party_filter,
            current_user_id=current_user_id,
        )
        return await project_asset_crud.get_asset_projects(
            self.db,
            asset_id=asset_id,
            active_only=False,
        )

    async def _list_asset_review_logs(self, asset_id: str) -> list[AssetReviewLog]:
        stmt = (
            select(AssetReviewLog)
            .where(AssetReviewLog.asset_id == asset_id)
            .order_by(AssetReviewLog.created_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_asset_review_logs(
        self,
        asset_id: str,
        *,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> list[AssetReviewLog]:
        await self.get_asset(
            asset_id,
            party_filter=party_filter,
            current_user_id=current_user_id,
        )
        return await self._list_asset_review_logs(asset_id)

    async def get_distinct_field_values(
        self,
        field_name: str,
        *,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> list[str]:
        asset_crud = self.asset_crud
        resolved_party_filter = await self._resolve_party_filter(
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            return []
        query_kwargs: dict[str, Any] = {}
        if resolved_party_filter is not None:
            query_kwargs["party_filter"] = resolved_party_filter
        values = await asset_crud.get_distinct_field_values(
            self.db, field_name, **query_kwargs
        )
        return [str(value) for value in values]

    async def get_ownership_entity_names(self) -> list[str]:
        """获取所有正常状态的权属方名称列表"""
        return await ownership.get_names_by_status_async(
            self.db, data_status=DataStatusValues.ASSET_NORMAL
        )
