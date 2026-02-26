"""
Excel模板下载模块
"""

from collections.abc import Generator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.middleware.auth import AuthzContext, get_current_active_user, require_authz
from src.models.auth import User
from src.services.excel import ExcelTemplateService

router = APIRouter()


@router.get("/template", summary="下载Excel导入模板")
async def download_template(
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="asset",
        )
    ),
) -> StreamingResponse:
    """
    下载Excel导入模板文件 - 已优化与新增资产表单字段保持一致
    """
    # 使用ExcelTemplateService生成模板
    service = ExcelTemplateService()
    buffer = service.generate_template()

    # 返回文件流（避免重复读取buffer）
    def file_generator() -> Generator[bytes, None, None]:
        data = buffer.getvalue()
        yield data
        buffer.close()

    return StreamingResponse(
        file_generator(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=land_property_asset_template.xlsx"
        },
    )
