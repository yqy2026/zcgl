"""
租金台账模块 - 包含押金、服务费、月度台账CRUD
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....constants.rent_contract_constants import PaymentStatus
from ....core.exception_handler import (
    BaseBusinessError,
    forbidden,
    internal_error,
    not_found,
    validation_error,
)
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....database import get_async_db
from ....middleware.auth import AuthzContext, get_current_active_user, require_authz
from ....models.auth import User
from ....schemas.rent_contract import (
    DepositLedgerResponse,
    GenerateLedgerRequest,
    RentLedgerBatchUpdate,
    RentLedgerResponse,
    RentLedgerUpdate,
    ServiceFeeLedgerResponse,
)
from ....services.authz import authz_service
from ....services.rent_contract import rent_contract_service

router = APIRouter()
_RENT_LEDGER_BATCH_UPDATE_UNSCOPED_PARTY_ID = (
    "__unscoped__:rent_contract_ledger:batch_update"
)
_RENT_LEDGER_GENERATE_UNSCOPED_PARTY_ID = "__unscoped__:rent_contract_ledger:generate"
_RENT_LEDGER_READ_UNSCOPED_PARTY_ID = "__unscoped__:rent_contract_ledger:read"
_RENT_LEDGER_UPDATE_UNSCOPED_PARTY_ID = "__unscoped__:rent_contract_ledger:update"
_RENT_LEDGER_BATCH_UPDATE_RESOURCE_CONTEXT: dict[str, str] = {
    "party_id": _RENT_LEDGER_BATCH_UPDATE_UNSCOPED_PARTY_ID,
    "owner_party_id": _RENT_LEDGER_BATCH_UPDATE_UNSCOPED_PARTY_ID,
    "manager_party_id": _RENT_LEDGER_BATCH_UPDATE_UNSCOPED_PARTY_ID,
}


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "":
        return None
    return normalized


def _normalize_identifier_sequence(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized_values: list[str] = []
    for value in values:
        normalized = _normalize_optional_str(value)
        if normalized is None:
            continue
        normalized_values.append(normalized)
    return normalized_values


def _resolve_authz_scope_party_ids(
    *,
    authz_ctx: Any,
    field: str,
    list_field: str,
) -> list[str]:
    if not isinstance(authz_ctx, AuthzContext):
        return []
    scope_ids = _normalize_identifier_sequence(
        authz_ctx.resource_context.get(list_field),
    )
    if scope_ids:
        return scope_ids
    scoped_party_id = _normalize_optional_str(authz_ctx.resource_context.get(field))
    if scoped_party_id is None:
        return []
    return [scoped_party_id]


async def _resolve_owner_party_scope_by_ownership_id(
    *,
    db: AsyncSession,
    ownership_id: str | None,
) -> str | None:
    normalized_ownership_id = _normalize_optional_str(ownership_id)
    if normalized_ownership_id is None:
        return None
    resolved_party_id = (
        await rent_contract_service.resolve_owner_party_scope_by_ownership_id_async(
            db=db,
            ownership_id=normalized_ownership_id,
        )
    )
    return _normalize_optional_str(resolved_party_id)


async def _build_ledger_contract_resource_context(
    *,
    db: AsyncSession,
    contract: Any,
    contract_id: str,
    ledger_id: str | None = None,
    fallback_party_id: str | None = None,
) -> dict[str, Any]:
    resource_context: dict[str, Any] = {"contract_id": contract_id}
    if ledger_id is not None:
        resource_context["ledger_id"] = ledger_id

    owner_party_id = _normalize_optional_str(getattr(contract, "owner_party_id", None))
    manager_party_id = _normalize_optional_str(getattr(contract, "manager_party_id", None))
    ownership_id = _normalize_optional_str(getattr(contract, "ownership_id", None))

    if owner_party_id is not None:
        resource_context["owner_party_id"] = owner_party_id
    if manager_party_id is not None:
        resource_context["manager_party_id"] = manager_party_id
    if ownership_id is not None:
        resource_context["ownership_id"] = ownership_id

    primary_party_id = owner_party_id or manager_party_id
    if owner_party_id is None and ownership_id is not None:
        resolved_owner_party_id = await _resolve_owner_party_scope_by_ownership_id(
            db=db,
            ownership_id=ownership_id,
        )
        if resolved_owner_party_id is not None:
            owner_party_id = resolved_owner_party_id
            resource_context["owner_party_id"] = resolved_owner_party_id

    party_id = primary_party_id or owner_party_id or fallback_party_id
    if party_id is not None:
        resource_context["party_id"] = party_id

    return resource_context


async def _require_ledger_generate_authz(
    request: GenerateLedgerRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    resolved_contract_id = _normalize_optional_str(request.contract_id)
    if resolved_contract_id is None:
        raise not_found(
            "合同不存在",
            resource_type="contract",
            resource_id=request.contract_id,
        )

    contract = await rent_contract_service.get_contract_with_details_async(
        db=db,
        contract_id=resolved_contract_id,
    )
    if contract is None:
        raise not_found(
            "合同不存在",
            resource_type="contract",
            resource_id=resolved_contract_id,
        )

    resource_context = await _build_ledger_contract_resource_context(
        db=db,
        contract=contract,
        contract_id=resolved_contract_id,
        fallback_party_id=_RENT_LEDGER_GENERATE_UNSCOPED_PARTY_ID,
    )

    try:
        decision = await authz_service.check_access(
            db,
            user_id=str(current_user.id),
            resource_type="rent_contract",
            action="create",
            resource_id=resolved_contract_id,
            resource=resource_context,
        )
    except Exception:
        raise forbidden("权限校验失败")

    if not decision.allowed:
        raise forbidden("权限不足")

    return AuthzContext(
        current_user=current_user,
        action="create",
        resource_type="rent_contract",
        resource_id=resolved_contract_id,
        resource_context=resource_context,
        allowed=True,
        reason_code=decision.reason_code,
    )


async def _require_ledger_contract_authz(
    *,
    action: str,
    ledger_id: str,
    current_user: User,
    db: AsyncSession,
) -> AuthzContext:
    resolved_ledger_id = _normalize_optional_str(ledger_id)
    if resolved_ledger_id is None:
        raise not_found("台账记录不存在", resource_type="ledger", resource_id=ledger_id)

    ledger = await rent_contract_service.get_rent_ledger_by_id_async(
        db=db,
        ledger_id=resolved_ledger_id,
    )
    if ledger is None:
        raise not_found(
            "台账记录不存在",
            resource_type="ledger",
            resource_id=resolved_ledger_id,
        )

    resolved_contract_id = _normalize_optional_str(getattr(ledger, "contract_id", None))
    if resolved_contract_id is None:
        raise not_found(
            "合同不存在",
            resource_type="contract",
            resource_id=getattr(ledger, "contract_id", None),
        )

    contract = await rent_contract_service.get_contract_with_details_async(
        db=db,
        contract_id=resolved_contract_id,
    )
    if contract is None:
        raise not_found(
            "合同不存在",
            resource_type="contract",
            resource_id=resolved_contract_id,
        )

    fallback_party_id = (
        _RENT_LEDGER_READ_UNSCOPED_PARTY_ID
        if action == "read"
        else _RENT_LEDGER_UPDATE_UNSCOPED_PARTY_ID
    )
    resource_context = await _build_ledger_contract_resource_context(
        db=db,
        contract=contract,
        contract_id=resolved_contract_id,
        ledger_id=resolved_ledger_id,
        fallback_party_id=fallback_party_id,
    )

    try:
        decision = await authz_service.check_access(
            db,
            user_id=str(current_user.id),
            resource_type="rent_contract",
            action=action,
            resource_id=resolved_contract_id,
            resource=resource_context,
        )
    except Exception:
        raise forbidden("权限校验失败")

    if not decision.allowed:
        raise forbidden("权限不足")

    return AuthzContext(
        current_user=current_user,
        action=action,
        resource_type="rent_contract",
        resource_id=resolved_contract_id,
        resource_context=resource_context,
        allowed=True,
        reason_code=decision.reason_code,
    )


async def _require_ledger_read_authz(
    ledger_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    return await _require_ledger_contract_authz(
        action="read",
        ledger_id=ledger_id,
        current_user=current_user,
        db=db,
    )


async def _require_ledger_update_authz(
    ledger_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    return await _require_ledger_contract_authz(
        action="update",
        ledger_id=ledger_id,
        current_user=current_user,
        db=db,
    )


# V2: 押金台账API
@router.get(
    "/contracts/{contract_id}/deposit-ledger",
    response_model=list[DepositLedgerResponse],
    summary="获取合同押金变动记录",
)
async def get_contract_deposit_ledger(
    contract_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="rent_contract",
            resource_id="{contract_id}",
            deny_as_not_found=True,
        )
    ),
) -> list[DepositLedgerResponse]:
    """
    获取指定合同的押金变动记录
    """

    contract = await rent_contract_service.get_contract_by_id_async(
        db, contract_id=contract_id
    )
    if not contract:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)
    ledgers = await rent_contract_service.get_deposit_ledger_async(
        db, contract_id=contract_id
    )
    return [DepositLedgerResponse.model_validate(ledger) for ledger in ledgers]


# V2: 服务费台账API
@router.get(
    "/contracts/{contract_id}/service-fee-ledger",
    response_model=list[ServiceFeeLedgerResponse],
    summary="获取合同服务费台账",
)
async def get_contract_service_fee_ledger(
    contract_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="rent_contract",
            resource_id="{contract_id}",
            deny_as_not_found=True,
        )
    ),
) -> list[ServiceFeeLedgerResponse]:
    """
    获取指定合同的服务费台账记录
    """

    contract = await rent_contract_service.get_contract_by_id_async(
        db, contract_id=contract_id
    )
    if not contract:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)
    ledgers = await rent_contract_service.get_service_fee_ledger_async(
        db, contract_id=contract_id
    )
    return [ServiceFeeLedgerResponse.model_validate(ledger) for ledger in ledgers]


# 租金台账CRUD
@router.post("/ledger/generate", summary="生成月度台账")
async def generate_monthly_ledger(
    request: GenerateLedgerRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_ledger_generate_authz),
) -> Any:
    """
    根据合同信息生成月度租金台账
    """
    try:
        ledgers = await rent_contract_service.generate_monthly_ledger_async(
            db=db, request=request
        )
        ledger_responses = [
            RentLedgerResponse.model_validate(ledger) for ledger in ledgers
        ]
        return {
            "message": f"成功生成 {len(ledger_responses)} 条台账记录",
            "ledgers": ledger_responses,
        }
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"生成台账失败: {str(e)}")


@router.get(
    "/ledger",
    response_model=APIResponse[PaginatedData[RentLedgerResponse]],
    summary="获取租金台账列表",
)
async def get_rent_ledger(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="rent_contract",
        )
    ),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    contract_id: str | None = Query(None, description="合同ID筛选"),
    asset_id: str | None = Query(None, description="资产ID筛选"),
    owner_party_id: str | None = Query(None, description="产权方主体ID筛选"),
    ownership_id: str | None = Query(None, description="权属方ID筛选（DEPRECATED）"),
    year_month: str | None = Query(None, description="年月筛选"),
    payment_status: str | None = Query(None, description="支付状态筛选"),
    start_date: date | None = Query(None, description="开始日期筛选"),
    end_date: date | None = Query(None, description="结束日期筛选"),
) -> JSONResponse:
    """
    获取租金台账列表，支持分页和筛选
    """
    owner_party_id_value = owner_party_id if isinstance(owner_party_id, str) else None
    scoped_owner_party_ids = _resolve_authz_scope_party_ids(
        authz_ctx=authz_ctx,
        field="owner_party_id",
        list_field="owner_party_ids",
    )
    scoped_manager_party_ids = _resolve_authz_scope_party_ids(
        authz_ctx=authz_ctx,
        field="manager_party_id",
        list_field="manager_party_ids",
    )

    if owner_party_id_value is not None:
        if scoped_owner_party_ids and owner_party_id_value not in scoped_owner_party_ids:
            raise forbidden("权限不足")
        if not scoped_owner_party_ids and scoped_manager_party_ids:
            # Manager-only scoped callers cannot inject owner filter because the
            # current query layer combines owner/manager scope with OR.
            raise forbidden("权限不足")

    effective_owner_party_ids: list[str] | None = None
    if owner_party_id_value is not None:
        effective_owner_party_ids = [owner_party_id_value]
    elif scoped_owner_party_ids:
        effective_owner_party_ids = scoped_owner_party_ids

    effective_manager_party_ids = (
        scoped_manager_party_ids if scoped_manager_party_ids else None
    )

    effective_owner_party_id = (
        effective_owner_party_ids[0] if effective_owner_party_ids else None
    )
    effective_manager_party_id = (
        effective_manager_party_ids[0] if effective_manager_party_ids else None
    )
    ownership_id_value = ownership_id if isinstance(ownership_id, str) else None  # DEPRECATED alias

    skip = (page - 1) * page_size
    ledgers, total = await rent_contract_service.get_rent_ledger_page_async(
        db=db,
        skip=skip,
        limit=page_size,
        contract_id=contract_id,
        asset_id=asset_id,
        owner_party_id=effective_owner_party_id,
        manager_party_id=effective_manager_party_id,
        owner_party_ids=effective_owner_party_ids,
        manager_party_ids=effective_manager_party_ids,
        ownership_id=ownership_id_value,  # DEPRECATED alias
        year_month=year_month,
        payment_status=payment_status,
        start_date=start_date,
        end_date=end_date,
    )

    ledger_responses = [RentLedgerResponse.model_validate(ledger) for ledger in ledgers]

    return ResponseHandler.paginated(
        data=ledger_responses,
        page=page,
        page_size=page_size,
        total=total,
        message="获取租金台账列表成功",
    )


@router.get(
    "/ledger/{ledger_id}", response_model=RentLedgerResponse, summary="获取租金台账详情"
)
async def get_rent_ledger_detail(
    ledger_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_ledger_read_authz),
) -> Any:
    """
    获取租金台账详情
    """
    ledger = await rent_contract_service.get_rent_ledger_by_id_async(
        db=db,
        ledger_id=ledger_id,
    )
    if not ledger:
        raise not_found("台账记录不存在", resource_type="ledger", resource_id=ledger_id)
    return ledger


@router.put("/ledger/batch", summary="批量更新租金台账")
async def batch_update_rent_ledger(
    request: RentLedgerBatchUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="rent_contract",
            resource_context=_RENT_LEDGER_BATCH_UPDATE_RESOURCE_CONTEXT,
        )
    ),
) -> Any:
    """
    批量更新租金台账支付状态
    """
    try:
        ledgers = await rent_contract_service.batch_update_payment_async(
            db=db, request=request
        )
        ledger_responses = [
            RentLedgerResponse.model_validate(ledger) for ledger in ledgers
        ]
        return {
            "message": f"成功更新 {len(ledgers)} 条台账记录",
            "ledgers": ledger_responses,
        }
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"批量更新失败: {str(e)}")


@router.put(
    "/ledger/{ledger_id}", response_model=RentLedgerResponse, summary="更新租金台账"
)
async def update_rent_ledger(
    ledger_id: str,
    ledger_in: RentLedgerUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_ledger_update_authz),
) -> Any:
    """
    更新租金台账信息（支付状态等）
    """
    if ledger_in.payment_status is not None:
        valid_statuses = [s.value for s in PaymentStatus]
        if ledger_in.payment_status not in valid_statuses:
            raise validation_error(f"支付状态必须是: {', '.join(valid_statuses)}")

    try:
        updated_ledger = await rent_contract_service.update_ledger_async(
            db=db, ledger_id=ledger_id, update_data=ledger_in
        )
        return updated_ledger
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"更新台账失败: {str(e)}")


@router.get(
    "/contracts/{contract_id}/ledger",
    response_model=list[RentLedgerResponse],
    summary="获取合同台账",
)
async def get_contract_ledger(
    contract_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="rent_contract",
            resource_id="{contract_id}",
            deny_as_not_found=True,
        )
    ),
) -> Any:
    """
    获取指定合同的所有台账记录
    """
    ledgers = await rent_contract_service.get_contract_ledger_async(
        db=db,
        contract_id=contract_id,
        limit=1000,
    )
    return ledgers
