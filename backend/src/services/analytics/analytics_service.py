"""
Analytics Service - 综合分析服务

重构目标: 将 analytics.py 中的业务逻辑迁移到服务层

包含:
- 综合统计分析
- 趋势分析
- 分布计算
- 缓存管理
"""

import asyncio
import logging
from collections import defaultdict
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from ...models.auth import User

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...constants.business_constants import DataStatusValues
from ...core.cache_manager import analytics_cache
from ...core.response_handler import ResponseHandler
from ...models.asset import Asset
from ...models.contract_group import (
    Contract,
    ContractGroup,
    ContractLifecycleStatus,
    GroupRelationType,
    RevenueMode,
)
from ...models.party import PartyReviewStatus

logger = logging.getLogger(__name__)

ANALYTICS_METRICS_VERSION = "req-ana-001-v1"


class AnalyticsService:
    """综合分析服务 - 提供统计分析核心功能"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache = analytics_cache
        self.response_handler = ResponseHandler()

    async def get_comprehensive_analytics(
        self,
        filters: dict[str, Any] | None = None,
        should_use_cache: bool = True,
        current_user: "User | None" = None,
    ) -> dict[str, Any]:
        """
        获取综合统计分析数据

        这是核心的分析方法，整合了多种统计维度

        Args:
            filters: 筛选条件
            should_use_cache: 是否使用缓存
            current_user: 当前用户（用于权限控制）

        Returns:
            包含多维度统计数据的字典
        """
        # 验证筛选条件
        validated_filters = self._validate_filters(filters or {})

        # 尝试从缓存获取
        cache_key = self._generate_cache_key(validated_filters)
        if should_use_cache:
            try:
                cached_result = await self._cache_get(cache_key)
            except Exception as e:
                logger.warning(f"缓存读取失败，继续回源计算: {e}", exc_info=True)
                cached_result = None
            if cached_result is not None:
                logger.info(f"从缓存返回分析结果: {cache_key}")
                return cast(dict[str, Any], cached_result)

        # 执行分析计算
        result = await self._calculate_analytics(validated_filters)

        # 存入缓存
        if should_use_cache:
            try:
                await self._cache_set(cache_key, result, ttl=3600)
            except Exception as e:
                logger.warning(f"缓存写入失败，不影响本次返回: {e}", exc_info=True)

        return result

    def _validate_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        """验证和规范化筛选条件"""
        # 实现验证逻辑
        validated = {}

        if "include_deleted" in filters:
            validated["include_deleted"] = bool(filters["include_deleted"])

        if "date_from" in filters:
            validated["date_from"] = filters["date_from"]

        if "date_to" in filters:
            validated["date_to"] = filters["date_to"]

        return validated

    @staticmethod
    def _build_asset_status_filters(include_deleted: bool) -> dict[str, Any]:
        """
        构建资产状态筛选条件。

        说明：
        QueryBuilder 会在未显式传入 data_status 过滤时自动追加
        `data_status != "已删除"` 软删条件。为确保 include_deleted=true 生效，
        这里显式传入 data_status 相关过滤，避免被默认软删规则覆盖。
        """
        if include_deleted:
            return {
                "data_status__in": [
                    DataStatusValues.ASSET_NORMAL,
                    DataStatusValues.ASSET_ABNORMAL,
                    DataStatusValues.ASSET_DELETED,
                    DataStatusValues.ASSET_ARCHIVED,
                ]
            }
        return {"data_status": DataStatusValues.ASSET_NORMAL}

    def _generate_cache_key(self, filters: dict[str, Any]) -> str:
        """生成缓存键"""
        # 简化版本：基于筛选条件生成键
        import hashlib
        import json

        filter_str = json.dumps(filters, sort_keys=True)
        return f"analytics:{hashlib.md5(filter_str.encode(), usedforsecurity=False).hexdigest()}"

    async def _calculate_analytics(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        执行核心分析计算

        这里整合了:
        - 资产总数
        - 面积统计
        - 出租率统计
        - 财务数据
        - 分布数据
        """
        # 获取基础数据
        from ...crud.asset import asset_crud

        query_filters = self._build_asset_status_filters(
            include_deleted=filters.get("include_deleted", False)
        )

        assets, _ = await asset_crud.get_multi_with_search_async(
            db=self.db,
            skip=0,
            limit=10000,
            filters=query_filters,
            include_contract_projection=False,
        )

        # 计算各项统计
        stats = {
            "total_assets": len(assets),
            "timestamp": datetime.now().isoformat(),
        }

        # 添加面积统计（使用已有的 AreaService）
        from .area_service import AreaService
        from .occupancy_service import OccupancyService

        area_service = AreaService(self.db)
        occupancy_service = OccupancyService(self.db)

        # 面积汇总
        area_stats = await area_service.calculate_summary_with_aggregation(
            filters=filters
        )
        stats["area_summary"] = area_stats

        # 出租率统计
        occupancy_stats = await occupancy_service.calculate_with_aggregation(
            filters=filters
        )
        stats["occupancy_rate"] = occupancy_stats

        active_contracts = await self._list_active_contracts(filters)
        stats.update(self._calculate_operational_metrics(active_contracts))

        return stats

    async def _list_active_contracts(self, filters: dict[str, Any]) -> list[Contract]:
        stmt = (
            select(Contract)
            .where(
                Contract.status == ContractLifecycleStatus.ACTIVE,
                Contract.data_status == "正常",
            )
            .options(
                selectinload(Contract.contract_group).selectinload(
                    ContractGroup.operator_party
                ),
                selectinload(Contract.contract_group).selectinload(
                    ContractGroup.owner_party
                ),
                selectinload(Contract.lease_detail),
                selectinload(Contract.agency_detail),
                selectinload(Contract.lessor_party),
                selectinload(Contract.lessee_party),
            )
        )

        date_from = self._safe_parse_date(filters.get("date_from"))
        date_to = self._safe_parse_date(filters.get("date_to"))
        if date_from is not None or date_to is not None:
            overlap_clauses: list[Any] = []
            if date_to is not None:
                overlap_clauses.append(Contract.effective_from <= date_to)
            if date_from is not None:
                overlap_clauses.append(
                    or_(
                        Contract.effective_to.is_(None),
                        Contract.effective_to >= date_from,
                    )
                )
            if len(overlap_clauses) > 0:
                stmt = stmt.where(and_(*overlap_clauses))

        return list((await self.db.execute(stmt)).scalars().unique().all())

    def _calculate_operational_metrics(
        self, contracts: list[Contract]
    ) -> dict[str, Any]:
        self_operated_rent_income = Decimal("0")
        agency_service_income = Decimal("0")
        customer_party_ids: set[str] = set()
        customer_contract_ids: set[str] = set()

        agency_group_ratios: dict[str, Decimal] = {}
        for contract in contracts:
            group = getattr(contract, "contract_group", None)
            if (
                group is None
                or getattr(group, "revenue_mode", None) != RevenueMode.AGENCY
            ):
                continue
            if (
                getattr(contract, "group_relation_type", None)
                != GroupRelationType.ENTRUSTED
            ):
                continue
            agency_detail = getattr(contract, "agency_detail", None)
            if agency_detail is None:
                continue
            group_id = self._resolve_contract_group_id(contract, group)
            if group_id == "":
                continue
            agency_group_ratios[group_id] = self._to_decimal(
                getattr(agency_detail, "service_fee_ratio", None)
            )

        for contract in contracts:
            if not self._is_contract_statistically_eligible(contract):
                continue

            group = getattr(contract, "contract_group", None)
            if group is None:
                continue

            relation_type = getattr(contract, "group_relation_type", None)
            group_mode = getattr(group, "revenue_mode", None)

            if (
                group_mode == RevenueMode.LEASE
                and relation_type == GroupRelationType.DOWNSTREAM
            ):
                lease_detail = getattr(contract, "lease_detail", None)
                if lease_detail is not None:
                    self_operated_rent_income += self._to_decimal(
                        getattr(lease_detail, "rent_amount", None)
                    )
                lessee_party_id = str(getattr(contract, "lessee_party_id", "")).strip()
                if lessee_party_id != "":
                    customer_party_ids.add(lessee_party_id)
                customer_contract_ids.add(
                    str(getattr(contract, "contract_id", "")).strip()
                )

            if (
                group_mode == RevenueMode.AGENCY
                and relation_type == GroupRelationType.DIRECT_LEASE
            ):
                lease_detail = getattr(contract, "lease_detail", None)
                if lease_detail is not None:
                    group_id = self._resolve_contract_group_id(contract, group)
                    ratio = agency_group_ratios.get(group_id, Decimal("0"))
                    agency_service_income += self._quantize_money(
                        self._to_decimal(getattr(lease_detail, "rent_amount", None))
                        * ratio
                    )
                lessee_party_id = str(getattr(contract, "lessee_party_id", "")).strip()
                if lessee_party_id != "":
                    customer_party_ids.add(lessee_party_id)
                customer_contract_ids.add(
                    str(getattr(contract, "contract_id", "")).strip()
                )

        total_income = self._quantize_money(
            self_operated_rent_income + agency_service_income
        )
        return {
            "total_income": float(total_income),
            "self_operated_rent_income": float(
                self._quantize_money(self_operated_rent_income)
            ),
            "agency_service_income": float(self._quantize_money(agency_service_income)),
            "customer_entity_count": len(customer_party_ids),
            "customer_contract_count": len(
                [
                    contract_id
                    for contract_id in customer_contract_ids
                    if contract_id != ""
                ]
            ),
            "metrics_version": ANALYTICS_METRICS_VERSION,
        }

    @staticmethod
    def _is_party_approved(party: Any) -> bool:
        if party is None:
            return False
        return getattr(party, "review_status", None) == PartyReviewStatus.APPROVED.value

    def _is_contract_statistically_eligible(self, contract: Contract) -> bool:
        if getattr(contract, "status", None) != ContractLifecycleStatus.ACTIVE:
            return False
        if getattr(contract, "data_status", None) != "正常":
            return False

        group = getattr(contract, "contract_group", None)
        if group is None or getattr(group, "data_status", "正常") != "正常":
            return False

        return all(
            (
                self._is_party_approved(getattr(contract, "lessor_party", None)),
                self._is_party_approved(getattr(contract, "lessee_party", None)),
                self._is_party_approved(getattr(group, "operator_party", None)),
                self._is_party_approved(getattr(group, "owner_party", None)),
            )
        )

    @staticmethod
    def _resolve_contract_group_id(
        contract: Contract, group: ContractGroup | None
    ) -> str:
        raw_direct_group_id = getattr(contract, "contract_group_id", None)
        if isinstance(raw_direct_group_id, str):
            direct_group_id = raw_direct_group_id.strip()
            if direct_group_id != "":
                return direct_group_id
        if group is None:
            return ""
        return str(getattr(group, "contract_group_id", "")).strip()

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        if value is None:
            return Decimal("0")
        return Decimal(str(value))

    @staticmethod
    def _quantize_money(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _safe_parse_date(value: Any) -> date | None:
        if value is None:
            return None
        try:
            normalized = str(value).strip()
            if normalized == "":
                return None
            return date.fromisoformat(normalized)
        except ValueError:
            return None

    async def clear_cache(self) -> dict[str, Any]:
        """清除分析缓存"""
        # CacheManager 使用 clear() 方法，支持 pattern 参数
        try:
            cleared = await self._cache_clear("*")
            return {
                "status": "success",
                "cleared_keys": 1 if cleared else 0,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"缓存清理失败: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "cleared_keys": 0,
                "timestamp": datetime.now().isoformat(),
            }

    async def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cache_type": "analytics_cache_shared_backend",
            "stats": await self._cache_stats(),
            "timestamp": datetime.now().isoformat(),
        }

    async def _cache_get(self, key: str) -> Any:
        return await asyncio.to_thread(self.cache.get, key)

    async def _cache_set(self, key: str, value: Any, ttl: int) -> None:
        await asyncio.to_thread(self.cache.set, key, value, ttl=ttl)

    async def _cache_clear(self, pattern: str) -> Any:
        return await asyncio.to_thread(self.cache.clear, pattern=pattern)

    async def _cache_stats(self) -> dict[str, Any]:
        if hasattr(self.cache, "get_stats"):
            return await asyncio.to_thread(self.cache.get_stats)
        return {}

    async def calculate_trend(
        self,
        trend_type: str,
        time_dimension: str = "monthly",
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        计算趋势数据

        Args:
            trend_type: 趋势类型 (occupancy, area, financial)
            time_dimension: 时间维度 (daily, weekly, monthly, quarterly, yearly)
            filters: 筛选条件

        Returns:
            趋势数据列表
        """
        # 获取资产数据
        from ...crud.asset import asset_crud

        include_deleted = (
            bool(filters.get("include_deleted", False)) if filters else False
        )
        query_filters = self._build_asset_status_filters(
            include_deleted=include_deleted
        )

        assets, _ = await asset_crud.get_multi_with_search_async(
            db=self.db,
            skip=0,
            limit=10000,
            filters=query_filters,
            include_contract_projection=False,
        )

        # 根据趋势类型和维度生成数据
        if trend_type == "occupancy":
            return self._generate_occupancy_trend(assets, time_dimension)
        elif trend_type == "area":
            return self._generate_area_trend(assets, time_dimension)
        else:
            return []

    def _generate_occupancy_trend(
        self, assets: list[Asset], time_dimension: str
    ) -> list[dict[str, Any]]:
        """生成出租率趋势"""
        # 简化实现：返回模拟趋势数据
        # 实际实现应该根据合同日期等计算真实趋势
        return [
            {
                "period": "2024-01",
                "occupancy_rate": 0.85,
                "rented_area": 5000.0,
                "total_area": 5882.35,
            },
            {
                "period": "2024-02",
                "occupancy_rate": 0.87,
                "rented_area": 5100.0,
                "total_area": 5862.07,
            },
        ]

    def _generate_area_trend(
        self, assets: list[Asset], time_dimension: str
    ) -> list[dict[str, Any]]:
        """生成面积趋势"""
        # 简化实现
        return [
            {
                "period": "2024-01",
                "total_land_area": 6000.0,
                "total_rentable_area": 5882.35,
            },
            {
                "period": "2024-02",
                "total_land_area": 6100.0,
                "total_rentable_area": 5900.0,
            },
        ]

    async def calculate_distribution(
        self,
        distribution_type: str,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        计算分布数据

        Args:
            distribution_type: 分布类型 (property_nature, business_category, usage_status)
            filters: 筛选条件

        Returns:
            分布数据
        """
        # Security: Whitelist of allowed distribution fields to prevent arbitrary field access
        allowed_distribution_fields = {
            "property_nature",
            "business_category",
            "usage_status",
            "ownership_status",
            "manager_name",
            "revenue_mode",
            "operation_status",
            "project_name",
        }

        if distribution_type not in allowed_distribution_fields:
            from ...core.exception_handler import bad_request

            raise bad_request(
                f"无效的分布类型: {distribution_type}",
                details=f"允许的类型: {', '.join(sorted(allowed_distribution_fields))}",
            )

        from ...crud.asset import asset_crud

        include_deleted = (
            bool(filters.get("include_deleted", False)) if filters else False
        )
        query_filters = self._build_asset_status_filters(
            include_deleted=include_deleted
        )

        assets, _ = await asset_crud.get_multi_with_search_async(
            db=self.db,
            skip=0,
            limit=10000,
            filters=query_filters,
            include_contract_projection=False,
        )

        # 统计分布
        distribution: defaultdict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "area": 0.0}
        )

        for asset in assets:
            key = str(getattr(asset, distribution_type, "unknown"))
            distribution[key]["count"] += 1
            if asset.rentable_area:
                distribution[key]["area"] += float(asset.rentable_area)

        return {
            "distribution_type": distribution_type,
            "data": dict(distribution),
            "total": len(distribution),
        }
