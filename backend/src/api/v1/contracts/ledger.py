"""合同台账聚合查询与重算 API。"""

from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import BaseBusinessError, internal_error
from ....database import get_async_db
from ....middleware.auth import (
    AuthzContext,
    get_current_active_user,
    require_authz,
)
from ....models.auth import User
from ....schemas.contract_group import (
    ContractLedgerListResponse,
    LedgerAggregateQueryParams,
    LedgerRecalculateResponse,
)
from ....services.contract.ledger_service_v2 import ledger_service_v2

router = APIRouter()

LedgerPaymentStatus = Literal["unpaid", "paid", "overdue", "partial", "voided"]


def resolve_ledger_query_params(
    asset_id: str | None = Query(None, description="资产 ID"),
    party_id: str | None = Query(None, description="主体 ID"),
    contract_id: str | None = Query(None, description="合同 ID"),
    year_month_start: str | None = Query(None, description="开始账期，格式 YYYY-MM"),
    year_month_end: str | None = Query(None, description="结束账期，格式 YYYY-MM"),
    payment_status: str | None = Query(None, description="支付状态"),
    include_voided: bool = Query(False, description="是否包含作废条目"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    limit: int = Query(20, ge=1, le=200, description="每页条数"),
) -> LedgerAggregateQueryParams:
    try:
        normalized_payment_status: LedgerPaymentStatus | None = None
        if payment_status is not None:
            allowed_payment_statuses: set[LedgerPaymentStatus] = {
                "unpaid",
                "paid",
                "overdue",
                "partial",
                "voided",
            }
            if payment_status not in allowed_payment_statuses:
                raise ValidationError.from_exception_data(
                    "LedgerAggregateQueryParams",
                    [
                        {
                            "type": "literal_error",
                            "loc": ("payment_status",),
                            "input": payment_status,
                            "ctx": {
                                "expected": ", ".join(sorted(allowed_payment_statuses)),
                            },
                        }
                    ],
                )
            normalized_payment_status = cast(LedgerPaymentStatus, payment_status)

        return LedgerAggregateQueryParams(
            asset_id=asset_id,
            party_id=party_id,
            contract_id=contract_id,
            year_month_start=year_month_start,
            year_month_end=year_month_end,
            payment_status=normalized_payment_status,
            include_voided=include_voided,
            offset=offset,
            limit=limit,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


@router.get(
    "/ledger/entries",
    response_model=ContractLedgerListResponse,
    summary="跨合同查询台账条目",
)
async def get_ledger_entries(
    params: LedgerAggregateQueryParams = Depends(resolve_ledger_query_params),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="contract",
            )
        ),
    ] = None,
) -> ContractLedgerListResponse:
    _ = current_user
    _ = _authz
    try:
        result = await ledger_service_v2.query_ledger_entries(
            db,
            asset_id=params.asset_id,
            party_id=params.party_id,
            contract_id=params.contract_id,
            year_month_start=params.year_month_start,
            year_month_end=params.year_month_end,
            payment_status=params.payment_status,
            include_voided=params.include_voided,
            offset=params.offset,
            limit=params.limit,
        )
        return ContractLedgerListResponse.model_validate(result)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询台账条目失败", original_error=exc) from exc


@router.post(
    "/contracts/{contract_id}/ledger/recalculate",
    response_model=LedgerRecalculateResponse,
    summary="重算合同台账",
)
async def recalculate_contract_ledger(
    contract_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="contract",
                resource_id="{contract_id}",
            )
        ),
    ] = None,
) -> LedgerRecalculateResponse:
    _ = current_user
    _ = _authz
    try:
        result = await ledger_service_v2.recalculate_ledger(db, contract_id=contract_id)
        return LedgerRecalculateResponse.model_validate(result)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("重算合同台账失败", original_error=exc) from exc
