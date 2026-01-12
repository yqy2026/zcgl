#!/usr/bin/env python3
"""
PDF 导入服务
编排 PDF 处理流程，管理会话和后台任务
"""

import asyncio
import logging
import os
import time
import traceback
from datetime import UTC, date
from typing import Any

from sqlalchemy.orm import Session

from ...core.task_queue import get_task_queue  # 现有任务队列系统
from ...models.pdf_import_session import PDFImportSession, ProcessingStep, SessionStatus
from ...models.rent_contract import (
    ContractType,
    PaymentCycle,
    RentContract,
)
from .contract_extractor import ContractExtractor
from .llm_contract_extractor import get_llm_contract_extractor
from .paddleocr_service import get_paddleocr_service

logger = logging.getLogger(__name__)

# 从环境变量读取并发限制
MAX_CONCURRENT_PDF_TASKS = int(os.getenv("OCR_MAX_CONCURRENT", "3"))


class PDFImportService:
    """
    PDF 导入服务

    职责:
    - 管理数据库会话
    - 调度异步处理任务
    - 整合 OCR 和提取逻辑
    - 并发控制和错误追踪
    """

    # 类级别的并发控制信号量
    _processing_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PDF_TASKS)
    # 显式跟踪活动任务数，避免访问私有属性
    _active_tasks = 0
    _active_tasks_lock = asyncio.Lock()

    def __init__(self):
        self.paddle_service = get_paddleocr_service()
        self.regex_extractor = ContractExtractor()
        self.llm_extractor = get_llm_contract_extractor()
        self.task_queue = get_task_queue()

    @classmethod
    def get_available_slots(cls) -> int:
        """获取当前可用的处理槽位数"""
        available = max(0, MAX_CONCURRENT_PDF_TASKS - cls._active_tasks)
        return available

    @classmethod
    def get_current_concurrent_count(cls) -> int:
        """获取当前正在处理的任务数"""
        return cls._active_tasks

    async def get_session_status(self, db: Session, session_id: str) -> dict[str, Any]:
        """
        获取会话状态

        Args:
            db: 数据库会话
            session_id: PDF 导入会话 ID

        Returns:
            会话状态信息
        """
        session = (
            db.query(PDFImportSession)
            .filter(PDFImportSession.session_id == session_id)
            .first()
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
        db: Session,
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
        # 更新会话状态为处理中
        session = (
            db.query(PDFImportSession)
            .filter(PDFImportSession.session_id == session_id)
            .first()
        )
        if session:
            session.status = SessionStatus.PROCESSING
            session.current_step = ProcessingStep.FILE_UPLOAD
            session.progress_percentage = 0.0
            db.commit()

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

    def _handle_task_completion(self, task: asyncio.Task) -> None:
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
            force_method = None
            if options.get("prefer_ocr"):
                force_method = "text"
            elif options.get("prefer_vision"):
                force_method = "vision"

            # Step 1: 智能提取
            logger.info("Step 1: Running Smart Extraction...")
            smart_result = await self.llm_extractor.extract_smart(
                pdf_path=file_path,
                force_method=force_method,
            )

            if not smart_result.get("success"):
                raise Exception(f"Smart extraction failed: {smart_result.get('error')}")

            # Step 2: 正则验证
            logger.info("Step 2: Running Regex validation...")
            regex_result = None
            if smart_result.get("extraction_method") == "text" and smart_result.get(
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
        from ...database import _get_database_manager

        db_manager = _get_database_manager()

        with db_manager.get_session() as db:
            try:
                session = (
                    db.query(PDFImportSession)
                    .filter(PDFImportSession.session_id == session_id)
                    .first()
                )

                if session:
                    # 更新处理结果（包含处理时间）
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

                    # 更新状态
                    confidence_threshold = 0.8
                    should_auto_confirm = (
                        result.get("auto_confirm")
                        and result.get("confidence_score", 0) > confidence_threshold
                    )

                    if should_auto_confirm:
                        # 高置信度，自动完成
                        session.status = SessionStatus.COMPLETED
                        session.progress_percentage = 100.0
                    else:
                        # 需要用户确认
                        session.status = SessionStatus.READY_FOR_REVIEW
                        session.progress_percentage = 90.0

                    session.current_step = ProcessingStep.FINAL_REVIEW

                    # 设置完成时间
                    from datetime import datetime

                    session.completed_at = datetime.now(UTC)

                    db.commit()
                    logger.info(f"Persisted processing result for session {session_id}")

            except Exception as e:
                logger.error(
                    f"Failed to persist processing result for {session_id}: {e}",
                    exc_info=True,
                    extra={
                        "error_id": "PERSIST_RESULT_FAILED",
                        "session_id": session_id,
                    },
                )
                db.rollback()
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
        from ...database import _get_database_manager

        db_manager = _get_database_manager()

        with db_manager.get_session() as db:
            try:
                session = (
                    db.query(PDFImportSession)
                    .filter(PDFImportSession.session_id == session_id)
                    .first()
                )

                if session:
                    # 更新错误信息
                    session.error_message = error_result.get("error", "Unknown error")
                    session.processing_result = error_result
                    session.status = SessionStatus.FAILED
                    session.progress_percentage = 0.0

                    # 设置完成时间
                    from datetime import datetime

                    session.completed_at = datetime.now(UTC)

                    db.commit()
                    logger.info(f"Persisted processing error for session {session_id}")

            except Exception as e:
                logger.error(
                    f"Failed to persist processing error for {session_id}: {e}",
                    exc_info=True,
                    extra={
                        "error_id": "PERSIST_ERROR_FAILED",
                        "session_id": session_id,
                    },
                )
                db.rollback()
                raise

    # ========================================================================
    # 结果合并辅助函数
    # ========================================================================

    # 常量定义
    EXPECTED_FIELD_COUNT = 14
    CONFIDENCE_BASE_THRESHOLD = 0.8
    CONFIDENCE_MIN_BASE = 0.3
    CONFIDENCE_WEIGHT_EXTRACTION = 0.3
    CONFIDENCE_MAX_SCORE = 0.95

    def _get_extracted_fields(self, smart_result: dict) -> dict:
        """从智能提取结果中获取字段"""
        return smart_result.get("raw_llm_json") or smart_result.get(
            "extracted_fields", {}
        )

    def _fill_missing_fields_with_regex(
        self, extracted: dict, regex_result: dict | None
    ) -> tuple[dict, int]:
        """
        使用正则提取结果填补缺失字段

        Returns:
            tuple[dict, int]: (填充后的字段字典, 填充的字段数)
        """
        extracted_count = sum(1 for v in extracted.values() if v is not None)

        if regex_result and regex_result.get("success"):
            regex_fields = regex_result.get("extracted_fields", {})
            for key, val in regex_fields.items():
                if not extracted.get(key):
                    extracted[key] = val["value"] if isinstance(val, dict) else val
                    extracted_count += 1

        return extracted, extracted_count

    def _calculate_extraction_rate(self, extracted_count: int) -> float:
        """计算字段提取率"""
        return (
            extracted_count / self.EXPECTED_FIELD_COUNT
            if self.EXPECTED_FIELD_COUNT > 0
            else 0
        )

    def _calculate_confidence(
        self, smart_result: dict, extraction_rate: float
    ) -> float:
        """计算综合置信度分数"""
        base_confidence = (
            smart_result.get("confidence", self.CONFIDENCE_BASE_THRESHOLD)
            if smart_result.get("success")
            else self.CONFIDENCE_MIN_BASE
        )
        weighted_confidence = base_confidence * (
            0.7 + self.CONFIDENCE_WEIGHT_EXTRACTION * extraction_rate
        )
        return min(self.CONFIDENCE_MAX_SCORE, weighted_confidence)

    def _merge_smart_results(
        self, smart_result: dict, regex_result: dict | None
    ) -> dict:
        """
        合并智能提取结果与正则验证结果

        策略:
        - LLM/Vision 提取为主数据源
        - 正则填补空缺和验证模式
        """
        # 获取提取字段
        extracted = self._get_extracted_fields(smart_result)

        # 用正则填补空缺并统计
        extracted, extracted_count = self._fill_missing_fields_with_regex(
            extracted, regex_result
        )

        # 计算置信度
        extraction_rate = self._calculate_extraction_rate(extracted_count)
        confidence_score = self._calculate_confidence(smart_result, extraction_rate)

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
        }

    def _merge_results(self, regex_result: dict, llm_result: dict) -> dict:
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
        db: Session,
        session_id: str,
        confirmed_data: dict,
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
            # 获取导入会话
            import_session = (
                db.query(PDFImportSession)
                .filter(PDFImportSession.session_id == session_id)
                .first()
            )

            if not import_session:
                return {"success": False, "error": "Import session not found"}

            # 提取合同数据
            contract_data = confirmed_data.get("contract_data", {})
            # 注意: asset_data 将在未来版本中用于关联资产
            # 目前只创建合同记录，资产关联逻辑待实现

            # 验证必填字段
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

            # 确定合同类型
            contract_type_str = contract_data.get("contract_type", "lease_downstream")
            contract_type_map = {
                "lease_upstream": ContractType.LEASE_UPSTREAM,
                "lease_downstream": ContractType.LEASE_DOWNSTREAM,
                "entrusted": ContractType.ENTRUSTED,
            }
            contract_type = contract_type_map.get(
                contract_type_str, ContractType.LEASE_DOWNSTREAM
            )

            # 确定付款周期
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

            # 创建合同记录
            from datetime import date

            contract = RentContract(
                contract_number=contract_data["contract_number"],
                ownership_id=contract_data.get("ownership_id", ""),
                contract_type=contract_type,
                tenant_name=contract_data["tenant_name"],
                tenant_contact=contract_data.get("tenant_contact"),
                tenant_phone=contract_data.get("tenant_phone"),
                tenant_address=contract_data.get("tenant_address"),
                tenant_usage=contract_data.get("tenant_usage"),
                sign_date=contract_data.get("sign_date", date.today()),
                start_date=self._parse_date(contract_data["start_date"]),
                end_date=self._parse_date(contract_data["end_date"]),
                total_deposit=contract_data.get("total_deposit", 0),
                monthly_rent_base=contract_data.get("monthly_rent", 0),
                payment_cycle=payment_cycle,
                payment_terms=contract_data.get("payment_terms"),
                contract_notes=contract_data.get("contract_notes"),
                service_fee_rate=contract_data.get("service_fee_rate"),
                source_session_id=session_id,
            )

            db.add(contract)
            db.flush()  # 获取 ID 但不提交

            # 更新导入会话状态
            import_session.status = SessionStatus.CONFIRMED
            import_session.extracted_data = confirmed_data
            db.commit()

            logger.info(
                f"Created contract {contract.id} from PDF import session {session_id}"
            )

            return {
                "success": True,
                "contract_id": contract.id,
                "contract_number": contract.contract_number,
                "message": "Contract created successfully",
            }

        except ValueError as e:
            # 用户输入验证错误 - 用户可修复
            db.rollback()
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
                "error_type": "VALIDATION_ERROR",
                "error_category": "USER_ERROR",
            }
        except Exception as e:
            # 导入 SQLAlchemy 异常类型
            from sqlalchemy.exc import IntegrityError, OperationalError

            if isinstance(e, IntegrityError):
                # 数据库约束冲突 - 用户可能需要修复数据
                db.rollback()
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
            elif isinstance(e, OperationalError):
                # 数据库操作错误 - 系统问题
                logger.error(
                    f"Database operation failed creating contract: {e}",
                    exc_info=True,
                    extra={"error_id": "CONTRACT_DB_ERROR", "session_id": session_id},
                )
                # 重新抛出 - 这是服务器错误，不是用户错误
                raise RuntimeError("Database error creating contract") from e
            else:
                # 其他未预期错误 - 系统问题
                db.rollback()
                logger.error(
                    f"Unexpected error creating contract from session {session_id}: {e}",
                    exc_info=True,
                    extra={
                        "error_id": "CONTRACT_CREATE_ERROR",
                        "session_id": session_id,
                    },
                )
                # 重新抛出未预期错误，不要静默处理
                raise

    def _parse_date(self, date_value: Any) -> date | None:
        """
        解析日期值

        Args:
            date_value: 日期值（字符串、date对象等）

        Returns:
            解析后的日期对象
        """
        if isinstance(date_value, date):
            return date_value

        if isinstance(date_value, str):
            # 尝试常见格式
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%Y年%m月%d日"):
                try:
                    from datetime import datetime

                    return datetime.strptime(date_value, fmt).date()
                except ValueError:
                    continue

        return None

    async def cancel_processing(
        self, db: Session, session_id: str, reason: str
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
        session = (
            db.query(PDFImportSession)
            .filter(PDFImportSession.session_id == session_id)
            .first()
        )

        if session and session.is_processing:
            session.status = SessionStatus.CANCELLED
            session.error_message = f"Cancelled: {reason}"
            db.commit()

        return {"success": True, "message": "Session cancelled"}
