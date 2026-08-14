"""Reviewed property-certificate extraction session endpoints."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from src.constants.document_processing_constants import (
    PROPERTY_CERTIFICATE_MAX_PDF_PAGES,
)
from src.core.cache_manager import RedisCache, cache_manager
from src.core.config_llm import LlmSettings
from src.core.exception_handler import BaseBusinessError, internal_error
from src.database import get_async_db
from src.middleware.auth import AuthzContext, get_current_active_user, require_authz
from src.models.auth import User
from src.schemas.extraction_session import (
    PropertyCertificateExistingExtractionConfirmRequest,
    PropertyCertificateExtractionConfirmRequest,
)
from src.services.document.candidate_review import (
    CandidateReviewError,
    CandidateReviewService,
)
from src.services.document.deepseek_text_enrichment import DeepSeekTextEnricher
from src.services.document.extraction_sessions import (
    ExtractionSessionRepository,
    ExtractionSessionStateError,
)
from src.services.document.page_text_pipeline import get_ordered_page_text_pipeline
from src.services.document.property_certificate_extraction_workflow import (
    PropertyCertificateConflictError,
    PropertyCertificateExtractionWorkflow,
)
from src.services.file_upload import StagedFileService, UploadPurpose

router = APIRouter()
_TEMP_UPLOAD_ROOT = Path("temp_uploads")
_PROPERTY_CERTIFICATE_CREATE_CONTEXT = {
    "party_id": "__unscoped__:property_certificate:create",
    "owner_party_id": "__unscoped__:property_certificate:create",
    "manager_party_id": "__unscoped__:property_certificate:create",
}


def _workflow() -> PropertyCertificateExtractionWorkflow:
    backend = cache_manager.backend
    if not isinstance(backend, RedisCache):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="distributed extraction sessions require Redis",
        )
    return PropertyCertificateExtractionWorkflow(
        repository=ExtractionSessionRepository(backend.client),
        pipeline=get_ordered_page_text_pipeline(
            max_pdf_pages=PROPERTY_CERTIFICATE_MAX_PDF_PAGES
        ),
        reviewer=CandidateReviewService(),
        enricher=DeepSeekTextEnricher(LlmSettings()),
        lifecycle=StagedFileService(_TEMP_UPLOAD_ROOT),
    )


def _session_error(exc: ExtractionSessionStateError) -> HTTPException:
    if str(exc) == "session_not_found":
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="session not found"
        )
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/property-certificate-extraction-sessions",
    status_code=status.HTTP_201_CREATED,
)
async def create_property_certificate_extraction_session(
    asset_id: Annotated[str, Form(min_length=1)],
    file: Annotated[UploadFile, File()],
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="property_certificate",
            resource_context=_PROPERTY_CERTIFICATE_CREATE_CONTEXT,
        )
    ),
) -> dict[str, object]:
    _ = current_user, _authz
    lifecycle = StagedFileService(_TEMP_UPLOAD_ROOT)
    staged = await lifecycle.stage_upload(
        file, UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION
    )
    try:
        return _workflow().create(
            staged=staged,
            context={"mode": "new", "source_kind": "staged", "asset_id": asset_id},
        )
    except HTTPException:
        lifecycle.discard_staged(staged)
        raise
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error(
            "property certificate extraction failed", original_error=exc
        ) from exc


@router.post(
    "/property-certificates/{certificate_id}/extraction-sessions",
    status_code=status.HTTP_201_CREATED,
)
async def create_existing_property_certificate_review_session(
    certificate_id: str,
    asset_id: Annotated[str, Form(min_length=1)],
    attachment_id: Annotated[str, Form(min_length=1)],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="property_certificate",
            resource_id="{certificate_id}",
            deny_as_not_found=True,
        )
    ),
) -> dict[str, object]:
    _ = current_user, _authz
    try:
        return await _workflow().create_existing(
            db=db,
            asset_id=asset_id,
            certificate_id=certificate_id,
            attachment_id=attachment_id,
        )
    except CandidateReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise internal_error(
            "property certificate review failed", original_error=exc
        ) from exc


@router.get("/property-certificate-extraction-sessions/{session_id}")
async def get_property_certificate_extraction_session(
    session_id: str,
) -> dict[str, object]:
    session = _workflow().get(session_id)
    if session is None or session.get("target_type") != "property_certificate":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="session not found"
        )
    return session


async def _confirm_property_certificate_extraction_session(
    session_id: str,
    actions: Sequence[Mapping[str, str | None]],
    certificate_type: str,
    holder_party_ids: list[str],
    link_existing_certificate_id: str | None,
    attach_staged: bool,
    db: AsyncSession,
    current_user_id: str,
) -> dict[str, str]:
    try:
        certificate_id = await _workflow().confirm(
            session_id=session_id,
            actions=actions,
            certificate_type=certificate_type,
            holder_party_ids=holder_party_ids,
            link_existing_certificate_id=link_existing_certificate_id,
            attach_staged=attach_staged,
            db=db,
            current_user_id=current_user_id,
        )
        return {"certificate_id": certificate_id}
    except PropertyCertificateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except ExtractionSessionStateError as exc:
        raise _session_error(exc) from exc
    except CandidateReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except BaseBusinessError:
        raise
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "property certificate confirmation failed: %s", exc
        )
        raise internal_error(
            "property certificate confirmation failed", original_error=exc
        ) from exc


@router.post("/property-certificate-extraction-sessions/{session_id}/confirm")
async def confirm_property_certificate_extraction_session(
    session_id: str,
    payload: PropertyCertificateExtractionConfirmRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="property_certificate",
            resource_context=_PROPERTY_CERTIFICATE_CREATE_CONTEXT,
        )
    ),
) -> dict[str, str]:
    _ = _authz
    return await _confirm_property_certificate_extraction_session(
        session_id=session_id,
        actions=[action.model_dump() for action in payload.actions],
        certificate_type=payload.certificate_type,
        holder_party_ids=payload.holder_party_ids,
        link_existing_certificate_id=payload.link_existing_certificate_id,
        attach_staged=payload.attach_staged,
        db=db,
        current_user_id=str(current_user.id),
    )


@router.post(
    "/property-certificates/{certificate_id}/extraction-sessions/{session_id}/confirm"
)
async def confirm_existing_property_certificate_review_session(
    certificate_id: str,
    session_id: str,
    payload: PropertyCertificateExistingExtractionConfirmRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="property_certificate",
            resource_id="{certificate_id}",
            deny_as_not_found=True,
        )
    ),
) -> dict[str, str]:
    _ = _authz
    session = _workflow().get(session_id)
    context = session.get("context") if session is not None else None
    if (
        session is None
        or session.get("target_type") != "property_certificate"
        or not isinstance(context, Mapping)
        or context.get("mode") != "existing"
        or context.get("certificate_id") != certificate_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="session not found"
        )
    return await _confirm_property_certificate_extraction_session(
        session_id=session_id,
        actions=[action.model_dump() for action in payload.actions],
        certificate_type="other",
        holder_party_ids=[],
        link_existing_certificate_id=None,
        attach_staged=False,
        db=db,
        current_user_id=str(current_user.id),
    )


@router.post(
    "/property-certificate-extraction-sessions/{session_id}/cancel",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_property_certificate_extraction_session(session_id: str) -> None:
    try:
        _workflow().cancel(session_id)
    except ExtractionSessionStateError as exc:
        raise _session_error(exc) from exc


__all__ = ["router"]
