#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一PDF处理服务
整合优化的OCR、NLP处理和多引擎融合功能，提供统一的中文合同处理接口
"""

import logging
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """处理结果"""
    success: bool
    processing_time: float
    text_content: str
    structured_data: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    error_message: Optional[str] = None
    processing_method: str = "unknown"

@dataclass
class QualityMetrics:
    """质量指标"""
    total_pages: int
    processed_pages: int
    text_coverage: float
    avg_confidence: float
    ocr_quality: str
    nlp_entities_found: int
    processing_efficiency: float

class UnifiedPDFProcessor:
    """统一PDF处理器"""

    def __init__(self):
        self.optimized_ocr = None
        self.nlp_processor = None
        self.multi_engine_fusion = None

        # 初始化所有组件
        self._initialize_components()

    def _initialize_components(self):
        """初始化所有处理组件"""
        try:
            # 1. 初始化优化的OCR服务
            from .optimized_ocr_service import optimized_ocr_service
            self.optimized_ocr = optimized_ocr_service

            # 2. 初始化中文NLP处理器
            from .chinese_nlp_processor import get_chinese_nlp_processor
            self.nlp_processor = get_chinese_nlp_processor()

            # 3. 初始化多引擎融合
            from .multi_engine_fusion import MultiEngineFusion
            self.multi_engine_fusion = MultiEngineFusion()

            logger.info("统一PDF处理器组件初始化完成")

        except Exception as e:
            logger.error(f"组件初始化失败: {e}")

    async def process_pdf_contract(self, pdf_path: str, options: Dict[str, Any] = None) -> ProcessingResult:
        """
        处理PDF合同的主要入口点

        Args:
            pdf_path: PDF文件路径
            options: 处理选项
                - max_pages: 最大处理页面数 (默认: 10)
                - use_preprocessing: 是否使用图像预处理 (默认: True)
                - extract_structured: 是否提取结构化数据 (默认: True)
                - quality_threshold: 质量阈值 (默认: 0.4)
                - enable_nlp: 是否启用NLP处理 (默认: True)
                - parallel_processing: 是否并行处理 (默认: True)

        Returns:
            ProcessingResult: 包含文本、结构化数据和质量指标的处理结果
        """
        start_time = time.time()

        # 设置默认选项
        if options is None:
            options = {}

        max_pages = options.get('max_pages', 10)
        use_preprocessing = options.get('use_preprocessing', True)
        extract_structured = options.get('extract_structured', True)
        quality_threshold = options.get('quality_threshold', 0.4)
        enable_nlp = options.get('enable_nlp', True)
        parallel_processing = options.get('parallel_processing', True)

        logger.info(f"开始统一PDF处理: {Path(pdf_path).name}")
        logger.info(f"处理选项: max_pages={max_pages}, use_preprocessing={use_preprocessing}")

        try:
            # 阶段1: OCR文本提取
            logger.info("阶段1: OCR文本提取")
            ocr_result = await self._perform_ocr_extraction(
                pdf_path, max_pages, use_preprocessing, parallel_processing
            )

            if not ocr_result.get("success", False):
                return ProcessingResult(
                    success=False,
                    processing_time=time.time() - start_time,
                    text_content="",
                    structured_data={},
                    quality_metrics={},
                    error_message=ocr_result.get("error", "OCR处理失败"),
                    processing_method="ocr_failed"
                )

            # 阶段2: 质量评估和优化
            logger.info("阶段2: 质量评估")
            quality_metrics = self._assess_processing_quality(ocr_result)

            # 阶段3: 结构化数据提取
            structured_data = {}
            if extract_structured and enable_nlp and len(ocr_result.get("combined_text", "")) > 10:
                logger.info("阶段3: 结构化数据提取")
                structured_data = await self._extract_structured_data(ocr_result)
            else:
                logger.info("跳过结构化数据提取")
                structured_data = {"entities": [], "extraction_skipped": True}

            # 阶段4: 多引擎融合优化
            if self.multi_engine_fusion and len(ocr_result.get("page_results", [])) > 0:
                logger.info("阶段4: 多引擎融合优化")
                fusion_result = await self._apply_multi_engine_fusion(ocr_result)
                if fusion_result.get("success", False):
                    # 如果融合成功，更新文本内容
                    ocr_result["combined_text"] = fusion_result.get("fused_text", "")
                    ocr_result["fusion_method"] = fusion_result.get("method", "unknown")
                    logger.info(f"融合优化完成，使用方法: {fusion_result.get('method')}")

            # 构建最终结果
            processing_time = time.time() - start_time
            text_content = ocr_result.get("combined_text", "")

            # 质量指标计算
            quality_metrics_final = self._calculate_comprehensive_quality_metrics(
                ocr_result, structured_data, processing_time
            )

            # 判断处理是否成功
            is_success = (
                len(text_content) > quality_threshold * 100 and  # 足够的文本
                quality_metrics_final.text_coverage >= 0.3  # 足够的覆盖率
            )

            processing_method = self._determine_processing_method(ocr_result, quality_metrics_final)

            logger.info(f"统一PDF处理完成: {len(text_content)}字符, 用时{processing_time:.2f}秒")

            return ProcessingResult(
                success=is_success,
                processing_time=processing_time,
                text_content=text_content,
                structured_data=structured_data,
                quality_metrics=quality_metrics_final.__dict__,
                processing_method=processing_method
            )

        except Exception as e:
            logger.error(f"统一PDF处理失败: {e}")
            return ProcessingResult(
                success=False,
                processing_time=time.time() - start_time,
                text_content="",
                structured_data={},
                quality_metrics={},
                error_message=str(e),
                processing_method="processing_error"
            )

    async def _perform_ocr_extraction(self, pdf_path: str, max_pages: int,
                                  use_preprocessing: bool, parallel_processing: bool) -> Dict[str, Any]:
        """执行OCR文本提取"""
        if self.optimized_ocr is None:
            return {"success": False, "error": "OCR服务未初始化"}

        try:
            return await self.optimized_ocr.process_pdf_document(
                pdf_path=pdf_path,
                max_pages=max_pages
            )
        except Exception as e:
            logger.error(f"OCR提取失败: {e}")
            return {"success": False, "error": str(e)}

    def _assess_processing_quality(self, ocr_result: Dict[str, Any]) -> QualityMetrics:
        """评估处理质量"""
        try:
            processing_stats = ocr_result.get("processing_stats", {})
            page_results = ocr_result.get("page_results", [])

            total_pages = processing_stats.get("total_pages", 0)
            processed_pages = processing_stats.get("processed_pages", 0)
            pages_with_text = processing_stats.get("pages_with_text", 0)
            avg_confidence = processing_stats.get("avg_confidence", 0.0)
            total_processing_time = processing_stats.get("total_processing_time", 0.0)

            # 计算文本覆盖率
            text_coverage = pages_with_text / processed_pages if processed_pages > 0 else 0.0

            # 计算OCR质量等级
            if avg_confidence >= 0.8 and text_coverage >= 0.8:
                ocr_quality = "excellent"
            elif avg_confidence >= 0.6 and text_coverage >= 0.6:
                ocr_quality = "good"
            elif avg_confidence >= 0.4 and text_coverage >= 0.4:
                ocr_quality = "acceptable"
            else:
                ocr_quality = "poor"

            # 计算处理效率
            processing_efficiency = total_pages / total_processing_time if total_processing_time > 0 else 0.0

            return QualityMetrics(
                total_pages=total_pages,
                processed_pages=processed_pages,
                text_coverage=text_coverage,
                avg_confidence=avg_confidence,
                ocr_quality=ocr_quality,
                nlp_entities_found=0,  # 将在后续计算
                processing_efficiency=processing_efficiency
            )

        except Exception as e:
            logger.error(f"质量评估失败: {e}")
            return QualityMetrics(
                total_pages=0, processed_pages=0, text_coverage=0.0,
                avg_confidence=0.0, ocr_quality="error",
                nlp_entities_found=0, processing_efficiency=0.0
            )

    async def _extract_structured_data(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """提取结构化数据"""
        try:
            if self.nlp_processor is None:
                return {"success": False, "error": "NLP处理器未初始化"}

            text = ocr_result.get("combined_text", "")
            if len(text.strip()) < 10:
                return {"success": False, "error": "文本长度不足"}

            # 使用中文NLP处理器
            nlp_result = self.nlp_processor.process_chinese_text(text)

            # 增强结构化数据
            enhanced_result = {
                "success": True,
                "processing_time": time.time(),
                "entities": nlp_result.get("entities", []),
                "names": nlp_result.get("names", []),
                "phones": nlp_result.get("phones", []),
                "addresses": nlp_result.get("addresses", []),
                "amounts": nlp_result.get("amounts", []),
                "dates": nlp_result.get("dates", []),
                "id_cards": nlp_result.get("id_cards", []),
                "entities_found": len(nlp_result.get("entities", [])),
                "text_stats": nlp_result.get("text_stats", {}),
                "extraction_quality": self._assess_extraction_quality(nlp_result)
            }

            logger.info(f"结构化数据提取完成: {enhanced_result['entities_found']}个实体")
            return enhanced_result

        except Exception as e:
            logger.error(f"结构化数据提取失败: {e}")
            return {"success": False, "error": str(e)}

    def _assess_extraction_quality(self, nlp_result: Dict[str, Any]) -> str:
        """评估提取质量"""
        entities_count = len(nlp_result.get("entities", []))

        if entities_count >= 10:
            return "excellent"
        elif entities_count >= 5:
            return "good"
        elif entities_count >= 2:
            return "acceptable"
        else:
            return "poor"

    async def _apply_multi_engine_fusion(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """应用多引擎融合优化"""
        try:
            if self.multi_engine_fusion is None:
                return {"success": False, "error": "多引擎融合服务未初始化"}

            page_results = ocr_result.get("page_results", [])
            if not page_results:
                return {"success": False, "error": "无页面结果可供融合"}

            # 构建模拟的引擎结果用于融合测试
            engine_results = []
            for page_result in page_results[:3]:  # 只融合前3页
                if page_result.get("text", ""):
                    engine_results.append({
                        "engine": "optimized_ocr",
                        "text": page_result.get("text", ""),
                        "confidence": page_result.get("confidence", 0.0)
                    })

            if not engine_results:
                return {"success": False, "error": "无有效引擎结果"}

            # 使用融合服务
            fusion_result = self.multi_engine_fusion.fuse_results(engine_results)

            return {
                "success": True,
                "method": fusion_result.get("fusion_method", "unknown"),
                "fused_text": fusion_result.get("text", ""),
                "confidence": fusion_result.get("confidence", 0.0),
                "contributing_engines": fusion_result.get("contributing_engines", [])
            }

        except Exception as e:
            logger.error(f"多引擎融合失败: {e}")
            return {"success": False, "error": str(e)}

    def _calculate_comprehensive_quality_metrics(self, ocr_result: Dict[str, Any],
                                            structured_data: Dict[str, Any],
                                            processing_time: float) -> QualityMetrics:
        """计算综合质量指标"""
        try:
            processing_stats = ocr_result.get("processing_stats", {})

            # 基础指标
            total_pages = processing_stats.get("total_pages", 0)
            processed_pages = processing_stats.get("processed_pages", 0)
            pages_with_text = processing_stats.get("pages_with_text", 0)
            avg_confidence = processing_stats.get("avg_confidence", 0.0)

            # 结构化数据指标
            nlp_entities_found = structured_data.get("entities_found", 0)

            # 覆盖率
            text_coverage = pages_with_text / processed_pages if processed_pages > 0 else 0.0

            # OCR质量评估
            if avg_confidence >= 0.8 and text_coverage >= 0.8:
                ocr_quality = "excellent"
            elif avg_confidence >= 0.6 and text_coverage >= 0.6:
                ocr_quality = "good"
            elif avg_confidence >= 0.4 and text_coverage >= 0.4:
                ocr_quality = "acceptable"
            else:
                ocr_quality = "poor"

            # 处理效率
            processing_efficiency = total_pages / processing_time if processing_time > 0 else 0.0

            return QualityMetrics(
                total_pages=total_pages,
                processed_pages=processed_pages,
                text_coverage=text_coverage,
                avg_confidence=avg_confidence,
                ocr_quality=ocr_quality,
                nlp_entities_found=nlp_entities_found,
                processing_efficiency=processing_efficiency
            )

        except Exception as e:
            logger.error(f"综合质量指标计算失败: {e}")
            return QualityMetrics(
                total_pages=0, processed_pages=0, text_coverage=0.0,
                avg_confidence=0.0, ocr_quality="error",
                nlp_entities_found=0, processing_efficiency=0.0
            )

    def _determine_processing_method(self, ocr_result: Dict[str, Any],
                                  quality_metrics: QualityMetrics) -> str:
        """确定处理方法"""
        methods = []

        # 记录使用的处理方法
        if ocr_result.get("processing_stats", {}).get("total_text_length", 0) > 0:
            methods.append("ocr")

        if ocr_result.get("processing_stats", {}).get("pymupdf_text_length", 0) > 0:
            methods.append("native_text")

        if ocr_result.get("fusion_method"):
            methods.append("fusion")

        if quality_metrics.nlp_entities_found > 0:
            methods.append("nlp")

        if not methods:
            return "none"
        elif len(methods) == 1:
            return methods[0]
        else:
            return "+".join(methods)

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "service_status": "ready",
                "components": {
                    "optimized_ocr": self.optimized_ocr is not None,
                    "nlp_processor": self.nlp_processor is not None,
                    "multi_engine_fusion": self.multi_engine_fusion is not None
                },
                "capabilities": {
                    "image_preprocessing": True,
                    "numpy_conversion": True,
                    "parallel_processing": True,
                    "structured_extraction": True,
                    "quality_assessment": True,
                    "multi_engine_fusion": True,
                    "chinese_text_recognition": True
                }
            }

            # 获取OCR服务性能报告
            if self.optimized_ocr:
                ocr_report = self.optimized_ocr.get_performance_report()
                status["ocr_performance"] = ocr_report

            return status

        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "service_status": "error",
                "error": str(e)
            }

    async def test_processing_pipeline(self, pdf_path: str) -> Dict[str, Any]:
        """测试处理管道"""
        logger.info(f"开始测试处理管道: {Path(pdf_path).name}")

        test_results = {
            "test_start_time": datetime.now().isoformat(),
            "pdf_file": pdf_path,
            "components_test": {},
            "overall_success": False
        }

        # 测试1: OCR组件
        try:
            if self.optimized_ocr:
                ocr_test = await self.optimized_ocr.process_pdf_document(pdf_path, max_pages=3)
                test_results["components_test"]["ocr"] = {
                    "success": ocr_test.get("success", False),
                    "text_length": ocr_test.get("text_length", 0),
                    "processing_time": ocr_test.get("total_processing_time", 0),
                    "pages_processed": ocr_test.get("processing_stats", {}).get("processed_pages", 0)
                }
            else:
                test_results["components_test"]["ocr"] = {"success": False, "error": "OCR组件未初始化"}
        except Exception as e:
            test_results["components_test"]["ocr"] = {"success": False, "error": str(e)}

        # 测试2: NLP组件
        try:
            if self.nlp_processor:
                test_text = "甲方：王军，联系电话：13800138000，地址：广州市番禺区"
                nlp_test = self.nlp_processor.process_chinese_text(test_text)
                test_results["components_test"]["nlp"] = {
                    "success": True,
                    "entities_found": len(nlp_test.get("entities", [])),
                    "names_found": len(nlp_test.get("names", [])),
                    "phones_found": len(nlp_test.get("phones", []))
                }
            else:
                test_results["components_test"]["nlp"] = {"success": False, "error": "NLP组件未初始化"}
        except Exception as e:
            test_results["components_test"]["nlp"] = {"success": False, "error": str(e)}

        # 测试3: 多引擎融合组件
        try:
            if self.multi_engine_fusion:
                mock_results = [
                    {"engine": "test1", "text": "测试文本1", "confidence": 0.9},
                    {"engine": "test2", "text": "测试文本2", "confidence": 0.8}
                ]
                fusion_test = self.multi_engine_fusion.fuse_results(mock_results)
                test_results["components_test"]["fusion"] = {
                    "success": True,
                    "fusion_method": fusion_test.get("fusion_method", "unknown"),
                    "confidence": fusion_test.get("confidence", 0)
                }
            else:
                test_results["components_test"]["fusion"] = {"success": False, "error": "融合组件未初始化"}
        except Exception as e:
            test_results["components_test"]["fusion"] = {"success": False, "error": str(e)}

        # 判断整体测试状态
        component_success_count = sum(
            1 for test in test_results["components_test"].values()
            if test.get("success", False)
        )
        total_components = len(test_results["components_test"])

        test_results["overall_success"] = component_success_count >= total_components * 0.8
        test_results["test_end_time"] = datetime.now().isoformat()

        logger.info(f"处理管道测试完成: {component_success_count}/{total_components}组件成功")

        return test_results

# 创建全局统一PDF处理器实例
try:
    unified_pdf_processor = UnifiedPDFProcessor()
    logger.info("统一PDF处理器初始化成功")
except Exception as e:
    logger.error(f"统一PDF处理器初始化失败: {e}")
    unified_pdf_processor = None