from __future__ import annotations

from ...core.exception_handler import forbidden
from ...models.auth import User
from ...models.task import AsyncTask
from ...security.roles import RoleNormalizer


def ensure_task_access(task: AsyncTask, current_user: User) -> None:
    if RoleNormalizer.is_admin(str(current_user.role)):
        return
    task_user_id = getattr(task, "user_id", None)
    if not task_user_id or task_user_id != current_user.id:
        raise forbidden("无权访问该任务")


def resolve_task_user_filter(
    requested_user_id: str | None, current_user: User
) -> str | None:
    if RoleNormalizer.is_admin(str(current_user.role)):
        return requested_user_id
    if requested_user_id and requested_user_id != current_user.id:
        raise forbidden("无权访问其他用户任务")
    return current_user.id
