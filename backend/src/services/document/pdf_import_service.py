#!/usr/bin/env python3
"""
PDF 导入服务
编排 PDF 处理流程，管理会话和后台任务

管线逻辑（提取、合并、持久化）见 pdf_import_pipeline.py。
"""

import asyncio
import logging
import os
import traceback
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.task_queue import get_task_queue  # 现有任务队列系统
from ...crud.pdf_import_session import pdf_import_session_crud
from ...crud.query_builder import PartyFilter
from ...models.pdf_import_session import PDFImportSession, ProcessingStep, SessionStatus

# Re-export so `src.services.document.pdf_import_service.contract_group_service`
# and `src.services.document.pdf_import_service.party_service` are patchable.
from ...services.contract.contract_group_service import (
    contract_group_service,  # noqa: F401
)
from ...services.party import party_service  # noqa: F401
from ...services.party_scope import resolve_user_party_filter
from .contract_extractor import ContractExtractor
from .llm_contract_extractor import get_llm_contract_extractor
from .pdf_import_pipeline import (
    _calculate_confidence,
    _calculate_extraction_rate,
    _fill_missing_fields_with_regex,
    _get_extracted_fields,
    _parse_date,
    cleanup_source_file,
    merge_results_legacy,
    merge_smart_results,
    persist_processing_error,
    persist_processing_result,
    process_background,
)

logger = logging.getLogger(__name__)

# 从环境变量读取并发限制
MAX_CONCURRENT_PDF_TASKS = int(os.getenv("PDF_MAX_CONCURRENT", "3"))


