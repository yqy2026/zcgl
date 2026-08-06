"""
组织架构管理 API 路由
"""

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import (
    BaseBusinessError,
    bad_request,
    forbidden,
    not_found,
)
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....database import get_async_db
from ....middleware.auth import AuthzContext, get_current_active_user, require_authz
from ....models.auth import User
from ....schemas.organization import (
    OrganizationCreate,
    OrganizationHistoryResponse,
    OrganizationMoveCommitRequest,
    OrganizationMoveCommitResponse,
    OrganizationMovePreviewResponse,
    OrganizationMoveProposal,
    OrganizationPartyScopeBatchCommitRequest,
    OrganizationPartyScopeBatchCommitResponse,
    OrganizationPartyScopeBatchPreviewRequest,
    OrganizationPartyScopeBatchPreviewResponse,
    OrganizationPartyScopeCommitRequest,
    OrganizationPartyScopeCommitResponse,
    OrganizationPartyScopePreviewResponse,
    OrganizationPartyScopeProposal,
    OrganizationResponse,
    OrganizationSearchRequest,
    OrganizationStatistics,
    OrganizationTree,
    OrganizationUpdate,
)
from ....services.authz import authz_service
from ....services.organization import (
    organization_move_service,
    organization_party_scope_batch_service,
    organization_party_scope_service,
    organization_service,
)

router = APIRouter(tags=["组织架构管理"])
_ORGANIZATION_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:organization:create"


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "":
        return None
    return normalized


def _resolve_current_user_organization_id(current_user: User) -> str | None:
    return _normalize_optional_str(current_user.organization_id)


async def _resolve_organization_party_id(
    *,
    db: AsyncSession,
    organization_id: str | None,
) -> str | None:
    normalized_organization_id = _normalize_optional_str(organization_id)
    if normalized_organization_id is None:
        return None

    organization = await organization_service.get_organization(
        db,
        org_id=normalized_organization_id,
    )
    if organization is None:
        return None
    return _normalize_optional_str(organization.represented_party_id)


def _build_party_scope_context(
    *,
    scoped_party_id: str,
    organization_id: str | None = None,
) -> dict[str, str]:
    context: dict[str, str] = {
        "party_id": scoped_party_id,
        "owner_party_id": scoped_party_id,
        "manager_party_id": scoped_party_id,
    }
    if organization_id is not None:
        context["organization_id"] = organization_id
    return context


async def _require_organization_create_authz(
    organization: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    # 创建组织时优先沿 parent_id 建立作用域，缺失时回退到当前用户默认组织。
    scoped_organization_id = _normalize_optional_str(organization.parent_id)
    if scoped_organization_id is None:
        scoped_organization_id = _resolve_current_user_organization_id(current_user)

    scoped_party_id: str | None = None
    if scoped_organization_id is not None:
        scoped_party_id = await _resolve_organization_party_id(
            db=db,
            organization_id=scoped_organization_id,
        )

    if scoped_party_id is None:
        scoped_party_id = _ORGANIZATION_CREATE_UNSCOPED_PARTY_ID

    resource_context = _build_party_scope_context(
        scoped_party_id=scoped_party_id,
        organization_id=scoped_organization_id,
    )

    try:
        decision = await authz_service.check_access(
            db,
            user_id=str(current_user.id),
            resource_type="organization",
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
        resource_type="organization",
        resource_id=None,
        resource_context=resource_context,
        allowed=True,
        reason_code=decision.reason_code,
    )


async def _require_organization_party_scope_batch_authz(
    *,
    request: Request,
    db: AsyncSession,
    current_user: User,
    organization_ids: tuple[str, ...],
) -> None:
    """Apply the normal per-Organization ABAC decision to every batch target."""
    for organization_id in sorted(set(organization_ids)):
        await require_authz(
            action="manage_party_scope",
            resource_type="organization",
            resource_id=organization_id,
        ).resolve(
            request=request,
            current_user=current_user,
            db=db,
        )


@router.get(
    "",
    response_model=APIResponse[PaginatedData[OrganizationResponse]],
)
@router.get(
    "/",
    response_model=APIResponse[PaginatedData[OrganizationResponse]],
)
async def get_organizations(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="organization")
    ),
) -> JSONResponse:
    """
    获取组织列表

    **Party 隔离策略**：Organization 是系统内部管理层级（总部→分公司→部门），
    无 party_id 外键，与业务主体（Party）为独立概念。组织架构是全局共享只读元数据，
    所有认证用户均可读取（用于选择归属组织、审批路由等），不按 party 隔离。
    """
    skip = (page - 1) * page_size
    organizations, total = await organization_service.get_organizations(
        db,
        skip=skip,
        limit=page_size,
    )
    items = [OrganizationResponse.model_validate(org) for org in organizations]
    return ResponseHandler.paginated(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
        message="获取组织列表成功",
    )


