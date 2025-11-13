from typing import Any

"""
PDF文本处理服务
支持多种PDF处理引擎和OCR功能
"""

import asyncio
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
from PIL import Image
import os

logger = logging.getLogger(__name__)

try:
    from ...models.pdf_import_session import ProcessingStep, SessionStatus
except ImportError as e:
    logger.warning(f"无法导入pdf_import_session模型: {e}")
    # 定义本地枚举作为后备
    from enum import Enum

    class ProcessingStep(Enum):
        PDF_CONVERSION = "pdf_conversion"
        TEXT_EXTRACTION = "text_extraction"
        INFO_EXTRACTION = "info_extraction"
        DATA_VALIDATION = "data_validation"
        ASSET_MATCHING = "asset_matching"
        DUPLICATE_CHECK = "duplicate_check"
        FINAL_REVIEW = "final_review"

    class SessionStatus(Enum):
        UPLOADING = "uploading"
        PROCESSING = "processing"
        TEXT_EXTRACTED = "text_extracted"
        INFO_EXTRACTED = "info_extracted"
        VALIDATING = "validating"
        VALIDATION_FAILED = "validation_failed"
        MATCHING = "matching"
        MATCHING_FAILED = "matching_failed"
        READY_FOR_REVIEW = "ready_for_review"
        CONFIRMED = "confirmed"
        COMPLETED = "completed"
        FAILED = "failed"
        CANCELLED = "cancelled"


logger = logging.getLogger(__name__)


