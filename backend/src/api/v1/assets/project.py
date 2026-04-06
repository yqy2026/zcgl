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
from ....crud.party import party_crud
from ....crud.query_builder import PartyFilter
from ....database import get_async_db
from ....middleware.auth import (
    AuthzContext,
    DataScopeContext,
    get_current_active_user,
    require_authz,
    require_data_scope_context,
)
from ....models.auth import User
from ....schemas.asset import AssetListItemResponse
from ....schemas.project import (
    ProjectActiveAssetsResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectSearchRequest,
    ProjectStatisticsResponse,
    ProjectUpdate,
)
from ....services.authz import authz_service
from ....services.party_scope import build_party_filter_from_scope_context
from ....services.project import project_service

router = APIRouter()
_PROJECT_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:project:create"
ProjectActiveAssetsResponse.model_rebuild(
    _types_namespace={"AssetListItemResponse": AssetListItemResponse}
)


def _build_project_party_filter(
    scope_context: DataScopeContext,
) -> PartyFilter:
    return build_party_filter_from_scope_context(scope_context)


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "":
        return None
    return normalized


def _normalize_identifier_sequence(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []

    normalized_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized_value = _normalize_optional_str(value)
        if normalized_value is None or normalized_value in seen:
            continue
        seen.add(normalized_value)
        normalized_values.append(normalized_value)
    return normalized_values


def _resolve_current_user_organization_id(current_user: User) -> str | None:
    return _normalize_optional_str(
        getattr(current_user, "default_organization_id", None)
    )


def _resolve_effective_organization_id(
    *,
    project_in: ProjectCreate,
    current_user: User,
) -> str | None:
    request_organization_id = _normalize_optional_str(project_in.organization_id)
    if request_organization_id is not None:
        return request_organization_id
    return _resolve_current_user_organization_id(current_user)


async def _resolve_organization_party_id(
    *,
    db: AsyncSession,
    organization_id: str | None,
) -> str | None:
    normalized_organization_id = _normalize_optional_str(organization_id)
    if normalized_organization_id is None:
        return None

    try:
        resolved_party_id = await party_crud.resolve_organization_party_id(
            db,
            organization_id=normalized_organization_id,
        )
    except Exception:
        return None
    return _normalize_optional_str(resolved_party_id)


async def _build_subject_scope_hint(
    *,
    db: AsyncSession,
    user_id: str,
) -> dict[str, Any]:
    try:
        subject_context = await authz_service.context_builder.build_subject_context(
            db,
            user_id=user_id,
        )
    except Exception:
        return {}

    owner_party_ids = _normalize_identifier_sequence(
        getattr(subject_context, "owner_party_ids", [])
    )
    manager_party_ids = _normalize_identifier_sequence(
        getattr(subject_context, "manager_party_ids", [])
    )

    scope_hint: dict[str, Any] = {}
    if len(owner_party_ids) > 0:
        scope_hint["owner_party_id"] = owner_party_ids[0]
        scope_hint["owner_party_ids"] = owner_party_ids
    if len(manager_party_ids) > 0:
        scope_hint["manager_party_id"] = manager_party_ids[0]
        scope_hint["manager_party_ids"] = manager_party_ids

    if len(manager_party_ids) > 0:
        scope_hint["party_id"] = manager_party_ids[0]
    elif len(owner_party_ids) > 0:
        scope_hint["party_id"] = owner_party_ids[0]

    return scope_hint


async def _require_project_create_authz(
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    manager_party_id = _normalize_optional_str(project_in.manager_party_id)
    request_organization_id = _normalize_optional_str(project_in.organization_id)
    effective_organization_id = _resolve_effective_organization_id(
        project_in=project_in,
        current_user=current_user,
    )
    project_in.manager_party_id = manager_party_id
    project_in.organization_id = request_organization_id

    if manager_party_id is None and effective_organization_id is not None:
        resolved_party_id = await _resolve_organization_party_id(
            db=db,
            organization_id=effective_organization_id,
        )
        if resolved_party_id is not None:
            manager_party_id = resolved_party_id
            project_in.manager_party_id = resolved_party_id

    resource_context: dict[str, Any] = {}
    if manager_party_id is not None:
        resource_context["manager_party_id"] = manager_party_id
    if effective_organization_id is not None:
        resource_context["organization_id"] = effective_organization_id
    if manager_party_id is None:
        subject_scope_hint = await _build_subject_scope_hint(
            db=db,
            user_id=str(current_user.id),
        )
        for key, value in subject_scope_hint.items():
            resource_context.setdefault(key, value)
        inferred_manager_party_id = _normalize_optional_str(
            resource_context.get("manager_party_id")
        )
        if inferred_manager_party_id is not None:
            manager_party_id = inferred_manager_party_id
            project_in.manager_party_id = inferred_manager_party_id
            resource_context["manager_party_id"] = inferred_manager_party_id

    resource_context["party_id"] = (
        manager_party_id
        or _normalize_optional_str(resource_context.get("party_id"))
        or effective_organization_id
        or _PROJECT_CREATE_UNSCOPED_PARTY_ID
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
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="project")
    ),
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
            resolved_organization_id = _normalize_optional_str(
                _authz_ctx.resource_context.get("organization_id")
            )
        else:
            resolved_organization_id = None

        organization_id = (
            resolved_organization_id
            or _resolve_effective_organization_id(
                project_in=project_in,
                current_user=current_user,
            )
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
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="project")
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="project")
    ),
    page: int = 1,
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    owner_party_id: str | None = None,
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
            status=status,
            owner_party_id=owner_party_id,
        )
        result = await project_service.search_projects(
            db=db,
            search_params=search_params,
            current_user_id=str(current_user.id),
            party_filter=_build_project_party_filter(_scope_ctx),
        )
        items = [
            project_service.project_to_response(item)
            for item in result.get("items", [])
        ]
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
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="project")
    ),
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
            party_filter=_build_project_party_filter(_scope_ctx),
        )
        items = [
            project_service.project_to_response(item)
            for item in result.get("items", [])
        ]
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
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="project")
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="project")
    ),
    status: str | None = Query("active", description="项目状态过滤，留空返回全部状态"),
) -> list[dict[str, Any]]:
    """获取项目下拉列表选项（标准端点）"""
    return await project_service.get_project_dropdown_options(
        db,
        status=status,
        current_user_id=str(current_user.id),
        party_filter=_build_project_party_filter(_scope_ctx),
    )