@router.get("/tree", response_model=list[OrganizationTree])
async def get_organization_tree(
    parent_id: str | None = Query(None, description="父组织ID，为空时获取根组织"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="organization")
    ),
) -> list[OrganizationTree]:
    """获取组织层级结构"""

    async def build_tree(pid: str | None = None) -> list[OrganizationTree]:
        organizations = await organization_service.get_organization_tree(
            db,
            parent_id=pid,
        )
        tree: list[OrganizationTree] = []
        for org in organizations:
            org_id = getattr(org, "id", "")
            children = await build_tree(str(org_id))
            tree.append(
                OrganizationTree(
                    id=str(getattr(org, "id", "")),
                    name=str(getattr(org, "name", "")),
                    code=str(getattr(org, "code", "")),
                    level=int(getattr(org, "level", 0)),
                    sort_order=int(getattr(org, "sort_order", 0)),
                    type=str(getattr(org, "type", "")),
                    status=str(getattr(org, "status", "")),
                    children=children,
                )
            )
        return tree

    return await build_tree(parent_id)


@router.get(
    "/search",
    response_model=APIResponse[PaginatedData[OrganizationResponse]],
)
async def search_organizations(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="organization")
    ),
) -> JSONResponse:
    """搜索组织"""
    skip = (page - 1) * page_size
    organizations, total = await organization_service.search_organizations(
        db,
        keyword=keyword,
        skip=skip,
        limit=page_size,
    )
    items = [OrganizationResponse.model_validate(org) for org in organizations]

    return ResponseHandler.paginated(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
        message="搜索组织成功",
    )


@router.get("/statistics", response_model=OrganizationStatistics)
async def get_organization_statistics(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="organization")
    ),
) -> OrganizationStatistics:
    """获取组织统计信息"""
    stats = await organization_service.get_statistics(db)
    return OrganizationStatistics(**stats)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="organization",
            resource_id="{org_id}",
            deny_as_not_found=True,
        )
    ),
) -> OrganizationResponse:
    """根据ID获取组织详情"""
    organization = await organization_service.get_organization(db, org_id=org_id)
    if not organization:
        raise not_found("组织不存在", resource_type="organization", resource_id=org_id)
    return OrganizationResponse.model_validate(organization)


@router.get("/{org_id}/children", response_model=list[OrganizationResponse])
async def get_organization_children(
    org_id: str,
    is_recursive: bool = Query(False, description="是否递归获取子级组织"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="organization",
            resource_id="{org_id}",
            deny_as_not_found=True,
        )
    ),
) -> list[OrganizationResponse]:
    """获取组织下的子级组织"""
    parent = await organization_service.get_organization(db, org_id=org_id)
    if not parent:
        raise not_found("组织不存在", resource_type="organization", resource_id=org_id)
    children = await organization_service.get_organization_children(
        db,
        org_id=org_id,
        recursive=is_recursive,
    )
    return [OrganizationResponse.model_validate(org) for org in children]


