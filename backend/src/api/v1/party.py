"""Party domain API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import BaseBusinessError, internal_error, not_found
from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import (
    AuthzContext,
    get_current_active_user,
    require_admin,
    require_authz,
)
from ...models.auth import User
from ...schemas.party import (
    PartyContactCreate,
    PartyContactResponse,
    PartyCreate,
    PartyHierarchyCreate,
    PartyHierarchyResponse,
    PartyResponse,
    PartyUpdate,
    UserPartyBindingCreate,
    UserPartyBindingResponse,
    UserPartyBindingUpdate,
    UserPartyBindingUpsert,
)
from ...services.party import party_service

router = APIRouter(tags=["主体管理"])
_PARTY_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:party:create"
_PARTY_CREATE_RESOURCE_CONTEXT: dict[str, str] = {
    "party_id": _PARTY_CREATE_UNSCOPED_PARTY_ID,
    "owner_party_id": _PARTY_CREATE_UNSCOPED_PARTY_ID,
    "manager_party_id": _PARTY_CREATE_UNSCOPED_PARTY_ID,
}


@router.get("/parties", response_model=list[PartyResponse], summary="获取主体列表")
async def list_parties(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回条数"),
    party_type: str | None = Query(None, description="主体类型过滤"),
    status: str | None = Query(None, description="状态过滤"),
    search: str | None = Query(None, description="名称/编码模糊搜索"),
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
        current_user_id=current_user_id if current_user_id != "" else None,
    )
    return [PartyResponse.model_validate(party) for party in parties]


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
        return PartyResponse.model_validate(party)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("创建主体失败", original_error=exc) from exc


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
    return PartyResponse.model_validate(party)


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
        return PartyResponse.model_validate(party)
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


@router.get(
    "/parties/{party_id}/hierarchy",
    response_model=list[str],
    summary="获取主体下级列表",
)
async def get_party_hierarchy(
    party_id: str,
    include_self: bool = Query(False, description="是否包含自身"),
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
) -> list[str]:
    _ = current_user
    party = await party_service.get_party(db, party_id=party_id)
    if party is None:
        raise not_found("主体不存在", resource_type="party", resource_id=party_id)

    return await party_service.get_descendants(
        db,
        party_id=party_id,
        include_self=include_self,
    )


@router.post(
    "/parties/{party_id}/hierarchy",
    response_model=PartyHierarchyResponse,
    summary="新增主体层级",
)
async def add_party_hierarchy(
    party_id: str,
    payload: PartyHierarchyCreate,
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
) -> PartyHierarchyResponse:
    _ = current_user
    try:
        relation = await party_service.add_hierarchy(
            db,
            parent_party_id=party_id,
            child_party_id=payload.child_party_id,
        )
        return PartyHierarchyResponse.model_validate(relation)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("新增层级失败", original_error=exc) from exc


@router.delete("/parties/{party_id}/hierarchy", summary="删除主体层级")
async def delete_party_hierarchy(
    party_id: str,
    child_party_id: str = Query(..., description="子主体ID"),
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
    deleted = await party_service.remove_hierarchy(
        db,
        parent_party_id=party_id,
        child_party_id=child_party_id,
    )
    if not deleted:
        raise not_found("层级关系不存在", resource_type="party_hierarchy")
    return {"message": "层级关系已删除"}


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


@router.get(
    "/users/{user_id}/party-bindings",
    response_model=list[UserPartyBindingResponse],
    summary="获取用户主体绑定列表",
)
async def get_user_party_bindings(
    user_id: str,
    active_only: bool = Query(True, description="仅返回当前有效绑定"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
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
    "/users/{user_id}/party-bindings",
    response_model=UserPartyBindingResponse,
    status_code=201,
    summary="新增用户主体绑定",
)
async def create_user_party_binding(
    user_id: str,
    payload: UserPartyBindingUpsert,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="user",
                resource_id="{user_id}",
            )
        ),
    ] = None,
) -> UserPartyBindingResponse:
    _ = current_user
    try:
        binding_payload = UserPartyBindingCreate(
            user_id=user_id,
            **payload.model_dump(exclude_none=True),
        )
        binding = await party_service.create_user_party_binding(
            db,
            obj_in=binding_payload,
        )
        return UserPartyBindingResponse.model_validate(binding)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("创建用户主体绑定失败", original_error=exc) from exc


@router.put(
    "/users/{user_id}/party-bindings/{binding_id}",
    response_model=UserPartyBindingResponse,
    summary="更新用户主体绑定",
)
async def update_user_party_binding(
    user_id: str,
    binding_id: str,
    payload: UserPartyBindingUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="user",
                resource_id="{user_id}",
            )
        ),
    ] = None,
) -> UserPartyBindingResponse:
    _ = current_user
    try:
        binding = await party_service.update_user_party_binding(
            db,
            user_id=user_id,
            binding_id=binding_id,
            obj_in=payload,
        )
        return UserPartyBindingResponse.model_validate(binding)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("更新用户主体绑定失败", original_error=exc) from exc


@router.delete(
    "/users/{user_id}/party-bindings/{binding_id}",
    summary="关闭用户主体绑定",
)
async def close_user_party_binding(
    user_id: str,
    binding_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="delete",
                resource_type="user",
                resource_id="{user_id}",
            )
        ),
    ] = None,
) -> dict[str, str]:
    _ = current_user
    closed = await party_service.close_user_party_binding(
        db,
        user_id=user_id,
        binding_id=binding_id,
    )
    if not closed:
        raise not_found(
            "用户主体绑定不存在或已失效",
            resource_type="user_party_binding",
            resource_id=binding_id,
        )
    return {"message": "用户主体绑定已关闭"}


route_registry.register_router(router, prefix="/api/v1", tags=["主体管理"], version="v1")


__all__ = ["router"]
