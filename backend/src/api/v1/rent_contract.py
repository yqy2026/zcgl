from typing import Any

"""
租金台账相关API接口
"""

import os
import tempfile
from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...crud.asset import asset_crud
from ...crud.ownership import ownership
from ...crud.rent_contract import rent_contract, rent_ledger, rent_term
from ...database import get_db
from ...middleware.auth import can_edit_contract, get_current_active_user
from ...models.auth import User, UserRole
from ...schemas.rent_contract import (
    AssetRentStatistics,
    DepositLedgerResponse,
    GenerateLedgerRequest,
    MonthlyRentStatistics,
    OwnershipRentStatistics,
    RentContractCreate,
    RentContractListResponse,
    RentContractResponse,
    RentContractUpdate,
    RentLedgerBatchUpdate,
    RentLedgerListResponse,
    RentLedgerResponse,
    RentLedgerUpdate,
    RentStatisticsQuery,
    RentTermCreate,
    RentTermResponse,
    ServiceFeeLedgerResponse,
)
from ...services.rent_contract import rent_contract_service

try:
    from ...services.document.rent_contract_excel import rent_contract_excel_service

    EXCEL_SERVICE_AVAILABLE = True
except (ImportError, SyntaxError):
    rent_contract_excel_service = None
    EXCEL_SERVICE_AVAILABLE = False

router = APIRouter()


# 租金合同API
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
    # HTTPException should propagate through
    from fastapi import HTTPException

    # V2: 验证关联的资产（多资产）
    if contract_in.asset_ids:
        for asset_id in contract_in.asset_ids:
            asset = asset_crud.get(db, id=asset_id)
            if not asset:
                raise HTTPException(
                    status_code=404, detail=f"关联的资产不存在: {asset_id}"
                )

    ownership_obj = ownership.get(db, id=contract_in.ownership_id)
    if not ownership_obj:
        raise HTTPException(status_code=404, detail="关联的权属方不存在")

    try:
        contract = rent_contract_service.create_contract(db=db, obj_in=contract_in)
        return contract
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Don't catch HTTPException - let it propagate
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"创建合同失败: {str(e)}")


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
        raise HTTPException(status_code=404, detail="合同不存在")
    return contract


@router.get(
    "/contracts", response_model=RentContractListResponse, summary="获取租金合同列表"
)
def get_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    contract_number: str | None = Query(None, description="合同编号筛选"),
    tenant_name: str | None = Query(None, description="承租方名称筛选"),
    asset_id: str | None = Query(None, description="资产ID筛选"),
    ownership_id: str | None = Query(None, description="权属方ID筛选"),
    contract_status: str | None = Query(None, description="合同状态筛选"),
    start_date: date | None = Query(None, description="开始日期筛选"),
    end_date: date | None = Query(None, description="结束日期筛选"),
) -> RentContractListResponse:
    """
    获取租金合同列表，支持分页和筛选
    """
    skip = (page - 1) * limit
    contracts, total = rent_contract.get_multi_with_filters(
        db=db,
        skip=skip,
        limit=limit,
        contract_number=contract_number,
        tenant_name=tenant_name,
        asset_id=asset_id,
        ownership_id=ownership_id,
        contract_status=contract_status,
        start_date=start_date,
        end_date=end_date,
    )

    pages = (total + limit - 1) // limit

    # Convert ORM models to response schemas
    contract_responses = [RentContractResponse.model_validate(c) for c in contracts]

    return RentContractListResponse(
        items=contract_responses, total=total, page=page, limit=limit, pages=pages
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
    # 权限检查
    if not can_edit_contract(current_user, db, contract_id):
        raise HTTPException(status_code=403, detail="权限不足: 您没有权限编辑此合同")

    contract = rent_contract.get_with_details(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    try:
        updated_contract = rent_contract_service.update_contract(
            db=db, db_obj=contract, obj_in=contract_in
        )
        return updated_contract
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Don't catch HTTPException - let it propagate
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"更新合同失败: {str(e)}")


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
    # 权限检查 - 删除是敏感操作,仅管理员可以执行
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="权限不足: 只有管理员可以删除合同")

    contract = rent_contract.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    try:
        rent_contract.remove(db, id=contract_id)
        return {"message": "合同删除成功"}
    except Exception as e:
        # Don't catch HTTPException - let it propagate
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"删除合同失败: {str(e)}")


