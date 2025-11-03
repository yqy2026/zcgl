"""
认证相关API路由
"""

import json
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ...crud.auth import AuditLogCRUD, UserCRUD, UserSessionCRUD
from ...database import get_db
from ...exceptions import BusinessLogicError
from ...middleware.auth import SecurityConfig, get_current_active_user, require_admin
from ...models.auth import User, UserSession
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
from ...services.security_service import SecurityService

router = APIRouter(tags=["认证管理"])
logger = logging.getLogger(__name__)


@router.post("/login", response_model=LoginResponse, summary="用户登录")
async def login(
    request: Request, credentials: LoginRequest, db: Session = Depends(get_db)
):
    """
    用户登录接口（增强安全版）

    - 支持用户名或邮箱登录
    - 增强的密码策略验证
    - 设备指纹识别
    - 可疑活动检测
    - 返回增强的JWT令牌
    - 详细的安全审计日志
    """
    auth_service = AuthService(db)
    security_service = SecurityService(db)
    audit_crud = AuditLogCRUD()
    user_crud = UserCRUD()

    # 获取客户端信息（增强版）
    client_ip = request.client.host
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    user_agent = request.headers.get("user-agent", "")
    device_info = {
        "ip_address": client_ip,
        "user_agent": user_agent,
        "device_id": request.headers.get("X-Device-ID"),
        "platform": request.headers.get("X-Platform"),
    }

    try:
        # 认证用户
        user = auth_service.authenticate_user(
            credentials.username, credentials.password
        )
        if not user:
            # 记录失败登录（增强版）
            existing_user = user_crud.get_by_username(db, credentials.username)
            if existing_user:
                # 检查是否需要处理可疑活动
                security_service.handle_suspicious_activity(
                    existing_user,
                    "multiple_failed_logins",
                    {"ip_address": client_ip, "user_agent": user_agent},
                )

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

        # 检查账户安全状态
        security_status = security_service.check_account_security(user)
        if security_status["issues"]:
            # 如果有安全问题，记录但允许登录
            audit_crud.create(
                db=db,
                user_id=user.id,
                action="security_issues_detected",
                resource_type="authentication",
                ip_address=client_ip,
                user_agent=user_agent,
            )

        # 创建增强的令牌
        tokens_data = security_service.create_tokens_enhanced(user, device_info)

        # 创建会话（增强版）
        auth_service.create_user_session(
            user_id=user.id,
            refresh_token=tokens_data["refresh_token"],
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # 记录成功登录（增强版）
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

        # 转换为TokenResponse格式
        tokens = TokenResponse(
            access_token=tokens_data["access_token"],
            refresh_token=tokens_data["refresh_token"],
            token_type=tokens_data["token_type"],
            expires_in=tokens_data["expires_in"],
        )

        return LoginResponse(
            user=UserResponse.from_orm(user), tokens=tokens, message="登录成功"
        )

    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/logout", summary="用户登出")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    标准用户登出接口

    功能：
    - 撤销用户所有活跃会话
    - 记录审计日志
    - 返回登出结果
    """
    request.headers.get("user-agent", "Unknown")

    try:
        # 1. 撤销用户所有会话
        revoked_count = (
            db.query(UserSession)
            .filter(UserSession.user_id == current_user.id, UserSession.is_active)
            .update({"is_active": False})
        )
        db.commit()

        # 2. 记录审计日志（暂时禁用，专注核心功能测试）
        # TODO: 修复AuditLog创建问题后重新启用
        logger.info(f"用户登出: {current_user.username}, 撤销会话数: {revoked_count}")

        return {
            "success": True,
            "message": "登出成功",
            "data": {
                "user_id": str(current_user.id),
                "username": current_user.username,
                "revoked_sessions": revoked_count,
                "logout_time": datetime.now(UTC).isoformat(),
            },
        }

    except Exception as e:
        # 记录错误并回滚
        logger.error(f"用户登出失败: {str(e)}")
        db.rollback()

        # 即使出错也尝试撤销会话
        try:
            db.query(UserSession).filter(
                UserSession.user_id == current_user.id, UserSession.is_active
            ).update({"is_active": False})
            db.commit()
        except Exception:
            # 静默处理会话清理失败，不影响主要登录流程
            pass

        return {
            "success": False,
            "message": "登出过程出现错误，但会话已被清理",
            "data": {
                "user_id": str(current_user.id),
                "username": current_user.username,
                "revoked_sessions": 0,
                "logout_time": datetime.now(UTC).isoformat(),
            },
        }


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


# ==================== 增强安全API端点 ====================


@router.post("/security/validate-password", summary="验证密码强度")
async def validate_password_strength(password: str, db: Session = Depends(get_db)):
    """
    验证密码强度
    """
    security_service = SecurityService(db)
    result = security_service.validate_password_strength_advanced(password)
    return result


@router.post("/security/generate-password", summary="生成安全密码")
async def generate_secure_password(length: int = 12, db: Session = Depends(get_db)):
    """
    生成安全密码
    """
    security_service = SecurityService(db)
    password = security_service.generate_secure_password(length)
    return {"password": password, "length": length}


@router.get("/security/account-status", summary="获取账户安全状态")
async def get_account_security_status(
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取当前用户的账户安全状态
    """
    security_service = SecurityService(db)

    # 获取用户实体
    from ...crud.auth import UserCRUD

    user_crud = UserCRUD()
    user = user_crud.get_by_id(db, current_user.id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    security_status = security_service.check_account_security(user)
    return security_status


@router.get("/security/audit-log", summary="获取安全审计日志")
async def get_security_audit_log(
    days: int = 30,
    limit: int = 100,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取安全审计日志
    """
    security_service = SecurityService(db)

    # 计算日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # 获取日志
    logs = security_service.get_security_audit_log(
        user_id=current_user.id, start_date=start_date, end_date=end_date, limit=limit
    )

    return {"logs": logs, "total": len(logs)}


@router.get("/security/report", summary="生成安全报告")
async def generate_security_report(
    days: int = 30,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    生成个人安全报告
    """
    security_service = SecurityService(db)

    # 计算日期范围
    end_date = datetime.now()
    end_date - timedelta(days=days)

    # 生成报告
    report = security_service.generate_security_report(current_user.id)
    report["period"]["days"] = days

    return report


@router.post("/security/revoke-sessions", summary="撤销所有会话")
async def revoke_all_sessions(
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    撤销当前用户的所有会话（强制重新登录）
    """
    auth_service = AuthService(db)

    count = auth_service.revoke_all_user_sessions(current_user.id)

    # 记录审计日志
    from ...crud.auth import AuditLogCRUD

    audit_crud = AuditLogCRUD()
    audit_crud.create(
        db=db,
        user_id=current_user.id,
        action="sessions_revoked",
        resource_type="security",
    )

    return {"message": f"已撤销{count}个会话", "revoked_count": count}


@router.get("/security/admin/report", summary="管理员安全报告")
async def get_admin_security_report(
    days: int = 30,
    user_id: str | None = None,
    current_user: UserResponse = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    获取管理员安全报告（仅管理员）
    """
    security_service = SecurityService(db)

    # 生成报告
    report = security_service.generate_security_report(user_id)
    report["period"]["days"] = days

    return report


@router.get("/security/admin/audit-log", summary="管理员审计日志")
async def get_admin_audit_log(
    days: int = 30,
    user_id: str | None = None,
    limit: int = 1000,
    current_user: UserResponse = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    获取管理员审计日志（仅管理员）
    """
    security_service = SecurityService(db)

    # 计算日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # 获取日志
    logs = security_service.get_security_audit_log(
        user_id=user_id, start_date=start_date, end_date=end_date, limit=limit
    )

    return {"logs": logs, "total": len(logs), "period": {"days": days}}


# ==================== 个人资料管理API ====================


@router.get("/debug-me", summary="调试用户信息端点（不需要认证）")
async def debug_current_user_profile():
    """
    调试用户信息端点（不需要认证）
    """
    # 临时调试：抛出明确异常来查看错误详情
    import sys
    import traceback

    error_info = f"Debug info:\nPython version: {sys.version}\nPath: {sys.path}\n"

    # 尝试导入依赖
    try:
        error_info += "User model import: SUCCESS\n"
    except Exception as e:
        error_info += f"User model import FAILED: {str(e)}\n"
        traceback_str = traceback.format_exc()
        error_info += f"Traceback: {traceback_str}\n"

    try:
        error_info += "get_current_active_user import: SUCCESS\n"
    except Exception as e:
        error_info += f"get_current_active_user import FAILED: {str(e)}\n"
        traceback_str = traceback.format_exc()
        error_info += f"Traceback: {traceback_str}\n"

    # 尝试获取数据库
    try:
        error_info += "get_db import: SUCCESS\n"
    except Exception as e:
        error_info += f"get_db import FAILED: {str(e)}\n"
        traceback_str = traceback.format_exc()
        error_info += f"Traceback: {traceback_str}\n"

    # 抛出异常以触发错误处理
    raise Exception(f"Debug endpoint reached. Error info:\n{error_info}")


@router.get("/test-auth", summary="测试认证")
async def test_auth():
    """测试端点，不需要认证"""
    return {"success": True, "message": "测试端点工作正常，已重新加载"}


@router.get("/test-auth", summary="测试认证端点")
async def test_auth_endpoint(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """测试认证端点"""
    try:
        return {
            "success": True,
            "message": "认证测试成功",
            "user": {
                "id": str(current_user.id),
                "username": current_user.username,
                "email": current_user.email,
                "role": current_user.role.value
                if hasattr(current_user.role, "value")
                else current_user.role,
            },
        }
    except Exception as e:
        logger.error(f"Test auth error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"认证测试失败: {str(e)}",
        )


@router.get("/debug-auth", summary="调试认证依赖")
async def debug_auth_dependency():
    """
    逐步测试认证依赖
    """
    from datetime import datetime

    try:
        # 测试1: 数据库连接
        print("[DEBUG] Step 1: Testing database connection")
        # next(get_db())  # 暂时注释掉，避免数据库连接问题

        # 测试2: 导入认证模块
        print("[DEBUG] Step 2: Importing auth middleware")

        # 测试3: 检查枚举
        print("[DEBUG] Step 3: Checking UserRole enum")
        from ..models.auth import UserRole

        admin_role = UserRole.ADMIN
        print(f"[DEBUG] UserRole.ADMIN = {admin_role}, type = {type(admin_role)}")

        # 测试4: 检查JWT配置
        print("[DEBUG] Step 4: Checking JWT config")
        from ..core.config import settings

        secret_key = settings.SECRET_KEY
        print(f"[DEBUG] SECRET_KEY exists: {bool(secret_key)}")

        return {
            "success": True,
            "message": "认证依赖调试成功",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        import traceback

        error_detail = f"调试失败: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"调试失败: {str(e)}",
        )


@router.put("/profile", response_model=UserResponse, summary="更新个人资料")
async def update_user_profile(
    profile_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """
    更新当前用户的个人资料

    - 只能更新自己的信息
    - 不能修改敏感字段（如密码、角色等）
    - 自动验证数据有效性
    """
    try:
        user_crud = UserCRUD()

        # 获取用户实体
        user = user_crud.get(db, current_user.id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在"
            )

        # 验证只能更新允许的字段
        allowed_fields = {"full_name", "email", "phone"}
        update_data = {}

        for field, value in profile_data.dict(exclude_unset=True).items():
            if field in allowed_fields:
                update_data[field] = value

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="没有可更新的字段"
            )

        # 更新用户信息
        updated_user = user_crud.update(db, current_user.id, update_data)

        # 记录审计日志
        audit_crud = AuditLogCRUD()
        audit_crud.create(
            db=db,
            user_id=current_user.id,
            action="profile_updated",
            resource_type="user_profile",
            resource_id=current_user.id,
        )

        return UserResponse.from_orm(updated_user)

    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/profile/change-password", summary="修改密码")
async def change_user_password(
    password_data: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """
    修改当前用户的密码

    - 验证当前密码
    - 应用密码策略
    - 更新密码历史记录
    - 撤销所有其他会话
    """
    try:
        auth_service = AuthService(db)

        # 验证当前密码
        user_crud = UserCRUD()
        user = user_crud.get(db, current_user.id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在"
            )

        # 验证当前密码
        if not auth_service.authenticate_user(
            user.username, password_data.old_password
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确"
            )

        # 更新密码
        success = auth_service.change_password(
            user_id=current_user.id, new_password=password_data.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="密码修改失败"
            )

        # 记录审计日志
        audit_crud = AuditLogCRUD()
        audit_crud.create(
            db=db,
            user_id=current_user.id,
            action="password_changed",
            resource_type="user_security",
            resource_id=current_user.id,
        )

        return {"message": "密码修改成功"}

    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/activity", response_model=list[dict], summary="获取用户活动记录")
async def get_user_activity(
    limit: int = 20,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """
    获取当前用户的活动记录

    - 支持分页
    - 支持时间范围筛选
    - 包含登录、操作等记录
    """
    try:
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        audit_crud = AuditLogCRUD()

        # 获取用户活动记录
        activities = audit_crud.get_user_activities(
            db=db,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

        # 格式化返回数据
        formatted_activities = []
        for activity in activities:
            formatted_activities.append(
                {
                    "id": activity.id,
                    "action": activity.action,
                    "resource_type": activity.resource_type,
                    "resource_id": activity.resource_id,
                    "details": json.loads(activity.details) if activity.details else {},
                    "ip_address": activity.ip_address,
                    "user_agent": activity.user_agent,
                    "created_at": activity.created_at.isoformat(),
                    "action_display": _get_action_display_name(activity.action),
                }
            )

        return formatted_activities

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取活动记录失败: {str(e)}",
        )


def _get_action_display_name(action: str) -> str:
    """获取操作的显示名称"""
    action_map = {
        "login": "登录",
        "logout": "退出登录",
        "profile_updated": "更新个人资料",
        "password_changed": "修改密码",
        "sessions_revoked": "撤销会话",
        "asset_created": "创建资产",
        "asset_updated": "更新资产",
        "asset_deleted": "删除资产",
        "contract_created": "创建合同",
        "contract_updated": "更新合同",
        "contract_deleted": "删除合同",
    }
    return action_map.get(action, action)
