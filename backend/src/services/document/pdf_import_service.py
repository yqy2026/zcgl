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
from datetime import date
from pathlib import Path
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    BaseBusinessError,
    BusinessValidationError,
    FileProcessingError,
    InternalServerError,
)
from ...core.task_queue import get_task_queue  # 现有任务队列系统
from ...models.pdf_import_session import PDFImportSession, ProcessingStep, SessionStatus
from ...models.rent_contract import (
    ContractType,
    PaymentCycle,
    RentContract,
)
from .contract_extractor import ContractExtractor
from .llm_contract_extractor import get_llm_contract_extractor

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

        from ....utils.file_security import generate_safe_filename

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

    def _parse_date(self, date_str: str | None) -> date | None:
        """
        解析日期字符串

        Args:
            date_str: 日期字符串 (格式: YYYY-MM-DD 或 YYYY/MM/DD)

        Returns:
            date | None: 解析后的日期对象
        """
        if not date_str:
            return None

        from datetime import datetime

        # 尝试常见日期格式
        formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"]
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

    async def get_session_status(
        self, db: AsyncSession, session_id: str
    ) -> dict[str, Any]:
        """
        获取会话状态

        Args:
            db: 数据库会话
            session_id: PDF 导入会话 ID

        Returns:
            会话状态信息
        """

        session_stmt = select(PDFImportSession).where(
            PDFImportSession.session_id == session_id
        )
        session = (await db.execute(session_stmt)).scalars().first()
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
        session_stmt = select(PDFImportSession).where(
            PDFImportSession.session_id == session_id
        )
        session = (await db.execute(session_stmt)).scalars().first()
        if session:
            session.status = SessionStatus.PROCESSING
            session.current_step = ProcessingStep.FILE_UPLOAD
            session.progress_percentage = 0.0
            await db.commit()

        # 创建带异常追踪的后台任务
        task = asyncio.create_task(
            self._process_background_safe(session_id, file_path, processing_options)
        )

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
                session_stmt = select(PDFImportSession).where(
                    PDFImportSession.session_id == session_id
                )
                session = (await db.execute(session_stmt)).scalars().first()

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

                    from datetime import datetime

                    session.completed_at = datetime.utcnow()

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
                session_stmt = select(PDFImportSession).where(
                    PDFImportSession.session_id == session_id
                )
                session = (await db.execute(session_stmt)).scalars().first()

                if session:
                    session.error_message = error_result.get("error", "Unknown error")
                    session.processing_result = error_result
                    session.status = SessionStatus.FAILED
                    session.progress_percentage = 0.0

                    from datetime import datetime

                    session.completed_at = datetime.utcnow()

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
        user_id: int,
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
        try:
            import_session_stmt = select(PDFImportSession).where(
                PDFImportSession.session_id == session_id
            )
            import_session = (await db.execute(import_session_stmt)).scalars().first()

            if not import_session:
                return {"success": False, "error": "Import session not found"}

            contract_data = confirmed_data.get("contract_data", {})

            required_fields = [
                "contract_number",
                "tenant_name",
                "start_date",
                "end_date",
            ]
            missing_fields = [f for f in required_fields if not contract_data.get(f)]
            if missing_fields:
                return {
                    "success": False,
                    "error": f"Missing required fields: {', '.join(missing_fields)}",
                }

            contract_type_str = contract_data.get("contract_type", "lease_downstream")
            contract_type_map = {
                "lease_upstream": ContractType.LEASE_UPSTREAM,
                "lease_downstream": ContractType.LEASE_DOWNSTREAM,
                "entrusted": ContractType.ENTRUSTED,
            }
            contract_type = contract_type_map.get(
                contract_type_str, ContractType.LEASE_DOWNSTREAM
            )

            payment_cycle_str = contract_data.get("payment_cycle", "monthly")
            payment_cycle_map = {
                "monthly": PaymentCycle.MONTHLY,
                "quarterly": PaymentCycle.QUARTERLY,
                "semi_annual": PaymentCycle.SEMI_ANNUAL,
                "annual": PaymentCycle.ANNUAL,
            }
            payment_cycle = payment_cycle_map.get(
                payment_cycle_str, PaymentCycle.MONTHLY
            )

            contract = RentContract()
            contract.contract_number = contract_data["contract_number"]
            contract.ownership_id = contract_data.get("ownership_id", "")
            contract.contract_type = contract_type
            contract.tenant_name = contract_data["tenant_name"]
            contract.tenant_contact = contract_data.get("tenant_contact")
            contract.tenant_phone = contract_data.get("tenant_phone")
            contract.tenant_address = contract_data.get("tenant_address")
            contract.tenant_usage = contract_data.get("tenant_usage")
            contract.sign_date = (
                self._parse_date(contract_data.get("sign_date")) or date.today()
            )
            start_date = self._parse_date(contract_data.get("start_date"))
            end_date = self._parse_date(contract_data.get("end_date"))
            if start_date is None or end_date is None:
                raise BusinessValidationError(
                    "Invalid date format for start_date or end_date",
                    field_errors={
                        "start_date": ["invalid_date_format"],
                        "end_date": ["invalid_date_format"],
                    },
                )
            contract.start_date = start_date
            contract.end_date = end_date
            contract.total_deposit = contract_data.get("total_deposit", 0)
            contract.monthly_rent_base = contract_data.get("monthly_rent", 0)
            contract.payment_cycle = payment_cycle
            contract.payment_terms = contract_data.get("payment_terms")
            contract.contract_notes = contract_data.get("contract_notes")
            contract.service_fee_rate = contract_data.get("service_fee_rate")
            contract.source_session_id = session_id

            db.add(contract)
            await db.flush()

            import_session.status = SessionStatus.CONFIRMED
            import_session.extracted_data = confirmed_data
            await db.commit()

            await db.refresh(contract)

            logger.info(
                f"Created contract {contract.id} from PDF import session {session_id}"
            )

            return {
                "success": True,
                "contract_id": contract.id,
                "contract_number": contract.contract_number,
                "message": "Contract created successfully",
            }

        except BaseBusinessError as e:
            await db.rollback()
            logger.info(
                f"Validation failed for session {session_id}: {e}",
                extra={
                    "error_id": "CONTRACT_VALIDATION_ERROR",
                    "session_id": session_id,
                },
            )
            return {
                "success": False,
                "error": str(e),
                "error_type": e.code,
                "error_category": "USER_ERROR",
            }
        except Exception as e:
            from sqlalchemy.exc import IntegrityError, OperationalError

            if isinstance(e, IntegrityError):
                await db.rollback()
                logger.error(
                    f"Database constraint violation creating contract: {e}",
                    extra={
                        "error_id": "CONTRACT_INTEGRITY_ERROR",
                        "session_id": session_id,
                    },
                )
                return {
                    "success": False,
                    "error": "Cannot create contract: data conflicts with existing records",
                    "error_type": "INTEGRITY_ERROR",
                    "error_category": "USER_ERROR",
                    "suggested_action": "Check if contract number already exists or review data for duplicates",
                }
            if isinstance(e, OperationalError):
                await db.rollback()
                logger.error(
                    f"Database operation failed creating contract: {e}",
                    exc_info=True,
                    extra={
                        "error_id": "CONTRACT_DB_ERROR",
                        "session_id": session_id,
                    },
                )
                raise InternalServerError(
                    message="Database error creating contract",
                    original_error=e,
                    details={
                        "error_id": "CONTRACT_DB_ERROR",
                        "session_id": session_id,
                    },
                ) from e

            await db.rollback()
            logger.error(
                f"Unexpected error creating contract from session {session_id}: {e}",
                exc_info=True,
                extra={
                    "error_id": "CONTRACT_CREATE_ERROR",
                    "session_id": session_id,
                },
            )
            raise InternalServerError(
                message="Unexpected error creating contract",
                original_error=e,
                details={
                    "error_id": "CONTRACT_CREATE_ERROR",
                    "session_id": session_id,
                },
            ) from e

    async def cancel_processing(
        self, db: AsyncSession, session_id: str, reason: str
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
        session_stmt = select(PDFImportSession).where(
            PDFImportSession.session_id == session_id
        )
        session = (await db.execute(session_stmt)).scalars().first()

        if session and session.is_processing:
            session.status = SessionStatus.CANCELLED
            session.error_message = f"Cancelled: {reason}"
            await db.commit()

        return {"success": True, "message": "Session cancelled"}
