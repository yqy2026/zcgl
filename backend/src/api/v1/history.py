"""
资产历史记录API路由
"""

from typing import Any

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from ...core.api_errors import internal_error, not_found
from ...core.exception_handler import ResourceNotFoundError
from ...crud.asset import asset_crud
from ...crud.history import history_crud
from ...database import get_db
from ...schemas.asset import AssetHistoryResponse

# 创建历史路由器
router = APIRouter()


@router.get("/", summary="获取历史记录列表")
async def get_history_list(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    asset_id: str | None = Query(None, description="资产ID筛选"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    获取资产历史记录列表

    - **page**: 页码，从1开始
    - **limit**: 每页记录数，最多100
    - **asset_id**: 按资产ID筛选
    """
    try:
        if asset_id:
            # 检查资产是否存在
            asset = asset_crud.get(db=db, id=asset_id)
            if not asset:
                raise ResourceNotFoundError("Asset", asset_id)

            # 获取特定资产的历史记录
            history_records = history_crud.get_by_asset_id(db=db, asset_id=asset_id)

            # 简单分页
            start = (page - 1) * limit
            end = start + limit
            paginated_records = history_records[start:end]

            return {
                "items": paginated_records,
                "total": len(history_records),
                "page": page,
                "limit": limit,
                "pages": (len(history_records) + limit - 1) // limit,
            }
        else:
            # 获取所有历史记录
            skip = (page - 1) * limit
            history_records = history_crud.get_multi(db=db, skip=skip, limit=limit)

            # 这里简化处理，实际应该有总数统计
            return {
                "items": history_records,
                "total": len(history_records),
                "page": page,
                "limit": limit,
                "pages": 1,  # 简化处理
            }

    except ResourceNotFoundError:
        raise
    except Exception as e:
        raise internal_error(f"获取历史记录失败: {str(e)}")


@router.get(
    "/{history_id}", response_model=AssetHistoryResponse, summary="获取历史记录详情"
)
async def get_history_detail(
    history_id: str = Path(..., description="历史记录ID"), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    根据ID获取历史记录详情

    - **history_id**: 历史记录ID
    """
    try:
        history_record = history_crud.get(db=db, id=history_id)
        if not history_record:
            raise not_found(
                f"历史记录 {history_id} 不存在",
                resource_type="history",
                resource_id=history_id,
            )

        return history_record

    except Exception as e:
        if "UnifiedError" in type(e).__name__:
            raise
        raise internal_error(f"获取历史记录详情失败: {str(e)}")


@router.delete("/{history_id}", summary="删除历史记录")
async def delete_history(
    history_id: str = Path(..., description="历史记录ID"), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    删除历史记录

    - **history_id**: 历史记录ID
    """
    try:
        history_record = history_crud.get(db=db, id=history_id)
        if not history_record:
            raise not_found(
                f"历史记录 {history_id} 不存在",
                resource_type="history",
                resource_id=history_id,
            )

        history_crud.remove(db=db, id=history_id)
        return {"message": f"历史记录 {history_id} 已成功删除"}

    except Exception as e:
        if "UnifiedError" in type(e).__name__:
            raise
        raise internal_error(f"删除历史记录失败: {str(e)}")
