"""
资产管理API路由
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from database import get_db
from models.asset import Asset
from schemas.asset import AssetCreate, AssetUpdate, AssetResponse, AssetListResponse
from crud.asset import asset_crud
from crud.history import history_crud
from exceptions import AssetNotFoundError, DuplicateAssetError, BusinessLogicError

# 创建资产路由器
router = APIRouter()


@router.get("/", response_model=AssetListResponse, summary="获取资产列表")
async def get_assets(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    ownership_status: Optional[str] = Query(None, description="确权状态筛选"),
    property_nature: Optional[str] = Query(None, description="物业性质筛选"),
    usage_status: Optional[str] = Query(None, description="使用状态筛选"),
    ownership_entity: Optional[str] = Query(None, description="权属方筛选"),
    management_entity: Optional[str] = Query(None, description="经营管理方筛选"),
    business_category: Optional[str] = Query(None, description="业态类别筛选"),
    min_area: Optional[float] = Query(None, ge=0, description="最小面积筛选"),
    max_area: Optional[float] = Query(None, ge=0, description="最大面积筛选"),
    is_litigated: Optional[str] = Query(None, description="是否涉诉筛选"),
    db: Session = Depends(get_db),
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
        assets, total = asset_crud.get_multi_with_search(
            db=db,
            skip=(page - 1) * limit,
            limit=limit,
            search=search,
            filters=filters,
            sort_field=sort_field,
            sort_order=sort_order
        )

        return AssetListResponse(
            items=assets,
            total=total,
            page=page,
            limit=limit,
            pages=(total + limit - 1) // limit
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资产列表失败: {str(e)}")


@router.get("/{asset_id}", response_model=AssetResponse, summary="获取资产详情")
async def get_asset(
    asset_id: str = Path(..., description="资产ID"),
    db: Session = Depends(get_db)
):
    """
    根据ID获取单个资产的详细信息
    
    - **asset_id**: 资产ID
    """
    try:
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise AssetNotFoundError(asset_id)
        return asset
    except AssetNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资产详情失败: {str(e)}")


@router.post("/", response_model=AssetResponse, summary="创建新资产", status_code=201)
async def create_asset(
    asset_in: AssetCreate,
    db: Session = Depends(get_db)
):
    """
    创建新的资产记录
    
    - **asset_in**: 资产创建数据
    """
    try:
        # 检查是否存在同名资产
        existing_asset = asset_crud.get_by_name(db=db, property_name=asset_in.property_name)
        if existing_asset:
            raise DuplicateAssetError(asset_in.property_name)
        
        # 创建资产并记录历史
        asset = asset_crud.create_with_history(db=db, obj_in=asset_in)
        return asset
        
    except DuplicateAssetError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建资产失败: {str(e)}")


@router.put("/{asset_id}", response_model=AssetResponse, summary="更新资产")
async def update_asset(
    asset_id: str = Path(..., description="资产ID"),
    asset_in: AssetUpdate = None,
    db: Session = Depends(get_db)
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
            raise AssetNotFoundError(asset_id)
        
        # 如果更新了物业名称，检查是否重复
        if asset_in.property_name and asset_in.property_name != asset.property_name:
            existing_asset = asset_crud.get_by_name(db=db, property_name=asset_in.property_name)
            if existing_asset and existing_asset.id != asset_id:
                raise DuplicateAssetError(asset_in.property_name)
        
        # 更新资产并记录历史
        updated_asset = asset_crud.update_with_history(
            db=db,
            db_obj=asset,
            obj_in=asset_in
        )
        return updated_asset
        
    except (AssetNotFoundError, DuplicateAssetError):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新资产失败: {str(e)}")


@router.delete("/{asset_id}", summary="删除资产")
async def delete_asset(
    asset_id: str = Path(..., description="资产ID"),
    db: Session = Depends(get_db)
):
    """
    删除资产记录
    
    - **asset_id**: 资产ID
    """
    try:
        # 检查资产是否存在
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise AssetNotFoundError(asset_id)
        
        # 删除资产
        asset_crud.remove(db=db, id=asset_id)
        return {"message": f"资产 {asset_id} 已成功删除"}
        
    except AssetNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除资产失败: {str(e)}")


@router.get("/{asset_id}/history", summary="获取资产历史")
async def get_asset_history(
    asset_id: str = Path(..., description="资产ID"),
    db: Session = Depends(get_db)
):
    """
    获取资产的变更历史记录
    
    - **asset_id**: 资产ID
    """
    try:
        # 检查资产是否存在
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise AssetNotFoundError(asset_id)
        
        # 获取历史记录
        history_records = history_crud.get_by_asset_id(db=db, asset_id=asset_id)
        return {"asset_id": asset_id, "history": history_records}
        
    except AssetNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资产历史失败: {str(e)}")


@router.get("/statistics/summary", summary="获取资产统计摘要")
async def get_asset_statistics(
    db: Session = Depends(get_db)
):
    """
    获取资产统计摘要信息
    """
    try:
        # 总资产数
        total_assets = asset_crud.count(db=db)
        
        # 按确权状态统计
        confirmed_count = asset_crud.count_with_search(
            db=db, filters={"ownership_status": "已确权"}
        )
        unconfirmed_count = asset_crud.count_with_search(
            db=db, filters={"ownership_status": "未确权"}
        )
        partial_count = asset_crud.count_with_search(
            db=db, filters={"ownership_status": "部分确权"}
        )
        
        # 按物业性质统计
        commercial_count = asset_crud.count_with_search(
            db=db, filters={"property_nature": "经营性"}
        )
        non_commercial_count = asset_crud.count_with_search(
            db=db, filters={"property_nature": "非经营性"}
        )
        
        # 按使用状态统计
        rented_count = asset_crud.count_with_search(
            db=db, filters={"usage_status": "出租"}
        )
        self_used_count = asset_crud.count_with_search(
            db=db, filters={"usage_status": "自用"}
        )
        vacant_count = asset_crud.count_with_search(
            db=db, filters={"usage_status": "空置"}
        )
        
        return {
            "total_assets": total_assets,
            "ownership_status": {
                "confirmed": confirmed_count,
                "unconfirmed": unconfirmed_count,
                "partial": partial_count
            },
            "property_nature": {
                "commercial": commercial_count,
                "non_commercial": non_commercial_count
            },
            "usage_status": {
                "rented": rented_count,
                "self_used": self_used_count,
                "vacant": vacant_count
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")