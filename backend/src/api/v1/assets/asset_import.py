"""资产导入API路由模块。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import internal_error
from ....database import get_async_db
from ....middleware.auth import require_permission
from ....models.auth import User
from ....schemas.asset import AssetImportRequest, AssetImportResponse
from ....services.asset.import_service import AsyncAssetImportService

# 创建导入路由器
router = APIRouter()


@router.post("/import", response_model=AssetImportResponse, summary="导入资产数据")
async def import_assets(
    request: AssetImportRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("asset", "create")),
) -> AssetImportResponse:
    """
    批量导入资产数据

    - **data**: 待导入的资产数据列表
    - **import_mode**: 导入模式（create/merge/update）
    - **skip_errors**: 是否跳过错误数据
    - **dry_run**: 是否仅验证不实际导入
    """

    try:
        service = AsyncAssetImportService(db)
        return await service.import_assets(request=request, current_user=current_user)
    except Exception as e:
        raise internal_error(f"资产导入失败: {str(e)}")
