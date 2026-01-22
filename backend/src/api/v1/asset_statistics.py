"""
资产统计API路由模块

从 assets.py 中提取的统计相关端点
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ...core.exception_handler import internal_error
from ...core.route_guards import debug_only
from ...database import get_db
from ...middleware.auth import get_current_active_user
from ...models.asset import Asset
from ...models.auth import User
from ...utils.numeric import to_float

# 创建统计路由器
router = APIRouter()

# 获取 logger（如果需要的话，可以配置专门的 logger）
import logging

logger = logging.getLogger(__name__)


@router.get("/test", summary="测试统计API")
@debug_only
async def test_statistics(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> dict[str, Any]:
    """
    简单的统计测试API
    """
    try:
        logger.debug("测试统计API开始")

        # 简单测试查询
        total_assets = db.query(Asset).count()

        return {
            "success": True,
            "message": "测试成功",
            "total_assets": total_assets,
            "timestamp": "2024-01-01T00:00:00Z",
        }

    except Exception as e:
        logger.error(f"测试统计API失败: {e}")
        import traceback

        logger.error(f"详细错误: {traceback.format_exc()}")
        raise internal_error(f"测试失败: {str(e)}")


@router.get("/summary", summary="获取资产统计摘要")
async def get_asset_statistics(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> dict[str, Any]:
    """
    获取资产统计摘要信息
    """
    try:
        # 添加调试信息
        logger.debug(
            f"开始执行资产统计查询，"
            f"用户: {current_user.username if current_user else 'unknown'}"
        )

        # 检查数据库连接是否正常
        try:
            db.execute(text("SELECT 1"))
        except Exception as e:
            logger.error(f"数据库连接检查失败: {e}")
            raise internal_error("数据库连接失败")

        # 总资产数 - 直接查询避免缓存问题
        total_assets = db.query(Asset).count()
        logger.debug(f"总资产数: {total_assets}")

        # 按确权状态统计 - 使用精确匹配
        confirmed_count = (
            db.query(Asset).filter(Asset.ownership_status == "已确权").count()
        )
        unconfirmed_count = (
            db.query(Asset).filter(Asset.ownership_status == "未确权").count()
        )
        partial_count = (
            db.query(Asset).filter(Asset.ownership_status == "部分确权").count()
        )

        # 按物业性质统计 - 使用精确匹配和模糊查询结合
        commercial_count = (
            db.query(Asset)
            .filter(
                (Asset.property_nature == "经营性")
                | (Asset.property_nature == "经营类")
                | (Asset.property_nature.like("%经营性%"))
            )
            .count()
        )
        non_commercial_count = (
            db.query(Asset).filter(Asset.property_nature == "非经营类").count()
        )

        # 按使用状态统计 - 使用数据库中实际的状态值
        rented_count = db.query(Asset).filter(Asset.usage_status == "出租").count()
        self_used_count = db.query(Asset).filter(Asset.usage_status == "自用").count()
        vacant_count = (
            db.query(Asset).filter(Asset.usage_status == "闲置").count()
        )  # 修复：数据库中是"闲置"而不是"空置"

        # 获取面积统计数据
        area_result = (
            db.query(Asset)
            .filter(Asset.data_status == "正常")
            .with_entities(
                func.sum(Asset.land_area).label("total_land_area"),
                func.sum(Asset.rentable_area).label("total_rentable_area"),
                func.sum(Asset.rented_area).label("total_rented_area"),
                func.sum(Asset.non_commercial_area).label("total_non_commercial_area"),
            )
            .first()
        )

        # 安全处理 area_result 可能为 None 的情况
        if area_result is None:
            total_land_area = 0.0
            total_rentable_area = 0.0
            total_rented_area = 0.0
            total_non_commercial_area = 0.0
        else:
            # 使用共享的 to_float 函数进行数值转换
            total_land_area = to_float(area_result.total_land_area)
            total_rentable_area = to_float(area_result.total_rentable_area)
            total_rented_area = to_float(area_result.total_rented_area)
            total_non_commercial_area = to_float(area_result.total_non_commercial_area)

        # 计算未出租面积（可出租面积 - 已出租面积）
        total_unrented_area = max(total_rentable_area - total_rented_area, 0.0)

        # 计算有面积数据的资产数
        assets_with_area = (
            db.query(Asset)
            .filter(
                Asset.data_status == "正常",
                (Asset.land_area.isnot(None)) | (Asset.rentable_area.isnot(None)),
            )
            .count()
        )

        # 计算整体出租率
        overall_occupancy_rate = 0.0
        if total_rentable_area > 0:
            overall_occupancy_rate = (total_rented_area / total_rentable_area) * 100

        return {
            "total_assets": total_assets,
            "ownership_status": {
                "confirmed": confirmed_count,
                "unconfirmed": unconfirmed_count,
                "partial": partial_count,
            },
            "property_nature": {
                "commercial": commercial_count,
                "non_commercial": non_commercial_count,
            },
            "usage_status": {
                "rented": rented_count,
                "self_used": self_used_count,
                "vacant": vacant_count,
            },
            # 添加面积统计数据
            "total_land_area": total_land_area,
            "total_rentable_area": total_rentable_area,
            "total_rented_area": total_rented_area,
            "total_unrented_area": total_unrented_area,
            "total_non_commercial_area": total_non_commercial_area,
            "assets_with_area_data": assets_with_area,
            "overall_occupancy_rate": overall_occupancy_rate,
        }

    except Exception as e:
        # 记录详细的错误信息用于调试
        import traceback

        error_detail = traceback.format_exc()
        logger.error(f"资产统计查询失败: {str(e)}")
        logger.error(f"详细错误信息: {error_detail}")
        raise internal_error(f"获取统计信息失败: {str(e)}. 请检查数据库连接和表结构。")


@router.get("/area-summary", summary="获取资产面积统计摘要")
async def get_asset_area_statistics(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> dict[str, Any]:
    """
    获取资产面积统计摘要信息
    """
    try:
        # 获取所有正常状态的资产
        assets_query = db.query(Asset).filter(Asset.data_status == "正常")

        # 计算总面积数据
        total_result = assets_query.with_entities(
            func.sum(Asset.land_area).label("total_land_area"),
            func.sum(Asset.rentable_area).label("total_rentable_area"),
            func.sum(Asset.rented_area).label("total_rented_area"),
            func.sum(Asset.non_commercial_area).label("total_non_commercial_area"),
            func.count(Asset.id).label("total_assets"),
        ).first()

        # 安全处理 total_result 可能为 None 的情况
        if total_result is None:
            total_land_area = 0.0
            total_rentable_area = 0.0
            total_rented_area = 0.0
            total_non_commercial_area = 0.0
            total_assets = 0
        else:
            # 使用共享的 to_float 函数进行数值转换
            total_land_area = to_float(total_result.total_land_area)
            total_rentable_area = to_float(total_result.total_rentable_area)
            total_rented_area = to_float(total_result.total_rented_area)
            total_non_commercial_area = to_float(total_result.total_non_commercial_area)
            total_assets = (
                int(total_result.total_assets) if total_result.total_assets else 0
            )

        # 计算未出租面积（可出租面积 - 已出租面积）
        total_unrented_area = max(total_rentable_area - total_rented_area, 0.0)

        # 计算有面积数据的资产数
        assets_with_area = assets_query.filter(
            (Asset.land_area.isnot(None)) | (Asset.rentable_area.isnot(None))
        ).count()

        # 计算整体出租率
        overall_occupancy_rate = 0.0
        if total_rentable_area > 0:
            overall_occupancy_rate = (total_rented_area / total_rentable_area) * 100

        return {
            "total_assets": total_assets,
            "total_land_area": total_land_area,
            "total_rentable_area": total_rentable_area,
            "total_rented_area": total_rented_area,
            "total_unrented_area": total_unrented_area,
            "total_non_commercial_area": total_non_commercial_area,
            "assets_with_area_data": assets_with_area,
            "overall_occupancy_rate": overall_occupancy_rate,
        }
    except Exception as e:
        # 记录详细的错误信息用于调试
        import traceback

        error_detail = traceback.format_exc()
        logger.error(f"面积统计查询失败: {str(e)}")
        logger.error(f"详细错误信息: {error_detail}")
        raise internal_error(
            f"获取面积统计信息失败: {str(e)}. 请检查数据库连接和表结构。"
        )