@router.get("/{org_id}/path", response_model=list[OrganizationResponse])
async def get_organization_path(
    org_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="organization",
            resource_id="{org_id}",
            deny_as_not_found=True,
        )
    ),
) -> list[OrganizationResponse]:
    """获取组织到根的路径"""
    organization = await organization_service.get_organization(db, org_id=org_id)
    if not organization:
        raise not_found("组织不存在", resource_type="organization", resource_id=org_id)
    path = await organization_service.get_organization_path(db, org_id=org_id)
    return [OrganizationResponse.model_validate(org) for org in path]


@router.get(
    "/{org_id}/history",
    response_model=APIResponse[PaginatedData[OrganizationHistoryResponse]],
)
async def get_organization_history(
    org_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="organization",
            resource_id="{org_id}",
            deny_as_not_found=True,
        )
    ),
) -> JSONResponse:
    """获取组织变更历史"""
    skip = (page - 1) * page_size
    organization = await organization_service.get_organization(db, org_id=org_id)
    if not organization:
        raise not_found("组织不存在", resource_type="organization", resource_id=org_id)
    history, total = await organization_service.get_history_with_count(
        db, org_id=org_id, skip=skip, limit=page_size
    )

    items = [OrganizationHistoryResponse.model_validate(item) for item in history]

    return ResponseHandler.paginated(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
        message="获取组织历史成功",
    )


@router.post("", response_model=OrganizationResponse)
@router.post("/", response_model=OrganizationResponse)
async def create_organization(
    organization: OrganizationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_organization_create_authz),
) -> OrganizationResponse:
    """创建组织"""
    try:
        db_organization = await organization_service.create_organization(
            db, obj_in=organization
        )
        return OrganizationResponse.model_validate(db_organization)
    except BaseBusinessError:
        raise
    except ValueError as e:
        raise bad_request(str(e))


@router.post(
    "/party-scope/batch/preview",
    response_model=OrganizationPartyScopeBatchPreviewResponse,
)
async def preview_organization_party_scope_batch(
    payload: OrganizationPartyScopeBatchPreviewRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> OrganizationPartyScopeBatchPreviewResponse:
    """Preview direct represented-Party changes for independent Organizations."""
    try:
        await _require_organization_party_scope_batch_authz(
            request=http_request,
            db=db,
            current_user=current_user,
            organization_ids=tuple(item.organization_id for item in payload.items),
        )
        return await organization_party_scope_batch_service.preview(
            db,
            request=payload,
            actor_id=str(current_user.id),
        )
    except BaseBusinessError:
        raise
    except ValueError as e:
        raise bad_request(str(e))


@router.post(
    "/party-scope/batch/commit",
    response_model=OrganizationPartyScopeBatchCommitResponse,
)
async def commit_organization_party_scope_batch(
    payload: OrganizationPartyScopeBatchCommitRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> OrganizationPartyScopeBatchCommitResponse:
    """Atomically commit a current batch represented-Party scope preview."""
    try:
        actor_id = str(current_user.id)
        await _require_organization_party_scope_batch_authz(
            request=http_request,
            db=db,
            current_user=current_user,
            organization_ids=await organization_party_scope_batch_service.get_commit_organization_ids(
                db,
                request=payload,
                actor_id=actor_id,
            ),
        )
        return await organization_party_scope_batch_service.commit(
            db,
            request=payload,
            actor_id=actor_id,
        )
    except BaseBusinessError:
        raise
    except ValueError as e:
        raise bad_request(str(e))


@router.post(
    "/{org_id}/party-scope/preview",
    response_model=OrganizationPartyScopePreviewResponse,
)
async def preview_organization_party_scope(
    org_id: str,
    proposal: OrganizationPartyScopeProposal,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="manage_party_scope",
            resource_type="organization",
            resource_id="{org_id}",
        )
    ),
) -> OrganizationPartyScopePreviewResponse:
    """预览组织代表主体范围变更。"""
    try:
        return await organization_party_scope_service.preview(
            db,
            organization_id=org_id,
            proposal=proposal,
            actor_id=str(current_user.id),
        )
    except BaseBusinessError:
        raise
    except ValueError as e:
        raise bad_request(str(e))


