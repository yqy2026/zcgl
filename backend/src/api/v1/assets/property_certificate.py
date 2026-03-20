"""
Property Certificate API Endpoints
产权证管理API
"""

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from ....core.exception_handler import BaseBusinessError, forbidden
from ....database import get_async_db
from ....middleware.auth import (
    AuthzContext,
    get_current_active_user,
    require_authz,
)
from ....models.auth import User
from ....schemas.property_certificate import (
    CertificateImportConfirm,
    PropertyCertificateCreate,
    PropertyCertificateResponse,
    PropertyCertificateUpdate,
    PropertyCertificateUploadResponse,
)
from ....services.authz import authz_service
from ....services.property_certificate.service import PropertyCertificateService
from ....services.view_scope import resolve_selected_view_party_filter_dependency
from ....utils.file_security import generate_safe_filename, validate_file_extension
from ....utils.str import normalize_optional_str

logger = logging.getLogger(__name__)

router = APIRouter()
_PROPERTY_CERTIFICATE_CREATE_UNSCOPED_PARTY_ID = (
    "__unscoped__:property_certificate:create"
)


def _resolve_current_user_organization_id(current_user: User) -> str | None:
    return normalize_optional_str(
        getattr(current_user, "default_organization_id", None)
    )


async def _resolve_organization_party_id(
    *,
    db: AsyncSession,
    organization_id: str | None,
) -> str | None:
    normalized_organization_id = normalize_optional_str(organization_id)
    if normalized_organization_id is None:
        return None

    from ....models.party import Party, PartyType

    stmt = (
        select(Party.id.label("party_id"))
        .where(
            Party.party_type == PartyType.ORGANIZATION.value,
            or_(
                Party.id == normalized_organization_id,
                Party.external_ref == normalized_organization_id,
            ),
        )
        .order_by(Party.id)
        .limit(1)
    )
    row = (await db.execute(stmt)).mappings().one_or_none()
    return normalize_optional_str(row.get("party_id") if row is not None else None)


async def _build_property_certificate_create_resource_context(
    *,
    db: AsyncSession,
    current_user: User,
) -> dict[str, Any]:
    organization_id = _resolve_current_user_organization_id(current_user)
    resource_context: dict[str, Any] = {}
    if organization_id is None:
        resource_context["party_id"] = _PROPERTY_CERTIFICATE_CREATE_UNSCOPED_PARTY_ID
        resource_context["owner_party_id"] = (
            _PROPERTY_CERTIFICATE_CREATE_UNSCOPED_PARTY_ID
        )
        resource_context["manager_party_id"] = (
            _PROPERTY_CERTIFICATE_CREATE_UNSCOPED_PARTY_ID
        )
        return resource_context

    resource_context["organization_id"] = organization_id
    scoped_party_id = await _resolve_organization_party_id(
        db=db,
        organization_id=organization_id,
    )
    resolved_party_id = (
        scoped_party_id if scoped_party_id is not None else organization_id
    )
    resource_context["party_id"] = resolved_party_id
    resource_context["owner_party_id"] = resolved_party_id
    resource_context["manager_party_id"] = resolved_party_id
    return resource_context


async def _require_property_certificate_create_authz(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    resource_context = await _build_property_certificate_create_resource_context(
        db=db,
        current_user=current_user,
    )

    try:
        decision = await authz_service.check_access(
            db,
            user_id=str(current_user.id),
            resource_type="property_certificate",
            action="create",
            resource_id=None,
            resource=resource_context,
        )
    except Exception:
        raise forbidden("权限校验失败")

    if not decision.allowed:
        raise forbidden("权限不足")

    return AuthzContext(
        current_user=current_user,
        action="create",
        resource_type="property_certificate",
        resource_id=None,
        resource_context=resource_context,
        allowed=True,
        reason_code=decision.reason_code,
    )


@router.post("/upload", response_model=PropertyCertificateUploadResponse)
async def upload_certificate(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_property_certificate_create_authz),
) -> PropertyCertificateUploadResponse:
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

    # 🔒 安全修复: 生成安全文件名，使用统一的允许类型
    file_id = str(uuid.uuid4())
    safe_filename = generate_safe_filename(
        file.filename, file_id, allowed_extensions=allowed_extensions
    )

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

        logger.info(
            f"Processing certificate upload: {safe_filename}, size: {total_size} bytes"
        )

        # Extract information from file
        result = await service.extract_from_file(str(temp_file_path), safe_filename)

        asset_matches = await service.match_assets(result.get("data", {}))

        # Transform result to response model
        response = PropertyCertificateUploadResponse(
            session_id=file_id,
            certificate_type="property_cert",
            extracted_data=result.get("data", {}),
            confidence_score=result.get("confidence", 0.0),
            asset_matches=asset_matches,
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
async def confirm_import(
    data: CertificateImportConfirm,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_property_certificate_create_authz),
) -> dict[str, Any]:
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
        organization_id = _resolve_current_user_organization_id(current_user)
        certificate = await service.confirm_import(
            data.model_dump(),
            created_by=str(current_user.id),
            organization_id=organization_id,
        )

        logger.info(
            f"Created certificate {certificate.id} from upload session {data.session_id}"
        )

        return {"certificate_id": certificate.id, "status": "success"}
    except BaseBusinessError:
        raise
    except Exception as e:
        logger.error(f"Error confirming import: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入产权证失败: {str(e)}",
        )


