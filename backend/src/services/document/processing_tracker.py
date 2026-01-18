#!/usr/bin/env python3
"""
PDF 处理追踪器
提供统一的进度追踪、错误处理和日志记录功能
"""

import logging
import time
import traceback
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy.orm import Session

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore

from ...enums.status import TaskExecutionStatus
from ...models.pdf_import_session import (
    PDFImportSession,
    ProcessingStep,
    SessionLog,
    SessionStatus,
)
from .base import ErrorCode, ExtractionResult

logger = logging.getLogger(__name__)


class ProcessingTracker:
    """
    PDF 处理进度追踪器

    提供统一的接口来更新处理状态、记录日志和处理错误
    """

    def __init__(self, db: Session, session_id: str):
        """
        初始化追踪器

        Args:
            db: 数据库会话
            session_id: PDF 导入会话 ID
        """
        self.db = db
        self.session_id = session_id
        self._start_time = time.time()
        self._step_start_time: float | None = None

    def get_session(self) -> PDFImportSession | None:
        """
        获取 PDF 导入会话

        Returns:
            PDFImportSession 会话对象，如果不存在则返回 None
        """
        return (
            self.db.query(PDFImportSession)
            .filter(PDFImportSession.session_id == self.session_id)
            .first()
        )

    def update_progress(
        self,
        progress: int,
        status: SessionStatus | None = None,
        step: ProcessingStep | None = None,
        message: str | None = None,
    ) -> bool:
        """
        更新处理进度

        Args:
            progress: 进度百分比 (0-100)
            status: 会话状态（可选）
            step: 当前处理步骤（可选）
            message: 状态消息（可选）

        Returns:
            bool: 是否更新成功
        """
        try:
            session = self.get_session()
            if not session:
                logger.warning(f"Session {self.session_id} not found")
                return False

            # 更新进度
            session.progress_percentage = float(progress)

            if status:
                session.status = status

            if step:
                session.current_step = step

            self.db.commit()

            # 记录日志
            log_message = message or f"Progress: {progress}%"
            logger.info(f"Session {self.session_id}: {log_message}")

            return True

        except Exception as e:
            logger.error(f"Failed to update progress for {self.session_id}: {e}")
            self.db.rollback()
            return False

    def start_step(
        self,
        step: ProcessingStep,
        message: str | None = None,
    ) -> bool:
        """
        开始一个处理步骤

        Args:
            step: 处理步骤
            message: 步骤描述

        Returns:
            bool: 是否成功
        """
        self._step_start_time = time.time()

        # 创建会话日志
        return self._create_log(
            step=step,
            status="started",
            message=message or f"Started {step.value}",
        )

    def complete_step(
        self,
        step: ProcessingStep,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """
        完成一个处理步骤

        Args:
            step: 处理步骤
            message: 步骤描述
            details: 详细信息

        Returns:
            bool: 是否成功
        """
        duration_ms = None
        if self._step_start_time:
            duration_ms = (time.time() - self._step_start_time) * 1000
            self._step_start_time = None

        return self._create_log(
            step=step,
            status="completed",
            message=message or f"Completed {step.value}",
            details=details,
            duration_ms=duration_ms,
        )

    def fail_step(
        self,
        step: ProcessingStep,
        error_message: str,
        error_code: ErrorCode | None = None,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """
        标记步骤失败

        Args:
            step: 处理步骤
            error_message: 错误消息
            error_code: 错误码
            details: 错误详情

        Returns:
            bool: 是否成功
        """
        duration_ms = None
        if self._step_start_time:
            duration_ms = (time.time() - self._step_start_time) * 1000
            self._step_start_time = None

        # 记录失败日志
        error_details = details or {}
        if error_code:
            error_details["error_code"] = error_code.value

        return self._create_log(
            step=step,
            status="failed",
            message=error_message,
            details=error_details,
            duration_ms=duration_ms,
        )

    def handle_failure(
        self,
        error: Exception,
        step: ProcessingStep | None = None,
        context: dict[str, Any] | None = None,
        retry_suggested: bool = False,
    ) -> None:
        """
        统一错误处理

        Args:
            error: 异常对象
            step: 失败的步骤
            context: 错误上下文
            retry_suggested: 是否建议重试
        """
        error_type = type(error).__name__
        error_message = str(error)
        error_traceback = traceback.format_exc()

        # 构建错误详情
        error_details = {
            "error_type": error_type,
            "error_message": error_message,
            "traceback": error_traceback,
            "context": context or {},
            "retry_suggested": retry_suggested,
            "timestamp": datetime.now().isoformat(),
        }

        # 记录详细错误日志
        logger.error(
            f"Processing failed for session {self.session_id}: {error_details}",
            exc_info=error,
        )

        # 更新会话状态为失败
        session = self.get_session()
        if session:
            session.status = SessionStatus.FAILED
            session.error_message = error_message
            session.progress_percentage = 0.0
            self.db.commit()

        # 记录失败日志
        if step:
            self.fail_step(
                step=step,
                error_message=error_message,
                details=error_details,
            )

    def save_result(
        self,
        result: ExtractionResult,
        step: ProcessingStep = ProcessingStep.INFO_EXTRACTION,
    ) -> bool:
        """
        保存提取结果

        Args:
            result: 提取结果
            step: 处理步骤

        Returns:
            bool: 是否成功
        """
        try:
            session = self.get_session()
            if not session:
                return False

            # 保存处理结果
            session.extracted_data = result.extracted_fields
            session.processing_result = result.model_dump()
            session.confidence_score = result.confidence
            session.processing_method = result.extraction_method.value

            # 如果有错误，保存错误信息
            if not result.success and result.error:
                session.error_message = result.error

            self.db.commit()

            # 记录完成日志
            if result.success:
                self.complete_step(
                    step=step,
                    message=f"Extraction completed with confidence {result.confidence:.2f}",
                    details={
                        "method": result.extraction_method.value,
                        "fields_extracted": len(result.extracted_fields),
                        "processing_time_ms": result.processing_time_ms,
                    },
                )
            else:
                self.fail_step(
                    step=step,
                    error_message=result.error or "Extraction failed",
                    details={
                        "error_code": result.error_code.value
                        if result.error_code
                        else None
                    },
                )

            return True

        except Exception as e:
            logger.error(f"Failed to save result for {self.session_id}: {e}")
            self.db.rollback()
            return False

    def _create_log(
        self,
        step: ProcessingStep,
        status: str,
        message: str,
        details: dict[str, Any] | None = None,
        duration_ms: float | None = None,
    ) -> bool:
        """
        创建会话日志

        Args:
            step: 处理步骤
            status: 状态
            message: 消息
            details: 详细信息
            duration_ms: 持续时间

        Returns:
            bool: 是否成功
        """
        try:
            log = SessionLog(
                session_id=self.session_id,
                step=step,
                status=status,
                message=message,
                details=details,
                duration_ms=duration_ms,
            )
            self.db.add(log)
            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to create log for {self.session_id}: {e}")
            self.db.rollback()
            return False


def track_processing_step(
    db: Session,
    session_id: str,
    step: ProcessingStep,
):
    """
    处理步骤追踪装饰器

    自动记录步骤的开始、完成和失败

    Args:
        db: 数据库会话
        session_id: PDF 导入会话 ID
        step: 处理步骤

    Example:
        @track_processing_step(db, session_id, ProcessingStep.TEXT_EXTRACTION)
        async def extract_text(pdf_path: str):
            # 处理逻辑
            pass
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracker = ProcessingTracker(db, session_id)

            # 开始步骤
            tracker.start_step(step)

            try:
                # 执行处理函数
                result = await func(*args, **kwargs)

                # 完成步骤
                if isinstance(result, ExtractionResult):
                    if result.success:
                        tracker.complete_step(
                            step, details={"result": result.model_dump()}
                        )
                    else:
                        tracker.fail_step(step, result.error or "Processing failed")
                else:
                    tracker.complete_step(step)

                return result

            except Exception as e:
                # 处理失败
                tracker.handle_failure(e, step=step)
                raise

        return wrapper

    return decorator


class ProgressCallback:
    """进度回调协议 - 用于批处理进度更新"""

    def __call__(
        self,
        progress: int,
        message: str,
        stage: str | None = None,
    ) -> None:
        """
        更新进度回调

        Args:
            progress: 进度百分比 (0-100)
            message: 状态消息
            stage: 当前阶段（可选）
        """
        pass


# ============================================================================
# 批处理状态追踪器 (支持 Redis 持久化)
# ============================================================================


class BatchStatusTracker:
    """
    批处理状态追踪器 - 使用 Redis 持久化

    如果 Redis 不可用，自动回退到内存存储
    """

    def __init__(
        self,
        redis_host: str | None = None,
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: str | None = None,
        ttl_seconds: int = 86400,  # 24小时
    ):
        """
        初始化批处理状态追踪器

        Args:
            redis_host: Redis 主机地址
            redis_port: Redis 端口
            redis_db: Redis 数据库编号
            redis_password: Redis 密码
            ttl_seconds: 数据过期时间（秒）
        """
        self.ttl = ttl_seconds
        self._use_redis = False
        self._redis_client = None
        self._fallback_store: dict[str, dict[str, Any]] = {}

        # 尝试连接 Redis
        if REDIS_AVAILABLE and redis_host:
            try:
                self._redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                # 测试连接
                self._redis_client.ping()
                self._use_redis = True
                logger.info(
                    f"BatchStatusTracker: Using Redis at {redis_host}:{redis_port}"
                )
            except Exception as e:
                logger.warning(
                    f"Redis connection failed: {e}, falling back to memory storage"
                )
                self._redis_client = None
        else:
            logger.info("Redis not available, using in-memory batch status storage")

    def _get_key(self, batch_id: str) -> str:
        """获取 Redis 键名"""
        return f"batch:status:{batch_id}"

    def create_batch(
        self,
        batch_id: str,
        total: int,
        user_id: int | None = None,
        organization_id: int | None = None,
        **metadata,
    ) -> bool:
        """
        创建批处理记录

        Args:
            batch_id: 批处理 ID
            total: 总文件数
            user_id: 用户 ID
            organization_id: 组织 ID
            **metadata: 其他元数据

        Returns:
            bool: 是否创建成功
        """
        batch_data = {
            "batch_id": batch_id,
            "status": "pending",
            "total": str(total),
            "processed": "0",
            "failed": "0",
            "user_id": str(user_id) if user_id else "",
            "organization_id": str(organization_id) if organization_id else "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            **{
                k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                for k, v in metadata.items()
            },
        }

        if self._use_redis and self._redis_client:
            try:
                key = self._get_key(batch_id)
                self._redis_client.hset(key, mapping=batch_data)
                self._redis_client.expire(key, self.ttl)
                logger.debug(f"Batch {batch_id} created in Redis")
                return True
            except Exception as e:
                logger.error(
                    f"Failed to create batch in Redis: {e}, falling back to memory"
                )
                self._use_redis = False

        # 回退到内存存储
        self._fallback_store[batch_id] = {
            **batch_data,
            **{
                k: int(v) if isinstance(v, str) and v.isdigit() else v
                for k, v in batch_data.items()
            },
        }
        return True

    def update_progress(
        self,
        batch_id: str,
        processed: int | None = None,
        failed: int | None = None,
        status: str | None = None,
    ) -> bool:
        """
        更新批处理进度

        Args:
            batch_id: 批处理 ID
            processed: 已处理数量增量
            failed: 失败数量增量
            status: 新状态

        Returns:
            bool: 是否更新成功
        """
        if self._use_redis and self._redis_client:
            try:
                key = self._get_key(batch_id)
                # 检查批处理是否存在
                if not self._redis_client.exists(key):
                    logger.warning(f"Batch {batch_id} not found in Redis")
                    return False

                # 更新字段
                updates = {"updated_at": datetime.now().isoformat()}
                if processed is not None:
                    self._redis_client.hincrby(key, "processed", processed)
                if failed is not None:
                    self._redis_client.hincrby(key, "failed", failed)
                if status:
                    self._redis_client.hset(key, "status", status)
                    if status == "completed":
                        self._redis_client.hset(
                            key, "completed_at", datetime.now().isoformat()
                        )

                self._redis_client.hset(key, "updated_at", updates["updated_at"])
                return True
            except Exception as e:
                logger.error(f"Failed to update batch in Redis: {e}")
                return False

        # 回退到内存存储
        if batch_id in self._fallback_store:
            if processed is not None:
                self._fallback_store[batch_id]["processed"] = (
                    self._fallback_store[batch_id].get("processed", 0) + processed
                )
            if failed is not None:
                self._fallback_store[batch_id]["failed"] = (
                    self._fallback_store[batch_id].get("failed", 0) + failed
                )
            if status:
                self._fallback_store[batch_id]["status"] = status
                if status == "completed":
                    self._fallback_store[batch_id]["completed_at"] = (
                        datetime.now().isoformat()
                    )
            self._fallback_store[batch_id]["updated_at"] = datetime.now().isoformat()
            return True
        return False

    def get_status(self, batch_id: str) -> dict[str, Any] | None:
        """
        获取批处理状态

        Args:
            batch_id: 批处理 ID

        Returns:
            批处理状态字典，不存在则返回 None
        """
        if self._use_redis and self._redis_client:
            try:
                key = self._get_key(batch_id)
                data: dict[str, Any] = cast(
                    dict[str, Any], self._redis_client.hgetall(key)
                )
                if not data:
                    return None
                # 转换数字类型 (Redis 返回的值都是字符串)
                result: dict[str, Any] = {}
                for k, v in data.items():
                    if isinstance(v, str) and v.isdigit():
                        result[k] = int(v)
                    else:
                        result[k] = v
                return result
            except Exception as e:
                logger.error(f"Failed to get batch from Redis: {e}")
                return None

        # 回退到内存存储
        return self._fallback_store.get(batch_id)

    def set_status(self, batch_id: str, status: str) -> bool:
        """
        设置批处理状态

        Args:
            batch_id: 批处理 ID
            status: 新状态

        Returns:
            bool: 是否设置成功
        """
        return self.update_progress(batch_id, status=status)

    def delete_batch(self, batch_id: str) -> bool:
        """
        删除批处理记录

        Args:
            batch_id: 批处理 ID

        Returns:
            bool: 是否删除成功
        """
        if self._use_redis and self._redis_client:
            try:
                key = self._get_key(batch_id)
                return bool(self._redis_client.delete(key))
            except Exception as e:
                logger.error(f"Failed to delete batch from Redis: {e}")
                return False

        # 回退到内存存储
        return self._fallback_store.pop(batch_id, None) is not None

    def list_batches(
        self, status_filter: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        列出批处理记录

        Args:
            status_filter: 状态过滤
            limit: 返回数量限制

        Returns:
            批处理记录列表
        """
        if self._use_redis and self._redis_client:
            try:
                # 搜索所有批处理键
                keys = []
                for key in self._redis_client.scan_iter(match="batch:status:*"):
                    keys.append(key)

                batches = []
                for key in keys[: limit * 2]:  # 多获取一些用于过滤
                    data: dict[str, Any] = cast(
                        dict[str, Any], self._redis_client.hgetall(key)
                    )
                    if not data:
                        continue
                    # Redis 返回的值都是字符串，转换数字类型
                    batch: dict[str, Any] = {}
                    for k, v in data.items():
                        if isinstance(v, str) and v.isdigit():
                            batch[k] = int(v)
                        else:
                            batch[k] = v
                    if status_filter is None or batch.get("status") == status_filter:
                        batches.append(batch)
                    if len(batches) >= limit:
                        break

                # 按创建时间倒序
                batches.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                return batches[:limit]
            except Exception as e:
                logger.error(f"Failed to list batches from Redis: {e}")

        # 回退到内存存储
        batches = list(self._fallback_store.values())
        if status_filter:
            batches = [b for b in batches if b.get("status") == status_filter]
        batches.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return batches[:limit]

    def cleanup_old_batches(self, older_than_hours: int = 24) -> int:
        """
        清理旧的批处理记录

        Args:
            older_than_hours: 清理多少小时前的记录

        Returns:
            清理的数量
        """
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        cleaned = 0

        if self._use_redis and self._redis_client:
            # Redis 通过 TTL 自动清理，这里主要处理内存回退
            pass

        # 清理内存回退存储
        to_delete = []
        for batch_id, batch in self._fallback_store.items():
            created_at = batch.get("created_at")
            if created_at:
                try:
                    created_dt = datetime.fromisoformat(created_at)
                    if created_dt < cutoff_time:
                        to_delete.append(batch_id)
                except ValueError:
                    continue

        for batch_id in to_delete:
            self.delete_batch(batch_id)
            cleaned += 1

        return cleaned

    def get_stats(self) -> dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        stats: dict[str, Any] = {
            "storage_type": "redis" if self._use_redis else "memory",
            "total_batches": 0,
            "active_batches": 0,
            "completed_batches": 0,
            "failed_batches": 0,
        }

        if self._use_redis and self._redis_client:
            try:
                keys = list(self._redis_client.scan_iter(match="batch:status:*"))
                stats["total_batches"] = len(keys)
                # 统计各状态数量
                active_count = 0
                completed_count = 0
                failed_count = 0
                for key in keys:
                    status = self._redis_client.hget(key, "status")
                    if (
                        status == TaskExecutionStatus.PENDING.value
                        or status == TaskExecutionStatus.RUNNING.value
                    ):
                        active_count += 1
                    elif status == TaskExecutionStatus.COMPLETED.value:
                        completed_count += 1
                    elif status == TaskExecutionStatus.FAILED.value:
                        failed_count += 1
                stats["active_batches"] = active_count
                stats["completed_batches"] = completed_count
                stats["failed_batches"] = failed_count
            except Exception as e:
                logger.error(f"Failed to get stats from Redis: {e}")
        else:
            batches = list(self._fallback_store.values())
            stats["total_batches"] = len(batches)
            active_count = 0
            completed_count = 0
            failed_count = 0
            for batch in batches:
                status = batch.get("status")
                if status in ("pending", "processing"):
                    active_count += 1
                elif status == "completed":
                    completed_count += 1
                elif status == "failed":
                    failed_count += 1
            stats["active_batches"] = active_count
            stats["completed_batches"] = completed_count
            stats["failed_batches"] = failed_count

        return stats


class TrackerProgressCallback:
    """
    追踪器进度回调类
    用于在处理过程中报告进度到 ProcessingTracker
    """

    def __init__(self, tracker: ProcessingTracker):
        """
        初始化进度回调

        Args:
            tracker: 处理追踪器
        """
        self.tracker = tracker
        self._current_progress = 0

    def __call__(
        self,
        progress: int,
        message: str,
        stage: str | None = None,
    ) -> None:
        """
        报告进度

        Args:
            progress: 进度百分比 (0-100)
            message: 状态消息
            stage: 当前阶段
        """
        self._current_progress = progress
        self.tracker.update_progress(
            progress=progress,
            message=message,
        )

        # 记录关键阶段
        if stage in ("start", "complete"):
            logger.info(f"Session {self.tracker.session_id}: {stage} - {message}")

    def get_current_progress(self) -> int:
        """获取当前进度"""
        return self._current_progress
