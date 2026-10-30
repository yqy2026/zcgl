"""Thin Party-scoped HTTP boundaries for monthly management fee statements."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import AuthzContext, get_current_active_user, require_authz
from ...models.auth import User
from ...schemas.management_fee_commands import (
    ManagementFeeCommandResponse,
    ManagementFeeConfirmationRequest,
    ManagementFeeDeferralRequest,
    ManagementFeeOwnerReceiptRequest,
    ManagementFeeStampResponse,
    ManagementFeeSuccessorRequest,
    ManagementFeeSuccessorResponse,
)
from ...schemas.management_fee_responses import (
    ManagementFeeListResponse,
    ManagementFeeStatementResponse,
)
from ...schemas.rent_commands import RentRecordCommandResponse
from ...services.asset_operations.errors import AssetOperationsPermissionDeniedError
from ...services.asset_operations.management_fee_command_service import (
    management_fee_command_service,
)
from ...services.asset_operations.management_fee_confirmation_service import (
    management_fee_confirmation_service,
)
from ...services.asset_operations.management_fee_owner_receipt_service import (
    management_fee_owner_receipt_service,
)
from ...services.asset_operations.management_fee_response_service import (
    management_fee_response_service,
)
from ...services.asset_operations.management_fee_upload_service import (
    management_fee_upload_service,
)
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


@router.get("/management-fee-statements", response_model=ManagementFeeListResponse)
async def list_statements(
    period: str = Query(),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: ReadAuthz = None,
) -> ManagementFeeListResponse:
    scope = await party_scope_resolver.resolve(db, user_id=str(current_user.id))
    return await management_fee_response_service.list(db, period=period, scope=scope)


@router.get(
    "/management-fee-statements/{statement_id}",
    response_model=ManagementFeeStatementResponse,
)
async def get_statement(
    statement_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: ReadAuthz = None,
) -> ManagementFeeStatementResponse:
    scope = await party_scope_resolver.resolve(db, user_id=str(current_user.id))
    return await management_fee_response_service.get(
        db, statement_id=statement_id, scope=scope
    )


@router.post(
    "/management-fee-statements/{statement_id}/owner-receipts",
    response_model=RentRecordCommandResponse,
)
async def register_owner_receipt(
    statement_id: str,
    payload: ManagementFeeOwnerReceiptRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: WriteAuthz = None,
) -> RentRecordCommandResponse:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await management_fee_owner_receipt_service.register(
        db,
        statement_id=statement_id,
        request=payload,
        actor_id=actor_id,
        scope=scope,
        idempotency_key=idempotency_key.strip(),
    )


@router.post(
    "/management-fee-statements/{statement_id}/deferrals",
    response_model=ManagementFeeCommandResponse,
)
async def defer_line(
    statement_id: str,
    payload: ManagementFeeDeferralRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: WriteAuthz = None,
) -> ManagementFeeCommandResponse:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await management_fee_command_service.defer_line(
        db,
        statement_id=statement_id,
        request=payload,
        actor_id=actor_id,
        scope=scope,
        idempotency_key=idempotency_key.strip(),
    )


@router.post(
    "/management-fee-statements/{statement_id}/stamped-document",
    response_model=ManagementFeeStampResponse,
)
async def upload_stamp(
    statement_id: str,
    file: UploadFile = File(),
    expected_version: int = Form(ge=1),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: WriteAuthz = None,
) -> ManagementFeeStampResponse:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await management_fee_upload_service.upload(
        db,
        statement_id=statement_id,
        file=file,
        expected_version=expected_version,
        actor_id=actor_id,
        scope=scope,
    )


@router.post(
    "/management-fee-statements/{statement_id}/confirmation",
    response_model=ManagementFeeCommandResponse,
)
async def confirm_statement(
    statement_id: str,
    payload: ManagementFeeConfirmationRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: WriteAuthz = None,
) -> ManagementFeeCommandResponse:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await management_fee_confirmation_service.confirm(
        db,
        statement_id=statement_id,
        request=payload,
        actor_id=actor_id,
        scope=scope,
        idempotency_key=idempotency_key.strip(),
    )


@router.post(
    "/management-fee-statements/{statement_id}/successor",
    response_model=ManagementFeeSuccessorResponse,
)
async def supersede_statement(
    statement_id: str,
    payload: ManagementFeeSuccessorRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: WriteAuthz = None,
) -> ManagementFeeSuccessorResponse:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await management_fee_confirmation_service.supersede(
        db,
        statement_id=statement_id,
        request=payload,
        actor_id=actor_id,
        scope=scope,
        idempotency_key=idempotency_key.strip(),
    )


route_registry.register_router(
    router, prefix="/api/v1", tags=["资产运营"], version="v1"
)
