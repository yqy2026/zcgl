from typing import Any
"""
PDF导入会话管理服务
负责处理会话的创建、更新、查询和清理
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta


from sqlalchemy.orm import Session

from ..models.pdf_import_session import (
    PDFImportSession,
    ProcessingConfiguration,
    ProcessingStep,
    SessionLog,
    SessionStatus,
)

logger = logging.getLogger(__name__)


class PDFSessionService:
    """PDF导入会话管理服务"""

    def __init__(self):
        self.active_tasks = {}  # 跟踪活跃的处理任务

    async def create_session(
        self,
        db: Session,
        filename: str,
        file_size: int,
        file_path: str,
        content_type: str = "application/pdf",
        user_id: int | None = None,
        organization_id: int | None = None,
        processing_options: dict[str, Any] | None = None,
    ) -> PDFImportSession:
        """创建新的PDF导入会话"""

        session_id = (
            f"pdf_session_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"
        )

        # 创建会话记录
        session = PDFImportSession(
            session_id=session_id,
            original_filename=filename,
            file_size=file_size,
            file_path=file_path,
            content_type=content_type,
            status=SessionStatus.UPLOADED,
            current_step=ProcessingStep.FILE_UPLOAD,
            progress_percentage=10.0,
            user_id=user_id,
            organization_id=organization_id,
            processing_options=processing_options or {},
        )

        db.add(session)
        db.commit()
        db.refresh(session)

        # 创建处理配置，只传递有效的字段
        valid_options = processing_options or {}

        # 过滤出ProcessingConfiguration模型支持的字段
        supported_fields = {
            "prefer_ocr",
            "ocr_languages",
            "dpi",
            "max_pages",
            "extraction_confidence_threshold",
            "validate_fields",
            "strict_validation",
            "enable_asset_matching",
            "enable_ownership_matching",
            "enable_duplicate_check",
            "matching_threshold",
            "auto_confirm_high_confidence",
            "notification_enabled",
        }

        filtered_options = {
            k: v for k, v in valid_options.items() if k in supported_fields
        }

        config = ProcessingConfiguration(session_id=session_id, **filtered_options)
        db.add(config)

        # 记录日志
        await self.log_step(
            db,
            session_id,
            ProcessingStep.FILE_UPLOAD,
            "completed",
            f"文件上传成功: {filename} ({file_size} bytes)",
        )

        db.commit()

        logger.info(f"创建PDF导入会话: {session_id}, 文件: {filename}")
        return session

    async def update_session_progress(
        self,
        db: Session,
        session_id: str,
        status: SessionStatus,
        current_step: ProcessingStep,
        progress_percentage: float,
        error_message: str | None = None,
        extracted_data: dict[str, Any] | None = None,
        **kwargs,
    ) -> PDFImportSession | None:
        """更新会话进度"""

        session = (
            db.query(PDFImportSession)
            .filter(PDFImportSession.session_id == session_id)
            .first()
        )

        if not session:
            logger.error(f"会话不存在: {session_id}")
            return None

        # 更新字段
        session.status = status
        session.current_step = current_step
        session.progress_percentage = progress_percentage
        session.updated_at = datetime.now()

        if error_message:
            session.error_message = error_message

        if extracted_data:
            session.extracted_data = extracted_data

        # 处理其他字段
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

        # 记录完成时间
        if status in [
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
        ]:
            session.completed_at = datetime.now()

        db.commit()
        db.refresh(session)

        # 记录进度日志
        log_status = "failed" if error_message else "completed"
        log_message = f"步骤完成: {current_step.value}"

        if error_message:
            log_message += f", 错误: {error_message}"

        await self.log_step(db, session_id, current_step, log_status, log_message)

        logger.info(
            f"更新会话进度: {session_id} -> {status.value} ({progress_percentage}%)"
        )
        return session

    async def get_session(
        self, db: Session, session_id: str
    ) -> PDFImportSession | None:
        """获取会话信息"""
        return (
            db.query(PDFImportSession)
            .filter(PDFImportSession.session_id == session_id)
            .first()
        )

    async def get_active_sessions(
        self,
        db: Session,
        user_id: int | None = None,
        organization_id: int | None = None,
    ) -> list[PDFImportSession]:
        """获取活跃会话列表"""

        query = db.query(PDFImportSession).filter(
            PDFImportSession.status.in_(
                [
                    SessionStatus.UPLOADING,
                    SessionStatus.UPLOADED,
                    SessionStatus.PROCESSING,
                    SessionStatus.TEXT_EXTRACTED,
                    SessionStatus.INFO_EXTRACTED,
                    SessionStatus.VALIDATING,
                    SessionStatus.MATCHING,
                    SessionStatus.READY_FOR_REVIEW,
                ]
            )
        )

        if user_id:
            query = query.filter(PDFImportSession.user_id == user_id)

        if organization_id:
            query = query.filter(PDFImportSession.organization_id == organization_id)

        return query.order_by(PDFImportSession.created_at.desc()).limit(50).all()

    async def get_session_history(
        self,
        db: Session,
        user_id: int | None = None,
        organization_id: int | None = None,
        limit: int = 100,
    ) -> list[PDFImportSession]:
        """获取会话历史"""

        query = db.query(PDFImportSession).filter(
            PDFImportSession.status.in_(
                [
                    SessionStatus.COMPLETED,
                    SessionStatus.FAILED,
                    SessionStatus.CANCELLED,
                    SessionStatus.CONFIRMED,
                ]
            )
        )

        if user_id:
            query = query.filter(PDFImportSession.user_id == user_id)

        if organization_id:
            query = query.filter(PDFImportSession.organization_id == organization_id)

        return query.order_by(PDFImportSession.completed_at.desc()).limit(limit).all()

    async def cancel_session(
        self, db: Session, session_id: str, reason: str = "用户取消"
    ) -> bool:
        """取消会话"""

        session = await self.get_session(db, session_id)
        if not session:
            return False

        if session.is_completed:
            return False

        # 更新状态
        await self.update_session_progress(
            db,
            session_id,
            SessionStatus.CANCELLED,
            session.current_step,
            session.progress_percentage,
            f"会话已取消: {reason}",
        )

        # 取消关联的后台任务
        if session_id in self.active_tasks:
            task = self.active_tasks[session_id]
            if not task.done():
                task.cancel()
            del self.active_tasks[session_id]

        logger.info(f"取消会话: {session_id}, 原因: {reason}")
        return True

    async def log_step(
        self,
        db: Session,
        session_id: str,
        step: ProcessingStep,
        status: str,
        message: str,
        details: dict[str, Any] | None = None,
        duration_ms: float | None = None,
    ) -> SessionLog:
        """记录处理步骤日志"""

        log = SessionLog(
            session_id=session_id,
            step=step,
            status=status,
            message=message,
            details=details,
            duration_ms=duration_ms,
        )

        db.add(log)
        db.commit()
        db.refresh(log)

        return log

    async def get_session_logs(self, db: Session, session_id: str) -> list[SessionLog]:
        """获取会话日志"""
        return (
            db.query(SessionLog)
            .filter(SessionLog.session_id == session_id)
            .order_by(SessionLog.created_at.asc())
            .all()
        )

    async def cleanup_old_sessions(self, db: Session, days: int = 7) -> int:
        """清理旧会话数据"""

        cutoff_date = datetime.now() - timedelta(days=days)

        # 删除旧会话日志
        deleted_logs = (
            db.query(SessionLog).filter(SessionLog.created_at < cutoff_date).delete()
        )

        # 删除旧处理配置
        deleted_configs = (
            db.query(ProcessingConfiguration)
            .filter(ProcessingConfiguration.created_at < cutoff_date)
            .delete()
        )

        # 删除旧会话记录
        deleted_sessions = (
            db.query(PDFImportSession)
            .filter(
                PDFImportSession.created_at < cutoff_date,
                PDFImportSession.status.in_(
                    [
                        SessionStatus.COMPLETED,
                        SessionStatus.FAILED,
                        SessionStatus.CANCELLED,
                        SessionStatus.CONFIRMED,
                    ]
                ),
            )
            .delete()
        )

        db.commit()

        total_deleted = deleted_logs + deleted_configs + deleted_sessions
        logger.info(f"清理旧会话数据完成: {total_deleted} 条记录")
        return total_deleted

    async def get_session_statistics(
        self, db: Session, organization_id: int | None = None
    ) -> dict[str, Any]:
        """获取会话统计信息"""

        # 基础查询
        query = db.query(PDFImportSession)
        if organization_id:
            query = query.filter(PDFImportSession.organization_id == organization_id)

        # 总体统计
        total_sessions = query.count()
        active_sessions = query.filter(
            PDFImportSession.status.in_(
                [
                    SessionStatus.UPLOADING,
                    SessionStatus.UPLOADED,
                    SessionStatus.PROCESSING,
                    SessionStatus.TEXT_EXTRACTED,
                    SessionStatus.INFO_EXTRACTED,
                    SessionStatus.VALIDATING,
                    SessionStatus.MATCHING,
                    SessionStatus.READY_FOR_REVIEW,
                ]
            )
        ).count()

        completed_sessions = query.filter(
            PDFImportSession.status == SessionStatus.COMPLETED
        ).count()

        failed_sessions = query.filter(
            PDFImportSession.status == SessionStatus.FAILED
        ).count()

        # 最近24小时的统计
        yesterday = datetime.now() - timedelta(days=1)
        recent_sessions = query.filter(PDFImportSession.created_at >= yesterday).count()

        # 平均处理时间
        completed_with_time = query.filter(
            PDFImportSession.status == SessionStatus.COMPLETED,
            PDFImportSession.completed_at.isnot(None),
        ).all()

        avg_processing_time = 0
        if completed_with_time:
            total_time = sum(
                [
                    (s.completed_at - s.created_at).total_seconds()
                    for s in completed_with_time
                ]
            )
            avg_processing_time = total_time / len(completed_with_time)

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "completed_sessions": completed_sessions,
            "failed_sessions": failed_sessions,
            "recent_sessions_24h": recent_sessions,
            "average_processing_time_seconds": round(avg_processing_time, 2),
            "success_rate": round(completed_sessions / max(total_sessions, 1) * 100, 2),
        }

    def register_background_task(self, session_id: str, task: asyncio.Task):
        """注册后台任务"""
        self.active_tasks[session_id] = task

    def unregister_background_task(self, session_id: str):
        """取消注册后台任务"""
        if session_id in self.active_tasks:
            del self.active_tasks[session_id]


# 创建全局实例
pdf_session_service = PDFSessionService()
