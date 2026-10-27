"""Read-only business changes with asset-operations authorization."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import AuthzContext, get_current_active_user, require_authz
from ...models.auth import User
from ...schemas.business_change_event import BusinessChangeEventListResponse
from ...services.asset_operations.business_change_service import business_change_service
from ...services.asset_operations.errors import AssetOperationsPermissionDeniedError
from ...services.party_scope_resolver import party_scope_resolver

router = APIRouter(tags=["资产运营"])


@router.get(
    "/business-change-events",
    response_model=BusinessChangeEventListResponse,
    summary="查询变更记录",
)
async def list_business_change_events(
    target_type: Literal["upstream_contract", "terminal_contract"] | None = None,
    target_id: str | None = Query(None, max_length=36),
    period: str | None = Query(None, description="上海业务月 YYYY-MM"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="asset_ops",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> BusinessChangeEventListResponse:
    scope = await party_scope_resolver.resolve(db, user_id=str(current_user.id))
    items, total = await business_change_service.list_events(
        db,
        scope=scope,
        target_type=target_type,
        target_id=target_id,
        period=period,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return BusinessChangeEventListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


route_registry.register_router(
    router, prefix="/api/v1", tags=["资产运营"], version="v1"
)
