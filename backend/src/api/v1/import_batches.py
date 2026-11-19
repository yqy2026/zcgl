"""Import template download, scan staging and import batch lifecycle endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import AuthzContext, get_current_active_user, require_authz
from ...models.attachment import Attachment
from ...models.auth import User
from ...schemas.import_batch import (
    ImportBatchChangePage,
    ImportBatchChangeResponse,
    ImportBatchListResponse,
    ImportBatchStatusResponse,
    ImportCommitPreviewResponse,
    ImportCommitRequest,
    ImportCommitResponse,
    ImportRevertPreviewResponse,
    ImportRevertRequest,
    ImportRevertResponse,
    ImportSelectionRequest,
    ImportStagedFile,
    ImportStagingResponse,
)
from ...services.asset_operations.errors import AssetOperationsPermissionDeniedError
from ...services.asset_operations.import_batch_service import (
    import_batch_service,
    staging_owner_id,
)
from ...services.asset_operations.import_template_service import (
    build_template_workbook,
)
from ...services.party_scope_resolver import party_scope_resolver

router = APIRouter(tags=["资产运营"])

AssetOpsRead = Annotated[
    AuthzContext | None,
    Depends(
        require_authz(
            action="read",
            resource_type="asset_ops",
            denial_error_factory=AssetOperationsPermissionDeniedError,
        )
    ),
]
AssetOpsWrite = Annotated[
    AuthzContext | None,
    Depends(
        require_authz(
            action="write",
            resource_type="asset_ops",
            denial_error_factory=AssetOperationsPermissionDeniedError,
        )
    ),
]
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=100,
        pattern=r".*\S.*",
    ),
]


@router.post("/imports/templates/update")
async def export_update_base(
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz: AssetOpsRead,
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> Response:
    scope = await party_scope_resolver.resolve(db, user_id=str(current_user.id))
    content = await import_batch_service.build_update_base(db, scope=scope)
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": 'attachment; filename="import-update-base.xlsx"'
        },
    )


@router.get("/imports/templates/create")
async def download_create_template(
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz: AssetOpsRead,
) -> Response:
    content = build_template_workbook()
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": 'attachment; filename="import-template.xlsx"'},
    )


@router.post(
    "/import-batches/scan-staging",
    response_model=ImportStagingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_scan_staging(
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz: AssetOpsWrite,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    files: list[UploadFile] = File(...),
) -> ImportStagingResponse:
    staged = await import_batch_service.stage_scan_files(
        db, actor_id=str(current_user.id), uploads=list(files)
    )
    return ImportStagingResponse(
        files=[ImportStagedFile.model_validate(f) for f in staged]
    )


@router.get(
    "/import-batches/scan-staging",
    response_model=ImportStagingResponse,
)
async def list_scan_staging(
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz: AssetOpsRead,
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> ImportStagingResponse:
    owner_id = staging_owner_id(str(current_user.id))
    rows = (
        (
            await db.execute(
                select(Attachment)
                .where(
                    Attachment.owner_type == "contract",
                    Attachment.owner_id == owner_id,
                )
                .order_by(Attachment.created_at)
            )
        )
        .scalars()
        .all()
    )
    return ImportStagingResponse(
        files=[
            ImportStagedFile(
                id=row.id, file_name=row.file_name, file_size=row.file_size
            )
            for row in rows
        ]
    )


@router.post(
    "/import-batches",
    response_model=ImportBatchStatusResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_import_batch(
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz: AssetOpsWrite,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _idempotency: IdempotencyKey,
    mode: str = Form(..., pattern="^(create|update)$"),
    file: UploadFile = File(...),
) -> ImportBatchStatusResponse:
    content = await file.read()
    scope = await party_scope_resolver.resolve(db, user_id=str(current_user.id))
    batch = await import_batch_service.upload_batch(
        db,
        actor_id=str(current_user.id),
        scope=scope,
        mode=mode,
        filename=file.filename or "import.xlsx",
        content=content,
    )
    return ImportBatchStatusResponse.model_validate(batch)


@router.get(
    "/import-batches",
    response_model=ImportBatchListResponse,
    summary="查询导入批次列表",
)
async def list_import_batches(
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz: AssetOpsRead,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> ImportBatchListResponse:
    """The actor's recent batches (create & update modes mixed)."""
    from ...crud.import_batch import import_batch_repository

    batches, total = await import_batch_repository.list_batches(
        db, created_by=str(current_user.id), offset=offset, limit=limit
    )
    return ImportBatchListResponse(
        items=[ImportBatchStatusResponse.model_validate(row) for row in batches],
        total=total,
    )


