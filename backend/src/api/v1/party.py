"""Party domain API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    BaseBusinessError,
    bad_request,
    internal_error,
    not_found,
)
from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import (
    AuthzContext,
    DataScopeContext,
    get_current_active_user,
    require_authz,
    require_data_scope_context,
)
from ...models.auth import User
from ...schemas.organization import RepresentingOrganizationItem
from ...schemas.party import (
    CustomerProfileResponse,
    PartyBusinessRole,
    PartyContactCreate,
    PartyContactResponse,
    PartyCreate,
    PartyImportRequest,
    PartyImportResponse,
    PartyLifecycleCommitRequest,
    PartyLifecycleCommitResponse,
    PartyLifecyclePreviewRequest,
    PartyLifecyclePreviewResponse,
    PartyResponse,
    PartyReviewLogResponse,
    PartyReviewRejectRequest,
    PartyUpdate,
    UserPartyBindingResponse,
)
from ...schemas.user_party_scope import (
    UserPartyBindingScopeProposal,
    UserPartyScopeBatchCommitRequest,
    UserPartyScopeBatchCommitResponse,
    UserPartyScopeBatchPreviewRequest,
    UserPartyScopeBatchPreviewResponse,
    UserPartyScopeCommitRequest,
    UserPartyScopeCommitResponse,
    UserPartyScopePreviewResponse,
)
from ...security.permissions import require_any_role
from ...services.organization.service import organization_service
from ...services.party import party_lifecycle_change_service, party_service
from ...services.party.user_scope_batch_change_service import (
    user_party_scope_batch_change_service,
)
from ...services.party.user_scope_change_service import user_party_scope_change_service

router = APIRouter(tags=["主体管理"])
_SYSTEM_MANAGEMENT_ROLE_CODES = ["admin", "system_admin", "perm_admin"]
_PARTY_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:party:create"
_PARTY_CREATE_RESOURCE_CONTEXT: dict[str, str] = {
    "party_id": _PARTY_CREATE_UNSCOPED_PARTY_ID,
    "owner_party_id": _PARTY_CREATE_UNSCOPED_PARTY_ID,
    "manager_party_id": _PARTY_CREATE_UNSCOPED_PARTY_ID,
}


async def _require_user_party_scope_batch_authz(
    *,
    request: Request,
    db: AsyncSession,
    current_user: User,
    user_ids: tuple[str, ...],
) -> None:
    """Apply the normal per-user ABAC decision to every batch target."""
    for user_id in sorted(set(user_ids)):
        await require_authz(
            action="manage_party_scope",
            resource_type="user",
            resource_id=user_id,
        ).resolve(
            request=request,
            current_user=current_user,
            db=db,
        )


@router.get("/parties", response_model=list[PartyResponse], summary="获取主体列表")
async def list_parties(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回条数"),
    party_type: str | None = Query(None, description="主体类型过滤"),
    status: str | None = Query(None, description="状态过滤"),
    search: str | None = Query(None, description="名称/编码模糊搜索"),
    business_role: PartyBusinessRole | None = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="party",
            )
        ),
    ] = None,
) -> list[PartyResponse]:
    current_user_id = str(current_user.id).strip()
    parties = await party_service.get_parties(
        db,
        skip=skip,
        limit=limit,
        party_type=party_type,
        status=status,
        search=search,
        business_role=business_role,
        current_user_id=current_user_id if current_user_id != "" else None,
    )
    return [party_service.to_response(party) for party in parties]


@router.post("/parties", response_model=PartyResponse, summary="创建主体")
async def create_party(
    payload: PartyCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="create",
                resource_type="party",
                resource_context=_PARTY_CREATE_RESOURCE_CONTEXT,
            )
        ),
    ] = None,
) -> PartyResponse:
    _ = current_user
    try:
        party = await party_service.create_party(db, obj_in=payload)
        return party_service.to_response(party)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("创建主体失败", original_error=exc) from exc


@router.post(
    "/parties/import", response_model=PartyImportResponse, summary="批量导入主体"
)
async def import_parties(
    payload: PartyImportRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="create",
                resource_type="party",
                resource_context=_PARTY_CREATE_RESOURCE_CONTEXT,
            )
        ),
    ] = None,
) -> PartyImportResponse:
    operator = (
        str(getattr(current_user, "full_name", "")).strip()
        or str(getattr(current_user, "username", "")).strip()
        or str(current_user.id)
    )
    try:
        result = await party_service.import_parties(
            db,
            items=payload.items,
            operator=operator,
        )
        return PartyImportResponse.model_validate(result)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("批量导入主体失败", original_error=exc) from exc


@router.get("/parties/{party_id}", response_model=PartyResponse, summary="获取主体详情")
async def get_party(
    party_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="party",
                resource_id="{party_id}",
                deny_as_not_found=True,
            )
        ),
    ] = None,
) -> PartyResponse:
    _ = current_user
    party = await party_service.get_party(db, party_id=party_id)
    if party is None:
        raise not_found("主体不存在", resource_type="party", resource_id=party_id)
    return party_service.to_response(party)


@router.get(
    "/parties/{party_id}/organizations",
    response_model=list[RepresentingOrganizationItem],
    summary="获取代表主体的组织（只读反向列表）",
)
async def get_representing_organizations(
    party_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="party",
                resource_id="{party_id}",
                deny_as_not_found=True,
            )
        ),
    ] = None,
) -> list[RepresentingOrganizationItem]:
    _ = current_user
    party = await party_service.get_party(db, party_id=party_id)
    if party is None:
        raise not_found("主体不存在", resource_type="party", resource_id=party_id)
    return await organization_service.get_representing_organizations(
        db, party_id=party_id
    )


@router.get(
    "/customers/{party_id}",
    response_model=CustomerProfileResponse,
    summary="获取客户档案详情",
)
async def get_customer_profile(
    party_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="analytics")
    ),
) -> CustomerProfileResponse:
    _ = current_user
    try:
        profile = await party_service.get_customer_profile(
            db,
            party_id=party_id,
            binding_type=_scope_ctx.scope_mode,
            effective_party_ids=_scope_ctx.effective_party_ids,
        )
        return CustomerProfileResponse.model_validate(profile)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("获取客户档案失败", original_error=exc) from exc


@router.put("/parties/{party_id}", response_model=PartyResponse, summary="更新主体")
async def update_party(
    party_id: str,
    payload: PartyUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="party",
                resource_id="{party_id}",
            )
        ),
    ] = None,
) -> PartyResponse:
    _ = current_user
    try:
        party = await party_service.update_party(db, party_id=party_id, obj_in=payload)
        return party_service.to_response(party)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("更新主体失败", original_error=exc) from exc


@router.delete("/parties/{party_id}", summary="删除主体")
async def delete_party(
    party_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="delete",
                resource_type="party",
                resource_id="{party_id}",
            )
        ),
    ] = None,
) -> dict[str, str]:
    _ = current_user
    deleted = await party_service.delete_party(db, party_id=party_id)
    if not deleted:
        raise not_found("主体不存在", resource_type="party", resource_id=party_id)
    return {"message": "主体已删除"}


@router.post(
    "/parties/{party_id}/submit-review",
    response_model=PartyResponse,
    summary="提交主体审核",
)
async def submit_party_review(
    party_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="party",
                resource_id="{party_id}",
            )
        ),
    ] = None,
) -> PartyResponse:
    _ = current_user
    try:
        party = await party_service.submit_party_review(db, party_id=party_id)
        return party_service.to_response(party)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("提交主体审核失败", original_error=exc) from exc


@router.post(
    "/parties/{party_id}/approve-review",
    response_model=PartyResponse,
    summary="审核通过主体",
)
async def approve_party_review(
    party_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="party",
                resource_id="{party_id}",
            )
        ),
    ] = None,
) -> PartyResponse:
    reviewer = (
        str(getattr(current_user, "full_name", "")).strip()
        or str(getattr(current_user, "username", "")).strip()
        or str(current_user.id)
    )
    try:
        party = await party_service.approve_party_review(
            db,
            party_id=party_id,
            reviewer=reviewer,
        )
        return party_service.to_response(party)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("审核通过主体失败", original_error=exc) from exc


@router.post(
    "/parties/{party_id}/reject-review",
    response_model=PartyResponse,
    summary="驳回主体审核",
)
async def reject_party_review(
    party_id: str,
    payload: PartyReviewRejectRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="party",
                resource_id="{party_id}",
            )
        ),
    ] = None,
) -> PartyResponse:
    reviewer = (
        str(getattr(current_user, "full_name", "")).strip()
        or str(getattr(current_user, "username", "")).strip()
        or str(current_user.id)
    )
    try:
        party = await party_service.reject_party_review(
            db,
            party_id=party_id,
            reviewer=reviewer,
            reason=payload.reason,
        )
        return party_service.to_response(party)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("驳回主体审核失败", original_error=exc) from exc


@router.post(
    "/parties/{party_id}/status/preview",
    response_model=PartyLifecyclePreviewResponse,
    summary="Preview Party lifecycle change",
)
async def preview_party_lifecycle_change(
    party_id: str,
    payload: PartyLifecyclePreviewRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="party",
                resource_id="{party_id}",
            )
        ),
    ] = None,
) -> PartyLifecyclePreviewResponse:
    try:
        return await party_lifecycle_change_service.preview(
            db,
            party_id=party_id,
            request=payload,
            actor_id=str(current_user.id),
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("Preview Party lifecycle change failed", original_error=exc) from exc


async def _commit_party_lifecycle_change(
    *,
    party_id: str,
    operation: str,
    payload: PartyLifecycleCommitRequest,
    db: AsyncSession,
    current_user: User,
) -> PartyLifecycleCommitResponse:
    return await party_lifecycle_change_service.commit(
        db,
        party_id=party_id,
        operation=operation,
        request=payload,
        actor_id=str(current_user.id),
    )


@router.post(
    "/parties/{party_id}/deactivate",
    response_model=PartyLifecycleCommitResponse,
    summary="Deactivate an approved Party",
)
async def deactivate_party(
    party_id: str,
    payload: PartyLifecycleCommitRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="party",
                resource_id="{party_id}",
            )
        ),
    ] = None,
) -> PartyLifecycleCommitResponse:
    try:
        return await _commit_party_lifecycle_change(
            party_id=party_id,
            operation="deactivate",
            payload=payload,
            db=db,
            current_user=current_user,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("Deactivate Party failed", original_error=exc) from exc


@router.post(
    "/parties/{party_id}/reactivate",
    response_model=PartyLifecycleCommitResponse,
    summary="Reactivate an approved Party",
)
async def reactivate_party(
    party_id: str,
    payload: PartyLifecycleCommitRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="party",
                resource_id="{party_id}",
            )
        ),
    ] = None,
) -> PartyLifecycleCommitResponse:
    try:
        return await _commit_party_lifecycle_change(
            party_id=party_id,
            operation="reactivate",
            payload=payload,
            db=db,
            current_user=current_user,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("Reactivate Party failed", original_error=exc) from exc

@router.get(
    "/parties/{party_id}/review-logs",
    response_model=list[PartyReviewLogResponse],
    summary="获取主体审核/变更日志",
)
async def get_party_review_logs(
    party_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="party",
                resource_id="{party_id}",
                deny_as_not_found=True,
            )
        ),
    ] = None,
) -> list[PartyReviewLogResponse]:
    _ = current_user
    party = await party_service.get_party(db, party_id=party_id)
    if party is None:
        raise not_found("主体不存在", resource_type="party", resource_id=party_id)

    logs = await party_service.get_review_logs(db, party_id=party_id)
    return [PartyReviewLogResponse.model_validate(item) for item in logs]


@router.get(
    "/parties/{party_id}/contacts",
    response_model=list[PartyContactResponse],
    summary="获取主体联系人",
)
async def get_party_contacts(
    party_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="party",
                resource_id="{party_id}",
                deny_as_not_found=True,
            )
        ),
    ] = None,
) -> list[PartyContactResponse]:
    _ = current_user
    party = await party_service.get_party(db, party_id=party_id)
    if party is None:
        raise not_found("主体不存在", resource_type="party", resource_id=party_id)

    contacts = await party_service.get_contacts(db, party_id=party_id)
    return [PartyContactResponse.model_validate(item) for item in contacts]


@router.post(
    "/parties/{party_id}/contacts",
    response_model=PartyContactResponse,
    summary="新增主体联系人",
)
async def create_party_contact(
    party_id: str,
    payload: PartyContactCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="create",
                resource_type="party",
                resource_id="{party_id}",
            )
        ),
    ] = None,
) -> PartyContactResponse:
    _ = current_user
    try:
        contact_payload = payload.model_copy(update={"party_id": party_id})
        contact = await party_service.create_contact(db, obj_in=contact_payload)
        return PartyContactResponse.model_validate(contact)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("创建联系人失败", original_error=exc) from exc


@router.post(
    "/users/party-bindings/batch/preview",
    response_model=UserPartyScopeBatchPreviewResponse,
    summary="预览用户主体范围批量变更",
)
async def preview_user_party_scope_batch(
    payload: UserPartyScopeBatchPreviewRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> UserPartyScopeBatchPreviewResponse:
    """Preview explicit user Party-binding changes for multiple users."""
    try:
        await _require_user_party_scope_batch_authz(
            request=http_request,
            db=db,
            current_user=current_user,
            user_ids=tuple(item.user_id for item in payload.items),
        )
        return await user_party_scope_batch_change_service.preview(
            db,
            request=payload,
            actor_id=str(current_user.id),
        )
    except BaseBusinessError:
        raise
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post(
    "/users/party-bindings/batch/commit",
    response_model=UserPartyScopeBatchCommitResponse,
    summary="提交用户主体范围批量变更",
)
async def commit_user_party_scope_batch(
    payload: UserPartyScopeBatchCommitRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> UserPartyScopeBatchCommitResponse:
    """Atomically commit a current user Party-binding batch preview."""
    try:
        actor_id = str(current_user.id)
        await _require_user_party_scope_batch_authz(
            request=http_request,
            db=db,
            current_user=current_user,
            user_ids=await user_party_scope_batch_change_service.get_commit_user_ids(
                db,
                request=payload,
                actor_id=actor_id,
            ),
        )
        return await user_party_scope_batch_change_service.commit(
            db,
            request=payload,
            actor_id=actor_id,
        )
    except BaseBusinessError:
        raise
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get(
    "/users/{user_id}/party-bindings",
    response_model=list[UserPartyBindingResponse],
    summary="获取用户主体绑定列表",
)
async def get_user_party_bindings(
    user_id: str,
    active_only: bool = Query(True, description="仅返回当前有效绑定"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_any_role(_SYSTEM_MANAGEMENT_ROLE_CODES)),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="user",
                resource_id="{user_id}",
            )
        ),
    ] = None,
) -> list[UserPartyBindingResponse]:
    _ = current_user
    bindings = await party_service.get_user_party_bindings(
        db,
        user_id=user_id,
        active_only=active_only,
    )
    return [UserPartyBindingResponse.model_validate(item) for item in bindings]


@router.post(
    "/users/{user_id}/party-bindings/preview",
    response_model=UserPartyScopePreviewResponse,
    summary="预览用户主体范围变更",
)
async def preview_user_party_scope(
    user_id: str,
    proposal: UserPartyBindingScopeProposal,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="manage_party_scope",
                resource_type="user",
                resource_id="{user_id}",
            )
        ),
    ] = None,
) -> UserPartyScopePreviewResponse:
    """预览用户显式主体范围变更，不写入绑定。"""
    return await user_party_scope_change_service.preview(
        db,
        user_id=user_id,
        proposal=proposal,
        actor_id=str(current_user.id),
    )


@router.post(
    "/users/{user_id}/party-bindings/commit",
    response_model=UserPartyScopeCommitResponse,
    summary="提交用户主体范围变更",
)
async def commit_user_party_scope(
    user_id: str,
    request: UserPartyScopeCommitRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="manage_party_scope",
                resource_type="user",
                resource_id="{user_id}",
            )
        ),
    ] = None,
) -> UserPartyScopeCommitResponse:
    """提交已预览的用户显式主体范围变更。"""
    return await user_party_scope_change_service.commit(
        db,
        user_id=user_id,
        request=request,
        actor_id=str(current_user.id),
    )


route_registry.register_router(
    router, prefix="/api/v1", tags=["主体管理"], version="v1"
)


__all__ = ["router"]
