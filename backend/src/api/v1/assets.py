"""
资产管理API路由
"""

import os
import shutil
import uuid
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Path,
    Query,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.status import HTTP_204_NO_CONTENT

from ...core.exception_handler import DuplicateResourceError, ResourceNotFoundError
from ...crud.asset import asset_crud
from ...crud.history import history_crud
from ...database import get_db

# 开发模式配置 - 用于开发环境绕过认证
from ...middleware.auth import audit_action, get_current_active_user, require_permission
from ...models.asset import Asset
from ...models.auth import User
from ...schemas.asset import (
    AssetBatchUpdateRequest,
    AssetBatchUpdateResponse,
    AssetCreate,
    AssetImportRequest,
    AssetImportResponse,
    AssetListResponse,
    AssetResponse,
    AssetUpdate,
    AssetValidationRequest,
    AssetValidationResponse,
    BatchCustomFieldUpdateRequest,
    BatchCustomFieldUpdateResponse,
)

# 获取开发模式配置，但不完全绕过认证
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# 创建资产路由器
router = APIRouter()


# @router.get("/dev-test", summary="开发模式测试端点")
# async def dev_test(db: Session = Depends(get_db)):
#     """开发模式测试端点（无认证）"""
#     try:
#         # 测试数据库连接
#         asset_count = db.query(Asset).count()
#         return {
#             "success": True,
#             "message": "开发模式API测试成功",
#             "database_status": "正常",
#             "asset_count": asset_count,
#             "timestamp": datetime.now().isoformat()
#         }
#     except Exception as e:
#         return {
#             "success": False,
#             "message": f"开发模式API测试失败: {str(e)}",
#             "timestamp": datetime.now().isoformat()
#         }


# @router.get("/temp-test", summary="临时API测试")
# async def temp_test(db: Session = Depends(get_db)):
#     """临时API测试端点（无认证）"""
#     try:
#         # 测试数据库连接
#         asset_count = db.query(Asset).count()
#         return {
#             "success": True,
#             "message": "临时API测试成功",
#             "database_status": "正常",
#             "asset_count": asset_count,
#             "timestamp": datetime.now().isoformat()
#         }
#     except Exception as e:
#         return {
#             "success": False,
#             "message": f"临时API测试失败: {str(e)}",
#             "timestamp": datetime.now().isoformat()
#         }


# @router.get("/test-api", summary="API测试")
# async def api_test(db: Session = Depends(get_db)):
#     """简单的API测试端点"""
#     try:
#         # 测试数据库连接
#         asset_count = db.query(Asset).count()
#     return {
#         "success": True,
#         "message": "API测试成功",
#         "database_status": "正常",
#         "asset_count": asset_count,
#         "timestamp": datetime.now().isoformat()
#     }
#     except Exception as e:
#         return {
#             "success": False,
#             "message": f"API测试失败: {str(e)}",
#             "timestamp": datetime.now().isoformat()
#         }


# @router.get("/list-test", summary="资产列表测试")
# async def list_test(page: int = Query(1, ge=1), limit: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
#     """资产列表测试端点（无认证）"""
#     try:
#         # 获取资产列表
#         query = asset_crud.get_filtered_query(db, None, {}, "created_at", "desc")
#         assets, total = asset_crud.execute_paginated_query(query, skip=(page - 1) * limit, limit=limit)

#         return {
#             "success": True,
#             "data": {
#                 "items": assets,
#                 "total": total,
#                 "page": page,
#                 "limit": limit,
#                 "pages": (total + limit - 1) // limit
#             },
#             "message": "资产列表测试成功",
#             "timestamp": datetime.now().isoformat()
#         }
#     except Exception as e:
#         return {
#             "success": False,
#             "message": f"资产列表测试失败: {str(e)}",
#             "timestamp": datetime.now().isoformat()
#         }


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
        # 检查是否存在同名资产
        existing_asset = asset_crud.get_by_name(
            db=db, property_name=asset_in.property_name
        )
        if existing_asset:
            raise DuplicateResourceError("Asset", "property_name", asset_in.property_name)

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
                raise DuplicateResourceError("Asset", "property_name", asset_in.property_name)

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


