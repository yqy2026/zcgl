"""Provider-free temporary document-extraction session endpoints."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1 import property_certificate_extraction_sessions as property_sessions
from src.constants.document_processing_constants import (
    CONTRACT_MAX_PDF_PAGES,
    DOCUMENT_PAGES_PER_BATCH,
    PROPERTY_CERTIFICATE_MAX_PDF_PAGES,
)
from src.core.cache_manager import RedisCache, cache_manager
from src.core.config_llm import LlmSettings
from src.core.exception_handler import (
    BaseBusinessError,
    OperationNotAllowedError,
    forbidden,
    internal_error,
)
from src.core.router_registry import route_registry
from src.database import get_async_db
from src.middleware.auth import get_current_active_user
from src.models.auth import User
from src.models.contract_group import ContractDirection, GroupRelationType, RevenueMode
from src.schemas.extraction_session import (
    ExtractionSessionConfirmRequest,
    PropertyCertificateExistingExtractionConfirmRequest,
    PropertyCertificateExtractionConfirmRequest,
)
from src.services.authz import authz_service
from src.services.contract.contract_group_service import (
    validate_revenue_mode_compatibility,
)
from src.services.document.candidate_review import (
    CandidateReviewError,
    CandidateReviewService,
)
from src.services.document.contract_extraction_workflow import (
    ContractExtractionWorkflow,
)
from src.services.document.deepseek_text_enrichment import DeepSeekTextEnricher
from src.services.document.extraction_sessions import (
    ExtractionSessionRepository,
    ExtractionSessionStateError,
)
from src.services.document.page_text_pipeline import get_ordered_page_text_pipeline
from src.services.file_upload import StagedFileService, UploadPurpose

logger = logging.getLogger(__name__)

router = APIRouter()
_TEMP_UPLOAD_ROOT = Path("temp_uploads")
_CONTRACT_CREATE_RESOURCE_CONTEXT = {
    "party_id": "__unscoped__:contract:create",
    "owner_party_id": "__unscoped__:contract:create",
    "manager_party_id": "__unscoped__:contract:create",
}
_PROPERTY_CERTIFICATE_CREATE_RESOURCE_CONTEXT = {
    "party_id": "__unscoped__:property_certificate:create",
    "owner_party_id": "__unscoped__:property_certificate:create",
    "manager_party_id": "__unscoped__:property_certificate:create",
}


def _workflow() -> ContractExtractionWorkflow:
    backend = cache_manager.backend
    if not isinstance(backend, RedisCache):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="distributed extraction sessions require Redis",
        )
    return ContractExtractionWorkflow(
        repository=ExtractionSessionRepository(backend.client),
        pipeline=get_ordered_page_text_pipeline(max_pdf_pages=CONTRACT_MAX_PDF_PAGES),
        reviewer=CandidateReviewService(),
        enricher=DeepSeekTextEnricher(LlmSettings()),
        lifecycle=StagedFileService(_TEMP_UPLOAD_ROOT),
    )


async def _authorize(
    *,
    db: AsyncSession,
    current_user: User,
    resource_type: str,
    action: str,
    resource_id: str | None,
    resource_context: Mapping[str, str] | None = None,
    deny_as_not_found: bool = False,
) -> None:
    try:
        decision = await authz_service.check_access(
            db,
            user_id=str(current_user.id),
            resource_type=resource_type,
            action=action,
            resource_id=resource_id,
            resource=dict(resource_context or {}),
        )
    except Exception as exc:
        raise forbidden("权限校验失败") from exc
    if decision.allowed:
        return
    if deny_as_not_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="session not found"
        )
    raise forbidden("权限不足")


def _context(
    *,
    project_id: str,
    revenue_mode: str,
    contract_direction: str,
    group_relation_type: str,
) -> dict[str, str]:
    try:
        revenue_mode_value = RevenueMode(revenue_mode)
        ContractDirection(contract_direction)
        group_relation_type_value = GroupRelationType(group_relation_type)
        validate_revenue_mode_compatibility(
            revenue_mode_value,
            group_relation_type_value,
        )
    except (OperationNotAllowedError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid contract extraction context",
        ) from exc
    return {
        "project_id": project_id,
        "revenue_mode": revenue_mode,
        "contract_direction": contract_direction,
        "group_relation_type": group_relation_type,
    }


def _session_error(exc: ExtractionSessionStateError) -> HTTPException:
    if str(exc) == "session_not_found":
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="session not found"
        )
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _require_property_context(session: Mapping[str, object]) -> Mapping[str, str]:
    context = session.get("context")
    if not isinstance(context, Mapping):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="session not found"
        )
    return {str(key): str(value) for key, value in context.items()}


async def _authorize_existing_session(
    *, db: AsyncSession, current_user: User, session: Mapping[str, object]
) -> dict[str, object] | None:
    """授权既有解析会话；产权证目标返回完整会话快照，contract 目标返回 None。

    public_session（_workflow().get 的返回值）有意剥离 context；产权证授权的
    context 校验（mode/asset_id/certificate_id）需要完整会话（2026-08-14 验收
    ACC-009 回归修复）。调用方（confirm）应复用本函数返回的快照，端点层不再二次
    get_raw：同一仓库的两次读取是冗余 IO，即用即弃会话也可能在两次读取之间被清理
    （2026-08-14 两轴复核 D9）；workflow 内部 confirm 经 repository.transition
    的状态机读取不在此列。
    """
    if session.get("target_type") == "contract":
        await _authorize(
            db=db,
            current_user=current_user,
            resource_type="contract",
            action="create",
            resource_id=None,
            resource_context=_CONTRACT_CREATE_RESOURCE_CONTEXT,
        )
        return None
    if session.get("target_type") != "property_certificate":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="session not found"
        )
    # public_session（_workflow().get 的返回值）有意剥离 context；产权证授权的
    # context 校验（mode/asset_id/certificate_id）需要完整会话，否则解析会话创建后
    # GET/confirm 一律 404（2026-08-14 验收 ACC-009 回归修复）。
    raw_session = property_sessions._workflow().get_raw(
        str(session.get("session_id", ""))
    )
    if raw_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="session not found"
        )
    context = _require_property_context(raw_session)
    if context.get("mode") == "existing":
        await _authorize(
            db=db,
            current_user=current_user,
            resource_type="property_certificate",
            action="read",
            resource_id=context.get("certificate_id"),
            deny_as_not_found=True,
        )
        return raw_session
    await _authorize(
        db=db,
        current_user=current_user,
        resource_type="property_certificate",
        action="create",
        resource_id=None,
        resource_context=_PROPERTY_CERTIFICATE_CREATE_RESOURCE_CONTEXT,
    )
    return raw_session


@router.post("/extraction-sessions", status_code=status.HTTP_201_CREATED)
async def create_extraction_session(
    target_type: Annotated[Literal["contract", "property_certificate"], Form()],
    file: Annotated[UploadFile | None, File()] = None,
    project_id: Annotated[str | None, Form()] = None,
    revenue_mode: Annotated[str | None, Form()] = None,
    contract_direction: Annotated[str | None, Form()] = None,
    group_relation_type: Annotated[str | None, Form()] = None,
    asset_id: Annotated[str | None, Form()] = None,
    certificate_id: Annotated[str | None, Form()] = None,
    attachment_id: Annotated[str | None, Form()] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, object]:
    if target_type == "contract":
        if (
            file is None
            or project_id is None
            or revenue_mode is None
            or contract_direction is None
            or group_relation_type is None
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="contract context and file are required",
            )
        await _authorize(
            db=db,
            current_user=current_user,
            resource_type="contract",
            action="create",
            resource_id=None,
            resource_context=_CONTRACT_CREATE_RESOURCE_CONTEXT,
        )
        context = _context(
            project_id=project_id,
            revenue_mode=revenue_mode,
            contract_direction=contract_direction,
            group_relation_type=group_relation_type,
        )
        workflow = _workflow()
        lifecycle = StagedFileService(_TEMP_UPLOAD_ROOT)
        staged = await lifecycle.stage_upload(file, UploadPurpose.CONTRACT_EXTRACTION)
        try:
            return workflow.create(staged=staged, context=context)
        except BaseBusinessError:
            raise
        except Exception as exc:
            raise internal_error(
                "document extraction failed", original_error=exc
            ) from exc

    if asset_id is None or asset_id.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="asset_id is required",
        )
    if certificate_id is not None or attachment_id is not None:
        if file is not None or certificate_id is None or attachment_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="existing attachment reference is incomplete",
            )
        await _authorize(
            db=db,
            current_user=current_user,
            resource_type="property_certificate",
            action="read",
            resource_id=certificate_id,
            deny_as_not_found=True,
        )
        return await property_sessions._workflow().create_existing(
            db=db,
            asset_id=asset_id,
            certificate_id=certificate_id,
            attachment_id=attachment_id,
        )
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="property certificate file is required",
        )
    await _authorize(
        db=db,
        current_user=current_user,
        resource_type="property_certificate",
        action="create",
        resource_id=None,
        resource_context=_PROPERTY_CERTIFICATE_CREATE_RESOURCE_CONTEXT,
    )
    lifecycle = StagedFileService(_TEMP_UPLOAD_ROOT)
    staged = await lifecycle.stage_upload(
        file, UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION
    )
    try:
        return property_sessions._workflow().create(
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


@router.get("/extraction-sessions/{session_id}")
async def get_extraction_session(
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, object]:
    session = _workflow().get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="session not found"
        )
    await _authorize_existing_session(db=db, current_user=current_user, session=session)
    return session


@router.post("/extraction-sessions/{session_id}/confirm")
async def confirm_extraction_session(
    session_id: str,
    payload: dict[str, object],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    session = _workflow().get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="session not found"
        )
    # 授权即快照：产权证确认直接复用授权步骤返回的完整会话，端点层不再二次 get_raw
    # （2026-08-14 两轴复核 D9）。
    raw_session = await _authorize_existing_session(
        db=db, current_user=current_user, session=session
    )
    try:
        if session.get("target_type") == "contract":
            contract_request = ExtractionSessionConfirmRequest.model_validate(payload)
            contract_id = await _workflow().confirm(
                session_id=session_id,
                actions=[action.model_dump() for action in contract_request.actions],
                party_ids=contract_request.party_ids.model_dump(),
                asset_ids=contract_request.asset_ids,
                db=db,
                current_user_id=str(current_user.id),
            )
            return {"contract_id": contract_id}
        if raw_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="session not found"
            )
        context = _require_property_context(raw_session)
        if context.get("mode") == "existing":
            existing_request = (
                PropertyCertificateExistingExtractionConfirmRequest.model_validate(
                    payload
                )
            )
            return await property_sessions._confirm_property_certificate_extraction_session(
                session_id=session_id,
                actions=[action.model_dump() for action in existing_request.actions],
                certificate_type="other",
                holder_party_ids=[],
                link_existing_certificate_id=None,
                attach_staged=False,
                db=db,
                current_user_id=str(current_user.id),
            )
        certificate_request = (
            PropertyCertificateExtractionConfirmRequest.model_validate(payload)
        )
        return await property_sessions._confirm_property_certificate_extraction_session(
            session_id=session_id,
            actions=[action.model_dump() for action in certificate_request.actions],
            certificate_type=certificate_request.certificate_type,
            holder_party_ids=certificate_request.holder_party_ids,
            link_existing_certificate_id=certificate_request.link_existing_certificate_id,
            attach_staged=certificate_request.attach_staged,
            db=db,
            current_user_id=str(current_user.id),
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.errors()
        ) from exc
    except HTTPException:
        raise
    except ExtractionSessionStateError as exc:
        raise _session_error(exc) from exc
    except CandidateReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except BaseBusinessError:
        raise
    except Exception as exc:
        logger.exception("document extraction confirmation failed: %s", exc)
        raise internal_error(
            "document extraction confirmation failed", original_error=exc
        ) from exc


@router.post(
    "/extraction-sessions/{session_id}/cancel", status_code=status.HTTP_204_NO_CONTENT
)
async def cancel_extraction_session(
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    session = _workflow().get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="session not found"
        )
    await _authorize_existing_session(db=db, current_user=current_user, session=session)
    try:
        if session.get("target_type") == "property_certificate":
            property_sessions._workflow().cancel(session_id)
        else:
            _workflow().cancel(session_id)
    except ExtractionSessionStateError as exc:
        raise _session_error(exc) from exc


@router.get("/document-extraction/capabilities")
async def document_extraction_capabilities() -> dict[str, object]:
    return {
        "targets": [
            {"target_type": "contract", "input": "pdf_upload"},
            {"target_type": "property_certificate", "input": "pdf_or_image_upload"},
        ],
        "limits": {
            "max_contract_pages": CONTRACT_MAX_PDF_PAGES,
            "property_certificate_pdf_max_pages": (PROPERTY_CERTIFICATE_MAX_PDF_PAGES),
            "pages_per_batch": DOCUMENT_PAGES_PER_BATCH,
            "contract_pdf_max_bytes": 50 * 1024 * 1024,
        },
        "stages": ["ready_for_review", "disabled"],
    }


route_registry.register_router(
    router, prefix="/api/v1", tags=["document extraction"], version="v1"
)

__all__ = ["router"]
