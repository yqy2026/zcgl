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
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.params import Depends as DependsParam
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.middleware.auth import get_current_active_user
from src.models.auth import User
from src.schemas.statistics import DistributionResponse
from src.services.analytics.distribution_service import (
    DistributionService,
    get_distribution_service,
)

logger = logging.getLogger(__name__)

# 创建分布统计路由器
router = APIRouter()


def _resolve_service(
    service: DistributionService | Any,
) -> DistributionService | Any:
    if isinstance(service, DependsParam):
        return get_distribution_service()
    return service


@router.get(
    "/ownership-distribution",
    response_model=DistributionResponse,
    summary="获取权属分布统计",
)
async def get_ownership_distribution(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: DistributionService = Depends(get_distribution_service),
) -> DistributionResponse:
    """
    获取按权属状态的资产分布统计

    返回资产在不同权属状态（已确权、未确权、部分确权）下的分布情况
    """
    _ = current_user
    resolved_service = _resolve_service(service)
    return await resolved_service.get_ownership_distribution(db=db)


@router.get(
    "/property-nature-distribution",
    response_model=DistributionResponse,
    summary="获取物业性质分布统计",
)
async def get_property_nature_distribution(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: DistributionService = Depends(get_distribution_service),
) -> DistributionResponse:
    """
    获取按物业性质的资产分布统计
    返回资产在不同物业性质（经营性、非经营性）下的分布情况
    """
    _ = current_user
    resolved_service = _resolve_service(service)
    return await resolved_service.get_property_nature_distribution(db=db)


@router.get(
    "/usage-status-distribution",
    response_model=DistributionResponse,
    summary="获取使用状态分布统计",
)
async def get_usage_status_distribution(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: DistributionService = Depends(get_distribution_service),
) -> DistributionResponse:
    """
    获取按使用状态的资产分布统计

    返回资产在不同使用状态（出租、空置、自用）下的分布情况
    """
    _ = current_user
    resolved_service = _resolve_service(service)
    return await resolved_service.get_usage_status_distribution(db=db)


@router.get("/asset-distribution", summary="获取资产分布统计")
async def get_asset_distribution(
    group_by: str = Query("ownership_status", description="分组字段"),
    should_include_deleted: bool = Query(False, description="是否包含已删除资产"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: DistributionService = Depends(get_distribution_service),
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
        - 阻止 PII 字段（manager_name, tenant_name 等）的分析
        - 记录所有被阻止的访问尝试
    """
    _ = current_user
    resolved_service = _resolve_service(service)
    return await resolved_service.get_asset_distribution(
        db=db,
        group_by=group_by,
        should_include_deleted=should_include_deleted,
    )
