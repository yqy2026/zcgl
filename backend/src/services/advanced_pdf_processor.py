"""
Advanced PDF Processing System
先进的PDF智能导入系统

基于2025年最佳实践的多引擎PDF处理架构
"""

import os
import time
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# PDF处理引擎
import fitz  # PyMuPDF
import pdfplumber
from unstructured.partition.pdf import partition_pdf
from paddleocr import PaddleOCR

# 数据处理
import pandas as pd
from pydantic import BaseModel, validator

# 配置
logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """文档类型枚举"""
    TEXT_HEAVY = "text_heavy"
    TABLE_HEAVY = "table_heavy"
    MIXED = "mixed"
    SCANNED = "scanned"
    COMPLEX = "complex"
    UNKNOWN = "unknown"


class ProcessingEngine(Enum):
    """处理引擎枚举"""
    PYMUPDF = "pymupdf"
    PDFPLUMBER = "pdfplumber"
    UNSTRUCTURED = "unstructured"
    PADDLEOCR = "paddleocr"
    HYBRID = "hybrid"


@dataclass
class ProcessingResult:
    """处理结果数据类"""
    success: bool
    content: str
    metadata: Dict[str, Any]
    engine_used: ProcessingEngine
    confidence: float
    processing_time: float
    tables: List[Dict[str, Any]]
    images: List[str]
    error: Optional[str] = None


