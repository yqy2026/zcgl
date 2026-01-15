"""
认证相关API路由 - 认证端点

包含: 登录、登出、刷新令牌、获取当前用户信息
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ....core.route_guards import debug_only
from ....crud.auth import AuditLogCRUD, UserCRUD
from ....database import get_db
from ....exceptions import BusinessLogicError
from ....middleware.auth import (
    ALGORITHM,
    SECRET_KEY,
    get_current_active_user,
)
from ....schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
)
from ....services import AuthService

router = APIRouter(tags=["认证管理"])


@router.post("/login", summary="用户登录")
async def login(
    request: Request, credentials: LoginRequest, db: Session = Depends(get_db)
) -> dict[str, Any]:
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
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    try:
        # 认证用户（启用真实认证流程）
        user = auth_service.authenticate_user(  # type: ignore[no-untyped-call]
            credentials.username, credentials.password
        )
        if not user:
            # 记录失败登录
            existing_user = user_crud.get_by_username(db, credentials.username)
            if existing_user:
                audit_crud.create(
                    db=db,
                    user_id=str(existing_user.id) if existing_user else "unknown",
                    action="user_login_failed",
                    resource_type="authentication",
                    ip_address=client_ip,
                    user_agent=user_agent,
                )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
            )

        # 创建令牌（增强安全性）
        device_info: dict[str, str] = {
            "user_agent": user_agent,
            "ip_address": client_ip,
        }
        tokens = auth_service.create_tokens(user, device_info)  # type: ignore[no-untyped-call]

        # 创建会话
        auth_service.create_user_session(  # type: ignore[no-untyped-call]
            user_id=str(user.id),
            refresh_token=tokens.refresh_token,
            ip_address=client_ip,
            user_agent=user_agent,
            session_id=getattr(tokens, "session_id", None),
        )

        # 记录成功登录
        audit_crud.create(
            db=db,
            user_id=str(user.id),
            action="user_login",
            resource_type="authentication",
            api_endpoint="/api/auth/login",
            http_method="POST",
            response_status=200,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Return simple response instead of LoginResponse to avoid validation issues
        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": bool(user.is_active)
                if hasattr(user.is_active, "__int__")
                else user.is_active,
            },
            "tokens": {
                "access_token": tokens.access_token,
                "refresh_token": tokens.refresh_token,
                "token_type": tokens.token_type,
                "expires_in": tokens.expires_in,
            },
            "message": "登录成功",
        }

    except HTTPException:
        raise
    except Exception as e:
        # Log the error for debugging (internal use only)
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Authentication error: {str(e)}", exc_info=True)

        # Return generic error message to client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录服务暂时不可用，请稍后重试",
        )

    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/logout", summary="用户登出")
async def logout(
    request: Request,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    用户登出接口

    - 撤销当前会话
    - 将当前JWT令牌加入黑名单
    - 清除客户端令牌
    - 记录登出审计日志
    """
    auth_service = AuthService(db)
    audit_crud = AuditLogCRUD()

    # 获取客户端信息
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # 提取并黑名单当前JWT令牌
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            # 解码JWT获取jti和exp
            payload = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                audience="land-property-system",
                issuer="land-property-auth",
                options={"verify_exp": False},  # 允许解码已过期的令牌
            )
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                from ....core.token_blacklist import blacklist_manager

                blacklist_manager.add_token(jti, exp)
        except Exception as e:
            # 记录错误但继续登出流程
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to blacklist token during logout: {e}")

    # 撤销用户所有会话
    revoked_count = auth_service.revoke_all_user_sessions(current_user.id)  # type: ignore[no-untyped-call]

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
    request: Request, refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    """
    刷新访问令牌接口

    - 使用刷新令牌获取新的访问令牌
    - 自动延长会话有效期
    - 增强安全性：记录刷新操作、检查IP变化等
    """
    auth_service = AuthService(db)

    # 获取客户端信息
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # 验证刷新令牌（增强安全性）
    session = auth_service.validate_refresh_token(  # type: ignore[no-untyped-call]
        refresh_data.refresh_token, client_ip=client_ip, user_agent=user_agent
    )
    if not session:
        # 记录失败的刷新尝试
        from ....crud.auth import AuditLogCRUD

        audit_crud = AuditLogCRUD()
        audit_crud.create(
            db=db,
            user_id="unknown",  # 无法确定用户
            action="token_refresh_failed",
            resource_type="authentication",
            api_endpoint="/api/v1/auth/refresh",
            http_method="POST",
            response_status=401,
            response_message="无效的刷新令牌",
            ip_address=client_ip,
            user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌"
        )

    # 获取用户
    user = auth_service.get_user_by_id(str(session.user_id))  # type: ignore[no-untyped-call]
    user_active = getattr(user, "is_active", False) if user else False
    if not user or not user_active:
        # 撤销无效会话
        auth_service.revoke_session(refresh_data.refresh_token)  # type: ignore[no-untyped-call]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已被禁用"
        )

    # 检查IP变化（可选安全检查）
    session_ip = (
        str(getattr(session, "ip_address", ""))
        if getattr(session, "ip_address", "")
        else None
    )
    if session_ip and session_ip != client_ip:
        # 可以选择拒绝IP变化的请求，或记录警告
        user_id = getattr(user, "id", None)
        logger.warning(
            "IP address changed for user during session refresh",
            extra={"user_id": user_id},
            exc_info=False,
        )

    # 创建新令牌（增强安全性）
    device_info: dict[str, str | None] = {
        "user_agent": user_agent,
        "ip_address": client_ip,
        "device_id": getattr(session, "device_id", None),
        "platform": getattr(session, "platform", None),
    }
    tokens = auth_service.create_tokens(user, device_info)  # type: ignore[no-untyped-call]

    # 更新会话
    setattr(session, "refresh_token", tokens.refresh_token)
    setattr(session, "last_accessed_at", datetime.now())
    setattr(session, "ip_address", client_ip)  # 更新IP地址
    setattr(session, "user_agent", user_agent)  # 更新User-Agent
    # 更新会话ID（如果存在）
    if tokens.session_id:
        setattr(session, "session_id", tokens.session_id)
    db.commit()

    # 记录成功的刷新操作
    from ....crud.auth import AuditLogCRUD

    audit_crud = AuditLogCRUD()
    audit_crud.create(
        db=db,
        user_id=str(getattr(user, "id", "unknown")),
        action="token_refresh_success",
        resource_type="authentication",
        api_endpoint="/api/v1/auth/refresh",
        http_method="POST",
        response_status=200,
        response_message="令牌刷新成功",
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return tokens  # type: ignore[no-any-return]


@router.get("/me", response_model=dict[str, Any], summary="获取当前用户信息")
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_active_user),
) -> dict[str, Any]:
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


