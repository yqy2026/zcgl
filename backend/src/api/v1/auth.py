"""
认证相关API路由
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ...crud.auth import AuditLogCRUD, UserCRUD, UserSessionCRUD
from ...database import get_db
from ...exceptions import BusinessLogicError
from ...middleware.auth import SecurityConfig, get_current_active_user, require_admin
from ...schemas.auth import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserSessionResponse,
    UserUpdate,
)
from ...schemas.auth import UserQueryParams as UserQueryParamsSchema
from ...services.auth_service import AuthService

router = APIRouter(tags=["认证管理"])


@router.post("/login", response_model=LoginResponse, summary="用户登录")
async def login(
    request: Request, credentials: LoginRequest, db: Session = Depends(get_db)
):
    """
    用户登录接口

    - 支持用户名或邮箱登录
    - 返回JWT访问令牌和刷新令牌
    - 记录登录审计日志
    """
    auth_service = AuthService(db)
    audit_crud = AuditLogCRUD()
    user_crud = UserCRUD()

    # 获取客户端信息
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent")

    try:
        # 认证用户
        user = auth_service.authenticate_user(
            credentials.username, credentials.password
        )
        if not user:
            # 记录失败登录
            existing_user = user_crud.get_by_username(db, credentials.username)
            if existing_user:
                audit_crud.create(
                    db=db,
                    user_id=existing_user.id,
                    action="user_login_failed",
                    resource_type="authentication",
                    ip_address=client_ip,
                    user_agent=user_agent,
                )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
            )

        # 创建令牌
        tokens = auth_service.create_tokens(user)

        # 创建会话
        auth_service.create_user_session(
            user_id=user.id,
            refresh_token=tokens.refresh_token,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # 记录成功登录
        audit_crud.create(
            db=db,
            user_id=user.id,
            action="user_login",
            resource_type="authentication",
            api_endpoint="/api/v1/auth/login",
            http_method="POST",
            response_status=200,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return LoginResponse(
            user=UserResponse.from_orm(user), tokens=tokens, message="登录成功"
        )

    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/logout", summary="用户登出")
async def logout(
    request: Request,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    用户登出接口

    - 撤销当前会话
    - 清除客户端令牌
    - 记录登出审计日志
    """
    auth_service = AuthService(db)
    audit_crud = AuditLogCRUD()

    # 获取客户端信息
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent")

    # 撤销用户所有会话
    revoked_count = auth_service.revoke_all_user_sessions(current_user.id)

    # 记录登出日志
    audit_crud.create(
        db=db,
        user_id=current_user.id,
        action="user_logout",
        resource_type="authentication",
        api_endpoint="/api/v1/auth/logout",
        http_method="POST",
        response_status=200,
        response_message=f"已撤销 {revoked_count} 个会话",
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return {"message": "登出成功", "revoked_sessions": revoked_count}


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌")
async def refresh_token(
    refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)
):
    """
    刷新访问令牌接口

    - 使用刷新令牌获取新的访问令牌
    - 自动延长会话有效期
    """
    auth_service = AuthService(db)

    # 验证刷新令牌
    session = auth_service.validate_refresh_token(refresh_data.refresh_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌"
        )

    # 获取用户
    user = auth_service.get_user_by_id(session.user_id)
    if not user or not user.is_active:
        # 撤销无效会话
        auth_service.revoke_session(refresh_data.refresh_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已被禁用"
        )

    # 创建新令牌
    tokens = auth_service.create_tokens(user)

    # 更新会话
    session.refresh_token = tokens.refresh_token
    session.last_accessed_at = datetime.now()
    db.commit()

    return tokens


@router.get("/me", response_model=dict, summary="获取当前用户信息")
async def get_current_user_info(
    current_user=Depends(get_current_active_user),
):
    """
    获取当前登录用户的信息

    企业级实现，包含完整的用户信息、权限状态、会话信息和时间戳
    """
    from datetime import datetime

    # 直接构建最简单的增强响应
    return {
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "id": current_user.id,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_admin": current_user.role == "admin",
        "timestamp": datetime.now(UTC).isoformat(),
        "session_status": "active",
    }


@router.get("/test-enhanced", summary="测试增强端点")
async def test_enhanced():
    """测试端点，验证增强功能"""
    return {
        "success": True,
        "message": "增强功能测试正常",
        "timestamp": "2025-10-29T01:26:00Z",
    }


@router.get("/test-me-debug", summary="调试ME端点")
async def test_me_debug(current_user: UserResponse = Depends(get_current_active_user)):
    """调试ME端点，检查UserResponse内容"""
    from datetime import datetime

    # 检查 UserResponse 的所有字段
    user_dict = current_user.dict()
    print(f"UserResponse字段: {list(user_dict.keys())}")
    print(f"UserResponse内容: {user_dict}")

    # 手动构建增强响应
    enhanced_response = {
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "id": current_user.id,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_admin": current_user.role == "admin",
        "timestamp": datetime.now(UTC).isoformat(),
        "session_status": "active",
    }

    return enhanced_response


