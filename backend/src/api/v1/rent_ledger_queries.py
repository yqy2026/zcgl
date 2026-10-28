"""Read-only rent ledger routes for the asset-operations workbench."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import AuthzContext, get_current_active_user, require_authz
from ...models.auth import User
from ...schemas.rent_queries import RentEntryView, RentMatrixView
from ...services.asset_operations.errors import AssetOperationsPermissionDeniedError
from ...services.asset_operations.rent_ledger_query_service import (
    rent_ledger_query_service,
)
from ...services.party_scope_resolver import party_scope_resolver

router = APIRouter(tags=["资产运营"])
_read_guard = require_authz(
    action="read",
    resource_type="asset_ops",
    denial_error_factory=AssetOperationsPermissionDeniedError,
)


@router.get("/rent-ledgers", response_model=RentMatrixView)
async def get_rent_ledger(
    ledger_type: Literal["upstream_rent", "terminal_rent"] = Query("terminal_rent"),
    year: int = Query(..., ge=1000, le=9998),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[AuthzContext | None, Depends(_read_guard)] = None,
) -> RentMatrixView:
    scope = await party_scope_resolver.resolve(db, user_id=str(current_user.id))
    return await rent_ledger_query_service.matrix(
        db, scope=scope, ledger_type=ledger_type, year=year
    )


@router.get("/rent-ledger-entries/{entry_id}", response_model=RentEntryView)
async def get_rent_ledger_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[AuthzContext | None, Depends(_read_guard)] = None,
) -> RentEntryView:
    scope = await party_scope_resolver.resolve(db, user_id=str(current_user.id))
    return await rent_ledger_query_service.detail(db, scope=scope, entry_id=entry_id)


route_registry.register_router(
    router, prefix="/api/v1", tags=["资产运营"], version="v1"
)
