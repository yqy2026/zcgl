"""
催缴管理 API 端点

重构后：所有数据库操作委托给 CollectionService
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ....core.exception_handler import BaseBusinessError, not_found
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....core.router_registry import route_registry
from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....models.collection import CollectionStatus
from ....schemas.collection import (
    CollectionRecordCreate,
    CollectionRecordResponse,
    CollectionRecordUpdate,
    CollectionTaskSummary,
)
from ....services.collection import collection_service

router = APIRouter(prefix="/collection", tags=["催缴管理"])


@router.get(
    "/summary", response_model=CollectionTaskSummary, summary="获取催缴任务汇总"
)
def get_collection_summary(
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
    return collection_service.get_summary(db)


@router.get(
    "/records",
    response_model=APIResponse[PaginatedData[CollectionRecordResponse]],
    summary="获取催缴记录列表",
)
def list_collection_records(
    ledger_id: str | None = Query(None, description="租金台账ID"),
    contract_id: str | None = Query(None, description="合同ID"),
    collection_status: CollectionStatus | None = Query(None, description="催缴状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """查询催缴记录列表，支持按台账、合同、状态筛选"""
    result = collection_service.list_records(
        db,
        ledger_id=ledger_id,
        contract_id=contract_id,
        collection_status=collection_status,
        page=page,
        page_size=page_size,
    )

    items = [
        CollectionRecordResponse.model_validate(record) for record in result["items"]
    ]

    return ResponseHandler.paginated(
        data=items,
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        message="获取催缴记录列表成功",
    )


@router.get(
    "/records/{record_id}",
    response_model=CollectionRecordResponse,
    summary="获取催缴记录详情",
)
def get_collection_record(
    record_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CollectionRecordResponse:
    """获取单条催缴记录详情"""
    record = collection_service.get_by_id(db, record_id=record_id)

    if not record:
        raise not_found(
            "催缴记录不存在", resource_type="collection_record", resource_id=record_id
        )

    return CollectionRecordResponse.model_validate(record)


@router.post(
    "/records", response_model=CollectionRecordResponse, summary="创建催缴记录"
)
def create_collection_record(
    record_data: CollectionRecordCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CollectionRecordResponse:
    """创建新的催缴记录"""
    try:
        record = collection_service.create(
            db,
            obj_in=record_data,
            operator=str(current_user.username or current_user.email),
            operator_id=str(current_user.id),
        )
    except BaseBusinessError:
        raise

    return CollectionRecordResponse.model_validate(record)


@router.put(
    "/records/{record_id}",
    response_model=CollectionRecordResponse,
    summary="更新催缴记录",
)
def update_collection_record(
    record_id: str,
    update_data: CollectionRecordUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CollectionRecordResponse:
    """更新催缴记录（状态、承诺信息等）"""
    record = collection_service.get_by_id(db, record_id=record_id)

    if not record:
        raise not_found(
            "催缴记录不存在", resource_type="collection_record", resource_id=record_id
        )

    updated_record = collection_service.update(db, db_obj=record, obj_in=update_data)
    return CollectionRecordResponse.model_validate(updated_record)


@router.delete("/records/{record_id}", summary="删除催缴记录")
def delete_collection_record(
    record_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """删除催缴记录"""
    record = collection_service.get_by_id(db, record_id=record_id)

    if not record:
        raise not_found(
            "催缴记录不存在", resource_type="collection_record", resource_id=record_id
        )

    collection_service.delete(db, db_obj=record)
    return {"message": "催缴记录已删除"}


# 注册路由
route_registry.register_router(
    router, prefix="/api/v1", tags=["催缴管理"], version="v1"
)
