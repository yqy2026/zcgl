"""
租金合同CRUD操作模块
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ....core.exception_handler import (
    BaseBusinessError,
    forbidden,
    internal_error,
    not_found,
)
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....crud.asset import asset_crud
from ....crud.ownership import ownership
from ....crud.rent_contract import rent_contract
from ....database import get_db
from ....middleware.auth import can_edit_contract, get_current_active_user
from ....models.auth import User, UserRole
from ....schemas.rent_contract import (
    RentContractCreate,
    RentContractResponse,
    RentContractUpdate,
)
from ....services.rent_contract import rent_contract_service

router = APIRouter()


@router.post("/contracts", response_model=RentContractResponse, summary="创建租金合同")
def create_contract(
    *,
    db: Session = Depends(get_db),
    contract_in: RentContractCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    创建新的租金合同，包含租金条款信息 - V2 支持多资产
    """
    # V2: 验证关联的资产（多资产）
    if contract_in.asset_ids:
        for asset_id in contract_in.asset_ids:
            asset = asset_crud.get(db, id=asset_id)
            if not asset:
                raise not_found(
                    f"关联的资产不存在: {asset_id}",
                    resource_type="asset",
                    resource_id=asset_id,
                )

    ownership_obj = ownership.get(db, id=contract_in.ownership_id)
    if not ownership_obj:
        raise not_found(
            "关联的权属方不存在",
            resource_type="ownership",
            resource_id=str(contract_in.ownership_id),
        )

    try:
        contract = rent_contract_service.create_contract(db=db, obj_in=contract_in)
        return contract
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"创建合同失败: {str(e)}")


@router.get(
    "/contracts/{contract_id}",
    response_model=RentContractResponse,
    summary="获取租金合同详情",
)
def get_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取租金合同详情，包含租金条款信息
    """
    contract = rent_contract.get_with_details(db, id=contract_id)
    if not contract:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)
    return contract


@router.get(
    "/contracts",
    response_model=APIResponse[PaginatedData[RentContractResponse]],
    summary="获取租金合同列表",
)
def get_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    contract_number: str | None = Query(None, description="合同编号筛选"),
    tenant_name: str | None = Query(None, description="承租方名称筛选"),
    asset_id: str | None = Query(None, description="资产ID筛选"),
    ownership_id: str | None = Query(None, description="权属方ID筛选"),
    contract_status: str | None = Query(None, description="合同状态筛选"),
    start_date: date | None = Query(None, description="开始日期筛选"),
    end_date: date | None = Query(None, description="结束日期筛选"),
) -> JSONResponse:
    """
    获取租金合同列表，支持分页和筛选
    """
    skip = (page - 1) * page_size
    contracts, total = rent_contract.get_multi_with_filters(
        db=db,
        skip=skip,
        limit=page_size,
        contract_number=contract_number,
        tenant_name=tenant_name,
        asset_id=asset_id,
        ownership_id=ownership_id,
        contract_status=contract_status,
        start_date=start_date,
        end_date=end_date,
    )

    contract_responses = [RentContractResponse.model_validate(c) for c in contracts]

    return ResponseHandler.paginated(
        data=contract_responses,
        page=page,
        page_size=page_size,
        total=total,
        message="获取租金合同列表成功",
    )


@router.put(
    "/contracts/{contract_id}",
    response_model=RentContractResponse,
    summary="更新租金合同",
)
def update_contract(
    contract_id: str,
    *,
    db: Session = Depends(get_db),
    contract_in: RentContractUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    更新租金合同信息

    权限要求:
    - 管理员可以编辑任何合同
    - 其他用户需要通过RBAC权限检查
    """
    if not can_edit_contract(current_user, db, contract_id):
        raise forbidden("权限不足: 您没有权限编辑此合同")

    contract = rent_contract.get_with_details(db, id=contract_id)
    if not contract:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)

    try:
        updated_contract = rent_contract_service.update_contract(
            db=db, db_obj=contract, obj_in=contract_in
        )
        return updated_contract
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"更新合同失败: {str(e)}")


@router.delete("/contracts/{contract_id}", summary="删除租金合同")
def delete_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    删除租金合同（同时删除相关的租金条款和台账记录）

    权限要求: 仅管理员可以删除合同
    """
    if current_user.role != UserRole.ADMIN:
        raise forbidden("权限不足: 只有管理员可以删除合同")

    contract = rent_contract.get(db, id=contract_id)
    if not contract:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)

    try:
        rent_contract.remove(db, id=contract_id)
        return {"message": "合同删除成功"}
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"删除合同失败: {str(e)}")


@router.get(
    "/assets/{asset_id}/contracts",
    response_model=list[RentContractResponse],
    summary="获取资产合同",
)
def get_asset_contracts(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取指定资产的所有合同
    """
    contracts, _ = rent_contract.get_multi_with_filters(
        db=db,
        asset_id=asset_id,
        limit=1000,
    )
    return contracts
