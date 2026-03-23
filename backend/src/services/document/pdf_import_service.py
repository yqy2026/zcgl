#!/usr/bin/env python3
"""
PDF 导入服务
编排 PDF 处理流程，管理会话和后台任务
"""

import asyncio
import logging
import os
import tempfile
import time
import traceback
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    BaseBusinessError,
    FileProcessingError,
)
from ...core.task_queue import get_task_queue  # 现有任务队列系统
from ...crud.pdf_import_session import pdf_import_session_crud
from ...crud.query_builder import PartyFilter
from ...models.contract_group import (
    ContractDirection,
    ContractLifecycleStatus,
    ContractReviewStatus,
    GroupRelationType,
    RevenueMode,
)
from ...models.pdf_import_session import PDFImportSession, ProcessingStep, SessionStatus
from ...schemas.contract_group import (
    AgencyDetailCreate,
    ContractCreate,
    ContractGroupCreate,
    ContractRentTermCreate,
    LeaseDetailCreate,
    SettlementRuleSchema,
)
from ...services.contract.contract_group_service import contract_group_service
from ...services.party import party_service
from ...services.party_scope import resolve_user_party_filter
from .contract_extractor import ContractExtractor
from .llm_contract_extractor import get_llm_contract_extractor

logger = logging.getLogger(__name__)

# 从环境变量读取并发限制
MAX_CONCURRENT_PDF_TASKS = int(os.getenv("PDF_MAX_CONCURRENT", "3"))


def _utcnow_naive() -> datetime:
    """返回 naive UTC 时间。"""
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized if normalized != "" else None


