"""Property-certificate generic attachment endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import BaseBusinessError, internal_error
from src.core.router_registry import route_registry
from src.database import get_async_db
from src.middleware.auth import AuthzContext, get_current_active_user, require_authz
from src.models.attachment import Attachment
from src.models.auth import User
from src.services.property_certificate.attachment_service import (
    property_certificate_attachment_service,
)

router = APIRouter()


def _attachment_response(attachment: Attachment) -> dict[str, object]:
    return {
        "id": str(attachment.id),
        "file_name": attachment.file_name,
        "file_type": attachment.file_type,
        "file_size": attachment.file_size,
        "created_at": attachment.created_at,
    }


@router.get("/property-certificates/{certificate_id}/attachments")
async def list_property_certificate_attachments(
    certificate_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="property_certificate",
            resource_id="{certificate_id}",
        )
    ),
) -> list[dict[str, object]]:
    _ = current_user, _authz
    return [
        _attachment_response(item)
        for item in await property_certificate_attachment_service.list(
            db, certificate_id=certificate_id
        )
    ]


@router.post(
    "/property-certificates/{certificate_id}/attachments",
    status_code=status.HTTP_201_CREATED,
)
async def append_property_certificate_attachments(
    certificate_id: str,
    files: Annotated[list[UploadFile], File()],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="property_certificate",
            resource_id="{certificate_id}",
        )
    ),
) -> dict[str, list[dict[str, object]]]:
    _ = _authz
    results: list[dict[str, object]] = []
    for file in files:
        try:
            attachment = await property_certificate_attachment_service.append(
                db,
                certificate_id=certificate_id,
                file=file,
                user_id=str(current_user.id),
            )
            results.append(
                {
                    "file_name": attachment.file_name,
                    "attachment": _attachment_response(attachment),
                }
            )
        except BaseBusinessError as exc:
            results.append(
                {
                    "file_name": file.filename or "unknown",
                    "error": str(exc),
                }
            )
    return {"results": results}


@router.put("/property-certificates/{certificate_id}/attachments/{attachment_id}")
async def replace_property_certificate_attachment(
    certificate_id: str,
    attachment_id: str,
    file: Annotated[UploadFile, File()],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="property_certificate",
            resource_id="{certificate_id}",
        )
    ),
) -> dict[str, object]:
    _ = _authz
    try:
        attachment = await property_certificate_attachment_service.replace(
            db,
            certificate_id=certificate_id,
            attachment_id=attachment_id,
            file=file,
            user_id=str(current_user.id),
        )
        return _attachment_response(attachment)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error(
            "property certificate attachment replacement failed", original_error=exc
        ) from exc


@router.delete(
    "/property-certificates/{certificate_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_property_certificate_attachment(
    certificate_id: str,
    attachment_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="delete",
            resource_type="property_certificate",
            resource_id="{certificate_id}",
        )
    ),
) -> None:
    _ = current_user, _authz
    try:
        await property_certificate_attachment_service.delete(
            db, certificate_id=certificate_id, attachment_id=attachment_id
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error(
            "property certificate attachment deletion failed", original_error=exc
        ) from exc


@router.get(
    "/property-certificates/{certificate_id}/attachments/{attachment_id}/preview"
)
async def preview_property_certificate_attachment(
    certificate_id: str,
    attachment_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="property_certificate",
            resource_id="{certificate_id}",
        )
    ),
) -> FileResponse:
    _ = _authz
    result = await property_certificate_attachment_service.prepare_download(
        db,
        certificate_id=certificate_id,
        attachment_id=attachment_id,
        user_id=str(current_user.id),
    )
    return FileResponse(
        result.path,
        media_type={
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
        }[result.attachment.file_type],
        content_disposition_type="inline",
    )


@router.get(
    "/property-certificates/{certificate_id}/attachments/{attachment_id}/download"
)
async def download_property_certificate_attachment(
    certificate_id: str,
    attachment_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="export",
            resource_type="property_certificate",
            resource_id="{certificate_id}",
        )
    ),
) -> FileResponse:
    _ = _authz
    result = await property_certificate_attachment_service.prepare_download(
        db,
        certificate_id=certificate_id,
        attachment_id=attachment_id,
        user_id=str(current_user.id),
    )
    return FileResponse(
        result.path,
        filename=result.attachment.file_name,
        media_type={
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
        }[result.attachment.file_type],
    )


route_registry.register_router(
    router, prefix="/api/v1", tags=["property certificate attachments"], version="v1"
)

__all__ = ["router"]
