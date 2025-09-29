"""
租金台账相关API接口
"""

from typing import Any, List, Optional
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Response, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import tempfile
import os

from ...database import get_db
from ...models import RentContract, RentTerm, RentLedger
from ...schemas.rent_contract import (
    RentContractCreate, RentContractUpdate, RentContractResponse,
    RentTermCreate, RentTermUpdate, RentTermResponse,
    RentLedgerCreate, RentLedgerUpdate, RentLedgerResponse,
    RentLedgerBatchUpdate, GenerateLedgerRequest,
    RentStatisticsQuery, RentContractListResponse, RentLedgerListResponse,
    OwnershipRentStatistics, AssetRentStatistics, MonthlyRentStatistics
)
from ...crud.rent_contract import rent_contract, rent_term, rent_ledger
from ...crud.asset import asset_crud
from ...crud.ownership import ownership
from ...services.rent_contract_excel import rent_contract_excel_service

router = APIRouter()


# 租金合同API
@router.post("/contracts", response_model=RentContractResponse, summary="创建租金合同")
def create_contract(
    *,
    db: Session = Depends(get_db),
    contract_in: RentContractCreate
) -> Any:
    """
    创建新的租金合同，包含租金条款信息
    """
    try:
        # 验证关联的资产和权属方是否存在
        asset = asset_crud.get(db, id=contract_in.asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="关联的资产不存在")

        ownership = ownership.get(db, id=contract_in.ownership_id)
        if not ownership:
            raise HTTPException(status_code=404, detail="关联的权属方不存在")

        contract = rent_contract.create_with_terms(db=db, obj_in=contract_in)
        return contract
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建合同失败: {str(e)}")


