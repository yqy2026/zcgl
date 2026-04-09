"""基础统计服务层。"""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.asset import asset_crud
from ...crud.query_builder import PartyFilter
from ...schemas.statistics import BasicStatisticsResponse
from ...utils.numeric import to_float


class BasicStatsService:
    """基础统计相关服务。"""

    @staticmethod
    def _build_basic_filters(
        ownership_status: str | None,
        property_nature: str | None,
        usage_status: str | None,
        ownership_id: str | None,
    ) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if ownership_status is not None:
            filters["ownership_status"] = ownership_status
        if property_nature is not None:
            filters["property_nature"] = property_nature
        if usage_status is not None:
            filters["usage_status"] = usage_status
        if ownership_id is not None:
            filters["ownership_id"] = ownership_id
        return filters

    async def calculate_basic_statistics(
        self,
        db: AsyncSession,
        *,
        ownership_status: str | None,
        property_nature: str | None,
        usage_status: str | None,
        ownership_id: str | None,
        party_filter: PartyFilter | None = None,
    ) -> BasicStatisticsResponse:
        filters = self._build_basic_filters(
            ownership_status,
            property_nature,
            usage_status,
            ownership_id,
        )

        assets, _ = await asset_crud.get_multi_with_search_async(
            db=db,
            skip=0,
            limit=10000,
            filters=filters,
            include_contract_projection=False,
            party_filter=party_filter,
        )
        total_assets = len(assets)

        if total_assets == 0:
            return BasicStatisticsResponse(
                total_assets=0,
                ownership_status={"confirmed": 0, "unconfirmed": 0, "partial": 0},
                property_nature={"commercial": 0, "non_commercial": 0},
                usage_status={"rented": 0, "self_used": 0, "vacant": 0},
                generated_at=datetime.now(),
                filters_applied=filters,
            )

        ownership_stats = {"confirmed": 0, "unconfirmed": 0, "partial": 0}
        property_stats = {"commercial": 0, "non_commercial": 0}
        usage_stats = {"rented": 0, "self_used": 0, "vacant": 0}

        for asset in assets:
            if getattr(asset, "ownership_status", None) == "已确权":
                ownership_stats["confirmed"] += 1
            elif getattr(asset, "ownership_status", None) == "未确权":
                ownership_stats["unconfirmed"] += 1
            elif getattr(asset, "ownership_status", None) == "部分确权":
                ownership_stats["partial"] += 1

            if getattr(asset, "property_nature", None) == "经营性":
                property_stats["commercial"] += 1
            elif getattr(asset, "property_nature", None) == "非经营性":
                property_stats["non_commercial"] += 1

            if getattr(asset, "usage_status", None) == "出租":
                usage_stats["rented"] += 1
            elif getattr(asset, "usage_status", None) == "自用":
                usage_stats["self_used"] += 1
            elif getattr(asset, "usage_status", None) == "空置":
                usage_stats["vacant"] += 1

        return BasicStatisticsResponse(
            total_assets=total_assets,
            ownership_status=ownership_stats,
            property_nature=property_stats,
            usage_status=usage_stats,
            generated_at=datetime.now(),
            filters_applied=filters,
        )

    async def calculate_comprehensive_statistics(
        self,
        db: AsyncSession,
        *,
        should_include_deleted: bool,
        party_filter: PartyFilter | None = None,
    ) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if not should_include_deleted:
            filters["data_status"] = "正常"

        assets, _ = await asset_crud.get_multi_with_search_async(
            db=db,
            skip=0,
            limit=10000,
            filters=filters,
            include_contract_projection=False,
            party_filter=party_filter,
        )

        total_assets = len(assets)
        total_land_area = sum(
            to_float(getattr(asset, "land_area"))
            for asset in assets
            if getattr(asset, "land_area", None)
        )
        total_rentable_area = sum(
            to_float(getattr(asset, "rentable_area"))
            for asset in assets
            if getattr(asset, "rentable_area", None)
        )
        total_rented_area = sum(
            to_float(getattr(asset, "rented_area"))
            for asset in assets
            if getattr(asset, "rented_area", None)
        )

        occupancy_rate = (
            (total_rented_area / total_rentable_area * 100)
            if total_rentable_area > 0
            else 0.0
        )

        comprehensive_data = {
            "total_assets": total_assets,
            "total_land_area": round(total_land_area, 2),
            "total_rentable_area": round(total_rentable_area, 2),
            "total_rented_area": round(total_rented_area, 2),
            "occupancy_rate": round(occupancy_rate, 2),
            "generated_at": datetime.now().isoformat(),
            "filters_applied": filters,
        }

        return {
            "success": True,
            "data": comprehensive_data,
            "message": "综合统计数据获取成功",
        }


basic_stats_service = BasicStatsService()


def get_basic_stats_service() -> BasicStatsService:
    return basic_stats_service
