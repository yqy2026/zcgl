"""
权属方相关API端点
"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from ....core.exception_handler import bad_request, internal_error, not_found
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....crud.ownership import ownership
from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....models.asset import Ownership
from ....schemas.ownership import (
    OwnershipCreate,
    OwnershipDeleteResponse,
    OwnershipResponse,
    OwnershipSearchRequest,
    OwnershipStatisticsResponse,
    OwnershipUpdate,
)
from ....services.ownership import ownership_service

router = APIRouter()


@router.get("/dropdown-options", summary="获取权属方选项列表")
async def get_ownership_dropdown_options(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    is_active: bool | None = Query(True, description="是否启用"),
) -> list[OwnershipResponse]:
    """获取权属方选项列表（用于下拉选择等）- V2修复is_active过滤"""
    try:
        # 调用服务层获取下拉选项
        dropdown_data = ownership_service.get_ownership_dropdown_options(
            db, is_active=is_active
        )

        # 转换为响应格式
        responses = []
        for item_data in dropdown_data:
            # 创建临时Ownership对象以便model_validate使用
            temp_ownership = Ownership(
                **{
                    k: v
                    for k, v in item_data.items()
                    if k not in ["asset_count", "project_count"]
                }
            )
            response = OwnershipResponse.model_validate(temp_ownership)
            # 设置额外的计数字段
            response.asset_count = item_data["asset_count"]
            response.project_count = item_data["project_count"]
            responses.append(response)
        return responses
    except Exception as e:
        raise internal_error(f"获取权属方选项失败: {str(e)}")


@router.post("/", response_model=OwnershipResponse, summary="创建权属方")
async def create_ownership(
    *,
    db: Annotated[Session, Depends(get_db)],
    ownership_in: OwnershipCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> OwnershipResponse:
    """创建新权属方"""
    try:
        db_ownership = ownership_service.create_ownership(db, obj_in=ownership_in)
        return OwnershipResponse.model_validate(db_ownership)
    except ValueError as e:
        raise bad_request(str(e))
    except Exception as e:
        raise internal_error(f"创建权属方失败: {str(e)}")


@router.put("/{ownership_id}", response_model=OwnershipResponse, summary="更新权属方")
async def update_ownership(
    *,
    db: Annotated[Session, Depends(get_db)],
    ownership_id: str,
    ownership_in: OwnershipUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> OwnershipResponse:
    """更新权属方信息"""
    db_ownership = ownership.get(db, id=ownership_id)
    if not db_ownership:
        raise not_found(
            "权属方不存在", resource_type="ownership", resource_id=ownership_id
        )

    try:
        updated_ownership = ownership_service.update_ownership(
            db, db_obj=db_ownership, obj_in=ownership_in
        )
        return OwnershipResponse.model_validate(updated_ownership)
    except ValueError as e:
        raise bad_request(str(e))
    except Exception as e:
        raise internal_error(f"更新权属方失败: {str(e)}")


@router.put("/{ownership_id}/projects", summary="更新权属方关联项目")
async def update_ownership_projects(
    *,
    db: Annotated[Session, Depends(get_db)],
    ownership_id: str,
    project_ids: list[str] = Body(..., description="关联项目ID列表"),
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> OwnershipResponse:
    """更新权属方的关联项目"""
    db_ownership = ownership.get(db, id=ownership_id)
    if not db_ownership:
        raise not_found(
            "权属方不存在", resource_type="ownership", resource_id=ownership_id
        )

    try:
        # 更新关联项目
        ownership_service.update_related_projects(
            db, ownership_id=ownership_id, project_ids=project_ids
        )

        # 返回更新后的权属方信息
        updated_ownership = ownership.get(db, id=ownership_id)
        response = OwnershipResponse.model_validate(updated_ownership)

        # 获取实际的项目计数
        actual_project_count = ownership_service.get_project_count(db, ownership_id)
        response.project_count = actual_project_count
        return response
    except Exception as e:
        raise internal_error(f"更新关联项目失败: {str(e)}")


@router.delete(
    "/{ownership_id}", response_model=OwnershipDeleteResponse, summary="删除权属方"
)
async def delete_ownership(
    *,
    db: Annotated[Session, Depends(get_db)],
    ownership_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> OwnershipDeleteResponse:
    """删除权属方"""
    try:
        # 先检查关联资产数量
        asset_count = ownership_service.get_asset_count(db, ownership_id)

        deleted_ownership = ownership_service.delete_ownership(db, id=ownership_id)
        return OwnershipDeleteResponse(
            message="权属方删除成功",
            id=deleted_ownership.id,
            affected_assets=asset_count,
        )
    except ValueError as e:
        raise bad_request(str(e))
    except Exception as e:
        raise internal_error(f"删除权属方失败: {str(e)}")


@router.get(
    "",
    response_model=APIResponse[PaginatedData[OwnershipResponse]],
    summary="获取权属方列表",
)
@router.get(
    "/",
    response_model=APIResponse[PaginatedData[OwnershipResponse]],
    summary="获取权属方列表",
)
async def get_ownerships(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: str | None = Query(None, description="搜索关键词"),
    is_active: bool | None = Query(None, description="是否启用"),
) -> Any:
    """获取权属方列表"""
    search_params = OwnershipSearchRequest(
        page=page, page_size=page_size, keyword=keyword, is_active=is_active
    )

    result = ownership.search(db, search_params)

    # 转换为响应格式，并添加关联计数
    items = []
    for item in result["items"]:
        response = OwnershipResponse.model_validate(item)
        # 获取关联资产数量
        response.asset_count = ownership_service.get_asset_count(db, item.id)
        # 获取关联项目数量
        response.project_count = ownership_service.get_project_count(db, item.id)
        items.append(response)

    return ResponseHandler.paginated(
        data=items,
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        message="获取权属方列表成功",
    )


@router.post(
    "/search",
    response_model=APIResponse[PaginatedData[OwnershipResponse]],
    summary="搜索权属方",
)
async def search_ownerships(
    *,
    db: Annotated[Session, Depends(get_db)],
    search_params: OwnershipSearchRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Any:
    """搜索权属方"""
    result = ownership.search(db, search_params)

    # 转换为响应格式，并添加关联计数
    items = []
    for item in result["items"]:
        response = OwnershipResponse.model_validate(item)
        # 获取关联资产数量
        response.asset_count = ownership_service.get_asset_count(db, item.id)
        # 获取关联项目数量
        response.project_count = ownership_service.get_project_count(db, item.id)
        items.append(response)

    return ResponseHandler.paginated(
        data=items,
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        message="搜索权属方成功",
    )


@router.get(
    "/statistics/summary",
    response_model=OwnershipStatisticsResponse,
    summary="获取权属方统计",
)
async def get_ownership_statistics(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> OwnershipStatisticsResponse:
    """获取权属方统计信息"""
    stats = ownership_service.get_statistics(db)

    # 转换最近创建的权属方
    recent_created = [
        OwnershipResponse.model_validate(item) for item in stats["recent_created"]
    ]

    return OwnershipStatisticsResponse(
        total_count=stats["total_count"],
        active_count=stats["active_count"],
        inactive_count=stats["inactive_count"],
        recent_created=recent_created,
    )


@router.post(
    "/{ownership_id}/toggle-status",
    response_model=OwnershipResponse,
    summary="切换权属方状态",
)
async def toggle_ownership_status(
    *,
    db: Annotated[Session, Depends(get_db)],
    ownership_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> OwnershipResponse:
    """切换权属方启用/禁用状态"""
    try:
        db_ownership = ownership_service.toggle_status(db, id=ownership_id)
        return OwnershipResponse.model_validate(db_ownership)
    except ValueError as e:
        raise bad_request(str(e))
    except Exception as e:
        raise internal_error(f"切换状态失败: {str(e)}")


@router.get(
    "/{ownership_id}/financial-summary",
    summary="获取权属方收支汇总",
)
async def get_ownership_financial_summary(
    ownership_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict[str, Any]:
    """
    获取权属方的收支汇总信息

    包括:
    - 总收入 (来自租金台账)
    - 总支出 (如果有的话)
    - 应收未收金额
    - 已收金额
    """

    from sqlalchemy import and_, func

    from ....models.rent_contract import RentContract, RentLedger

    # 验证权属方是否存在
    ownership_obj = ownership.get(db, id=ownership_id)
    if not ownership_obj:
        raise not_found(
            "权属方不存在", resource_type="ownership", resource_id=ownership_id
        )

    # 查询该权属方下所有合同的台账
    subquery = (
        db.query(RentContract.id)
        .filter(RentContract.ownership_id == ownership_id)
        .scalar_subquery()
    )

    # 统计应收总额
    due_amount_result = (
        db.query(func.coalesce(func.sum(RentLedger.due_amount), 0))
        .filter(RentLedger.contract_id == subquery)
        .scalar()
    )

    # 统计实收总额
    paid_amount_result = (
        db.query(func.coalesce(func.sum(RentLedger.paid_amount), 0))
        .filter(RentLedger.contract_id == subquery)
        .scalar()
    )

    # 统计欠款总额
    arrears_amount_result = (
        db.query(func.coalesce(func.sum(RentLedger.overdue_amount), 0))
        .filter(RentLedger.contract_id == subquery)
        .scalar()
    )

    # 统计合同数量
    contract_count = (
        db.query(func.count(RentContract.id))
        .filter(RentContract.ownership_id == ownership_id)
        .scalar()
    )

    # 统计活跃合同数
    active_contract_count = (
        db.query(func.count(RentContract.id))
        .filter(
            and_(
                RentContract.ownership_id == ownership_id,
                RentContract.contract_status == "有效",
            )
        )
        .scalar()
    )

    return {
        "ownership_id": ownership_id,
        "ownership_name": ownership_obj.name,
        "financial_summary": {
            "total_due_amount": float(due_amount_result or 0),
            "total_paid_amount": float(paid_amount_result or 0),
            "total_arrears_amount": float(arrears_amount_result or 0),
            "payment_rate": float(
                (paid_amount_result / due_amount_result * 100)
                if due_amount_result > 0
                else 0
            ),
        },
        "contract_summary": {
            "total_contracts": contract_count or 0,
            "active_contracts": active_contract_count or 0,
        },
    }
