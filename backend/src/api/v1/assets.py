# 异常类定义
class AssetNotFoundError(Exception):
    pass


class DuplicateAssetError(Exception):
    pass


class NotFoundError(Exception):
    pass


"""
资产管理API路由 - 核心CRUD操作

统计、附件、批量操作、导入功能已拆分到独立模块:
- asset_statistics.py: 统计相关端点
- asset_attachments.py: 附件管理端点
- asset_batch.py: 批量操作端点
- asset_import.py: 导入功能端点
"""

import os

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Response,
)
from sqlalchemy.orm import Session
from starlette.status import HTTP_204_NO_CONTENT

from ...core.exception_handler import DuplicateResourceError, ResourceNotFoundError
from ...crud.asset import asset_crud
from ...crud.history import history_crud
from ...database import get_db
from ...middleware.auth import audit_action, get_current_active_user, require_permission
from ...models.asset import Asset
from ...models.auth import User
from ...schemas.asset import (
    AssetCreate,
    AssetListResponse,
    AssetResponse,
    AssetUpdate,
)

# 导入子路由模块
from . import asset_attachments, asset_batch, asset_import, asset_statistics

# 获取开发模式配置，但不完全绕过认证
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# 创建资产路由器
router = APIRouter()

# 包含子路由器
router.include_router(asset_statistics.router, prefix="/statistics", tags=["资产统计"])
router.include_router(asset_attachments.router, tags=["资产附件"])
router.include_router(asset_batch.router, tags=["资产批量操作"])
router.include_router(asset_import.router, tags=["资产导入"])