# V2: 续签和终止API
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"合同续签失败: {str(e)}")


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
    from decimal import Decimal

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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"合同终止失败: {str(e)}")


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

    - **contract_id**: 合同ID
    """
    from ...models.rent_contract import RentContract, RentDepositLedger

    # 检查合同是否存在
    contract = db.query(RentContract).filter(RentContract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    # 获取押金变动记录，按时间倒序
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

    - **contract_id**: 合同ID
    - 返回该合同的所有服务费台账，按年月倒序排列
    """
    from ...models.rent_contract import RentContract, ServiceFeeLedger

    # 检查合同是否存在
    contract = db.query(RentContract).filter(RentContract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    # 获取服务费台账，按年月倒序
    ledgers = (
        db.query(ServiceFeeLedger)
        .filter(ServiceFeeLedger.contract_id == contract_id)
        .order_by(ServiceFeeLedger.year_month.desc())
        .all()
    )

    return [ServiceFeeLedgerResponse.model_validate(ledger) for ledger in ledgers]


# 租金条款API
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
    # 验证合同是否存在
    contract = rent_contract.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    term_data = term_in.model_dump()
    term_data["contract_id"] = contract_id
    term = rent_term.create(db=db, obj_in=term_data)
    return term


# 租金台账API
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
        # 转换为Pydantic响应模型
        ledger_responses = []
        for ledger in ledgers:
            ledger_responses.append(RentLedgerResponse.model_validate(ledger))

        return {
            "message": f"成功生成 {len(ledger_responses)} 条台账记录",
            "ledgers": ledger_responses,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Don't catch HTTPException - let it propagate
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"生成台账失败: {str(e)}")


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

    # Convert ORM models to response schemas
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
        raise HTTPException(status_code=404, detail="台账记录不存在")
    return ledger


# 批量更新路由必须在参数路由之前，避免路径匹配冲突
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
        # Convert SQLAlchemy models to Pydantic schemas
        ledger_responses = [
            RentLedgerResponse.model_validate(ledger) for ledger in ledgers
        ]
        return {
            "message": f"成功更新 {len(ledgers)} 条台账记录",
            "ledgers": ledger_responses,
        }
    except Exception as e:
        # Don't catch HTTPException - let it propagate
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"批量更新失败: {str(e)}")


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
        raise HTTPException(status_code=404, detail="台账记录不存在")

    # 验证支付状态
    if ledger_in.payment_status is not None:
        valid_statuses = ["未支付", "部分支付", "已支付", "逾期"]
        if ledger_in.payment_status not in valid_statuses:
            raise HTTPException(
                status_code=422, detail=f"支付状态必须是: {', '.join(valid_statuses)}"
            )

    try:
        updated_ledger = rent_ledger.update(db=db, db_obj=ledger, obj_in=ledger_in)
        return updated_ledger
    except Exception as e:
        # Don't catch HTTPException - let it propagate
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"更新台账失败: {str(e)}")


# 统计报表API
@router.get("/statistics/overview", summary="获取租金统计概览")
def get_rent_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    ownership_ids: list[str] | None = Query(None, description="权属方ID列表"),
    asset_ids: list[str] | None = Query(None, description="资产ID列表"),
    contract_status: str | None = Query(None, description="合同状态"),
) -> Any:
    """
    获取租金统计概览信息
    """
    query_params = RentStatisticsQuery(
        start_date=start_date,
        end_date=end_date,
        ownership_ids=ownership_ids,
        asset_ids=asset_ids,
        contract_status=contract_status,
    )

    try:
        statistics = rent_contract_service.get_statistics(
            db=db, query_params=query_params
        )
        return statistics
    except Exception as e:
        # Don't catch HTTPException - let it propagate
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get(
    "/statistics/ownership",
    response_model=list[OwnershipRentStatistics],
    summary="权属方租金统计",
)
def get_ownership_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    ownership_ids: list[str] | None = Query(None, description="权属方ID列表"),
) -> Any:
    """
    按权属方统计租金情况
    """
    try:
        statistics = rent_contract_service.get_ownership_statistics(
            db=db, start_date=start_date, end_date=end_date, ownership_ids=ownership_ids
        )
        return statistics
    except Exception as e:
        # Don't catch HTTPException - let it propagate
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"获取权属方统计失败: {str(e)}")


