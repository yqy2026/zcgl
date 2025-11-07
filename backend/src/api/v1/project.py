"""
项目管理相关API端点
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...crud.project import project
from ...database import get_db
from ...schemas.project import (
    ProjectCreate,
    ProjectDeleteResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectSearchRequest,
    ProjectUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dropdown-options", summary="获取项目选项列表")
async def get_project_options(
    db: Session = Depends(get_db),
    is_active: bool | None = Query(True, description="是否启用"),
):
    """获取项目选项列表（用于下拉选择等）"""
    try:
        options = project.get_dropdown_options(db)
        return options
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取项目选项失败: {str(e)}")


@router.post("/", response_model=ProjectResponse, summary="创建项目")
async def create_project(*, db: Session = Depends(get_db), project_in: ProjectCreate):
    """创建新项目"""
    try:
        db_project = project.create(db, obj_in=project_in, created_by="system")
        return ProjectResponse.model_validate(db_project)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")


@router.get("/{project_id}", response_model=ProjectResponse, summary="获取项目详情")
async def get_project(project_id: str, db: Session = Depends(get_db)):
    """获取指定项目的详细信息"""
    db_project = project.get(db, id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 获取关联资产数量
    asset_count = project.get_asset_count(db, project_id)

    # 获取权属方关系数据
    ownership_relations_data = []
    if hasattr(db_project, "ownership_relations") and db_project.ownership_relations:
        for relation in db_project.ownership_relations:
            if hasattr(relation, "ownership") and relation.ownership:
                ownership_relations_data.append(
                    {
                        "id": relation.id,
                        "project_id": relation.project_id,
                        "ownership_id": relation.ownership_id,
                        "ownership_name": relation.ownership.name
                        if relation.ownership
                        else None,
                        "ownership_code": relation.ownership.code
                        if relation.ownership
                        else None,
                        "ownership_short_name": relation.ownership.short_name
                        if relation.ownership
                        else None,
                        "is_active": relation.is_active,
                        "created_at": relation.created_at,
                        "updated_at": relation.updated_at,
                    }
                )

    # 手动创建响应对象
    response_dict = {
        "id": db_project.id,
        "name": db_project.name,
        "short_name": db_project.short_name,
        "code": db_project.code,
        "project_type": db_project.project_type,
        "project_scale": db_project.project_scale,
        "project_status": db_project.project_status,
        "start_date": db_project.start_date,
        "end_date": db_project.end_date,
        "expected_completion_date": db_project.expected_completion_date,
        "actual_completion_date": db_project.actual_completion_date,
        "address": db_project.address,
        "city": db_project.city,
        "district": db_project.district,
        "province": db_project.province,
        "project_manager": db_project.project_manager,
        "project_phone": db_project.project_phone,
        "project_email": db_project.project_email,
        "total_investment": db_project.total_investment,
        "planned_investment": db_project.planned_investment,
        "actual_investment": db_project.actual_investment,
        "project_budget": db_project.project_budget,
        "project_description": db_project.project_description,
        "project_objectives": db_project.project_objectives,
        "project_scope": db_project.project_scope,
        "management_entity": db_project.management_entity,
        "ownership_entity": db_project.ownership_entity,
        "construction_company": db_project.construction_company,
        "design_company": db_project.design_company,
        "supervision_company": db_project.supervision_company,
        "is_active": db_project.is_active,
        "data_status": db_project.data_status,
        "created_at": db_project.created_at,
        "updated_at": db_project.updated_at,
        "created_by": db_project.created_by,
        "updated_by": db_project.updated_by,
        "asset_count": asset_count,
        "ownership_relations": ownership_relations_data,
    }
    return response_dict


@router.put("/{project_id}", response_model=ProjectResponse, summary="更新项目")
async def update_project(
    *, db: Session = Depends(get_db), project_id: str, project_in: ProjectUpdate
):
    """更新项目信息"""
    db_project = project.get(db, id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="项目不存在")

    try:
        updated_project = project.update(
            db, db_obj=db_project, obj_in=project_in, updated_by="system"
        )
        return ProjectResponse.model_validate(updated_project)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新项目失败: {str(e)}")


@router.delete(
    "/{project_id}", response_model=ProjectDeleteResponse, summary="删除项目"
)
async def delete_project(*, db: Session = Depends(get_db), project_id: str):
    """删除项目"""
    try:
        # 先检查关联资产数量
        asset_count = project.get_asset_count(db, project_id)

        deleted_project = project.delete(db, id=project_id)
        return ProjectDeleteResponse(
            message="项目删除成功",
            deleted_id=deleted_project.id,
            affected_assets=asset_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除项目失败: {str(e)}")


@router.get("/", response_model=ProjectListResponse, summary="获取项目列表")
async def get_projects(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: str | None = Query(None, description="搜索关键词"),
    is_active: bool | None = Query(None, description="是否启用"),
    project_type: str | None = Query(None, description="项目类型"),
    project_status: str | None = Query(None, description="项目状态"),
    city: str | None = Query(None, description="城市"),
    ownership_id: str | None = Query(None, description="权属方ID"),
    ownership_entity: str | None = Query(None, description="权属方名称"),
):
    """获取项目列表"""
    search_params = ProjectSearchRequest(
        page=page,
        size=size,
        keyword=keyword,
        is_active=is_active,
        project_type=project_type,
        project_status=project_status,
        city=city,
        ownership_id=ownership_id,
        ownership_entity=ownership_entity,
    )

    result = project.search(db, search_params)

    # 转换为响应格式，使用ownership_relations_data而不是SQLAlchemy关系
    items = []
    for item in result["items"]:
        # 直接使用model_validate转换，CRUD层已经处理了ownership_relations_data
        item_dict = ProjectResponse.model_validate(item)
        items.append(item_dict)

    return ProjectListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"],
    )


@router.post("/search", response_model=ProjectListResponse, summary="搜索项目")
async def search_projects(
    *, db: Session = Depends(get_db), search_params: ProjectSearchRequest
):
    """搜索项目"""
    result = project.search(db, search_params)

    # 转换为响应格式，使用ownership_relations_data而不是SQLAlchemy关系
    items = []
    for item in result["items"]:
        # 直接使用model_validate转换，CRUD层已经处理了ownership_relations_data
        item_dict = ProjectResponse.model_validate(item)
        items.append(item_dict)

    return ProjectListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"],
    )


@router.get("/statistics/summary", summary="获取项目统计")
async def get_project_statistics(db: Session = Depends(get_db)):
    """获取项目统计信息"""
    try:
        stats = project.get_statistics(db)

        # 转换最近创建的项目
        recent_created = [
            ProjectResponse.model_validate(item) for item in stats["recent_created"]
        ]

        response_data = {
            "total_count": stats["total_count"],
            "active_count": stats["active_count"],
            "inactive_count": stats["inactive_count"],
            "type_distribution": stats.get("type_distribution"),
            "status_distribution": stats.get("status_distribution"),
            "city_distribution": stats.get("city_distribution"),
            "investment_stats": stats.get("investment_stats"),
            "recent_created": [],
        }

        # Convert each recent project to dict and handle datetime serialization
        for item in recent_created:
            item_dict = item.model_dump()
            # Handle datetime serialization manually
            for key, value in item_dict.items():
                if hasattr(value, "isoformat"):
                    item_dict[key] = value.isoformat()
            response_data["recent_created"].append(item_dict)

        return response_data
    except Exception as e:
        # Log the actual error for debugging
        logger.error(f"Statistics API error: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Statistics calculation failed: {str(e)}"
        )


@router.post(
    "/{project_id}/toggle-status",
    response_model=ProjectResponse,
    summary="切换项目状态",
)
async def toggle_project_status(*, db: Session = Depends(get_db), project_id: str):
    """切换项目启用/禁用状态"""
    try:
        db_project = project.toggle_status(db, id=project_id, updated_by="system")
        return ProjectResponse.model_validate(db_project)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换状态失败: {str(e)}")
