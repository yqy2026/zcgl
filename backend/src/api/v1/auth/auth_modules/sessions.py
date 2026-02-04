"""
会话管理API路由

包含: 会话查询、会话撤销
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .....core.exception_handler import internal_error, not_found
from .....crud.auth import UserSessionCRUD
from .....database import get_async_db
from .....middleware.auth import get_current_active_user
from .....schemas.auth import UserResponse, UserSessionResponse
from .....services.core.session_service import AsyncSessionService

router = APIRouter(prefix="/sessions", tags=["会话管理"])


@router.get("", response_model=list[UserSessionResponse], summary="获取用户会话列表")
async def get_user_sessions(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(get_current_active_user),
) -> list[UserSessionResponse]:
    """获取当前用户的所有会话"""
    session_crud = UserSessionCRUD()
    sessions = await session_crud.get_user_sessions_async(db, current_user.id)
    return [UserSessionResponse.model_validate(session) for session in sessions]


@router.delete("/{session_id}", summary="撤销会话")
async def revoke_session(
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(get_current_active_user),
) -> dict[str, str]:
    """撤销指定会话"""
    session_service = AsyncSessionService(db)
    session_crud = UserSessionCRUD()

    session = await session_crud.get_async(db, session_id)
    if not session or str(session.user_id) != str(current_user.id):
        raise not_found("会话不存在", resource_type="session", resource_id=session_id)

    refresh_token = getattr(session, "refresh_token", None)
    if not refresh_token:
        raise internal_error("撤销会话失败")

    success = await session_service.revoke_session(refresh_token)
    if success:
        return {"message": "会话已撤销"}
    raise internal_error("撤销会话失败")