@router.get(
    "/import-batches/{batch_id}",
    response_model=ImportBatchStatusResponse,
)
async def get_import_batch(
    batch_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz: AssetOpsRead,
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> ImportBatchStatusResponse:
    batch = await import_batch_service.get_batch(
        db, actor_id=str(current_user.id), batch_id=batch_id
    )
    return ImportBatchStatusResponse.model_validate(batch)


@router.get(
    "/import-batches/{batch_id}/changes",
    response_model=ImportBatchChangePage,
)
async def list_import_changes(
    batch_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz: AssetOpsRead,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    severity: str | None = Query(None, pattern="^(change|warning|error)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> ImportBatchChangePage:
    await import_batch_service.get_batch(
        db, actor_id=str(current_user.id), batch_id=batch_id
    )
    from ...crud.import_batch import import_batch_repository

    changes, total = await import_batch_repository.list_changes(
        db, batch_id=batch_id, severity=severity, offset=offset, limit=limit
    )
    return ImportBatchChangePage(
        items=[ImportBatchChangeResponse.model_validate(c) for c in changes],
        total=total,
    )


@router.put(
    "/import-batches/{batch_id}/selection",
    response_model=ImportBatchStatusResponse,
)
async def update_import_selection(
    batch_id: str,
    request: ImportSelectionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz: AssetOpsWrite,
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> ImportBatchStatusResponse:
    batch = await import_batch_service.update_selection(
        db,
        actor_id=str(current_user.id),
        batch_id=batch_id,
        selections=request.selections,
    )
    return ImportBatchStatusResponse.model_validate(batch)


@router.post(
    "/import-batches/{batch_id}/commit-preview",
    response_model=ImportCommitPreviewResponse,
)
async def import_commit_preview(
    batch_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz: AssetOpsWrite,
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> ImportCommitPreviewResponse:
    result = await import_batch_service.commit_preview(
        db, actor_id=str(current_user.id), batch_id=batch_id
    )
    return ImportCommitPreviewResponse.model_validate(result)


@router.post(
    "/import-batches/{batch_id}/commit",
    response_model=ImportCommitResponse,
)
async def import_commit(
    batch_id: str,
    request: ImportCommitRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz: AssetOpsWrite,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _idempotency: IdempotencyKey,
) -> ImportCommitResponse:
    scope = await party_scope_resolver.resolve(db, user_id=str(current_user.id))
    result = await import_batch_service.commit(
        db,
        actor_id=str(current_user.id),
        scope=scope,
        batch_id=batch_id,
        token=request.commit_token,
        expected_version=request.expected_version,
        proposal_hash=request.proposal_hash,
        idempotency_key=_idempotency,
    )
    return ImportCommitResponse.model_validate(result)


@router.post(
    "/import-batches/{batch_id}/revert-preview",
    response_model=ImportRevertPreviewResponse,
)
async def import_revert_preview(
    batch_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz: AssetOpsWrite,
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> ImportRevertPreviewResponse:
    result = await import_batch_service.revert_preview(
        db, actor_id=str(current_user.id), batch_id=batch_id
    )
    return ImportRevertPreviewResponse.model_validate(result)


@router.post(
    "/import-batches/{batch_id}/revert",
    response_model=ImportRevertResponse,
)
async def import_revert(
    batch_id: str,
    request: ImportRevertRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz: AssetOpsWrite,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _idempotency: IdempotencyKey,
) -> ImportRevertResponse:
    scope = await party_scope_resolver.resolve(db, user_id=str(current_user.id))
    result = await import_batch_service.revert(
        db,
        actor_id=str(current_user.id),
        scope=scope,
        batch_id=batch_id,
        token=request.revert_token,
        reason=request.reason,
        idempotency_key=_idempotency,
    )
    return ImportRevertResponse.model_validate(result)


route_registry.register_router(
    router, prefix="/api/v1", tags=["资产运营"], version="v1"
)
