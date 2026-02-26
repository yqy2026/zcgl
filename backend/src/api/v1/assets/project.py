"""
项目管理API路由
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import (
    BaseBusinessError,
    forbidden,
    internal_error,
    not_found,
)
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....database import get_async_db
from ....middleware.auth import AuthzContext, get_current_active_user, require_authz
from ....models.auth import User
from ....schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectSearchRequest,
    ProjectUpdate,
)
from ....services.authz import authz_service
from ....services.project import project_service

router = APIRouter()
_PROJECT_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:project:create"


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "":
        return None
    return normalized


async def _require_project_create_authz(
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    manager_party_id = _normalize_optional_str(project_in.manager_party_id)
    organization_id = _normalize_optional_str(project_in.organization_id)
    project_in.manager_party_id = manager_party_id
    project_in.organization_id = organization_id
    if manager_party_id is None and organization_id is not None:
        manager_party_id = organization_id
        project_in.manager_party_id = manager_party_id
    resource_context: dict[str, Any] = {}
    if manager_party_id is not None:
        resource_context["manager_party_id"] = manager_party_id
    if organization_id is not None:
        resource_context["organization_id"] = organization_id
    resource_context["party_id"] = (
        manager_party_id or organization_id or _PROJECT_CREATE_UNSCOPED_PARTY_ID
    )

    try:
        decision = await authz_service.check_access(
            db,
            user_id=str(current_user.id),
            resource_type="project",
            action="create",
            resource_id=None,
            resource=resource_context,
        )
    except Exception:
        raise forbidden("权限校验失败")

    if not decision.allowed:
        raise forbidden("权限不足")

    return AuthzContext(
        current_user=current_user,
        action="create",
        resource_type="project",
        resource_id=None,
        resource_context=resource_context,
        allowed=True,
        reason_code=decision.reason_code,
    )


@router.post("", response_model=ProjectResponse, summary="创建项目")
@router.post("/", response_model=ProjectResponse, summary="创建项目")
async def create_project(
    project_in: ProjectCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz_ctx: AuthzContext = Depends(_require_project_create_authz),
) -> ProjectResponse:
    """
    创建新项目
    """
    try:
        if isinstance(_authz_ctx, AuthzContext):
            resolved_manager_party_id = _normalize_optional_str(
                _authz_ctx.resource_context.get("manager_party_id")
            )
            if (
                _normalize_optional_str(project_in.manager_party_id) is None
                and resolved_manager_party_id is not None
            ):
                project_in.manager_party_id = resolved_manager_party_id
        default_org_id = getattr(current_user, "default_organization_id", None)
        organization_id = (
            str(default_org_id)
            if default_org_id is not None and str(default_org_id).strip() != ""
            else None
        )
        project = await project_service.create_project(
            db=db,
            obj_in=project_in,
            created_by=current_user.id,
            organization_id=organization_id,
        )
        return project_service.project_to_response(project)
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
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="project")
    ),
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
            db=db,
            search_params=search_params,
            current_user_id=str(current_user.id),
        )
        items = [project_service.project_to_response(item) for item in result.get("items", [])]
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
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="project")
    ),
) -> Any:
    """
    搜索项目列表
    """
    try:
        result = await project_service.search_projects(
            db=db,
            search_params=search_params,
            current_user_id=str(current_user.id),
        )
        items = [project_service.project_to_response(item) for item in result.get("items", [])]
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
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="project")
    ),
    is_active: bool | None = Query(True, description="是否仅返回启用项目"),
) -> list[dict[str, Any]]:
    """获取项目下拉列表选项（标准端点）"""
    return await project_service.get_project_dropdown_options(
        db,
        is_active=is_active,
        current_user_id=str(current_user.id),
    )


@router.get("/stats/overview", summary="获取项目统计")
async def get_project_statistics(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="project")
    ),
) -> dict[str, Any]:
    """
    获取项目统计概览
    """
    return await project_service.get_project_statistics(
        db=db,
        current_user_id=str(current_user.id),
    )


@router.get("/{project_id}", response_model=ProjectResponse, summary="获取项目详情")
async def get_project(
    project_id: Annotated[str, Path(description="项目ID")],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="project",
            resource_id="{project_id}",
            deny_as_not_found=True,
        )
    ),
) -> ProjectResponse:
    """
    获取项目详情
    """
    project = await project_service.get_project_by_id(
        db=db,
        project_id=project_id,
        current_user_id=str(current_user.id),
    )
    if not project:
        raise not_found("项目不存在", resource_type="project", resource_id=project_id)
    return project_service.project_to_response(project)


@router.put("/{project_id}", response_model=ProjectResponse, summary="更新项目")
async def update_project(
    project_id: Annotated[str, Path(description="项目ID")],
    project_in: ProjectUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="project",
            resource_id="{project_id}",
        )
    ),
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
            current_user_id=str(current_user.id),
        )
        return project_service.project_to_response(project)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"更新项目失败: {str(e)}")


@router.delete("/{project_id}", summary="删除项目")
async def delete_project(
    project_id: Annotated[str, Path(description="项目ID")],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="delete",
            resource_type="project",
            resource_id="{project_id}",
        )
    ),
) -> dict[str, str]:
    """
    删除项目
    """
    try:
        await project_service.delete_project(
            db=db,
            project_id=project_id,
            current_user_id=str(current_user.id),
        )
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
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="project",
            resource_id="{project_id}",
        )
    ),
) -> ProjectResponse:
    """
    切换项目状态 (暂停/恢复)
    """
    try:
        project = await project_service.toggle_status(
            db=db,
            project_id=project_id,
            updated_by=current_user.id,
            current_user_id=str(current_user.id),
        )
        return project_service.project_to_response(project)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"切换状态失败: {str(e)}")