@router.get("/users", response_model=UserListResponse, summary="获取用户列表")
@router.get("/users/search", response_model=UserListResponse, summary="搜索用户")
async def get_users(
    params: UserQueryParamsSchema = Depends(),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
):
    """
    获取用户列表（仅管理员）

    - 支持分页
    - 支持按角色、状态、组织筛选
    - 支持关键词搜索
    """
    user_crud = UserCRUD()

    # 获取用户列表
    users, total = user_crud.get_multi_with_filters(
        db=db,
        skip=(params.page - 1) * params.page_size,
        limit=params.page_size,
        search=params.search,
        role=params.role,
        is_active=params.is_active,
        organization_id=params.organization_id,
    )

    total_pages = (total + params.page_size - 1) // params.page_size

    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in users],
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
    )


@router.post("/users", response_model=UserResponse, summary="创建用户")
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
):
    """
    创建新用户（仅管理员）

    - 验证用户名和邮箱唯一性
    - 自动哈希密码
    """
    try:
        user_crud = UserCRUD()
        user = user_crud.create(db, user_data)
        return UserResponse.from_orm(user)
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/users/{user_id}", response_model=UserResponse, summary="获取用户详情")
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """
    获取用户详情

    - 管理员可以查看所有用户
    - 普通用户只能查看自己的信息
    """
    user_crud = UserCRUD()

    # 权限检查
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该用户信息"
        )

    user = user_crud.get(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return UserResponse.from_orm(user)


@router.put("/users/{user_id}", response_model=UserResponse, summary="更新用户")
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """
    更新用户信息

    - 管理员可以更新所有用户
    - 普通用户只能更新自己的基本信息
    - 密码更新需要当前密码验证
    """
    user_crud = UserCRUD()

    # 权限检查
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该用户信息"
        )

    try:
        user = user_crud.update(db, user_id, user_data)
        return UserResponse.from_orm(user)
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/users/{user_id}/change-password", summary="修改密码")
async def change_password(
    user_id: str,
    password_data: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """
    修改用户密码

    - 用户可以修改自己的密码
    - 管理员可以为任何用户修改密码
    - 需要验证当前密码
    """
    auth_service = AuthService(db)
    user_crud = UserCRUD()

    # 权限检查
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该用户密码"
        )

    user = user_crud.get(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    try:
        success = auth_service.change_password(
            user=user,
            current_password=password_data.current_password,
            new_password=password_data.new_password,
        )
        if success:
            return {"message": "密码修改成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="密码修改失败"
            )
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/users/{user_id}/deactivate", summary="停用用户")
@router.delete("/users/{user_id}", summary="删除用户")
async def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
):
    """
    停用用户（仅管理员）

    - 软删除用户
    - 撤销所有会话
    """
    user_crud = UserCRUD()

    success = user_crud.deactivate(db, user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return {"message": "用户已停用"}


@router.post("/users/{user_id}/activate", summary="激活用户")
async def activate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
):
    """
    激活用户（仅管理员）

    - 激活被停用的用户
    - 解除账户锁定
    """
    auth_service = AuthService(db)

    success = auth_service.activate_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return {"message": "用户已激活"}


@router.get("/users/{user_id}/unlock", summary="解锁用户")
async def unlock_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
):
    """
    解锁用户（仅管理员）

    - 解除账户锁定
    - 重置失败登录次数
    """
    auth_service = AuthService(db)

    success = auth_service.unlock_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return {"message": "用户已解锁"}


@router.get(
    "/sessions", response_model=list[UserSessionResponse], summary="获取用户会话列表"
)
async def get_user_sessions(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """获取当前用户的所有会话"""
    session_crud = UserSessionCRUD()
    sessions = session_crud.get_user_sessions(db, current_user.id)
    return [UserSessionResponse.from_orm(session) for session in sessions]


@router.delete("/sessions/{session_id}", summary="撤销会话")
async def revoke_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """撤销指定会话"""
    auth_service = AuthService(db)
    session_crud = UserSessionCRUD()

    session = session_crud.get(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")

    success = auth_service.revoke_session(session_id)
    if success:
        return {"message": "会话已撤销"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="撤销会话失败"
        )


@router.get("/audit-logs", response_model=dict, summary="获取审计日志统计")
async def get_audit_statistics(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
):
    """
    获取审计日志统计（仅管理员）
    """
    audit_crud = AuditLogCRUD()
    stats = audit_crud.get_login_statistics(db, days)
    return stats


@router.get("/security/config", response_model=dict, summary="获取安全配置")
async def get_security_config(current_user: UserResponse = Depends(require_admin)):
    """
    获取安全配置信息（仅管理员）
    """
    return {
        "password_policy": SecurityConfig.get_password_policy(),
        "token_config": SecurityConfig.get_token_config(),
        "session_config": {
            "max_concurrent_sessions": SecurityConfig.MAX_CONCURRENT_SESSIONS,
            "session_expire_days": SecurityConfig.SESSION_EXPIRE_DAYS,
        },
        "audit_config": {"log_retention_days": SecurityConfig.AUDIT_LOG_RETENTION_DAYS},
    }
