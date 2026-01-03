"""
项目管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from ...crud.project import project_crud
from ...database import get_db
from ...middleware.auth import get_current_active_user
from ...models.auth import User
from ...schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectSearchRequest,
    ProjectUpdate,
)
from ...services.project import project_service

router = APIRouter(prefix="/projects", tags=["项目管理"])


@router.post("/", response_model=ProjectResponse, summary="创建项目")
async def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    创建新项目
    """
    try:
        project = project_service.create_project(
            db=db, obj_in=project_in, created_by=current_user.id
        )
        return project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")


@router.post("/search", response_model=ProjectListResponse, summary="搜索项目")
async def search_projects(
    search_params: ProjectSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    搜索项目列表
    """
    try:
        result = project_service.search_projects(db=db, search_params=search_params)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索项目失败: {str(e)}")


@router.get("/{project_id}", response_model=ProjectResponse, summary="获取项目详情")
async def get_project(
    project_id: str = Path(..., description="项目ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取项目详情
    """
    project = project_crud.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.put("/{project_id}", response_model=ProjectResponse, summary="更新项目")
async def update_project(
    project_id: str = Path(..., description="项目ID"),
    project_in: ProjectUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新项目信息
    """
    try:
        project = project_service.update_project(
            db=db, project_id=project_id, obj_in=project_in, updated_by=current_user.id
        )
        return project
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新项目失败: {str(e)}")


@router.delete("/{project_id}", summary="删除项目")
async def delete_project(
    project_id: str = Path(..., description="项目ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    删除项目
    """
    try:
        project_service.delete_project(db=db, project_id=project_id)
        return {"message": "项目删除成功"}
    except ValueError as e:
        if "资产" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除项目失败: {str(e)}")


@router.put("/{project_id}/status", response_model=ProjectResponse, summary="切换状态")
async def toggle_project_status(
    project_id: str = Path(..., description="项目ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    切换项目状态 (暂停/恢复)
    """
    try:
        project = project_service.toggle_status(
            db=db, project_id=project_id, updated_by=current_user.id
        )
        return project
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换状态失败: {str(e)}")


@router.get("/options/dropdown", summary="获取项目下拉选项")
async def get_project_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取项目下拉列表选项
    """
    return project_service.get_dropdown_options(db=db)


@router.get("/stats/overview", summary="获取项目统计")
async def get_project_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取项目统计概览
    """
    return project_crud.get_statistics(db=db)