# ==================== Debug Endpoints ====================
# Note: Consider removing debug endpoints from production code


@router.get("/test-enhanced", summary="测试增强端点")
@debug_only
async def test_enhanced() -> dict[str, Any]:
    """测试端点，验证增强功能"""
    return {
        "success": True,
        "message": "增强功能测试正常",
        "timestamp": "2025-10-29T01:26:00Z",
    }


@router.get("/debug-auth", summary="调试认证流程")
@debug_only
async def debug_auth(db: Session = Depends(get_db)) -> dict[str, Any]:
    """调试认证流程，测试各个步骤"""
    try:
        auth_service = AuthService(db)

        # 1. 测试用户查询
        admin_user = auth_service.get_user_by_username("admin")  # type: ignore[no-untyped-call]
        if not admin_user:
            return {"error": "Admin user not found"}

        # 2. 测试密码验证
        password_valid = auth_service.verify_password(  # type: ignore[no-untyped-call]
            "Admin123!@#", admin_user.password_hash
        )

        # 3. 测试用户认证
        auth_error_debug: str | None = None
        try:
            authenticated_user = auth_service.authenticate_user("admin", "Admin123!@#")  # type: ignore[no-untyped-call]
            auth_success = authenticated_user is not None
        except Exception as auth_exc:
            auth_success = False
            auth_error_debug = str(auth_exc)

        # 4. 测试token创建
        try:
            if authenticated_user:
                tokens = auth_service.create_tokens(authenticated_user)  # type: ignore[no-untyped-call]
                token_success = True
                access_token_length = (
                    len(tokens.access_token) if tokens.access_token else 0
                )
            else:
                token_success = False
                access_token_length = 0
        except Exception as e:
            token_success = False
            access_token_length = 0
            token_error: str | None = str(e)
        else:
            token_error = None

        return {
            "admin_user_found": admin_user is not None,
            "admin_username": admin_user.username if admin_user else None,
            "admin_role": admin_user.role if admin_user else None,
            "password_valid": password_valid,
            "auth_success": auth_success,
            "auth_error": auth_error_debug,
            "token_success": token_success,
            "token_error": token_error,
            "access_token_length": access_token_length,
        }

    except Exception as e:
        return {"error": f"Debug endpoint error: {str(e)}"}


@router.get("/test-me-debug", summary="调试ME端点")
@debug_only
async def test_me_debug(
    current_user: UserResponse = Depends(get_current_active_user),
) -> dict[str, Any]:
    """调试ME端点，检查UserResponse内容"""
    from datetime import datetime

    # 检查 UserResponse 的所有字段
    user_dict = current_user.model_dump()
    logger.debug(f"UserResponse fields: {len(user_dict.keys())} fields")

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
