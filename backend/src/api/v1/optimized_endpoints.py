#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
优化的API端点
集成性能监控、缓存、错误处理等功能
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone

from .monitoring import APIMonitoringService, record_api_call, get_performance_summary, generate_performance_report
from ...services.unified_pdf_processor import unified_pdf_processor
from .utils.api_performance_optimizer import optimize_api_response_time, cache_api_result, get_performance_stats
from ...services.enhanced_error_handler import enhanced_error_handler, handle_pdf_error, handle_ocr_error

logger = logging.getLogger(__name__)

class OptimizedPDFEndpoints:
    """优化的PDF API端点"""

    def __init__(self):
        self.pdf_processor = None
        self.monitoring = APIMonitoringService()

        # 延迟初始化PDF处理器
        try:
            self._initialize_pdf_processor()
            logger.info("优化PDF处理器初始化完成")
        except Exception as e:
            logger.error(f"优化PDF处理器初始化失败: {e}")

    def _initialize_pdf_processor(self):
        """延迟初始化PDF处理器"""
        try:
            from ...services.unified_pdf_processor import unified_pdf_processor
            self.pdf_processor = unified_pdf_processor()
            logger.info("延迟PDF处理器初始化成功")
        except ImportError as e:
            logger.warning(f"延迟初始化失败，使用fallback: {e}")

    async def upload_pdf_file_optimized(self, file_path: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """优化的PDF文件上传端点"""
        start_time = time.time()

        if not self.pdf_processor:
            return handle_pdf_error(
                "PDF处理器未初始化",
                "pdf_processor_unavailable",
                {"upload_time": 0, "success": False}
            )

        try:
            # 记录API调用
            record_api_call("/upload", "upload_pdf_file_optimized", 0, 200, True)

            # 执行优化的PDF处理
            result = await self.pdf_processor.process_pdf_contract(file_path, options or {})

            processing_time = (time.time() - start_time) * 1000

            # 记录处理完成
            record_api_call(
                "/upload", "process_pdf_contract", processing_time,
                200 if result.success else 500,
                result.success
            )

            if result.success:
                return {
                    "success": True,
                    "message": "PDF文件上传并处理成功",
                    "session_id": result.structured_data.get("session_id", ""),
                    "processing_time": processing_time / 1000,  # 转换为毫秒
                    "text_extracted": result.text_content,
                    "text_length": len(result.text_content),
                    "quality_metrics": result.quality_metrics,
                    "structured_data": result.structured_data,
                    "processing_method": result.processing_method,
                    "recommendations": self._generate_processing_recommendations(result),
                    "optimization_level": self._assess_optimization_level(processing_time)
                }
            else:
                return handle_pdf_error(
                    f"PDF处理失败: {result.get('error_message', '未知错误')}",
                    "processing_failed",
                    {"upload_time": 0, "success": False}
                )

        except Exception as e:
            logger.error(f"PDF上传优化处理失败: {e}")
            return handle_pdf_error(
                f"系统错误: {str(e)}",
                "system_error",
                {"upload_time": 0, "success": False}
            )

    def _generate_processing_recommendations(self, result: Dict[str, Any]) -> List[str]:
        """生成处理建议"""
        recommendations = []

        processing_time = result.get("processing_time", 0) / 1000  # 转换为秒

        # 基于处理时间的建议
        if processing_time < 10000:  # 小于10秒，优秀
            recommendations.append("处理速度优秀，建议保持当前配置")
        elif processing_time < 30000:  # 小于30秒，良好
            recommendations.append("处理速度良好，可适当增加OCR精度以获得更好结果")
        elif processing_time < 60000:  # 小于60秒，一般
            recommendations.append("处理速度一般，建议优化OCR参数或启用预处理")
        else:
            recommendations.append("处理速度较慢，建议启用并行处理或优化图像质量")

        # 基于文本长度的建议
        text_length = result.get("text_length", 0)
        if text_length < 100:
            recommendations.append("提取文本较少，可能为扫描件质量问题")
        elif text_length < 500:
            recommendations.append("文本提取中等，建议检查OCR配置")
        else:
            recommendations.append("文本提取充分，系统运行良好")

        # 基于质量指标的建议
        quality_metrics = result.get("quality_metrics", {})
        avg_confidence = quality_metrics.get("avg_confidence", 0)
        text_coverage = quality_metrics.get("text_coverage", 0)

        if avg_confidence < 0.6:
            recommendations.append("识别置信度较低，建议使用多引擎融合")
        if text_coverage < 0.7:
            recommendations.append("文本覆盖率不足，建议增加OCR分辨率或预处理")

        return recommendations

    def _assess_optimization_level(self, processing_time: float) -> str:
        """评估优化水平"""
        if processing_time < 10000:
            return "excellent"
        elif processing_time < 30000:
            return "good"
        elif processing_time < 60000:
            return "acceptable"
        else:
            return "poor"

    async def get_session_status_optimized(self, session_id: str) -> Dict[str, Any]:
        """优化的会话状态查询"""
        start_time = time.time()

        # 记录API调用
        record_api_call("/progress", "get_session_status_optimized", 0, 200, True)

        try:
            if not self.pdf_processor:
                return {
                    "success": False,
                    "error_message": "PDF处理器未初始化",
                    "session_status": None
                }

            # 使用统一处理器查询状态
            status = await self.pdf_processor.get_system_status()

            processing_time = (time.time() - start_time) * 1000

            return {
                "success": True,
                "session_status": status,
                "system_components": status.get("components", {}),
                "performance_stats": status.get("ocr_performance", {}),
                "recommendations": status.get("capabilities", {}),
                "response_time": processing_time
            }

        except Exception as e:
            logger.error(f"查询会话状态失败: {e}")
            record_api_call("/progress", "get_session_status_optimized", 0, 500, False)

            return {
                "success": False,
                "error_message": f"查询失败: {str(e)}",
                "session_status": None
            }

    async def process_pdf_with_optimization(self, session_id: str, file_path: str,
                                             processing_options: Dict[str, Any]) -> Dict[str, Any]:
        """带有优化的PDF处理"""
        start_time = time.time()

        # 记录API调用
        record_api_call("/process", "process_pdf_with_optimization", 0, 200, True)

        try:
            if not self.pdf_processor:
                return handle_pdf_error(
                    "PDF处理器未初始化",
                    "processor_unavailable",
                    {"processing_time": 0, "success": False}
                )

            # 应用优化选项
            optimized_options = self._apply_optimization_rules(processing_options)

            # 执行优化处理
            result = await self.pdf_processor.process_pdf_contract(file_path, optimized_options)

            processing_time = (time.time() - start_time) * 1000

            # 记录处理完成
            record_api_call(
                "/process", "process_pdf_with_optimization", processing_time,
                200 if result.success else 500,
                result.success
            )

            if result.success:
                return {
                    "success": True,
                    "message": "PDF处理完成（已优化）",
                    "session_id": result.structured_data.get("session_id", ""),
                    "processing_time": processing_time,
                    "text_extracted": result.text_content,
                    "text_length": len(result.text_content),
                    "quality_metrics": result.quality_metrics,
                    "structured_data": result.structured_data,
                    "processing_method": result.processing_method,
                    "optimization_level": self._assess_optimization_level(processing_time),
                    "recommendations": self._generate_processing_recommendations(result)
                }
            else:
                return handle_pdf_error(
                    f"PDF处理失败: {result.get('error_message', '未知错误')}",
                    "processing_failed",
                    {"processing_time": 0, "success": False}
                )

        except Exception as e:
            logger.error(f"优化PDF处理失败: {e}")
            record_api_call("/process", "process_pdf_with_optimization", 0, 500, False)

            return handle_pdf_error(
                f"系统错误: {str(e)}",
                "system_error",
                {"processing_time": 0, "success": False}
            )

    def _apply_optimization_rules(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """应用优化规则"""
        optimized_options = options.copy()

        # 根据文件大小调整处理策略
        # 注意：这里可以根据实际需要添加更多优化逻辑

        return optimized_options

    def get_optimization_summary(self) -> Dict[str, Any]:
        """获取优化总结"""
        try:
            performance_stats = get_performance_stats()
            monitoring_status = self.monitoring.get_real_time_monitoring("/upload", 60) if self.monitoring else {}

            return {
                "timestamp": datetime.now().isoformat(),
                "pdf_processor_status": "ready" if self.pdf_processor else "unavailable",
                "monitoring_active": len(monitoring_status.get("calls", [])) > 0,
                "performance_summary": performance_stats,
                "optimization_enabled": True,
                "recent_alerts": len(self.monitoring.alerts[-10:]),
                "recommendations": self._generate_system_recommendations()
            }
        except Exception as e:
            logger.error(f"获取优化总结失败: {e}")
            return {"error": str(e)}

    def _generate_system_recommendations(self) -> List[str]:
        """生成系统优化建议"""
        recommendations = []

        try:
            performance_stats = get_performance_stats()
            avg_response_time = performance_stats.get("avg_response_time_ms", 0) / 1000

            if avg_response_time > 1000:  # 大于1秒
                recommendations.append("建议启用响应压缩以减少传输时间")

            if performance_stats.get("error_rate", 0) > 0.1:
                recommendations.append("建议检查和优化错误处理逻辑")

            if performance_stats.get("cache_hit_rate", 0) < 0.5:
                recommendations.append("建议优化缓存策略以提高命中率")

            if len(performance_stats.get("slow_requests", [])) > 0:
                recommendations.append("建议分析慢请求并优化数据库查询")

        except Exception as e:
            recommendations.append("无法获取性能统计")

        return recommendations

# 创建全局优化端点实例
optimized_endpoints = OptimizedPDFEndpoints()
logger.info("优化API端点初始化完成")