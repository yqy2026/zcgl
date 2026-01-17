from typing import Annotated, Any

"""
系统设置API路由
"""

import json
import logging
import os
from datetime import datetime

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ...crud.auth import AuditLogCRUD
from ...database import get_db
from ...middleware.auth import get_current_active_user
from ...schemas.auth import UserResponse

# 创建系统设置路由器
router = APIRouter()
logger = logging.getLogger(__name__)


def handle_audit_log_failure(
    db: Session,
    current_user: Any,
    action: str,
    error: Exception,
) -> None:
    """
    统一处理审计日志失败

    Args:
        db: 数据库会话
        current_user: 当前用户
        action: 操作类型
        error: 捕获的异常
    """
    # 1. 记录CRITICAL级别日志
    logger.critical(
        "审计日志失败 - 安全违规未记录",
        exc_info=True,
        extra={
            "error_id": "AUDIT_LOG_FAILED",
            "error_type": type(error).__name__,
            "user_id": str(current_user.id),
            "action": action,
            "severity": "CRITICAL",
            "security_impact": "Audit trail compromised"
        }
    )

    # 2. 生产环境发送安全警报
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "production":
        # TODO: 集成到监控系统 (Sentry, PagerDuty等)
        # send_security_alert(...)
        pass

    # 3. 回退: 写入文件审计日志
    try:
        from pathlib import Path

        audit_log_path = Path("logs/audit_log_fallback.txt")
        audit_log_path.parent.mkdir(exist_ok=True)

        timestamp = datetime.now().isoformat()
        with open(audit_log_path, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} | {action} | {current_user.id} | ERROR: {error}\n")
    except (PermissionError, OSError, IOError) as fallback_error:
        # 最后手段: 记录到系统日志
        import sys
        print(
            f"[AUDIT LOG FALLBACK FAILED] {timestamp} | {action} | {current_user.id} | "
            f"PRIMARY: {error} | FALLBACK: {fallback_error}",
            file=sys.stderr
        )


def create_audit_log_with_fallback(
    db: Session,
    current_user: Any,
    action: str,
    resource_type: str,
    request: Request,
    **kwargs
) -> bool:
    """
    创建审计日志，带统一错误处理

    Returns:
        bool: 是否成功创建审计日志
    """
    try:
        ip_address = request.client.host if request.client else None
        user_agent = str(request.headers.get("user-agent", ""))

        audit_crud = AuditLogCRUD()
        audit_crud.create(
            db,
            user_id=current_user.id,
            action=action,
            resource_type=resource_type,
            ip_address=ip_address,
            user_agent=user_agent,
            request_body=json.dumps(kwargs),
        )
        return True

    except (SQLAlchemyError, ValueError, TypeError, json.JSONDecodeError) as audit_error:
        handle_audit_log_failure(db, current_user, action, audit_error)
        return False


class SystemSettings(BaseModel):
    """系统设置模型"""

    site_name: str = "土地物业资产管理系统"
    site_description: str = "专业的土地物业资产管理平台"
    allow_registration: bool = False
    session_timeout: int = 120
    password_policy: dict[str, Any] = {
        "min_length": 8,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_numbers": True,
        "require_special_chars": False,
    }


class SystemInfo(BaseModel):
    """系统信息模型"""

    version: str = "2.0.0"
    build_time: str
    database_status: str = "connected"
    api_version: str = "v1"
    environment: str = "development"


# Response models for API endpoints
class SystemSettingsResponse(BaseModel):
    """系统设置响应模型"""

    success: bool
    data: SystemSettings
    timestamp: str


class SystemInfoResponse(BaseModel):
    """系统信息响应模型"""

    success: bool
    data: SystemInfo
    timestamp: str


class SystemBackupResponse(BaseModel):
    """系统备份响应模型"""

    success: bool
    message: str
    data: dict[str, Any]
    timestamp: str


class SystemRestoreResponse(BaseModel):
    """系统恢复响应模型"""

    success: bool
    message: str
    restored_backup: dict[str, Any]
    timestamp: str


# 内存存储设置（实际应用中应该存储在数据库或配置文件中）
_system_settings = SystemSettings()


@router.get("/settings", summary="获取系统设置", response_model=SystemSettingsResponse)
async def get_system_settings(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
) -> SystemSettingsResponse:
    """
    获取系统设置

    返回当前系统的所有设置项
    """
    try:
        return SystemSettingsResponse(
            success=True,
            data=_system_settings,
            timestamp=datetime.now().isoformat(),
        )
    except (ValueError, TypeError, AttributeError) as e:
        # 预期的验证/格式化错误
        logger.error(
            f"系统设置验证错误: {e}",
            extra={"error_id": "SYSTEM_SETTINGS_VALIDATION_ERROR"}
        )
        raise HTTPException(
            status_code=500,
            detail=f"获取系统设置失败: {str(e)}"
        ) from e
    except Exception as e:
        # 未预期的错误 - 记录完整详情并重新抛出
        logger.critical(
            f"系统设置未知错误: {e}",
            exc_info=True,
            extra={"error_id": "SYSTEM_SETTINGS_UNEXPECTED_ERROR"}
        )
        # 不捕获系统错误 - 让中间件处理
        raise


