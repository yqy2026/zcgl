"""
Property Certificate API Endpoints
产权证管理API
"""

import logging
import os
import tempfile

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from ...core.router_registry import route_registry
from ...database import get_db
from ...services.property_certificate.service import PropertyCertificateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/property-certificates", tags=["Property Certificates"])


@router.post("/upload")
async def upload_certificate(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    """
    上传产权证文件并提取信息

    Args:
        file: 上传的文件（PDF或图片格式）
        db: 数据库会话

    Returns:
        提取结果，包含识别的字段和置信度
    """
    service = PropertyCertificateService(db)

    # Save uploaded file temporarily
    # Ensure filename is not None
    original_filename = file.filename or "uploaded_file"

    with tempfile.NamedTemporaryFile(delete=False, suffix=original_filename) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await service.extract_from_file(tmp_path, original_filename)
        return result
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/confirm-import")
async def confirm_import(data: dict, db: Session = Depends(get_db)):
    """
    确认导入，创建产权证

    Args:
        data: 包含提取字段和用户确认信息的字典
        db: 数据库会话

    Returns:
        创建的产权证ID和状态
    """
    service = PropertyCertificateService(db)
    certificate = await service.confirm_import(data)
    return {"certificate_id": certificate.id, "status": "success"}


# Register router
route_registry.register_router(
    router, prefix="/api/v1", tags=["Property Certificates"], version="v1"
)
