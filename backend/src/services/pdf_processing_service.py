"""
PDF文本处理服务
支持多种PDF处理引擎和OCR功能
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import asyncio
from datetime import datetime

import pdfplumber
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
import aiofiles

from ..models.pdf_import_session import ProcessingStep, SessionStatus

logger = logging.getLogger(__name__)

class PDFProcessingMethod:
    """PDF处理方法枚举"""
    PDFPLUMBER = "pdfplumber"
    PYMUPDF = "pymupdf"
    OCR = "ocr"

class PDFProcessingService:
    """PDF文本处理服务"""

    def __init__(self):
        # 初始化PaddleOCR（支持中文）
        self.ocr = PaddleOCR(use_angle_cls=True, lang='ch')
        self.supported_methods = [
            PDFProcessingMethod.PYMUPDF,
            PDFProcessingMethod.PDFPLUMBER,
            PDFProcessingMethod.OCR
        ]

    async def extract_text_from_pdf(
        self,
        file_path: str,
        method: Optional[str] = None,
        prefer_ocr: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        从PDF文件提取文本

        Args:
            file_path: PDF文件路径
            method: 指定的处理方法
            prefer_ocr: 是否优先使用OCR
            **kwargs: 其他配置参数

        Returns:
            包含提取结果和元数据的字典
        """
        start_time = datetime.now()
        file_path = Path(file_path)

        try:
            # 验证文件
            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")

            if file_path.suffix.lower() != '.pdf':
                raise ValueError(f"不支持的文件格式: {file_path.suffix}")

            # 选择处理方法
            if method is None:
                method = await self._select_best_method(file_path, prefer_ocr)

            logger.info(f"开始处理PDF文件: {file_path.name}, 使用方法: {method}")

            # 根据选择的方法提取文本
            if method == PDFProcessingMethod.PYMUPDF:
                result = await self._extract_with_pymupdf(file_path, **kwargs)
            elif method == PDFProcessingMethod.PDFPLUMBER:
                result = await self._extract_with_pdfplumber(file_path, **kwargs)
            elif method == PDFProcessingMethod.OCR:
                result = await self._extract_with_ocr(file_path, **kwargs)
            else:
                raise ValueError(f"不支持的PDF处理方法: {method}")

            # 添加处理元数据
            processing_time = (datetime.now() - start_time).total_seconds()
            result.update({
                'processing_method': method,
                'processing_time_seconds': processing_time,
                'file_size_bytes': file_path.stat().st_size,
                'extracted_at': datetime.now().isoformat(),
                'ocr_used': method == PDFProcessingMethod.OCR,
                'success': True
            })

            logger.info(f"PDF处理完成: {file_path.name}, 耗时: {processing_time:.2f}秒, "
                       f"文本长度: {len(result.get('text', ''))}")

            return result

        except Exception as e:
            logger.error(f"PDF处理失败: {file_path.name}, 错误: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'processing_method': method,
                'processing_time_seconds': (datetime.now() - start_time).total_seconds(),
                'text': '',
                'pages': []
            }

    async def _select_best_method(self, file_path: Path, prefer_ocr: bool) -> str:
        """智能选择最佳PDF处理方法"""

        if prefer_ocr:
            return PDFProcessingMethod.OCR

        # 检查PDF是否为扫描版
        is_scanned = await self._is_scanned_pdf(file_path)

        if is_scanned:
            logger.info(f"检测到扫描版PDF，使用OCR处理: {file_path.name}")
            return PDFProcessingMethod.OCR
        else:
            # 优先使用PyMuPDF（性能更好）
            return PDFProcessingMethod.PYMUPDF

    async def _is_scanned_pdf(self, file_path: Path) -> bool:
        """检查PDF是否为扫描版"""
        try:
            doc = fitz.open(str(file_path))
            text_content = ""

            # 检查前3页的文本内容
            for page in doc[:min(3, len(doc))]:
                text_content += page.get_text()

            doc.close()

            # 如果文本很少，可能是扫描版
            text_threshold = 100  # 字符数阈值
            return len(text_content.strip()) < text_threshold

        except Exception as e:
            logger.warning(f"检查扫描版PDF失败: {str(e)}")
            return False  # 默认认为不是扫描版

    async def _extract_with_pymupdf(self, file_path: Path, **kwargs) -> Dict[str, Any]:
        """使用PyMuPDF提取文本"""
        doc = fitz.open(str(file_path))
        pages_text = []
        full_text = ""

        for page_num, page in enumerate(doc, 1):
            try:
                # 提取文本
                text = page.get_text()

                # 提取图像信息（如果有）
                images = []
                for img_index, img in enumerate(page.get_images()):
                    try:
                        images.append({
                            'index': img_index,
                            'xref': img[0],
                            'width': img[2],
                            'height': img[3],
                            'type': img[-1]
                        })
                    except:
                        continue

                page_info = {
                    'page_number': page_num,
                    'text': text,
                    'text_length': len(text),
                    'images_count': len(images),
                    'images': images
                }

                pages_text.append(page_info)
                full_text += text + "\n"

            except Exception as e:
                logger.warning(f"提取第{page_num}页文本失败: {str(e)}")
                continue

        doc.close()

        return {
            'text': full_text.strip(),
            'pages': pages_text,
            'total_pages': len(pages_text),
            'chinese_char_count': len([c for c in full_text if '\u4e00' <= c <= '\u9fff']),
            'english_char_count': len([c for c in full_text if c.isalpha() and ord(c) < 128])
        }

    async def _extract_with_pdfplumber(self, file_path: Path, **kwargs) -> Dict[str, Any]:
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
                        if table and any(row for row in table if any(cell for cell in row)):
                            tables.append({
                                'data': table,
                                'rows': len(table),
                                'columns': len(table[0]) if table else 0
                            })

                    page_info = {
                        'page_number': page_num,
                        'text': text or '',
                        'text_length': len(text or ''),
                        'tables_count': len(tables),
                        'tables': tables,
                        'width': page.width,
                        'height': page.height
                    }

                    pages_text.append(page_info)
                    if text:
                        full_text += text + "\n"

                except Exception as e:
                    logger.warning(f"pdfplumber提取第{page_num}页失败: {str(e)}")
                    continue

        return {
            'text': full_text.strip(),
            'pages': pages_text,
            'total_pages': len(pages_text),
            'chinese_char_count': len([c for c in full_text if '\u4e00' <= c <= '\u9fff']),
            'english_char_count': len([c for c in full_text if c.isalpha() and ord(c) < 128])
        }

    async def _extract_with_ocr(self, file_path: Path, **kwargs) -> Dict[str, Any]:
        """使用OCR提取文本"""
        dpi = kwargs.get('dpi', 300)
        max_pages = kwargs.get('max_pages', 10)

        # 将PDF转换为图像
        try:
            images = convert_from_path(
                str(file_path),
                dpi=dpi,
                first_page=1,
                last_page=max_pages,
                thread_count=2
            )
        except Exception as e:
            raise Exception(f"PDF转图像失败: {str(e)}")

        pages_text = []
        full_text = ""

        for page_num, image in enumerate(images, 1):
            try:
                # 使用PaddleOCR进行文字识别
                result = self.ocr.ocr(image, cls=True)

                # 提取识别的文本
                page_text = ""
                confidences = []

                for line in result:
                    if line:
                        for word_info in line:
                            if word_info:
                                text, confidence = word_info[1], word_info[2]
                                page_text += text + "\n"
                                confidences.append(confidence)

                # 计算页面平均置信度
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                page_info = {
                    'page_number': page_num,
                    'text': page_text.strip(),
                    'text_length': len(page_text),
                    'confidence_score': avg_confidence,
                    'ocr_used': True
                }

                pages_text.append(page_info)
                full_text += page_text + "\n"

                logger.info(f"OCR处理第{page_num}页完成，置信度: {avg_confidence:.2f}")

            except Exception as e:
                logger.warning(f"OCR处理第{page_num}页失败: {str(e)}")
                continue

        # 计算整体置信度
        all_confidences = [p.get('confidence_score', 0) for p in pages_text if p.get('confidence_score')]
        overall_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0

        return {
            'text': full_text.strip(),
            'pages': pages_text,
            'total_pages': len(pages_text),
            'chinese_char_count': len([c for c in full_text if '\u4e00' <= c <= '\u9fff']),
            'english_char_count': len([c for c in full_text if c.isalpha() and ord(c) < 128]),
            'overall_confidence_score': overall_confidence,
            'ocr_used': True,
            'ocr_dpi': dpi
        }

    async def extract_text_from_image(self, image_path: str, **kwargs) -> Dict[str, Any]:
        """从图像文件提取文本（OCR）"""
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

            # 计算置信度
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            processing_time = (datetime.now() - start_time).total_seconds()

            return {
                'success': True,
                'text': text.strip(),
                'confidence_score': avg_confidence,
                'processing_time_seconds': processing_time,
                'ocr_used': True,
                'chinese_char_count': len([c for c in text if '\u4e00' <= c <= '\u9fff']),
                'english_char_count': len([c for c in text if c.isalpha() and ord(c) < 128])
            }

        except Exception as e:
            logger.error(f"图像OCR失败: {image_path}, 错误: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'confidence_score': 0,
                'processing_time_seconds': (datetime.now() - start_time).total_seconds()
            }

# 创建全局实例
pdf_processing_service = PDFProcessingService()