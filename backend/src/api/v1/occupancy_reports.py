"""Monthly occupancy-report endpoints for the reporting vertical."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import BaseBusinessError, internal_error
from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import AuthzContext, get_current_active_user, require_authz
from ...models.auth import User
from ...schemas.asset_operations import (
    OccupancyReportDraftResponse,
    OccupancyReportExportResponse,
    OccupancyReportNoteResponse,
    OccupancyReportSnapshotResponse,
    OccupancyReportSubmissionPreviewResponse,
    OccupancyReportSubmitResponse,
    OccupancyReportWithdrawalPreviewResponse,
    OccupancyReportWithdrawResponse,
    SaveOccupancyReportNoteRequest,
    SubmitOccupancyReportRequest,
    WithdrawOccupancyReportRequest,
)
from ...services.asset_operations import (
    AssetOperationsPermissionDeniedError,
    occupancy_report_draft_service,
    occupancy_report_submission_service,
)
from ...services.party_scope_resolver import party_scope_resolver

router = APIRouter(tags=["资产运营"])


@router.get(
    "/occupancy-reports/{period}/draft",
    response_model=OccupancyReportDraftResponse,
    summary="查询月度出租率报送草稿",
)
async def get_occupancy_report_draft(
    period: str,
    operator_party_id: Annotated[str, Query(min_length=1)],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="asset_ops",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> OccupancyReportDraftResponse:
    """Return real-time totals, lines, gates, baseline diff and scope version."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await occupancy_report_draft_service.get_draft(
            db,
            operator_party_id=operator_party_id,
            period=period,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询报送草稿失败", original_error=exc) from exc


@router.put(
    "/occupancy-reports/{period}/draft-note",
    response_model=OccupancyReportNoteResponse,
    summary="保存月度报送草稿变动说明",
)
async def save_occupancy_report_note(
    period: str,
    payload: SaveOccupancyReportNoteRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="report",
                resource_type="asset_ops",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> OccupancyReportNoteResponse:
    """Persist the draft change note without producing any snapshot."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await occupancy_report_draft_service.save_note(
            db,
            period=period,
            request=payload,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("保存报送草稿说明失败", original_error=exc) from exc


@router.post(
    "/occupancy-reports/{period}/submission-preview",
    response_model=OccupancyReportSubmissionPreviewResponse,
    summary="月度报送提交预览",
)
async def preview_occupancy_report_submission(
    period: str,
    operator_party_id: Annotated[str, Query(min_length=1)],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="report",
                resource_type="asset_ops",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> OccupancyReportSubmissionPreviewResponse:
    """Gate the submission on must-handle items and the change note."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await occupancy_report_submission_service.submission_preview(
            db,
            operator_party_id=operator_party_id,
            period=period,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("报送提交预览失败", original_error=exc) from exc


@router.post(
    "/occupancy-reports/{period}/submissions",
    response_model=OccupancyReportSubmitResponse,
    summary="提交月度出租率报送",
)
async def submit_occupancy_report(
    period: str,
    payload: SubmitOccupancyReportRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=100,
            pattern=r".*\S.*",
        ),
    ],
    operator_party_id: Annotated[str, Query(min_length=1)],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="report",
                resource_type="asset_ops",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> OccupancyReportSubmitResponse:
    """Atomically lock the snapshot, audit and receipt under one chain row."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await occupancy_report_submission_service.submit(
            db,
            operator_party_id=operator_party_id,
            period=period,
            request=payload,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key.strip(),
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("提交月度报送失败", original_error=exc) from exc


@router.get(
    "/occupancy-reports/{report_id}",
    response_model=OccupancyReportSnapshotResponse,
    summary="查询报送历史快照与台账差异",
)
async def get_occupancy_report_snapshot(
    report_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="asset_ops",
                resource_id="{report_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> OccupancyReportSnapshotResponse:
    """Read-only snapshot values, lines, scope version and live differences."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await occupancy_report_submission_service.get_snapshot(
            db,
            report_id=report_id,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询报送快照失败", original_error=exc) from exc


@router.post(
    "/occupancy-reports/{report_id}/withdrawal-preview",
    response_model=OccupancyReportWithdrawalPreviewResponse,
    summary="月度报送撤回预览",
)
async def preview_occupancy_report_withdrawal(
    report_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="report",
                resource_type="asset_ops",
                resource_id="{report_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> OccupancyReportWithdrawalPreviewResponse:
    """Describe the withdrawal impact and bind the withdrawal token."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await occupancy_report_submission_service.withdrawal_preview(
            db,
            report_id=report_id,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("报送撤回预览失败", original_error=exc) from exc


@router.post(
    "/occupancy-reports/{report_id}/withdrawal",
    response_model=OccupancyReportWithdrawResponse,
    summary="撤回月度报送",
)
async def withdraw_occupancy_report(
    report_id: str,
    payload: WithdrawOccupancyReportRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=100,
            pattern=r".*\S.*",
        ),
    ],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="report",
                resource_type="asset_ops",
                resource_id="{report_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> OccupancyReportWithdrawResponse:
    """Withdraw the snapshot; the original rows and audit trail remain."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await occupancy_report_submission_service.withdraw(
            db,
            report_id=report_id,
            request=payload,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key.strip(),
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("撤回月度报送失败", original_error=exc) from exc


@router.post(
    "/occupancy-reports/{report_id}/exports",
    response_model=OccupancyReportExportResponse,
    summary="发起报送快照导出任务",
)
async def export_occupancy_report(
    report_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="asset_ops",
                resource_id="{report_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> OccupancyReportExportResponse:
    """Queue an async CSV export over the immutable snapshot rows."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        service = occupancy_report_submission_service
        task_id = await service.create_export_task(
            db,
            report_id=report_id,
            actor_id=actor_id,
            scope=scope,
        )
        # Rendering happens in this request on the same session; no separate
        # worker process exists yet, so the queued task row is completed here
        # and the standard task endpoint serves the CSV payload.
        await service.render_export(db, task_id=task_id)
        return OccupancyReportExportResponse(
            task_id=task_id,
            report_id=report_id,
            status="completed",
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("发起报送导出失败", original_error=exc) from exc


route_registry.register_router(
    router,
    prefix="/api/v1",
    tags=["资产运营"],
    version="v1",
)


__all__ = ["router"]
