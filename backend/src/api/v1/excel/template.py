"""
Excel模板下载模块
"""

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....services.excel import ExcelTemplateService

router = APIRouter()


@router.get("/template", summary="下载Excel导入模板")
async def download_template(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """
    下载Excel导入模板文件 - 已优化与新增资产表单字段保持一致
    """
    # 使用ExcelTemplateService生成模板
    service = ExcelTemplateService(db)
    buffer = service.generate_template()

    # 返回文件流（避免重复读取buffer）
    async def file_generator() -> AsyncGenerator[bytes, None]:
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
