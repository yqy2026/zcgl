"""
租金条款模块
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ....core.exception_handler import not_found
from ....crud.rent_contract import rent_contract, rent_term
from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....schemas.rent_contract import RentTermCreate, RentTermResponse

router = APIRouter()


@router.get(
    "/contracts/{contract_id}/terms",
    response_model=list[RentTermResponse],
    summary="获取合同租金条款",
)
def get_contract_terms(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取指定合同的所有租金条款
    """
    terms = rent_term.get_by_contract(db, contract_id=contract_id)
    return terms


@router.post(
    "/contracts/{contract_id}/terms",
    response_model=RentTermResponse,
    summary="添加租金条款",
)
def add_rent_term(
    contract_id: str,
    *,
    db: Session = Depends(get_db),
    term_in: RentTermCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    为合同添加新的租金条款
    """
    contract = rent_contract.get(db, id=contract_id)
    if not contract:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)

    term_data = term_in.model_dump()
    term_data["contract_id"] = contract_id
    term = rent_term.create(db=db, obj_in=term_data)
    return term
