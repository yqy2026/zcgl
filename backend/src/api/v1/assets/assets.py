# 异常类定义
class AssetNotFoundError(Exception):
    pass


class DuplicateAssetError(Exception):
    pass


class NotFoundError(Exception):
    pass


"""
资产管理API路由 - 核心CRUD操作

批量操作、导入功能已拆分到独立模块:
- asset_batch.py: 批量操作端点
- asset_import.py: 导入功能端点
"""

import os
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    Path,
    Query,
    Request,
    Response,
)
from sqlalchemy.orm import Session
from starlette.status import HTTP_204_NO_CONTENT

from ....constants.api_constants import PaginationLimits
from ....constants.business_constants import DateTimeFields
from ....crud.history import history_crud
from ....database import get_db
from ....middleware.auth import (
    audit_action,
    get_current_active_user,
    require_permission,
)
from ....middleware.security_middleware import get_client_ip
from ....models.auth import User
from ....schemas.asset import (
    AssetCreate,
    AssetListResponse,
    AssetResponse,
    AssetUpdate,
)
from ....services.asset.asset_service import AssetService

# 导入子路由模块
from . import asset_attachments, asset_batch, asset_import

# 获取开发模式配置，但不完全绕过认证
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# 创建资产路由器
router = APIRouter()

# 包含子路由器
router.include_router(asset_batch.router, tags=["资产批量操作"])
router.include_router(asset_import.router, tags=["资产导入"])
router.include_router(asset_attachments.router, tags=["资产附件"])


