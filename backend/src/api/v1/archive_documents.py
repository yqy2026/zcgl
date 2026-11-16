"""Scoped archive endpoints for v5 property certificates."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import AuthzContext, get_current_active_user, require_authz
from ...models.auth import User
from ...schemas.archive_batch_match import (
    BatchMatchCommitRequest,
    BatchMatchCommitResponse,
    BatchMatchPreviewResponse,
)
from ...schemas.archive_document import (
    ArchiveDocumentItem,
    ArchiveDocumentListResponse,
    HandoverTargets,
)
from ...services.asset_operations import AssetOperationsPermissionDeniedError
from ...services.asset_operations.archive_batch_match_service import (
    archive_batch_match_service,
)
from ...services.asset_operations.archive_document_query_service import (
    CONTENT_TYPES,
    archive_document_query_service,
    render_pdf_first_page,
)
from ...services.party_scope_resolver import party_scope_resolver

router = APIRouter()
ArchiveAccess = Annotated[
    AuthzContext | None,
    Depends(
        require_authz(
            action="archive",
            resource_type="asset_ops",
            denial_error_factory=AssetOperationsPermissionDeniedError,
        )
    ),
]
DocumentArchiveAccess = Annotated[
    AuthzContext | None,
    Depends(
        require_authz(
            action="archive",
            resource_type="asset_ops",
            resource_id="{document_id}",
            denial_error_factory=AssetOperationsPermissionDeniedError,
        )
    ),
]


@router.post("/archive/documents", response_model=ArchiveDocumentItem, status_code=201)
async def upload_archive_document(
    target_type: Annotated[
        Literal[
            "property_certificate",
            "contract_supplement",
            "contract_lifecycle_event",
            "upstream_contract",
            "terminal_contract",
        ],
        Form(),
    ],
    target_id: Annotated[str, Form(min_length=1)],
    document_type: Annotated[
        Literal[
            "property_certificate",
            "supplement",
            "handover",
            "upstream_contract",
            "terminal_contract",
        ],
        Form(),
    ],
    file: Annotated[UploadFile, File()],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: ArchiveAccess = None,
) -> ArchiveDocumentItem:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    if (
        document_type
        != (
            {
                "contract_supplement": "supplement",
                "contract_lifecycle_event": "handover",
                "property_certificate": "property_certificate",
                "upstream_contract": "upstream_contract",
                "terminal_contract": "terminal_contract",
            }[target_type]
        )
    ):
        raise HTTPException(422, "Invalid archive target/type pair")
    if target_type == "contract_lifecycle_event":
        return await archive_document_query_service.append_handover(
            db, target_id=target_id, file=file, actor_id=actor_id, scope=scope
        )
    if target_type == "contract_supplement":
        return await archive_document_query_service.append_supplement(
            db, target_id=target_id, file=file, actor_id=actor_id, scope=scope
        )
    if target_type in ("upstream_contract", "terminal_contract"):
        return await archive_document_query_service.append_contract_scan(
            db,
            target_type=target_type,
            target_id=target_id,
            file=file,
            actor_id=actor_id,
            scope=scope,
        )
    return await archive_document_query_service.append_document(
        db, certificate_id=target_id, file=file, actor_id=actor_id, scope=scope
    )


@router.post(
    "/archive/documents/{document_id}/replacement",
    response_model=ArchiveDocumentItem,
    status_code=201,
)
async def replace_archive_document(
    document_id: str,
    file: Annotated[UploadFile, File()],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: DocumentArchiveAccess = None,
) -> ArchiveDocumentItem:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await archive_document_query_service.replace_document(
        db, document_id=document_id, file=file, actor_id=actor_id, scope=scope
    )


ReadAccess = Annotated[
    AuthzContext | None,
    Depends(
        require_authz(
            action="read",
            resource_type="asset_ops",
            denial_error_factory=AssetOperationsPermissionDeniedError,
        )
    ),
]
DocumentReadAccess = Annotated[
    AuthzContext | None,
    Depends(
        require_authz(
            action="read",
            resource_type="asset_ops",
            resource_id="{document_id}",
            denial_error_factory=AssetOperationsPermissionDeniedError,
        )
    ),
]


@router.get("/archive/handover-targets", response_model=HandoverTargets)
async def handover_targets(
    contract_kind: Literal["upstream", "terminal"],
    contract_id: Annotated[str, Query(min_length=1)],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: ReadAccess = None,
) -> HandoverTargets:
    scope = await party_scope_resolver.resolve(db, user_id=str(current_user.id))
    return await archive_document_query_service.handover_targets(
        db, kind=contract_kind, contract_id=contract_id, scope=scope
    )


@router.get("/archive/documents", response_model=ArchiveDocumentListResponse)
async def list_archive_documents(
    target_type: Literal[
        "property_certificate",
        "contract_supplement",
        "contract_lifecycle_event",
        "upstream_contract",
        "terminal_contract",
        "management_fee_statement",
    ],
    target_id: Annotated[str, Query(min_length=1)],
    document_type: Literal[
        "property_certificate",
        "supplement",
        "handover",
        "upstream_contract",
        "terminal_contract",
        "management_fee_statement",
    ] = "property_certificate",
    include_history: bool = True,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: ReadAccess = None,
) -> ArchiveDocumentListResponse:
    scope = await party_scope_resolver.resolve(db, user_id=str(current_user.id))
    if (
        document_type
        != (
            {
                "contract_supplement": "supplement",
                "contract_lifecycle_event": "handover",
                "property_certificate": "property_certificate",
                "upstream_contract": "upstream_contract",
                "terminal_contract": "terminal_contract",
                "management_fee_statement": "management_fee_statement",
            }[target_type]
        )
    ):
        raise HTTPException(422, "Invalid archive target/type pair")
    if target_type == "contract_lifecycle_event":
        return await archive_document_query_service.list_handover(
            db, target_id=target_id, scope=scope, include_history=include_history
        )
    if target_type == "contract_supplement":
        return await archive_document_query_service.list_supplement(
            db, target_id=target_id, scope=scope, include_history=include_history
        )
    if target_type in ("upstream_contract", "terminal_contract"):
        return await archive_document_query_service.list_contract_scan(
            db,
            target_type=target_type,
            target_id=target_id,
            scope=scope,
            include_history=include_history,
        )
    if target_type == "management_fee_statement":
        return await archive_document_query_service.list_statement(
            db, target_id=target_id, scope=scope, include_history=include_history
        )
    return await archive_document_query_service.list_documents(
        db, certificate_id=target_id, scope=scope, include_history=include_history
    )


@router.get("/archive/documents/{document_id}/content")
async def download_archive_document(
    document_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: DocumentReadAccess = None,
) -> FileResponse:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    result = await archive_document_query_service.prepare_download(
        db, document_id=document_id, actor_id=actor_id, scope=scope
    )
    return FileResponse(
        result.path,
        filename=result.attachment.file_name,
        media_type=CONTENT_TYPES[result.attachment.file_type],
        content_disposition_type="attachment",
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/archive/documents/{document_id}/thumbnail")
async def get_archive_document_thumbnail(
    document_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: DocumentReadAccess = None,
) -> Response:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    result = await archive_document_query_service.prepare_thumbnail(
        db, document_id=document_id, actor_id=actor_id, scope=scope
    )
    if result.attachment.file_type != "pdf":
        raise HTTPException(404, "Thumbnail only available for PDF archives")
    thumbnail = render_pdf_first_page(result.path)
    return Response(
        content=thumbnail,
        media_type="image/png",
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/archive/batch-matches/preview", response_model=BatchMatchPreviewResponse)
async def preview_batch_matches(
    files: Annotated[list[UploadFile], File()],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: ArchiveAccess = None,
) -> BatchMatchPreviewResponse:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await archive_batch_match_service.preview(
        db, files=files, actor_id=actor_id, scope=scope
    )


@router.post(
    "/archive/batch-matches", response_model=BatchMatchCommitResponse, status_code=201
)
async def commit_batch_matches(
    payload: BatchMatchCommitRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: ArchiveAccess = None,
) -> BatchMatchCommitResponse:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await archive_batch_match_service.commit(
        db, request=payload, actor_id=actor_id, scope=scope
    )


route_registry.register_router(
    router, prefix="/api/v1", tags=["资产运营档案"], version="v1"
)
