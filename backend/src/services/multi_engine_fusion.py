"""
多引擎融合和置信度加权系统
整合多个OCR和AI引擎的结果，通过智能算法提高整体识别准确度
"""

import asyncio
import logging
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class EngineType(str, Enum):
    """引擎类型"""

    PADDLE_OCR = "paddle_ocr"
    TESSERACT = "tesseract"
    EASY_OCR = "easy_ocr"
    PYMUPDF = "pymupdf"
    PDFPLUMBER = "pdfplumber"
    CUSTOM_NLP = "custom_nlp"
    VISION_AI = "vision_ai"


@dataclass
class EngineResult:
    """单个引擎的结果"""

    engine_type: EngineType
    text: str
    confidence: float
    bbox: tuple[int, int, int, int] | None = None
    processing_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0


@dataclass
class FusionResult:
    """融合后的结果"""

    text: str
    confidence: float
    contributing_engines: list[EngineType]
    fusion_method: str
    quality_indicators: dict[str, float]
    processing_stats: dict[str, Any]


class MultiEngineFusion:
    """多引擎融合系统"""

    def __init__(self):
        self.engine_weights = self._initialize_engine_weights()
        self.fusion_methods = self._initialize_fusion_methods()
        self.quality_thresholds = self._initialize_quality_thresholds()
        self.performance_history = defaultdict(list)

    def _initialize_engine_weights(self) -> dict[EngineType, float]:
        """初始化引擎权重"""
        return {
            EngineType.PADDLE_OCR: 0.35,  # 中文识别效果较好
            EngineType.TESSERACT: 0.25,  # 传统但稳定
            EngineType.EASY_OCR: 0.20,  # 轻量级
            EngineType.PYMUPDF: 0.15,  # PDF原生
            EngineType.PDFPLUMBER: 0.15,  # 表格提取
            EngineType.CUSTOM_NLP: 0.30,  # 自定义NLP
            EngineType.VISION_AI: 0.40,  # AI视觉
        }

    def _initialize_fusion_methods(self) -> dict[str, callable]:
        """初始化融合方法"""
        return {
            "weighted_average": self._weighted_average_fusion,
            "confidence_voting": self._confidence_voting_fusion,
            "adaptive_selection": self._adaptive_selection_fusion,
            "text_similarity": self._text_similarity_fusion,
            "semantic_consensus": self._semantic_consensus_fusion,
            "quality_weighted": self._quality_weighted_fusion,
        }

    def _initialize_quality_thresholds(self) -> dict[str, float]:
        """初始化质量阈值"""
        return {
            "min_confidence": 0.3,
            "good_confidence": 0.7,
            "excellent_confidence": 0.9,
            "min_text_length": 2,
            "max_text_length": 1000,
            "chinese_ratio_threshold": 0.5,
        }

    async def fuse_multiple_engines(
        self, engine_results: list[EngineResult], context_type: str = "general"
    ) -> FusionResult:
        """融合多个引擎的结果"""
        try:
            if not engine_results:
                return self._create_empty_fusion_result()

            # 预处理和筛选
            valid_results = self._filter_valid_results(engine_results)
            if not valid_results:
                return self._create_empty_fusion_result()

            # 根据上下文调整权重
            adjusted_weights = self._adjust_weights_for_context(
                self.engine_weights, context_type
            )

            # 选择最佳融合方法
            fusion_method = self._select_optimal_fusion_method(
                valid_results, context_type
            )

            # 执行融合
            fusion_func = self.fusion_methods[fusion_method]
            fused_result = await fusion_func(valid_results, adjusted_weights)

            # 后处理和质量评估
            enhanced_result = self._enhance_fusion_result(
                fused_result, valid_results, context_type
            )

            # 记录性能历史
            self._record_performance(enhanced_result)

            return enhanced_result

        except Exception as e:
            logger.error(f"多引擎融合失败: {e}")
            return self._create_fallback_fusion_result(engine_results)

    def _filter_valid_results(self, results: list[EngineResult]) -> list[EngineResult]:
        """筛选有效的引擎结果"""
        valid_results = []
        thresholds = self.quality_thresholds

        for result in results:
            # 置信度筛选
            if result.confidence < thresholds["min_confidence"]:
                continue

            # 文本长度筛选
            text_length = len(result.text.strip())
            if (
                text_length < thresholds["min_text_length"]
                or text_length > thresholds["max_text_length"]
            ):
                continue

            # 中文内容检查
            if self._is_chinese_context(result.text):
                chinese_ratio = self._calculate_chinese_ratio(result.text)
                if chinese_ratio < thresholds["chinese_ratio_threshold"]:
                    continue

            # 质量分数检查
            if result.quality_score < 0.3:
                continue

            valid_results.append(result)

        return valid_results

    def _adjust_weights_for_context(
        self, base_weights: dict[EngineType, float], context_type: str
    ) -> dict[EngineType, float]:
        """根据上下文调整引擎权重"""
        adjusted_weights = base_weights.copy()

        if context_type == "chinese_contract":
            # 中文合同场景调整
            adjusted_weights[EngineType.PADDLE_OCR] *= 1.3
            adjusted_weights[EngineType.CUSTOM_NLP] *= 1.2
            adjusted_weights[EngineType.TESSERACT] *= 0.8

        elif context_type == "table_extraction":
            # 表格提取场景调整
            adjusted_weights[EngineType.PDFPLUMBER] *= 1.4
            adjusted_weights[EngineType.PYMUPDF] *= 1.2
            adjusted_weights[EngineType.VISION_AI] *= 1.1

        elif context_type == "handwritten_text":
            # 手写文本场景调整
            adjusted_weights[EngineType.VISION_AI] *= 1.5
            adjusted_weights[EngineType.PADDLE_OCR] *= 1.3

        # 归一化权重
        total_weight = sum(adjusted_weights.values())
        if total_weight > 0:
            adjusted_weights = {
                k: v / total_weight for k, v in adjusted_weights.items()
            }

        return adjusted_weights

    def _select_optimal_fusion_method(
        self, results: list[EngineResult], context_type: str
    ) -> str:
        """选择最优的融合方法"""
        num_results = len(results)

        if num_results == 1:
            return "adaptive_selection"

        elif num_results == 2:
            return "weighted_average"

        elif num_results >= 3:
            # 检查结果一致性
            consistency_score = self._calculate_result_consistency(results)
            if consistency_score > 0.8:
                return "confidence_voting"
            elif consistency_score > 0.5:
                return "text_similarity"
            else:
                return "semantic_consensus"

        # 根据上下文选择特定方法
        if context_type == "chinese_contract":
            return "quality_weighted"
        else:
            return "adaptive_selection"

    async def _weighted_average_fusion(
        self, results: list[EngineResult], weights: dict[EngineType, float]
    ) -> FusionResult:
        """加权平均融合"""
        total_weight = 0.0
        weighted_confidence = 0.0
        contributing_engines = []

        best_result = max(results, key=lambda x: x.confidence)

        for result in results:
            weight = weights.get(result.engine_type, 0.1)
            total_weight += weight
            weighted_confidence += result.confidence * weight
            contributing_engines.append(result.engine_type)

        if total_weight > 0:
            final_confidence = weighted_confidence / total_weight
        else:
            final_confidence = best_result.confidence

        # 文本选择策略
        final_text = self._select_best_text_by_weight(results, weights)

        return FusionResult(
            text=final_text,
            confidence=final_confidence,
            contributing_engines=contributing_engines,
            fusion_method="weighted_average",
            quality_indicators=self._calculate_quality_indicators(results),
            processing_stats={
                "num_engines": len(results),
                "total_weight": total_weight,
                "best_engine": best_result.engine_type,
            },
        )

    async def _confidence_voting_fusion(
        self, results: list[EngineResult], weights: dict[EngineType, float]
    ) -> FusionResult:
        """置信度投票融合"""
        # 按置信度分组
        high_confidence = [r for r in results if r.confidence >= 0.8]
        medium_confidence = [r for r in results if 0.5 <= r.confidence < 0.8]
        low_confidence = [r for r in results if r.confidence < 0.5]

        # 优先选择高置信度结果
        if high_confidence:
            primary_group = high_confidence
            confidence_multiplier = 1.0
        elif medium_confidence:
            primary_group = medium_confidence
            confidence_multiplier = 0.8
        else:
            primary_group = low_confidence
            confidence_multiplier = 0.6

        # 在主组内找最一致的结果
        best_result = self._find_most_consistent_result(primary_group)

        # 调整置信度
        adjusted_confidence = best_result.confidence * confidence_multiplier

        return FusionResult(
            text=best_result.text,
            confidence=min(adjusted_confidence, 0.95),
            contributing_engines=[r.engine_type for r in primary_group],
            fusion_method="confidence_voting",
            quality_indicators=self._calculate_quality_indicators(primary_group),
            processing_stats={
                "high_conf_count": len(high_confidence),
                "medium_conf_count": len(medium_confidence),
                "low_conf_count": len(low_confidence),
                "selected_group": "high"
                if high_confidence
                else "medium"
                if medium_confidence
                else "low",
            },
        )

    async def _adaptive_selection_fusion(
        self, results: list[EngineResult], weights: dict[EngineType, float]
    ) -> FusionResult:
        """自适应选择融合"""
        # 计算每个引擎的综合得分
        engine_scores = []
        for result in results:
            weight = weights.get(result.engine_type, 0.1)
            quality_factor = result.quality_score
            time_factor = 1.0 / (1.0 + result.processing_time)  # 处理时间越短越好

            综合得分 = result.confidence * weight * quality_factor * time_factor
            engine_scores.append((result, 综合得分))

        # 选择得分最高的结果
        best_result, best_score = max(engine_scores, key=lambda x: x[1])

        return FusionResult(
            text=best_result.text,
            confidence=min(best_result.confidence * 1.1, 0.98),  # 略微提升置信度
            contributing_engines=[best_result.engine_type],
            fusion_method="adaptive_selection",
            quality_indicators=self._calculate_quality_indicators([best_result]),
            processing_stats={
                "best_score": best_score,
                "engine_count": len(results),
                "selection_confidence": best_score
                / max(score for _, score in engine_scores)
                if engine_scores
                else 1.0,
            },
        )

    async def _text_similarity_fusion(
        self, results: list[EngineResult], weights: dict[EngineType, float]
    ) -> FusionResult:
        """文本相似度融合"""
        # 计算文本相似度矩阵
        similarity_matrix = self._calculate_similarity_matrix(results)

        # 找到最相似的文本簇
        text_clusters = self._find_text_clusters(results, similarity_matrix)

        # 选择最大的簇
        best_cluster = max(text_clusters, key=len) if text_clusters else [results[0]]

        # 在簇内选择最佳结果
        cluster_best = max(best_cluster, key=lambda x: x.confidence)

        # 计算簇的一致性得分
        consistency_score = self._calculate_cluster_consistency(
            best_cluster, similarity_matrix
        )

        return FusionResult(
            text=cluster_best.text,
            confidence=cluster_best.confidence * consistency_score,
            contributing_engines=[r.engine_type for r in best_cluster],
            fusion_method="text_similarity",
            quality_indicators={
                "consistency_score": consistency_score,
                "cluster_size": len(best_cluster),
                "total_clusters": len(text_clusters),
            },
            processing_stats={
                "cluster_size": len(best_cluster),
                "similarity_threshold": 0.7,
            },
        )

    async def _semantic_consensus_fusion(
        self, results: list[EngineResult], weights: dict[EngineType, float]
    ) -> FusionResult:
        """语义共识融合"""
        # 提取语义特征
        semantic_features = []
        for result in results:
            features = self._extract_semantic_features(result.text)
            semantic_features.append((result, features))

        # 计算语义相似度
        semantic_similarity = self._calculate_semantic_similarity(semantic_features)

        # 找到语义共识
        consensus_results = self._find_semantic_consensus(
            semantic_features, semantic_similarity
        )

        if consensus_results:
            # 计算共识强度
            consensus_strength = len(consensus_results) / len(results)
            best_consensus = max(consensus_results, key=lambda x: x.confidence)

            final_confidence = best_consensus.confidence * (
                0.7 + 0.3 * consensus_strength
            )
        else:
            # 没有共识，选择置信度最高的
            best_consensus = max(results, key=lambda x: x.confidence)
            consensus_strength = 0.3
            final_confidence = best_consensus.confidence * 0.7

        return FusionResult(
            text=best_consensus.text,
            confidence=min(final_confidence, 0.95),
            contributing_engines=[
                r.engine_type
                for r in (consensus_results if consensus_results else [best_consensus])
            ],
            fusion_method="semantic_consensus",
            quality_indicators={
                "consensus_strength": consensus_strength,
                "semantic_similarity": semantic_similarity,
            },
            processing_stats={
                "has_consensus": bool(consensus_results),
                "consensus_size": len(consensus_results) if consensus_results else 0,
            },
        )

    async def _quality_weighted_fusion(
        self, results: list[EngineResult], weights: dict[EngineType, float]
    ) -> FusionResult:
        """质量加权融合"""
        # 计算综合质量分数
        quality_scores = []
        for result in results:
            # 基础置信度
            base_score = result.confidence

            # 质量分数
            quality_factor = result.quality_score

            # 引擎权重
            engine_weight = weights.get(result.engine_type, 0.1)

            # 中文适配度
            chinese_factor = self._calculate_chinese_suitability(result.text)

            # 长度适配度
            length_factor = self._calculate_length_suitability(result.text)

            # 综合质量分数
            total_quality = (
                base_score
                * quality_factor
                * engine_weight
                * chinese_factor
                * length_factor
            )
            quality_scores.append((result, total_quality))

        # 选择质量分数最高的结果
        best_result, best_quality = max(quality_scores, key=lambda x: x[1])

        return FusionResult(
            text=best_result.text,
            confidence=min(best_result.confidence * best_quality, 0.98),
            contributing_engines=[best_result.engine_type],
            fusion_method="quality_weighted",
            quality_indicators=self._calculate_quality_indicators([best_result]),
            processing_stats={
                "total_quality_score": best_quality,
                "chinese_factor": self._calculate_chinese_suitability(best_result.text),
                "length_factor": self._calculate_length_suitability(best_result.text),
            },
        )

    def _calculate_quality_indicators(
        self, results: list[EngineResult]
    ) -> dict[str, float]:
        """计算质量指标"""
        if not results:
            return {}

        confidences = [r.confidence for r in results]
        quality_scores = [r.quality_score for r in results]
        processing_times = [r.processing_time for r in results]

        return {
            "avg_confidence": statistics.mean(confidences),
            "max_confidence": max(confidences),
            "min_confidence": min(confidences),
            "confidence_std": statistics.stdev(confidences)
            if len(confidences) > 1
            else 0.0,
            "avg_quality": statistics.mean(quality_scores),
            "avg_processing_time": statistics.mean(processing_times),
            "engine_diversity": len(set(r.engine_type for r in results)),
            "consistency_score": self._calculate_result_consistency(results),
        }

    def _calculate_result_consistency(self, results: list[EngineResult]) -> float:
        """计算结果一致性"""
        if len(results) <= 1:
            return 1.0

        # 计算文本相似度
        similarities = []
        for i, result1 in enumerate(results):
            for result2 in results[i + 1 :]:
                similarity = self._calculate_text_similarity(result1.text, result2.text)
                similarities.append(similarity)

        return statistics.mean(similarities) if similarities else 0.0

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        try:
            # 使用编辑距离计算相似度
            from difflib import SequenceMatcher

            return SequenceMatcher(None, text1, text2).ratio()
        except Exception:
            # 简单的字符重叠度
            set1, set2 = set(text1), set(text2)
            intersection = len(set1 & set2)
            union = len(set1 | set2)
            return intersection / union if union > 0 else 0.0

    def _calculate_similarity_matrix(self, results: list[EngineResult]) -> np.ndarray:
        """计算相似度矩阵"""
        n = len(results)
        matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(i, n):
                similarity = self._calculate_text_similarity(
                    results[i].text, results[j].text
                )
                matrix[i][j] = matrix[j][i] = similarity

        return matrix

    def _find_text_clusters(
        self,
        results: list[EngineResult],
        similarity_matrix: np.ndarray,
        threshold: float = 0.7,
    ) -> list[list[EngineResult]]:
        """找到文本簇"""
        n = len(results)
        visited = [False] * n
        clusters = []

        for i in range(n):
            if not visited[i]:
                cluster = [results[i]]
                visited[i] = True

                for j in range(n):
                    if not visited[j] and similarity_matrix[i][j] >= threshold:
                        cluster.append(results[j])
                        visited[j] = True

                clusters.append(cluster)

        return clusters

    def _extract_semantic_features(self, text: str) -> dict[str, Any]:
        """提取语义特征"""
        features = {
            "length": len(text),
            "word_count": len(text.split()),
            "has_numbers": bool(re.search(r"\d", text)),
            "has_chinese": bool(re.search(r"[\u4e00-\u9fff]", text)),
            "has_english": bool(re.search(r"[a-zA-Z]", text)),
            "has_special_chars": bool(re.search(r"[^\w\s\u4e00-\u9fff]", text)),
            "numeric_ratio": len(re.findall(r"\d", text)) / max(len(text), 1),
            "chinese_ratio": len(re.findall(r"[\u4e00-\u9fff]", text))
            / max(len(text), 1),
        }

        # 合同相关特征
        contract_keywords = ["租赁", "甲方", "乙方", "租金", "期限", "地址", "日期"]
        features["contract_relevance"] = sum(
            1 for keyword in contract_keywords if keyword in text
        ) / len(contract_keywords)

        return features

    def _calculate_semantic_similarity(
        self, semantic_features: list[tuple[EngineResult, dict[str, Any]]]
    ) -> float:
        """计算语义相似度"""
        if len(semantic_features) <= 1:
            return 1.0

        similarities = []
        for i, (result1, features1) in enumerate(semantic_features):
            for result2, features2 in semantic_features[i + 1 :]:
                similarity = self._compare_semantic_features(features1, features2)
                similarities.append(similarity)

        return statistics.mean(similarities) if similarities else 0.0

    def _compare_semantic_features(self, features1: dict, features2: dict) -> float:
        """比较语义特征"""
        similarity = 0.0
        count = 0

        comparable_features = [
            "length",
            "word_count",
            "has_numbers",
            "has_chinese",
            "has_english",
            "numeric_ratio",
            "chinese_ratio",
            "contract_relevance",
        ]

        for feature in comparable_features:
            if feature in features1 and feature in features2:
                val1, val2 = features1[feature], features2[feature]
                if isinstance(val1, bool) and isinstance(val2, bool):
                    similarity += 1.0 if val1 == val2 else 0.0
                elif isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    max_val = max(val1, val2)
                    similarity += min(val1, val2) / max_val if max_val > 0 else 1.0
                count += 1

        return similarity / count if count > 0 else 0.0

    def _find_semantic_consensus(
        self,
        semantic_features: list[tuple[EngineResult, dict[str, Any]]],
        semantic_similarity: float,
    ) -> list[EngineResult]:
        """找到语义共识"""
        if semantic_similarity < 0.5:
            return []

        # 基于语义特征分组
        groups = defaultdict(list)
        for result, features in semantic_features:
            # 创建特征签名
            signature = self._create_feature_signature(features)
            groups[signature].append(result)

        # 找到最大的组
        if groups:
            largest_group = max(groups.values(), key=len)
            if len(largest_group) >= len(semantic_features) * 0.5:
                return largest_group

        return []

    def _create_feature_signature(self, features: dict[str, Any]) -> str:
        """创建特征签名"""
        key_features = ["has_chinese", "has_numbers", "contract_relevance"]
        signature_parts = []

        for feature in key_features:
            if feature in features:
                value = features[feature]
                if isinstance(value, bool):
                    signature_parts.append(f"{feature}:{int(value)}")
                elif isinstance(value, (int, float)):
                    signature_parts.append(f"{feature}:{value:.2f}")

        return "|".join(signature_parts)

    def _select_best_text_by_weight(
        self, results: list[EngineResult], weights: dict[EngineType, float]
    ) -> str:
        """根据权重选择最佳文本"""
        best_score = -1
        best_text = ""

        for result in results:
            weight = weights.get(result.engine_type, 0.1)
            score = result.confidence * weight

            if score > best_score:
                best_score = score
                best_text = result.text

        return best_text

    def _find_most_consistent_result(self, results: list[EngineResult]) -> EngineResult:
        """找到最一致的结果"""
        if len(results) <= 1:
            return results[0] if results else None

        # 计算每个结果与其他结果的相似度
        consistency_scores = []
        for i, result in enumerate(results):
            similarities = []
            for j, other_result in enumerate(results):
                if i != j:
                    similarity = self._calculate_text_similarity(
                        result.text, other_result.text
                    )
                    similarities.append(similarity)

            avg_similarity = statistics.mean(similarities) if similarities else 0.0
            consistency_scores.append((result, avg_similarity))

        # 返回最一致的结果
        return max(consistency_scores, key=lambda x: x[1])[0]

    def _calculate_cluster_consistency(
        self, cluster: list[EngineResult], similarity_matrix: np.ndarray
    ) -> float:
        """计算簇的一致性"""
        if len(cluster) <= 1:
            return 1.0

        # 获取簇内相似度
        cluster_similarities = []
        for i, result1 in enumerate(cluster):
            for j, result2 in enumerate(cluster[i + 1 :], i + 1):
                # 找到在矩阵中的位置（这里需要更复杂的索引映射）
                similarity = self._calculate_text_similarity(result1.text, result2.text)
                cluster_similarities.append(similarity)

        return statistics.mean(cluster_similarities) if cluster_similarities else 0.0

    def _calculate_chinese_suitability(self, text: str) -> float:
        """计算中文适配度"""
        chinese_ratio = self._calculate_chinese_ratio(text)

        # 中文内容适应性
        if chinese_ratio > 0.8:
            return 1.2
        elif chinese_ratio > 0.5:
            return 1.0
        elif chinese_ratio > 0.2:
            return 0.8
        else:
            return 0.6

    def _calculate_length_suitability(self, text: str) -> float:
        """计算长度适配度"""
        length = len(text.strip())

        # 理想长度范围
        if 5 <= length <= 100:
            return 1.0
        elif 2 <= length <= 200:
            return 0.9
        elif length < 2:
            return 0.5
        else:
            return 0.7

    def _is_chinese_context(self, text: str) -> bool:
        """判断是否为中文上下文"""
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        total_chars = len(text.strip())
        return chinese_chars / max(total_chars, 1) > 0.3

    def _calculate_chinese_ratio(self, text: str) -> float:
        """计算中文字符比例"""
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        total_chars = len(re.sub(r"\s", "", text))
        return chinese_chars / max(total_chars, 1)

    def _enhance_fusion_result(
        self,
        fusion_result: FusionResult,
        original_results: list[EngineResult],
        context_type: str,
    ) -> FusionResult:
        """增强融合结果"""
        # 应用上下文特定的增强
        enhanced_confidence = fusion_result.confidence

        if context_type == "chinese_contract":
            # 中文合同特定增强
            if self._contains_contract_keywords(fusion_result.text):
                enhanced_confidence *= 1.1
            if self._has_good_chinese_structure(fusion_result.text):
                enhanced_confidence *= 1.05

        # 确保置信度在合理范围内
        enhanced_confidence = max(0.1, min(enhanced_confidence, 0.99))

        fusion_result.confidence = enhanced_confidence
        return fusion_result

    def _contains_contract_keywords(self, text: str) -> bool:
        """检查是否包含合同关键词"""
        contract_keywords = ["租赁", "租金", "甲方", "乙方", "房屋", "地址", "期限"]
        return any(keyword in text for keyword in contract_keywords)

    def _has_good_chinese_structure(self, text: str) -> bool:
        """检查是否有良好的中文结构"""
        # 简单的中文结构检查
        has_chinese = bool(re.search(r"[\u4e00-\u9fff]", text))
        reasonable_length = 2 <= len(text.strip()) <= 200
        not_too_special = (
            len(re.findall(r"[^\w\s\u4e00-\u9fff]", text)) <= len(text) * 0.2
        )

        return has_chinese and reasonable_length and not_too_special

    def _record_performance(self, fusion_result: FusionResult):
        """记录性能历史"""
        timestamp = asyncio.get_event_loop().time()
        performance_data = {
            "timestamp": timestamp,
            "fusion_method": fusion_result.fusion_method,
            "confidence": fusion_result.confidence,
            "num_engines": len(fusion_result.contributing_engines),
            "quality_indicators": fusion_result.quality_indicators,
        }

        self.performance_history[fusion_result.fusion_method].append(performance_data)

        # 保持历史记录在合理大小
        if len(self.performance_history[fusion_result.fusion_method]) > 100:
            self.performance_history[fusion_result.fusion_method] = (
                self.performance_history[fusion_result.fusion_method][-50:]
            )

    def _create_empty_fusion_result(self) -> FusionResult:
        """创建空的融合结果"""
        return FusionResult(
            text="",
            confidence=0.0,
            contributing_engines=[],
            fusion_method="empty",
            quality_indicators={},
            processing_stats={"error": "no_valid_results"},
        )

    def _create_fallback_fusion_result(
        self, results: list[EngineResult]
    ) -> FusionResult:
        """创建后备融合结果"""
        if results:
            best_result = max(results, key=lambda x: x.confidence)
            return FusionResult(
                text=best_result.text,
                confidence=best_result.confidence * 0.7,  # 降低置信度
                contributing_engines=[best_result.engine_type],
                fusion_method="fallback",
                quality_indicators={"fallback_used": True},
                processing_stats={"original_engines": len(results)},
            )
        else:
            return self._create_empty_fusion_result()

    def get_performance_statistics(self) -> dict[str, Any]:
        """获取性能统计信息"""
        stats = {}

        for method, history in self.performance_history.items():
            if history:
                confidences = [h["confidence"] for h in history]
                stats[method] = {
                    "usage_count": len(history),
                    "avg_confidence": statistics.mean(confidences),
                    "max_confidence": max(confidences),
                    "min_confidence": min(confidences),
                    "recent_performance": confidences[-10:]
                    if len(confidences) >= 10
                    else confidences,
                }

        return stats

    def update_engine_weights(self, new_weights: dict[EngineType, float]):
        """更新引擎权重"""
        # 验证权重
        total_weight = sum(new_weights.values())
        if total_weight <= 0:
            raise ValueError("权重总和必须大于0")

        # 归一化权重
        normalized_weights = {k: v / total_weight for k, v in new_weights.items()}

        self.engine_weights.update(normalized_weights)
        logger.info(f"引擎权重已更新: {normalized_weights}")

    def fuse_results(self, mock_engine_results: list[dict[str, Any]]) -> dict[str, Any]:
        """
        兼容性方法：融合简单格式的引擎结果
        用于兼容测试和简化调用
        """
        try:
            if not mock_engine_results:
                return {
                    "text": "",
                    "confidence": 0.0,
                    "fusion_method": "empty",
                    "contributing_engines": [],
                }

            # 转换为EngineResult格式
            engine_results = []
            for mock_result in mock_engine_results:
                if isinstance(mock_result, dict):
                    engine_type = mock_result.get("engine", "unknown")
                    text = mock_result.get("text", "")
                    confidence = mock_result.get("confidence", 0.0)

                    # 转换engine_type字符串为EngineType枚举
                    try:
                        if engine_type == "paddleocr":
                            engine_enum = EngineType.PADDLE_OCR
                        elif engine_type == "tesseract":
                            engine_enum = EngineType.TESSERACT
                        elif engine_type == "easy_ocr":
                            engine_enum = EngineType.EASY_OCR
                        elif engine_type == "pymupdf":
                            engine_enum = EngineType.PYMUPDF
                        elif engine_type == "pdfplumber":
                            engine_enum = EngineType.PDFPLUMBER
                        else:
                            engine_enum = EngineType.CUSTOM_NLP
                    except:
                        engine_enum = EngineType.CUSTOM_NLP

                    engine_result = EngineResult(
                        engine_type=engine_enum,
                        text=text,
                        confidence=confidence,
                        processing_time=0.0,
                    )
                    engine_results.append(engine_result)

            if not engine_results:
                return {
                    "text": "",
                    "confidence": 0.0,
                    "fusion_method": "empty",
                    "contributing_engines": [],
                }

            # 简单融合逻辑：选择置信度最高的结果
            best_result = max(engine_results, key=lambda x: x.confidence)

            return {
                "text": best_result.text,
                "confidence": best_result.confidence,
                "fusion_method": "confidence_selection",
                "contributing_engines": [
                    engine.engine_type.value for engine in engine_results
                ],
                "processing_stats": {
                    "total_engines": len(engine_results),
                    "best_engine": best_result.engine_type.value,
                    "avg_confidence": sum(r.confidence for r in engine_results)
                    / len(engine_results),
                },
            }

        except Exception as e:
            logger.error(f"结果融合失败: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "fusion_method": "error",
                "error": str(e),
                "contributing_engines": [],
            }


# 创建全局实例（安全导入）
try:
    multi_engine_fusion = MultiEngineFusion()
    logger.info("多引擎融合服务初始化成功")
except Exception as e:
    logger.error(f"多引擎融合服务初始化失败: {e}")
    multi_engine_fusion = None