@router.get("", response_model=AssetListResponse, summary="获取资产列表")
async def get_assets(
    page: int = Query(PaginationLimits.DEFAULT_PAGE, ge=1, description="页码"),
    page_size: int = Query(
        PaginationLimits.DEFAULT_PAGE_SIZE,
        ge=PaginationLimits.MIN_PAGE_SIZE,
        le=PaginationLimits.MAX_PAGE_SIZE,
        description="每页记录数",
    ),
    search: str | None = Query(None, description="搜索关键词"),
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    ownership_entity: str | None = Query(None, description="权属方筛选"),
    management_entity: str | None = Query(None, description="经营管理方筛选"),
    business_category: str | None = Query(None, description="业态类别筛选"),
    min_area: float | None = Query(None, ge=0, description="最小面积筛选"),
    max_area: float | None = Query(None, ge=0, description="最大面积筛选"),
    is_litigated: str | None = Query(None, description="是否涉诉筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    sort_field: str = Query(DateTimeFields.CREATED_AT, description="排序字段"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
) -> AssetListResponse:
    """
    获取资产列表，支持分页、搜索和筛选

    - **page**: 页码，从1开始
    - **limit**: 每页记录数，最多100
    - **search**: 搜索关键词，会在物业名称、地址、权属方等字段中搜索
    - **ownership_status**: 按确权状态筛选
    - **property_nature**: 按物业性质筛选
    - **usage_status**: 按使用状态筛选
    - **ownership_entity**: 按权属方筛选
    - **sort_field**: 排序字段
    - **sort_order**: 排序方向（asc/desc）
    """
    # 构建筛选条件
    filters = {}
    if ownership_status:
        filters["ownership_status"] = ownership_status
    if property_nature:
        filters["property_nature"] = property_nature
    if usage_status:
        filters["usage_status"] = usage_status
    if ownership_entity:
        filters["ownership_entity"] = ownership_entity
    if management_entity:
        filters["management_entity"] = management_entity
    if business_category:
        filters["business_category"] = business_category
    if min_area is not None:
        filters["min_area"] = str(min_area)
    if max_area is not None:
        filters["max_area"] = str(max_area)
    if is_litigated:
        filters["is_litigated"] = is_litigated

    asset_service = AssetService(db)
    assets, total = asset_service.get_assets(
        skip=(page - 1) * page_size,
        limit=page_size,
        search=search,
        filters=filters,
        sort_field=sort_field,
        sort_order=sort_order,
    )

    # Convert Asset models to AssetResponse
    from ....schemas.asset import AssetResponse

    items = [AssetResponse.model_validate(asset) for asset in assets]

    return AssetListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


# ===== 搜索筛选辅助接口 ===== (必须在 /{asset_id} 路由之前)


@router.get("/ownership-entities", response_model=list[str], summary="获取权属方列表")
async def get_ownership_entities(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> list[str]:
    """获取所有权属方列表，用于搜索筛选"""
    asset_service = AssetService(db)
    return [
        str(value)
        for value in asset_service.get_distinct_field_values("ownership_entity")
    ]


@router.get(
    "/business-categories", response_model=list[str], summary="获取业态类别列表"
)
async def get_business_categories(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> list[str]:
    """获取所有业态类别列表，用于搜索筛选"""
    asset_service = AssetService(db)
    return [
        str(value)
        for value in asset_service.get_distinct_field_values("business_category")
    ]


@router.get("/usage-statuses", response_model=list[str], summary="获取使用情况列表")
async def get_usage_statuses(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> list[str]:
    """获取所有使用情况列表，用于搜索筛选"""
    asset_service = AssetService(db)
    return [
        str(value) for value in asset_service.get_distinct_field_values("usage_status")
    ]


@router.get("/property-natures", response_model=list[str], summary="获取物业性质列表")
async def get_property_natures(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> list[str]:
    """获取所有物业性质列表，用于搜索筛选"""
    asset_service = AssetService(db)
    return [
        str(value)
        for value in asset_service.get_distinct_field_values("property_nature")
    ]


@router.get("/ownership-statuses", response_model=list[str], summary="获取确权状态列表")
async def get_ownership_statuses(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> list[str]:
    """获取所有确权状态列表，用于搜索筛选"""
    asset_service = AssetService(db)
    return [
        str(value)
        for value in asset_service.get_distinct_field_values("ownership_status")
    ]


# ===== 单个资产操作接口 =====


@router.get("/{asset_id}", response_model=AssetResponse, summary="获取资产详情")
async def get_asset(
    asset_id: str = Path(..., description="资产ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AssetResponse:
    """
    根据ID获取单个资产的详细信息

    - **asset_id**: 资产ID
    """
    asset_service = AssetService(db)
    asset = asset_service.get_asset(asset_id)
    return AssetResponse.model_validate(asset)


@router.post("", response_model=AssetResponse, summary="创建新资产", status_code=201)
async def create_asset(
    asset_in: AssetCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "create")),
    audit_logger: Any = Depends(audit_action("asset_create", "asset")),
) -> AssetResponse:
    """
    创建新的资产记录

    - **asset_in**: 资产创建数据
    """
    asset_service = AssetService(db)
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    session_id = request.headers.get("X-Session-ID") or request.headers.get(
        "X-Session-Id"
    )
    asset = asset_service.create_asset(
        asset_in,
        current_user,
        ip_address=ip_address,
        user_agent=user_agent,
        session_id=session_id,
    )
    return AssetResponse.model_validate(asset)


@router.put("/{asset_id}", response_model=AssetResponse, summary="更新资产")
async def update_asset(
    asset_id: str,
    asset_in: AssetUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "update")),
    audit_logger: Any = Depends(audit_action("asset_update", "asset")),
) -> AssetResponse:
    """
    更新资产信息

    - **asset_id**: 资产ID
    - **asset_in**: 资产更新数据
    """
    asset_service = AssetService(db)
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    session_id = request.headers.get("X-Session-ID") or request.headers.get(
        "X-Session-Id"
    )
    asset = asset_service.update_asset(
        asset_id,
        asset_in,
        current_user,
        ip_address=ip_address,
        user_agent=user_agent,
        session_id=session_id,
    )
    return AssetResponse.model_validate(asset)


@router.delete("/{asset_id}", summary="删除资产")
async def delete_asset(
    asset_id: str = Path(..., description="资产ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "delete")),
    audit_logger: Any = Depends(audit_action("asset_delete", "asset")),
) -> Response:
    """
    删除资产记录

    - **asset_id**: 资产ID
    """
    asset_service = AssetService(db)
    asset_service.delete_asset(asset_id, current_user)
    return Response(status_code=HTTP_204_NO_CONTENT)


@router.get("/{asset_id}/history", summary="获取资产历史")
async def get_asset_history(
    asset_id: str = Path(..., description="资产ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    获取资产的变更历史记录

    - **asset_id**: 资产ID
    """
    # 检查资产是否存在
    # 这里的检查可以交给 service，History 获取也可以封装进 Service
    # 但鉴于 get_asset_history 单独存在，这里暂时简单调用 existing crud
    # 更好的做法是 AssetService.get_asset_history(asset_id)

    asset_service = AssetService(db)
    asset_service.get_asset(asset_id)  # Validate existence

    # 获取历史记录
    history_records = history_crud.get_by_asset_id(db=db, asset_id=asset_id)
    return {"asset_id": asset_id, "history": history_records}
