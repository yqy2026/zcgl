#!/usr/bin/env python3
"""
PDF 处理管线

包含 PDF 提取、合并、验证、持久化等管线逻辑。
从 pdf_import_service.py 拆分而来，降低单文件行数。
"""

import logging
import tempfile
import time
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Any, cast

from ...core.exception_handler import FileProcessingError
from ...crud.pdf_import_session import pdf_import_session_crud
from ...models.pdf_import_session import ProcessingStep, SessionStatus
from ...utils.time import utcnow_naive

logger = logging.getLogger(__name__)


def _parse_date(date_str: date | str | None) -> date | None:
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


def _validate_consistency(extracted: dict[str, Any]) -> list[str]:
    """验证提取结果的一致性"""
    warnings: list[str] = []

    lease_start = _parse_date(str(extracted.get("lease_start_date") or ""))
    lease_end = _parse_date(str(extracted.get("lease_end_date") or ""))
    if lease_start and lease_end and lease_start > lease_end:
        warnings.append("lease_date_range_invalid")

    rent_terms = extracted.get("rent_terms")
    if isinstance(rent_terms, list):
        for idx, term in enumerate(rent_terms):
            if not isinstance(term, dict):
                continue
            term_start = _parse_date(str(term.get("start_date") or ""))
            term_end = _parse_date(str(term.get("end_date") or ""))
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


def _build_regex_evidence(regex_result: dict[str, Any]) -> dict[str, Any]:
    """从正则提取结果中构建字段证据"""
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


# ========================================================================
# 结果合并辅助函数 — 常量定义
# ========================================================================

EXPECTED_FIELD_COUNT = 14
CONFIDENCE_BASE_THRESHOLD = 0.8
CONFIDENCE_MIN_BASE = 0.3
CONFIDENCE_WEIGHT_EXTRACTION = 0.3
CONFIDENCE_MAX_SCORE = 0.95


def _get_extracted_fields(smart_result: dict[str, Any]) -> dict[str, Any]:
    """从智能提取结果中获取字段"""
    raw_fields = smart_result.get("raw_llm_json")
    if isinstance(raw_fields, dict):
        return raw_fields
    extracted_fields = smart_result.get("extracted_fields", {})
    return cast(dict[str, Any], extracted_fields)


def _fill_missing_fields_with_regex(
    extracted: dict[str, Any], regex_result: dict[str, Any] | None
) -> tuple[dict[str, Any], int, list[str]]:
    """
    使用正则提取结果填补缺失字段

    Returns:
        tuple[dict, int, list[str]]: (填充后的字段字典, 填充的字段数, 填充的键名列表)
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


def _calculate_extraction_rate(extracted_count: int) -> float:
    """计算字段提取率"""
    return extracted_count / EXPECTED_FIELD_COUNT if EXPECTED_FIELD_COUNT > 0 else 0


def _calculate_confidence(
    smart_result: dict[str, Any], extraction_rate: float
) -> float:
    """计算综合置信度分数"""
    if smart_result.get("success"):
        confidence_value = smart_result.get("confidence", CONFIDENCE_BASE_THRESHOLD)
        try:
            base_confidence = float(confidence_value)
        except (TypeError, ValueError):
            base_confidence = CONFIDENCE_BASE_THRESHOLD
    else:
        base_confidence = CONFIDENCE_MIN_BASE
    weighted_confidence = base_confidence * (
        0.7 + CONFIDENCE_WEIGHT_EXTRACTION * extraction_rate
    )
    return min(CONFIDENCE_MAX_SCORE, weighted_confidence)


def merge_smart_results(
    smart_result: dict[str, Any], regex_result: dict[str, Any] | None
) -> dict[str, Any]:
    """
    合并智能提取结果与正则验证结果

    策略:
    - LLM/Vision 提取为主数据源
    - 正则填补空缺和验证模式
    """
    # 获取提取字段
    extracted = _get_extracted_fields(smart_result)

    # 用正则填补空缺并统计
    extracted, extracted_count, filled_keys = _fill_missing_fields_with_regex(
        extracted, regex_result
    )

    # 计算置信度
    extraction_rate = _calculate_extraction_rate(extracted_count)
    confidence_score = _calculate_confidence(smart_result, extraction_rate)
    warnings = _validate_consistency(extracted)
    if warnings:
        confidence_score = max(0.0, confidence_score - 0.05 * len(warnings))

    field_evidence = smart_result.get("field_evidence", {}) or {}
    field_sources = smart_result.get("field_sources", {}) or {}
    if regex_result:
        regex_evidence = _build_regex_evidence(regex_result)
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
        "total_fields": EXPECTED_FIELD_COUNT,
        "pdf_analysis": smart_result.get("pdf_analysis"),
        "usage": smart_result.get("usage"),
        "source": "smart_extraction",
        "warnings": warnings,
        "field_evidence": field_evidence,
        "field_sources": field_sources,
    }


def merge_results_legacy(
    regex_result: dict[str, Any], llm_result: dict[str, Any]
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


# ========================================================================
# 临时文件清理
# ========================================================================


def cleanup_source_file(
    file_path: str | None, processing_options: dict[str, Any] | None
) -> bool:
    """清理源文件（仅清理临时目录下的文件）"""
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
# 持久化方法
# ========================================================================


async def persist_processing_result(
    session_id: str, result: dict[str, Any], processing_time_ms: float
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
                session.processing_method = result.get("extraction_method", "unknown")

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

                session.completed_at = utcnow_naive()

                await db.commit()
                logger.info(f"Persisted processing result for session {session_id}")
                cleaned = cleanup_source_file(
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


async def persist_processing_error(
    session_id: str, error_result: dict[str, Any]
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

                session.completed_at = utcnow_naive()

                await db.commit()
                logger.info(f"Persisted processing error for session {session_id}")
                cleaned = cleanup_source_file(
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


# ========================================================================
# 后台处理
# ========================================================================


async def process_background(
    session_id: str,
    file_path: str,
    options: dict[str, Any],
    *,
    llm_extractor: Any,
    regex_extractor: Any,
) -> dict[str, Any]:
    """
    智能提取管道 - 自动检测 PDF 类型并选择最佳提取方式

    Args:
        session_id: 会话 ID
        file_path: PDF 文件路径
        options: 处理选项
        llm_extractor: LLM 提取器实例
        regex_extractor: 正则提取器实例

    Returns:
        处理结果
    """
    logger.info(f"Starting smart processing for session {session_id}")
    start_time = time.time()

    try:
        # 确定提取方法
        force_method = options.get("force_method")
        if force_method is None and options.get("prefer_vision"):
            force_method = "vision"

        # Step 1: 智能提取
        logger.info("Step 1: Running Smart Extraction...")
        smart_result = await llm_extractor.extract_smart(
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
            regex_result = regex_extractor.extract_contract_info(
                smart_result.get("markdown_content", "")
            )

        # Step 3: 合并结果
        final_result = merge_smart_results(smart_result, regex_result)

        processing_time = (time.time() - start_time) * 1000
        logger.info(
            f"Processing Complete for {session_id}. "
            f"Method: {final_result.get('extraction_method')}, "
            f"Confidence: {final_result.get('confidence_score')}, "
            f"Time: {processing_time:.0f}ms"
        )

        # 持久化结果到数据库
        await persist_processing_result(session_id, final_result, processing_time)

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
        await persist_processing_error(session_id, error_result)

        return error_result
