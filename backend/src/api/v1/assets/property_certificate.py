"""
Property Certificate API Endpoints
产权证管理API
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import forbidden
from ....core.router_registry import route_registry
from ....database import get_async_db
from ....middleware.auth import (
    AuthzContext,
    get_current_active_user,
    require_authz,
)
from ....models.auth import User
from ....schemas.property_certificate import (
    PropertyCertificateCreate,
    PropertyCertificateResponse,
    PropertyCertificateUpdate,
)
from ....services.authz import authz_service
from ....services.organization import organization_service
from ....services.property_certificate.service import PropertyCertificateService

logger = logging.getLogger(__name__)

router = APIRouter()
_PROPERTY_CERTIFICATE_CREATE_UNSCOPED_PARTY_ID = (
    "__unscoped__:property_certificate:create"
)


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "":
        return None
    return normalized


def _resolve_current_user_organization_id(current_user: User) -> str | None:
    return _normalize_optional_str(current_user.organization_id)


async def _resolve_organization_party_id(
    *,
    db: AsyncSession,
    organization_id: str | None,
) -> str | None:
    normalized_organization_id = _normalize_optional_str(organization_id)
    if normalized_organization_id is None:
        return None

    organization = await organization_service.get_organization(
        db,
        org_id=normalized_organization_id,
    )
    if organization is None:
        return None
    return _normalize_optional_str(organization.represented_party_id)


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
        scoped_party_id or _PROPERTY_CERTIFICATE_CREATE_UNSCOPED_PARTY_ID
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


@router.get("", response_model=list[PropertyCertificateResponse])
@router.get("/", response_model=list[PropertyCertificateResponse])
async def list_certificates(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
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

    try:
        try:
            CertificateType(certificate.certificate_type)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"证书类型不正确: {str(e)}",
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


route_registry.register_router(
    router, prefix="/api/v1/property-certificates", tags=["产权证管理"], version="v1"
)