@router.get(
    "/statistics/asset",
    response_model=list[AssetRentStatistics],
    summary="资产租金统计",
)
def get_asset_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    asset_ids: list[str] | None = Query(None, description="资产ID列表"),
) -> Any:
    """
    按资产统计租金情况
    """
    try:
        statistics = rent_contract_service.get_asset_statistics(
            db=db, start_date=start_date, end_date=end_date, asset_ids=asset_ids
        )
        return statistics
    except Exception as e:
        # Don't catch HTTPException - let it propagate
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"获取资产统计失败: {str(e)}")


@router.get(
    "/statistics/monthly",
    response_model=list[MonthlyRentStatistics],
    summary="月度租金统计",
)
def get_monthly_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    year: int | None = Query(None, description="年份"),
    start_month: str | None = Query(None, description="开始月份(YYYY-MM)"),
    end_month: str | None = Query(None, description="结束月份(YYYY-MM)"),
) -> Any:
    """
    获取月度租金统计
    """
    try:
        statistics = rent_contract_service.get_monthly_statistics(
            db=db, year=year, start_month=start_month, end_month=end_month
        )
        return statistics
    except Exception as e:
        # Don't catch HTTPException - let it propagate
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"获取月度统计失败: {str(e)}")


@router.get("/statistics/export", summary="导出统计数据")
def export_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    format: str = Query("excel", description="导出格式"),
) -> Any:
    """
    导出统计数据
    """
    try:
        from datetime import datetime

        from ..services.excel_export import export_statistics_report

        # 获取统计数据
        overview_stats = rent_contract_service.get_statistics(
            db=db,
            query_params=RentStatisticsQuery(
                start_date=start_date,
                end_date=end_date,
                ownership_ids=None,
                asset_ids=None,
                contract_status=None,
            ),
        )

        ownership_stats = rent_contract_service.get_ownership_statistics(
            db=db, start_date=start_date, end_date=end_date
        )

        asset_stats = rent_contract_service.get_asset_statistics(
            db=db, start_date=start_date, end_date=end_date
        )

        monthly_stats = rent_contract_service.get_monthly_statistics(db=db)

        # 生成Excel文件
        excel_data = export_statistics_report(
            overview_data=overview_stats,
            ownership_data=ownership_stats,
            asset_data=asset_stats,
            monthly_data=monthly_stats,
            start_date=start_date,
            end_date=end_date,
        )

        filename = f"rent_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return Response(
            content=excel_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        # Don't catch HTTPException - let it propagate
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"导出统计数据失败: {str(e)}")


# 辅助API
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
        limit=1000,  # 设置较大限制
    )
    return ledgers


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
        limit=1000,  # 设置较大限制
    )
    return contracts


# Excel导入导出API
@router.get("/excel/template", summary="下载Excel导入模板")
def download_excel_template(
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    """
    下载租金合同Excel导入模板
    """
    try:
        result = rent_contract_excel_service.download_contract_template()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])

        return FileResponse(
            result["file_path"],
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=result["file_name"],
        )
    except Exception as e:
        # Don't catch HTTPException - let it propagate
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"下载模板失败: {str(e)}")


@router.post("/excel/import", summary="Excel导入合同数据")
def import_contracts_from_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    import_terms: bool = Form(True, description="是否导入租金条款"),
    import_ledger: bool = Form(False, description="是否导入台账数据"),
    overwrite_existing: bool = Form(False, description="是否覆盖已存在的数据"),
) -> dict[str, Any]:
    """
    从Excel文件导入租金合同数据
    """
    from typing import cast

    try:
        # 保存上传的文件
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, file.filename or "upload.xlsx")

        with open(file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)

        # 导入数据
        result = rent_contract_excel_service.import_contracts_from_excel(
            file_path=file_path,
            import_terms=import_terms,
            import_ledger=import_ledger,
            overwrite_existing=overwrite_existing,
        )

        # 清理临时文件
        rent_contract_excel_service.cleanup_file(file_path)

        return cast(dict[str, Any], result)

    except Exception as e:
        # Don't catch HTTPException - let it propagate
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/excel/export", summary="Excel导出合同数据")
def export_contracts_to_excel(
    contract_ids: list[str] | None = Query(None, description="要导出的合同ID列表"),
    current_user: User = Depends(get_current_active_user),
    include_terms: bool = Query(True, description="是否包含租金条款"),
    include_ledger: bool = Query(True, description="是否包含台账数据"),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
) -> FileResponse:
    """
    导出租金合同数据到Excel文件
    """
    try:
        result = rent_contract_excel_service.export_contracts_to_excel(
            contract_ids=contract_ids,
            include_terms=include_terms,
            include_ledger=include_ledger,
            start_date=start_date,
            end_date=end_date,
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])

        return FileResponse(
            result["file_path"],
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=result["file_name"],
        )

    except Exception as e:
        # Don't catch HTTPException - let it propagate
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


