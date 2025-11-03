from typing import Any

"""
增强PDF处理器
专门针对中文租赁合同的智能处理和质量优化
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .pdf_processing_service import pdf_processing_service

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """文档类型"""

    SCANNED_CONTRACT = "scanned_contract"
    DIGITAL_CONTRACT = "digital_contract"
    MIXED_CONTRACT = "mixed_contract"
    UNKNOWN = "unknown"


class ProcessingQuality(Enum):
    """处理质量等级"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass
class DocumentAnalysis:
    """文档分析结果"""

    document_type: DocumentType
    quality_score: float
    processing_quality: ProcessingQuality
    total_pages: int
    scanned_pages: int
    digital_pages: int
    text_density: float
    image_quality: float
    recommendations: list[str] = field(default_factory=list)


@dataclass
class ProcessingConfig:
    """处理配置"""

    use_ocr: bool = True
    dpi: int = 300
    enable_preprocessing: bool = True
    enable_enhancement: bool = True
    confidence_threshold: float = 0.6
    max_pages: int = 50
    enable_parallel: bool = True
    cache_results: bool = True


class EnhancedPDFProcessor:
    """增强PDF处理器"""

    def __init__(self):
        self.preprocessing_cache = {}
        self.quality_models = self._load_quality_models()

    def _load_quality_models(self) -> dict[str, Any]:
        """加载质量评估模型"""
        return {
            "text_density_threshold": 0.1,
            "image_quality_threshold": 0.5,
            "confidence_threshold": 0.6,
            "scanned_detection_threshold": 0.3,
        }

    async def analyze_document(self, file_path: str) -> DocumentAnalysis:
        """分析文档质量和类型"""
        try:
            file_path = Path(file_path)

            # 基础文件分析
            file_size = file_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            # 快速质量评估
            quick_analysis = await self._quick_quality_assessment(file_path)

            # 详细页面分析
            page_analysis = await self._detailed_page_analysis(file_path, max_pages=5)

            # 综合分析结果
            analysis = self._combine_analysis_results(
                quick_analysis, page_analysis, file_size_mb
            )

            logger.info(
                f"文档分析完成: {file_path.name}, 类型: {analysis.document_type.value}, 质量: {analysis.processing_quality.value}"
            )

            return analysis

        except Exception as e:
            logger.error(f"文档分析失败: {str(e)}")
            return DocumentAnalysis(
                document_type=DocumentType.UNKNOWN,
                quality_score=0.0,
                processing_quality=ProcessingQuality.POOR,
                total_pages=0,
                scanned_pages=0,
                digital_pages=0,
                text_density=0.0,
                image_quality=0.0,
                recommendations=["文档分析失败，请检查文件格式"],
            )

    async def _quick_quality_assessment(self, file_path: Path) -> dict[str, Any]:
        """快速质量评估"""
        try:
            # 使用pdfplumber进行快速检测
            import pdfplumber

            total_pages = 0
            text_content = ""
            image_count = 0

            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf)

                # 检查前3页
                for page in pdf[:3]:
                    text = page.extract_text() or ""
                    text_content += text

                    # 检查图像
                    if hasattr(page, "images"):
                        image_count += len(page.images)

            # 计算基础指标
            avg_text_per_page = (
                len(text_content) / min(total_pages, 3) if total_pages > 0 else 0
            )
            text_density = avg_text_per_page / 1000  # 标准化到0-1
            image_ratio = image_count / min(total_pages, 3) if total_pages > 0 else 0

            # 判断文档类型
            if text_density < 0.1 and image_ratio > 0.5:
                doc_type = DocumentType.SCANNED_CONTRACT
            elif text_density > 0.5 and image_ratio < 0.1:
                doc_type = DocumentType.DIGITAL_CONTRACT
            else:
                doc_type = DocumentType.MIXED_CONTRACT

            return {
                "total_pages": total_pages,
                "text_density": min(text_density, 1.0),
                "image_ratio": min(image_ratio, 1.0),
                "document_type": doc_type,
                "avg_text_per_page": avg_text_per_page,
            }

        except Exception as e:
            logger.warning(f"快速质量评估失败: {str(e)}")
            return {
                "total_pages": 0,
                "text_density": 0.0,
                "image_ratio": 0.0,
                "document_type": DocumentType.UNKNOWN,
                "avg_text_per_page": 0.0,
            }

    async def _detailed_page_analysis(
        self, file_path: Path, max_pages: int = 5
    ) -> dict[str, Any]:
        """详细页面分析"""
        try:
            # 转换前几页为图像进行分析
            from pdf2image import convert_from_path

            images = convert_from_path(
                str(file_path),
                dpi=150,  # 较低分辨率用于快速分析
                first_page=1,
                last_page=max_pages,
            )

            page_qualities = []
            scanned_count = 0

            for i, image in enumerate(images):
                try:
                    # 图像质量评估
                    quality_score = self._assess_image_quality(image)

                    # 扫描检测
                    is_scanned = self._detect_scanned_page(image)
                    if is_scanned:
                        scanned_count += 1

                    page_qualities.append(
                        {
                            "page_number": i + 1,
                            "quality_score": quality_score,
                            "is_scanned": is_scanned,
                            "brightness": self._calculate_brightness(image),
                            "contrast": self._calculate_contrast(image),
                        }
                    )

                except Exception as e:
                    logger.warning(f"页面{i + 1}分析失败: {str(e)}")
                    continue

            avg_quality = (
                sum(pq["quality_score"] for pq in page_qualities) / len(page_qualities)
                if page_qualities
                else 0
            )
            scanned_ratio = scanned_count / len(page_qualities) if page_qualities else 0

            return {
                "page_qualities": page_qualities,
                "avg_quality_score": avg_quality,
                "scanned_ratio": scanned_ratio,
                "analyzed_pages": len(page_qualities),
            }

        except Exception as e:
            logger.warning(f"详细页面分析失败: {str(e)}")
            return {
                "page_qualities": [],
                "avg_quality_score": 0.0,
                "scanned_ratio": 0.0,
                "analyzed_pages": 0,
            }

    def _assess_image_quality(self, image: Image.Image) -> float:
        """评估图像质量"""
        try:
            # 转换为灰度图
            gray = image.convert("L")
            img_array = np.array(gray)

            # 计算清晰度（拉普拉斯方差）
            laplacian_var = cv2.Laplacian(img_array, cv2.CV_64F).var()

            # 计算噪声水平
            noise_level = self._calculate_noise_level(img_array)

            # 综合质量评分
            clarity_score = min(laplacian_var / 1000, 1.0)  # 标准化
            noise_score = max(0, 1 - noise_level / 50)  # 噪声越低分数越高

            quality_score = clarity_score * 0.7 + noise_score * 0.3

            return min(max(quality_score, 0.0), 1.0)

        except Exception as e:
            logger.warning(f"图像质量评估失败: {str(e)}")
            return 0.5

    def _calculate_noise_level(self, img_array: np.ndarray) -> float:
        """计算图像噪声水平"""
        try:
            # 使用高斯滤波器计算噪声
            blurred = cv2.GaussianBlur(img_array, (5, 5), 0)
            noise = np.abs(img_array.astype(float) - blurred.astype(float))
            return np.mean(noise)
        except (Exception, OSError, ValueError):
            # 图像处理异常时返回默认值
            return 25.0  # 默认中等噪声水平

    def _detect_scanned_page(self, image: Image.Image) -> bool:
        """检测是否为扫描页面"""
        try:
            # 转换为灰度图
            gray = image.convert("L")
            img_array = np.array(gray)

            # 计算边缘密度
            edges = cv2.Canny(img_array, 50, 150)
            edge_density = np.sum(edges > 0) / (img_array.shape[0] * img_array.shape[1])

            # 扫描文档通常有更高的边缘密度
            return edge_density > 0.05

        except Exception as e:
            logger.warning(f"扫描检测失败: {str(e)}")
            return False

    def _calculate_brightness(self, image: Image.Image) -> float:
        """计算图像亮度"""
        try:
            gray = image.convert("L")
            img_array = np.array(gray)
            return np.mean(img_array) / 255.0
        except (Exception, OSError, ValueError):
            # 数据计算异常时返回默认值
            return 0.5

    def _calculate_contrast(self, image: Image.Image) -> float:
        """计算图像对比度"""
        try:
            gray = image.convert("L")
            img_array = np.array(gray)
            return np.std(img_array) / 128.0
        except (Exception, OSError, ValueError):
            # 数据计算异常时返回默认值
            return 0.5

    def _combine_analysis_results(
        self, quick_analysis: dict, page_analysis: dict, file_size_mb: float
    ) -> DocumentAnalysis:
        """综合分析结果"""
        # 确定文档类型
        doc_type = quick_analysis["document_type"]
        if page_analysis["scanned_ratio"] > 0.7:
            doc_type = DocumentType.SCANNED_CONTRACT
        elif quick_analysis["text_density"] > 0.7:
            doc_type = DocumentType.DIGITAL_CONTRACT
        else:
            doc_type = DocumentType.MIXED_CONTRACT

        # 计算综合质量分数
        text_score = quick_analysis["text_density"]
        image_score = page_analysis["avg_quality_score"]
        size_penalty = min(file_size_mb / 50, 1.0) * 0.1  # 大文件轻微扣分

        quality_score = text_score * 0.4 + image_score * 0.5 + (1 - size_penalty) * 0.1
        quality_score = min(max(quality_score, 0.0), 1.0)

        # 确定质量等级
        if quality_score >= 0.8:
            processing_quality = ProcessingQuality.EXCELLENT
        elif quality_score >= 0.6:
            processing_quality = ProcessingQuality.GOOD
        elif quality_score >= 0.4:
            processing_quality = ProcessingQuality.FAIR
        else:
            processing_quality = ProcessingQuality.POOR

        # 生成建议
        recommendations = self._generate_recommendations(
            doc_type, processing_quality, quick_analysis, page_analysis
        )

        return DocumentAnalysis(
            document_type=doc_type,
            quality_score=quality_score,
            processing_quality=processing_quality,
            total_pages=quick_analysis["total_pages"],
            scanned_pages=int(
                page_analysis["scanned_ratio"] * page_analysis["analyzed_pages"]
            ),
            digital_pages=page_analysis["analyzed_pages"]
            - int(page_analysis["scanned_ratio"] * page_analysis["analyzed_pages"]),
            text_density=quick_analysis["text_density"],
            image_quality=page_analysis["avg_quality_score"],
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self,
        doc_type: DocumentType,
        quality: ProcessingQuality,
        quick_analysis: dict,
        page_analysis: dict,
    ) -> list[str]:
        """生成处理建议"""
        recommendations = []

        if doc_type == DocumentType.SCANNED_CONTRACT:
            recommendations.append("建议使用高分辨率OCR处理（DPI 300+）")
            recommendations.append("启用图像预处理以提高识别准确率")
            if quality == ProcessingQuality.POOR:
                recommendations.append("文档质量较差，建议重新扫描或使用专业OCR工具")
        elif doc_type == DocumentType.DIGITAL_CONTRACT:
            recommendations.append("可以直接提取文本，OCR处理为备选方案")
        else:
            recommendations.append("建议使用混合处理模式：文本提取+OCR补充")

        if quick_analysis["text_density"] < 0.1:
            recommendations.append("文本密度较低，可能需要人工校验识别结果")

        if page_analysis["avg_quality_score"] < 0.5:
            recommendations.append("图像质量偏低，建议启用图像增强功能")

        if quick_analysis["total_pages"] > 20:
            recommendations.append("页面数量较多，建议分批处理以避免内存溢出")

        return recommendations

    async def optimize_processing_config(
        self, analysis: DocumentAnalysis
    ) -> ProcessingConfig:
        """根据分析结果优化处理配置"""
        config = ProcessingConfig()

        # 根据文档类型配置
        if analysis.document_type == DocumentType.SCANNED_CONTRACT:
            config.use_ocr = True
            config.dpi = (
                300
                if analysis.processing_quality
                in [ProcessingQuality.EXCELLENT, ProcessingQuality.GOOD]
                else 400
            )
            config.enable_preprocessing = True
            config.enable_enhancement = True
            config.confidence_threshold = (
                0.5 if analysis.processing_quality == ProcessingQuality.POOR else 0.6
            )
        elif analysis.document_type == DocumentType.DIGITAL_CONTRACT:
            config.use_ocr = False
            config.dpi = 200
            config.enable_preprocessing = False
            config.confidence_threshold = 0.8
        else:
            config.use_ocr = True
            config.dpi = 250
            config.enable_preprocessing = True
            config.confidence_threshold = 0.6

        # 根据页面数量配置
        if analysis.total_pages > 30:
            config.max_pages = 20  # 分批处理
            config.enable_parallel = True
        else:
            config.max_pages = analysis.total_pages

        # 根据质量配置
        if analysis.processing_quality == ProcessingQuality.POOR:
            config.enable_enhancement = True
            config.confidence_threshold = 0.5

        return config

    async def preprocess_image(
        self, image: Image.Image, config: ProcessingConfig
    ) -> Image.Image:
        """图像预处理"""
        if not config.enable_preprocessing:
            return image

        try:
            # 转换为OpenCV格式
            img_array = np.array(image.convert("RGB"))

            # 降噪
            img_array = cv2.fastNlMeansDenoisingColored(img_array, None, 10, 10, 7, 21)

            # 锐化
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            img_array = cv2.filter2D(img_array, -1, kernel)

            # 对比度增强
            lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l_channel = clahe.apply(l_channel)
            img_array = cv2.merge([l_channel, a_channel, b_channel])
            img_array = cv2.cvtColor(img_array, cv2.COLOR_LAB2RGB)

            # 转换回PIL格式
            return Image.fromarray(img_array)

        except Exception as e:
            logger.warning(f"图像预处理失败: {str(e)}")
            return image

    async def process_with_enhanced_config(
        self, file_path: str, custom_config: ProcessingConfig | None = None
    ) -> dict[str, Any]:
        """使用增强配置处理PDF"""
        try:
            # 分析文档
            analysis = await self.analyze_document(file_path)

            # 获取处理配置
            if custom_config:
                config = custom_config
            else:
                config = await self.optimize_processing_config(analysis)

            logger.info(
                f"使用增强配置处理PDF: {Path(file_path).name}, 配置: OCR={config.use_ocr}, DPI={config.dpi}"
            )

            # 调用原始处理服务，使用优化配置
            result = await pdf_processing_service.extract_text_from_pdf(
                file_path=file_path,
                prefer_ocr=config.use_ocr,
                dpi=config.dpi,
                max_pages=config.max_pages,
                enable_preprocessing=config.enable_preprocessing,
                enable_enhancement=config.enable_enhancement,
                confidence_threshold=config.confidence_threshold,
            )

            # 添加增强处理信息
            if result.get("success"):
                result["enhanced_processing"] = {
                    "document_analysis": {
                        "document_type": analysis.document_type.value,
                        "quality_score": analysis.quality_score,
                        "processing_quality": analysis.processing_quality.value,
                        "recommendations": analysis.recommendations,
                    },
                    "processing_config": {
                        "use_ocr": config.use_ocr,
                        "dpi": config.dpi,
                        "enable_preprocessing": config.enable_preprocessing,
                        "confidence_threshold": config.confidence_threshold,
                    },
                    "enhancement_applied": config.enable_enhancement,
                    "processing_timestamp": datetime.now().isoformat(),
                }

            return result

        except Exception as e:
            logger.error(f"增强处理失败: {str(e)}")
            return {
                "success": False,
                "error": f"增强处理失败: {str(e)}",
                "text": "",
                "pages": [],
            }


# 创建全局实例
enhanced_pdf_processor = EnhancedPDFProcessor()
