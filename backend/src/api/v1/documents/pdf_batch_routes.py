#!/usr/bin/env python3
"""
PDF 批量导入 API 路由
支持多文件并发上传和批处理状态追踪
"""

import asyncio
import logging
import os
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ....constants.file_size_constants import DEFAULT_MAX_FILE_SIZE
from ....core.config import settings
from ....core.exception_handler import (
    BusinessValidationError,
    bad_request,
    not_found,
    service_unavailable,
)
from ....core.response_handler import success_response
from ....crud.pdf_import_session import PDFImportSessionCRUD
from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....services.document.pdf_import_service import PDFImportService
from ....services.document.processing_tracker import BatchStatusTracker
from ....utils.file_security import generate_safe_filename

logger = logging.getLogger(__name__)

# 批量处理配置
MAX_BATCH_SIZE = int(os.getenv("PDF_MAX_BATCH_SIZE", "10"))
MAX_CONCURRENT_BATCHES = int(os.getenv("PDF_MAX_CONCURRENT_BATCHES", "2"))

# 批处理状态追踪器（支持 Redis 持久化）
_batch_tracker: BatchStatusTracker | None = None
_batch_lock: asyncio.Lock = asyncio.Lock()
_monitor_tasks: dict[str, asyncio.Task[None]] = {}


def _get_batch_tracker() -> BatchStatusTracker:
    """获取批处理状态追踪器单例"""
    global _batch_tracker
    if _batch_tracker is None:
        _batch_tracker = BatchStatusTracker(
            redis_host=settings.REDIS_HOST if settings.REDIS_ENABLED else None,
            redis_port=settings.REDIS_PORT,
            redis_db=settings.REDIS_DB,
            redis_password=settings.REDIS_PASSWORD,
        )
    return _batch_tracker


router = APIRouter(prefix="/pdf-import/batch", tags=["PDF批量导入"])


# ============================================================================
# 批处理数据模型
# ============================================================================


