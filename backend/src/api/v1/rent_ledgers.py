"""Authorized commands for append-only external rent registrations."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import AuthzContext, get_current_active_user, require_authz
from ...models.auth import User
from ...schemas.rent_commands import (
    ManualRentEntryRequest,
    RentEntryCommandResponse,
    RentPaymentRequest,
    RentRecordCommandResponse,
    RentReversalRequest,
    VoidRentEntryRequest,
)
from ...services.asset_operations.errors import AssetOperationsPermissionDeniedError
from ...services.asset_operations.rent_payment_command_service import (
    rent_payment_command_service,
)
from ...services.party_scope_resolver import party_scope_resolver

router = APIRouter(tags=["资产运营"])
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=100, pattern=r".*\S.*"),
]
RentWriteAuthz = Annotated[
    AuthzContext | None,
    Depends(
        require_authz(
            action="write",
            resource_type="asset_ops",
            denial_error_factory=AssetOperationsPermissionDeniedError,
        )
    ),
]


@router.post(
    "/rent-ledger-entries/{entry_id}/records",
    response_model=RentRecordCommandResponse,
    summary="登记租金付款或到账",
)
async def register_rent_payment(
    entry_id: str,
    payload: RentPaymentRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: RentWriteAuthz = None,
) -> RentRecordCommandResponse:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await rent_payment_command_service.register(
        db,
        entry_id=entry_id,
        request=payload,
        actor_id=actor_id,
        scope=scope,
        idempotency_key=idempotency_key.strip(),
    )


@router.post(
    "/rent-payment-records/{record_id}/reversal",
    response_model=RentRecordCommandResponse,
    summary="撤销租金登记",
)
async def reverse_rent_payment(
    record_id: str,
    payload: RentReversalRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: RentWriteAuthz = None,
) -> RentRecordCommandResponse:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await rent_payment_command_service.reverse(
        db,
        record_id=record_id,
        request=payload,
        actor_id=actor_id,
        scope=scope,
        idempotency_key=idempotency_key.strip(),
    )


@router.post(
    "/rent-ledger-entries",
    response_model=RentEntryCommandResponse,
    summary="登记手工租金义务",
)
async def create_manual_rent_entry(
    payload: ManualRentEntryRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: RentWriteAuthz = None,
) -> RentEntryCommandResponse:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await rent_payment_command_service.create_manual(
        db,
        request=payload,
        actor_id=actor_id,
        scope=scope,
        idempotency_key=idempotency_key.strip(),
    )


@router.post(
    "/rent-ledger-entries/{entry_id}/void",
    response_model=RentEntryCommandResponse,
    summary="作废手工租金义务",
)
async def void_manual_rent_entry(
    entry_id: str,
    payload: VoidRentEntryRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: RentWriteAuthz = None,
) -> RentEntryCommandResponse:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await rent_payment_command_service.void_manual(
        db,
        entry_id=entry_id,
        request=payload,
        actor_id=actor_id,
        scope=scope,
        idempotency_key=idempotency_key.strip(),
    )


route_registry.register_router(
    router, prefix="/api/v1", tags=["资产运营"], version="v1"
)