@router.put("/settings", summary="更新系统设置", response_model=SystemSettingsResponse)
async def update_system_settings(
    settings: SystemSettings,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
    request: Request,
) -> SystemSettingsResponse:
    """
    更新系统设置

    - **settings**: 系统设置数据
    """
    try:
        global _system_settings
        _system_settings = settings

        # 使用统一的审计日志处理函数
        create_audit_log_with_fallback(
            db=db,
            current_user=current_user,
            action="UPDATE_SYSTEM_SETTINGS",
            resource_type="system_settings",
            request=request,
            updated_settings=settings.model_dump()
        )

        return SystemSettingsResponse(
            success=True,
            data=_system_settings,
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新系统设置失败: {str(e)}")


@router.get("/info", summary="获取系统信息", response_model=SystemInfoResponse)
async def get_system_info(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
) -> SystemInfoResponse:
    """
    获取系统信息

    返回系统的基本信息和状态
    """
    try:
        # 检查数据库连接
        try:
            db.execute(text("SELECT 1"))
            database_status: str = "connected"
        except SQLAlchemyError as db_error:
            database_status = "disconnected"
            logger.error(
                "数据库连接检查失败",
                exc_info=True,
                extra={
                    "error_type": type(db_error).__name__,
                    "database_status": "disconnected",
                },
            )

        # 获取环境变量
        environment = os.getenv("ENVIRONMENT", "development")

        # 模拟构建时间
        build_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        system_info = SystemInfo(
            build_time=build_time,
            database_status=database_status,
            environment=environment,
        )

        return SystemInfoResponse(
            success=True,
            data=system_info,
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")


@router.post("/backup", summary="备份系统数据", response_model=SystemBackupResponse)
async def backup_system(
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
    request: Request,
) -> SystemBackupResponse:
    """
    备份系统数据

    创建系统数据的完整备份
    """
    try:
        # 这里可以实现真正的数据备份逻辑
        # 目前返回模拟的备份数据

        backup_data: dict[str, Any] = {
            "backup_time": datetime.now().isoformat(),
            "backup_user": current_user.username,
            "system_settings": _system_settings.model_dump(),
            "backup_type": "full",
            "version": "2.0.0",
        }

        # 使用统一的审计日志处理函数
        create_audit_log_with_fallback(
            db=db,
            current_user=current_user,
            action="SYSTEM_BACKUP",
            resource_type="system",
            request=request,
            backup_time=backup_data["backup_time"]
        )

        return SystemBackupResponse(
            success=True,
            message="系统数据备份成功",
            data=backup_data,
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系统备份失败: {str(e)}")


@router.post("/restore", summary="恢复系统数据", response_model=SystemRestoreResponse)
async def restore_system(
    backup_file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
    request: Request,
) -> SystemRestoreResponse:
    """
    恢复系统数据

    从备份文件恢复系统数据
    """
    try:
        # 验证文件类型
        filename = backup_file.filename
        if filename is None or not filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="备份文件必须是JSON格式")

        # 读取备份文件内容
        content = await backup_file.read()
        try:
            backup_data: dict[str, Any] = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="备份文件格式错误")

        # 验证备份数据格式
        required_fields = ["backup_time", "system_settings", "version"]
        for field in required_fields:
            if field not in backup_data:
                raise HTTPException(
                    status_code=400, detail=f"备份文件缺少必要字段: {field}"
                )

        # 恢复系统设置
        global _system_settings
        if "system_settings" in backup_data:
            _system_settings = SystemSettings(**backup_data["system_settings"])

        # 使用统一的审计日志处理函数
        create_audit_log_with_fallback(
            db=db,
            current_user=current_user,
            action="SYSTEM_RESTORE",
            resource_type="system",
            request=request,
            backup_time=backup_data.get("backup_time"),
            backup_file=filename,
            restored_settings=backup_data.get("system_settings", {})
        )

        return SystemRestoreResponse(
            success=True,
            message="系统数据恢复成功",
            restored_backup={
                "backup_time": backup_data.get("backup_time"),
                "version": backup_data.get("version"),
                "filename": filename,
            },
            timestamp=datetime.now().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系统恢复失败: {str(e)}")