class AdvancedPDFProcessor:
    """高级PDF处理器"""

    def __init__(self, config: Dict[str, Any] = None):
        """初始化高级PDF处理器"""
        self.config = config or self._get_default_config()
        self._init_engines()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "pymupdf": {
                "enabled": True,
                "text_extraction": True,
                "image_extraction": True,
                "table_extraction": True
            },
            "pdfplumber": {
                "enabled": True,
                "table_precision": "high",
                "text_tolerance": 3
            },
            "unstructured": {
                "enabled": True,
                "chunking_strategy": "by_title",
                "include_page_breaks": False
            },
            "paddleocr": {
                "enabled": True,
                "use_angle_cls": True,
                "lang": "ch",
                "show_log": False
            },
            "routing": {
                "prefer_pymupdf_for_text": True,
                "prefer_pdfplumber_for_tables": True,
                "prefer_unstructured_for_complex": True,
                "fallback_to_ocr": True
            }
        }

    def _init_engines(self):
        """初始化处理引擎"""
        logger.info("初始化PDF处理引擎...")

        # 初始化PyMuPDF
        if self.config["pymupdf"]["enabled"]:
            self.pymupdf_enabled = True
            logger.info("PyMuPDF引擎已启用")

        # 初始化pdfplumber
        if self.config["pdfplumber"]["enabled"]:
            self.pdfplumber_enabled = True
            logger.info("pdfplumber引擎已启用")

        # 初始化unstructured
        if self.config["unstructured"]["enabled"]:
            try:
                self.unstructured_enabled = True
                logger.info("Unstructured引擎已启用")
            except ImportError as e:
                logger.warning(f"Unstructured引擎初始化失败: {e}")
                self.unstructured_enabled = False

        # 初始化PaddleOCR
        if self.config["paddleocr"]["enabled"]:
            try:
                self.paddleocr = PaddleOCR(
                    use_angle_cls=self.config["paddleocr"]["use_angle_cls"],
                    lang=self.config["paddleocr"]["lang"],
                    show_log=self.config["paddleocr"]["show_log"]
                )
                self.paddleocr_enabled = True
                logger.info("PaddleOCR引擎已启用")
            except Exception as e:
                logger.error(f"PaddleOCR引擎初始化失败: {e}")
                self.paddleocr_enabled = False

    def analyze_document(self, file_path: str) -> DocumentType:
        """智能分析文档类型"""
        try:
            # 使用PyMuPDF快速分析
            doc = fitz.open(file_path)

            text_density = 0
            table_density = 0
            image_density = 0

            for page_num in range(min(3, len(doc))):  # 分析前3页
                page = doc[page_num]

                # 文本密度
                text = page.get_text()
                text_density += len(text)

                # 图像密度
                images = page.get_images()
                image_density += len(images)

                # 表格密度检测
                if '\t' in text or '|' in text:
                    table_density += 1

                # 扫描文档检测
                if len(text.strip()) < 100 and image_density > 0:
                    doc.close()
                    return DocumentType.SCANNED

            doc.close()

            # 判断文档类型
            total_pages = min(3, len(doc)) if 'doc' in locals() else 1

            avg_text_density = text_density / total_pages
            avg_image_density = image_density / total_pages

            if table_density > 1:
                return DocumentType.TABLE_HEAVY
            elif avg_text_density > 2000:
                return DocumentType.TEXT_HEAVY
            elif avg_image_density > 2:
                return DocumentType.COMPLEX
            else:
                return DocumentType.MIXED

        except Exception as e:
            logger.error(f"文档分析失败: {e}")
            return DocumentType.UNKNOWN

    def choose_best_engine(self, doc_type: DocumentType) -> List[ProcessingEngine]:
        """选择最佳处理引擎序列"""
        routing_config = self.config["routing"]

        if doc_type == DocumentType.TEXT_HEAVY:
            if routing_config["prefer_pymupdf_for_text"]:
                return [ProcessingEngine.PYMUPDF, ProcessingEngine.PDFPLUMBER, ProcessingEngine.UNSTRUCTURED]
        elif doc_type == DocumentType.TABLE_HEAVY:
            if routing_config["prefer_pdfplumber_for_tables"]:
                return [ProcessingEngine.PDFPLUMBER, ProcessingEngine.PYMUPDF, ProcessingEngine.UNSTRUCTURED]
        elif doc_type == DocumentType.COMPLEX:
            if routing_config["prefer_unstructured_for_complex"]:
                return [ProcessingEngine.UNSTRUCTURED, ProcessingEngine.PYMUPDF, ProcessingEngine.PDFPLUMBER]
        elif doc_type == DocumentType.SCANNED:
            return [ProcessingEngine.PADDLEOCR]

        # 默认引擎序列
        return [ProcessingEngine.PYMUPDF, ProcessingEngine.PDFPLUMBER, ProcessingEngine.UNSTRUCTURED]

    def process_with_pymupdf(self, file_path: str) -> ProcessingResult:
        """使用PyMuPDF处理文档"""
        start_time = time.time()

        try:
            doc = fitz.open(file_path)

            full_text = ""
            tables = []
            images = []
            total_confidence = 0.0
            text_blocks_count = 0

            for page_num in range(len(doc)):
                page = doc[page_num]

                # 文本提取
                text = page.get_text()
                if text.strip():
                    full_text += f"=== 第{page_num + 1}页 ===\n{text}\n\n"
                    text_blocks_count += 1
                    total_confidence += 0.95  # PyMuPDF对文本提取的置信度

                # 表格提取
                tables_data = page.find_tables()
                for table in tables_data:
                    try:
                        df = table.to_pandas()
                        table_dict = {
                            "page": page_num + 1,
                            "data": df.to_dict('records'),
                            "confidence": 0.9
                        }
                        tables.append(table_dict)
                    except Exception as e:
                        logger.warning(f"表格提取失败: {e}")

                # 图像提取
                image_list = page.get_images()
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_path = f"temp_image_page{page_num + 1}_img{img_index}.{base_image['ext']}"
                        with open(image_path, "wb") as f:
                            f.write(base_image["image"])
                        images.append(image_path)
                    except Exception as e:
                        logger.warning(f"图像提取失败: {e}")

            doc.close()

            processing_time = time.time() - start_time
            avg_confidence = total_confidence / text_blocks_count if text_blocks_count > 0 else 0.0

            return ProcessingResult(
                success=True,
                content=full_text.strip(),
                metadata={
                    "total_pages": len(doc),
                    "text_blocks": text_blocks_count,
                    "tables_found": len(tables),
                    "images_found": len(images),
                    "processing_time": processing_time
                },
                engine_used=ProcessingEngine.PYMUPDF,
                confidence=avg_confidence,
                processing_time=processing_time,
                tables=tables,
                images=images
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"PyMuPDF处理失败: {e}")
            return ProcessingResult(
                success=False,
                content="",
                metadata={},
                engine_used=ProcessingEngine.PYMUPDF,
                confidence=0.0,
                processing_time=processing_time,
                tables=[],
                images=[],
                error=str(e)
            )

    def process_with_pdfplumber(self, file_path: str) -> ProcessingResult:
        """使用pdfplumber处理文档"""
        start_time = time.time()

        try:
            with pdfplumber.open(file_path) as pdf:
                full_text = ""
                tables = []
                text_blocks_count = 0
                total_confidence = 0.0

                for page_num, page in enumerate(pdf.pages):
                    # 文本提取
                    text = page.extract_text()
                    if text and text.strip():
                        full_text += f"=== 第{page_num + 1}页 ===\n{text}\n\n"
                        text_blocks_count += 1
                        total_confidence += 0.9  # pdfplumber对文本提取的置信度

                    # 表格提取（pdfplumber的强项）
                    tables_data = page.extract_tables()
                    for table_data in tables_data:
                        if table_data and len(table_data) > 0:
                            df = pd.DataFrame(table_data[1:], columns=table_data[0])
                            table_dict = {
                                "page": page_num + 1,
                                "data": df.fillna('').to_dict('records'),
                                "confidence": 0.95  # pdfplumber表格提取置信度高
                            }
                            tables.append(table_dict)

                processing_time = time.time() - start_time
                avg_confidence = total_confidence / text_blocks_count if text_blocks_count > 0 else 0.0

                return ProcessingResult(
                    success=True,
                    content=full_text.strip(),
                    metadata={
                        "total_pages": len(pdf.pages),
                        "text_blocks": text_blocks_count,
                        "tables_found": len(tables),
                        "processing_time": processing_time
                    },
                    engine_used=ProcessingEngine.PDFPLUMBER,
                    confidence=avg_confidence,
                    processing_time=processing_time,
                    tables=tables,
                    images=[]
                )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"pdfplumber处理失败: {e}")
            return ProcessingResult(
                success=False,
                content="",
                metadata={},
                engine_used=ProcessingEngine.PDFPLUMBER,
                confidence=0.0,
                processing_time=processing_time,
                tables=[],
                images=[],
                error=str(e)
            )

    def process_with_paddleocr(self, file_path: str) -> ProcessingResult:
        """使用PaddleOCR处理扫描文档"""
        start_time = time.time()

        try:
            # 将PDF转换为图像进行OCR
            doc = fitz.open(file_path)
            full_text = ""
            text_blocks_count = 0
            total_confidence = 0.0

            for page_num in range(len(doc)):
                page = doc[page_num]

                # 将页面转换为图像
                mat = fitz.Matrix(2.0, 2.0)  # 提高分辨率
                pix = page.get_pixmap(matrix=mat)
                img_path = f"temp_page_{page_num + 1}.png"
                pix.save(img_path)

                # 使用PaddleOCR识别
                result = self.paddleocr.ocr(img_path, cls=True)

                if result and result[0]:
                    page_text = ""
                    for line in result[0]:
                        if line and len(line) >= 2:
                            bbox = line[0]
                            (text, confidence) = line[1]
                            if confidence > 0.5:  # 置信度阈值
                                page_text += text + "\n"
                                total_confidence += confidence
                                text_blocks_count += 1

                    if page_text.strip():
                        full_text += f"=== 第{page_num + 1}页 ===\n{page_text}\n\n"

                # 清理临时图像
                try:
                    os.remove(img_path)
                except:
                    pass

            doc.close()

            processing_time = time.time() - start_time
            avg_confidence = total_confidence / text_blocks_count if text_blocks_count > 0 else 0.0

            return ProcessingResult(
                success=True,
                content=full_text.strip(),
                metadata={
                    "total_pages": len(doc) if 'doc' in locals() else 1,
                    "text_blocks": text_blocks_count,
                    "processing_method": "ocr",
                    "processing_time": processing_time
                },
                engine_used=ProcessingEngine.PADDLEOCR,
                confidence=avg_confidence,
                processing_time=processing_time,
                tables=[],
                images=[]
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"PaddleOCR处理失败: {e}")
            return ProcessingResult(
                success=False,
                content="",
                metadata={},
                engine_used=ProcessingEngine.PADDLEOCR,
                confidence=0.0,
                processing_time=processing_time,
                tables=[],
                images=[],
                error=str(e)
            )

    def process_pdf(self, file_path: str) -> ProcessingResult:
        """智能PDF处理主入口"""
        logger.info(f"开始处理PDF文件: {file_path}")

        # 验证文件存在
        if not os.path.exists(file_path):
            return ProcessingResult(
                success=False,
                content="",
                metadata={},
                engine_used=ProcessingEngine.HYBRID,
                confidence=0.0,
                processing_time=0.0,
                tables=[],
                images=[],
                error="文件不存在"
            )

        # 分析文档类型
        doc_type = self.analyze_document(file_path)
        logger.info(f"文档类型: {doc_type.value}")

        # 选择最佳处理引擎序列
        engines = self.choose_best_engine(doc_type)
        logger.info(f"选择的处理引擎: {[engine.value for engine in engines]}")

        # 依次尝试不同的处理引擎
        last_error = None
        for engine in engines:
            try:
                if engine == ProcessingEngine.PYMUPDF and self.pymupdf_enabled:
                    result = self.process_with_pymupdf(file_path)
                elif engine == ProcessingEngine.PDFPLUMBER and self.pdfplumber_enabled:
                    result = self.process_with_pdfplumber(file_path)
                elif engine == ProcessingEngine.PADDLEOCR and self.paddleocr_enabled:
                    result = self.process_with_paddleocr(file_path)
                else:
                    logger.warning(f"引擎 {engine.value} 不可用，跳过")
                    continue

                if result.success and result.confidence > 0.7:
                    logger.info(f"处理成功: {engine.value}, 置信度: {result.confidence:.2f}")
                    return result
                elif result.success:
                    logger.info(f"处理完成但置信度较低: {engine.value}, 置信度: {result.confidence:.2f}")
                    last_error = result.error

            except Exception as e:
                logger.error(f"引擎 {engine.value} 处理失败: {e}")
                last_error = str(e)
                continue

        # 所有引擎都失败
        return ProcessingResult(
            success=False,
            content="",
            metadata={},
            engine_used=ProcessingEngine.HYBRID,
            confidence=0.0,
            processing_time=0.0,
            tables=[],
            images=[],
            error=f"所有处理引擎都失败: {last_error}"
        )


# 全局实例
advanced_pdf_processor = AdvancedPDFProcessor()


def process_pdf_intelligently(file_path: str) -> ProcessingResult:
    """智能PDF处理函数"""
    return advanced_pdf_processor.process_pdf(file_path)


if __name__ == "__main__":
    # 测试代码
    test_file = "test.pdf"
    if os.path.exists(test_file):
        result = process_pdf_intelligently(test_file)
        print(f"处理结果: {result.success}")
        print(f"引擎: {result.engine_used.value}")
        print(f"置信度: {result.confidence:.2f}")
        print(f"处理时间: {result.processing_time:.2f}s")
        print(f"文本长度: {len(result.content)}")
    else:
        print("测试文件不存在")