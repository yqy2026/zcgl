from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import forbidden
from ...models.auth import User
from ...models.task import AsyncTask
from ...services.permission.rbac_service import RBACService


async def ensure_task_access(
    task: AsyncTask, current_user: User, db: AsyncSession
) -> None:
    task_user_id = getattr(task, "user_id", None)
    if task_user_id and task_user_id == current_user.id:
        return

    rbac_service = RBACService(db)
    if await rbac_service.check_user_permission(current_user.id, "system", "admin"):
        return

    if not task_user_id:
        raise forbidden("无权访问该任务")
    if task_user_id != current_user.id:
        raise forbidden("无权访问该任务")


async def resolve_task_user_filter(
    requested_user_id: str | None, current_user: User, db: AsyncSession
) -> str | None:
    if requested_user_id is None or requested_user_id == current_user.id:
        return current_user.id

    rbac_service = RBACService(db)
    if await rbac_service.check_user_permission(current_user.id, "system", "admin"):
        return requested_user_id
    raise forbidden("无权访问其他用户任务")
