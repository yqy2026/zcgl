"""
资产管理服务模块

包含资产管理相关的所有服务：
- 资产计算服务
- 出租率计算服�?- 数据验证服务
- 历史追踪服务
"""

__all__ = []

try:
    from .asset_calculator import AssetCalculator, OccupancyRateCalculator

    __all__ += ["AssetCalculator", "OccupancyRateCalculator"]  # pragma: no cover
except Exception:  # nosec - B110: Intentional graceful degradation  # pragma: no cover
    pass