@router.put(
    "/{org_id}/party-scope",
    response_model=OrganizationPartyScopeCommitResponse,
)
async def commit_organization_party_scope(
    org_id: str,
    request: OrganizationPartyScopeCommitRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="manage_party_scope",
            resource_type="organization",
            resource_id="{org_id}",
        )
    ),
) -> OrganizationPartyScopeCommitResponse:
    """提交已预览的组织代表主体范围变更。"""
    try:
        return await organization_party_scope_service.commit(
            db,
            organization_id=org_id,
            request=request,
            actor_id=str(current_user.id),
        )
    except BaseBusinessError:
        raise
    except ValueError as e:
        raise bad_request(str(e))


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    organization: OrganizationUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update", resource_type="organization", resource_id="{org_id}"
        )
    ),
) -> OrganizationResponse:
    """更新组织"""
    try:
        db_organization = await organization_service.update_organization(
            db, org_id=org_id, obj_in=organization
        )
        return OrganizationResponse.model_validate(db_organization)
    except BaseBusinessError:
        raise
    except ValueError as e:
        if str(e).startswith("组织ID"):
            raise not_found(str(e), resource_type="organization")
        raise bad_request(str(e))


@router.delete("/{org_id}")
async def delete_organization(
    org_id: str,
    deleted_by: str | None = Query(None, description="删除人"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="delete", resource_type="organization", resource_id="{org_id}"
        )
    ),
) -> dict[str, str]:
    """删除组织（软删除）"""
    try:
        success = await organization_service.delete_organization(
            db, org_id=org_id, deleted_by=deleted_by
        )
        if not success:
            raise not_found(
                "组织不存在", resource_type="organization", resource_id=org_id
            )
        return {"message": "组织删除成功"}
    except BaseBusinessError:
        raise
    except ValueError as e:
        raise bad_request(str(e))


@router.post(
    "/{org_id}/move/preview",
    response_model=OrganizationMovePreviewResponse,
)
async def preview_organization_move(
    org_id: str,
    proposal: OrganizationMoveProposal,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="manage_party_scope",
            resource_type="organization",
            resource_id="{org_id}",
        )
    ),
) -> OrganizationMovePreviewResponse:
    """Preview a sensitive Organization hierarchy move without writing it."""
    try:
        return await organization_move_service.preview(
            db,
            organization_id=org_id,
            proposal=proposal,
            actor_id=str(current_user.id),
        )
    except BaseBusinessError:
        raise
    except ValueError as e:
        raise bad_request(str(e))


@router.post("/{org_id}/move", response_model=OrganizationMoveCommitResponse)
async def commit_organization_move(
    org_id: str,
    request: OrganizationMoveCommitRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="manage_party_scope",
            resource_type="organization",
            resource_id="{org_id}",
        )
    ),
) -> OrganizationMoveCommitResponse:
    """Commit a current Organization move preview exactly once."""
    try:
        return await organization_move_service.commit(
            db,
            organization_id=org_id,
            request=request,
            actor_id=str(current_user.id),
        )
    except BaseBusinessError:
        raise
    except ValueError as e:
        raise bad_request(str(e))


@router.post(
    "/advanced-search",
    response_model=APIResponse[PaginatedData[OrganizationResponse]],
)
async def advanced_search_organizations(
    search_request: OrganizationSearchRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="organization")
    ),
) -> JSONResponse:
    """高级搜索组织"""
    organizations = await organization_service.advanced_search_organizations(
        db,
        keyword=search_request.keyword,
        skip=search_request.skip,
        limit=search_request.page_size,
    )

    if search_request.level:
        organizations = [
            org for org in organizations if org.level == search_request.level
        ]
    if search_request.parent_id:
        organizations = [
            org for org in organizations if org.parent_id == search_request.parent_id
        ]

    items = [OrganizationResponse.model_validate(org) for org in organizations]
    page_size = search_request.page_size
    page = (search_request.skip // page_size) + 1 if page_size > 0 else 1

    return ResponseHandler.paginated(
        data=items,
        page=page,
        page_size=page_size,
        total=len(items),
        message="高级搜索组织成功",
    )
