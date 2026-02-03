"""
催缴管理 API 端点

重构后：所有数据库操作委托给 CollectionService
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ....core.exception_handler import BaseBusinessError, not_found
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....core.router_registry import route_registry
from ....database import get_async_db
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
async def get_collection_summary(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> CollectionTaskSummary:
    return await db.run_sync(lambda sync_db: collection_service.get_summary(sync_db))


@router.get(
    "/records",
    response_model=APIResponse[PaginatedData[CollectionRecordResponse]],
    summary="获取催缴记录列表",
)
async def list_collection_records(
    ledger_id: str | None = Query(None, description="租金台账ID"),
    contract_id: str | None = Query(None, description="合同ID"),
    collection_status: CollectionStatus | None = Query(None, description="催缴状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> JSONResponse:
    result = await db.run_sync(
        lambda sync_db: collection_service.list_records(
            sync_db,
            ledger_id=ledger_id,
            contract_id=contract_id,
            collection_status=collection_status,
            page=page,
            page_size=page_size,
        )
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
async def get_collection_record(
    record_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> CollectionRecordResponse:
    record = await db.run_sync(
        lambda sync_db: collection_service.get_by_id(sync_db, record_id=record_id)
    )
    if not record:
        raise not_found(
            "催缴记录不存在",
            resource_type="collection_record",
            resource_id=record_id,
        )
    return CollectionRecordResponse.model_validate(record)


@router.post(
    "/records", response_model=CollectionRecordResponse, summary="创建催缴记录"
)
async def create_collection_record(
    record_data: CollectionRecordCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> CollectionRecordResponse:
    try:
        record = await db.run_sync(
            lambda sync_db: collection_service.create(
                sync_db,
                obj_in=record_data,
                operator=str(current_user.username or current_user.email),
                operator_id=str(current_user.id),
            )
        )
    except BaseBusinessError:
        raise

    return CollectionRecordResponse.model_validate(record)


@router.put(
    "/records/{record_id}",
    response_model=CollectionRecordResponse,
    summary="更新催缴记录",
)
async def update_collection_record(
    record_id: str,
    update_data: CollectionRecordUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> CollectionRecordResponse:
    def _sync(sync_db: Session) -> object | None:
        record = collection_service.get_by_id(sync_db, record_id=record_id)
        if not record:
            return None
        return collection_service.update(sync_db, db_obj=record, obj_in=update_data)

    updated_record = await db.run_sync(_sync)
    if not updated_record:
        raise not_found(
            "催缴记录不存在",
            resource_type="collection_record",
            resource_id=record_id,
        )
    return CollectionRecordResponse.model_validate(updated_record)


@router.delete("/records/{record_id}", summary="删除催缴记录")
async def delete_collection_record(
    record_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    def _sync(sync_db: Session) -> bool:
        record = collection_service.get_by_id(sync_db, record_id=record_id)
        if not record:
            return False
        collection_service.delete(sync_db, db_obj=record)
        return True

    deleted = await db.run_sync(_sync)
    if not deleted:
        raise not_found(
            "催缴记录不存在",
            resource_type="collection_record",
            resource_id=record_id,
        )
    return {"message": "催缴记录已删除"}


route_registry.register_router(
    router, prefix="/api/v1", tags=["催缴管理"], version="v1"
)
