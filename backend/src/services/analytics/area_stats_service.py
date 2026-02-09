"""Area statistics service layer."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.asset import asset_crud
from ...schemas.statistics import AreaSummaryResponse
from ...utils.numeric import to_float
from .area_service import AreaService


class AreaStatsService:
    """Service for area-related statistics routes."""

    async def calculate_area_summary(
        self,
        db: AsyncSession,
        *,
        should_include_deleted: bool,
        should_use_aggregation: bool,
    ) -> AreaSummaryResponse:
        filters: dict[str, Any] = {}
        if not should_include_deleted:
            filters["data_status"] = "正常"

        area_service = AreaService(db)
        if should_use_aggregation:
            summary = await area_service.calculate_summary_with_aggregation(filters)
        else:
            summary = await area_service._calculate_summary_in_memory(filters)

        return AreaSummaryResponse(
            total_area=summary["total_land_area"],
            rentable_area=summary["total_rentable_area"],
            rented_area=summary["total_rented_area"],
            unrented_area=summary["total_unrented_area"],
            occupancy_rate=summary["overall_occupancy_rate"],
        )

    async def calculate_area_statistics(
        self,
        db: AsyncSession,
        *,
        ownership_status: str | None,
        property_nature: str | None,
        usage_status: str | None,
        should_include_deleted: bool,
    ) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if ownership_status:
            filters["ownership_status"] = ownership_status
        if property_nature:
            filters["property_nature"] = property_nature
        if usage_status:
            filters["usage_status"] = usage_status
        if not should_include_deleted:
            filters["data_status"] = "正常"

        assets, _ = await asset_crud.get_multi_with_search_async(
            db=db,
            skip=0,
            limit=10000,
            filters=filters,
            include_contract_projection=False,
        )

        total_land_area = 0.0
        total_rentable_area = 0.0
        total_rented_area = 0.0

        for asset in assets:
            if getattr(asset, "land_area", None):
                total_land_area += to_float(getattr(asset, "land_area"))
            if getattr(asset, "rentable_area", None):
                total_rentable_area += to_float(getattr(asset, "rentable_area"))
            if getattr(asset, "rented_area", None):
                total_rented_area += to_float(getattr(asset, "rented_area"))

        occupancy_rate = (
            (total_rented_area / total_rentable_area * 100)
            if total_rentable_area > 0
            else 0.0
        )

        return {
            "success": True,
            "data": {
                "total_land_area": round(total_land_area, 2),
                "total_rentable_area": round(total_rentable_area, 2),
                "total_rented_area": round(total_rented_area, 2),
                "total_unrented_area": round(total_rentable_area - total_rented_area, 2),
                "occupancy_rate": round(occupancy_rate, 2),
                "total_assets": len(assets),
                "filters_applied": filters,
            },
            "message": "面积统计数据获取成功",
        }


area_stats_service = AreaStatsService()


def get_area_stats_service() -> AreaStatsService:
    return area_stats_service
