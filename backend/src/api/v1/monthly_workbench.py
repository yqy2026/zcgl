"""Monthly workbench (本月) read endpoint for the asset-operations module."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    BaseBusinessError,
    internal_error,
)
from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import AuthzContext, get_current_active_user, require_authz
from ...models.auth import User
from ...schemas.monthly_workbench import MonthlyWorkbenchView
from ...services.asset_operations import (
    AssetOperationsPermissionDeniedError,
    monthly_workbench_service,
)
from ...services.party_scope_resolver import party_scope_resolver

router = APIRouter(tags=["资产运营"])


@router.get(
    "/monthly-workbench",
    response_model=MonthlyWorkbenchView,
    summary="查询本月工作台总览",
)
async def get_monthly_workbench(
    operator_party_id: Annotated[
        str, Query(min_length=1, description="运营主体（报送口径主体）")
    ],
    month: str | None = Query(None, pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$"),
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
) -> MonthlyWorkbenchView:
    """Derive the four deadline cards plus the anytime list on the fly."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await monthly_workbench_service.overview(
            db,
            scope=scope,
            operator_party_id=operator_party_id,
            actor_id=actor_id,
            month=month,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询本月工作台失败", original_error=exc) from exc


route_registry.register_router(
    router,
    prefix="/api/v1",
    tags=["资产运营"],
    version="v1",
)


__all__ = ["router"]
