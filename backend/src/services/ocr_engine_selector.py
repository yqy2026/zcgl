"""
OCR引擎选择器
智能选择最适合的OCR引擎处理不同类型的文档
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class OCREngineSelector:
    """OCR引擎智能选择器"""

    def __init__(self):
        # 引擎能力评估
        self.engine_capabilities = {
            "tesseract": {
                "strengths": [
                    "individual_characters",
                    "established_reliability",
                    "language_coverage",
                    "lightweight",
                    "fast_processing",
                ],
                "weaknesses": [
                    "chinese_accuracy",
                    "layout_analysis",
                    "handwriting_support",
                    "complex_documents",
                ],
                "optimal_for": [
                    "simple_text",
                    "english_content",
                    "structured_layouts",
                    "printed_text",
                ],
                "accuracy_estimates": {
                    "chinese": 0.85,
                    "english": 0.95,
                    "mixed": 0.80,
                    "handwritten": 0.30,
                },
            },
            "paddleocr": {
                "strengths": [
                    "chinese_accuracy",
                    "layout_analysis",
                    "handwriting_support",
                    "complex_documents",
                    "table_recognition",
                ],
                "weaknesses": [
                    "resource_heavy",
                    "slower_startup",
                    "complex_installation",
                ],
                "optimal_for": [
                    "chinese_documents",
                    "complex_layouts",
                    "scanned_contracts",
                    "mixed_content",
                ],
                "accuracy_estimates": {
                    "chinese": 0.95,
                    "english": 0.93,
                    "mixed": 0.92,
                    "handwritten": 0.85,
                },
            },
        }

        # 文档类型识别规则
        self.document_patterns = {
            "chinese_contract": [
                r"租赁合同|合同编号|承租方|出租方",
                r"包装合字|租字|第\d+号",
                r"甲方|乙方|租赁期限|月租金",
            ],
            "english_document": [
                r"[A-Za-z\s]{100,}",  # 大段英文
                r"Contract|Agreement|Lease",
                r"Tenant|Landlord|Rent",
            ],
            "mixed_content": [
                r"[A-Za-z]+[\u4e00-\u9fff]+",  # 中英混合
                r"[\u4e00-\u9fff]+[A-Za-z]+",
                r"Contract.*合同|Agreement.*协议",
            ],
            "simple_text": [
                r"^[A-Za-z0-9\s\.,!?;:()\-]+$",  # 简单文本
                r"^[\u4e00-\u9fff\s\.,!?;:()\-]+$",  # 简单中文
            ],
            "complex_layout": [
                r"表格|Table|表\d+",
                r"第.*页|Page\s*\d+",
                r"附件|Appendix|附图",
            ],
            "scanned_document": [
                # 这些特征通常通过图像分析检测
                # 这里作为占位符
            ],
        }

    def analyze_document_content(self, text: str) -> Dict[str, Any]:
        """
        分析文档内容特征

        Args:
            text: 文档文本内容

        Returns:
            文档特征分析结果
        """
        if not text:
            return {
                "document_type": "unknown",
                "chinese_ratio": 0.0,
                "complexity_score": 0.0,
                "recommended_engines": ["tesseract"],
                "confidence_scores": {},
            }

        # 基础文本分析
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        english_chars = len(re.findall(r"[A-Za-z]", text))
        total_chars = len(text.replace(" ", ""))

        chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0.0
        english_ratio = english_chars / total_chars if total_chars > 0 else 0.0

        # 文档类型检测
        document_scores = {}
        for doc_type, patterns in self.document_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
            document_scores[doc_type] = score

        # 确定主要文档类型
        primary_type = (
            max(document_scores, key=document_scores.get)
            if document_scores
            else "unknown"
        )

        # 复杂度评分
        complexity_indicators = {
            "tables": len(re.findall(r"表\s*\d+|Table\s*\d+", text, re.IGNORECASE)),
            "numbers": len(re.findall(r"\d+", text)),
            "special_chars": len(re.findall(r"[^\w\s\u4e00-\u9fff]", text)),
            "line_count": len(text.split("\n")),
            "avg_line_length": sum(len(line) for line in text.split("\n"))
            / len(text.split("\n")),
        }

        complexity_score = min(
            1.0,
            sum(
                [
                    complexity_indicators["tables"] * 0.2,
                    complexity_indicators["numbers"] * 0.01,
                    complexity_indicators["special_chars"] * 0.02,
                    min(complexity_indicators["line_count"] / 50, 1.0) * 0.3,
                    min(complexity_indicators["avg_line_length"] / 100, 1.0) * 0.2,
                ]
            ),
        )

        return {
            "document_type": primary_type,
            "chinese_ratio": chinese_ratio,
            "english_ratio": english_ratio,
            "complexity_score": complexity_score,
            "document_scores": document_scores,
            "complexity_indicators": complexity_indicators,
            "total_length": total_chars,
        }

    def select_best_engine(
        self, document_analysis: dict[str, Any], available_engines: list[str]
    ) -> Dict[str, Any]:
        """
        选择最佳OCR引擎 - 优先使用PaddleOCR

        Args:
            document_analysis: 文档分析结果
            available_engines: 可用的OCR引擎列表

        Returns:
            引擎选择建议
        """
        if not available_engines:
            return {
                "primary_engine": None,
                "fallback_engine": None,
                "confidence": 0.0,
                "reasoning": "没有可用的OCR引擎",
            }

        doc_type = document_analysis.get("document_type", "unknown")
        chinese_ratio = document_analysis.get("chinese_ratio", 0.0)
        complexity_score = document_analysis.get("complexity_score", 0.0)

        # 计算每个引擎的适用性评分
        engine_scores = {}

        for engine in available_engines:
            if engine not in self.engine_capabilities:
                continue

            capabilities = self.engine_capabilities[engine]
            score = 0.0
            reasoning = []

            # PaddleOCR优先策略：给PaddleOCR额外加分
            if engine == "paddleocr":
                score += 0.15  # PaddleOCR优先加分
                reasoning.append("PaddleOCR优先策略加分")

            # 基于文档类型的评分
            if doc_type in capabilities["optimal_for"]:
                score += 0.4
                reasoning.append(f"引擎擅长处理{doc_type}")
            elif doc_type in [
                opt
                for cap in self.engine_capabilities.values()
                for opt in cap["weaknesses"]
            ]:
                score -= 0.2
                reasoning.append(f"引擎不擅长处理{doc_type}")

            # 基于中文比例的评分 - 增强PaddleOCR优势
            if chinese_ratio > 0.1:  # 降低阈值，更容易触发PaddleOCR优势
                if engine == "paddleocr":
                    score += 0.35  # 增加PaddleOCR在中文内容的优势
                    reasoning.append("中文内容比例，PaddleOCR更合适")
                elif engine == "tesseract":
                    score -= 0.15  # 增加Tesseract在中文内容的劣势
                    reasoning.append("中文内容比例，Tesseract可能不够精确")

            # 基于复杂度的评分 - 增强PaddleOCR优势
            if complexity_score > 0.4:  # 降低阈值，更容易触发PaddleOCR优势
                if engine == "paddleocr":
                    score += 0.25  # 增加PaddleOCR在复杂文档的优势
                    reasoning.append("复杂文档，PaddleOCR处理能力更强")
                elif engine == "tesseract":
                    score -= 0.15  # 增加Tesseract在复杂文档的劣势
                    reasoning.append("复杂文档，Tesseract可能处理不佳")

            # 基于预期准确率的评分
            expected_accuracy = capabilities["accuracy_estimates"].get(
                "mixed"
                if chinese_ratio > 0.1 and chinese_ratio < 0.9
                else "chinese"
                if chinese_ratio > 0.9
                else "english",
                0.8,
            )
            score += expected_accuracy * 0.3
            reasoning.append(f"预期准确率: {expected_accuracy:.0%}")

            engine_scores[engine] = {
                "score": score,
                "reasoning": reasoning,
                "expected_accuracy": expected_accuracy,
            }

        # 选择最佳引擎
        if not engine_scores:
            return {
                "primary_engine": available_engines[0] if available_engines else None,
                "fallback_engine": None,
                "confidence": 0.0,
                "reasoning": "无法评估引擎适用性，使用默认引擎",
            }

        # 按评分排序
        sorted_engines = sorted(
            engine_scores.items(), key=lambda x: x[1]["score"], reverse=True
        )

        primary_engine = sorted_engines[0][0]
        fallback_engine = sorted_engines[1][0] if len(sorted_engines) > 1 else None

        primary_score = sorted_engines[0][1]["score"]
        primary_reasoning = sorted_engines[0][1]["reasoning"]

        # 如果PaddleOCR可用且评分接近，优先选择PaddleOCR
        if "paddleocr" in available_engines and primary_engine != "paddleocr":
            paddleocr_score = engine_scores.get("paddleocr", {}).get("score", 0.0)
            if (
                abs(paddleocr_score - primary_score) < 0.1
            ):  # 如果评分差距小于0.1，选择PaddleOCR
                primary_engine = "paddleocr"
                if paddleocr_score < primary_score:
                    primary_reasoning.append("PaddleOCR优先策略：评分接近时优先选择")
                else:
                    primary_reasoning = engine_scores["paddleocr"]["reasoning"]
                primary_score = paddleocr_score

        # 计算选择置信度
        confidence = min(1.0, primary_score / len(available_engines))

        return {
            "primary_engine": primary_engine,
            "fallback_engine": fallback_engine,
            "confidence": confidence,
            "primary_score": primary_score,
            "reasoning": primary_reasoning,
            "all_engine_scores": engine_scores,
        }

    def get_processing_strategy(
        self, document_analysis: dict[str, Any], engine_selection: dict[str, Any]
    ) -> Dict[str, Any]:
        """
        获取处理策略

        Args:
            document_analysis: 文档分析结果
            engine_selection: 引擎选择结果

        Returns:
            处理策略配置
        """
        primary_engine = engine_selection.get("primary_engine")
        confidence = engine_selection.get("confidence", 0.0)
        complexity_score = document_analysis.get("complexity_score", 0.0)

        strategy = {
            "engines_to_use": [primary_engine],
            "parallel_processing": False,
            "quality_threshold": 0.8,
            "use_fallback": False,
            "processing_mode": "standard",
        }

        # 如果置信度较低，启用备用引擎
        if confidence < 0.6:
            fallback_engine = engine_selection.get("fallback_engine")
            if fallback_engine:
                strategy["engines_to_use"].append(fallback_engine)
                strategy["parallel_processing"] = True
                strategy["use_fallback"] = True
                strategy["processing_mode"] = "comparison"

        # 根据复杂度调整处理参数
        if complexity_score > 0.7:
            strategy["processing_mode"] = "high_quality"
            strategy["quality_threshold"] = 0.85
        elif complexity_score < 0.3:
            strategy["processing_mode"] = "fast"

        # 根据引擎调整参数
        if primary_engine == "paddleocr":
            strategy.update(
                {
                    "use_high_accuracy": True,
                    "preprocessing_level": "advanced",
                    "confidence_threshold": 0.7,
                }
            )
        elif primary_engine == "tesseract":
            strategy.update(
                {
                    "use_high_accuracy": False,
                    "preprocessing_level": "standard",
                    "confidence_threshold": 0.8,
                }
            )

        return strategy

    def analyze_optimization_opportunities(
        self, results: list[dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析优化机会

        Args:
            results: OCR处理结果列表

        Returns:
            优化建议
        """
        if not results:
            return {"recommendations": [], "performance_metrics": {}}

        # 统计各引擎表现
        engine_performance = {}
        for result in results:
            engine = result.get("engine_used", "unknown")
            confidence = result.get("confidence", 0.0)
            success = result.get("success", False)

            if engine not in engine_performance:
                engine_performance[engine] = {
                    "total": 0,
                    "successful": 0,
                    "avg_confidence": 0.0,
                    "confidence_scores": [],
                }

            engine_performance[engine]["total"] += 1
            if success:
                engine_performance[engine]["successful"] += 1
            engine_performance[engine]["confidence_scores"].append(confidence)

        # 计算统计数据
        for engine, stats in engine_performance.items():
            if stats["confidence_scores"]:
                stats["avg_confidence"] = sum(stats["confidence_scores"]) / len(
                    stats["confidence_scores"]
                )
                stats["success_rate"] = stats["successful"] / stats["total"]
            else:
                stats["avg_confidence"] = 0.0
                stats["success_rate"] = 0.0

        # 生成优化建议
        recommendations = []

        # 找出表现最好的引擎
        best_engine = (
            max(engine_performance.items(), key=lambda x: x[1]["avg_confidence"])
            if engine_performance
            else None
        )

        if best_engine:
            engine_name, stats = best_engine
            if stats["success_rate"] > 0.9 and stats["avg_confidence"] > 0.85:
                recommendations.append(
                    {
                        "type": "engine_optimization",
                        "priority": "high",
                        "description": f"{engine_name}引擎表现优异，建议作为首选引擎",
                        "action": f"在配置中优先使用{engine_name}",
                    }
                )

        # 检查是否需要引擎切换
        for engine, stats in engine_performance.items():
            if stats["success_rate"] < 0.7:
                recommendations.append(
                    {
                        "type": "engine_issue",
                        "priority": "medium",
                        "description": f"{engine}引擎成功率较低({stats['success_rate']:.1%})",
                        "action": f"检查{engine}配置或考虑减少使用频率",
                    }
                )

        return {
            "recommendations": recommendations,
            "performance_metrics": engine_performance,
            "total_processed": len(results),
        }


# 创建全局实例
ocr_engine_selector = OCREngineSelector()
