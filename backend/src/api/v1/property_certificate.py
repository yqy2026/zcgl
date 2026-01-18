"""
Property Certificate API Endpoints
产权证管理API
"""

import logging
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from starlette.requests import Request

from ...database import get_db
from ...middleware.auth import require_permission
from ...schemas.property_certificate import CertificateImportConfirm, PropertyCertificateUploadResponse
from ...services.property_certificate.service import PropertyCertificateService
from ...utils.file_security import generate_safe_filename, validate_file_extension
from ...core.router_registry import route_registry
from fastapi import APIRouter, Depends, File, UploadFile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/property-certificates", tags=["Property Certificates"])


@router.post("/upload", response_model=PropertyCertificateUploadResponse)
@require_permission("property_certificate", "create")
async def upload_certificate(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    上传产权证文件并提取信息

    Args:
        request: FastAPI Request 对象
        file: 上传的文件（PDF或图片格式，最大10MB）
        db: 数据库会话

    Returns:
        PropertyCertificateUploadResponse: 提取结果

    Raises:
        HTTPException: 文件验证失败或提取错误
    """
    # Validate filename
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名不能为空",
        )

    # Validate file extension
    allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png"]
    if not validate_file_extension(file.filename, allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型。允许的类型: {', '.join(allowed_extensions)}",
        )

    # Get file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    # Validate file size (10MB limit)
    max_size = 10 * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制 ({max_size // (1024 * 1024)}MB)",
        )

    # Generate safe filename
    file_id = str(uuid.uuid4())
    safe_filename = generate_safe_filename(file.filename, file_id)

    # Create temp directory
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    temp_file_path = temp_dir / safe_filename

    service = PropertyCertificateService(db)

    try:
        # Stream file in chunks to avoid memory issues
        chunk_size = 64 * 1024  # 64KB chunks
        total_size = 0

        with open(temp_file_path, "wb") as temp_file:
            while chunk := await file.read(chunk_size):
                total_size += len(chunk)
                if total_size > max_size:
                    # Clean up partial file
                    temp_file.close()
                    temp_file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"文件大小超过限制 ({max_size // (1024 * 1024)}MB)",
                    )
                temp_file.write(chunk)

        logger.info(f"Processing certificate upload: {safe_filename}, size: {total_size} bytes")

        # Extract information from file
        result = await service.extract_from_file(str(temp_file_path), safe_filename)

        # Transform result to response model
        response = PropertyCertificateUploadResponse(
            session_id=file_id,
            certificate_type="property_cert",
            extracted_data=result.get("data", {}),
            confidence_score=result.get("confidence", 0.0),
            asset_matches=[],  # TODO: Implement asset matching
            validation_errors=[],
            warnings=[],
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing certificate upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理产权证文件失败: {str(e)}",
        )
    finally:
        # Clean up temporary file
        if temp_file_path.exists():
            temp_file_path.unlink()
            logger.debug(f"Cleaned up temp file: {temp_file_path}")


@router.post("/confirm-import")
@require_permission("property_certificate", "create")
async def confirm_import(data: CertificateImportConfirm, db: Session = Depends(get_db)):
    """
    确认导入，创建产权证

    Args:
        data: 导入确认数据
        db: 数据库会话

    Returns:
        dict: 包含证书ID和状态

    Raises:
        HTTPException: 导入失败
    """
    try:
        service = PropertyCertificateService(db)
        certificate = await service.confirm_import(data.model_dump())

        logger.info(f"Created certificate {certificate.id} from upload session {data.session_id}")

        return {"certificate_id": certificate.id, "status": "success"}

    except ValueError as e:
        logger.error(f"Validation error confirming import: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"数据验证失败: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error confirming import: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入产权证失败: {str(e)}",
        )


# Register router
route_registry.register_router(
    router, prefix="/api/v1", tags=["Property Certificates"], version="v1"
)
