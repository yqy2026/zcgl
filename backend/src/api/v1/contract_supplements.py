from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import AuthzContext, get_current_active_user, require_authz
from ...models.auth import User
from ...schemas.contract_supplement import (
    SupplementCreate,
    SupplementItem,
    SupplementList,
    SupplementWithdrawal,
)
from ...services.asset_operations import AssetOperationsPermissionDeniedError
from ...services.asset_operations.contract_supplement_service import (
    contract_supplement_service,
)
from ...services.party_scope_resolver import party_scope_resolver

router = APIRouter()
ReadAccess = Annotated[
    AuthzContext | None,
    Depends(
        require_authz(
            action="read",
            resource_type="asset_ops",
            denial_error_factory=AssetOperationsPermissionDeniedError,
        )
    ),
]
ArchiveAccess = Annotated[
    AuthzContext | None,
    Depends(
        require_authz(
            action="archive",
            resource_type="asset_ops",
            denial_error_factory=AssetOperationsPermissionDeniedError,
        )
    ),
]
WithdrawalAccess = Annotated[
    AuthzContext | None,
    Depends(
        require_authz(
            action="archive",
            resource_type="asset_ops",
            resource_id="{supplement_id}",
            denial_error_factory=AssetOperationsPermissionDeniedError,
        )
    ),
]


@router.get("/contract-supplements", response_model=SupplementList)
async def list_supplements(
    contract_kind: Literal["upstream", "terminal"],
    contract_id: str,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_active_user),
    _authz: ReadAccess = None,
) -> SupplementList:
    scope = await party_scope_resolver.resolve(db, user_id=str(user.id))
    return await contract_supplement_service.list(
        db, kind=contract_kind, contract_id=contract_id, scope=scope
    )


@router.post("/contract-supplements", response_model=SupplementItem, status_code=201)
async def register_supplement(
    request: SupplementCreate,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_active_user),
    _authz: ArchiveAccess = None,
) -> SupplementItem:
    scope = await party_scope_resolver.resolve(db, user_id=str(user.id))
    return await contract_supplement_service.create(
        db, request=request, scope=scope, actor_id=str(user.id)
    )


@router.post(
    "/contract-supplements/{supplement_id}/withdrawal", response_model=SupplementItem
)
async def withdraw_supplement(
    supplement_id: str,
    request: SupplementWithdrawal,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_active_user),
    _authz: WithdrawalAccess = None,
) -> SupplementItem:
    scope = await party_scope_resolver.resolve(db, user_id=str(user.id))
    return await contract_supplement_service.withdraw(
        db, identity=supplement_id, request=request, scope=scope, actor_id=str(user.id)
    )


route_registry.register_router(
    router, prefix="/api/v1", tags=["合同补充协议"], version="v1"
)
