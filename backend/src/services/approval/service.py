"""审批域服务。"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    ResourceNotFoundError,
    conflict,
    forbidden,
    operation_not_allowed,
    validation_error,
)
from ...crud.approval import approval_crud
from ...models.approval import ApprovalActionLog, ApprovalInstance, ApprovalTaskSnapshot
from ...models.notification import NotificationPriority
from ...services.asset.asset_service import AssetService
from ...services.notification.notification_service import (
    NotificationService,
    notification_service,
)

_APPROVAL_BUSINESS_ASSET = "asset"
_APPROVAL_STATUS_PENDING = "pending"
_APPROVAL_STATUS_APPROVED = "approved"
_APPROVAL_STATUS_REJECTED = "rejected"
_APPROVAL_STATUS_WITHDRAWN = "withdrawn"
_TASK_STATUS_PENDING = "pending"
_TASK_STATUS_COMPLETED = "completed"
_TASK_STATUS_CANCELLED = "cancelled"


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ApprovalService:
    """审批服务。"""

    def __init__(
        self,
        db: AsyncSession,
        *,
        asset_service: AssetService | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.db = db
        self.asset_service = asset_service or AssetService(db)
        self.notification_service = notification_service or notification_service_global

    @asynccontextmanager
    async def _transaction(self) -> Any:
        if self.db.in_transaction():
            try:
                yield
                await self.db.commit()
            except Exception:
                await self.db.rollback()
                raise
        else:
            async with self.db.begin():
                yield

    def _generate_approval_no(self) -> str:
        return f"APR-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    @staticmethod
    def _ensure_supported_business_type(business_type: str) -> None:
        if business_type != _APPROVAL_BUSINESS_ASSET:
            raise validation_error(
                "当前仅支持 asset 审批",
                field_errors={"business_type": "unsupported"},
            )

    @staticmethod
    def _ensure_task_pending(task: ApprovalTaskSnapshot) -> None:
        if task.status != _TASK_STATUS_PENDING:
            raise operation_not_allowed(
                "当前审批任务已处理，不能重复操作",
                reason="approval_task_not_pending",
            )

    @staticmethod
    def _ensure_non_empty_comment(action: str, comment: str | None) -> str:
        normalized = (comment or "").strip()
        if normalized == "":
            raise validation_error(
                f"{action}意见不能为空",
                field_errors={"comment": "required"},
            )
        return normalized

    async def _get_instance_or_raise(
        self, approval_instance_id: str
    ) -> ApprovalInstance:
        instance = await approval_crud.get_instance(
            self.db,
            approval_instance_id=approval_instance_id,
        )
        if instance is None:
            raise ResourceNotFoundError("ApprovalInstance", approval_instance_id)
        return instance

    async def _get_task_or_raise(self, task_id: str) -> ApprovalTaskSnapshot:
        task = await approval_crud.get_task(self.db, task_id=task_id)
        if task is None:
            raise ResourceNotFoundError("ApprovalTask", task_id)
        return task

    async def _append_action_log(
        self,
        *,
        approval_instance_id: str,
        approval_task_snapshot_id: str | None,
        action: str,
        operator_id: str,
        comment: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> ApprovalActionLog:
        log = ApprovalActionLog()
        log.id = str(uuid.uuid4())
        log.approval_instance_id = approval_instance_id
        log.approval_task_snapshot_id = approval_task_snapshot_id
        log.action = action
        log.operator_id = operator_id
        log.comment = comment
        log.context = context
        log.created_at = _utcnow_naive()
        self.db.add(log)
        await self.db.flush()
        return log

    async def start_process(
        self,
        *,
        business_type: str,
        business_id: str,
        assignee_user_id: str,
        starter_id: str,
        comment: str | None = None,
    ) -> ApprovalInstance:
        self._ensure_supported_business_type(business_type)
        normalized_comment = (comment or "").strip() or None

        async with self._transaction():
            active_instance = await approval_crud.find_active_instance(
                self.db,
                business_type=business_type,
                business_id=business_id,
            )
            if active_instance is not None:
                raise conflict(
                    "该业务对象已有进行中的审批", resource_type="ApprovalInstance"
                )

            await self.asset_service.get_asset(
                business_id,
                current_user_id=starter_id,
            )
            await self.asset_service.submit_asset_review(
                business_id,
                operator=starter_id,
            )

            now = _utcnow_naive()
            instance = ApprovalInstance()
            instance.id = str(uuid.uuid4())
            instance.approval_no = self._generate_approval_no()
            instance.business_type = business_type
            instance.business_id = business_id
            instance.status = _APPROVAL_STATUS_PENDING
            instance.starter_id = starter_id
            instance.assignee_user_id = assignee_user_id
            instance.current_task_id = None
            instance.started_at = now
            instance.ended_at = None
            self.db.add(instance)
            await self.db.flush()

            task = ApprovalTaskSnapshot()
            task.id = str(uuid.uuid4())
            task.approval_instance_id = instance.id
            task.business_type = business_type
            task.business_id = business_id
            task.task_name = "资产审批"
            task.assignee_user_id = assignee_user_id
            task.status = _TASK_STATUS_PENDING
            task.created_at = now
            task.completed_at = None
            self.db.add(task)
            await self.db.flush()

            instance.current_task_id = task.id
            self.db.add(instance)
            await self._append_action_log(
                approval_instance_id=instance.id,
                approval_task_snapshot_id=task.id,
                action="start",
                operator_id=starter_id,
                comment=normalized_comment,
            )
            await self.notification_service.create_approval_pending_notification(
                self.db,
                recipient_id=assignee_user_id,
                approval_instance_id=instance.id,
                business_type=business_type,
                business_id=business_id,
                starter_id=starter_id,
                priority=NotificationPriority.HIGH,
            )
            return instance

    async def list_pending_tasks(
        self, *, assignee_user_id: str
    ) -> list[ApprovalTaskSnapshot]:
        return await approval_crud.list_pending_tasks(
            self.db,
            assignee_user_id=assignee_user_id,
        )

    async def list_started_processes(
        self, *, starter_id: str
    ) -> list[ApprovalInstance]:
        return await approval_crud.list_started_processes(
            self.db, starter_id=starter_id
        )

    async def get_process_timeline(
        self,
        *,
        approval_instance_id: str,
        current_user_id: str,
    ) -> list[ApprovalActionLog]:
        instance = await self._get_instance_or_raise(approval_instance_id)
        if current_user_id not in {instance.starter_id, instance.assignee_user_id}:
            raise forbidden("仅流程发起人或处理人可查看时间线")
        return await approval_crud.list_action_logs(
            self.db,
            approval_instance_id=approval_instance_id,
        )

    async def approve_task(
        self,
        *,
        task_id: str,
        operator_id: str,
        comment: str | None = None,
    ) -> ApprovalInstance:
        async with self._transaction():
            task = await self._get_task_or_raise(task_id)
            self._ensure_task_pending(task)
            if task.assignee_user_id != operator_id:
                raise forbidden("仅当前处理人可审批")

            instance = await self._get_instance_or_raise(task.approval_instance_id)
            await self.asset_service.approve_asset_review(
                task.business_id,
                reviewer=operator_id,
            )

            now = _utcnow_naive()
            task.status = _TASK_STATUS_COMPLETED
            task.completed_at = now
            instance.status = _APPROVAL_STATUS_APPROVED
            instance.ended_at = now
            instance.current_task_id = None
            self.db.add(task)
            self.db.add(instance)
            await self._append_action_log(
                approval_instance_id=instance.id,
                approval_task_snapshot_id=task.id,
                action="approve",
                operator_id=operator_id,
                comment=(comment or "").strip() or None,
            )
            await self.notification_service.mark_approval_notifications_read(
                self.db,
                approval_instance_id=instance.id,
            )
            return instance

    async def reject_task(
        self,
        *,
        task_id: str,
        operator_id: str,
        comment: str | None = None,
    ) -> ApprovalInstance:
        normalized_comment = self._ensure_non_empty_comment("驳回", comment)

        async with self._transaction():
            task = await self._get_task_or_raise(task_id)
            self._ensure_task_pending(task)
            if task.assignee_user_id != operator_id:
                raise forbidden("仅当前处理人可驳回")

            instance = await self._get_instance_or_raise(task.approval_instance_id)
            await self.asset_service.reject_asset_review(
                task.business_id,
                reviewer=operator_id,
                reason=normalized_comment,
            )

            now = _utcnow_naive()
            task.status = _TASK_STATUS_COMPLETED
            task.completed_at = now
            instance.status = _APPROVAL_STATUS_REJECTED
            instance.ended_at = now
            instance.current_task_id = None
            self.db.add(task)
            self.db.add(instance)
            await self._append_action_log(
                approval_instance_id=instance.id,
                approval_task_snapshot_id=task.id,
                action="reject",
                operator_id=operator_id,
                comment=normalized_comment,
            )
            await self.notification_service.mark_approval_notifications_read(
                self.db,
                approval_instance_id=instance.id,
            )
            return instance

    async def withdraw_task(
        self,
        *,
        task_id: str,
        operator_id: str,
        comment: str | None = None,
    ) -> ApprovalInstance:
        async with self._transaction():
            task = await self._get_task_or_raise(task_id)
            self._ensure_task_pending(task)
            instance = await self._get_instance_or_raise(task.approval_instance_id)
            if instance.starter_id != operator_id:
                raise operation_not_allowed(
                    "仅发起人可撤回",
                    reason="approval_withdraw_forbidden",
                )

            await self.asset_service.withdraw_asset_review(
                task.business_id,
                operator=operator_id,
                reason=(comment or "").strip() or None,
            )

            now = _utcnow_naive()
            task.status = _TASK_STATUS_CANCELLED
            task.completed_at = now
            instance.status = _APPROVAL_STATUS_WITHDRAWN
            instance.ended_at = now
            instance.current_task_id = None
            self.db.add(task)
            self.db.add(instance)
            await self._append_action_log(
                approval_instance_id=instance.id,
                approval_task_snapshot_id=task.id,
                action="withdraw",
                operator_id=operator_id,
                comment=(comment or "").strip() or None,
            )
            await self.notification_service.mark_approval_notifications_read(
                self.db,
                approval_instance_id=instance.id,
            )
            return instance


notification_service_global = notification_service
