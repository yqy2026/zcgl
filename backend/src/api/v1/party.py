"""Party domain API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import BaseBusinessError, internal_error, not_found
from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import get_current_active_user
from ...models.auth import User
from ...schemas.party import (
    PartyContactCreate,
    PartyContactResponse,
    PartyCreate,
    PartyHierarchyCreate,
    PartyHierarchyResponse,
    PartyResponse,
    PartyUpdate,
)
from ...services.party import party_service

router = APIRouter(tags=["主体管理"])


@router.get("/parties", response_model=list[PartyResponse], summary="获取主体列表")
async def list_parties(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回条数"),
    party_type: str | None = Query(None, description="主体类型过滤"),
    status: str | None = Query(None, description="状态过滤"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> list[PartyResponse]:
    _ = current_user
    parties = await party_service.get_parties(
        db,
        skip=skip,
        limit=limit,
        party_type=party_type,
        status=status,
    )
    return [PartyResponse.model_validate(party) for party in parties]


@router.post("/parties", response_model=PartyResponse, summary="创建主体")
async def create_party(
    payload: PartyCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
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


route_registry.register_router(router, prefix="/api/v1", tags=["主体管理"], version="v1")


__all__ = ["router"]
