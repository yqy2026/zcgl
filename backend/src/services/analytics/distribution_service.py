"""Distribution statistics service layer."""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.asset import asset_crud
from ...schemas.statistics import ChartDataItem, DistributionResponse
from ...security.security import FieldValidator


class DistributionService:
    """Service for distribution statistics routes."""

    async def get_ownership_distribution(
        self, db: AsyncSession
    ) -> DistributionResponse:
        assets, _ = await asset_crud.get_multi_with_search_async(
            db=db,
            skip=0,
            limit=10000,
            include_contract_projection=False,
        )
        total_assets = len(assets)

        confirmed_assets, _ = await asset_crud.get_multi_with_search_async(
            db=db,
            skip=0,
            limit=10000,
            filters={"ownership_status": "已确权"},
            include_contract_projection=False,
        )
        unconfirmed_assets, _ = await asset_crud.get_multi_with_search_async(
            db=db,
            skip=0,
            limit=10000,
            filters={"ownership_status": "未确权"},
            include_contract_projection=False,
        )
        partial_assets, _ = await asset_crud.get_multi_with_search_async(
            db=db,
            skip=0,
            limit=10000,
            filters={"ownership_status": "部分确权"},
            include_contract_projection=False,
        )

        def _pct(count: int) -> float:
            return (count / total_assets * 100) if total_assets > 0 else 0.0

        return DistributionResponse(
            categories=[
                ChartDataItem(
                    name="已确权",
                    value=len(confirmed_assets),
                    percentage=_pct(len(confirmed_assets)),
                ),
                ChartDataItem(
                    name="未确权",
                    value=len(unconfirmed_assets),
                    percentage=_pct(len(unconfirmed_assets)),
                ),
                ChartDataItem(
                    name="部分确权",
                    value=len(partial_assets),
                    percentage=_pct(len(partial_assets)),
                ),
            ],
            total=total_assets,
        )

    async def get_property_nature_distribution(
        self, db: AsyncSession
    ) -> DistributionResponse:
        assets, _ = await asset_crud.get_multi_with_search_async(
            db=db,
            skip=0,
            limit=10000,
            include_contract_projection=False,
        )
        total_assets = len(assets)

        commercial_assets, _ = await asset_crud.get_multi_with_search_async(
            db=db,
            skip=0,
            limit=10000,
            filters={"property_nature": "经营性"},
            include_contract_projection=False,
        )
        non_commercial_assets, _ = await asset_crud.get_multi_with_search_async(
            db=db,
            skip=0,
            limit=10000,
            filters={"property_nature": "非经营性"},
            include_contract_projection=False,
        )

        def _pct(count: int) -> float:
            return (count / total_assets * 100) if total_assets > 0 else 0.0

        return DistributionResponse(
            categories=[
                ChartDataItem(
                    name="经营性",
                    value=len(commercial_assets),
                    percentage=_pct(len(commercial_assets)),
                ),
                ChartDataItem(
                    name="非经营性",
                    value=len(non_commercial_assets),
                    percentage=_pct(len(non_commercial_assets)),
                ),
            ],
            total=total_assets,
        )

    async def get_usage_status_distribution(
        self, db: AsyncSession
    ) -> DistributionResponse:
        assets, _ = await asset_crud.get_multi_with_search_async(
            db=db,
            skip=0,
            limit=10000,
            include_contract_projection=False,
        )
        total_assets = len(assets)

        rented_assets, _ = await asset_crud.get_multi_with_search_async(
            db=db,
            skip=0,
            limit=10000,
            filters={"usage_status": "出租"},
            include_contract_projection=False,
        )
        vacant_assets, _ = await asset_crud.get_multi_with_search_async(
            db=db,
            skip=0,
            limit=10000,
            filters={"usage_status": "空置"},
            include_contract_projection=False,
        )
        self_used_assets, _ = await asset_crud.get_multi_with_search_async(
            db=db,
            skip=0,
            limit=10000,
            filters={"usage_status": "自用"},
            include_contract_projection=False,
        )

        def _pct(count: int) -> float:
            return (count / total_assets * 100) if total_assets > 0 else 0.0

        return DistributionResponse(
            categories=[
                ChartDataItem(
                    name="出租",
                    value=len(rented_assets),
                    percentage=_pct(len(rented_assets)),
                ),
                ChartDataItem(
                    name="空置",
                    value=len(vacant_assets),
                    percentage=_pct(len(vacant_assets)),
                ),
                ChartDataItem(
                    name="自用",
                    value=len(self_used_assets),
                    percentage=_pct(len(self_used_assets)),
                ),
            ],
            total=total_assets,
        )

    async def get_asset_distribution(
        self,
        db: AsyncSession,
        *,
        group_by: str,
        should_include_deleted: bool,
    ) -> dict[str, Any]:
        FieldValidator.validate_group_by_field("Asset", group_by, raise_on_invalid=True)

        filters: dict[str, Any] = {}
        if not should_include_deleted:
            filters["data_status"] = "正常"

        assets, _ = await asset_crud.get_multi_with_search_async(
            db=db,
            skip=0,
            limit=10000,
            filters=filters,
            include_contract_projection=False,
        )

        distribution: dict[str, int] = {}
        for asset in assets:
            group_value = getattr(asset, group_by, None) or "未知"
            distribution[group_value] = distribution.get(group_value, 0) + 1

        total_assets = len(assets)
        distribution_data = [
            {
                "name": key,
                "value": count,
                "percentage": round((count / total_assets * 100), 2)
                if total_assets > 0
                else 0,
            }
            for key, count in distribution.items()
        ]

        return {
            "success": True,
            "data": {
                "group_by": group_by,
                "distribution": distribution_data,
                "total_assets": total_assets,
                "generated_at": datetime.now().isoformat(),
                "filters_applied": filters,
            },
            "message": "资产分布统计数据获取成功",
        }


distribution_service = DistributionService()


def get_distribution_service() -> DistributionService:
    return distribution_service
