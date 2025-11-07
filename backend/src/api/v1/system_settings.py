from typing import Any

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
async def get_system_settings(db: Session = Depends(get_db)):
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
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
    request: Request = None,
):
    """
    更新系统设置

    - **settings**: 系统设置数据
    """
    try:
        global _system_settings
        _system_settings = settings

        # 记录审计日志
        try:
            audit_data = {
                "user_id": current_user.id,
                "username": current_user.username,
                "action": "UPDATE_SYSTEM_SETTINGS",
                "resource": "system_settings",
                "details": {"updated_settings": settings.model_dump()},
                "ip_address": request.client.host if request else None,
                "user_agent": str(request.headers.get("user-agent", ""))
                if request
                else "",
            }
            AuditLogCRUD.create_log(db, audit_data)
        except Exception as e:
            # 审计日志失败不应该影响系统设置更新
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"记录系统设置审计日志失败: {e}")

        return {
            "success": True,
            "message": "系统设置更新成功",
            "data": _system_settings.model_dump(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新系统设置失败: {str(e)}")


@router.get("/info", summary="获取系统信息")
async def get_system_info(db: Session = Depends(get_db)):
    """
    获取系统信息

    返回系统的基本信息和状态
    """
    try:
        # 检查数据库连接
        try:
            db.execute("SELECT 1")
            database_status = "connected"
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
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    request: Request = None,
):
    """
    备份系统数据

    创建系统数据的完整备份
    """
    try:
        # 这里可以实现真正的数据备份逻辑
        # 目前返回模拟的备份数据

        backup_data = {
            "backup_time": datetime.now().isoformat(),
            "backup_user": current_user.username,
            "system_settings": _system_settings.model_dump(),
            "backup_type": "full",
            "version": "2.0.0",
        }

        # 记录审计日志
        try:
            audit_data = {
                "user_id": current_user.id,
                "username": current_user.username,
                "action": "SYSTEM_BACKUP",
                "resource": "system",
                "details": {"backup_time": backup_data["backup_time"]},
                "ip_address": request.client.host if request else None,
                "user_agent": str(request.headers.get("user-agent", ""))
                if request
                else "",
            }
            AuditLogCRUD.create_log(db, audit_data)
        except Exception as e:
            # 审计日志失败不应该影响备份流程
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"记录备份审计日志失败: {e}")

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
    backup_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    request: Request = None,
):
    """
    恢复系统数据

    从备份文件恢复系统数据
    """
    try:
        # 验证文件类型
        if not backup_file.filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="备份文件必须是JSON格式")

        # 读取备份文件内容
        content = await backup_file.read()
        try:
            backup_data = json.loads(content.decode("utf-8"))
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
            audit_data = {
                "user_id": current_user.id,
                "username": current_user.username,
                "action": "SYSTEM_RESTORE",
                "resource": "system",
                "details": {
                    "backup_time": backup_data.get("backup_time"),
                    "backup_file": backup_file.filename,
                    "restored_settings": backup_data.get("system_settings", {}),
                },
                "ip_address": request.client.host if request else None,
                "user_agent": str(request.headers.get("user-agent", ""))
                if request
                else "",
            }
            AuditLogCRUD.create_log(db, audit_data)
        except Exception as e:
            # 审计日志失败不应该影响恢复流程
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"记录恢复审计日志失败: {e}")

        return {
            "success": True,
            "message": "系统数据恢复成功",
            "restored_backup": {
                "backup_time": backup_data.get("backup_time"),
                "version": backup_data.get("version"),
                "filename": backup_file.filename,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系统恢复失败: {str(e)}")