class BatchStatus:
    """批处理状态枚举"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# 辅助函数
# ============================================================================


def _generate_batch_id() -> str:
    """生成唯一的批处理 ID"""
    return f"batch-{uuid.uuid4().hex[:12]}"


def _get_batch_status(batch_id: str) -> dict[str, Any] | None:
    """获取批处理状态"""
    tracker = _get_batch_tracker()
    result = tracker.get_status(batch_id)
    return result if isinstance(result, dict) else None


def _update_batch_status(batch_id: str, status: str, **updates: Any) -> None:
    """更新批处理状态"""
    tracker = _get_batch_tracker()
    tracker.update_progress(batch_id, status=status)
    # 更新其他字段通过 tracker.set_status 实现
    # 附加字段存储在 metadata 中


def _track_monitor_task(batch_id: str, task: asyncio.Task[None]) -> None:
    """记录监控任务，便于后续查询/取消"""
    _monitor_tasks[batch_id] = task


def _untrack_monitor_task(batch_id: str) -> None:
    """移除监控任务记录"""
    _monitor_tasks.pop(batch_id, None)


def _on_monitor_task_done(task: asyncio.Task[None], batch_id: str) -> None:
    """处理监控任务结束（清理记录并处理异常）"""
    _untrack_monitor_task(batch_id)
    _handle_task_exception(task, batch_id)


def _calculate_batch_progress(batch_id: str) -> dict[str, Any]:
    """计算批处理进度"""
    batch = _get_batch_status(batch_id)
    if not batch:
        return {"completed": 0, "total": 0, "percentage": 0, "failed": 0}

    total = int(batch.get("total", 0))
    processed = int(batch.get("processed", 0))
    failed = int(batch.get("failed", 0))

    return {
        "total": total,
        "completed": processed,
        "failed": failed,
        "processing": 0,  # 从数据库查询
        "pending": max(0, total - processed - failed),
    }


# ============================================================================
# API 端点
# ============================================================================


@router.post("/upload")
async def batch_upload_pdfs(
    db: Annotated[Session, Depends(get_db)],
    files: Annotated[list[UploadFile], File(...)],
    organization_id: Annotated[int | None, Form()] = None,
    prefer_ocr: Annotated[bool, Form()] = False,
    prefer_vision: Annotated[bool, Form()] = False,
    auto_confirm: Annotated[bool, Form()] = False,
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    批量上传 PDF 文件进行智能识别

    **功能说明**:
    - 支持同时上传最多 10 个 PDF 文件
    - 每个文件独立处理，互不影响
    - 返回批处理 ID 用于查询整体进度

    **Args**:
        - files: PDF 文件列表（最多 10 个）
        - organization_id: 所属组织 ID
        - prefer_ocr: 优先使用 OCR 文字识别
        - prefer_vision: 优先使用视觉模型
        - auto_confirm: 自动确认（跳过人工验证）

    **Returns**:
        ```json
        {
            "success": true,
            "batch_id": "batch-abc123",
            "session_count": 5,
            "session_ids": ["session-1", "session-2", ...],
            "estimated_time_minutes": 5,
            "message": "批处理任务已创建"
        }
        ```

    **错误处理**:
        - 400: 文件数量超过限制或文件格式错误
        - 413: 单个文件大小超过 50MB
        - 503: 系统繁忙（并发批处理达到上限）
    """
    # 验证文件数量
    if len(files) > MAX_BATCH_SIZE:
        raise bad_request(f"文件数量超过限制，最多支持 {MAX_BATCH_SIZE} 个文件")

    # 验证并发限制
    tracker = _get_batch_tracker()
    stats = tracker.get_stats()
    if stats["active_batches"] >= MAX_CONCURRENT_BATCHES:
        raise service_unavailable(
            f"系统繁忙，同时最多支持 {MAX_CONCURRENT_BATCHES} 个批处理任务"
        )

    # 生成批处理 ID
    batch_id = _generate_batch_id()

    # 验证文件
    valid_files: list[tuple[UploadFile, bytes, int, str]] = []
    for file in files:
        if file.filename is None or not file.filename.lower().endswith(".pdf"):
            logger.warning(f"跳过非 PDF 文件: {file.filename}")
            continue

        # 检查文件大小
        content = await file.read()
        file_size = len(content)
        await file.seek(0)  # 重置文件指针

        max_size = DEFAULT_MAX_FILE_SIZE
        if file_size > max_size:
            logger.warning(
                f"文件 {file.filename} 大小 {file_size / 1024 / 1024:.1f}MB 超过限制"
            )
            continue

        try:
            safe_filename = generate_safe_filename(
                file.filename, prefix=batch_id, allowed_extensions=["pdf"]
            )
        except BusinessValidationError as e:
            logger.warning(f"文件名不安全，已跳过: {file.filename} ({e})")
            continue

        valid_files.append((file, content, file_size, safe_filename))

    if not valid_files:
        raise bad_request("没有有效的 PDF 文件（请检查文件格式和大小）")

    # 初始化批处理状态（使用 BatchStatusTracker）
    tracker.create_batch(
        batch_id=batch_id,
        total=len(valid_files),
        organization_id=organization_id,
        prefer_ocr=prefer_ocr,
        prefer_vision=prefer_vision,
        auto_confirm=auto_confirm,
    )

    # 处理每个文件
    service = PDFImportService()
    session_ids: list[str] = []

    for file, content, file_size, safe_filename in valid_files:
        try:
            # 保存临时文件
            temp_dir = "uploads/temp"
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, safe_filename)

            with open(temp_path, "wb") as f:
                f.write(content)

            # 创建导入会话
            session_id = f"session-{uuid.uuid4().hex[:12]}"
            processing_options: dict[str, Any] = {
                "prefer_ocr": prefer_ocr,
                "prefer_vision": prefer_vision,
                "auto_confirm": auto_confirm,
            }
            service.create_import_session(
                db,
                session_id=session_id,
                original_filename=file.filename or "unknown.pdf",
                file_size=file_size,
                file_path=temp_path,
                content_type="application/pdf",
                organization_id=organization_id,
                processing_options=processing_options,
            )

            await service.process_pdf_file(
                db=db,
                session_id=session_id,
                organization_id=organization_id,
                file_size=file_size,
                file_path=temp_path,
                content_type="application/pdf",
                processing_options=processing_options,
            )

            session_ids.append(session_id)

            logger.info(
                f"Batch {batch_id}: Started processing {file.filename} -> {session_id}"
            )

        except Exception as e:
            logger.error(f"Failed to start processing for {file.filename}: {e}")
            tracker.update_progress(batch_id, failed=1)
            continue

    # 更新批处理状态为处理中
    tracker.set_status(batch_id, BatchStatus.PROCESSING)

    # 启动后台监控任务（带异常处理）
    monitor_task = asyncio.create_task(_monitor_batch_progress(batch_id, db))
    _track_monitor_task(batch_id, monitor_task)
    monitor_task.add_done_callback(lambda t: _on_monitor_task_done(t, batch_id))

    response: JSONResponse = success_response(
        data={
            "batch_id": batch_id,
            "session_count": len(session_ids),
            "session_ids": session_ids,
            "status": BatchStatus.PROCESSING,
            "estimated_time_minutes": max(1, len(session_ids) // 2),
        },
        message=f"已创建批处理任务，包含 {len(session_ids)} 个文件",
    )
    return response


@router.get("/status/{batch_id}")
def get_batch_status(
    batch_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    """
    查询批处理状态

    **Args**:
        - batch_id: 批处理 ID

    **Returns**:
        ```json
        {
            "success": true,
            "batch_status": {
                "batch_id": "batch-abc123",
                "status": "processing",
                "total": 5,
                "completed": 2,
                "failed": 0,
                "processing": 3,
                "pending": 0,
                "percentage": 40,
                "sessions": [
                    {
                        "session_id": "session-1",
                        "file_name": "contract1.pdf",
                        "status": "completed",
                        "progress": 100
                    },
                    ...
                ]
            }
        }
        ```
    """
    batch = _get_batch_status(batch_id)
    if not batch:
        raise not_found("批处理任务不存在", resource_id=batch_id)

    # 获取各会话状态
    session_crud = PDFImportSessionCRUD()
    session_statuses: list[dict[str, Any]] = []
    session_ids = [str(session_id) for session_id in batch.get("session_ids", [])]
    session_map = session_crud.get_session_map(db, session_ids)
    for session_id in session_ids:
        session = session_map.get(session_id)
        if session:
            session_statuses.append(
                {
                    "session_id": session_id,
                    "file_name": session.original_filename,
                    "status": session.status.value,
                    "progress": session.progress_percentage,
                    "error": session.error_message,
                }
            )

    # 计算进度
    progress_info = _calculate_batch_progress(batch_id)
    total = progress_info["total"]
    completed = progress_info["completed"]
    percentage = int((completed / total * 100) if total > 0 else 0)

    response: JSONResponse = success_response(
        data={
            "batch_status": {
                "batch_id": batch_id,
                "status": batch["status"],
                **progress_info,
                "percentage": percentage,
                "sessions": session_statuses,
                "created_at": batch.get("created_at"),
                "updated_at": batch.get("updated_at"),
            }
        },
        message="批处理状态查询成功",
    )
    return response


@router.get("/list")
def list_batches(
    status_filter: str | None = None,
    limit: int = 20,
) -> JSONResponse:
    """
    列出批处理任务

    **Args**:
        - status_filter: 状态过滤（pending, processing, completed, failed）
        - limit: 返回数量限制

    **Returns**:
        ```json
        {
            "success": true,
            "batches": [
                {
                    "batch_id": "batch-abc123",
                    "status": "processing",
                    "total": 5,
                    "completed": 2,
                    "created_at": "2024-01-10T10:30:00"
                },
                ...
            ]
        }
        ```
    """
    tracker = _get_batch_tracker()
    batches = tracker.list_batches(status_filter=status_filter, limit=limit)

    # 简化返回数据
    result_batches: list[dict[str, Any]] = []
    for batch in batches:
        result_batches.append(
            {
                "batch_id": batch["batch_id"],
                "status": batch["status"],
                "total": int(batch.get("total", 0)),
                "completed": int(batch.get("processed", 0)),
                "failed": int(batch.get("failed", 0)),
                "created_at": batch.get("created_at"),
                "updated_at": batch.get("updated_at"),
            }
        )

    response: JSONResponse = success_response(
        data={"batches": result_batches, "count": len(result_batches)},
        message="批处理列表查询成功",
    )
    return response


@router.post("/cancel/{batch_id}")
async def cancel_batch(
    batch_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    """
    取消批处理任务

    **Args**:
        - batch_id: 批处理 ID

    **Returns**:
        ```json
        {
            "success": true,
            "cancelled_count": 3,
            "message": "已取消 3 个处理中的任务"
        }
        ```
    """
    batch = _get_batch_status(batch_id)
    if not batch:
        raise not_found("批处理任务不存在", resource_id=batch_id)

    if batch["status"] in [
        BatchStatus.COMPLETED,
        BatchStatus.FAILED,
        BatchStatus.CANCELLED,
    ]:
        raise bad_request("批处理任务已完成或已取消，无法取消")

    # 取消所有处理中的会话
    service = PDFImportService()
    session_crud = PDFImportSessionCRUD()
    cancelled_count = 0

    session_ids = [str(session_id) for session_id in batch.get("session_ids", [])]
    session_map = session_crud.get_session_map(db, session_ids)
    for session_id in session_ids:
        session = session_map.get(session_id)
        if session and session.is_processing:
            await service.cancel_processing(
                db=db,
                session_id=session_id,
                reason=f"Batch {batch_id} cancelled by user",
            )
            cancelled_count += 1

    # 更新批处理状态
    _update_batch_status(batch_id, BatchStatus.CANCELLED)

    monitor_task = _monitor_tasks.get(batch_id)
    if monitor_task and not monitor_task.done():
        monitor_task.cancel()

    response: JSONResponse = success_response(
        data={"cancelled_count": cancelled_count},
        message=f"已取消 {cancelled_count} 个处理中的任务",
    )
    return response


@router.delete("/cleanup")
def cleanup_completed_batches(
    older_than_hours: int = 24,
) -> JSONResponse:
    """
    清理已完成的批处理记录

    **Args**:
        - older_than_hours: 清理多少小时前的记录（默认 24 小时）

    **Returns**:
        ```json
        {
            "success": true,
            "cleaned_count": 5,
            "message": "已清理 5 条批处理记录"
        }
        ```
    """
    tracker = _get_batch_tracker()
    cleaned_count = tracker.cleanup_old_batches(older_than_hours=older_than_hours)

    response: JSONResponse = success_response(
        data={"cleaned_count": cleaned_count},
        message=f"已清理 {cleaned_count} 条批处理记录",
    )
    return response


# ============================================================================
# 后台任务
# ============================================================================


def _handle_task_exception(task: asyncio.Task[None], batch_id: str) -> None:
    """
    处理后台任务异常

    当后台任务出现异常时，记录日志并更新批处理状态
    """
    try:
        exception = task.exception()
        if exception:
            logger.error(
                f"Batch {batch_id} monitoring task failed: {exception}",
                exc_info=exception,
            )

            # 更新批处理状态为失败
            async def _update_failed_status() -> None:
                _update_batch_status(
                    batch_id, BatchStatus.FAILED, error_message=str(exception)
                )
                return None

            # 在新的事件循环中运行（如果当前没有运行中的循环）
            try:
                asyncio.get_running_loop()
                asyncio.create_task(_update_failed_status())
            except RuntimeError:
                # 没有运行中的事件循环，创建一个新的
                asyncio.run(_update_failed_status())
    except asyncio.CancelledError:
        logger.info(f"Batch {batch_id} monitoring task was cancelled")
    except Exception as e:
        logger.error(f"Error handling task exception for batch {batch_id}: {e}")


async def _monitor_batch_progress(batch_id: str, db: Session) -> None:
    """
    监控批处理进度

    定期检查所有会话状态，更新批处理整体状态

    注意: db 参数仅用于创建新的会话上下文，不直接使用传入的会话
    """
    from ....database import _get_database_manager

    service = PDFImportService()
    db_manager = _get_database_manager()
    tracker = _get_batch_tracker()

    while True:
        batch = _get_batch_status(batch_id)
        if not batch:
            break

        # 统计各状态数量
        completed = 0
        failed = 0
        processing = 0
        pending = 0

        # 使用独立的数据库会话进行查询
        with db_manager.get_session() as session:
            for session_id in batch.get("session_ids", []):
                status_result = await service.get_session_status(session, session_id)
                if status_result.get("success"):
                    session_status = status_result["session_status"]
                    status = session_status.get("status")

                    if status == "completed":
                        completed += 1
                    elif status == "failed":
                        failed += 1
                    elif status == "processing":
                        processing += 1
                    else:
                        pending += 1

        # 更新统计到 tracker（增量更新，避免重复累加）
        total = len(batch.get("session_ids", []))
        current_processed = int(batch.get("processed", 0))
        current_failed = int(batch.get("failed", 0))
        delta_processed = max(0, completed - current_processed)
        delta_failed = max(0, failed - current_failed)
        if delta_processed or delta_failed:
            tracker.update_progress(
                batch_id,
                processed=delta_processed,
                failed=delta_failed,
            )

        # 判断是否全部完成
        if completed + failed >= total:
            # 批处理完成
            final_status = (
                BatchStatus.COMPLETED
                if failed == 0
                else BatchStatus.PARTIALLY_COMPLETED
            )
            tracker.set_status(batch_id, final_status)
            logger.info(
                f"Batch {batch_id} completed: {completed} succeeded, {failed} failed"
            )
            break

        # 等待后再次检查
        await asyncio.sleep(5)


# ============================================================================
# 健康检查
# ============================================================================


@router.get("/health")
def batch_health_check() -> JSONResponse:
    """
    批处理系统健康检查

    返回系统状态和配置信息
    """
    tracker = _get_batch_tracker()
    stats = tracker.get_stats()

    response: JSONResponse = success_response(
        data={
            "status": "healthy",
            "configuration": {
                "max_batch_size": MAX_BATCH_SIZE,
                "max_concurrent_batches": MAX_CONCURRENT_BATCHES,
            },
            "current_usage": {
                "active_batches": stats.get("active_batches", 0),
                "available_slots": MAX_CONCURRENT_BATCHES
                - stats.get("active_batches", 0),
                "total_stored_batches": stats.get("total_batches", 0),
            },
        },
        message="批处理系统运行正常",
    )
    return response