def _merge_confirmed_payload(confirmed_data: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    contract_data = confirmed_data.get("contract_data")
    if isinstance(contract_data, dict):
        merged.update(contract_data)
    for key, value in confirmed_data.items():
        if key != "contract_data":
            merged[key] = value
    return merged


def _parse_enum_member(enum_cls: Any, raw: Any) -> Any | None:
    if raw is None:
        return None
    if isinstance(raw, enum_cls):
        return raw
    normalized = _normalize_text(raw)
    if normalized is None:
        return None
    for member in enum_cls:
        if normalized == member.value or normalized.upper() == member.name:
            return member
    return None


def _parse_decimal(raw: Any, default: Decimal | None = None) -> Decimal | None:
    if raw is None:
        return default
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, int | float):
        return Decimal(str(raw))
    normalized = _normalize_text(raw)
    if normalized is None:
        return default
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None


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
        """
        上传文件到临时目录

        参数：
            file_content: 文件内容
            filename: 原始文件名

        返回：
            包含文件路径的字典
        """
        import tempfile

        from ...utils.file_security import generate_safe_filename

        temp_dir = Path(tempfile.gettempdir())
        file_id = str(uuid.uuid4())
        safe_filename = generate_safe_filename(filename, file_id)
        temp_file_path = temp_dir / safe_filename

        # 保存文件
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

    def _parse_date(self, date_str: date | str | None) -> date | None:
        """
        解析日期字符串

        Args:
            date_str: 日期字符串或日期对象

        Returns:
            date | None: 解析后的日期对象
        """
        if not date_str:
            return None

        if isinstance(date_str, date):
            return date_str

        # 尝试常见日期格式
        formats = ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%Y年%m月%d日"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        logger.warning(f"无法解析日期: {date_str}")
        return None

    @classmethod
    def get_available_slots(cls) -> int:
        """获取当前可用的处理槽位数"""
        available = max(0, MAX_CONCURRENT_PDF_TASKS - cls._active_tasks)
        return available

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
        """
        获取会话状态

        Args:
            db: 数据库会话
            session_id: PDF 导入会话 ID

        Returns:
            会话状态信息
        """

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
        """
        启动 PDF 处理流程

        使用后台任务处理 PDF，避免阻塞请求

        Args:
            db: 数据库会话
            session_id: PDF 导入会话 ID
            organization_id: 组织 ID
            file_size: 文件大小
            file_path: 文件路径
            content_type: 内容类型
            processing_options: 处理选项

        Returns:
            处理启动结果
        """
        session = await pdf_import_session_crud.get_by_session_id_async(db, session_id)
        if session:
            session.status = SessionStatus.PROCESSING
            session.current_step = ProcessingStep.FILE_UPLOAD
            session.progress_percentage = 0.0
            await db.commit()

        # 创建带异常追踪的后台任务
        background_coro = self._process_background_safe(
            session_id, file_path, processing_options
        )
        task = asyncio.create_task(background_coro)
        if not isinstance(task, asyncio.Task):
            # 测试场景中 create_task 可能被同步 mock，主动关闭协程避免未等待告警
            background_coro.close()

        # 添加任务完成回调（用于捕获异常）
        task.add_done_callback(self._handle_task_completion)

        logger.info(
            f"Started processing for session {session_id} "
            f"(concurrent: {self.get_current_concurrent_count()}/{MAX_CONCURRENT_PDF_TASKS})"
        )

        return {"success": True, "message": "Processing started"}

    def _handle_task_completion(self, task: asyncio.Task[Any]) -> None:
        """
        任务完成回调
        捕获未被处理的异常并记录到日志

        注意: 实际的错误持久化已经在 _process_background_safe 中处理
        这个回调主要用于最后一道防线的错误日志记录

        Args:
            task: 已完成的任务
        """
        try:
            # 获取任务结果（如果抛出异常会重新抛出）
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
        """
        安全的后台处理包装器
        使用信号量控制并发，确保异常被追踪

        Args:
            session_id: 会话 ID
            file_path: 文件路径
            options: 处理选项
        """
        async with self._processing_semaphore:
            # 增加活动任务计数
            async with self._active_tasks_lock:
                self.__class__._active_tasks += 1

            logger.info(
                f"Acquired processing slot for {session_id} "
                f"(active: {self.get_current_concurrent_count()})"
            )

            try:
                await self._process_background(session_id, file_path, options)
            except Exception as e:
                logger.error(
                    f"Processing failed for {session_id}: {e}",
                    exc_info=True,
                    extra={
                        "error_id": "PDF_BACKGROUND_TASK_FAILED",
                        "session_id": session_id,
                    },
                )
                # 持久化错误到数据库
                error_result = {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                }
                await self._persist_processing_error(session_id, error_result)
            finally:
                # 减少活动任务计数
                async with self._active_tasks_lock:
                    self.__class__._active_tasks -= 1
                logger.info(f"Released processing slot for {session_id}")

    async def _process_background(
        self, session_id: str, file_path: str, options: dict[str, Any]
    ) -> dict[str, Any]:
        """
        智能提取管道 - 自动检测 PDF 类型并选择最佳提取方式

        Args:
            session_id: 会话 ID
            file_path: PDF 文件路径
            options: 处理选项

        Returns:
            处理结果
        """
        logger.info(f"Starting smart processing for session {session_id}")
        start_time = time.time()

        # 注意: 后台任务使用独立的数据库会话（通过 _persist_processing_result/error 方法）
        # 避免与主请求会话冲突，每个持久化操作都创建新的会话上下文

        try:
            # 确定提取方法
            force_method = options.get("force_method")
            if force_method is None and options.get("prefer_vision"):
                force_method = "vision"

            # Step 1: 智能提取
            logger.info("Step 1: Running Smart Extraction...")
            smart_result = await self.llm_extractor.extract_smart(
                pdf_path=file_path,
                force_method=force_method,
            )

            if not smart_result.get("success"):
                error_detail = smart_result.get("error") or "unknown"
                raise FileProcessingError(
                    message="Smart extraction failed",
                    file_name=Path(file_path).name,
                    file_type="pdf",
                    details={"error": error_detail},
                )

            # Step 2: 正则验证
            logger.info("Step 2: Running Regex validation...")
            regex_result = None
            extraction_method = smart_result.get("extraction_method")
            if extraction_method in {"text", "ocr_text"} and smart_result.get(
                "markdown_content"
            ):
                regex_result = self.regex_extractor.extract_contract_info(
                    smart_result.get("markdown_content", "")
                )

            # Step 3: 合并结果
            final_result = self._merge_smart_results(smart_result, regex_result)

            processing_time = (time.time() - start_time) * 1000
            logger.info(
                f"Processing Complete for {session_id}. "
                f"Method: {final_result.get('extraction_method')}, "
                f"Confidence: {final_result.get('confidence_score')}, "
                f"Time: {processing_time:.0f}ms"
            )

            # 持久化结果到数据库
            await self._persist_processing_result(
                session_id, final_result, processing_time
            )

            return final_result

        except Exception as e:
            logger.error(f"Smart Processing Failed for {session_id}: {e}")
            logger.debug(traceback.format_exc())

            error_result = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
            }

            # 更新数据库状态为失败
            await self._persist_processing_error(session_id, error_result)

            return error_result

    async def _persist_processing_result(
        self, session_id: str, result: dict[str, Any], processing_time_ms: float
    ) -> None:
        """
        持久化处理结果到数据库

        Args:
            session_id: 会话 ID
            result: 处理结果
            processing_time_ms: 处理耗时（毫秒）
        """
        from ...database import async_session_scope

        async with async_session_scope() as db:
            try:
                session = await pdf_import_session_crud.get_by_session_id_async(
                    db,
                    session_id,
                )

                if session:
                    result_with_metrics = {
                        **result,
                        "processing_time_ms": processing_time_ms,
                    }
                    session.processing_result = result_with_metrics
                    session.extracted_data = result.get("extracted_fields", {})
                    session.confidence_score = result.get("confidence_score", 0.0)
                    session.processing_method = result.get(
                        "extraction_method", "unknown"
                    )

                    confidence_threshold = 0.8
                    should_auto_confirm = (
                        result.get("auto_confirm")
                        and result.get("confidence_score", 0) > confidence_threshold
                    )

                    if should_auto_confirm:
                        session.status = SessionStatus.COMPLETED
                        session.progress_percentage = 100.0
                    else:
                        session.status = SessionStatus.READY_FOR_REVIEW
                        session.progress_percentage = 90.0

                    session.current_step = ProcessingStep.FINAL_REVIEW

                    session.completed_at = _utcnow_naive()

                    await db.commit()
                    logger.info(f"Persisted processing result for session {session_id}")
                    cleaned = self._cleanup_source_file(
                        session.file_path, session.processing_options
                    )
                    if cleaned:
                        session.file_path = None
                        await db.commit()
            except Exception as e:
                logger.error(
                    f"Failed to persist processing result for {session_id}: {e}",
                    exc_info=True,
                    extra={
                        "error_id": "PERSIST_RESULT_FAILED",
                        "session_id": session_id,
                    },
                )
                await db.rollback()
                raise

    async def _persist_processing_error(
        self, session_id: str, error_result: dict[str, Any]
    ) -> None:
        """
        持久化处理错误到数据库

        Args:
            session_id: 会话 ID
            error_result: 错误结果
        """
        from ...database import async_session_scope

        async with async_session_scope() as db:
            try:
                session = await pdf_import_session_crud.get_by_session_id_async(
                    db,
                    session_id,
                )

                if session:
                    session.error_message = error_result.get("error", "Unknown error")
                    session.processing_result = error_result
                    session.status = SessionStatus.FAILED
                    session.progress_percentage = 0.0

                    session.completed_at = _utcnow_naive()

                    await db.commit()
                    logger.info(f"Persisted processing error for session {session_id}")
                    cleaned = self._cleanup_source_file(
                        session.file_path, session.processing_options
                    )
                    if cleaned:
                        session.file_path = None
                        await db.commit()
            except Exception as e:
                logger.error(
                    f"Failed to persist processing error for {session_id}: {e}",
                    exc_info=True,
                    extra={
                        "error_id": "PERSIST_ERROR_FAILED",
                        "session_id": session_id,
                    },
                )
                await db.rollback()
                raise

    def _cleanup_source_file(
        self, file_path: str | None, processing_options: dict[str, Any] | None
    ) -> bool:
        if not file_path:
            return False
        if (
            processing_options is not None
            and processing_options.get("cleanup_temp_file") is False
        ):
            return False

        try:
            path = Path(file_path)
            resolved_path = path.resolve()
            temp_dirs = [
                Path("temp_uploads").resolve(),
                Path(tempfile.gettempdir()).resolve(),
            ]
            should_cleanup = any(
                resolved_path.is_relative_to(temp_dir) for temp_dir in temp_dirs
            )
        except Exception:
            should_cleanup = False

        if not should_cleanup:
            return False

        try:
            path.unlink(missing_ok=True)
            logger.info(f"Cleaned up source file: {file_path}")
            return True
        except Exception as exc:
            logger.warning(f"Failed to clean up source file {file_path}: {exc}")
            return False

    # ========================================================================
    # 结果合并辅助函数
    # ========================================================================

    # 常量定义
    EXPECTED_FIELD_COUNT = 14
    CONFIDENCE_BASE_THRESHOLD = 0.8
    CONFIDENCE_MIN_BASE = 0.3
    CONFIDENCE_WEIGHT_EXTRACTION = 0.3
    CONFIDENCE_MAX_SCORE = 0.95

    def _get_extracted_fields(self, smart_result: dict[str, Any]) -> dict[str, Any]:
        """从智能提取结果中获取字段"""
        raw_fields = smart_result.get("raw_llm_json")
        if isinstance(raw_fields, dict):
            return raw_fields
        extracted_fields = smart_result.get("extracted_fields", {})
        return cast(dict[str, Any], extracted_fields)

    def _fill_missing_fields_with_regex(
        self, extracted: dict[str, Any], regex_result: dict[str, Any] | None
    ) -> tuple[dict[str, Any], int, list[str]]:
        """
        使用正则提取结果填补缺失字段

        Returns:
            tuple[dict, int]: (填充后的字段字典, 填充的字段数)
        """
        extracted_count = sum(1 for v in extracted.values() if v is not None)
        filled_keys: list[str] = []

        if regex_result and regex_result.get("success"):
            regex_fields = regex_result.get("extracted_fields", {})
            for key, val in regex_fields.items():
                if not extracted.get(key):
                    extracted[key] = val["value"] if isinstance(val, dict) else val
                    extracted_count += 1
                    filled_keys.append(key)

        return extracted, extracted_count, filled_keys

    def _calculate_extraction_rate(self, extracted_count: int) -> float:
        """计算字段提取率"""
        return (
            extracted_count / self.EXPECTED_FIELD_COUNT
            if self.EXPECTED_FIELD_COUNT > 0
            else 0
        )

    def _calculate_confidence(
        self, smart_result: dict[str, Any], extraction_rate: float
    ) -> float:
        """计算综合置信度分数"""
        if smart_result.get("success"):
            confidence_value = smart_result.get(
                "confidence", self.CONFIDENCE_BASE_THRESHOLD
            )
            try:
                base_confidence = float(confidence_value)
            except (TypeError, ValueError):
                base_confidence = self.CONFIDENCE_BASE_THRESHOLD
        else:
            base_confidence = self.CONFIDENCE_MIN_BASE
        weighted_confidence = base_confidence * (
            0.7 + self.CONFIDENCE_WEIGHT_EXTRACTION * extraction_rate
        )
        return min(self.CONFIDENCE_MAX_SCORE, weighted_confidence)

    def _merge_smart_results(
        self, smart_result: dict[str, Any], regex_result: dict[str, Any] | None
    ) -> dict[str, Any]:
        """
        合并智能提取结果与正则验证结果

        策略:
        - LLM/Vision 提取为主数据源
        - 正则填补空缺和验证模式
        """
        # 获取提取字段
        extracted = self._get_extracted_fields(smart_result)

        # 用正则填补空缺并统计
        extracted, extracted_count, filled_keys = self._fill_missing_fields_with_regex(
            extracted, regex_result
        )

        # 计算置信度
        extraction_rate = self._calculate_extraction_rate(extracted_count)
        confidence_score = self._calculate_confidence(smart_result, extraction_rate)
        warnings = self._validate_consistency(extracted)
        if warnings:
            confidence_score = max(0.0, confidence_score - 0.05 * len(warnings))

        field_evidence = smart_result.get("field_evidence", {}) or {}
        field_sources = smart_result.get("field_sources", {}) or {}
        if regex_result:
            regex_evidence = self._build_regex_evidence(regex_result)
            for key in filled_keys:
                if key in regex_evidence:
                    field_evidence[key] = regex_evidence[key]
                    field_sources[key] = "regex"

        return {
            "success": True,
            "data": extracted,
            "extracted_fields": extracted,
            "confidence_score": round(confidence_score, 2),
            "extraction_method": smart_result.get("extraction_method", "unknown"),
            "processed_fields": extracted_count,
            "total_fields": self.EXPECTED_FIELD_COUNT,
            "pdf_analysis": smart_result.get("pdf_analysis"),
            "usage": smart_result.get("usage"),
            "source": "smart_extraction",
            "warnings": warnings,
            "field_evidence": field_evidence,
            "field_sources": field_sources,
        }

    def _build_regex_evidence(self, regex_result: dict[str, Any]) -> dict[str, Any]:
        evidence: dict[str, Any] = {}
        regex_fields = regex_result.get("extracted_fields", {})
        if not isinstance(regex_fields, dict):
            return evidence
        for key, value in regex_fields.items():
            if not isinstance(value, dict):
                continue
            snippet = value.get("source_text")
            if not snippet:
                continue
            evidence[key] = {
                "snippet": snippet,
                "match": value.get("value"),
                "match_type": "regex",
                "source": "regex",
            }
        return evidence

    def _validate_consistency(self, extracted: dict[str, Any]) -> list[str]:
        warnings: list[str] = []

        lease_start = self._parse_date(str(extracted.get("lease_start_date") or ""))
        lease_end = self._parse_date(str(extracted.get("lease_end_date") or ""))
        if lease_start and lease_end and lease_start > lease_end:
            warnings.append("lease_date_range_invalid")

        rent_terms = extracted.get("rent_terms")
        if isinstance(rent_terms, list):
            for idx, term in enumerate(rent_terms):
                if not isinstance(term, dict):
                    continue
                term_start = self._parse_date(str(term.get("start_date") or ""))
                term_end = self._parse_date(str(term.get("end_date") or ""))
                if term_start and term_end and term_start > term_end:
                    warnings.append(f"rent_term_{idx}_date_invalid")
                if lease_start and term_start and term_start < lease_start:
                    warnings.append(f"rent_term_{idx}_before_lease_start")
                if lease_end and term_end and term_end > lease_end:
                    warnings.append(f"rent_term_{idx}_after_lease_end")

        payment_cycle = str(extracted.get("payment_cycle") or "").strip()
        if payment_cycle:
            valid_cycles = {"月付", "季付", "半年付", "年付", "月", "季", "半年", "年"}
            if payment_cycle not in valid_cycles:
                warnings.append("payment_cycle_unrecognized")

        return warnings

    def _merge_results(
        self, regex_result: dict[str, Any], llm_result: dict[str, Any]
    ) -> dict[str, Any]:
        """
        合并策略: LLM 优先，正则补充

        (保留用于向后兼容)
        """
        if not llm_result.get("success"):
            return regex_result

        merged = llm_result.get("extracted_fields", {}).copy()

        regex_fields = regex_result.get("extracted_fields", {})
        for key, val in regex_fields.items():
            if not merged.get(key):
                merged[key] = val["value"] if isinstance(val, dict) else val

        return {
            "success": True,
            "extracted_fields": merged,
            "confidence": max(
                regex_result.get("overall_confidence", 0),
                llm_result.get("confidence", 0),
            ),
            "source": "hybrid (llm+regex)",
        }

    async def confirm_import(
        self,
        db: AsyncSession,
        session_id: str,
        confirmed_data: dict[str, Any],
        user_id: str | int,
    ) -> dict[str, Any]:
        """
        用户验证数据后创建实际的资产/合同记录

        Args:
            db: 数据库会话
            session_id: 会话 ID
            confirmed_data: 用户确认的数据
            user_id: 用户 ID

        Returns:
            创建结果
        """
        import_session = await pdf_import_session_crud.get_by_session_id_async(
            db,
            session_id,
        )

        if not import_session:
            return {
                "success": False,
                "message": "Import session not found",
                "error": "Import session not found",
            }

        if import_session.status != SessionStatus.READY_FOR_REVIEW:
            return {
                "success": False,
                "message": "Import session is not ready for confirmation",
                "error": "Import session is not ready for confirmation",
            }

        merged_data = _merge_confirmed_payload(confirmed_data)
        required_fields = [
            "contract_number",
            "tenant_name",
            "start_date",
            "end_date",
            "revenue_mode",
            "operator_party_id",
            "owner_party_id",
            "contract_direction",
            "group_relation_type",
            "lessor_party_id",
            "lessee_party_id",
            "settlement_rule",
        ]
        missing_fields = [
            field for field in required_fields if merged_data.get(field) in (None, "")
        ]
        if missing_fields:
            return {
                "success": False,
                "message": f"Missing required fields: {', '.join(missing_fields)}",
                "error": f"Missing required fields: {', '.join(missing_fields)}",
            }

        revenue_mode = _parse_enum_member(RevenueMode, merged_data.get("revenue_mode"))
        contract_direction = _parse_enum_member(
            ContractDirection, merged_data.get("contract_direction")
        )
        group_relation_type = _parse_enum_member(
            GroupRelationType, merged_data.get("group_relation_type")
        )
        if (
            revenue_mode is None
            or contract_direction is None
            or group_relation_type is None
        ):
            return {
                "success": False,
                "message": "Invalid enum values in confirmed_data",
                "error": "Invalid enum values in confirmed_data",
            }

        start_date_raw = merged_data.get("start_date")
        end_date_raw = merged_data.get("end_date")
        sign_date_raw = merged_data.get("sign_date")
        effective_from = self._parse_date(start_date_raw)
        effective_to = self._parse_date(end_date_raw)
        sign_date = self._parse_date(sign_date_raw)
        if effective_from is None or effective_to is None:
            return {
                "success": False,
                "message": "Invalid start_date or end_date format",
                "error": "Invalid start_date or end_date format",
            }
        if sign_date_raw is not None and sign_date is None:
            return {
                "success": False,
                "message": "Invalid sign_date format",
                "error": "Invalid sign_date format",
            }

        monthly_rent_base = _parse_decimal(merged_data.get("monthly_rent_base"))
        if monthly_rent_base is None:
            return {
                "success": False,
                "message": "monthly_rent_base is required and must be a valid decimal",
                "error": "monthly_rent_base is required and must be a valid decimal",
            }

        asset_ids: list[str] = []
        if isinstance(merged_data.get("asset_ids"), list):
            asset_ids.extend(
                asset_id
                for raw_asset_id in merged_data.get("asset_ids", [])
                if (asset_id := _normalize_text(raw_asset_id)) is not None
            )
        single_asset_id = _normalize_text(merged_data.get("asset_id"))
        if single_asset_id is not None and single_asset_id not in asset_ids:
            asset_ids.append(single_asset_id)

        operator_party_id = _normalize_text(merged_data.get("operator_party_id"))
        owner_party_id = _normalize_text(merged_data.get("owner_party_id"))
        lessor_party_id = _normalize_text(merged_data.get("lessor_party_id"))
        lessee_party_id = _normalize_text(merged_data.get("lessee_party_id"))
        contract_number = _normalize_text(merged_data.get("contract_number"))
        if (
            operator_party_id is None
            or owner_party_id is None
            or lessor_party_id is None
            or lessee_party_id is None
            or contract_number is None
        ):
            return {
                "success": False,
                "message": "Missing required party ids or contract number",
                "error": "Missing required party ids or contract number",
            }

        settlement_rule_data = merged_data.get("settlement_rule")
        if not isinstance(settlement_rule_data, dict):
            return {
                "success": False,
                "message": "settlement_rule must be a JSON object",
                "error": "settlement_rule must be a JSON object",
            }

        total_deposit = _parse_decimal(merged_data.get("total_deposit"), Decimal("0"))
        if total_deposit is None:
            return {
                "success": False,
                "message": "total_deposit must be a valid decimal",
                "error": "total_deposit must be a valid decimal",
            }

        operator_party = await party_service.get_party(
            db,
            party_id=operator_party_id,
        )
        if operator_party is None:
            return {
                "success": False,
                "message": "Operator party not found",
                "error": "Operator party not found",
            }

        owner_party = await party_service.get_party(
            db,
            party_id=owner_party_id,
        )
        if owner_party is None:
            return {
                "success": False,
                "message": "Owner party not found",
                "error": "Owner party not found",
            }

        try:
            group_payload = ContractGroupCreate(
                revenue_mode=revenue_mode,
                operator_party_id=operator_party_id,
                owner_party_id=owner_party_id,
                effective_from=effective_from,
                effective_to=effective_to,
                settlement_rule=SettlementRuleSchema(**settlement_rule_data),
                revenue_attribution_rule=merged_data.get("revenue_attribution_rule"),
                revenue_share_rule=merged_data.get("revenue_share_rule"),
                risk_tags=merged_data.get("risk_tags"),
                predecessor_group_id=_normalize_text(
                    merged_data.get("predecessor_group_id")
                ),
                asset_ids=asset_ids,
            )

            lease_detail: LeaseDetailCreate | None = None
            agency_detail: AgencyDetailCreate | None = None
            if revenue_mode == RevenueMode.LEASE:
                payment_cycle = _normalize_text(merged_data.get("payment_cycle"))
                lease_detail = LeaseDetailCreate(
                    total_deposit=total_deposit,
                    rent_amount=monthly_rent_base,
                    monthly_rent_base=monthly_rent_base,
                    payment_cycle=payment_cycle or group_payload.settlement_rule.cycle,
                    payment_terms=_normalize_text(merged_data.get("payment_terms")),
                    tenant_name=_normalize_text(merged_data.get("tenant_name")),
                    tenant_contact=_normalize_text(merged_data.get("tenant_contact")),
                    tenant_phone=_normalize_text(merged_data.get("tenant_phone")),
                    tenant_address=_normalize_text(merged_data.get("tenant_address")),
                    tenant_usage=_normalize_text(merged_data.get("tenant_usage")),
                    owner_name=_normalize_text(merged_data.get("owner_name")),
                    owner_contact=_normalize_text(merged_data.get("owner_contact")),
                    owner_phone=_normalize_text(merged_data.get("owner_phone")),
                )
            else:
                agency_detail_data = merged_data.get("agency_detail")
                if not isinstance(agency_detail_data, dict):
                    return {
                        "success": False,
                        "message": (
                            "AGENCY confirm requires agency_detail to be provided explicitly"
                        ),
                        "error": (
                            "AGENCY confirm requires agency_detail to be provided explicitly"
                        ),
                    }
                agency_detail = AgencyDetailCreate(**agency_detail_data)

            group_code = await contract_group_service.generate_group_code(
                db,
                operator_party_id=operator_party_id,
                operator_party_code=operator_party.code,
            )
            created_group = await contract_group_service.create_contract_group(
                db,
                obj_in=group_payload,
                group_code=group_code,
                current_user=str(user_id),
                commit=False,
            )

            contract_payload = ContractCreate(
                contract_group_id=created_group.contract_group_id,
                contract_number=contract_number,
                contract_direction=contract_direction,
                group_relation_type=group_relation_type,
                lessor_party_id=lessor_party_id,
                lessee_party_id=lessee_party_id,
                sign_date=sign_date,
                effective_from=effective_from,
                effective_to=effective_to,
                currency_code="CNY",
                tax_rate=None,
                is_tax_included=True,
                status=ContractLifecycleStatus.DRAFT,
                review_status=ContractReviewStatus.DRAFT,
                contract_notes=_normalize_text(merged_data.get("contract_notes")),
                source_session_id=session_id,
                asset_ids=asset_ids,
                lease_detail=lease_detail,
                agency_detail=agency_detail,
            )
            created_contract = await contract_group_service.add_contract_to_group(
                db,
                obj_in=contract_payload,
                current_user=str(user_id),
                commit=False,
            )

            created_terms_count = 0
            rent_terms = merged_data.get("rent_terms")
            if isinstance(rent_terms, list):
                for index, rent_term in enumerate(rent_terms, start=1):
                    if not isinstance(rent_term, dict):
                        continue
                    rent_term_start = self._parse_date(rent_term.get("start_date"))
                    rent_term_end = self._parse_date(rent_term.get("end_date"))
                    rent_term_amount = _parse_decimal(rent_term.get("monthly_rent"))
                    management_fee = _parse_decimal(
                        rent_term.get("management_fee"), Decimal("0")
                    )
                    other_fees = _parse_decimal(
                        rent_term.get("other_fees"), Decimal("0")
                    )
                    if (
                        rent_term_start is None
                        or rent_term_end is None
                        or rent_term_amount is None
                        or management_fee is None
                        or other_fees is None
                    ):
                        return {
                            "success": False,
                            "message": "Invalid rent_terms payload",
                            "error": "Invalid rent_terms payload",
                        }
                    await contract_group_service.create_rent_term(
                        db,
                        contract_id=created_contract.contract_id,
                        obj_in=ContractRentTermCreate(
                            sort_order=index,
                            start_date=rent_term_start,
                            end_date=rent_term_end,
                            monthly_rent=rent_term_amount,
                            management_fee=management_fee,
                            other_fees=other_fees,
                            notes=_normalize_text(
                                rent_term.get("rent_description")
                                or rent_term.get("notes")
                            ),
                        ),
                        commit=False,
                    )
                    created_terms_count += 1

            processing_result = dict(import_session.processing_result or {})
            processing_result["created_contract_group_id"] = (
                created_group.contract_group_id
            )
            processing_result["created_contract_id"] = created_contract.contract_id
            processing_result["created_terms_count"] = created_terms_count

            import_session.status = SessionStatus.CONFIRMED
            import_session.current_step = ProcessingStep.FINAL_REVIEW
            import_session.progress_percentage = 100.0
            import_session.processing_result = processing_result
            import_session.completed_at = _utcnow_naive()

            await db.commit()
            await db.refresh(import_session)

            return {
                "success": True,
                "message": "合同导入成功",
                "contract_group_id": created_group.contract_group_id,
                "contract_id": created_contract.contract_id,
                "contract_number": contract_number,
                "created_terms_count": created_terms_count,
            }
        except ValidationError as exc:
            await db.rollback()
            logger.warning(
                "PDF contract confirm validation failed for session %s: %s",
                session_id,
                exc,
            )
            return {
                "success": False,
                "message": "Confirmed data validation failed",
                "error": "Confirmed data validation failed",
            }
        except BaseBusinessError as exc:
            await db.rollback()
            logger.warning(
                "PDF contract confirm business validation failed for session %s: %s",
                session_id,
                exc,
            )
            return {
                "success": False,
                "message": str(exc),
                "error": str(exc),
            }
        except Exception as exc:
            await db.rollback()
            logger.exception(
                "PDF contract confirm failed for session %s",
                session_id,
            )
            return {
                "success": False,
                "message": "Contract import confirm failed",
                "error": str(exc),
            }

    async def cancel_processing(
        self,
        db: AsyncSession,
        session_id: str,
        reason: str,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        取消处理

        Args:
            db: 数据库会话
            session_id: 会话 ID
            reason: 取消原因

        Returns:
            取消结果
        """
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
