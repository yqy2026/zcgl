"""
催缴管理 API 端点
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.router_registry import route_registry
from ...models.auth import User
from ...models.collection import CollectionRecord, CollectionStatus
from ...models.rent_contract import RentLedger
from ...schemas.collection import (
    CollectionRecordCreate,
    CollectionRecordListResponse,
    CollectionRecordResponse,
    CollectionRecordUpdate,
    CollectionTaskSummary,
)
from ...services.auth.dependency import get_current_active_user

router = APIRouter(prefix="/collection", tags=["催缴管理"])


@router.get(
    "/summary", response_model=CollectionTaskSummary, summary="获取催缴任务汇总"
)
async def get_collection_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CollectionTaskSummary:
    """
    获取催缴任务汇总统计

    包括：
    - 逾期台账总数和总金额
    - 待催缴数量
    - 本月催缴次数
    - 催缴成功率
    """
    from sqlalchemy import and_, func

    today = date.today()
    current_month_start = date(today.year, today.month, 1)

    # 1. 统计逾期台账
    overdue_stats = (
        db.query(
            func.count(RentLedger.id).label("total_count"),
            func.sum(RentLedger.overdue_amount).label("total_amount"),
        )
        .filter(
            and_(
                RentLedger.payment_status.in_(["未支付", "部分支付"]),
                RentLedger.due_date < today,
                RentLedger.data_status == "正常",
            )
        )
        .first()
    )

    total_overdue_count = overdue_stats.total_count if overdue_stats else 0
    total_overdue_amount = overdue_stats.total_amount if overdue_stats else Decimal("0")

    # 2. 统计待催缴数量（状态为 pending 或 in_progress 的记录）
    pending_count = (
        db.query(func.count(CollectionRecord.id))
        .filter(
            CollectionRecord.collection_status.in_(
                [CollectionStatus.PENDING, CollectionStatus.IN_PROGRESS]
            )
        )
        .scalar()
    )
    pending_collection_count = pending_count or 0

    # 3. 统计本月催缴次数
    this_month_count = (
        db.query(func.count(CollectionRecord.id))
        .filter(CollectionRecord.collection_date >= current_month_start)
        .scalar()
    )
    this_month_collection_count = this_month_count or 0

    # 4. 计算催缴成功率（状态为 success 的记录占比）
    success_count = (
        db.query(func.count(CollectionRecord.id))
        .filter(CollectionRecord.collection_status == CollectionStatus.SUCCESS)
        .scalar()
    )
    total_collection_count = db.query(func.count(CollectionRecord.id)).scalar()

    collection_success_rate = None
    if total_collection_count and total_collection_count > 0:
        collection_success_rate = (
            Decimal(success_count or 0)
            / Decimal(total_collection_count)
            * Decimal("100")
        )

    return CollectionTaskSummary(
        total_overdue_count=total_overdue_count,
        total_overdue_amount=total_overdue_amount,
        pending_collection_count=pending_collection_count,
        this_month_collection_count=this_month_collection_count,
        collection_success_rate=collection_success_rate,
    )


@router.get(
    "/records",
    response_model=CollectionRecordListResponse,
    summary="获取催缴记录列表",
)
async def list_collection_records(
    ledger_id: str | None = Query(None, description="租金台账ID"),
    contract_id: str | None = Query(None, description="合同ID"),
    collection_status: CollectionStatus | None = Query(None, description="催缴状态"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CollectionRecordListResponse:
    """查询催缴记录列表，支持按台账、合同、状态筛选"""

    query = db.query(CollectionRecord)

    # 应用筛选条件
    if ledger_id:
        query = query.filter(CollectionRecord.ledger_id == ledger_id)
    if contract_id:
        query = query.filter(CollectionRecord.contract_id == contract_id)
    if collection_status:
        query = query.filter(CollectionRecord.collection_status == collection_status)

    # 计算总数
    total = query.count()

    # 分页
    offset = (page - 1) * limit
    records = (
        query.order_by(CollectionRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # 计算总页数
    pages = (total + limit - 1) // limit if total > 0 else 0

    return CollectionRecordListResponse(
        items=records,  # type: ignore[arg-type]  # FastAPI handles ORM to response model conversion
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get(
    "/records/{record_id}",
    response_model=CollectionRecordResponse,
    summary="获取催缴记录详情",
)
async def get_collection_record(
    record_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CollectionRecordResponse:
    """获取单条催缴记录详情"""
    record = db.query(CollectionRecord).filter(CollectionRecord.id == record_id).first()

    if not record:
        raise HTTPException(status_code=404, detail="催缴记录不存在")

    return record


@router.post(
    "/records", response_model=CollectionRecordResponse, summary="创建催缴记录"
)
async def create_collection_record(
    record_data: CollectionRecordCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CollectionRecordResponse:
    """创建新的催缴记录"""
    # 验证台账和合同存在
    ledger = db.query(RentLedger).filter(RentLedger.id == record_data.ledger_id).first()
    if not ledger:
        raise HTTPException(status_code=404, detail="租金台账不存在")

    # 设置操作人
    if not record_data.operator:
        record_data.operator = str(current_user.username or current_user.email)
    if not record_data.operator_id:
        record_data.operator_id = str(current_user.id)

    # 创建记录
    record = CollectionRecord(**record_data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)

    return record


@router.put(
    "/records/{record_id}",
    response_model=CollectionRecordResponse,
    summary="更新催缴记录",
)
async def update_collection_record(
    record_id: str,
    update_data: CollectionRecordUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CollectionRecordResponse:
    """更新催缴记录（状态、承诺信息等）"""
    record = db.query(CollectionRecord).filter(CollectionRecord.id == record_id).first()

    if not record:
        raise HTTPException(status_code=404, detail="催缴记录不存在")

    # 更新字段
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)

    return record


@router.delete("/records/{record_id}", summary="删除催缴记录")
async def delete_collection_record(
    record_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """删除催缴记录"""
    record = db.query(CollectionRecord).filter(CollectionRecord.id == record_id).first()

    if not record:
        raise HTTPException(status_code=404, detail="催缴记录不存在")

    db.delete(record)
    db.commit()

    return {"message": "催缴记录已删除"}


# 注册路由
route_registry.register_router(
    router, prefix="/api/v1", tags=["催缴管理"], version="v1"
)
