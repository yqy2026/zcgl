"""
资产管理服务模块

包含资产管理相关的所有服务：
- 资产计算服务
- 出租率计算服�?- 数据验证服务
- 历史追踪服务
"""

import logging

__all__ = []
logger = logging.getLogger(__name__)


def _log_import_error(service_name: str) -> None:
    logger.warning(f"Service import failed: {service_name}", exc_info=True)


try:
    from .asset_calculator import AssetCalculator, OccupancyRateCalculator  # noqa: F401

    __all__ += ["AssetCalculator", "OccupancyRateCalculator"]  # pragma: no cover
except Exception:  # nosec - B110: Intentional graceful degradation  # pragma: no cover
    _log_import_error("asset.asset_calculator.AssetCalculator")
