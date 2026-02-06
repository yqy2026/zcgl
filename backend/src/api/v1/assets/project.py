"""
项目管理API路由
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import (
    BaseBusinessError,
    internal_error,
    not_found,
)
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....crud.project import project_crud
from ....database import get_async_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectSearchRequest,
    ProjectUpdate,
)
from ....services.project import project_service

router = APIRouter()


def _project_to_response(project: Any) -> ProjectResponse:
    data = {
        attr.key: getattr(project, attr.key)
        for attr in sa_inspect(project).mapper.column_attrs
    }
    data["ownership_relations"] = []
    return ProjectResponse.model_validate(data)


@router.post("", response_model=ProjectResponse, summary="创建项目")
@router.post("/", response_model=ProjectResponse, summary="创建项目")
async def create_project(
    project_in: ProjectCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ProjectResponse:
    """
    创建新项目
    """
    try:
        project = await project_service.create_project(
            db=db, obj_in=project_in, created_by=current_user.id
        )
        return _project_to_response(project)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"创建项目失败: {str(e)}")


@router.get(
    "",
    response_model=APIResponse[PaginatedData[ProjectResponse]],
    summary="获取项目列表",
)
@router.get(
    "/",
    response_model=APIResponse[PaginatedData[ProjectResponse]],
    summary="获取项目列表",
)
async def list_projects(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    page: int = 1,
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    is_active: bool | None = None,
    ownership_id: str | None = None,
    project_status: str | None = None,
) -> Any:
    """
    获取项目列表，支持分页和筛选

    分页参数使用 page/page_size
    """
    try:
        search_params = ProjectSearchRequest(
            page=page,
            page_size=page_size,
            keyword=keyword,
            is_active=is_active,
            project_type=None,
            project_status=project_status,
            city=None,
            ownership_id=ownership_id,
            ownership_entity=None,
        )
        result = await project_service.search_projects(
            db=db, search_params=search_params
        )
        items = [_project_to_response(item) for item in result.get("items", [])]
        return ResponseHandler.paginated(
            data=items,
            page=result.get("page", page),
            page_size=result.get("page_size", page_size),
            total=result.get("total", 0),
            message="获取项目列表成功",
        )
    except Exception as e:
        raise internal_error(f"获取项目列表失败: {str(e)}")


@router.post(
    "/search",
    response_model=APIResponse[PaginatedData[ProjectResponse]],
    summary="搜索项目",
)
async def search_projects(
    search_params: ProjectSearchRequest,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Any:
    """
    搜索项目列表
    """
    try:
        result = await project_service.search_projects(
            db=db, search_params=search_params
        )
        items = [_project_to_response(item) for item in result.get("items", [])]
        return ResponseHandler.paginated(
            data=items,
            page=result.get("page", search_params.page),
            page_size=result.get("page_size", search_params.page_size),
            total=result.get("total", 0),
            message="搜索项目成功",
        )
    except Exception as e:
        raise internal_error(f"搜索项目失败: {str(e)}")


@router.get("/dropdown-options", summary="获取项目下拉选项")
async def get_project_options(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    is_active: bool | None = Query(True, description="是否仅返回启用项目"),
) -> list[dict[str, Any]]:
    """获取项目下拉列表选项（标准端点）"""
    return await project_service.get_project_dropdown_options(db, is_active=is_active)


@router.get("/stats/overview", summary="获取项目统计")
async def get_project_statistics(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict[str, Any]:
    """
    获取项目统计概览
    """
    return await project_crud.get_statistics(db=db)


@router.get("/{project_id}", response_model=ProjectResponse, summary="获取项目详情")
async def get_project(
    project_id: Annotated[str, Path(description="项目ID")],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ProjectResponse:
    """
    获取项目详情
    """
    project = await project_crud.get(db=db, id=project_id)
    if not project:
        raise not_found("项目不存在", resource_type="project", resource_id=project_id)
    return _project_to_response(project)


@router.put("/{project_id}", response_model=ProjectResponse, summary="更新项目")
async def update_project(
    project_id: Annotated[str, Path(description="项目ID")],
    project_in: ProjectUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ProjectResponse:
    """
    更新项目信息
    """
    try:
        project = await project_service.update_project(
            db=db,
            project_id=project_id,
            obj_in=project_in,
            updated_by=current_user.id,
        )
        return _project_to_response(project)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"更新项目失败: {str(e)}")


@router.delete("/{project_id}", summary="删除项目")
async def delete_project(
    project_id: Annotated[str, Path(description="项目ID")],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict[str, str]:
    """
    删除项目
    """
    try:
        await project_service.delete_project(db=db, project_id=project_id)
        return {"message": "项目删除成功"}
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"删除项目失败: {str(e)}")


@router.put("/{project_id}/status", response_model=ProjectResponse, summary="切换状态")
async def toggle_project_status(
    project_id: Annotated[str, Path(description="项目ID")],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ProjectResponse:
    """
    切换项目状态 (暂停/恢复)
    """
    try:
        project = await project_service.toggle_status(
            db=db, project_id=project_id, updated_by=current_user.id
        )
        return _project_to_response(project)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"切换状态失败: {str(e)}")