@router.get("/contracts/{contract_id}", response_model=RentContractResponse, summary="获取租金合同详情")
def get_contract(
    contract_id: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    获取租金合同详情，包含租金条款信息
    """
    contract = rent_contract.get_with_details(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    return contract


@router.get("/contracts", response_model=RentContractListResponse, summary="获取租金合同列表")
def get_contracts(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    contract_number: Optional[str] = Query(None, description="合同编号筛选"),
    tenant_name: Optional[str] = Query(None, description="承租方名称筛选"),
    asset_id: Optional[str] = Query(None, description="资产ID筛选"),
    ownership_id: Optional[str] = Query(None, description="权属方ID筛选"),
    contract_status: Optional[str] = Query(None, description="合同状态筛选"),
    start_date: Optional[date] = Query(None, description="开始日期筛选"),
    end_date: Optional[date] = Query(None, description="结束日期筛选")
) -> Any:
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
        end_date=end_date
    )

    pages = (total + limit - 1) // limit

    return RentContractListResponse(
        items=contracts,
        total=total,
        page=page,
        limit=limit,
        pages=pages
    )


@router.put("/contracts/{contract_id}", response_model=RentContractResponse, summary="更新租金合同")
def update_contract(
    contract_id: str,
    *,
    db: Session = Depends(get_db),
    contract_in: RentContractUpdate
) -> Any:
    """
    更新租金合同信息
    """
    contract = rent_contract.get_with_details(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    try:
        updated_contract = rent_contract.update_with_terms(
            db=db, db_obj=contract, obj_in=contract_in
        )
        return updated_contract
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新合同失败: {str(e)}")


@router.delete("/contracts/{contract_id}", summary="删除租金合同")
def delete_contract(
    contract_id: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    删除租金合同（同时删除相关的租金条款和台账记录）
    """
    contract = rent_contract.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    try:
        rent_contract.remove(db, id=contract_id)
        return {"message": "合同删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除合同失败: {str(e)}")


# 租金条款API
@router.get("/contracts/{contract_id}/terms", response_model=List[RentTermResponse], summary="获取合同租金条款")
def get_contract_terms(
    contract_id: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    获取指定合同的所有租金条款
    """
    terms = rent_term.get_by_contract(db, contract_id=contract_id)
    return terms


@router.post("/contracts/{contract_id}/terms", response_model=RentTermResponse, summary="添加租金条款")
def add_rent_term(
    contract_id: str,
    *,
    db: Session = Depends(get_db),
    term_in: RentTermCreate
) -> Any:
    """
    为合同添加新的租金条款
    """
    # 验证合同是否存在
    contract = rent_contract.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    term_data = term_in.dict()
    term_data["contract_id"] = contract_id
    term = rent_term.create(db=db, obj_in=term_data)
    return term


# 租金台账API
@router.post("/ledger/generate", summary="生成月度台账")
def generate_monthly_ledger(
    *,
    db: Session = Depends(get_db),
    request: GenerateLedgerRequest
) -> Any:
    """
    根据合同信息生成月度租金台账
    """
    try:
        ledgers = rent_ledger.generate_monthly_ledger(db=db, request=request)
        return {
            "message": f"成功生成 {len(ledgers)} 条台账记录",
            "ledgers": ledgers
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成台账失败: {str(e)}")


@router.get("/ledger", response_model=RentLedgerListResponse, summary="获取租金台账列表")
def get_rent_ledger(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    contract_id: Optional[str] = Query(None, description="合同ID筛选"),
    asset_id: Optional[str] = Query(None, description="资产ID筛选"),
    ownership_id: Optional[str] = Query(None, description="权属方ID筛选"),
    year_month: Optional[str] = Query(None, description="年月筛选"),
    payment_status: Optional[str] = Query(None, description="支付状态筛选"),
    start_date: Optional[date] = Query(None, description="开始日期筛选"),
    end_date: Optional[date] = Query(None, description="结束日期筛选")
) -> Any:
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
        end_date=end_date
    )

    pages = (total + limit - 1) // limit

    return RentLedgerListResponse(
        items=ledgers,
        total=total,
        page=page,
        limit=limit,
        pages=pages
    )


@router.get("/ledger/{ledger_id}", response_model=RentLedgerResponse, summary="获取租金台账详情")
def get_rent_ledger_detail(
    ledger_id: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    获取租金台账详情
    """
    ledger = rent_ledger.get(db, id=ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="台账记录不存在")
    return ledger


@router.put("/ledger/{ledger_id}", response_model=RentLedgerResponse, summary="更新租金台账")
def update_rent_ledger(
    ledger_id: str,
    *,
    db: Session = Depends(get_db),
    ledger_in: RentLedgerUpdate
) -> Any:
    """
    更新租金台账信息（支付状态等）
    """
    ledger = rent_ledger.get(db, id=ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="台账记录不存在")

    try:
        updated_ledger = rent_ledger.update(db=db, db_obj=ledger, obj_in=ledger_in)
        return updated_ledger
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新台账失败: {str(e)}")


@router.put("/ledger/batch", summary="批量更新租金台账")
def batch_update_rent_ledger(
    *,
    db: Session = Depends(get_db),
    request: RentLedgerBatchUpdate
) -> Any:
    """
    批量更新租金台账支付状态
    """
    try:
        ledgers = rent_ledger.batch_update_payment(db=db, request=request)
        return {
            "message": f"成功更新 {len(ledgers)} 条台账记录",
            "ledgers": ledgers
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量更新失败: {str(e)}")


# 统计报表API
@router.get("/statistics/overview", summary="获取租金统计概览")
def get_rent_statistics(
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    ownership_ids: Optional[List[str]] = Query(None, description="权属方ID列表"),
    asset_ids: Optional[List[str]] = Query(None, description="资产ID列表")
) -> Any:
    """
    获取租金统计概览信息
    """
    query_params = RentStatisticsQuery(
        start_date=start_date,
        end_date=end_date,
        ownership_ids=ownership_ids,
        asset_ids=asset_ids
    )

    try:
        statistics = rent_ledger.get_statistics(db=db, query_params=query_params)
        return statistics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/statistics/ownership", response_model=List[OwnershipRentStatistics], summary="权属方租金统计")
def get_ownership_statistics(
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    ownership_ids: Optional[List[str]] = Query(None, description="权属方ID列表")
) -> Any:
    """
    按权属方统计租金情况
    """
    try:
        statistics = rent_ledger.get_ownership_statistics(
            db=db,
            start_date=start_date,
            end_date=end_date,
            ownership_ids=ownership_ids
        )
        return statistics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取权属方统计失败: {str(e)}")


@router.get("/statistics/asset", response_model=List[AssetRentStatistics], summary="资产租金统计")
def get_asset_statistics(
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    asset_ids: Optional[List[str]] = Query(None, description="资产ID列表")
) -> Any:
    """
    按资产统计租金情况
    """
    try:
        statistics = rent_ledger.get_asset_statistics(
            db=db,
            start_date=start_date,
            end_date=end_date,
            asset_ids=asset_ids
        )
        return statistics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资产统计失败: {str(e)}")


@router.get("/statistics/monthly", response_model=List[MonthlyRentStatistics], summary="月度租金统计")
def get_monthly_statistics(
    db: Session = Depends(get_db),
    year: Optional[int] = Query(None, description="年份"),
    start_month: Optional[str] = Query(None, description="开始月份(YYYY-MM)"),
    end_month: Optional[str] = Query(None, description="结束月份(YYYY-MM)")
) -> Any:
    """
    获取月度租金统计
    """
    try:
        statistics = rent_ledger.get_monthly_statistics(
            db=db,
            year=year,
            start_month=start_month,
            end_month=end_month
        )
        return statistics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取月度统计失败: {str(e)}")


@router.get("/statistics/export", summary="导出统计数据")
def export_statistics(
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    format: str = Query("excel", description="导出格式")
) -> Any:
    """
    导出统计数据
    """
    try:
        from ..services.excel_export import export_statistics_report
        from datetime import datetime

        # 获取统计数据
        overview_stats = rent_ledger.get_statistics(
            db=db,
            query_params=RentStatisticsQuery(
                start_date=start_date,
                end_date=end_date
            )
        )

        ownership_stats = rent_ledger.get_ownership_statistics(
            db=db,
            start_date=start_date,
            end_date=end_date
        )

        asset_stats = rent_ledger.get_asset_statistics(
            db=db,
            start_date=start_date,
            end_date=end_date
        )

        monthly_stats = rent_ledger.get_monthly_statistics(
            db=db
        )

        # 生成Excel文件
        excel_data = export_statistics_report(
            overview_data=overview_stats,
            ownership_data=ownership_stats,
            asset_data=asset_stats,
            monthly_data=monthly_stats,
            start_date=start_date,
            end_date=end_date
        )

        filename = f"rent_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return Response(
            content=excel_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出统计数据失败: {str(e)}")


# 辅助API
@router.get("/contracts/{contract_id}/ledger", response_model=List[RentLedgerResponse], summary="获取合同台账")
def get_contract_ledger(
    contract_id: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    获取指定合同的所有台账记录
    """
    ledgers, _ = rent_ledger.get_multi_with_filters(
        db=db,
        contract_id=contract_id,
        limit=1000  # 设置较大限制
    )
    return ledgers


@router.get("/assets/{asset_id}/contracts", response_model=List[RentContractResponse], summary="获取资产合同")
def get_asset_contracts(
    asset_id: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    获取指定资产的所有合同
    """
    contracts, _ = rent_contract.get_multi_with_filters(
        db=db,
        asset_id=asset_id,
        limit=1000  # 设置较大限制
    )
    return contracts


# Excel导入导出API
@router.get("/excel/template", summary="下载Excel导入模板")
def download_excel_template():
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
            filename=result["file_name"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载模板失败: {str(e)}")


@router.post("/excel/import", summary="Excel导入合同数据")
def import_contracts_from_excel(
    file: UploadFile = File(...),
    import_terms: bool = Form(True, description="是否导入租金条款"),
    import_ledger: bool = Form(False, description="是否导入台账数据"),
    overwrite_existing: bool = Form(False, description="是否覆盖已存在的数据")
):
    """
    从Excel文件导入租金合同数据
    """
    try:
        # 保存上传的文件
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, file.filename)

        with open(file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)

        # 导入数据
        result = rent_contract_excel_service.import_contracts_from_excel(
            file_path=file_path,
            import_terms=import_terms,
            import_ledger=import_ledger,
            overwrite_existing=overwrite_existing
        )

        # 清理临时文件
        rent_contract_excel_service.cleanup_file(file_path)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/excel/export", summary="Excel导出合同数据")
def export_contracts_to_excel(
    contract_ids: Optional[List[str]] = Query(None, description="要导出的合同ID列表"),
    include_terms: bool = Query(True, description="是否包含租金条款"),
    include_ledger: bool = Query(True, description="是否包含台账数据"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期")
):
    """
    导出租金合同数据到Excel文件
    """
    try:
        result = rent_contract_excel_service.export_contracts_to_excel(
            contract_ids=contract_ids,
            include_terms=include_terms,
            include_ledger=include_ledger,
            start_date=start_date,
            end_date=end_date
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])

        return FileResponse(
            result["file_path"],
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=result["file_name"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")