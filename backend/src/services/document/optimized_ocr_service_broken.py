#!/usr/bin/env python
from typing import Any

"""
优化的OCR服务
解决PaddleOCR数据类型和API兼容性问题，提供高性能扫描件处理
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)
import os


@dataclass
class OCRResult:
    """OCR处理结果"""

    text: str
    confidence: float
    processing_time: float
    method_used: str
    page_number: int
    image_quality: str = "unknown"
    bbox_count: int = 0


@dataclass
class ProcessingStats:
    """处理统计信息"""

    total_pages: int
    processed_pages: int
    total_text_length: int
    avg_confidence: float
    total_processing_time: float
    pages_with_text: int
    pages_without_text: int
    # 线程卸载统计与派生指标
    thread_offloads_total: int = 0
    thread_offloads_detail: dict[str, int] = field(default_factory=dict)
    avg_page_time_seconds: float = 0.0
    pages_per_second: float = 0.0


class OptimizedOCRService:
    """优化的OCR服务"""

    def __init__(self):
        self.ocr_engines = {}
        self.stats = ProcessingStats(
            total_pages=0,
            processed_pages=0,
            total_text_length=0,
            avg_confidence=0.0,
            total_processing_time=0.0,
            pages_with_text=0,
            pages_without_text=0,
        )
        self._initialize_engines()

    def _initialize_engines(self):
        """初始化OCR引擎"""
        try:
            # 初始化PaddleOCR（优化参数）
            from paddleocr import PaddleOCR

            # 从环境变量读取配置（提供合理默认值）
            lang = os.getenv("OCR_LANG", "ch")
            use_gpu = os.getenv("OCR_USE_GPU", "false").lower() in {"1", "true", "yes"}
            use_angle_cls = os.getenv("OCR_USE_ANGLE_CLS", "true").lower() in {"1", "true", "yes"}
            enable_mkldnn = os.getenv("OCR_ENABLE_MKLDNN", "true").lower() in {"1", "true", "yes"}
            det_limit_side_len = int(os.getenv("OCR_DET_LIMIT_SIDE_LEN", "960"))
            rec_batch_num = int(os.getenv("OCR_REC_BATCH_NUM", "6"))
            det_db_thresh = float(os.getenv("OCR_DET_DB_THRESH", "0.3"))
            drop_score = float(os.getenv("OCR_DROP_SCORE", "0.5"))

            # 构建基础参数（不包含可能不兼容的 show_log）
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

            # 优先使用新版参数 use_textline_orientation；如果不支持则回退到use_angle_cls
            use_textline_orientation = os.getenv("OCR_USE_TEXTLINE_ORIENTATION", "true").lower() in {"1", "true", "yes"}

            try:
                self.ocr_engines["paddleocr"] = PaddleOCR(
                    **base_args,
                    use_textline_orientation=use_textline_orientation,
                )
            except Exception as e:
                msg = str(e)
                if "Unknown argument" in msg and "use_textline_orientation" in msg:
                    # 回退为旧参数
                    try:
                        self.ocr_engines["paddleocr"] = PaddleOCR(
                            **base_args,
                            use_angle_cls=use_angle_cls,
                        )
                    except Exception as e2:
                        # 如果 enable_mkldnn 导致不兼容，再次回退去掉它
                        if "Unknown argument" in str(e2) and "enable_mkldnn" in str(e2):
                            base_args.pop("enable_mkldnn", None)
                            self.ocr_engines["paddleocr"] = PaddleOCR(
                                **base_args,
                                use_angle_cls=use_angle_cls,
                            )
                        else:
                            raise
                else:
                    # 其他未知参数，尝试移除MKLDNN 再试一次
                    if "Unknown argument" in msg and "enable_mkldnn" in msg:
                        base_args.pop("enable_mkldnn", None)
                        self.ocr_engines["paddleocr"] = PaddleOCR(
                            **base_args,
                            use_textline_orientation=use_textline_orientation,
                        )
                    else:
                        raise
            logger.info("PaddleOCR引擎初始化成功")

        except Exception as e:
            logger.error(f"PaddleOCR初始化失败: {e}")
            self.ocr_engines["paddleocr"] = None

    def _convert_pdf_page_to_numpy(self, page) -> np.ndarray | None:
        """将PDF页面转换为numpy数组"""
        try:
            import fitz  # PyMuPDF

            # 使用更高分辨率获取图像
            matrix = fitz.Matrix(3.0, 3.0)  # 3倍分辨率
            pix = page.get_pixmap(matrix=matrix)

            # 转换为numpy数组
            img_data = pix.samples
            width = pix.width
            height = pix.height

            if pix.n == 4:  # RGBA
                img_array = np.frombuffer(img_data, dtype=np.uint8).reshape(
                    (height, width, 4)
                )
                img_array = img_array[:, :, :3]  # 移除alpha通道
            elif pix.n == 3:  # RGB
                img_array = np.frombuffer(img_data, dtype=np.uint8).reshape(
                    (height, width, 3)
                )
            elif pix.n == 1:  # 灰度
                img_array = np.frombuffer(img_data, dtype=np.uint8).reshape(
                    (height, width)
                )
                # 转换为RGB格式
                img_array = np.stack([img_array, img_array, img_array], axis=2)
            else:
                logger.warning(f"不支持的图像格式: {pix.n}通道")
                return None

            return img_array

        except Exception as e:
            logger.error(f"PDF页面转换为numpy数组失败: {e}")
            return None

    def _preprocess_image(self, img_array: np.ndarray) -> np.ndarray:
        """图像预处理优化""
        try:
            import cv2  # OpenCV用于图像处理

            # 1. 转换为灰度图
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array.copy()

            # 2. 增强对比秒
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)

            # 3. 降噪
            denoised = cv2.fastNlMeansDenoising(
                enhanced, None, h=10, templateWindowSize=7, searchWindowSize=21
            )

            # 4. 锐化
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)

            # 5. 二值化处理（可选，根据图像质量决定秒
            _, binary = cv2.threshold(
                sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            # 转换秒通道格式供OCR使用
            result = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)

            return result

        except ImportError:
            logger.warning("OpenCV未安装，跳过图像预处理)
            return img_array
        except Exception as e:
            logger.error(f"图像预处理失败 {e}")
            return img_array

    def _process_with_paddleocr(
        self, img_array: np.ndarray, page_num: int
    ) -> OCRResult:
        """使用PaddleOCR处理图像"""
        start_time = time.time()

        try:
            if self.ocr_engines["paddleocr"] is None:
                return OCRResult(
                    text="",
                    confidence=0.0,
                    processing_time=0.0,
                    method_used="paddleocr_failed",
                    page_number=page_num,
                )

            # 使用numpy数组进行OCR（移除cls参数以兼容新版本
            try:
                # 尝试使用新版本的predict方法
                result = self.ocr_engines["paddleocr"].predict(img_array)
            except (TypeError, AttributeError):
                # 如果predict方法不可用，回退到ocr方法
                result = self.ocr_engines["paddleocr"].ocr(img_array)
            processing_time = time.time() - start_time

            if result and len(result) > 0 and result[0]:
                # 提取所有文本
                texts = []
                confidences = []
                bboxes = []

                for line in result[0]:
                    if line and len(line) >= 2:
                        text = line[1][0]
                        confidence = line[1][1]
                        bbox = line[0]

                        texts.append(text)
                        confidences.append(confidence)
                        bboxes.append(bbox)

                combined_text = "\n".join(texts)
                avg_confidence = np.mean(confidences) if confidences else 0.0

                logger.info(
                    f"页面 {page_num + 1} OCR成功: {len(texts)}行文本 平均置信度 {avg_confidence:.3f}"
                )

                return OCRResult(
                    text=combined_text,
                    confidence=avg_confidence,
                    processing_time=processing_time,
                    method_used="paddleocr",
                    page_number=page_num,
                    bbox_count=len(bboxes),
                    image_quality="preprocessed",
                )
            else:
                logger.warning(f"页面 {page_num + 1} OCR未识别到文本")
                return OCRResult(
                    text="",
                    confidence=0.0,
                    processing_time=processing_time,
                    method_used="paddleocr_no_text",
                    page_number=page_num,
                )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"页面 {page_num + 1} PaddleOCR处理失败: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                processing_time=processing_time,
                method_used="paddleocr_error",
                page_number=page_num,
            )

    def _extract_text_with_pymupdf(self, page, page_num: int) -> OCRResult:
        """使用PyMuPDF提取文本作为补充"""
        start_time = time.time()

        try:
            text = page.get_text()
            processing_time = time.time() - start_time

            if text and len(text.strip()) > 0:
                logger.info(f"页面 {page_num + 1} PyMuPDF文本提取成功: {len(text)}字符")
                return OCRResult(
                    text=text.strip(),
                    confidence=1.0,  # 原生文本置信度最秒
                    processing_time=processing_time,
                    method_used="pymupdf",
                    page_number=page_num,
                    image_quality="native_text",
                )
            else:
                return OCRResult(
                    text="",
                    confidence=0.0,
                    processing_time=processing_time,
                    method_used="pymupdf_no_text",
                    page_number=page_num,
                )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"页面 {page_num + 1} PyMuPDF文本提取失败: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                processing_time=processing_time,
                method_used="pymupdf_error",
                page_number=page_num,
            )

    async def process_pdf_page(
        self, page, page_num: int, use_preprocessing: bool = True
    ) -> OCRResult:
        """处理单个PDF页面"""
        logger.info(f"开始处理页面{page_num + 1}")

        results = []

        # 1. 尝试PyMuPDF文本提取
        try:
            pymupdf_result = await asyncio.to_thread(
                self._extract_text_with_pymupdf, page, page_num
            )
            # 记录线程卸载
            self._record_thread_offload("pymupdf_text")
        except Exception as e:
            logger.error(f"页面 {page_num + 1} PyMuPDF线程卸载提取失败: {e}")
            pymupdf_result = self._extract_text_with_pymupdf(page, page_num)
        results.append(pymupdf_result)

        # 2. 如果没有原生文本，使用OCR
        if len(pymupdf_result.text) < 10:  # 原生文本很少，使用OCR
            try:
                # 转换为numpy数组
                try:
                    img_array = await asyncio.to_thread(
                        self._convert_pdf_page_to_numpy, page
                    )
                    self._record_thread_offload("page_to_numpy")
                except Exception as e:
                    logger.error(
                        f"页面 {page_num + 1} 线程卸载页面到numpy失败: {e}"
                    )
                    img_array = self._convert_pdf_page_to_numpy(page)

                if img_array is not None:
                    # 图像预处秒
                    if use_preprocessing:
                        try:
                            img_array = await asyncio.to_thread(
                                self._preprocess_image, img_array
                            )
                            self._record_thread_offload("preprocess_image")
                        except Exception as e:
                            logger.error(
                                f"页面 {page_num + 1} 线程卸载图像预处理失败 {e}"
                            )
                            img_array = self._preprocess_image(img_array)

                    # PaddleOCR处理
                    try:
                        ocr_result = await asyncio.to_thread(
                            self._process_with_paddleocr, img_array, page_num
                        )
                        self._record_thread_offload("paddleocr")
                    except Exception as e:
                        logger.error(
                            f"页面 {page_num + 1} 线程卸载PaddleOCR失败: {e}"
                        )
                        ocr_result = self._process_with_paddleocr(
                            img_array, page_num
                        )
                    results.append(ocr_result)

            except Exception as e:
                logger.error(f"页面 {page_num + 1} OCR处理异常: {e}")

        # 3. 选择最佳结果
        best_result = max(results, key=lambda r: (len(r.text), r.confidence))

        logger.info(
            f"页面 {page_num + 1} 处理完成，最佳方法 {best_result.method_used}"
        )
        return best_result

    async def process_pdf_document(
        self,
        pdf_path: str,
        max_pages: int = 10,
        max_concurrency: int | None = None,
        use_preprocessing: bool = True,
    ) -> dict[str, Any]:
        """处理整个PDF文档"""
        logger.info(f"开始处理PDF文档: {Path(pdf_path).name}")

        start_time = time.time()

        try:
            import fitz

            doc = fitz.open(pdf_path)
            total_pages = min(doc.page_count, max_pages)

            self.stats.total_pages = total_pages
            self.stats.processed_pages = 0
            self.stats.total_text_length = 0
            self.stats.pages_with_text = 0
            self.stats.pages_without_text = 0

            all_results = []
            total_text = ""
            all_confidences = []

            # 并行处理页面（自适应并发数）
            concurrency = self._compute_optimal_concurrency(total_pages)
            if isinstance(max_concurrency, int) and max_concurrency > 0:
                concurrency = max(1, min(concurrency, max_concurrency))
            semaphore = asyncio.Semaphore(concurrency)
            logger.info(f"使用并发数 {concurrency}")

            async def process_page_with_semaphore(page_num):
                async with semaphore:
                    page = doc[page_num]
                    result = await self.process_pdf_page(
                        page, page_num, use_preprocessing=use_preprocessing
                    )
                    return result

            # 创建任务
            tasks = [process_page_with_semaphore(i) for i in range(total_pages)]

            # 等待所有任务完成
            page_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            for i, result in enumerate(page_results):
                if isinstance(result, Exception):
                    logger.error(f"页面 {i + 1} 处理异常: {result}")
                    continue

                all_results.append(result)
                total_text += result.text + "\n\n"

                if result.confidence > 0:
                    all_confidences.append(result.confidence)
                    self.stats.pages_with_text += 1
                else:
                    self.stats.pages_without_text += 1

                self.stats.total_text_length += len(result.text)
                self.stats.processed_pages += 1

            doc.close()

            # 计算统计信息
            total_processing_time = time.time() - start_time
            avg_confidence = np.mean(all_confidences) if all_confidences else 0.0

            self.stats.total_processing_time = total_processing_time
            self.stats.avg_confidence = avg_confidence
            # 衍生指标
            self.stats.avg_page_time_seconds = (
                total_processing_time / self.stats.processed_pages
                if self.stats.processed_pages > 0
                else 0.0
            )
            self.stats.pages_per_second = (
                total_pages / total_processing_time if total_processing_time > 0 else 0.0
            )

            # 构建返回结果
            processing_summary = {
                "success": True,
                "pdf_path": pdf_path,
                "total_pages": total_pages,
                "processing_stats": self.stats.__dict__,
                "page_results": [r.__dict__ for r in all_results],
                "combined_text": total_text.strip(),
                "text_length": len(total_text.strip()),
                "avg_confidence": avg_confidence,
                "total_processing_time": total_processing_time,
                "pages_per_second": total_pages / total_processing_time
                if total_processing_time > 0
                else 0,
                "method_distribution": self._get_method_distribution(all_results),
                "quality_assessment": self._assess_quality(all_results),
                "concurrency_used": concurrency,
            }

            logger.info(
                f"PDF处理完成: {total_pages}秒 {len(total_text)}字符, 用时{total_processing_time:.2f}秒
            )

            return processing_summary

        except Exception as e:
            logger.error(f"PDF文档处理失败: {e}")
            return {"success": False, "error": str(e), "pdf_path": pdf_path}

    def _compute_optimal_concurrency(self, total_pages: int) -> int:
        """根据系统资源与处理负载自适应计算并发数""
        try:
            import os
            cpu = os.cpu_count() or 4
        except Exception:
            cpu = 4

        # 基线并发：CPU一半，范围[2, 8]
        base = max(2, min(8, cpu // 2))

        # PaddleOCR较重，减少并发上限
        if getattr(self, "paddle_ocr", None) is not None:
            base = min(base, 4)

        # 若OpenCV不可用，预处理能力受限，略降并发
        try:
            opencv_ok = self._check_opencv_availability()
        except Exception:
            opencv_ok = False
        if not opencv_ok:
            base = min(base, 3)

        # 小文档无需高并发
        if total_pages <= 2:
            return max(1, total_pages)

        return max(1, min(base, total_pages))

    def _get_method_distribution(self, results: list[OCRResult]) -> dict[str, int]:
        """获取方法使用分布"""
        distribution = {}
        for result in results:
            method = result.method_used
            distribution[method] = distribution.get(method, 0) + 1
        return distribution

    def _assess_quality(self, results: list[OCRResult]) -> dict[str, Any]:
        """评估处理质量"""
        successful_results = [r for r in results if r.confidence > 0]

        if not successful_results:
            return {
                "overall_quality": "poor",
                "text_coverage": 0.0,
                "avg_confidence": 0.0,
                "recommendation": "所有页面处理失败，建议检查PDF质量",
            }

        avg_confidence = np.mean([r.confidence for r in successful_results])
        text_pages = len([r for r in successful_results if len(r.text) > 0])
        coverage = text_pages / len(results)

        if avg_confidence >= 0.8 and coverage >= 0.8:
            quality = "excellent"
            recommendation = "处理质量优秀"
        elif avg_confidence >= 0.6 and coverage >= 0.6:
            quality = "good"
            recommendation = "处理质量良好"
        elif avg_confidence >= 0.4 and coverage >= 0.4:
            quality = "acceptable"
            recommendation = "处理质量可接受，建议优化图像质量"
        else:
            quality = "poor"
            recommendation = "处理质量较差，建议提高DPI或使用专业OCR工具"

        return {
            "overall_quality": quality,
            "text_coverage": coverage,
            "avg_confidence": avg_confidence,
            "recommendation": recommendation,
            "pages_with_high_confidence": len(
                [r for r in successful_results if r.confidence >= 0.8]
            ),
            "pages_with_text": text_pages,
        }

    async def extract_structured_data(
        self, ocr_result: dict[str, Any]
    ) -> dict[str, Any]:
        """提取结构化数据""
        try:
            from .chinese_nlp_processor import get_chinese_nlp_processor

            processor = get_chinese_nlp_processor()
            text = ocr_result.get("combined_text", "")

            if len(text) < 10:
                return {
                    "success": False,
                    "error": "文本长度不足，无法进行结构化提取",
                    "entities_found": 0,
                }

            # 使用中文NLP处理器提取结构化数据
            nlp_result = processor.process_chinese_text(text)

            structured_data = {
                "success": True,
                "entities": nlp_result.get("entities", []),
                "names": nlp_result.get("names", []),
                "phones": nlp_result.get("phones", []),
                "addresses": nlp_result.get("addresses", []),
                "amounts": nlp_result.get("amounts", []),
                "dates": nlp_result.get("dates", []),
                "id_cards": nlp_result.get("id_cards", []),
                "entities_found": len(nlp_result.get("entities", [])),
                "extraction_quality": "good"
                if len(nlp_result.get("entities", [])) > 5
                else "limited",
            }

            logger.info(
                f"结构化数据提取完成 {structured_data['entities_found']}个实体
            )
            return structured_data

        except Exception as e:
            logger.error(f"结构化数据提取失败 {e}")
            return {"success": False, "error": str(e), "entities_found": 0}

    def get_performance_report(self) -> dict[str, Any]:
        """获取性能报告"""
        return {
            "service_status": "ready",
            "ocr_engines": {
                "paddleocr": self.ocr_engines["paddleocr"] is not None,
                "opencv": self._check_opencv_availability(),
            },
            "processing_stats": self.stats.__dict__,
            "capabilities": {
                "image_preprocessing": True,
                "numpy_conversion": True,
                "parallel_processing": True,
                "structured_extraction": True,
                "quality_assessment": True,
            },
            "recommendations": self._get_optimization_recommendations(),
        }

    def _check_opencv_availability(self) -> bool:
        """检查OpenCV可用性""
        try:
            import cv2  # noqa: F401

            return True
        except ImportError:
            return False

    def _get_optimization_recommendations(self) -> list[str]:
        """获取优化建议"""
        recommendations = []

        if not self.ocr_engines["paddleocr"]:
            recommendations.append("建议安装PaddleOCR以获得最佳OCR效果")

        if not self._check_opencv_availability():
            recommendations.append("建议安装OpenCV以启用图像预处理功能")

        if self.stats.avg_confidence < 0.6:
            recommendations.append("建议提高图像DPI或优化扫描质量")

        if self.stats.pages_without_text > self.stats.pages_with_text:
            recommendations.append("大部分页面未识别到文本，建议检查PDF质量")

        if not recommendations:
            recommendations.append("系统配置良好，可以正常使用")

        return recommendations

    def _record_thread_offload(self, key: str):
        """记录一次线程卸载操作"""
        try:
            self.stats.thread_offloads_total += 1
            detail = self.stats.thread_offloads_detail
            detail[key] = detail.get(key, 0) + 1
        except Exception:
            # 统计失败不影响主流程
            pass


# 全局优化OCR服务实例
try:
    optimized_ocr_service = OptimizedOCRService()
    logger.info("优化OCR服务初始化成功")
except Exception as e:
    logger.error(f"优化OCR服务初始化失败 {e}")
    optimized_ocr_service = None
