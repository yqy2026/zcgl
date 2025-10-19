"""
权属方相关API端点
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from ...database import get_db
from ...crud.ownership import ownership
from ...schemas.ownership import (
    OwnershipCreate,
    OwnershipUpdate,
    OwnershipResponse,
    OwnershipListResponse,
    OwnershipDeleteResponse,
    OwnershipSearchRequest,
    OwnershipStatisticsResponse
)

router = APIRouter()


@router.get("/dropdown-options", summary="获取权属方选项列表")
async def get_ownership_options(
    db: Session = Depends(get_db),
    is_active: Optional[bool] = Query(True, description="是否启用")
):
    """获取权属方选项列表（用于下拉选择等）"""
    try:
        ownerships = ownership.get_multi(
            db, skip=0, limit=1000, is_active=is_active
        )
        # 为下拉选项添加关联计数
        responses = []
        for item in ownerships:
            response = OwnershipResponse.model_validate(item)
            # 获取关联资产数量
            response.asset_count = ownership.get_asset_count(db, item.id)
            # 获取关联项目数量
            response.project_count = ownership.get_project_count(db, item.id)
            responses.append(response)
        return responses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取权属方选项失败: {str(e)}")


@router.post("/", response_model=OwnershipResponse, summary="创建权属方")
async def create_ownership(
    *,
    db: Session = Depends(get_db),
    ownership_in: OwnershipCreate
):
    """创建新权属方"""
    try:
        db_ownership = ownership.create(db, obj_in=ownership_in)
        return OwnershipResponse.model_validate(db_ownership)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建权属方失败: {str(e)}")


@router.get("/{ownership_id}", response_model=OwnershipResponse, summary="获取权属方详情")
async def get_ownership(
    ownership_id: str,
    db: Session = Depends(get_db)
):
    """获取指定权属方的详细信息"""
    db_ownership = ownership.get(db, id=ownership_id)
    if not db_ownership:
        raise HTTPException(status_code=404, detail="权属方不存在")

    # 获取关联资产数量
    asset_count = ownership.get_asset_count(db, ownership_id)
    # 获取关联项目数量
    project_count = ownership.get_project_count(db, ownership_id)

    response = OwnershipResponse.from_orm(db_ownership)
    response.asset_count = asset_count
    response.project_count = project_count
    return response


@router.put("/{ownership_id}", response_model=OwnershipResponse, summary="更新权属方")
async def update_ownership(
    *,
    db: Session = Depends(get_db),
    ownership_id: str,
    ownership_in: OwnershipUpdate
):
    """更新权属方信息"""
    db_ownership = ownership.get(db, id=ownership_id)
    if not db_ownership:
        raise HTTPException(status_code=404, detail="权属方不存在")

    try:
        updated_ownership = ownership.update(
            db, db_obj=db_ownership, obj_in=ownership_in
        )
        return OwnershipResponse.from_orm(updated_ownership)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新权属方失败: {str(e)}")


@router.put("/{ownership_id}/projects", summary="更新权属方关联项目")
async def update_ownership_projects(
    *,
    db: Session = Depends(get_db),
    ownership_id: str,
    project_ids: List[str] = Body(..., description="关联项目ID列表")
):
    """更新权属方的关联项目"""
    db_ownership = ownership.get(db, id=ownership_id)
    if not db_ownership:
        raise HTTPException(status_code=404, detail="权属方不存在")

    try:
        # 更新关联项目
        ownership.update_related_projects(db, ownership_id=ownership_id, project_ids=project_ids)

        # 返回更新后的权属方信息
        updated_ownership = ownership.get(db, id=ownership_id)
        response = OwnershipResponse.from_orm(updated_ownership)

        # 获取实际的项目计数
        actual_project_count = ownership.get_project_count(db, ownership_id)
        response.project_count = actual_project_count
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新关联项目失败: {str(e)}")


@router.delete("/{ownership_id}", response_model=OwnershipDeleteResponse, summary="删除权属方")
async def delete_ownership(
    *,
    db: Session = Depends(get_db),
    ownership_id: str
):
    """删除权属方"""
    try:
        # 先检查关联资产数量
        asset_count = ownership.get_asset_count(db, ownership_id)

        deleted_ownership = ownership.delete(db, id=ownership_id)
        return OwnershipDeleteResponse(
            message="权属方删除成功",
            id=deleted_ownership.id,
            affected_assets=asset_count
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除权属方失败: {str(e)}")




@router.get("/", response_model=OwnershipListResponse, summary="获取权属方列表")
async def get_ownerships(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    is_active: Optional[bool] = Query(None, description="是否启用")
):
    """获取权属方列表"""
    search_params = OwnershipSearchRequest(
        page=page,
        size=size,
        keyword=keyword,
        is_active=is_active
    )

    result = ownership.search(db, search_params)

    # 转换为响应格式，并添加关联计数
    items = []
    for item in result["items"]:
        response = OwnershipResponse.from_orm(item)
        # 获取关联资产数量
        response.asset_count = ownership.get_asset_count(db, item.id)
        # 获取关联项目数量
        response.project_count = ownership.get_project_count(db, item.id)
        items.append(response)

    return OwnershipListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"]
    )


@router.post("/search", response_model=OwnershipListResponse, summary="搜索权属方")
async def search_ownerships(
    *,
    db: Session = Depends(get_db),
    search_params: OwnershipSearchRequest
):
    """搜索权属方"""
    result = ownership.search(db, search_params)

    # 转换为响应格式，并添加关联计数
    items = []
    for item in result["items"]:
        response = OwnershipResponse.from_orm(item)
        # 获取关联资产数量
        response.asset_count = ownership.get_asset_count(db, item.id)
        # 获取关联项目数量
        response.project_count = ownership.get_project_count(db, item.id)
        items.append(response)

    return OwnershipListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"]
    )


@router.get("/statistics/summary", response_model=OwnershipStatisticsResponse, summary="获取权属方统计")
async def get_ownership_statistics(
    db: Session = Depends(get_db)
):
    """获取权属方统计信息"""
    stats = ownership.get_statistics(db)

    # 转换最近创建的权属方
    recent_created = [OwnershipResponse.model_validate(item) for item in stats["recent_created"]]

    return OwnershipStatisticsResponse(
        total_count=stats["total_count"],
        active_count=stats["active_count"],
        inactive_count=stats["inactive_count"],
        recent_created=recent_created
    )




@router.post("/{ownership_id}/toggle-status", response_model=OwnershipResponse, summary="切换权属方状态")
async def toggle_ownership_status(
    *,
    db: Session = Depends(get_db),
    ownership_id: str
):
    """切换权属方启用/禁用状态"""
    try:
        db_ownership = ownership.toggle_status(db, id=ownership_id)
        return OwnershipResponse.model_validate(db_ownership)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换状态失败: {str(e)}")




