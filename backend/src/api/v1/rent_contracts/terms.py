"""
租金条款模块
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import not_found
from ....crud.rent_contract import rent_contract, rent_term
from ....database import get_async_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....schemas.rent_contract import RentTermCreate, RentTermResponse

router = APIRouter()


@router.get(
    "/contracts/{contract_id}/terms",
    response_model=list[RentTermResponse],
    summary="获取合同租金条款",
)
async def get_contract_terms(
    contract_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取指定合同的所有租金条款
    """
    terms = await rent_term.get_by_contract_async(db, contract_id=contract_id)
    return terms


@router.post(
    "/contracts/{contract_id}/terms",
    response_model=RentTermResponse,
    summary="添加租金条款",
)
async def add_rent_term(
    contract_id: str,
    *,
    db: AsyncSession = Depends(get_async_db),
    term_in: RentTermCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    为合同添加新的租金条款
    """

    contract = await rent_contract.get_with_details_async(db, id=contract_id)
    if not contract:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)
    term_data = term_in.model_dump()
    term_data["contract_id"] = contract_id
    term = await rent_term.create(db=db, obj_in=term_data)
    if not term:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)
    return term
