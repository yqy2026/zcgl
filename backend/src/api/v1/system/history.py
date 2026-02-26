"""
资产历史记录API路由
"""

from typing import Any

from fastapi import APIRouter, Depends, Path, Query
from fastapi.params import Depends as DependsParam
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import (
    BaseBusinessError,
    ResourceNotFoundError,
    internal_error,
)
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....database import get_async_db
from ....middleware.auth import (
    AuthzContext,
    get_current_active_user,
    require_admin,
    require_authz,
)
from ....models.auth import User
from ....schemas.asset import AssetHistoryResponse
from ....services.history.history_service import HistoryService, get_history_service

# 创建历史路由器
router = APIRouter(dependencies=[Depends(get_current_active_user)])


def _resolve_service(service: HistoryService | Any) -> HistoryService | Any:
    if isinstance(service, DependsParam):
        return get_history_service()
    return service


@router.get(
    "/",
    response_model=APIResponse[PaginatedData[AssetHistoryResponse]],
    summary="获取历史记录列表",
)
async def get_history_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数"),
    asset_id: str | None = Query(None, description="资产ID筛选"),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="history",
        )
    ),
    service: HistoryService = Depends(get_history_service),
) -> JSONResponse:
    """
    获取资产历史记录列表

    - **page**: 页码，从1开始
    - **limit**: 每页记录数，最多100
    - **asset_id**: 按资产ID筛选
    """

    try:
        skip = (page - 1) * page_size
        resolved_service = _resolve_service(service)
        history_records, total = await resolved_service.get_history_list(
            db=db,
            skip=skip,
            limit=page_size,
            asset_id=asset_id,
        )

        items = [
            AssetHistoryResponse.model_validate(record) for record in history_records
        ]
        return ResponseHandler.paginated(
            data=items,
            page=page,
            page_size=page_size,
            total=total,
            message="获取历史记录成功",
        )

    except ResourceNotFoundError:
        raise
    except Exception as e:
        raise internal_error(f"获取历史记录失败: {str(e)}")


@router.get(
    "/{history_id}", response_model=AssetHistoryResponse, summary="获取历史记录详情"
)
async def get_history_detail(
    history_id: str = Path(..., description="历史记录ID"),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="history",
            resource_id="{history_id}",
        )
    ),
    service: HistoryService = Depends(get_history_service),
) -> AssetHistoryResponse:
    """
    根据ID获取历史记录详情

    - **history_id**: 历史记录ID
    """

    try:
        resolved_service = _resolve_service(service)
        history_record = await resolved_service.get_history_detail(
            db=db,
            history_id=history_id,
        )

        return AssetHistoryResponse.model_validate(history_record)

    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取历史记录详情失败: {str(e)}")


@router.delete("/{history_id}", summary="删除历史记录")
async def delete_history(
    history_id: str = Path(..., description="历史记录ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="delete",
            resource_type="history",
            resource_id="{history_id}",
        )
    ),
    service: HistoryService = Depends(get_history_service),
) -> dict[str, Any]:
    """
    删除历史记录

    - **history_id**: 历史记录ID
    """

    try:
        resolved_service = _resolve_service(service)
        await resolved_service.delete_history(
            db=db,
            history_id=history_id,
        )
        return {"message": f"历史记录 {history_id} 已成功删除"}

    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"删除历史记录失败: {str(e)}")