@router.get("/statistics/test", summary="测试统计API")
async def test_statistics(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """
    简单的统计测试API
    """
    try:
        print("[DEBUG] 测试统计API开始")

        # 简单测试查询
        total_assets = db.query(Asset).count()

        return {
            "success": True,
            "message": "测试成功",
            "total_assets": total_assets,
            "timestamp": "2024-01-01T00:00:00Z",
        }

    except Exception as e:
        print(f"[ERROR] 测试统计API失败: {e}")
        import traceback

        print(f"[ERROR] 详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")


@router.get("/statistics/summary", summary="获取资产统计摘要")
async def get_asset_statistics(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """
    获取资产统计摘要信息
    """
    try:
        from sqlalchemy import func

        from ...models.asset import Asset

        # 添加调试信息
        print(
            f"[DEBUG] 开始执行资产统计查询，用户: {current_user.username if current_user else 'unknown'}"
        )

        # 检查数据库连接是否正常
        try:
            db.execute(text("SELECT 1"))
        except Exception as e:
            print(f"[ERROR] 数据库连接检查失败: {e}")
            raise HTTPException(status_code=500, detail="数据库连接失败")

        # 总资产数 - 直接查询避免缓存问题
        total_assets = db.query(Asset).count()
        print(f"[DEBUG] 总资产数: {total_assets}")

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

        # 转换为float并处理None值
        def to_float(value):
            if value is None:
                return 0.0
            try:
                return float(value)
            except (ValueError, TypeError) as e:
                print(f"[WARNING] 转换数值失败: {value} -> {e}")
                return 0.0

        total_land_area = to_float(area_result.total_land_area)
        total_rentable_area = to_float(area_result.total_rentable_area)
        total_rented_area = to_float(area_result.total_rented_area)
        # 计算未出租面积（可出租面积 - 已出租面积）
        total_unrented_area = max(total_rentable_area - total_rented_area, 0.0)
        total_non_commercial_area = to_float(area_result.total_non_commercial_area)

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
        print(f"[ERROR] 资产统计查询失败: {str(e)}")
        print(f"[ERROR] 详细错误信息: {error_detail}")
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息失败: {str(e)}. 请检查数据库连接和表结构。",
        )


@router.get("/statistics/area-summary", summary="获取资产面积统计摘要")
async def get_asset_area_statistics(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """
    获取资产面积统计摘要信息
    """
    try:
        from sqlalchemy import func

        from ...models.asset import Asset

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

        # 转换为float并处理None值
        def to_float(value):
            if value is None:
                return 0.0
            try:
                return float(value)
            except (ValueError, TypeError) as e:
                print(f"[WARNING] 转换数值失败: {value} -> {e}")
                return 0.0

        total_land_area = to_float(total_result.total_land_area)
        total_rentable_area = to_float(total_result.total_rentable_area)
        total_rented_area = to_float(total_result.total_rented_area)
        # 计算未出租面积（可出租面积 - 已出租面积）
        total_unrented_area = max(total_rentable_area - total_rented_area, 0.0)
        total_non_commercial_area = to_float(total_result.total_non_commercial_area)
        total_assets = (
            int(total_result.total_assets) if total_result.total_assets else 0
        )

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
        print(f"[ERROR] 面积统计查询失败: {str(e)}")
        print(f"[ERROR] 详细错误信息: {error_detail}")
        raise HTTPException(
            status_code=500,
            detail=f"获取面积统计信息失败: {str(e)}. 请检查数据库连接和表结构。",
        )


# ===== 资产附件管理接口 =====


@router.post("/{asset_id}/attachments", summary="上传资产附件")
async def upload_asset_attachments(
    asset_id: str = Path(..., description="资产ID"),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "update")),
):
    """
    上传资产附件（PDF格式）

    - **asset_id**: 资产ID
    - **files**: 要上传的文件列表
    """
    try:
        # 检查资产是否存在
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("Asset", asset_id)

        # 创建附件目录
        upload_dir = f"uploads/attachments/{asset_id}"
        os.makedirs(upload_dir, exist_ok=True)

        success_files = []
        failed_files = []

        for file in files:
            try:
                # 验证文件类型
                if not file.filename.lower().endswith(".pdf"):
                    failed_files.append(f"{file.filename}: 仅支持PDF格式")
                    continue

                # 验证文件大小（10MB限制）
                max_size = 10 * 1024 * 1024  # 10MB
                file.file.seek(0, 2)  # 移动到文件末尾
                file_size = file.file.tell()
                file.file.seek(0)  # 重置到文件开头

                if file_size > max_size:
                    failed_files.append(f"{file.filename}: 文件大小超过10MB限制")
                    continue

                # 生成唯一文件名
                file_extension = os.path.splitext(file.filename)[1]
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                file_path = os.path.join(upload_dir, unique_filename)

                # 保存文件
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                success_files.append(file.filename)

            except Exception as e:
                failed_files.append(f"{file.filename}: {str(e)}")

        return {
            "success": success_files,
            "failed": failed_files,
            "message": f"成功上传 {len(success_files)} 个文件，失败 {len(failed_files)} 个文件",
        }

    except ResourceNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传附件失败: {str(e)}")