class PDFImportService:
    """
    PDF 导入服务

    职责:
    - 管理数据库会话
    - 调度异步处理任务
    - 整合文本/视觉提取逻辑
    - 并发控制和错误追踪
    """

    # 类级别的并发控制信号量
    _processing_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PDF_TASKS)
    # 显式跟踪活动任务数，避免访问私有属性
    _active_tasks = 0
    _active_tasks_lock = asyncio.Lock()

    def __init__(self) -> None:
        self.regex_extractor = ContractExtractor()
        self.llm_extractor = get_llm_contract_extractor()
        self.task_queue = get_task_queue()

    async def _resolve_party_filter(
        self,
        db: AsyncSession,
        *,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> PartyFilter | None:
        return await resolve_user_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
            logger=logger,
            allow_legacy_default_organization_fallback=False,
        )

    async def upload_file(self, file_content: bytes, filename: str) -> dict[str, Any]:
        """上传文件到临时目录"""
        import tempfile

        from ...utils.file_security import generate_safe_filename

        temp_dir = Path(tempfile.gettempdir())
        file_id = str(uuid.uuid4())
        safe_filename = generate_safe_filename(filename, file_id)
        temp_file_path = temp_dir / safe_filename

        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(file_content)

        logger.info(f"文件已上传到临时路径: {temp_file_path}")

        return {
            "file_path": str(temp_file_path),
            "filename": safe_filename,
            "original_filename": filename,
            "file_size": len(file_content),
        }

    async def create_import_session(
        self,
        db: AsyncSession,
        *,
        session_id: str,
        original_filename: str,
        file_size: int,
        file_path: str,
        content_type: str,
        organization_id: int | None,
        processing_options: dict[str, Any] | None = None,
    ) -> PDFImportSession:
        """创建PDF导入会话并持久化"""
        session = PDFImportSession()
        session.session_id = session_id
        session.original_filename = original_filename
        session.file_size = file_size
        session.file_path = file_path
        session.content_type = content_type
        session.organization_id = organization_id
        session.status = SessionStatus.UPLOADED
        session.current_step = ProcessingStep.FILE_UPLOAD
        session.progress_percentage = 0.0
        if processing_options is not None:
            session.processing_options = processing_options

        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @classmethod
    def get_available_slots(cls) -> int:
        """获取当前可用的处理槽位数"""
        return max(0, MAX_CONCURRENT_PDF_TASKS - cls._active_tasks)

    @classmethod
    def get_current_concurrent_count(cls) -> int:
        """获取当前正在处理的任务数"""
        return cls._active_tasks

    async def get_session_map_async(
        self,
        db: AsyncSession,
        session_ids: list[str],
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> dict[str, PDFImportSession]:
        """批量获取会话ID到会话对象映射。"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        return await pdf_import_session_crud.get_session_map_async(
            db,
            session_ids,
            party_filter=resolved_party_filter,
        )

    async def get_session_status(
        self,
        db: AsyncSession,
        session_id: str,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> dict[str, Any]:
        """获取会话状态"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        session = await pdf_import_session_crud.get_by_session_id_async(
            db,
            session_id,
            party_filter=resolved_party_filter,
        )
        if not session:
            return {"success": False, "error": "Session not found"}

        return {
            "success": True,
            "session_status": {
                "status": session.status.value,
                "progress": session.progress_percentage,
                "error": session.error_message,
                "result": session.processing_result,
                "current_step": session.current_step.value
                if session.current_step
                else None,
            },
        }

    async def process_pdf_file(
        self,
        db: AsyncSession,
        session_id: str,
        organization_id: int | None,
        file_size: int,
        file_path: str,
        content_type: str,
        processing_options: dict[str, Any],
    ) -> dict[str, Any]:
        """启动 PDF 处理流程（后台任务）"""
        session = await pdf_import_session_crud.get_by_session_id_async(db, session_id)
        if session:
            session.status = SessionStatus.PROCESSING
            session.current_step = ProcessingStep.FILE_UPLOAD
            session.progress_percentage = 0.0
            await db.commit()

        background_coro = self._process_background_safe(
            session_id, file_path, processing_options
        )
        task = asyncio.create_task(background_coro)
        if not isinstance(task, asyncio.Task):
            background_coro.close()

        task.add_done_callback(self._handle_task_completion)

        logger.info(
            f"Started processing for session {session_id} "
            f"(concurrent: {self.get_current_concurrent_count()}/{MAX_CONCURRENT_PDF_TASKS})"
        )

        return {"success": True, "message": "Processing started"}

    def _handle_task_completion(self, task: asyncio.Task[Any]) -> None:
        """任务完成回调 — 最后一道防线的错误日志记录"""
        try:
            task.result()
        except Exception as e:
            logger.error(
                f"Background task failed (caught by completion callback): {e}",
                exc_info=True,
                extra={"error_id": "TASK_COMPLETION_ERROR"},
            )

    async def _process_background_safe(
        self, session_id: str, file_path: str, options: dict[str, Any]
    ) -> None:
        """安全的后台处理包装器 — 信号量控制并发"""
        async with self._processing_semaphore:
            async with self._active_tasks_lock:
                self.__class__._active_tasks += 1

            logger.info(
                f"Acquired processing slot for {session_id} "
                f"(active: {self.get_current_concurrent_count()})"
            )

            try:
                await process_background(
                    session_id,
                    file_path,
                    options,
                    llm_extractor=self.llm_extractor,
                    regex_extractor=self.regex_extractor,
                )
            except Exception as e:
                logger.error(
                    f"Processing failed for {session_id}: {e}",
                    exc_info=True,
                    extra={
                        "error_id": "PDF_BACKGROUND_TASK_FAILED",
                        "session_id": session_id,
                    },
                )
                error_result = {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                }
                await persist_processing_error(session_id, error_result)
            finally:
                async with self._active_tasks_lock:
                    self.__class__._active_tasks -= 1
                logger.info(f"Released processing slot for {session_id}")

    # ── 向后兼容的实例方法代理 ─────────────────────────────────────────────

    def _parse_date(self, date_str: date | str | None) -> date | None:
        return _parse_date(date_str)

    def _merge_smart_results(
        self, smart_result: dict[str, Any], regex_result: dict[str, Any] | None
    ) -> dict[str, Any]:
        return merge_smart_results(smart_result, regex_result)

    def _merge_results(
        self, regex_result: dict[str, Any], llm_result: dict[str, Any]
    ) -> dict[str, Any]:
        return merge_results_legacy(regex_result, llm_result)

    def _cleanup_source_file(
        self, file_path: str | None, processing_options: dict[str, Any] | None
    ) -> bool:
        return cleanup_source_file(file_path, processing_options)

    # 向后兼容: 实例方法代理 — pipeline 提取/计算函数
    async def _persist_processing_result(
        self, session_id: str, result: dict[str, Any], processing_time_ms: float
    ) -> None:
        await persist_processing_result(session_id, result, processing_time_ms)

    async def _persist_processing_error(
        self, session_id: str, error_result: dict[str, Any]
    ) -> None:
        await persist_processing_error(session_id, error_result)

    def _get_extracted_fields(self, smart_result: dict[str, Any]) -> dict[str, Any]:
        return _get_extracted_fields(smart_result)

    def _fill_missing_fields_with_regex(
        self,
        extracted: dict[str, Any],
        regex_result: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], int, list[str]]:
        return _fill_missing_fields_with_regex(extracted, regex_result)

    def _calculate_extraction_rate(self, extracted_count: int) -> float:
        return _calculate_extraction_rate(extracted_count)

    def _calculate_confidence(
        self,
        smart_result: dict[str, Any],
        extraction_rate: float,
    ) -> float:
        return _calculate_confidence(smart_result, extraction_rate)

    # ── confirm_import ───────────────────────────────────────────────────

    async def confirm_import(
        self,
        db: AsyncSession,
        session_id: str,
        confirmed_data: dict[str, Any],
        user_id: str | int,
    ) -> dict[str, Any]:
        """用户验证数据后创建实际的资产/合同记录"""
        from .pdf_import_confirm import execute_confirm_import

        return await execute_confirm_import(db, session_id, confirmed_data, user_id)

    async def cancel_processing(
        self,
        db: AsyncSession,
        session_id: str,
        reason: str,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> dict[str, Any]:
        """取消处理"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        session = await pdf_import_session_crud.get_by_session_id_async(
            db,
            session_id,
            party_filter=resolved_party_filter,
        )

        if session and session.is_processing:
            session.status = SessionStatus.CANCELLED
            session.error_message = f"Cancelled: {reason}"
            await db.commit()

        return {"success": True, "message": "Session cancelled"}
