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
from collections.abc import Sequence
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    Path,
    Query,
    Request,
    Response,
)
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_204_NO_CONTENT

from ....constants.api_constants import PaginationLimits
from ....constants.business_constants import DateTimeFields
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....database import get_async_db
from ....middleware.auth import (
    audit_action,
    get_current_active_user,
    require_admin,
    require_permission,
)
from ....middleware.security_middleware import get_client_ip
from ....models.auth import User
from ....schemas.asset import (
    AssetCreate,
    AssetListItemResponse,
    AssetResponse,
    AssetUpdate,
)
from ....services.asset.asset_service import AssetService, AsyncAssetService

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

_asset_response_list_adapter = TypeAdapter(list[AssetResponse])
_asset_list_item_adapter = TypeAdapter(list[AssetListItemResponse])


async def _get_distinct_values(
    db: AsyncSession,
    field_name: str,
) -> list[str]:
    return await AsyncAssetService(db).get_distinct_field_values(field_name)


@router.get(
    "",
    response_model=APIResponse[PaginatedData[AssetResponse | AssetListItemResponse]],
    summary="获取资产列表",
)
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
    ownership_id: str | None = Query(None, description="权属方ID筛选"),
    management_entity: str | None = Query(None, description="经营管理方筛选"),
    business_category: str | None = Query(None, description="业态类别筛选"),
    data_status: str | None = Query(None, description="数据状态筛选"),
    min_area: float | None = Query(None, ge=0, description="最小面积筛选"),
    max_area: float | None = Query(None, ge=0, description="最大面积筛选"),
    min_occupancy_rate: float | None = Query(None, ge=0, description="最小出租率筛选"),
    max_occupancy_rate: float | None = Query(None, ge=0, description="最大出租率筛选"),
    is_litigated: bool | str | None = Query(
        None, description="是否涉诉筛选（支持 true/false 或 是/否）"
    ),
    include_relations: bool = Query(False, description="是否加载关联数据"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    sort_field: str | None = Query(None, description="排序字段"),
    sort_by: str | None = Query(None, description="排序字段（兼容参数）"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
) -> Response:
    """
    获取资产列表，支持分页、搜索和筛选

    - **page**: 页码，从1开始
    - **limit**: 每页记录数，最多100
    - **search**: 搜索关键词，会在物业名称、地址、权属方等字段中搜索
    - **ownership_status**: 按确权状态筛选
    - **property_nature**: 按物业性质筛选
    - **usage_status**: 按使用状态筛选
    - **ownership_id**: 按权属方ID筛选
    - **sort_field**: 排序字段
    - **sort_by**: 排序字段（兼容参数）
    - **sort_order**: 排序方向（asc/desc）
    - **include_relations**: 是否加载关联数据（默认不加载）
    """
    resolved_sort_field = (
        sort_field
        if sort_field is not None and sort_field != ""
        else sort_by
        if sort_by is not None and sort_by != ""
        else DateTimeFields.CREATED_AT
    )

    filters = AssetService.build_filters(
        ownership_status=ownership_status,
        property_nature=property_nature,
        usage_status=usage_status,
        ownership_id=ownership_id,
        management_entity=management_entity,
        business_category=business_category,
        data_status=data_status,
        min_area=min_area,
        max_area=max_area,
        min_occupancy_rate=min_occupancy_rate,
        max_occupancy_rate=max_occupancy_rate,
        is_litigated=is_litigated,
    )

    asset_service = AsyncAssetService(db)
    assets, total = await asset_service.get_assets(
        skip=(page - 1) * page_size,
        limit=page_size,
        search=search,
        filters=filters,
        sort_field=resolved_sort_field,
        sort_order=sort_order,
        include_relations=include_relations,
    )

    items: Sequence[AssetResponse | AssetListItemResponse]
    if include_relations:
        items = _asset_response_list_adapter.validate_python(
            assets, from_attributes=True
        )
    else:
        items = _asset_list_item_adapter.validate_python(assets, from_attributes=True)
    return ResponseHandler.paginated(
        data=list(items),
        page=page,
        page_size=page_size,
        total=total,
        message="获取资产列表成功",
    )


# ===== 搜索筛选辅助接口 ===== (必须在 /{asset_id} 路由之前)


@router.get("/ownership-entities", response_model=list[str], summary="获取权属方列表")
async def get_ownership_entities(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> list[str]:
    """获取所有权属方列表，用于搜索筛选"""
    return await AsyncAssetService(db).get_ownership_entity_names()


@router.get(
    "/business-categories", response_model=list[str], summary="获取业态类别列表"
)
async def get_business_categories(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> list[str]:
    """获取所有业态类别列表，用于搜索筛选"""
    return await _get_distinct_values(db, "business_category")


@router.get("/usage-statuses", response_model=list[str], summary="获取使用情况列表")
async def get_usage_statuses(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> list[str]:
    """获取所有使用情况列表，用于搜索筛选"""
    return await _get_distinct_values(db, "usage_status")


@router.get("/property-natures", response_model=list[str], summary="获取物业性质列表")
async def get_property_natures(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> list[str]:
    """获取所有物业性质列表，用于搜索筛选"""
    return await _get_distinct_values(db, "property_nature")


@router.get("/ownership-statuses", response_model=list[str], summary="获取确权状态列表")
async def get_ownership_statuses(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> list[str]:
    """获取所有确权状态列表，用于搜索筛选"""
    return await _get_distinct_values(db, "ownership_status")


# ===== 单个资产操作接口 =====


@router.get("/{asset_id}", response_model=AssetResponse, summary="获取资产详情")
async def get_asset(
    asset_id: str = Path(..., description="资产ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AssetResponse:
    """
    根据ID获取单个资产的详细信息

    - **asset_id**: 资产ID
    """
    asset_service = AsyncAssetService(db)
    asset = await asset_service.get_asset(asset_id)
    return AssetResponse.model_validate(asset)


@router.post("", response_model=AssetResponse, summary="创建新资产", status_code=201)
async def create_asset(
    asset_in: AssetCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("asset", "create")),
    audit_logger: Any = Depends(audit_action("asset_create", "asset")),
) -> AssetResponse:
    """
    创建新的资产记录

    - **asset_in**: 资产创建数据
    """
    asset_service = AsyncAssetService(db)
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    session_id = request.headers.get("X-Session-ID") or request.headers.get(
        "X-Session-Id"
    )
    asset = await asset_service.create_asset(
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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("asset", "update")),
    audit_logger: Any = Depends(audit_action("asset_update", "asset")),
) -> AssetResponse:
    """
    更新资产信息

    - **asset_id**: 资产ID
    - **asset_in**: 资产更新数据
    """
    asset_service = AsyncAssetService(db)
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    session_id = request.headers.get("X-Session-ID") or request.headers.get(
        "X-Session-Id"
    )
    asset = await asset_service.update_asset(
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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("asset", "delete")),
    audit_logger: Any = Depends(audit_action("asset_delete", "asset")),
) -> Response:
    """
    删除资产记录

    - **asset_id**: 资产ID
    """
    asset_service = AsyncAssetService(db)
    await asset_service.delete_asset(asset_id, current_user)
    return Response(status_code=HTTP_204_NO_CONTENT)


@router.post("/{asset_id}/restore", response_model=AssetResponse, summary="恢复资产")
async def restore_asset(
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    audit_logger: Any = Depends(audit_action("asset_restore", "asset")),
) -> AssetResponse:
    """
    恢复已删除的资产记录

    - **asset_id**: 资产ID
    """
    asset_service = AsyncAssetService(db)
    asset = await asset_service.restore_asset(asset_id, current_user)
    return AssetResponse.model_validate(asset)


@router.delete("/{asset_id}/hard-delete", summary="彻底删除资产")
async def hard_delete_asset(
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    audit_logger: Any = Depends(audit_action("asset_hard_delete", "asset")),
) -> Response:
    """
    彻底删除资产记录（物理删除）

    - **asset_id**: 资产ID
    """
    asset_service = AsyncAssetService(db)
    await asset_service.hard_delete_asset(asset_id, current_user)
    return Response(status_code=HTTP_204_NO_CONTENT)


@router.get("/{asset_id}/history", summary="获取资产历史")
async def get_asset_history(
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    获取资产的变更历史记录

    - **asset_id**: 资产ID
    """
    asset_service = AsyncAssetService(db)
    history_records = await asset_service.get_asset_history_records(asset_id)
    return {"asset_id": asset_id, "history": history_records}