class PDFProcessingCache:
    """PDF处理缓存�?""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.cache = {}
        self.access_times = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Any:
        """获取缓存�?""
        if key in self.cache:
            # 检查是否过�?
            if time.time() - self.access_times[key] > self.ttl_seconds:
                del self.cache[key]
                del self.access_times[key]
                return None
            self.access_times[key] = time.time()
            return self.cache[key]
        return None

    def set(self, key: str, value: Any):
        """设置缓存�?""
        # 如果缓存已满，清理最旧的�?
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times, key=self.access_times.get)
            del self.cache[oldest_key]
            del self.access_times[oldest_key]

        self.cache[key] = value
        self.access_times[key] = time.time()

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_times.clear()


class PDFProcessingMethod:
    """PDF处理方法枚举"""

    PDFPLUMBER = "pdfplumber"
    PYMUPDF = "pymupdf"
    OCR = "ocr"


class PDFProcessingService:
    """PDF文本处理服务 - 优化版本"""

    def __init__(self):
        # 延迟初始化OCR引擎，避免启动时占用过多资源
        self._ocr_engine = None
        self._ocr_initialized = False
        self._ocr_warmup_in_progress = False
        self.supported_methods = [
            PDFProcessingMethod.PYMUPDF,
            PDFProcessingMethod.PDFPLUMBER,
            PDFProcessingMethod.OCR,
        ]
        # 初始化缓存服�?
        try:
            from .pdf_processing_cache import PDFProcessingCache

            self.cache = PDFProcessingCache()
        except ImportError as e:
            logger.warning(f"无法导入PDF处理缓存: {e}")
            self.cache = None

        # 初始化质量评估器
        try:
            from .pdf_quality_assessment import pdf_quality_assessor

            self.quality_assessor = pdf_quality_assessor
        except ImportError as e:
            logger.warning(f"无法导入质量评估�? {e}")
            self.quality_assessor = None

        # 初始化并发处理优化器
        try:
            from .concurrent_processing_optimizer import concurrent_optimizer

            self.concurrent_optimizer = concurrent_optimizer
            # 启动并发处理�?
            self.concurrent_optimizer.start()
            logger.info("并发处理优化器已启动")
        except ImportError as e:
            logger.warning(f"无法导入并发优化�? {e}")
            self.concurrent_optimizer = None

        # 初始化PDF处理监控�?
        try:
            from .pdf_processing_monitor import pdf_processing_monitor

            self.monitor = pdf_processing_monitor
            self.monitor.start_monitoring()
            logger.info("PDF处理监控器已启动")
        except ImportError as e:
            logger.warning(f"无法导入PDF处理监控�? {e}")
            self.monitor = None

    @property
    def ocr(self):
        """OCR引擎管理"""
        if not self._ocr_initialized and not self._ocr_warmup_in_progress:
            self._ocr_warmup_in_progress = True
            try:
                # 启动OCR引擎预热
                logger.info("开始OCR引擎预热初始�?..")
                # 读取环境变量
                lang = os.getenv("OCR_LANG", "ch")
                use_gpu = os.getenv("OCR_USE_GPU", "false").lower() in {"1", "true", "yes"}
                use_angle_cls = os.getenv("OCR_USE_ANGLE_CLS", "true").lower() in {"1", "true", "yes"}
                enable_mkldnn = os.getenv("OCR_ENABLE_MKLDNN", "true").lower() in {"1", "true", "yes"}
                det_limit_side_len = int(os.getenv("OCR_DET_LIMIT_SIDE_LEN", "960"))
                rec_batch_num = int(os.getenv("OCR_REC_BATCH_NUM", "6"))
                det_db_thresh = float(os.getenv("OCR_DET_DB_THRESH", "0.3"))
                drop_score = float(os.getenv("OCR_DROP_SCORE", "0.5"))
                # 构建基础参数（不包含 show_log 以提高兼容性）
                base_args = {
                    "lang": lang,
                    "use_gpu": use_gpu,
                    "det_limit_side_len": det_limit_side_len,
                    "rec_batch_num": rec_batch_num,
                    "det_db_thresh": det_db_thresh,
                    "drop_score": drop_score,
                }
                if enable_mkldnn:
                    base_args["enable_mkldnn"] = True

                use_textline_orientation = os.getenv("OCR_USE_TEXTLINE_ORIENTATION", "true").lower() in {"1", "true", "yes"}
                try:
                    self._ocr_engine = PaddleOCR(
                        **base_args,
                        use_textline_orientation=use_textline_orientation,
                    )
                except Exception as e:
                    msg = str(e)
                    if "Unknown argument" in msg and "use_textline_orientation" in msg:
                        try:
                            self._ocr_engine = PaddleOCR(
                                **base_args,
                                use_angle_cls=use_angle_cls,
                            )
                        except Exception as e2:
                            if "Unknown argument" in str(e2) and "enable_mkldnn" in str(e2):
                                base_args.pop("enable_mkldnn", None)
                                self._ocr_engine = PaddleOCR(
                                    **base_args,
                                    use_angle_cls=use_angle_cls,
                                )
                            else:
                                raise
                    else:
                        if "Unknown argument" in msg and "enable_mkldnn" in msg:
                            base_args.pop("enable_mkldnn", None)
                            self._ocr_engine = PaddleOCR(
                                **base_args,
                                use_textline_orientation=use_textline_orientation,
                            )
                        else:
                            raise
                self._ocr_initialized = True
                logger.info("OCR引擎预热初始化完�?)
                self._ocr_warmup_in_progress = False
            except Exception as e:
                logger.error(f"OCR引擎预热失败: {e}")
                self._ocr_engine = None
                self._ocr_initialized = False
                self._ocr_warmup_in_progress = False
        elif not self._ocr_initialized:
            # 如果引擎未初始化且没有在预热中，则进行标准初始化
            try:
                logger.info("开始OCR引擎标准初始�?..")
                lang = os.getenv("OCR_LANG", "ch")
                use_gpu = os.getenv("OCR_USE_GPU", "false").lower() in {"1", "true", "yes"}
                use_angle_cls = os.getenv("OCR_USE_ANGLE_CLS", "true").lower() in {"1", "true", "yes"}
                enable_mkldnn = os.getenv("OCR_ENABLE_MKLDNN", "true").lower() in {"1", "true", "yes"}
                det_limit_side_len = int(os.getenv("OCR_DET_LIMIT_SIDE_LEN", "960"))
                rec_batch_num = int(os.getenv("OCR_REC_BATCH_NUM", "6"))
                det_db_thresh = float(os.getenv("OCR_DET_DB_THRESH", "0.3"))
                drop_score = float(os.getenv("OCR_DROP_SCORE", "0.5"))
                base_args = {
                    "lang": lang,
                    "use_gpu": use_gpu,
                    "det_limit_side_len": det_limit_side_len,
                    "rec_batch_num": rec_batch_num,
                    "det_db_thresh": det_db_thresh,
                    "drop_score": drop_score,
                }
                if enable_mkldnn:
                    base_args["enable_mkldnn"] = True

                use_textline_orientation = os.getenv("OCR_USE_TEXTLINE_ORIENTATION", "true").lower() in {"1", "true", "yes"}
                try:
                    self._ocr_engine = PaddleOCR(
                        **base_args,
                        use_textline_orientation=use_textline_orientation,
                    )
                except Exception as e:
                    msg = str(e)
                    if "Unknown argument" in msg and "use_textline_orientation" in msg:
                        try:
                            self._ocr_engine = PaddleOCR(
                                **base_args,
                                use_angle_cls=use_angle_cls,
                            )
                        except Exception as e2:
                            if "Unknown argument" in str(e2) and "enable_mkldnn" in str(e2):
                                base_args.pop("enable_mkldnn", None)
                                self._ocr_engine = PaddleOCR(
                                    **base_args,
                                    use_angle_cls=use_angle_cls,
                                )
                            else:
                                raise
                    else:
                        if "Unknown argument" in msg and "enable_mkldnn" in msg:
                            base_args.pop("enable_mkldnn", None)
                            self._ocr_engine = PaddleOCR(
                                **base_args,
                                use_textline_orientation=use_textline_orientation,
                            )
                        else:
                            raise
                self._ocr_initialized = True
                logger.info("OCR引擎标准初始化完�?)
            except Exception as e:
                logger.error(f"OCR引擎标准初始化失�? {e}")
                self._ocr_engine = None
                self._ocr_initialized = False

        return self._ocr_engine

    async def extract_text_from_pdf(
        self,
        file_path: str,
        method: str | None = None,
        prefer_ocr: bool = False,
        ocr_service: Any | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        从PDF文件提取文本

        Args:
            file_path: PDF文件路径
            method: 指定的处理方�?
            prefer_ocr: 是否优先使用OCR
            **kwargs: 其他配置参数

        Returns:
            包含提取结果和元数据的字�?
        """
        start_time = datetime.now()
        file_path = Path(file_path)

        # 生成会话ID用于监控
        session_id = f"pdf_process_{int(time.time())}_{file_path.stem}"

        # 开始监控会�?
        if self.monitor:
            try:
                from .pdf_processing_monitor import ProcessingStage

                self.monitor.start_session(
                    session_id=session_id,
                    file_name=file_path.name,
                    file_size=file_path.stat().st_size,
                    processing_method=method,
                    prefer_ocr=prefer_ocr,
                )
            except Exception as e:
                logger.warning(f"启动监控会话失败: {e}")

        try:
            # 验证文件
            if not file_path.exists():
                if self.monitor:
                    from .pdf_processing_monitor import LogLevel, ProcessingStage

                    self.monitor.log_event(
                        session_id=session_id,
                        stage=ProcessingStage.VALIDATION,
                        event_type="file_not_found",
                        event_level=LogLevel.ERROR,
                        message=f"文件不存�? {file_path}",
                        details={"file_path": str(file_path)},
                    )
                raise FileNotFoundError(f"文件不存�? {file_path}")

            if file_path.suffix.lower() != ".pdf":
                if self.monitor:
                    from .pdf_processing_monitor import LogLevel, ProcessingStage

                    self.monitor.log_event(
                        session_id=session_id,
                        stage=ProcessingStage.VALIDATION,
                        event_type="invalid_file_format",
                        event_level=LogLevel.ERROR,
                        message=f"不支持的文件格式: {file_path.suffix}",
                        details={
                            "file_path": str(file_path),
                            "file_suffix": file_path.suffix,
                        },
                    )
                raise ValueError(f"不支持的文件格式: {file_path.suffix}")

            # 记录文件验证成功
            if self.monitor:
                from .pdf_processing_monitor import LogLevel, ProcessingStage

                self.monitor.log_event(
                    session_id=session_id,
                    stage=ProcessingStage.VALIDATION,
                    event_type="validation_success",
                    event_level=LogLevel.INFO,
                    message="文件验证通过",
                    details={
                        "file_size": file_path.stat().st_size,
                        "file_format": file_path.suffix,
                    },
                )

            # 选择处理方法
            if method is None:
                method = await self._select_best_method(file_path, prefer_ocr)

            if self.monitor:
                from .pdf_processing_monitor import LogLevel, ProcessingStage

                self.monitor.log_event(
                    session_id=session_id,
                    stage=ProcessingStage.PREPROCESSING,
                    event_type="method_selected",
                    event_level=LogLevel.INFO,
                    message=f"选择处理方法: {method}",
                    details={"method": method, "prefer_ocr": prefer_ocr},
                )

            logger.info(f"开始处理PDF文件: {file_path.name}, 使用方法: {method}")

            # 选择方法后再检查缓存，确保键包含最终方法及参数
            if self.cache:
                try:
                    cache_result = self.cache.get(
                        file_path, method, prefer_ocr=prefer_ocr, **kwargs
                    )
                except Exception as e:
                    logger.warning(f"读取缓存失败: {e}")
                    cache_result = None

                if cache_result:
                    logger.info(f"缓存命中: {file_path.name}")
                    logger.info("使用缓存结果，跳过处�?)

                    if self.monitor:
                        from .pdf_processing_monitor import LogLevel, ProcessingStage

                        self.monitor.log_event(
                            session_id=session_id,
                            stage=ProcessingStage.EXTRACTION,
                            event_type="cache_hit",
                            event_level=LogLevel.INFO,
                            message=f"缓存命中: {file_path.name}",
                            details={"method": method},
                        )

                    return cache_result

            # 根据选择的方法提取文�?
            if method == PDFProcessingMethod.PYMUPDF:
                result = await self._extract_with_pymupdf(file_path, **kwargs)
            elif method == PDFProcessingMethod.PDFPLUMBER:
                result = await self._extract_with_pdfplumber(file_path, **kwargs)
            elif method == PDFProcessingMethod.OCR:
                result = await self._extract_with_ocr(file_path, ocr_service=ocr_service, **kwargs)
            else:
                raise ValueError(f"不支持的PDF处理方法: {method}")

            # 统一结果结构，保证字段一�?
            result = self._normalize_result_structure(result, method, prefer_ocr, kwargs)

            # 添加处理元数�?
            processing_time = (datetime.now() - start_time).total_seconds()
            result.update(
                {
                    "processing_method": method,
                    "processing_time_seconds": processing_time,
                    "file_size_bytes": file_path.stat().st_size,
                    "extracted_at": datetime.now().isoformat(),
                    "ocr_used": method == PDFProcessingMethod.OCR,
                    "success": True,
                }
            )

            # 执行质量评估
            if self.quality_assessor and result.get("text"):
                try:
                    logger.info(f"开始对 {file_path.name} 进行质量评估")
                    quality_assessment = (
                        self.quality_assessor.assess_processing_quality(
                            extracted_data=result.get("extracted_fields", {}),
                            original_text=result.get("text", ""),
                            processing_metadata={
                                "processing_method": method,
                                "processing_time_seconds": processing_time,
                                "file_size_bytes": file_path.stat().st_size,
                                "ocr_used": method == PDFProcessingMethod.OCR,
                                "page_count": result.get("page_count", 1),
                                "dpi": kwargs.get("dpi", 150),
                                "concurrency_used": result.get("concurrency_used"),
                                "pages_per_second": result.get("pages_per_second"),
                            },
                            ocr_results=result.get("ocr_results"),
                        )
                    )
                    result["quality_assessment"] = quality_assessment
                    # 暴露统一的整体置信度字段，供上层使用
                    result["overall_confidence_score"] = quality_assessment.get(
                        "overall_quality_score", 0.8
                    )
                    logger.info(
                        f"质量评估完成 - 总分: {quality_assessment['overall_quality_score']:.3f}, "
                        f"等级: {quality_assessment['quality_level']['description']}"
                    )
                except Exception as e:
                    logger.error(f"质量评估失败: {e}")
                    result["quality_assessment"] = {
                        "overall_quality_score": 0.5,
                        "quality_level": {
                            "level": "unknown",
                            "description": "评估失败",
                        },
                        "error": str(e),
                    }
                    result["overall_confidence_score"] = 0.5

            # 缓存结果（包括质量评估）
            # 在缓存前，构建统一结果包并附加，便于上层持久化
            try:
                envelope = self._build_processing_result_envelope(result, file_path)
                result["processing_result_envelope"] = envelope
            except Exception as e:
                logger.warning(f"构建统一结果包失�? {e}")

            # 缓存结果（包括质量评估与统一包）
            if self.cache:
                try:
                    self.cache.set(
                        file_path, method, result, prefer_ocr=prefer_ocr, **kwargs
                    )
                    logger.debug(f"结果已缓�? {file_path.name}")
                except Exception as e:
                    logger.warning(f"缓存保存失败: {e}")

            logger.info(
                f"PDF处理完成: {file_path.name}, 耗时: {processing_time:.2f}�? "
                f"文本长度: {len(result.get('text', ''))}, "
                f"质量分数: {result.get('quality_assessment', {}).get('overall_quality_score', 'N/A')}"
            )

            return result

        except Exception as e:
            logger.error(f"PDF处理失败: {file_path.name}, 错误: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processing_method": method,
                "processing_time_seconds": (
                    datetime.now() - start_time
                ).total_seconds(),
                "text": "",
                "pages": [],
                "page_count": 0,
                "overall_confidence_score": 0.0,
            }

    def _normalize_result_structure(
        self,
        result: dict[str, Any],
        method: str,
        prefer_ocr: bool,
        kwargs: dict,
    ) -> dict[str, Any]:
        """统一各处理方法的输出结构，保证核心字段一致�?

        目标字段�?
        - text: str
        - pages: list[dict]
        - page_count: int
        - total_pages: int（与page_count一致）
        - ocr_results: list | None
        - overall_confidence_score: float（如已有质量评估，用其overall质量分）
        - extraction_metadata: dict（收敛处理参数）
        """
        normalized = dict(result or {})

        # 标准化文本与页面计数
        if "text" not in normalized:
            normalized["text"] = ""

        pages = normalized.get("pages")
        if not isinstance(pages, list):
            pages = []
        normalized["pages"] = pages

        # page_count与total_pages统一
        if "page_count" not in normalized:
            if "total_pages" in normalized and isinstance(normalized["total_pages"], int):
                normalized["page_count"] = normalized["total_pages"]
            else:
                normalized["page_count"] = len(pages)
        normalized["total_pages"] = normalized.get("total_pages", normalized["page_count"])  # 兼容上游调用

        # 统一ocr_results字段（非OCR路径给空�?
        if "ocr_results" not in normalized:
            normalized["ocr_results"] = None if method != PDFProcessingMethod.OCR else normalized.get("ocr_results")

        # 统一overall_confidence_score（如暂未评估则默�?.8�?
        if "overall_confidence_score" not in normalized:
            qa = normalized.get("quality_assessment")
            if isinstance(qa, dict) and "overall_quality_score" in qa:
                normalized["overall_confidence_score"] = qa.get("overall_quality_score", 0.8)
            else:
                normalized["overall_confidence_score"] = 0.8

        # 聚合处理参数为extraction_metadata
        base_metadata = {
            "prefer_ocr": prefer_ocr,
            "method": method,
        }
        # 仅挑选常见参数字�?
        for key in ("dpi", "max_pages", "enable_preprocessing", "confidence_threshold"):
            if key in kwargs:
                base_metadata[key] = kwargs[key]
        normalized["extraction_metadata"] = {**normalized.get("extraction_metadata", {}), **base_metadata}

        return normalized

    def _build_processing_result_envelope(self, result: dict[str, Any], file_path: Path) -> dict[str, Any]:
        """构建统一处理结果包，稳定对齐API响应字段�?

        该包用于持久化到会话�?processing_result 字段，同时保�?
        现有返回字典不变（非破坏性集成）�?
        """
        # 基础字段
        metrics = {
            "concurrency_used": result.get("concurrency_used"),
            "pages_per_second": result.get("pages_per_second"),
            "processing_time_seconds": result.get("processing_time_seconds"),
        }

        file_info = {
            "file_name": file_path.name,
            "file_size_bytes": result.get("file_size_bytes"),
        }

        envelope = {
            "success": bool(result.get("success", True)),
            "text": result.get("text", ""),
            "pages": result.get("pages", []),
            "total_pages": result.get("total_pages") or result.get("page_count"),
            "processing_method": result.get("processing_method"),
            "ocr_used": result.get("ocr_used"),
            "overall_confidence_score": result.get("overall_confidence_score"),
            "quality_assessment": result.get("quality_assessment"),
            "metrics": metrics,
            "processing_stats": result.get("processing_stats"),
            "extraction_metadata": result.get("extraction_metadata"),
            "file_info": file_info,
            "extracted_at": result.get("extracted_at"),
            "extra": {
                # 兼容保留：保留方法分布、融合方法等扩展信息
                "method_distribution": result.get("method_distribution"),
                "fusion_method": result.get("fusion_method"),
            },
        }

        return envelope

    async def _select_best_method(self, file_path: Path, prefer_ocr: bool) -> str:
        """
        智能选择最佳PDF处理方法 - 增强版本
        """
        try:
            file_size = file_path.stat().st_size

            # 基于文件大小的初步判�?
            if file_size > 20 * 1024 * 1024:  # 20MB以上文件，优先OCR
                logger.info(
                    f"大文件检�?{file_size / 1024 / 1024:.1f}MB)，倾向于OCR处理"
                )

            # 尝试多种方法进行质量评估
            methods_scores = {}

            # 1. PyMuPDF评估
            pymupdf_score = await self._evaluate_pymupdf_quality(file_path)
            methods_scores[PDFProcessingMethod.PYMUPDF] = pymupdf_score

            # 2. PDFPlumber评估
            plumber_score = await self._evaluate_pdfplumber_quality(file_path)
            methods_scores[PDFProcessingMethod.PDFPLUMBER] = plumber_score

            # 3. OCR评估（对小样本）
            if file_size <= 10 * 1024 * 1024:  # 10MB以下才评估OCR
                ocr_score = await self._evaluate_ocr_quality(file_path)
                methods_scores[PDFProcessingMethod.OCR] = ocr_score

            # 选择最佳方�?
            if prefer_ocr:
                return PDFProcessingMethod.OCR

            best_method = max(methods_scores.items(), key=lambda x: x[1])[0]
            logger.info(f"方法评分: {methods_scores}，选择: {best_method}")

            return best_method

        except Exception as e:
            logger.error(f"选择处理方法失败: {e}")
            return PDFProcessingMethod.PYMUPDF  # 默认使用PyMuPDF

    async def _evaluate_pymupdf_quality(self, file_path: Path) -> float:
        """评估PyMuPDF处理质量"""
        try:
            doc = fitz.open(file_path)
            text_samples = []
            total_chars = 0
            chinese_chars = 0

            # 检查前5�?
            for page_num in range(min(5, len(doc))):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_samples.append(text)
                    total_chars += len(text)
                    chinese_chars += len(re.findall(r"[\u4e00-\u9fff]", text))

            doc.close()

            if not text_samples:
                return 0.0

            # 计算质量分数
            avg_text_length = len(text_samples) / len(text_samples)
            chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0

            # 评分标准
            score = 0.0
            # 文本长度分数�?-30分）
            score += min(avg_text_length / 10, 30)
            # 中文字符比例分数�?-40分）
            score += min(chinese_ratio * 80, 40)
            # 页面覆盖分数�?-30分）
            score += (len(text_samples) / 5) * 30

            return min(score, 100.0)

        except Exception as e:
            logger.warning(f"PyMuPDF质量评估失败: {e}")
            return 0.0

    async def _evaluate_pdfplumber_quality(self, file_path: Path) -> float:
        """评估PDFPlumber处理质量"""
        try:
            total_text = ""
            page_count = 0

            with pdfplumber.open(file_path) as pdf:
                for page in pdf[:5]:  # 检查前5�?
                    text = page.extract_text() or ""
                    if text.strip():
                        total_text += text
                        page_count += 1

            if not total_text:
                return 0.0

            # 基于文本质量和结构评�?
            lines = total_text.split("\n")
            meaningful_lines = [line for line in lines if len(line.strip()) > 5]

            score = 0.0
            # 有效行数分数�?-40分）
            score += min(len(meaningful_lines) / 10, 40)
            # 文本密度分数�?-30分）
            score += min(len(total_text) / 100, 30)
            # 页面覆盖分数�?-30分）
            score += (page_count / 5) * 30

            return min(score, 100.0)

        except Exception as e:
            logger.warning(f"PDFPlumber质量评估失败: {e}")
            return 0.0

    async def _evaluate_ocr_quality(self, file_path: Path) -> float:
        """评估OCR处理质量（仅小文件）"""
        try:
            # 转换第一页为图片进行OCR测试
            images = convert_from_path(file_path, first_page=1, last_page=1, dpi=150)
            if not images:
                return 0.0

            image = images[0]
            result = self.ocr.ocr(image, cls=True)

            if not result or not result[0]:
                return 0.0

            # 提取文本
            text_lines = []
            for line in result[0]:
                if line[1][0]:  # 置信�?
                    text_lines.append(line[1][0])

            text = "\n".join(text_lines)

            # 评分标准
            score = 0.0
            # 文本行数分数�?-40分）
            score += min(len(text_lines) / 20, 40)
            # 文本长度分数�?-30分）
            score += min(len(text) / 50, 30)
            # 中文字符检测（0-30分）
            chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
            score += min(chinese_chars / 10, 30)

            return min(score, 100.0)

        except Exception as e:
            logger.warning(f"OCR质量评估失败: {e}")
            return 0.0

    async def _is_scanned_pdf(self, file_path: Path) -> bool:
        """检查PDF是否为扫描版（保留原方法作为备用�?""
        try:
            doc = fitz.open(str(file_path))
            text_content = ""

            # 检查前3页的文本内容
            for page in doc[: min(3, len(doc))]:
                text_content += page.get_text()

            doc.close()

            # 如果文本很少，可能是扫描�?
            text_threshold = 100  # 字符数阈�?
            return len(text_content.strip()) < text_threshold

        except Exception as e:
            logger.warning(f"检查扫描版PDF失败: {str(e)}")
            return False  # 默认认为不是扫描�?

    async def _extract_with_pymupdf(self, file_path: Path, **kwargs) -> dict[str, Any]:
        """使用PyMuPDF提取文本"""
        doc = fitz.open(str(file_path))
        pages_text = []
        full_text = ""

        for page_num, page in enumerate(doc, 1):
            try:
                # 提取文本
                text = page.get_text()

                # 提取图像信息（如果有�?
                images = []
                for img_index, img in enumerate(page.get_images()):
                    try:
                        images.append(
                            {
                                "index": img_index,
                                "xref": img[0],
                                "width": img[2],
                                "height": img[3],
                                "type": img[-1],
                            }
                        )
                    except (Exception, ValueError, TypeError):
                        # API处理失败时跳过当前项
                        continue

                page_info = {
                    "page_number": page_num,
                    "text": text,
                    "text_length": len(text),
                    "images_count": len(images),
                    "images": images,
                }

                pages_text.append(page_info)
                full_text += text + "\n"

            except Exception as e:
                logger.warning(f"提取第{page_num}页文本失�? {str(e)}")
                continue

        doc.close()

        return {
            "text": full_text.strip(),
            "pages": pages_text,
            "total_pages": len(pages_text),
            "chinese_char_count": len(
                [c for c in full_text if "\u4e00" <= c <= "\u9fff"]
            ),
            "english_char_count": len(
                [c for c in full_text if c.isalpha() and ord(c) < 128]
            ),
        }

    async def _extract_with_pdfplumber(
        self, file_path: Path, **kwargs
    ) -> dict[str, Any]:
        """使用pdfplumber提取文本"""
        pages_text = []
        full_text = ""

        with pdfplumber.open(str(file_path)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    text = page.extract_text()

                    # 提取表格数据
                    tables = []
                    for table in page.extract_tables():
                        if table and any(
                            row for row in table if any(cell for cell in row)
                        ):
                            tables.append(
                                {
                                    "data": table,
                                    "rows": len(table),
                                    "columns": len(table[0]) if table else 0,
                                }
                            )

                    page_info = {
                        "page_number": page_num,
                        "text": text or "",
                        "text_length": len(text or ""),
                        "tables_count": len(tables),
                        "tables": tables,
                        "width": page.width,
                        "height": page.height,
                    }

                    pages_text.append(page_info)
                    if text:
                        full_text += text + "\n"

                except Exception as e:
                    logger.warning(f"pdfplumber提取第{page_num}页失�? {str(e)}")
                    continue

        return {
            "text": full_text.strip(),
            "pages": pages_text,
            "total_pages": len(pages_text),
            "chinese_char_count": len(
                [c for c in full_text if "\u4e00" <= c <= "\u9fff"]
            ),
            "english_char_count": len(
                [c for c in full_text if c.isalpha() and ord(c) < 128]
            ),
        }

    async def _extract_with_ocr(self, file_path: Path, ocr_service: Any | None = None, **kwargs) -> dict[str, Any]:
        """使用OCR提取文本 - 统一接入优化OCR服务"""
        max_pages = kwargs.get("max_pages", 10)
        max_concurrency = kwargs.get("max_concurrency")
        use_preprocessing = kwargs.get("enable_preprocessing", True)

        # 优先使用注入�?OCR 服务；否则通过提供者获�?
        try:
            if ocr_service is None:
                from .providers.ocr_provider import get_ocr_service as _get
                ocr_service = _get()

            ocr_summary = await ocr_service.process_pdf_document(
                pdf_path=str(file_path),
                max_pages=max_pages,
                max_concurrency=max_concurrency,
                use_preprocessing=use_preprocessing,
            )

            if not ocr_summary.get("success", False):
                # 回退到原有OCR路径
                raise RuntimeError(ocr_summary.get("error", "优化OCR失败"))

            # 构建统一结果结构（初始字典，后续由_normalize_result_structure补充�?
            page_results = ocr_summary.get("page_results", [])
            pages_text = []
            for pr in page_results:
                try:
                    pn = int(pr.get("page_number", 0)) + 1
                except Exception:
                    pn = 1
                text = pr.get("text", "")
                confidence = float(pr.get("confidence", 0.0) or 0.0)

                pages_text.append(
                    {
                        "page_number": pn,
                        "text": text,
                        "text_length": len(text),
                        "confidence_score": confidence,
                        "ocr_used": True,
                    }
                )

            overall_conf = float(ocr_summary.get("avg_confidence", 0.0) or 0.0)

            return {
                "text": ocr_summary.get("combined_text", ""),
                "pages": pages_text,
                "total_pages": int(ocr_summary.get("total_pages", len(pages_text)) or len(pages_text)),
                "overall_confidence_score": overall_conf,
                "ocr_used": True,
                "quality_assessment": ocr_summary.get("quality_assessment", {}),
                "processing_stats": ocr_summary.get("processing_stats", {}),
                "concurrency_used": int(ocr_summary.get("concurrency_used", 0) or 0),
                "pages_per_second": float(ocr_summary.get("pages_per_second") or 0.0),
            }

        except Exception as e:
            logger.warning(f"优化OCR接入失败，回退到内部OCR实现: {e}")

            # 原内部OCR路径（保持作为稳健后备）
            dpi = kwargs.get("dpi", 300)
            try:
                images = convert_from_path(
                    str(file_path),
                    dpi=dpi,
                    first_page=1,
                    last_page=max_pages,
                    thread_count=4,
                    grayscale=True,
                    size=(2000, None),
                )
            except Exception as ex:
                raise Exception(f"PDF转图像失�? {str(ex)}")

            pages_text = []
            full_text = ""

            for page_num, image in enumerate(images, 1):
                try:
                    import cv2
                    import numpy as np

                    img_array = np.array(image)
                    if len(img_array.shape) == 3:
                        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

                    img_array = cv2.adaptiveThreshold(
                        img_array,
                        255,
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY,
                        11,
                        2,
                    )

                    result = self.ocr.ocr(img_array, cls=True)

                    page_text = ""
                    confidences = []
                    if result and result[0]:
                        for line in result[0]:
                            if line and len(line) >= 2:
                                try:
                                    box, (text, confidence) = line
                                    if text and confidence > 0.5:
                                        page_text += text + "\n"
                                        confidences.append(confidence)
                                except (IndexError, TypeError):
                                    continue

                    avg_confidence = (
                        sum(confidences) / len(confidences) if confidences else 0
                    )
                    page_text = self._post_process_ocr_text(page_text)

                    pages_text.append(
                        {
                            "page_number": page_num,
                            "text": page_text.strip(),
                            "text_length": len(page_text),
                            "confidence_score": avg_confidence,
                            "ocr_used": True,
                        }
                    )
                    full_text += page_text + "\n"

                except Exception:
                    continue

            all_confidences = [p.get("confidence_score", 0) for p in pages_text if p.get("confidence_score")]
            overall_confidence = (
                sum(all_confidences) / len(all_confidences) if all_confidences else 0
            )

            return {
                "text": full_text.strip(),
                "pages": pages_text,
                "total_pages": len(pages_text),
                "overall_confidence_score": overall_confidence,
                "ocr_used": True,
            }

    def _post_process_ocr_text(self, text: str) -> str:
        """OCR文本后处�?""
        if not text:
            return text

        # 清理常见的OCR错误
        text = text.strip()

        # 移除多余的空�?
        text = "\n".join(line for line in text.split("\n") if line.strip())

        # 修复常见的标点符号错�?
        replacements = {
            "，�?: "�?,
            "。�?: "�?,
            "，，": "�?,
            "？？": "�?,
            "！！": "�?,
            "�?": "�?,
            " �?: "�?,
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    async def extract_multiple_pdfs_concurrent(
        self,
        file_paths: list[str],
        method: str | None = None,
        prefer_ocr: bool = False,
        max_concurrency: int | None = None,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        并发处理多个PDF文件

        Args:
            file_paths: PDF文件路径列表
            method: 指定的处理方�?
            prefer_ocr: 是否优先使用OCR
            max_concurrency: 最大并发数
            **kwargs: 其他配置参数

        Returns:
            处理结果列表
        """
        if not self.concurrent_optimizer:
            logger.warning("并发优化器不可用，回退到串行处�?)
            results = []
            for file_path in file_paths:
                result = await self.extract_text_from_pdf(
                    file_path, method, prefer_ocr, **kwargs
                )
                results.append(result)
            return results

        # 限制并发�?
        if max_concurrency is None:
            stats = self.concurrent_optimizer.get_statistics()
            max_concurrency = min(4, stats.get("optimal_concurrency", 4))

        logger.info(
            f"开始并发处�?{len(file_paths)} 个PDF文件，最大并发数: {max_concurrency}"
        )

        # 创建任务
        tasks = []
        for i, file_path in enumerate(file_paths):
            task_id = f"pdf_process_{i}_{Path(file_path).name}"
            try:
                from .concurrent_processing_optimizer import TaskPriority

                task_id = self.concurrent_optimizer.submit_task(
                    task_id=task_id,
                    func=self._extract_single_pdf_wrapper,
                    args=(file_path, method, prefer_ocr),
                    kwargs=kwargs,
                    priority=TaskPriority.NORMAL,
                    estimated_duration=30.0,  # 估算30�?
                    resource_requirements={
                        "cpu_intensive": True,
                        "memory_intensive": True,
                        "io_intensive": True,
                    },
                )
                tasks.append(task_id)
            except Exception as e:
                logger.error(f"提交任务失败: {task_id}, 错误: {e}")
                # 创建失败结果
                tasks.append(f"failed_{task_id}")

        # 等待所有任务完�?
        results = [None] * len(file_paths)
        completed_count = 0

        start_time = time.time()
        timeout = max(300, len(file_paths) * 60)  # 至少5分钟，每文件额外1分钟

        while (
            completed_count < len(file_paths) and (time.time() - start_time) < timeout
        ):
            await asyncio.sleep(1)  # 检查间�?

            for i, task_id in enumerate(tasks):
                if task_id.startswith("failed_"):
                    if results[i] is None:
                        results[i] = {
                            "success": False,
                            "error": "任务提交失败",
                            "file_path": file_paths[i],
                        }
                        completed_count += 1

        logger.info(
            f"并发处理完成，处理文件数: {len(results)}, 耗时: {time.time() - start_time:.2f}�?
        )
        return results

    def _extract_single_pdf_wrapper(
        self, file_path: str, method: str | None, prefer_ocr: bool, **kwargs
    ) -> dict[str, Any]:
        """
        单个PDF文件提取的包装器（用于并发处理）
        """
        import asyncio

        try:
            # 由于在线程池中运行，需要创建新的事件循�?
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 同步调用异步方法
            result = loop.run_until_complete(
                self.extract_text_from_pdf(file_path, method, prefer_ocr, **kwargs)
            )
            loop.close()
            return result

        except Exception as e:
            logger.error(f"PDF处理包装器异�? {file_path}, 错误: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path,
                "processing_method": method,
                "text": "",
                "pages": [],
            }

    def get_concurrent_stats(self) -> dict[str, Any]:
        """获取并发处理统计信息"""
        if self.concurrent_optimizer:
            return self.concurrent_optimizer.get_statistics()
        return {"concurrent_optimizer_available": False, "message": "并发优化器不可用"}

    def cleanup_concurrent_resources(self):
        """清理并发处理资源"""
        if self.concurrent_optimizer:
            try:
                self.concurrent_optimizer.stop()
                logger.info("并发处理资源已清�?)
            except Exception as e:
                logger.error(f"清理并发资源失败: {e}")

    async def extract_text_from_image(
        self, image_path: str, **kwargs
    ) -> dict[str, Any]:
        """从图像文件提取文本（OCR�?""
        start_time = datetime.now()

        try:
            # 打开图像
            image = Image.open(image_path)

            # OCR识别
            result = self.ocr.ocr(image, cls=True)

            # 提取文本
            text = ""
            confidences = []

            for line in result:
                if line:
                    for word_info in line:
                        if word_info:
                            text_line, confidence = word_info[1], word_info[2]
                            text += text_line + "\n"
                            confidences.append(confidence)

            # 计算置信�?
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            processing_time = (datetime.now() - start_time).total_seconds()

            return {
                "success": True,
                "text": text.strip(),
                "confidence_score": avg_confidence,
                "processing_time_seconds": processing_time,
                "ocr_used": True,
                "chinese_char_count": len(
                    [c for c in text if "\u4e00" <= c <= "\u9fff"]
                ),
                "english_char_count": len(
                    [c for c in text if c.isalpha() and ord(c) < 128]
                ),
            }

        except Exception as e:
            logger.error(f"图像OCR失败: {image_path}, 错误: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "confidence_score": 0,
                "processing_time_seconds": (
                    datetime.now() - start_time
                ).total_seconds(),
            }


# 创建全局实例
pdf_processing_service = PDFProcessingService()
