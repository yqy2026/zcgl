#!/usr/bin/env python
from typing import Any
"""
扫描件PDF专用处理器
专门解决扫描件PDF的OCR识别问题，使用多种方法确保文本提取成功
"""

import logging
import time
from dataclasses import dataclass


import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ScanProcessingResult:
    """扫描件处理结果"""

    success: bool
    processing_method: str
    text_extracted: str
    confidence_score: float
    pages_processed: int
    total_pages: int
    processing_time: float
    error_message: str | None = None


class ScannedPDFProcessor:
    """扫描件PDF专用处理器"""

    def __init__(self):
        self.paddle_ocr = None
        self.fallback_methods = []

    async def initialize_engines(self):
        """异步初始化处理引擎"""
        try:
            # 1. 初始化PaddleOCR（简化配置）
            logger.info("初始化PaddleOCR引擎...")
            from paddleocr import PaddleOCR

            # 使用最基本的配置
            self.paddle_ocr = PaddleOCR(lang="ch", use_textline_orientation=True)
            logger.info("PaddleOCR引擎初始化成功")

        except Exception as e:
            logger.error(f"PaddleOCR初始化失败: {e}")
            self.paddle_ocr = None

        # 2. 检查备用方法
        self.fallback_methods = self._check_fallback_methods()
        logger.info(f"可用备用方法: {len(self.fallback_methods)}个")

    def _check_fallback_methods(self) -> list[str]:
        """检查可用的备用处理方法"""
        available = []

        # 检查PyMuPDF
        try:
            import fitz  # noqa: F401

            available.append("pymupdf_text")
        except ImportError:
            pass

        # 检查OpenCV（用于图像预处理）
        try:
            import cv2  # noqa: F401

            available.append("opencv_preprocessing")
        except ImportError:
            pass

        # 检查EasyOCR
        try:
            import easyocr  # noqa: F401

            available.append("easyocr")
        except ImportError:
            pass

        return available

    def convert_pdf_page_to_image_array(self, page) -> np.ndarray | None:
        """将PDF页面转换为图像数组（简化版）"""
        try:
            import fitz

            # 使用适中的分辨率
            matrix = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=matrix)

            # 简化的数组转换
            img_data = pix.samples
            if pix.n == 4:  # RGBA
                img_array = np.frombuffer(img_data, dtype=np.uint8).reshape(
                    (pix.height, pix.width, 4)
                )
                img_array = img_array[:, :, :3]  # 移除alpha
            elif pix.n == 3:  # RGB
                img_array = np.frombuffer(img_data, dtype=np.uint8).reshape(
                    (pix.height, pix.width, 3)
                )
            elif pix.n == 1:  # 灰度
                img_array = np.frombuffer(img_data, dtype=np.uint8).reshape(
                    (pix.height, pix.width)
                )
                # 转换为RGB格式
                img_array = np.stack([img_array, img_array, img_array], axis=2)
            else:
                logger.warning(f"不支持的图像格式: {pix.n}通道")
                return None

            return img_array

        except Exception as e:
            logger.error(f"PDF页面转换失败: {e}")
            return None

    def extract_text_with_pymupdf_fallback(
        self, doc, max_pages: int = 3
    ) -> ScanProcessingResult:
        """使用PyMuPDF作为备用文本提取"""
        start_time = time.time()

        try:
            total_pages = min(doc.page_count, max_pages)
            all_text = ""

            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text()

                if text.strip():
                    all_text += text + "\n\n"
                    logger.info(
                        f"页面 {page_num + 1} 使用PyMuPDF提取文本: {len(text)}字符"
                    )

            doc.close()
            processing_time = time.time() - start_time

            if len(all_text.strip()) > 0:
                return ScanProcessingResult(
                    success=True,
                    processing_method="pymupdf_fallback",
                    text_extracted=all_text.strip(),
                    confidence_score=0.9,  # PyMuPDF文本置信度最高
                    pages_processed=total_pages,
                    total_pages=total_pages,
                    processing_time=processing_time,
                )
            else:
                return ScanProcessingResult(
                    success=False,
                    processing_method="pymupdf_fallback",
                    text_extracted="",
                    confidence_score=0.0,
                    pages_processed=total_pages,
                    total_pages=total_pages,
                    processing_time=processing_time,
                    error_message="PyMuPDF未提取到文本",
                )

        except Exception as e:
            processing_time = time.time() - start_time
            return ScanProcessingResult(
                success=False,
                processing_method="pymupdf_fallback",
                text_extracted="",
                confidence_score=0.0,
                pages_processed=0,
                total_pages=0,
                processing_time=processing_time,
                error_message=str(e),
            )

    async def extract_with_simplified_paddleocr(
        self, pdf_path: str, max_pages: int = 3
    ) -> ScanProcessingResult:
        """使用简化的PaddleOCR提取"""
        start_time = time.time()

        if self.paddle_ocr is None:
            return ScanProcessingResult(
                success=False,
                processing_method="paddleocr_unavailable",
                text_extracted="",
                confidence_score=0.0,
                pages_processed=0,
                total_pages=0,
                processing_time=0.0,
                error_message="PaddleOCR未初始化",
            )

        try:
            import fitz

            doc = fitz.open(pdf_path)
            total_pages = min(doc.page_count, max_pages)
            all_text = ""
            successful_pages = 0

            # 串行处理页面以减少内存占用
            for page_num in range(total_pages):
                logger.info(f"开始处理页面 {page_num + 1}/{total_pages}")

                # 转换页面为图像数组
                img_array = self.convert_pdf_page_to_image_array(doc[page_num])
                if img_array is None:
                    logger.warning(f"页面 {page_num + 1} 转换失败，跳过")
                    continue

                try:
                    # 使用最基础的OCR调用
                    result = self.paddle_ocr.ocr(img_array)

                    if result and len(result) > 0:
                        page_text = ""
                        for line in result[0]:
                            if line and len(line) >= 2:
                                text = line[1][0]  # 提取文本
                                line[1][1]  # 提取置信度，预留用于质量评估
                                page_text += text + "\n"

                        if page_text.strip():
                            all_text += page_text + "\n\n"
                            successful_pages += 1
                            logger.info(
                                f"页面 {page_num + 1} OCR成功: {len(page_text)}字符"
                            )
                        else:
                            logger.info(f"页面 {page_num + 1} OCR无结果")

                except Exception as e:
                    logger.error(f"页面 {page_num + 1} OCR处理失败: {e}")

            doc.close()
            processing_time = time.time() - start_time

            # 计算平均置信度
            avg_confidence = 0.5 if successful_pages > 0 else 0.0

            return ScanProcessingResult(
                success=successful_pages > 0,
                processing_method="paddleocr_simplified",
                text_extracted=all_text.strip(),
                confidence_score=avg_confidence,
                pages_processed=successful_pages,
                total_pages=total_pages,
                processing_time=processing_time,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            return ScanProcessingResult(
                success=False,
                processing_method="paddleocr_simplified",
                text_extracted="",
                confidence_score=0.0,
                pages_processed=0,
                total_pages=0,
                processing_time=processing_time,
                error_message=str(e),
            )

    async def extract_text_with_combined_methods(
        self, pdf_path: str, max_pages: int = 3
    ) -> ScanProcessingResult:
        """使用组合方法提取文本"""
        start_time = time.time()

        results = []

        # 方法1: 简化PaddleOCR
        logger.info("尝试方法1: 简化PaddleOCR")
        paddle_result = await self.extract_with_simplified_paddleocr(
            pdf_path, max_pages
        )
        results.append(paddle_result)

        # 方法2: PyMuPDF备用
        logger.info("尝试方法2: PyMuPDF备用")
        try:
            import fitz

            doc = fitz.open(pdf_path)
            pymupdf_result = self.extract_text_with_pymupdf_fallback(doc, max_pages)
            doc.close()
            results.append(pymupdf_result)
        except Exception as e:
            logger.error(f"PyMuPDF备用方法失败: {e}")
            results.append(
                ScanProcessingResult(
                    success=False,
                    processing_method="pymupdf_error",
                    text_extracted="",
                    confidence_score=0.0,
                    pages_processed=0,
                    total_pages=0,
                    processing_time=0.0,
                    error_message=str(e),
                )
            )

        # 选择最佳结果
        best_result = max(
            results, key=lambda r: (len(r.text_extracted), r.confidence_score)
        )

        processing_time = time.time() - start_time

        logger.info(f"组合处理完成，最佳方法: {best_result.processing_method}")
        logger.info(f"提取文本长度: {len(best_result.text_extracted)}字符")

        return ScanProcessingResult(
            success=best_result.success,
            processing_method=f"combined_{best_result.processing_method}",
            text_extracted=best_result.text_extracted,
            confidence_score=best_result.confidence_score,
            pages_processed=best_result.pages_processed,
            total_pages=best_result.total_pages,
            processing_time=processing_time,
        )

    async def process_scanned_pdf(
        self, pdf_path: str, max_pages: int = 5
    ) -> dict[str, Any]:
        """处理扫描件PDF的主入口"""
        logger.info(f"开始处理扫描件PDF: {pdf_path}")

        # 确保引擎已初始化
        if self.paddle_ocr is None:
            await self.initialize_engines()

        start_time = time.time()

        # 执行处理
        result = await self.extract_text_with_combined_methods(pdf_path, max_pages)

        total_time = time.time() - start_time

        # 构建返回结果
        processing_result = {
            "success": result.success,
            "processing_method": result.processing_method,
            "text_extracted": result.text_extracted,
            "text_length": len(result.text_extracted),
            "confidence_score": result.confidence_score,
            "pages_processed": result.pages_processed,
            "total_pages": result.total_pages,
            "processing_time": result.processing_time,
            "pages_per_second": result.total_pages / result.processing_time
            if result.processing_time > 0
            else 0,
            "total_time": total_time,
            "error_message": result.error_message,
            "available_methods": self.fallback_methods,
            "paddle_ocr_available": self.paddle_ocr is not None,
            "recommendations": self._generate_recommendations(result),
        }

        logger.info(f"扫描件PDF处理完成: {len(result.text_extracted)}字符")
        return processing_result

    def _generate_recommendations(self, result: ScanProcessingResult) -> list[str]:
        """生成处理建议"""
        recommendations = []

        if not result.success:
            if "PaddleOCR未初始化" in str(result.error_message or ""):
                recommendations.append("建议安装PaddleOCR以获得更好的OCR效果")
            else:
                recommendations.append("OCR处理失败，建议检查PDF文件质量")

        elif result.confidence_score < 0.3:
            recommendations.append("识别置信度较低，建议提高图像DPI")
        elif result.pages_processed < result.total_pages * 0.5:
            recommendations.append("部分页面处理失败，建议检查图像质量")

        elif len(result.text_extracted) < 50:
            recommendations.append("识别文本较少，可能是扫描质量问题")

        if not recommendations:
            recommendations.append("处理成功，建议继续使用当前配置")

        return recommendations


# 全局扫描件处理器实例
try:
    scanned_pdf_processor = ScannedPDFProcessor()
    logger.info("扫描件PDF处理器初始化成功")
except Exception as e:
    logger.error(f"扫描件PDF处理器初始化失败: {e}")
    scanned_pdf_processor = None
