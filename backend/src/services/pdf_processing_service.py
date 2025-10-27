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
from datetime import datetime, timezone

import pdfplumber
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
import aiofiles

logger = logging.getLogger(__name__)

try:
    from ..models.pdf_import_session import ProcessingStep, SessionStatus
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
        self.supported_methods = [
            PDFProcessingMethod.PYMUPDF,
            PDFProcessingMethod.PDFPLUMBER,
            PDFProcessingMethod.OCR
        ]

    @property
    def ocr(self):
        """延迟初始化OCR引擎"""
        if not self._ocr_initialized:
            try:
                # 修复PaddleOCR配置问题
                self._ocr_engine = PaddleOCR(
                    use_textline_orientation=True,
                    lang='ch',
                    show_log=False,
                    use_gpu=False,  # 修复GPU参数问题
                    text_det_thresh=0.3,  # 新的检测阈值参数
                    text_det_limit_side_len=960,  # 新的检测性能参数
                    text_recognition_batch_size=6  # 新的识别性能参数
                )
                self._ocr_initialized = True
                logger.info("PaddleOCR引擎初始化成功")
            except Exception as e:
                logger.error(f"PaddleOCR初始化失败: {e}")
                self._ocr_engine = None
                self._ocr_initialized = True  # 避免重复尝试
        return self._ocr_engine

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
        """
        智能选择最佳PDF处理方法 - 增强版本
        """
        try:
            file_size = file_path.stat().st_size

            # 基于文件大小的初步判断
            if file_size > 20 * 1024 * 1024:  # 20MB以上文件，优先OCR
                logger.info(f"大文件检测({file_size/1024/1024:.1f}MB)，倾向于OCR处理")

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

            # 选择最佳方法
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

            # 检查前5页
            for page_num in range(min(5, len(doc))):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_samples.append(text)
                    total_chars += len(text)
                    chinese_chars += len(re.findall(r'[\u4e00-\u9fff]', text))

            doc.close()

            if not text_samples:
                return 0.0

            # 计算质量分数
            avg_text_length = len(text_samples) / len(text_samples)
            chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0

            # 评分标准
            score = 0.0
            # 文本长度分数（0-30分）
            score += min(avg_text_length / 10, 30)
            # 中文字符比例分数（0-40分）
            score += min(chinese_ratio * 80, 40)
            # 页面覆盖分数（0-30分）
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
                for page in pdf[:5]:  # 检查前5页
                    text = page.extract_text() or ""
                    if text.strip():
                        total_text += text
                        page_count += 1

            if not total_text:
                return 0.0

            # 基于文本质量和结构评分
            lines = total_text.split('\n')
            meaningful_lines = [line for line in lines if len(line.strip()) > 5]

            score = 0.0
            # 有效行数分数（0-40分）
            score += min(len(meaningful_lines) / 10, 40)
            # 文本密度分数（0-30分）
            score += min(len(total_text) / 100, 30)
            # 页面覆盖分数（0-30分）
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
                if line[1][0]:  # 置信度
                    text_lines.append(line[1][0])

            text = '\n'.join(text_lines)

            # 评分标准
            score = 0.0
            # 文本行数分数（0-40分）
            score += min(len(text_lines) / 20, 40)
            # 文本长度分数（0-30分）
            score += min(len(text) / 50, 30)
            # 中文字符检测（0-30分）
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            score += min(chinese_chars / 10, 30)

            return min(score, 100.0)

        except Exception as e:
            logger.warning(f"OCR质量评估失败: {e}")
            return 0.0

    async def _is_scanned_pdf(self, file_path: Path) -> bool:
        """检查PDF是否为扫描版（保留原方法作为备用）"""
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
        """使用OCR提取文本 - 优化版本"""
        dpi = kwargs.get('dpi', 300)
        max_pages = kwargs.get('max_pages', 10)

        # 检查OCR引擎可用性
        if not self.ocr:
            raise Exception("OCR引擎未初始化或初始化失败")

        # 优化图像转换参数
        try:
            images = convert_from_path(
                str(file_path),
                dpi=dpi,
                first_page=1,
                last_page=max_pages,
                thread_count=4,  # 增加线程数
                grayscale=True,   # 转为灰度图提高识别率
                size=(2000, None) # 限制最大宽度，提高处理速度
            )
        except Exception as e:
            raise Exception(f"PDF转图像失败: {str(e)}")

        pages_text = []
        full_text = ""

        for page_num, image in enumerate(images, 1):
            try:
                # 图像预处理
                import cv2
                import numpy as np

                # 转换为OpenCV格式
                img_array = np.array(image)
                if len(img_array.shape) == 3:
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

                # 图像增强
                img_array = cv2.adaptiveThreshold(
                    img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
                )

                # 使用PaddleOCR进行文字识别
                result = self.ocr.ocr(img_array, cls=True)

                # 提取识别的文本
                page_text = ""
                confidences = []
                text_blocks = []

                if result and result[0]:
                    for line in result[0]:
                        if line and len(line) >= 2:
                            try:
                                # 修复数据结构访问问题
                                box, (text, confidence) = line
                                if text and confidence > 0.5:  # 过滤低置信度结果
                                    page_text += text + "\n"
                                    confidences.append(confidence)
                                    text_blocks.append({
                                        'text': text,
                                        'confidence': confidence,
                                        'bbox': box
                                    })
                            except (IndexError, TypeError) as e:
                                logger.warning(f"解析OCR结果失败: {e}")
                                continue

                # 计算页面平均置信度
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                # 后处理：文本清理和格式化
                page_text = self._post_process_ocr_text(page_text)

                page_info = {
                    'page_number': page_num,
                    'text': page_text.strip(),
                    'text_length': len(page_text),
                    'confidence_score': avg_confidence,
                    'ocr_used': True,
                    'text_blocks': text_blocks,
                    'chinese_ratio': len([c for c in page_text if '\u4e00' <= c <= '\u9fff']) / len(page_text) if page_text else 0
                }

                pages_text.append(page_info)
                full_text += page_text + "\n"

                logger.info(f"OCR处理第{page_num}页完成，置信度: {avg_confidence:.2f}, 文本长度: {len(page_text)}")

            except Exception as e:
                logger.warning(f"OCR处理第{page_num}页失败: {str(e)}")
                continue

        # 计算整体置信度
        all_confidences = [p.get('confidence_score', 0) for p in pages_text if p.get('confidence_score')]
        overall_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0

        # 计算中文字符统计
        chinese_count = len([c for c in full_text if '\u4e00' <= c <= '\u9fff'])
        english_count = len([c for c in full_text if c.isalpha() and ord(c) < 128])

        return {
            'text': full_text.strip(),
            'pages': pages_text,
            'total_pages': len(pages_text),
            'chinese_char_count': chinese_count,
            'english_char_count': english_count,
            'overall_confidence_score': overall_confidence,
            'ocr_used': True,
            'ocr_dpi': dpi,
            'quality_metrics': {
                'avg_page_confidence': overall_confidence,
                'chinese_text_ratio': chinese_count / len(full_text) if full_text else 0,
                'total_text_blocks': sum(len(p.get('text_blocks', [])) for p in pages_text)
            }
        }

    def _post_process_ocr_text(self, text: str) -> str:
        """OCR文本后处理"""
        if not text:
            return text

        # 清理常见的OCR错误
        text = text.strip()

        # 移除多余的空行
        text = '\n'.join(line for line in text.split('\n') if line.strip())

        # 修复常见的标点符号错误
        replacements = {
            '，。': '，',
            '。。': '。',
            '，，': '，',
            '？？': '？',
            '！！': '！',
            '（ ': '（',
            ' ）': '）'
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

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