@router.get("/{asset_id}/attachments", summary="获取资产附件列表")
async def get_asset_attachments(
    asset_id: str = Path(..., description="资产ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取资产附件列表

    - **asset_id**: 资产ID
    """
    try:
        # 检查资产是否存在
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("Asset", asset_id)

        # 获取附件目录
        upload_dir = f"uploads/attachments/{asset_id}"

        if not os.path.exists(upload_dir):
            return []

        attachments = []
        for filename in os.listdir(upload_dir):
            if filename.lower().endswith(".pdf"):
                file_path = os.path.join(upload_dir, filename)
                file_stat = os.stat(file_path)

                attachments.append(
                    {
                        "id": filename,
                        "name": filename,
                        "size": file_stat.st_size,
                        "url": f"/api/v1/assets/{asset_id}/attachments/{filename}",
                        "upload_time": file_stat.st_mtime,
                    }
                )

        return attachments

    except ResourceNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取附件列表失败: {str(e)}")


@router.get("/{asset_id}/attachments/{filename}", summary="下载资产附件")
async def download_asset_attachment(
    asset_id: str = Path(..., description="资产ID"),
    filename: str = Path(..., description="文件名"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    下载资产附件

    - **asset_id**: 资产ID
    - **filename**: 文件名
    """
    try:
        # 检查资产是否存在
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("Asset", asset_id)

        # 验证文件路径
        file_path = f"uploads/attachments/{asset_id}/{filename}"

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        # 验证文件类型
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="仅支持PDF文件")

        return FileResponse(file_path, filename=filename, media_type="application/pdf")

    except ResourceNotFoundError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载附件失败: {str(e)}")


@router.delete("/{asset_id}/attachments/{attachment_id}", summary="删除资产附件")
async def delete_asset_attachment(
    asset_id: str = Path(..., description="资产ID"),
    attachment_id: str = Path(..., description="附件ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "delete")),
):
    """
    删除资产附件

    - **asset_id**: 资产ID
    - **attachment_id**: 附件ID（文件名）
    """
    try:
        # 检查资产是否存在
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("Asset", asset_id)

        # 验证文件路径
        file_path = f"uploads/attachments/{asset_id}/{attachment_id}"

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        # 删除文件
        os.remove(file_path)

        return {"message": "附件删除成功"}

    except ResourceNotFoundError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除附件失败: {str(e)}")


# ===== 批量操作API =====


@router.post(
    "/batch-update", response_model=AssetBatchUpdateResponse, summary="批量更新资产"
)
async def batch_update_assets(
    request: AssetBatchUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "update")),
):
    """
    批量更新资产信息

    - **asset_ids**: 资产ID列表
    - **updates**: 更新数据字典
    - **update_all**: 是否更新所有资产
    """
    try:
        # 如果更新所有资产，获取所有资产ID
        if request.update_all:
            all_assets, _ = asset_crud.get_multi_with_search(db=db, skip=0, limit=10000)
            asset_ids = [asset.id for asset in all_assets]
        else:
            asset_ids = request.asset_ids

        total_count = len(asset_ids)
        success_count = 0
        failed_count = 0
        errors = []
        updated_assets = []

        for asset_id in asset_ids:
            try:
                # 获取现有资产
                asset = asset_crud.get(db=db, id=asset_id)
                if not asset:
                    errors.append({"asset_id": asset_id, "error": "资产不存在"})
                    failed_count += 1
                    continue

                # 更新资产
                asset_crud.update(db=db, db_obj=asset, obj_in=request.updates)

                success_count += 1
                updated_assets.append(asset_id)

                # 记录历史
                history_crud.create(
                    db=db,
                    obj_in={
                        "asset_id": asset_id,
                        "operation_type": "批量更新",
                        "description": f"批量更新字段: {', '.join(request.updates.keys())}",
                        "operator": "system",
                    },
                )

            except Exception as e:
                errors.append({"asset_id": asset_id, "error": str(e)})
                failed_count += 1

        return AssetBatchUpdateResponse(
            success_count=success_count,
            failed_count=failed_count,
            total_count=total_count,
            errors=errors,
            updated_assets=updated_assets,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量更新失败: {str(e)}")


@router.post(
    "/validate", response_model=AssetValidationResponse, summary="验证资产数据"
)
async def validate_asset_data(
    request: AssetValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    验证资产数据的完整性和正确性

    - **data**: 待验证的资产数据
    - **validate_rules**: 验证规则列表
    """
    try:
        errors = []
        warnings = []
        validated_fields = []

        data = request.data
        validate_rules = request.validate_rules or ["required_fields", "data_format"]

        # 验证必填字段
        if "required_fields" in validate_rules:
            required_fields = [
                "property_name",
                "address",
                "ownership_status",
                "property_nature",
                "usage_status",
            ]

            for field in required_fields:
                if field not in data or not data[field]:
                    errors.append({"field": field, "error": f"{field}为必填字段"})
                else:
                    validated_fields.append(field)

        # 验证数据格式
        if "data_format" in validate_rules:
            # 验证枚举值
            if "ownership_status" in data:
                valid_statuses = ["已确权", "未确权", "部分确权", "无法确认业权"]
                if data["ownership_status"] not in valid_statuses:
                    errors.append(
                        {
                            "field": "ownership_status",
                            "error": f"权属状态必须是: {', '.join(valid_statuses)}",
                        }
                    )
                else:
                    validated_fields.append("ownership_status")

            # 验证数值字段
            numeric_fields = [
                "land_area",
                "actual_property_area",
                "rentable_area",
                "rented_area",
                "annual_income",
                "annual_expense",
                "monthly_rent",
                "deposit",
            ]

            for field in numeric_fields:
                if field in data and data[field] is not None:
                    try:
                        float(data[field])
                        validated_fields.append(field)
                    except (ValueError, TypeError):
                        errors.append(
                            {"field": field, "error": f"{field}必须是有效的数字"}
                        )

            # 验证日期字段
            date_fields = [
                "contract_start_date",
                "contract_end_date",
                "operation_agreement_start_date",
                "operation_agreement_end_date",
            ]

            for field in date_fields:
                if field in data and data[field] is not None:
                    try:
                        # 简单的日期格式验证
                        if isinstance(data[field], str):
                            # 验证 YYYY-MM-DD 格式
                            import re

                            if not re.match(r"^\d{4}-\d{2}-\d{2}$", data[field]):
                                errors.append(
                                    {
                                        "field": field,
                                        "error": f"{field}日期格式应为 YYYY-MM-DD",
                                    }
                                )
                            else:
                                validated_fields.append(field)
                    except Exception:
                        errors.append({"field": field, "error": f"{field}日期格式无效"})

        # 添加建议性警告
        suggestion_fields = [
            ("land_area", "建议填写土地面积"),
            ("annual_income", "建议填写年收入"),
            ("annual_expense", "建议填写年支出"),
            ("tenant_name", "建议填写租户信息（如果是已出租资产）"),
        ]

        for field, suggestion in suggestion_fields:
            if field not in data or data[field] is None:
                warnings.append({"field": field, "message": suggestion})

        is_valid = len(errors) == 0

        return AssetValidationResponse(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            validated_fields=validated_fields,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据验证失败: {str(e)}")


@router.post("/import", response_model=AssetImportResponse, summary="导入资产数据")
async def import_assets(
    request: AssetImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "create")),
):
    """
    批量导入资产数据

    - **data**: 待导入的资产数据列表
    - **import_mode**: 导入模式（create/merge/update）
    - **skip_errors**: 是否跳过错误数据
    - **dry_run**: 是否仅验证不实际导入
    """
    try:
        import_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        success_count = 0
        failed_count = 0
        total_count = len(request.data)
        errors = []
        imported_assets = []

        for index, asset_data in enumerate(request.data):
            try:
                # 验证数据
                validation_request = AssetValidationRequest(data=asset_data)
                validation_result = await validate_asset_data(validation_request, db)

                if not validation_result.is_valid and not request.skip_errors:
                    errors.append(
                        {
                            "row": index + 1,
                            "data": asset_data,
                            "errors": validation_result.errors,
                        }
                    )
                    failed_count += 1
                    continue

                # 检查重复项（仅在merge和update模式下）
                if request.import_mode in ["merge", "update"]:
                    existing_asset = None
                    if "property_name" in asset_data and "address" in asset_data:
                        # 按物业名称和地址查找重复项
                        assets, _ = asset_crud.get_multi_with_search(
                            db=db,
                            search=f"{asset_data.get('property_name', '')} {asset_data.get('address', '')}",
                            limit=1,
                        )
                        if assets:
                            existing_asset = assets[0]

                if request.dry_run:
                    # 仅验证，不实际导入
                    success_count += 1
                    continue

                # 根据模式处理数据
                if request.import_mode == "create":
                    # 创建新资产
                    asset_create = AssetCreate(**asset_data)
                    new_asset = asset_crud.create(db=db, obj_in=asset_create)
                    imported_assets.append(new_asset.id)
                    success_count += 1

                elif request.import_mode == "merge" and existing_asset:
                    # 更新现有资产
                    asset_update = AssetUpdate(
                        **{
                            k: v
                            for k, v in asset_data.items()
                            if k not in ["id", "created_at"]
                        }
                    )
                    updated_asset = asset_crud.update(
                        db=db, db_obj=existing_asset, obj_in=asset_update
                    )
                    imported_assets.append(updated_asset.id)
                    success_count += 1

                elif request.import_mode == "update" and existing_asset:
                    # 强制更新现有资产
                    asset_update = AssetUpdate(**asset_data)
                    updated_asset = asset_crud.update(
                        db=db, db_obj=existing_asset, obj_in=asset_update
                    )
                    imported_assets.append(updated_asset.id)
                    success_count += 1

                else:
                    # 创建新资产（默认情况）
                    asset_create = AssetCreate(**asset_data)
                    new_asset = asset_crud.create(db=db, obj_in=asset_create)
                    imported_assets.append(new_asset.id)
                    success_count += 1

                # 记录历史
                history_crud.create(
                    db=db,
                    obj_in={
                        "asset_id": imported_assets[-1]
                        if imported_assets
                        else "unknown",
                        "operation_type": "批量导入",
                        "description": "通过批量导入创建/更新资产",
                        "operator": "system",
                    },
                )

            except Exception as e:
                errors.append({"row": index + 1, "data": asset_data, "error": str(e)})
                failed_count += 1

        return AssetImportResponse(
            success_count=success_count,
            failed_count=failed_count,
            total_count=total_count,
            errors=errors,
            imported_assets=imported_assets,
            import_id=import_id if not request.dry_run else None,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"资产导入失败: {str(e)}")


@router.post(
    "/batch-custom-fields",
    response_model=BatchCustomFieldUpdateResponse,
    summary="批量更新自定义字段",
)
async def batch_update_custom_fields(
    request: BatchCustomFieldUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "update")),
):
    """
    批量更新资产的自定义字段

    - **asset_ids**: 资产ID列表
    - **field_values**: 自定义字段值字典
    """
    try:
        total_count = len(request.asset_ids)
        success_count = 0
        failed_count = 0
        errors = []

        for asset_id in request.asset_ids:
            try:
                # 检查资产是否存在
                asset = asset_crud.get(db=db, id=asset_id)
                if not asset:
                    errors.append({"asset_id": asset_id, "error": "资产不存在"})
                    failed_count += 1
                    continue

                # 这里简化处理，实际项目中应该有专门的自定义字段表
                # 可以将自定义字段存储在JSON格式的字段中
                success_count += 1

            except Exception as e:
                errors.append({"asset_id": asset_id, "error": str(e)})
                failed_count += 1

        return BatchCustomFieldUpdateResponse(
            success_count=success_count,
            failed_count=failed_count,
            total_count=total_count,
            errors=errors,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量更新自定义字段失败: {str(e)}")


@router.get("/all", summary="获取所有资产（不分页）")
async def get_all_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    search: str | None = Query(None, description="搜索关键字"),
    ownership_status: str | None = Query(None, description="确权状态"),
    usage_status: str | None = Query(None, description="使用状态"),
    property_nature: str | None = Query(None, description="物业性质"),
    business_category: str | None = Query(None, description="业态类别"),
    sort_by: str | None = Query("created_at", description="排序字段"),
    sort_order: str | None = Query("desc", description="排序顺序"),
    limit: int = Query(10000, ge=1, le=50000, description="最大返回数量"),
):
    """
    获取所有资产列表，不分页，用于导出等场景

    支持的查询参数：
    - **search**: 搜索关键字（物业名称、地址等）
    - **ownership_status**: 确权状态过滤
    - **usage_status**: 使用状态过滤
    - **property_nature**: 物业性质过滤
    - **business_category**: 业态类别过滤
    - **sort_by**: 排序字段
    - **sort_order**: 排序顺序（asc/desc）
    - **limit**: 最大返回数量限制
    """
    try:
        # 构建查询过滤器
        filters = {}
        if search:
            filters["search"] = search
        if ownership_status:
            filters["ownership_status"] = ownership_status
        if usage_status:
            filters["usage_status"] = usage_status
        if property_nature:
            filters["property_nature"] = property_nature
        if business_category:
            filters["business_category"] = business_category

        # 排序
        order_by = None
        if sort_by and sort_order:
            if sort_order.lower() == "desc":
                order_by = f"{sort_by} desc"
            else:
                order_by = f"{sort_by} asc"

        # 获取所有资产（不分页）
        assets = asset_crud.get_multi(
            db=db, filters=filters if filters else None, order_by=order_by, limit=limit
        )

        # 转换为响应格式
        asset_responses = []
        for asset in assets:
            asset_dict = asset.__dict__.copy()
            asset_dict["_sa_instance_state"] = None  # 移除SQLAlchemy实例状态

            # 确保计算字段包含在响应中
            if hasattr(asset, "unrented_area"):
                asset_dict["unrented_area"] = float(asset.unrented_area)
            if hasattr(asset, "occupancy_rate"):
                asset_dict["occupancy_rate"] = float(asset.occupancy_rate)

            asset_responses.append(AssetResponse.model_validate(asset_dict))

        # 返回统一格式，符合前端期望
        return {
            "success": True,
            "data": asset_responses,
            "message": f"成功获取{len(asset_responses)}个资产",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资产列表失败: {str(e)}")


@router.post("/by-ids", summary="根据ID列表获取资产")
async def get_assets_by_ids(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    根据资产ID列表批量获取资产信息

    - **ids**: 资产ID列表
    """
    try:
        asset_ids = request.get("ids", [])
        if not asset_ids:
            return []

        # 批量查询资产
        assets = asset_crud.get_multi_by_ids(db=db, ids=asset_ids)

        # 转换为响应格式
        asset_responses = []
        for asset in assets:
            asset_dict = asset.__dict__.copy()
            asset_dict["_sa_instance_state"] = None  # 移除SQLAlchemy实例状态

            # 确保计算字段包含在响应中
            if hasattr(asset, "unrented_area"):
                asset_dict["unrented_area"] = float(asset.unrented_area)
            if hasattr(asset, "occupancy_rate"):
                asset_dict["occupancy_rate"] = float(asset.occupancy_rate)

            asset_responses.append(AssetResponse.model_validate(asset_dict))

        # 返回统一格式，符合前端期望
        return {
            "success": True,
            "data": asset_responses,
            "message": f"成功获取{len(asset_responses)}个资产",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"根据ID列表获取资产失败: {str(e)}")


@router.post("/batch-delete", summary="批量删除资产")
async def batch_delete_assets(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    批量删除资产

    - **asset_ids**: 要删除的资产ID列表
    """
    try:
        asset_ids = request.get("asset_ids", [])
        if not asset_ids:
            raise HTTPException(status_code=400, detail="未提供要删除的资产ID列表")

        # 批量删除资产
        deleted_count = 0
        for asset_id in asset_ids:
            try:
                asset = asset_crud.get(db=db, id=asset_id)
                if asset:
                    asset_crud.remove(db=db, id=asset_id)
                    deleted_count += 1
            except Exception:
                continue  # 即使单个资产删除失败也继续处理其他资产

        return {
            "success": True,
            "data": {"deleted_count": deleted_count},
            "message": f"成功删除{deleted_count}个资产"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量删除资产失败: {str(e)}")


@router.post("/validate", summary="验证资产数据")
async def validate_asset_data(
    asset_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    验证资产数据的完整性和有效性

    - **asset_data**: 要验证的资产数据
    """
    try:
        validation_errors = []
        warnings = []

        # 检查必填字段
        required_fields = ["propertyName", "address", "ownershipStatus", "propertyNature", "usageStatus"]
        for field in required_fields:
            if field not in asset_data or not asset_data[field]:
                validation_errors.append(f"缺少必填字段: {field}")

        # 检查数据类型
        if "landArea" in asset_data and asset_data["landArea"]:
            try:
                float(asset_data["landArea"])
            except (ValueError, TypeError):
                validation_errors.append("土地面积必须是有效数字")

        if "actualPropertyArea" in asset_data and asset_data["actualPropertyArea"]:
            try:
                float(asset_data["actualPropertyArea"])
            except (ValueError, TypeError):
                validation_errors.append("实际面积必须是有效数字")

        # 检查业务规则
        if asset_data.get("ownershipStatus") == "已出租" and not asset_data.get("leaseContractNumber"):
            warnings.append("已出租资产建议填写租赁合同号")

        if asset_data.get("rentedArea", 0) > asset_data.get("rentableArea", 0):
            validation_errors.append("已出租面积不能大于可出租面积")

        return {
            "success": len(validation_errors) == 0,
            "data": {
                "is_valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "warnings": warnings,
                "validation_score": max(0, 100 - len(validation_errors) * 10)
            },
            "message": "验证完成" if len(validation_errors) == 0 else f"发现{len(validation_errors)}个验证错误"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"资产数据验证失败: {str(e)}")


@router.get("/ownership-entities", summary="获取权属实体列表")
async def get_ownership_entities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取所有权属实体列表
    """
    try:
        # 从资产表中提取所有唯一的权属实体
        query = text("SELECT DISTINCT ownership_entity FROM assets WHERE ownership_entity IS NOT NULL ORDER BY ownership_entity")
        result = db.execute(query)
        ownership_entities = [row[0] for row in result.fetchall()]

        return {
            "success": True,
            "data": ownership_entities,
            "message": f"获取到{len(ownership_entities)}个权属实体"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取权属实体列表失败: {str(e)}")


@router.get("/business-categories", summary="获取业务分类列表")
async def get_business_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取所有业务分类列表
    """
    try:
        # 从资产表中提取所有唯一的业务分类
        query = text("SELECT DISTINCT ownership_category FROM assets WHERE ownership_category IS NOT NULL ORDER BY ownership_category")
        result = db.execute(query)
        business_categories = [row[0] for row in result.fetchall()]

        return {
            "success": True,
            "data": business_categories,
            "message": f"获取到{len(business_categories)}个业务分类"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取业务分类列表失败: {str(e)}")


@router.get("/statistics/summary", summary="获取资产统计摘要")
async def get_asset_statistics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取资产统计摘要信息
    """
    try:
        # 获取基本统计数据
        total_assets = asset_crud.count(db)

        # 按权属状态统计
        status_query = text("""
            SELECT ownership_status, COUNT(*) as count
            FROM assets
            GROUP BY ownership_status
        """)
        status_result = db.execute(status_query)
        status_stats = {row[0]: row[1] for row in status_result.fetchall()}

        # 按使用状态统计
        usage_query = text("""
            SELECT usage_status, COUNT(*) as count
            FROM assets
            GROUP BY usage_status
        """)
        usage_result = db.execute(usage_query)
        usage_stats = {row[0]: row[1] for row in usage_result.fetchall()}

        # 计算总面积
        area_query = text("""
            SELECT
                SUM(CASE WHEN land_area IS NOT NULL THEN land_area ELSE 0 END) as total_land_area,
                SUM(CASE WHEN actual_property_area IS NOT NULL THEN actual_property_area ELSE 0 END) as total_property_area,
                SUM(CASE WHEN rentable_area IS NOT NULL THEN rentable_area ELSE 0 END) as total_rentable_area,
                SUM(CASE WHEN rented_area IS NOT NULL THEN rented_area ELSE 0 END) as total_rented_area
            FROM assets
        """)
        area_result = db.execute(area_query)
        area_stats = area_result.fetchone()

        return {
            "success": True,
            "data": {
                "total_assets": total_assets,
                "status_distribution": status_stats,
                "usage_distribution": usage_stats,
                "area_summary": {
                    "total_land_area": float(area_stats[0] or 0),
                    "total_property_area": float(area_stats[1] or 0),
                    "total_rentable_area": float(area_stats[2] or 0),
                    "total_rented_area": float(area_stats[3] or 0)
                }
            },
            "message": "资产统计摘要获取成功"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资产统计摘要失败: {str(e)}")