# ==================== 合同附件管理 ====================


@router.post(
    "/{contract_id}/attachments", response_model=dict[str, Any], summary="上传合同附件"
)
async def upload_contract_attachment(
    contract_id: str,
    file: UploadFile = File(..., description="附件文件"),
    file_type: str = Form("other", description="文件类型: contract_scan/id_card/other"),
    description: str | None = Form(None, description="附件描述"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    上传合同附件

    支持的文件类型:
    - PDF (.pdf)
    - 图片 (.jpg, .jpeg, .png)
    - Word文档 (.doc, .docx)

    文件将存储在 uploads/contracts/ 目录下
    """
    import uuid
    from pathlib import Path

    from ...models.rent_contract import RentContractAttachment

    # 验证合同是否存在
    contract = rent_contract.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    # 验证文件类型
    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(allowed_extensions)}",
        )

    # 创建上传目录
    upload_dir = Path("uploads/contracts")
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 生成唯一文件名
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename

    # 保存文件
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        file_size = len(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    # 创建附件记录
    attachment = RentContractAttachment(
        contract_id=contract_id,
        file_name=file.filename or "unnamed",
        file_path=str(file_path),
        file_size=file_size,
        mime_type=file.content_type,
        file_type=file_type,
        description=description,
        uploader=current_user.full_name or current_user.username,
        uploader_id=current_user.id,
    )

    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return {
        "id": attachment.id,
        "file_name": attachment.file_name,
        "file_size": attachment.file_size,
        "file_type": attachment.file_type,
        "description": attachment.description,
        "uploaded_at": attachment.created_at.isoformat(),
    }


@router.get(
    "/{contract_id}/attachments", response_model=list[Any], summary="获取合同附件列表"
)
async def get_contract_attachments(
    contract_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    获取指定合同的所有附件
    """
    from ...models.rent_contract import RentContractAttachment

    # 验证合同是否存在
    contract = rent_contract.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    # 查询附件列表
    attachments = (
        db.query(RentContractAttachment)
        .filter(RentContractAttachment.contract_id == contract_id)
        .order_by(RentContractAttachment.created_at.desc())
        .all()
    )

    return [
        {
            "id": a.id,
            "file_name": a.file_name,
            "file_size": a.file_size,
            "file_type": a.file_type,
            "mime_type": a.mime_type,
            "description": a.description,
            "uploader": a.uploader,
            "uploaded_at": a.created_at.isoformat(),
        }
        for a in attachments
    ]


@router.get(
    "/{contract_id}/attachments/{attachment_id}/download", summary="下载合同附件"
)
async def download_contract_attachment(
    contract_id: str,
    attachment_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """
    下载指定的合同附件
    """
    from pathlib import Path

    from ...models.rent_contract import RentContractAttachment

    # 查询附件记录
    attachment = (
        db.query(RentContractAttachment)
        .filter(
            RentContractAttachment.id == attachment_id,
            RentContractAttachment.contract_id == contract_id,
        )
        .first()
    )

    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")

    # 验证文件是否存在
    file_path = Path(attachment.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=str(file_path),
        filename=attachment.file_name,
        media_type=attachment.mime_type or "application/octet-stream",
    )


@router.delete(
    "/{contract_id}/attachments/{attachment_id}",
    response_model=dict[str, Any],
    summary="删除合同附件",
)
async def delete_contract_attachment(
    contract_id: str,
    attachment_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    删除指定的合同附件
    """
    from pathlib import Path

    from ...models.rent_contract import RentContractAttachment

    # 查询附件记录
    attachment = (
        db.query(RentContractAttachment)
        .filter(
            RentContractAttachment.id == attachment_id,
            RentContractAttachment.contract_id == contract_id,
        )
        .first()
    )

    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")

    # 删除物理文件
    file_path = Path(attachment.file_path)
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception:
            # 即使文件删除失败,也继续删除数据库记录
            pass

    # 删除数据库记录
    db.delete(attachment)
    db.commit()

    return {"message": "附件已删除"}
