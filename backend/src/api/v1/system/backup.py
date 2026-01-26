"""
数据备份和恢复API路由
"""

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.params import Query as QueryParam
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ....core.exception_handler import (
    BaseBusinessError,
    bad_request,
    internal_error,
    not_found,
)
from ....database import get_db
from ....services.backup import BackupService

# 配置日志
logger = logging.getLogger(__name__)

# 创建备份路由器
router = APIRouter()

# 备份目录
BACKUP_DIR = "backups"
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)


@router.post("/create", summary="创建数据备份")
async def create_backup(
    backup_name: str | None = Query(None, description="备份名称，默认使用时间戳"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    创建数据库备份

    Args:
        backup_name: 备份名称，如果不提供则使用时间戳
        db: 数据库会话

    Returns:
        备份结果信息
    """
    try:
        # 使用BackupService创建备份
        service = BackupService(backup_dir=BACKUP_DIR)

        # 从数据库连接获取数据库文件路径（SQLite）
        db_path: str | None = None
        if db.bind is not None and hasattr(db.bind, "url") and db.bind.url is not None:
            db_url = str(db.bind.url)
            if db_url.startswith("sqlite:///"):
                db_path = db_url.replace("sqlite:///", "")

        result = service.create_backup(backup_name=backup_name, db_path=db_path)

        logger.info(f"数据备份创建成功: {result['backup_path']}")

        return {
            "success": True,
            "message": "数据备份创建成功",
            "data": result,
        }

    except Exception as e:
        logger.error(f"创建数据备份异常: {str(e)}")
        raise internal_error(f"创建数据备份失败: {str(e)}")


@router.get("/list[Any]", summary="获取备份列表")
async def list_backups() -> dict[str, Any]:
    """
    获取所有备份文件列表

    Returns:
        备份文件列表
    """
    try:
        # 使用BackupService获取备份列表
        service = BackupService(backup_dir=BACKUP_DIR)
        backups = service.list_backups()

        logger.info(f"找到 {len(backups)} 个备份文件")

        return {
            "success": True,
            "message": f"找到 {len(backups)} 个备份文件",
            "data": backups,
        }

    except Exception as e:
        logger.error(f"获取备份列表异常: {str(e)}")
        raise internal_error(f"获取备份列表失败: {str(e)}")


@router.get("/download/{backup_name}", summary="下载备份文件")
async def download_backup(backup_name: str) -> FileResponse:
    """
    下载指定的备份文件

    Args:
        backup_name: 备份名称

    Returns:
        备份文件
    """
    try:
        service = BackupService(backup_dir=BACKUP_DIR)
        backup_info = service.get_backup(backup_name)

        if not backup_info:
            raise not_found(f"备份文件不存在: {backup_name}", resource_type="backup")

        backup_path = backup_info["file_path"]
        backup_filename = backup_info["filename"]

        logger.info(f"下载备份文件: {backup_path}")

        return FileResponse(
            path=backup_path,
            filename=backup_filename,
            media_type="application/octet-stream",
        )

    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        logger.error(f"下载备份文件异常: {str(e)}")
        raise internal_error(f"下载备份文件失败: {str(e)}")


@router.post("/restore/{backup_name}", summary="恢复数据备份")
async def restore_backup(
    backup_name: str,
    confirm: bool = Query(False, description="确认恢复操作"),
    should_confirm: bool | None = Query(
        None, description="确认恢复操作", alias="should_confirm"
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    从备份文件恢复数据

    Args:
        backup_name: 备份名称
        should_confirm: 确认恢复操作
        db: 数据库会话

    Returns:
        恢复结果信息
    """
    try:
        if isinstance(should_confirm, QueryParam):
            confirm_value = confirm
        else:
            confirm_value = confirm if should_confirm is None else should_confirm
        if not confirm_value:
            raise bad_request("请确认恢复操作，这将覆盖当前数据")

        # 使用BackupService恢复备份
        service = BackupService(backup_dir=BACKUP_DIR)

        # 从数据库连接获取数据库文件路径（SQLite）
        db_path: str | None = None
        if db.bind is not None and hasattr(db.bind, "url") and db.bind.url is not None:
            db_url = str(db.bind.url)
            if db_url.startswith("sqlite:///"):
                db_path = db_url.replace("sqlite:///", "")

        result = service.restore_backup(
            backup_name=backup_name,
            db_path=db_path,
            create_current_backup=True,
        )

        logger.info(f"数据恢复成功: {backup_name}")

        return {
            "success": True,
            "message": "数据恢复成功",
            "data": result,
        }

    except FileNotFoundError as e:
        raise not_found(str(e), resource_type="backup")
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        logger.error(f"恢复数据备份异常: {str(e)}")
        raise internal_error(f"恢复数据备份失败: {str(e)}")


@router.delete("/delete/{backup_name}", summary="删除备份文件")
async def delete_backup(backup_name: str) -> dict[str, Any]:
    """
    删除指定的备份文件

    Args:
        backup_name: 备份名称

    Returns:
        删除结果信息
    """
    try:
        # 使用BackupService删除备份
        service = BackupService(backup_dir=BACKUP_DIR)
        result = service.delete_backup(backup_name)

        logger.info(f"删除备份文件: {backup_name}")

        return {
            "success": True,
            "message": f"备份文件 {backup_name} 已成功删除",
            "data": result,
        }

    except FileNotFoundError as e:
        raise not_found(str(e), resource_type="backup")
    except Exception as e:
        logger.error(f"删除备份文件异常: {str(e)}")
        raise internal_error(f"删除备份文件失败: {str(e)}")


@router.get("/stats", summary="获取备份统计信息")
async def get_backup_stats() -> dict[str, Any]:
    """
    获取备份统计信息

    Returns:
        备份统计信息
    """
    try:
        service = BackupService(backup_dir=BACKUP_DIR)
        stats = service.get_backup_stats()

        return {
            "success": True,
            "data": stats,
        }

    except Exception as e:
        logger.error(f"获取备份统计异常: {str(e)}")
        raise internal_error(f"获取备份统计失败: {str(e)}")


@router.post("/validate/{backup_name}", summary="验证备份文件")
async def validate_backup(backup_name: str) -> dict[str, Any]:
    """
    验证备份文件的完整性

    Args:
        backup_name: 备份名称

    Returns:
        验证结果
    """
    try:
        service = BackupService(backup_dir=BACKUP_DIR)
        validation_result = service.validate_backup(backup_name)

        return {
            "success": validation_result["valid"],
            "data": validation_result,
        }

    except Exception as e:
        logger.error(f"验证备份文件异常: {str(e)}")
        raise internal_error(f"验证备份文件失败: {str(e)}")


@router.post("/cleanup", summary="清理旧备份")
async def cleanup_old_backups(
    keep_count: int = Query(10, ge=1, le=100, description="保留的备份数量"),
) -> dict[str, Any]:
    """
    清理旧的备份文件，保留最新的 N 个

    Args:
        keep_count: 保留的备份数量

    Returns:
        清理结果
    """
    try:
        service = BackupService(backup_dir=BACKUP_DIR)
        result = service.cleanup_old_backups(keep_count=keep_count)

        return {
            "success": True,
            "message": f"已清理 {result['cleaned']} 个旧备份",
            "data": result,
        }

    except Exception as e:
        logger.error(f"清理旧备份异常: {str(e)}")
        raise internal_error(f"清理旧备份失败: {str(e)}")