@router.get(
    "/stats/overview",
    response_model=ProjectStatisticsResponse,
    summary="获取项目统计",
)
async def get_project_statistics(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="project")
    ),
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
        party_filter=_build_project_party_filter(_scope_ctx),
    )


@router.get(
    "/{project_id}/assets",
    response_model=APIResponse[ProjectActiveAssetsResponse],
    summary="获取项目有效关联资产",
)
async def get_project_active_assets(
    project_id: Annotated[str, Path(description="项目ID")],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="project")
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="project",
            resource_id="{project_id}",
            deny_as_not_found=True,
        )
    ),
) -> Any:
    """获取项目有效关联资产列表及面积汇总。"""
    try:
        assets, summary = await project_service.get_project_active_assets(
            db=db,
            project_id=project_id,
            current_user_id=str(current_user.id),
            party_filter=_build_project_party_filter(_scope_ctx),
        )
        items = [AssetListItemResponse.model_validate(asset) for asset in assets]
        response_payload = ProjectActiveAssetsResponse(
            items=items,
            total=len(items),
            summary=summary,
        )
        return ResponseHandler.success(
            data=response_payload.model_dump(mode="json"),
            message="获取项目有效关联资产成功",
        )
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取项目有效关联资产失败: {str(e)}")


@router.get("/{project_id}", response_model=ProjectResponse, summary="获取项目详情")
async def get_project(
    project_id: Annotated[str, Path(description="项目ID")],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="project")
    ),
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
        party_filter=_build_project_party_filter(_scope_ctx),
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
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="project")
    ),
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
            party_filter=_build_project_party_filter(_scope_ctx),
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
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="project")
    ),
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
            party_filter=_build_project_party_filter(_scope_ctx),
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
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="project")
    ),
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
            party_filter=_build_project_party_filter(_scope_ctx),
        )
        return project_service.project_to_response(project)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"切换状态失败: {str(e)}")