@router.get("/", response_model=list[PropertyCertificateResponse])
async def list_certificates(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    selected_view_party_filter=Depends(resolve_selected_view_party_filter_dependency),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="property_certificate",
        )
    ),
) -> list[PropertyCertificateResponse]:
    """
    获取产权证列表

    Args:
        skip: 跳过记录数
        limit: 返回记录数限制
        db: 数据库会话

    Returns:
        List[PropertyCertificateResponse]: 产权证列表
    """
    try:
        service = PropertyCertificateService(db)
        certificates = await service.list_certificates(
            skip=skip,
            limit=limit,
            current_user_id=str(current_user.id),
            party_filter=selected_view_party_filter,
        )
        logger.debug(
            "Retrieved %d certificates (skip=%d, limit=%d)",
            len(certificates),
            skip,
            limit,
        )
        return [
            PropertyCertificateResponse.model_validate(certificate)
            for certificate in certificates
        ]
    except Exception as e:
        logger.error(f"Error listing certificates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取产权证列表失败: {str(e)}",
        )


@router.get("/{certificate_id}", response_model=PropertyCertificateResponse)
async def get_certificate(
    certificate_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    selected_view_party_filter=Depends(resolve_selected_view_party_filter_dependency),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="property_certificate",
            resource_id="{certificate_id}",
            deny_as_not_found=True,
        )
    ),
) -> PropertyCertificateResponse:
    """
    获取产权证详情

    Args:
        certificate_id: 产权证ID
        db: 数据库会话

    Returns:
        PropertyCertificateResponse: 产权证详情

    Raises:
        HTTPException: 产权证不存在
    """
    try:
        service = PropertyCertificateService(db)
        cert = await service.get_certificate(
            certificate_id,
            current_user_id=str(current_user.id),
            party_filter=selected_view_party_filter,
        )
        if not cert:
            logger.warning(f"Certificate not found: {certificate_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="产权证不存在",
            )
        logger.debug(f"Retrieved certificate {certificate_id}")
        return PropertyCertificateResponse.model_validate(cert)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting certificate {certificate_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取产权证失败: {str(e)}",
        )


@router.post("/", response_model=PropertyCertificateResponse)
async def create_certificate(
    certificate: PropertyCertificateCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_property_certificate_create_authz),
) -> PropertyCertificateResponse:
    """
    手动创建产权证

    Args:
        certificate: 产权证创建数据
        db: 数据库会话

    Returns:
        PropertyCertificateResponse: 创建的产权证

    Raises:
        HTTPException: 创建失败
    """
    from ....models.property_certificate import CertificateType
    from ....services.property_certificate.validator import PropertyCertificateValidator

    try:
        try:
            cert_type = CertificateType(certificate.certificate_type)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"证书类型不正确: {str(e)}",
            )

        validation = PropertyCertificateValidator.validate_extracted_fields(
            certificate.model_dump(), cert_type
        )
        if not validation.is_valid():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"errors": validation.errors},
            )

        service = PropertyCertificateService(db)
        organization_id = _resolve_current_user_organization_id(current_user)
        result = await service.create_certificate(
            certificate,
            created_by=str(current_user.id),
            organization_id=organization_id,
        )
        logger.info(
            "Created certificate %s (number: %r)",
            result.id,
            certificate.certificate_number,
        )
        return PropertyCertificateResponse.model_validate(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating certificate: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建产权证失败: {str(e)}",
        )


@router.put("/{certificate_id}", response_model=PropertyCertificateResponse)
async def update_certificate(
    certificate_id: str,
    certificate: PropertyCertificateUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="property_certificate",
            resource_id="{certificate_id}",
        )
    ),
) -> PropertyCertificateResponse:
    """
    更新产权证

    Args:
        certificate_id: 产权证ID
        certificate: 更新数据
        db: 数据库会话

    Returns:
        PropertyCertificateResponse: 更新后的产权证

    Raises:
        HTTPException: 更新失败
    """
    try:
        service = PropertyCertificateService(db)
        cert = await service.get_certificate(
            certificate_id,
            current_user_id=str(current_user.id),
        )
        if not cert:
            logger.warning(f"Certificate not found: {certificate_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="产权证不存在",
            )

        updated = await service.update_certificate(cert, certificate)
        logger.info("Updated certificate %s", certificate_id)
        return PropertyCertificateResponse.model_validate(updated)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating certificate {certificate_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新产权证失败: {str(e)}",
        )


@router.delete("/{certificate_id}")
async def delete_certificate(
    certificate_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="delete",
            resource_type="property_certificate",
            resource_id="{certificate_id}",
        )
    ),
) -> dict[str, str]:
    """
    删除产权证

    Args:
        certificate_id: 产权证ID
        db: 数据库会话

    Returns:
        dict: 删除结果

    Raises:
        HTTPException: 删除失败
    """
    try:
        service = PropertyCertificateService(db)
        cert = await service.get_certificate(
            certificate_id,
            current_user_id=str(current_user.id),
        )
        if not cert:
            logger.warning(f"Certificate not found: {certificate_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="产权证不存在",
            )

        await service.delete_certificate(certificate_id)
        logger.info("Deleted certificate %s", certificate_id)
        return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting certificate {certificate_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除产权证失败: {str(e)}",
        )
