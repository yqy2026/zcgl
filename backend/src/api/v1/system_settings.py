from typing import Any, Annotated

"""
系统设置API路由
"""

import json
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
from sqlalchemy.orm import Session

from ...crud.auth import AuditLogCRUD
from ...database import get_db
from ...middleware.auth import get_current_active_user
from ...schemas.auth import UserResponse

# 创建系统设置路由器
router = APIRouter()


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


# 内存存储设置（实际应用中应该存储在数据库或配置文件中）
_system_settings = SystemSettings()


@router.get("/settings", summary="获取系统设置")
async def get_system_settings(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
) -> dict[str, Any]:
    """
    获取系统设置

    返回当前系统的所有设置项
    """
    try:
        return {
            "success": True,
            "data": _system_settings.model_dump(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统设置失败: {str(e)}")


@router.put("/settings", summary="更新系统设置")
async def update_system_settings(
    settings: SystemSettings,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
    request: Request | None = None,
) -> dict[str, Any]:
    """
    更新系统设置

    - **settings**: 系统设置数据
    """
    try:
        global _system_settings
        _system_settings = settings

        # 记录审计日志
        try:
            ip_address: str | None = None
            user_agent: str = ""
            if request is not None:
                if request.client is not None:
                    ip_address = request.client.host
                user_agent = str(request.headers.get("user-agent", ""))

            audit_crud = AuditLogCRUD()
            audit_crud.create(
                db,
                user_id=current_user.id,
                username=current_user.username,
                action="UPDATE_SYSTEM_SETTINGS",
                resource_type="system_settings",
                ip_address=ip_address,
                user_agent=user_agent,
                request_body=json.dumps({"updated_settings": settings.model_dump()}),
            )
        except Exception:
            # 审计日志失败不应该影响系统设置更新
            import logging

            logger = logging.getLogger(__name__)
            logger.warning("记录系统设置审计日志失败", exc_info=True)

        return {
            "success": True,
            "message": "系统设置更新成功",
            "data": _system_settings.model_dump(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新系统设置失败: {str(e)}")


@router.get("/info", summary="获取系统信息")
async def get_system_info(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
) -> dict[str, Any]:
    """
    获取系统信息

    返回系统的基本信息和状态
    """
    try:
        # 检查数据库连接
        try:
            db.execute(text("SELECT 1"))
            database_status: str = "connected"
        except Exception:
            database_status = "disconnected"

        # 获取环境变量
        environment = os.getenv("ENVIRONMENT", "development")

        # 模拟构建时间
        build_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        system_info = SystemInfo(
            build_time=build_time,
            database_status=database_status,
            environment=environment,
        )

        return {
            "success": True,
            "data": system_info.model_dump(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")


@router.post("/backup", summary="备份系统数据")
async def backup_system(
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
    request: Request | None = None,
) -> dict[str, Any]:
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

        # 记录审计日志
        try:
            ip_address: str | None = None
            user_agent: str = ""
            if request is not None:
                if request.client is not None:
                    ip_address = request.client.host
                user_agent = str(request.headers.get("user-agent", ""))

            audit_crud = AuditLogCRUD()
            audit_crud.create(
                db,
                user_id=current_user.id,
                username=current_user.username,
                action="SYSTEM_BACKUP",
                resource_type="system",
                request_body=json.dumps({"backup_time": backup_data["backup_time"]}),
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception:
            # 审计日志失败不应该影响备份流程
            import logging

            logger = logging.getLogger(__name__)
            logger.warning("记录备份审计日志失败", exc_info=True)

        return {
            "success": True,
            "message": "系统数据备份成功",
            "data": backup_data,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系统备份失败: {str(e)}")


@router.post("/restore", summary="恢复系统数据")
async def restore_system(
    backup_file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
    request: Request | None = None,
) -> dict[str, Any]:
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

        # 记录审计日志
        try:
            ip_address: str | None = None
            user_agent: str = ""
            if request is not None:
                if request.client is not None:
                    ip_address = request.client.host
                user_agent = str(request.headers.get("user-agent", ""))

            audit_crud = AuditLogCRUD()
            audit_crud.create(
                db,
                user_id=current_user.id,
                username=current_user.username,
                action="SYSTEM_RESTORE",
                resource_type="system",
                request_body=json.dumps(
                    {
                        "backup_time": backup_data.get("backup_time"),
                        "backup_file": filename,
                        "restored_settings": backup_data.get("system_settings", {}),
                    }
                ),
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception:
            # 审计日志失败不应该影响恢复流程
            import logging

            logger = logging.getLogger(__name__)
            logger.warning("记录恢复审计日志失败", exc_info=True)

        return {
            "success": True,
            "message": "系统数据恢复成功",
            "restored_backup": {
                "backup_time": backup_data.get("backup_time"),
                "version": backup_data.get("version"),
                "filename": filename,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系统恢复失败: {str(e)}")
