"""数据备份和恢复API端点
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from src.database import get_db
from src.services.backup_service import backup_service, auto_backup_scheduler
from src.schemas.backup import (
    BackupRequest,
    BackupResponse,
    BackupListResponse,
    RestoreRequest,
    RestoreResponse,
    BackupInfoResponse
)

router = APIRouter(prefix="/backup", tags=["backup"])
logger = logging.getLogger(__name__)


@router.post("/create", response_model=BackupResponse)
def create_backup(
    request: BackupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> BackupResponse:
    """
    创建数据库备份
    
    Args:
        request: 备份请求参数
        background_tasks: 后台任务
        db: 数据库会话
    
    Returns:
        备份创建结果
    """
    try:
        logger.info(f"开始创建数据库备份，描述: {request.description}")
        
        if request.async_backup:
            # 异步备份
            background_tasks.add_task(
                _create_backup_task,
                request.description
            )
            
            return BackupResponse(
                success=True,
                message="备份任务已创建，正在后台执行",
                backup_info=None,
                async_backup=True
            )
        else:
            # 同步备份
            result = backup_service.create_backup(request.description)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=500,
                    detail=result["message"]
                )
            
            logger.info("数据库备份创建完成")
            
            return BackupResponse(
                success=True,
                message=result["message"],
                backup_info=result["backup_info"],
                async_backup=False
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建数据库备份异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"创建备份失败: {str(e)}"
        )


@router.get("/list", response_model=BackupListResponse)
def list_backups() -> BackupListResponse:
    """
    列出所有备份文件
    
    Returns:
        备份文件列表
    """
    try:
        logger.info("获取备份文件列表")
        
        result = backup_service.list_backups()
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result["message"]
            )
        
        return BackupListResponse(
            success=True,
            message=result["message"],
            backups=result["backups"],
            total_count=result["total_count"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取备份列表异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取备份列表失败: {str(e)}"
        )


@router.get("/info/{backup_filename}", response_model=BackupInfoResponse)
def get_backup_info(backup_filename: str) -> BackupInfoResponse:
    """
    获取备份文件详细信息
    
    Args:
        backup_filename: 备份文件名
    
    Returns:
        备份文件详细信息
    """
    try:
        logger.info(f"获取备份文件信息: {backup_filename}")
        
        result = backup_service.get_backup_info(backup_filename)
        
        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail=result["message"]
            )
        
        return BackupInfoResponse(
            success=True,
            message=result["message"],
            info=result["info"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取备份信息异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取备份信息失败: {str(e)}"
        )


@router.post("/restore", response_model=RestoreResponse)
def restore_backup(
    request: RestoreRequest,
    db: Session = Depends(get_db)
) -> RestoreResponse:
    """
    恢复数据库备份
    
    Args:
        request: 恢复请求参数
        db: 数据库会话
    
    Returns:
        恢复结果
    """
    try:
        logger.info(f"开始恢复数据库备份: {request.backup_filename}")
        
        result = backup_service.restore_backup(
            request.backup_filename,
            request.confirm
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
        
        logger.info("数据库备份恢复完成")
        
        return RestoreResponse(
            success=True,
            message=result["message"],
            restored=result["restored"],
            safety_backup=result.get("safety_backup")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复数据库备份异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"恢复备份失败: {str(e)}"
        )


@router.delete("/{backup_filename}")
def delete_backup(backup_filename: str) -> Dict[str, Any]:
    """
    删除备份文件
    
    Args:
        backup_filename: 备份文件名
    
    Returns:
        删除结果
    """
    try:
        logger.info(f"删除备份文件: {backup_filename}")
        
        result = backup_service.delete_backup(backup_filename)
        
        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail=result["message"]
            )
        
        return {
            "success": True,
            "message": result["message"],
            "deleted": result["deleted"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除备份文件异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"删除备份文件失败: {str(e)}"
        )


@router.post("/cleanup")
def cleanup_old_backups() -> Dict[str, Any]:
    """
    清理过期的备份文件
    
    Returns:
        清理结果
    """
    try:
        logger.info("开始清理过期备份文件")
        
        result = backup_service.cleanup_old_backups()
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result["message"]
            )
        
        return {
            "success": True,
            "message": result["message"],
            "deleted_count": result["deleted_count"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理备份文件异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"清理备份文件失败: {str(e)}"
        )


@router.get("/scheduler/status")
def get_scheduler_status() -> Dict[str, Any]:
    """
    获取自动备份调度器状态
    
    Returns:
        调度器状态信息
    """
    try:
        return {
            "success": True,
            "message": "获取调度器状态成功",
            "status": {
                "is_running": auto_backup_scheduler.is_running,
                "last_backup_time": auto_backup_scheduler.last_backup_time.isoformat() if auto_backup_scheduler.last_backup_time else None,
                "auto_backup_enabled": auto_backup_scheduler.config.auto_backup_enabled,
                "backup_interval_hours": auto_backup_scheduler.config.backup_interval_hours,
                "backup_retention_days": auto_backup_scheduler.config.backup_retention_days,
                "max_backups": auto_backup_scheduler.config.max_backups
            }
        }
        
    except Exception as e:
        logger.error(f"获取调度器状态异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取调度器状态失败: {str(e)}"
        )


async def _create_backup_task(description: Optional[str] = None):
    """后台备份任务"""
    try:
        result = await backup_service.create_backup_async(description)
        if result["success"]:
            logger.info(f"后台备份任务完成: {result['backup_info']['filename']}")
        else:
            logger.error(f"后台备份任务失败: {result['message']}")
    except Exception as e:
        logger.error(f"后台备份任务异常: {str(e)}")