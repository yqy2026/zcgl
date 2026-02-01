"""
Analytics Services

统计分析服务层
"""

import logging
from typing import TYPE_CHECKING

__all__: list[str] = []
logger = logging.getLogger(__name__)


def _log_import_error(service_name: str) -> None:
    logger.warning(f"Service import failed: {service_name}", exc_info=True)


# 导入新创建的Analytics服务
try:
    from .occupancy_service import OccupancyService as OccupancyService

    __all__.append("OccupancyService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("analytics.occupancy_service.OccupancyService")

try:
    from .area_service import AreaService as AreaService

    __all__.append("AreaService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("analytics.area_service.AreaService")

try:
    from .analytics_service import AnalyticsService as AnalyticsService

    __all__.append("AnalyticsService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("analytics.analytics_service.AnalyticsService")

try:
    from .financial_service import FinancialService as FinancialService

    __all__.append("FinancialService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("analytics.financial_service.FinancialService")

# 保留对旧服务的导入尝试（如果存在的话）
try:
    from .statistics import StatisticsService as StatisticsService

    __all__.append("StatisticsService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("analytics.statistics.StatisticsService")

try:
    from .data_filter import DataFilterService as DataFilterService

    __all__.append("DataFilterService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("analytics.data_filter.DataFilterService")

# 类型检查导入
if TYPE_CHECKING:
    pass  # Types already imported above with explicit re-export
