from __future__ import annotations

from ...core.exception_handler import forbidden
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.auth import User
from ...models.task import AsyncTask
from ...services.permission.rbac_service import RBACService


async def ensure_task_access(
    task: AsyncTask, current_user: User, db: AsyncSession
) -> None:
    rbac_service = RBACService(db)
    if await rbac_service.is_admin(current_user.id):
        return
    task_user_id = getattr(task, "user_id", None)
    if not task_user_id or task_user_id != current_user.id:
        raise forbidden("无权访问该任务")


async def resolve_task_user_filter(
    requested_user_id: str | None, current_user: User, db: AsyncSession
) -> str | None:
    rbac_service = RBACService(db)
    if await rbac_service.is_admin(current_user.id):
        return requested_user_id
    if requested_user_id and requested_user_id != current_user.id:
        raise forbidden("无权访问其他用户任务")
    return current_user.id
