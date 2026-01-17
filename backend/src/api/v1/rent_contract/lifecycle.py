"""
合同生命周期操作模块 - 续签和终止
"""

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends

from ....core.api_errors import bad_request, internal_error
from sqlalchemy.orm import Session

from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....schemas.rent_contract import RentContractCreate, RentContractResponse
from ....services.rent_contract import rent_contract_service

router = APIRouter()


@router.post(
    "/contracts/{contract_id}/renew",
    response_model=RentContractResponse,
    summary="V2: 合同续签",
)
def renew_contract(
    contract_id: str,
    *,
    db: Session = Depends(get_db),
    new_contract_data: RentContractCreate,
    transfer_deposit: bool = True,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    合同续签：创建新合同，结束原合同，转移押金
    """
    try:
        new_contract = rent_contract_service.renew_contract(
            db=db,
            original_contract_id=contract_id,
            new_contract_data=new_contract_data,
            transfer_deposit=transfer_deposit,
            operator=current_user.username if current_user else None,
            operator_id=current_user.id if current_user else None,
        )
        return new_contract
    except ValueError as e:
        raise bad_request(str(e))
    except Exception as e:
        if "UnifiedError" in type(e).__name__:
            raise
        raise internal_error(f"合同续签失败: {str(e)}")


@router.post(
    "/contracts/{contract_id}/terminate",
    response_model=RentContractResponse,
    summary="V2: 合同终止",
)
def terminate_contract(
    contract_id: str,
    *,
    db: Session = Depends(get_db),
    termination_date: date,
    refund_deposit: bool = True,
    deduction_amount: float = 0.0,
    termination_reason: str | None = None,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    合同终止：提前结束合同，处理押金退还/抵扣
    """
    try:
        contract = rent_contract_service.terminate_contract(
            db=db,
            contract_id=contract_id,
            termination_date=termination_date,
            refund_deposit=refund_deposit,
            deduction_amount=Decimal(str(deduction_amount)),
            termination_reason=termination_reason,
            operator=current_user.username if current_user else None,
            operator_id=current_user.id if current_user else None,
        )
        return contract
    except ValueError as e:
        raise bad_request(str(e))
    except Exception as e:
        if "UnifiedError" in type(e).__name__:
            raise
        raise internal_error(f"合同终止失败: {str(e)}")
