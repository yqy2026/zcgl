"""
会话管理API路由

包含: 会话查询、会话撤销
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ....core.api_errors import internal_error, not_found
from ....crud.auth import UserSessionCRUD
from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....schemas.auth import UserResponse, UserSessionResponse
from ....services import AuthService

router = APIRouter(prefix="/sessions", tags=["会话管理"])


@router.get("", response_model=list[UserSessionResponse], summary="获取用户会话列表")
async def get_user_sessions(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
) -> list[UserSessionResponse]:
    """获取当前用户的所有会话"""
    session_crud = UserSessionCRUD()
    sessions = session_crud.get_user_sessions(db, current_user.id)
    return [UserSessionResponse.model_validate(session) for session in sessions]


@router.delete("/{session_id}", summary="撤销会话")
async def revoke_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
) -> dict[str, str]:
    """撤销指定会话"""
    auth_service = AuthService(db)
    session_crud = UserSessionCRUD()

    # 获取会话记录
    session = session_crud.get(db, session_id)
    if not session or str(session.user_id) != str(current_user.id):
        raise not_found("会话不存在", resource_type="session", resource_id=session_id)

    # 使用refresh_token撤销会话（API修复：传递refresh_token而非session_id）
    success = auth_service.revoke_session(session.refresh_token)  # type: ignore[no-untyped-call]
    if success:
        return {"message": "会话已撤销"}
    else:
        raise internal_error("撤销会话失败")
