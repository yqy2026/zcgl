"""Party-scoped deposit balances and append-only registrations."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import AuthzContext, get_current_active_user, require_authz
from ...models.auth import User
from ...schemas.deposit_commands import (
    DepositEntryResponse,
    DepositListResponse,
    DepositRecordCommandResponse,
    DepositRecordRequest,
    DepositReversalRequest,
)
from ...services.asset_operations.deposit_command_service import deposit_command_service
from ...services.asset_operations.deposit_query_service import deposit_query_service
from ...services.asset_operations.errors import AssetOperationsPermissionDeniedError
from ...services.party_scope_resolver import party_scope_resolver

router = APIRouter(tags=["资产运营"])
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=100, pattern=r".*\S.*"),
]
ReadAuthz = Annotated[
    AuthzContext | None,
    Depends(
        require_authz(
            action="read",
            resource_type="asset_ops",
            denial_error_factory=AssetOperationsPermissionDeniedError,
        )
    ),
]
WriteAuthz = Annotated[
    AuthzContext | None,
    Depends(
        require_authz(
            action="write",
            resource_type="asset_ops",
            denial_error_factory=AssetOperationsPermissionDeniedError,
        )
    ),
]


@router.get("/deposits", response_model=DepositListResponse)
async def list_deposits(
    status: Literal[
        "receivable_uncollected",
        "payable_unpaid",
        "refundable_unreturned",
        "recoverable_unreceived",
        "settled",
    ]
    | None = None,
    contract_kind: Literal["upstream", "terminal"] | None = None,
    contract_id: str | None = None,
    party_id: str | None = None,
    project_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: ReadAuthz = None,
) -> DepositListResponse:
    scope = await party_scope_resolver.resolve(db, user_id=str(current_user.id))
    return await deposit_query_service.list(
        db,
        scope=scope,
        status=status,
        contract_kind=contract_kind,
        contract_id=contract_id,
        party_id=party_id,
        project_id=project_id,
        page=page,
        page_size=page_size,
    )


@router.get("/deposits/{deposit_id}", response_model=DepositEntryResponse)
async def get_deposit(
    deposit_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: ReadAuthz = None,
) -> DepositEntryResponse:
    scope = await party_scope_resolver.resolve(db, user_id=str(current_user.id))
    return await deposit_query_service.get(db, entry_id=deposit_id, scope=scope)


@router.post(
    "/deposits/{deposit_id}/records", response_model=DepositRecordCommandResponse
)
async def register_deposit(
    deposit_id: str,
    payload: DepositRecordRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: WriteAuthz = None,
) -> DepositRecordCommandResponse:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await deposit_command_service.register(
        db,
        entry_id=deposit_id,
        request=payload,
        actor_id=actor_id,
        scope=scope,
        idempotency_key=idempotency_key.strip(),
    )


@router.post(
    "/deposit-records/{record_id}/reversal", response_model=DepositRecordCommandResponse
)
async def reverse_deposit(
    record_id: str,
    payload: DepositReversalRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: WriteAuthz = None,
) -> DepositRecordCommandResponse:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await deposit_command_service.reverse(
        db,
        record_id=record_id,
        request=payload,
        actor_id=actor_id,
        scope=scope,
        idempotency_key=idempotency_key.strip(),
    )


route_registry.register_router(
    router, prefix="/api/v1", tags=["资产运营"], version="v1"
)
