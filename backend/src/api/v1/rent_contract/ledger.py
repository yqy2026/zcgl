"""
租金台账模块 - 包含押金、服务费、月度台账CRUD
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ....core.api_errors import bad_request, internal_error, not_found, validation_error
from ....crud.rent_contract import rent_ledger
from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....schemas.rent_contract import (
    DepositLedgerResponse,
    GenerateLedgerRequest,
    RentLedgerBatchUpdate,
    RentLedgerListResponse,
    RentLedgerResponse,
    RentLedgerUpdate,
    ServiceFeeLedgerResponse,
)
from ....services.rent_contract import rent_contract_service

router = APIRouter()


# V2: 押金台账API
@router.get(
    "/contracts/{contract_id}/deposit-ledger",
    response_model=list[DepositLedgerResponse],
    summary="获取合同押金变动记录",
)
def get_contract_deposit_ledger(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[DepositLedgerResponse]:
    """
    获取指定合同的押金变动记录
    """
    from ....models.rent_contract import RentContract, RentDepositLedger

    contract = db.query(RentContract).filter(RentContract.id == contract_id).first()
    if not contract:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)

    ledgers = (
        db.query(RentDepositLedger)
        .filter(RentDepositLedger.contract_id == contract_id)
        .order_by(RentDepositLedger.created_at.desc())
        .all()
    )

    return [DepositLedgerResponse.model_validate(ledger) for ledger in ledgers]


# V2: 服务费台账API
@router.get(
    "/contracts/{contract_id}/service-fee-ledger",
    response_model=list[ServiceFeeLedgerResponse],
    summary="获取合同服务费台账",
)
def get_contract_service_fee_ledger(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[ServiceFeeLedgerResponse]:
    """
    获取指定合同的服务费台账记录
    """
    from ....models.rent_contract import RentContract, ServiceFeeLedger

    contract = db.query(RentContract).filter(RentContract.id == contract_id).first()
    if not contract:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)

    ledgers = (
        db.query(ServiceFeeLedger)
        .filter(ServiceFeeLedger.contract_id == contract_id)
        .order_by(ServiceFeeLedger.year_month.desc())
        .all()
    )

    return [ServiceFeeLedgerResponse.model_validate(ledger) for ledger in ledgers]


# 租金台账CRUD
@router.post("/ledger/generate", summary="生成月度台账")
def generate_monthly_ledger(
    request: GenerateLedgerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    根据合同信息生成月度租金台账
    """
    try:
        ledgers = rent_contract_service.generate_monthly_ledger(db=db, request=request)
        ledger_responses = [
            RentLedgerResponse.model_validate(ledger) for ledger in ledgers
        ]
        return {
            "message": f"成功生成 {len(ledger_responses)} 条台账记录",
            "ledgers": ledger_responses,
        }
    except ValueError as e:
        raise bad_request(str(e))
    except Exception as e:
        if "UnifiedError" in type(e).__name__:
            raise
        raise internal_error(f"生成台账失败: {str(e)}")


@router.get(
    "/ledger", response_model=RentLedgerListResponse, summary="获取租金台账列表"
)
def get_rent_ledger(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    contract_id: str | None = Query(None, description="合同ID筛选"),
    asset_id: str | None = Query(None, description="资产ID筛选"),
    ownership_id: str | None = Query(None, description="权属方ID筛选"),
    year_month: str | None = Query(None, description="年月筛选"),
    payment_status: str | None = Query(None, description="支付状态筛选"),
    start_date: date | None = Query(None, description="开始日期筛选"),
    end_date: date | None = Query(None, description="结束日期筛选"),
) -> RentLedgerListResponse:
    """
    获取租金台账列表，支持分页和筛选
    """
    skip = (page - 1) * limit
    ledgers, total = rent_ledger.get_multi_with_filters(
        db=db,
        skip=skip,
        limit=limit,
        contract_id=contract_id,
        asset_id=asset_id,
        ownership_id=ownership_id,
        year_month=year_month,
        payment_status=payment_status,
        start_date=start_date,
        end_date=end_date,
    )

    pages = (total + limit - 1) // limit
    ledger_responses = [RentLedgerResponse.model_validate(ledger) for ledger in ledgers]

    return RentLedgerListResponse(
        items=ledger_responses, total=total, page=page, limit=limit, pages=pages
    )


@router.get(
    "/ledger/{ledger_id}", response_model=RentLedgerResponse, summary="获取租金台账详情"
)
def get_rent_ledger_detail(
    ledger_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取租金台账详情
    """
    ledger = rent_ledger.get(db, id=ledger_id)
    if not ledger:
        raise not_found("台账记录不存在", resource_type="ledger", resource_id=ledger_id)
    return ledger


@router.put("/ledger/batch", summary="批量更新租金台账")
def batch_update_rent_ledger(
    request: RentLedgerBatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    批量更新租金台账支付状态
    """
    try:
        ledgers = rent_contract_service.batch_update_payment(db=db, request=request)
        ledger_responses = [
            RentLedgerResponse.model_validate(ledger) for ledger in ledgers
        ]
        return {
            "message": f"成功更新 {len(ledgers)} 条台账记录",
            "ledgers": ledger_responses,
        }
    except Exception as e:
        if "UnifiedError" in type(e).__name__:
            raise
        raise internal_error(f"批量更新失败: {str(e)}")


@router.put(
    "/ledger/{ledger_id}", response_model=RentLedgerResponse, summary="更新租金台账"
)
def update_rent_ledger(
    ledger_id: str,
    ledger_in: RentLedgerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    更新租金台账信息（支付状态等）
    """
    ledger = rent_ledger.get(db, id=ledger_id)
    if not ledger:
        raise not_found("台账记录不存在", resource_type="ledger", resource_id=ledger_id)

    if ledger_in.payment_status is not None:
        valid_statuses = ["未支付", "部分支付", "已支付", "逾期"]
        if ledger_in.payment_status not in valid_statuses:
            raise validation_error(f"支付状态必须是: {', '.join(valid_statuses)}")

    try:
        updated_ledger = rent_ledger.update(db=db, db_obj=ledger, obj_in=ledger_in)
        return updated_ledger
    except Exception as e:
        if "UnifiedError" in type(e).__name__:
            raise
        raise internal_error(f"更新台账失败: {str(e)}")


@router.get(
    "/contracts/{contract_id}/ledger",
    response_model=list[RentLedgerResponse],
    summary="获取合同台账",
)
def get_contract_ledger(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取指定合同的所有台账记录
    """
    ledgers, _ = rent_ledger.get_multi_with_filters(
        db=db,
        contract_id=contract_id,
        limit=1000,
    )
    return ledgers
