"""审批域 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_async_db
from ...models.auth import User
from ...schemas.approval import ApprovalProcessStartRequest, ApprovalTaskActionRequest
from ...security.permissions import (
    require_approval_approve,
    require_approval_read,
    require_approval_reject,
    require_approval_start,
    require_approval_withdraw,
)
from ...services.approval import ApprovalService

router = APIRouter(tags=["审批流"])


@router.post("/processes/start", summary="发起审批")
async def start_approval_process(
    payload: ApprovalProcessStartRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_approval_start()),
) -> object:
    service = ApprovalService(db)
    return await service.start_process(
        business_type=payload.business_type,
        business_id=payload.business_id,
        assignee_user_id=payload.assignee_user_id,
        starter_id=str(current_user.id),
        comment=payload.comment,
    )


@router.get("/tasks/pending", summary="查询当前用户待办")
async def list_pending_approval_tasks(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_approval_read()),
) -> object:
    service = ApprovalService(db)
    return await service.list_pending_tasks(assignee_user_id=str(current_user.id))


@router.get("/processes/mine", summary="查询我发起的审批")
async def list_my_approval_processes(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_approval_read()),
) -> object:
    service = ApprovalService(db)
    return await service.list_started_processes(starter_id=str(current_user.id))


@router.get(
    "/processes/{approval_instance_id}/timeline",
    summary="查询审批时间线",
)
async def get_approval_process_timeline(
    approval_instance_id: str = Path(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_approval_read()),
) -> object:
    service = ApprovalService(db)
    return await service.get_process_timeline(
        approval_instance_id=approval_instance_id,
        current_user_id=str(current_user.id),
    )


@router.post("/tasks/{task_id}/approve", summary="审批通过")
async def approve_approval_task(
    task_id: str,
    payload: ApprovalTaskActionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_approval_approve()),
) -> object:
    service = ApprovalService(db)
    return await service.approve_task(
        task_id=task_id,
        operator_id=str(current_user.id),
        comment=payload.comment,
    )


@router.post("/tasks/{task_id}/reject", summary="审批驳回")
async def reject_approval_task(
    task_id: str,
    payload: ApprovalTaskActionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_approval_reject()),
) -> object:
    service = ApprovalService(db)
    return await service.reject_task(
        task_id=task_id,
        operator_id=str(current_user.id),
        comment=payload.comment,
    )


@router.post("/tasks/{task_id}/withdraw", summary="审批撤回")
async def withdraw_approval_task(
    task_id: str,
    payload: ApprovalTaskActionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_approval_withdraw()),
) -> object:
    service = ApprovalService(db)
    return await service.withdraw_task(
        task_id=task_id,
        operator_id=str(current_user.id),
        comment=payload.comment,
    )
