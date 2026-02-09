"""
数据备份和恢复API路由
"""

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import settings
from ....core.exception_handler import bad_request, not_found
from ....database import get_async_db
from ....middleware.auth import require_admin
from ....services.backup import BackupService
from ..utils import handle_api_errors

# 配置日志
logger = logging.getLogger(__name__)

# 创建备份路由器
router = APIRouter(dependencies=[Depends(require_admin)])

# 备份目录
BACKUP_DIR = "backups"
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)


@router.post("/create", summary="创建数据备份")
@handle_api_errors
async def create_backup(
    backup_name: str | None = Query(None, description="备份名称，默认使用时间戳"),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """
    创建数据库备份

    Args:
        backup_name: 备份名称，如果不提供则使用时间戳
        db: 数据库会话

    Returns:
        备份结果信息
    """

    service = BackupService(backup_dir=BACKUP_DIR)

    db_url: str | None = None
    bind = db.get_bind()
    if bind is not None and hasattr(bind, "url") and bind.url is not None:
        db_url = str(bind.url)
    if not db_url:
        db_url = settings.DATABASE_URL or None

    result = service.create_backup(backup_name=backup_name, database_url=db_url)

    logger.info(f"数据备份创建成功: {result['backup_path']}")

    return {
        "success": True,
        "message": "数据备份创建成功",
        "data": result,
    }


@router.get("/list[Any]", summary="获取备份列表")
@handle_api_errors
def list_backups() -> dict[str, Any]:
    """
    获取所有备份文件列表

    Returns:
        备份文件列表
    """
    # 使用BackupService获取备份列表
    service = BackupService(backup_dir=BACKUP_DIR)
    backups = service.list_backups()

    logger.info(f"找到 {len(backups)} 个备份文件")

    return {
        "success": True,
        "message": f"找到 {len(backups)} 个备份文件",
        "data": backups,
    }


@router.get("/download/{backup_name}", summary="下载备份文件")
@handle_api_errors
def download_backup(backup_name: str) -> FileResponse:
    """
    下载指定的备份文件

    Args:
        backup_name: 备份名称

    Returns:
        备份文件
    """
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


@router.post("/restore/{backup_name}", summary="恢复数据备份")
@handle_api_errors
async def restore_backup(
    backup_name: str,
    confirm: bool = Query(False, description="确认恢复操作"),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """
    从备份文件恢复数据

    Args:
        backup_name: 备份名称
        confirm: 确认恢复操作
        db: 数据库会话

    Returns:
        恢复结果信息
    """

    if not confirm:
        raise bad_request("请确认恢复操作，这将覆盖当前数据")

    service = BackupService(backup_dir=BACKUP_DIR)

    db_url: str | None = None
    bind = db.get_bind()
    if bind is not None and hasattr(bind, "url") and bind.url is not None:
        db_url = str(bind.url)
    if not db_url:
        db_url = settings.DATABASE_URL or None

    try:
        result = service.restore_backup(
            backup_name=backup_name,
            database_url=db_url,
            create_current_backup=True,
        )
    except FileNotFoundError as e:
        raise not_found(str(e), resource_type="backup")

    logger.info(f"数据恢复成功: {backup_name}")

    return {
        "success": True,
        "message": "数据恢复成功",
        "data": result,
    }


@router.delete("/delete/{backup_name}", summary="删除备份文件")
@handle_api_errors
def delete_backup(backup_name: str) -> dict[str, Any]:
    """
    删除指定的备份文件

    Args:
        backup_name: 备份名称

    Returns:
        删除结果信息
    """
    # 使用BackupService删除备份
    service = BackupService(backup_dir=BACKUP_DIR)
    try:
        result = service.delete_backup(backup_name)
    except FileNotFoundError as e:
        raise not_found(str(e), resource_type="backup")

    logger.info(f"删除备份文件: {backup_name}")

    return {
        "success": True,
        "message": f"备份文件 {backup_name} 已成功删除",
        "data": result,
    }


@router.get("/stats", summary="获取备份统计信息")
@handle_api_errors
def get_backup_stats() -> dict[str, Any]:
    """
    获取备份统计信息

    Returns:
        备份统计信息
    """
    service = BackupService(backup_dir=BACKUP_DIR)
    stats = service.get_backup_stats()

    return {
        "success": True,
        "data": stats,
    }


@router.post("/validate/{backup_name}", summary="验证备份文件")
@handle_api_errors
def validate_backup(backup_name: str) -> dict[str, Any]:
    """
    验证备份文件的完整性

    Args:
        backup_name: 备份名称

    Returns:
        验证结果
    """
    service = BackupService(backup_dir=BACKUP_DIR)
    validation_result = service.validate_backup(backup_name)

    return {
        "success": validation_result["valid"],
        "data": validation_result,
    }


@router.post("/cleanup", summary="清理旧备份")
@handle_api_errors
def cleanup_old_backups(
    keep_count: int = Query(10, ge=1, le=100, description="保留的备份数量"),
) -> dict[str, Any]:
    """
    清理旧的备份文件，保留最新的 N 个

    Args:
        keep_count: 保留的备份数量

    Returns:
        清理结果
    """
    service = BackupService(backup_dir=BACKUP_DIR)
    result = service.cleanup_old_backups(keep_count=keep_count)

    return {
        "success": True,
        "message": f"已清理 {result['cleaned']} 个旧备份",
        "data": result,
    }
