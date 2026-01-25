"""
分布统计模块

提供资产分布统计端点:
- 产权分布 (ownership-distribution)
- 物业性质分布 (property-nature-distribution)
- 使用状态分布 (usage-status-distribution)
- 自定义字段分布 (asset-distribution) - 带字段验证

Created: 2026-01-17 (Phase 2 - Large File Splitting)
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ....crud.asset import asset_crud
from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....schemas.statistics import ChartDataItem, DistributionResponse
from ....security.security import FieldValidator

logger = logging.getLogger(__name__)

# 创建分布统计路由器
router = APIRouter()


@router.get(
    "/ownership-distribution",
    response_model=DistributionResponse,
    summary="获取权属分布统计",
)
async def get_ownership_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DistributionResponse:
    """
    获取按权属状态的资产分布统计

    返回资产在不同权属状态（已确权、未确权、部分确权）下的分布情况
    """
    # 获取总资产数
    assets: list[Any] = asset_crud.get_multi(db=db, skip=0, limit=10000)
    total_assets = len(assets)

    # 按权属状态分类统计
    confirmed_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"ownership_status": "已确权"}
    )
    confirmed_count = len(confirmed_assets)

    unconfirmed_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"ownership_status": "未确权"}
    )
    unconfirmed_count = len(unconfirmed_assets)

    partial_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"ownership_status": "部分确权"}
    )
    partial_count = len(partial_assets)

    # 构建分布数据
    distribution = [
        ChartDataItem(
            name="已确权",
            value=confirmed_count,
            percentage=(confirmed_count / total_assets * 100)
            if total_assets > 0
            else 0,
        ),
        ChartDataItem(
            name="未确权",
            value=unconfirmed_count,
            percentage=(unconfirmed_count / total_assets * 100)
            if total_assets > 0
            else 0,
        ),
        ChartDataItem(
            name="部分确权",
            value=partial_count,
            percentage=(partial_count / total_assets * 100) if total_assets > 0 else 0,
        ),
    ]

    return DistributionResponse(
        categories=distribution,
        total=total_assets,
    )


@router.get(
    "/property-nature-distribution",
    response_model=DistributionResponse,
    summary="获取物业性质分布统计",
)
async def get_property_nature_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DistributionResponse:
    """
    获取按物业性质的资产分布统计

    返回资产在不同物业性质（经营性、非经营性）下的分布情况
    """
    # 获取总资产数
    assets: list[Any] = asset_crud.get_multi(db=db, skip=0, limit=10000)
    total_assets = len(assets)

    # 按物业性质分类统计
    commercial_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"property_nature": "经营性"}
    )
    commercial_count = len(commercial_assets)

    non_commercial_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"property_nature": "非经营性"}
    )
    non_commercial_count = len(non_commercial_assets)

    # 构建分布数据
    distribution = [
        ChartDataItem(
            name="经营性",
            value=commercial_count,
            percentage=(commercial_count / total_assets * 100)
            if total_assets > 0
            else 0,
        ),
        ChartDataItem(
            name="非经营性",
            value=non_commercial_count,
            percentage=(non_commercial_count / total_assets * 100)
            if total_assets > 0
            else 0,
        ),
    ]

    return DistributionResponse(
        categories=distribution,
        total=total_assets,
    )


@router.get(
    "/usage-status-distribution",
    response_model=DistributionResponse,
    summary="获取使用状态分布统计",
)
async def get_usage_status_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DistributionResponse:
    """
    获取按使用状态的资产分布统计

    返回资产在不同使用状态（出租、空置、自用）下的分布情况
    """
    # 获取总资产数
    assets: list[Any] = asset_crud.get_multi(db=db, skip=0, limit=10000)
    total_assets = len(assets)

    # 按使用状态分类统计
    rented_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"usage_status": "出租"}
    )
    rented_count = len(rented_assets)

    vacant_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"usage_status": "空置"}
    )
    vacant_count = len(vacant_assets)

    self_used_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"usage_status": "自用"}
    )
    self_used_count = len(self_used_assets)

    # 构建分布数据
    distribution = [
        ChartDataItem(
            name="出租",
            value=rented_count,
            percentage=(rented_count / total_assets * 100) if total_assets > 0 else 0,
        ),
        ChartDataItem(
            name="空置",
            value=vacant_count,
            percentage=(vacant_count / total_assets * 100) if total_assets > 0 else 0,
        ),
        ChartDataItem(
            name="自用",
            value=self_used_count,
            percentage=(self_used_count / total_assets * 100)
            if total_assets > 0
            else 0,
        ),
    ]

    return DistributionResponse(
        categories=distribution,
        total=total_assets,
    )


@router.get("/asset-distribution", summary="获取资产分布统计")
async def get_asset_distribution(
    group_by: str = Query("ownership_status", description="分组字段"),
    should_include_deleted: bool = Query(False, description="是否包含已删除资产"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    获取资产分布统计数据（支持自定义分组字段）

    使用字段验证框架确保只允许查询白名单字段，防止 PII 泄露。

    Args:
        group_by: 分组字段（必须在 Asset 模型的 filter_fields 白名单中）
        include_deleted: 是否包含已删除的资产

    Returns:
        分布统计数据，包含各分组的数量和百分比

    Security:
        - 使用 FieldValidator 验证 group_by 字段
        - 阻止对 PII 字段（manager_name, tenant_name 等）的分组
        - 记录所有被阻止的访问尝试
    """
    # Phase 1 安全改进：字段验证
    # 这会自动检查字段是否在 Asset 模型的 filter_fields 白名单中
    FieldValidator.validate_group_by_field("Asset", group_by, raise_on_invalid=True)

    # 构建筛选条件
    filters: dict[str, Any] = {}
    if not should_include_deleted:
        filters["data_status"] = "正常"

    # 获取资产数据
    assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters=filters
    )

    # 按字段分组统计
    distribution: dict[str, Any] = {}
    total_assets = len(assets)

    for asset in assets:
        group_value = getattr(asset, group_by, None) or "未知"
        if group_value not in distribution:
            distribution[group_value] = 0
        distribution[group_value] += 1

    # 构建响应数据
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