@router.get("", response_model=AssetListResponse, summary="获取资产列表")
async def get_assets(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
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
    sort_field: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
):
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
    try:
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
            filters["min_area"] = min_area
        if max_area is not None:
            filters["max_area"] = max_area
        if is_litigated:
            filters["is_litigated"] = is_litigated

        # 获取资产列表
        query = asset_crud.get_filtered_query(
            db, search, filters, sort_field, sort_order
        )

        # 执行分页查询
        assets, total = asset_crud.execute_paginated_query(
            query, skip=(page - 1) * limit, limit=limit
        )

        return AssetListResponse(
            items=assets,
            total=total,
            page=page,
            limit=limit,
            pages=(total + limit - 1) // limit,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资产列表失败: {str(e)}")


# ===== 搜索筛选辅助接口 ===== (必须在 /{asset_id} 路由之前)


@router.get("/ownership-entities", summary="获取权属方列表")
async def get_ownership_entities(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """获取所有权属方列表，用于搜索筛选"""
    try:
        # 从资产表中获取所有不重复的权属方
        entities = (
            db.query(Asset.ownership_entity)
            .filter(Asset.ownership_entity.isnot(None))
            .filter(Asset.ownership_entity != "")
            .distinct()
            .order_by(Asset.ownership_entity)
            .all()
        )

        return [entity[0] for entity in entities if entity[0]]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取权属方列表失败: {str(e)}")


@router.get("/business-categories", summary="获取业态类别列表")
async def get_business_categories(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """获取所有业态类别列表，用于搜索筛选"""
    try:
        # 从资产表中获取所有不重复的业态类别
        categories = (
            db.query(Asset.business_category)
            .filter(Asset.business_category.isnot(None))
            .filter(Asset.business_category != "")
            .distinct()
            .order_by(Asset.business_category)
            .all()
        )

        return [category[0] for category in categories if category[0]]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取业态类别列表失败: {str(e)}")


@router.get("/usage-statuses", summary="获取使用情况列表")
async def get_usage_statuses(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """获取所有使用情况列表，用于搜索筛选"""
    try:
        # 从资产表中获取所有不重复的使用情况
        statuses = (
            db.query(Asset.usage_status)
            .filter(Asset.usage_status.isnot(None))
            .filter(Asset.usage_status != "")
            .distinct()
            .order_by(Asset.usage_status)
            .all()
        )
        return [status[0] for status in statuses if status[0]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取使用情况列表失败: {str(e)}")


@router.get("/property-natures", summary="获取物业性质列表")
async def get_property_natures(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """获取所有物业性质列表，用于搜索筛选"""
    try:
        # 从资产表中获取所有不重复的物业性质
        natures = (
            db.query(Asset.property_nature)
            .filter(Asset.property_nature.isnot(None))
            .filter(Asset.property_nature != "")
            .distinct()
            .order_by(Asset.property_nature)
            .all()
        )
        return [nature[0] for nature in natures if nature[0]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取物业性质列表失败: {str(e)}")


@router.get("/ownership-statuses", summary="获取确权状态列表")
async def get_ownership_statuses(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """获取所有确权状态列表，用于搜索筛选"""
    try:
        # 从资产表中获取所有不重复的确权状态
        statuses = (
            db.query(Asset.ownership_status)
            .filter(Asset.ownership_status.isnot(None))
            .filter(Asset.ownership_status != "")
            .distinct()
            .order_by(Asset.ownership_status)
            .all()
        )
        return [status[0] for status in statuses if status[0]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取确权状态列表失败: {str(e)}")


# ===== 单个资产操作接口 =====


@router.get("/{asset_id}", response_model=AssetResponse, summary="获取资产详情")
async def get_asset(
    asset_id: str = Path(..., description="资产ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    根据ID获取单个资产的详细信息

    - **asset_id**: 资产ID
    """
    try:
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("Asset", asset_id)
        return asset
    except ResourceNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资产详情失败: {str(e)}")


@router.post("", response_model=AssetResponse, summary="创建新资产", status_code=201)
async def create_asset(
    asset_in: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "create")),
    audit_logger=Depends(audit_action("asset_create", "asset")),
):
    """
    创建新的资产记录

    - **asset_in**: 资产创建数据
    """
    try:
        # 动态验证枚举值
        from ...services.enum_validation_service import get_enum_validation_service

        validation_service = get_enum_validation_service(db)
        is_valid, errors = validation_service.validate_asset_data(asset_in.model_dump())
        if not is_valid:
            raise HTTPException(
                status_code=422, detail=f"枚举值验证失败: {'; '.join(errors)}"
            )

        # 检查是否存在同名资产
        existing_asset = asset_crud.get_by_name(
            db=db, property_name=asset_in.property_name
        )
        if existing_asset:
            raise DuplicateResourceError(
                "Asset", "property_name", asset_in.property_name
            )

        # 创建资产并记录历史
        asset = asset_crud.create_with_history(db=db, obj_in=asset_in)
        return asset

    except DuplicateResourceError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建资产失败: {str(e)}")


@router.put("/{asset_id}", response_model=AssetResponse, summary="更新资产")
async def update_asset(
    asset_id: str = Path(..., description="资产ID"),
    asset_in: AssetUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "update")),
    audit_logger=Depends(audit_action("asset_update", "asset")),
):
    """
    更新资产信息

    - **asset_id**: 资产ID
    - **asset_in**: 资产更新数据
    """
    try:
        # 动态验证枚举值
        from ...services.enum_validation_service import get_enum_validation_service

        validation_service = get_enum_validation_service(db)
        is_valid, errors = validation_service.validate_asset_data(
            asset_in.model_dump(exclude_unset=True)
        )
        if not is_valid:
            raise HTTPException(
                status_code=422, detail=f"枚举值验证失败: {'; '.join(errors)}"
            )

        # 检查资产是否存在
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("Asset", asset_id)

        # 如果更新了物业名称，检查是否重复
        if asset_in.property_name and asset_in.property_name != asset.property_name:
            existing_asset = asset_crud.get_by_name(
                db=db, property_name=asset_in.property_name
            )
            if existing_asset and existing_asset.id != asset_id:
                raise DuplicateResourceError(
                    "Asset", "property_name", asset_in.property_name
                )

        # 更新资产并记录历史
        updated_asset = asset_crud.update_with_history(
            db=db, db_obj=asset, obj_in=asset_in
        )
        return updated_asset

    except (AssetNotFoundError, DuplicateAssetError):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新资产失败: {str(e)}")


@router.delete("/{asset_id}", summary="删除资产")
async def delete_asset(
    asset_id: str = Path(..., description="资产ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "delete")),
    audit_logger=Depends(audit_action("asset_delete", "asset")),
):
    """
    删除资产记录

    - **asset_id**: 资产ID
    """
    try:
        # 检查资产是否存在
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("Asset", asset_id)

        # 删除资产
        asset_crud.remove(db=db, id=asset_id)
        return Response(status_code=HTTP_204_NO_CONTENT)

    except ResourceNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除资产失败: {str(e)}")


@router.get("/{asset_id}/history", summary="获取资产历史")
async def get_asset_history(
    asset_id: str = Path(..., description="资产ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取资产的变更历史记录

    - **asset_id**: 资产ID
    """
    try:
        # 检查资产是否存在
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("Asset", asset_id)

        # 获取历史记录
        history_records = history_crud.get_by_asset_id(db=db, asset_id=asset_id)
        return {"asset_id": asset_id, "history": history_records}

    except ResourceNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资产历史失败: {str(e)}")
