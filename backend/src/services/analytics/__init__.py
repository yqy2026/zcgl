"""
Analytics Services

统计分析服务层
"""

from typing import TYPE_CHECKING

__all__: list[str] = []

# 导入新创建的Analytics服务
try:
    from .occupancy_service import OccupancyService as OccupancyService

    __all__.append("OccupancyService")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

try:
    from .area_service import AreaService as AreaService

    __all__.append("AreaService")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

try:
    from .analytics_service import AnalyticsService as AnalyticsService

    __all__.append("AnalyticsService")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

# 保留对旧服务的导入尝试（如果存在的话）
try:
    from .statistics import StatisticsService as StatisticsService

    __all__.append("StatisticsService")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

try:
    from .data_filter import DataFilterService as DataFilterService

    __all__.append("DataFilterService")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

# 类型检查导入
if TYPE_CHECKING:
    pass  # Types already imported above with explicit re-export
