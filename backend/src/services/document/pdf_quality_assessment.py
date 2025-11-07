from typing import Any

"""
PDF处理质量评估服务
提供智能化的PDF处理质量评估和改进建议
"""

import logging
import re
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class PDFProcessingQualityAssessment:
    """PDF处理质量评估器"""

    def __init__(self):
        """初始化质量评估器"""
        self.quality_weights = {
            "text_completeness": 0.25,  # 文本完整性权重
            "field_extraction_rate": 0.30,  # 字段提取率权重
            "confidence_score": 0.20,  # 置信度权重
            "ocr_accuracy": 0.15,  # OCR准确度权重
            "structural_integrity": 0.10,  # 结构完整性权重
        }

        # 58个关键字段的预期模式
        self.expected_fields = {
            "contract_number": r"合同编号|合同号|协议编号|编号",
            "property_address": r"物业地址|房屋地址|地址|位置",
            "property_area": r"面积|建筑面积|租赁面积|平方米",
            "rent_amount": r"租金|月租金|租金金额|费用",
            "rent_period": r"租赁期限|租期|期限|个月",
            "party_a": r"甲方|出租方|业主|委托方",
            "party_b": r"乙方|承租方|租户|使用方",
            "start_date": r"起始日期|开始日期|生效日期|租赁开始",
            "end_date": r"终止日期|结束日期|到期日期|租赁结束",
            "payment_method": r"支付方式|付款方式|缴纳方式",
            "deposit": r"保证金|押金|履约保证金",
            "usage_purpose": r"用途|使用范围|经营用途",
            "property_type": r"物业类型|房屋类型|建筑类型",
            "ownership_certificate": r"房产证|不动产权证|产权证",
            "contact_info": r"联系电话|电话|联系方式",
            "legal_representative": r"法定代表人|法人代表|负责人",
            "registration_number": r"统一社会信用代码|注册号|营业执照",
            "management_fee": r"管理费|物业费|服务费",
            "water_electric": r"水电费|水费|电费",
            "renovation": r"装修|装饰|改建",
            "sublease": r"转租|分租|转让",
            "insurance": r"保险|保险责任|保险费用",
            "termination_conditions": r"解除条件|终止条件|违约责任",
            "renewal_terms": r"续租|续期| renewal",
        }

        # 质量等级定义
        self.quality_levels = {
            "excellent": {"min_score": 0.90, "description": "优秀", "color": "#52c41a"},
            "good": {"min_score": 0.75, "description": "良好", "color": "#1890ff"},
            "fair": {"min_score": 0.60, "description": "一般", "color": "#faad14"},
            "poor": {"min_score": 0.40, "description": "较差", "color": "#fa541c"},
            "very_poor": {"min_score": 0.0, "description": "很差", "color": "#ff4d4f"},
        }

    def assess_processing_quality(
        self,
        extracted_data: dict[str, Any],
        original_text: str,
        processing_metadata: dict[str, Any],
        ocr_results: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        评估PDF处理质量

        Args:
            extracted_data: 提取的结构化数据
            original_text: 原始文本内容
            processing_metadata: 处理元数�?
            ocr_results: OCR处理结果（可选）

        Returns:
            质量评估报告
        """
        logger.info(f"开始评估PDF处理质量，提取字段数: {len(extracted_data)}")

        assessment_start = datetime.now(UTC)

        # 计算各项质量指标
        text_completeness = self._assess_text_completeness(
            original_text, processing_metadata
        )
        field_extraction_rate = self._assess_field_extraction_rate(extracted_data)
        confidence_score = self._assess_confidence_score(
            extracted_data, processing_metadata
        )
        ocr_accuracy = self._assess_ocr_accuracy(original_text, ocr_results)
        structural_integrity = self._assess_structural_integrity(
            extracted_data, original_text
        )

        # 计算综合质量分数
        quality_score = (
            text_completeness * self.quality_weights["text_completeness"]
            + field_extraction_rate * self.quality_weights["field_extraction_rate"]
            + confidence_score * self.quality_weights["confidence_score"]
            + ocr_accuracy * self.quality_weights["ocr_accuracy"]
            + structural_integrity * self.quality_weights["structural_integrity"]
        )

        # 确定质量等级
        quality_level = self._determine_quality_level(quality_score)

        # 生成改进建议
        improvement_suggestions = self._generate_improvement_suggestions(
            {
                "text_completeness": text_completeness,
                "field_extraction_rate": field_extraction_rate,
                "confidence_score": confidence_score,
                "ocr_accuracy": ocr_accuracy,
                "structural_integrity": structural_integrity,
                "extracted_fields_count": len(extracted_data),
                "original_text_length": len(original_text),
            }
        )

        # 构建评估报告
        assessment_report = {
            "overall_quality_score": round(quality_score, 3),
            "quality_level": quality_level,
            "assessment_timestamp": assessment_start.isoformat(),
            "processing_time_seconds": processing_metadata.get(
                "processing_time_seconds", 0
            ),
            "detailed_scores": {
                "text_completeness": round(text_completeness, 3),
                "field_extraction_rate": round(field_extraction_rate, 3),
                "confidence_score": round(confidence_score, 3),
                "ocr_accuracy": round(ocr_accuracy, 3),
                "structural_integrity": round(structural_integrity, 3),
            },
            "field_analysis": {
                "total_expected_fields": len(self.expected_fields),
                "extracted_fields_count": len(extracted_data),
                "extraction_rate_percentage": round(field_extraction_rate * 100, 1),
                "missing_critical_fields": self._identify_missing_critical_fields(
                    extracted_data
                ),
                "extracted_field_names": list(extracted_data.keys()),
            },
            "text_analysis": {
                "original_text_length": len(original_text),
                "clean_text_length": len(self._clean_text(original_text)),
                "text_quality_issues": self._identify_text_quality_issues(
                    original_text
                ),
            },
            "improvement_suggestions": improvement_suggestions,
            "quality_weights": self.quality_weights,
            "recommendations": self._generate_processing_recommendations(
                extracted_data, processing_metadata
            ),
        }

        processing_time = (datetime.now(UTC) - assessment_start).total_seconds()
        logger.info(
            f"PDF处理质量评估完成，耗时: {processing_time:.3f}秒，质量分数: {quality_score:.3f}"
        )

        return assessment_report

    def _assess_text_completeness(
        self, original_text: str, processing_metadata: dict[str, Any]
    ) -> float:
        """评估文本完整性
        
        Args:
            original_text: 原始文本内容
            processing_metadata: 处理元数据
            
        Returns:
            文本完整性分数 (0-1)
        """
        if not original_text or len(original_text.strip()) == 0:
            return 0.0

        # 基础文本长度评估
        text_length = len(original_text.strip())

        # 期望的最小文本长度（基于合同类型）
        min_expected_length = 500  # 最少500字符
        optimal_length = 5000  # 最优5000字符

        # 长度评分
        if text_length < min_expected_length:
            length_score = text_length / min_expected_length * 0.5
        elif text_length > optimal_length:
            length_score = 1.0
        else:
            length_score = 0.5 + (text_length - min_expected_length) / (optimal_length - min_expected_length) * 0.5

        # 文本清洁度评估
        clean_text = re.sub(r'\s+', ' ', re.sub(r'[^\w\s\u4e00-\u9fff]', '', original_text))
        cleanliness_score = len(clean_text) / max(len(original_text), 1)

        # OCR引擎和页面数量评估
        engine_used = processing_metadata.get("ocr_engine", "unknown")
        page_count = processing_metadata.get("page_count", 1)
        
        # 引擎可靠性因子
        engine_reliability = {
            "tesseract": 0.85,
            "paddleocr": 0.90,
            "easyocr": 0.80,
            "chineseocr": 0.88,
            "unknown": 0.70
        }.get(engine_used.lower(), 0.70)
        
        # 页面数量因子（假设3页为基准）
        page_factor = min(1.0, page_count / 3)  # 假设3页为基准

        # 综合文本完整性分数
        completeness_score = (
            length_score * 0.4
            + cleanliness_score * 0.3
            + engine_reliability * 0.2
            + page_factor * 0.1
        )

        return min(1.0, completeness_score)

    def _assess_field_extraction_rate(self, extracted_data: dict) -> float:
        """评估字段提取率
        
        Args:
            extracted_data: 提取的结构化数据
            
        Returns:
            字段提取率分数 (0-1)
        """
        if not extracted_data:
            return 0.0

        extracted_fields = set(extracted_data.keys())
        expected_field_patterns = set(self.expected_fields.keys())

        # 计算直接匹配的字段数
        directly_matched = 0
        for field in extracted_fields:
            if field in expected_field_patterns:
                directly_matched += 1

        # 计算基于内容模式匹配的字段数
        pattern_matched = 0
        for field_name, patterns in self.expected_fields.items():
            if field_name not in extracted_data:
                # 检查是否可以通过模式匹配找到
                for key, value in extracted_data.items():
                    if re.search(patterns, str(key), re.IGNORECASE):
                        pattern_matched += 1
                        break

        # 计算提取率
        total_expected = len(expected_field_patterns)
        total_matched = directly_matched + pattern_matched
        extraction_rate = total_matched / total_expected if total_expected > 0 else 0.0

        return min(1.0, extraction_rate)

    def _assess_confidence_score(self, extracted_data: dict, processing_metadata: dict) -> float:
        """评估置信度分数
        
        Args:
            extracted_data: 提取的结构化数据
            processing_metadata: 处理元数据
            
        Returns:
            置信度分数 (0-1)
        """
        if not extracted_data:
            return 0.0

        # 从提取数据中获取置信度
        confidence_scores = []

        # 从字段值中提取置信度（如果字段值是对象）
        for field_name, field_value in extracted_data.items():
            if hasattr(field_value, "confidence"):
                confidence_scores.append(getattr(field_value, "confidence"))

        # 如果字段中没有置信度，使用元数据中的总体置信度
        if not confidence_scores:
            overall_confidence = processing_metadata.get("overall_confidence", 0.0)
            confidence_scores.append(overall_confidence)

        # 如果仍然没有置信度，基于字段数量和质量进行估计
        if not confidence_scores:
            field_count = len(extracted_data)
            estimated_confidence = min(0.8, field_count / 20)  # 假设20个字段为最优
            confidence_scores.append(estimated_confidence)

        # 计算平均置信度
        average_confidence = sum(confidence_scores) / len(confidence_scores)

        # 根据处理引擎调整置信度
        processing_engine = processing_metadata.get("processing_engine", "unknown")
        engine_adjustment = {
            "enhanced_ml": 1.1,
            "standard": 1.0,
            "basic": 0.9,
            "fallback": 0.8,
        }.get(processing_engine.lower(), 1.0)

        final_confidence = average_confidence * engine_adjustment
        return min(1.0, final_confidence)

    def _assess_ocr_accuracy(self, original_text: str, ocr_results: dict) -> float:
        """评估OCR准确度
        
        Args:
            original_text: 原始文本内容
            ocr_results: OCR处理结果
            
        Returns:
            OCR准确度分数 (0-1)
        """
        if not ocr_results:
            # 如果没有OCR结果，基于文本质量进行评估
            return self._assess_text_quality(original_text)

        # 从OCR结果中获取准确度指标
        ocr_confidence = ocr_results.get("confidence", 0.0)
        if ocr_confidence > 0:
            return min(1.0, ocr_confidence)

        # 基于OCR引擎类型估算准确度
        ocr_engine = ocr_results.get("engine", "unknown")
        engine_accuracy = {
            "paddleocr": 0.92,
            "tesseract": 0.85,
            "easyocr": 0.88,
            "chineseocr": 0.90,
            "unknown": 0.75,
        }.get(ocr_engine.lower(), 0.75)

        # 基于文本特征调整准确度
        text_quality_factor = self._assess_text_quality(original_text)

        final_accuracy = engine_accuracy * text_quality_factor
        return min(1.0, final_accuracy)

    def _assess_structural_integrity(self, extracted_data: dict) -> float:
        """评估结构完整性
        
        Args:
            extracted_data: 提取的结构化数据
            
        Returns:
            结构完整性分数 (0-1)
        """
        if not extracted_data:
            return 0.0

        # 检查关键字段的完整性
        critical_fields = [
            "contract_number",
            "party_a",
            "party_b",
            "property_address",
            "start_date",
            "end_date",
            "rent_amount",
        ]

        present_critical_fields = sum(
            1 for field in critical_fields if field in extracted_data and extracted_data[field]
        )
        critical_field_ratio = present_critical_fields / len(critical_fields)

        # 检查数据类型一致性
        type_consistency_score = 0.0
        typed_fields = 0
        for field_name, field_value in extracted_data.items():
            if field_value is not None and str(field_value).strip():
                typed_fields += 1
                # 基于字段名和值类型评估一致性
                if "date" in field_name.lower():
                    # 日期字段应该包含日期格式
                    if re.search(r"\d{4}[年\-\/]\d{1,2}[月\-\/]\d{1,2}", str(field_value)):
                        type_consistency_score += 1.0
                    else:
                        type_consistency_score += 0.3
                elif "amount" in field_name.lower() or "rent" in field_name.lower():
                    # 金额字段应该包含数字
                    if re.search(r"\d+", str(field_value)):
                        type_consistency_score += 1.0
                    else:
                        type_consistency_score += 0.2
                else:
                    type_consistency_score += 0.8  # 其他字段给部分分数

        type_consistency_score = type_consistency_score / max(typed_fields, 1)

        # 检查逻辑一致性
        logic_consistency_score = self._assess_logic_consistency(extracted_data)

        # 综合结构完整性分数
        structural_score = (
            critical_field_ratio * 0.4
            + type_consistency_score * 0.3
            + logic_consistency_score * 0.3
        )

        return min(1.0, structural_score)

    def _assess_text_quality(self, text: str) -> float:
        """评估文本质量
        
        Args:
            text: 文本内容
            
        Returns:
            文本质量分数 (0-1)
        """
        if not text or len(text.strip()) == 0:
            return 0.0

        quality_score = 1.0

        # 检查乱码比例
        garbled_chars = len(re.findall(r"[��□▪▫]", text))
        garbled_ratio = garbled_chars / len(text)
        quality_score -= garbled_ratio * 2  # 乱码严重扣分

        # 检查特殊字符比例
        special_chars = len(
            re.findall(r'[^\w\s\u4e00-\u9fff，。；：！？?（）【】"]', text)
        )
        special_ratio = special_chars / len(text)
        if special_ratio > 0.1:  # 特殊字符超过10%开始扣分
            quality_score -= (special_ratio - 0.1) * 1.5

        # 检查中文字符比例
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        chinese_ratio = chinese_chars / len(text)
        if chinese_ratio < 0.3:  # 中文字符应该占一定比例
            quality_score -= (0.3 - chinese_ratio) * 0.3

        # 检查数字和字母的合理分布
        alphanumeric_chars = len(re.findall(r"[a-zA-Z0-9]", text))
        alphanumeric_ratio = alphanumeric_chars / len(text)
        if alphanumeric_ratio > 0.6:  # 数字和字母过多可能有问题
            quality_score -= (alphanumeric_ratio - 0.6) * 0.5

        return max(0.0, quality_score)

    def _clean_text(self, text: str) -> str:
        """清理文本
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""

        # 移除多余的空白字符
        cleaned = re.sub(r"\s+", " ", text.strip())

        # 移除乱码字符
        cleaned = re.sub(r"[��□▪▫]", "", cleaned)

        # 标准化标点符号
        cleaned = re.sub(r'["""]', '"', cleaned)
        cleaned = re.sub(r"'{2,}", "'", cleaned)

        return cleaned.strip()

    def _determine_quality_level(self, score: float) -> dict[str, Any]:
        """确定质量等级"""
        for level_name, level_info in reversed(self.quality_levels.items()):
            if score >= level_info["min_score"]:
                return {
                    "level": level_name,
                    "description": level_info["description"],
                    "color": level_info["color"],
                }

        return self.quality_levels["very_poor"]

    def _identify_missing_critical_fields(
        self, extracted_data: dict[str, Any]
    ) -> list[str]:
        """识别缺失的关键字段"""
        critical_fields = [
            "contract_number",
            "property_address",
            "rent_amount",
            "party_a",
            "party_b",
            "start_date",
            "end_date",
        ]

        missing_fields = [
            field
            for field in critical_fields
            if field not in extracted_data or not extracted_data[field]
        ]

        return missing_fields

    def _identify_text_quality_issues(self, text: str) -> list[str]:
        """识别文本质量问题"""
        issues = []

        if len(text) < 200:
            issues.append("文本过短，可能存在提取不完整")

        garbled_ratio = len(re.findall(r"[��□▪▫]", text)) / len(text) if text else 0
        if garbled_ratio > 0.01:
            issues.append("检测到乱码字符，可能存在OCR识别错误")

        chinese_ratio = (
            len(re.findall(r"[\u4e00-\u9fff]", text)) / len(text) if text else 0
        )
        if chinese_ratio < 0.2:
            issues.append("中文字符比例较低，可能影响字段识别")

        if not re.search(r"\d{4}", text):
            issues.append("未检测到年份信息，可能影响日期字段提取")

        return issues

    def _generate_improvement_suggestions(
        self, quality_metrics: dict[str, float]
    ) -> list[dict[str, Any]]:
        """生成改进建议"""
        suggestions = []

        # 基于各项指标的改进建议
        if quality_metrics["text_completeness"] < 0.8:
            suggestions.append(
                {
                    "category": "文本完整性",
                    "priority": "high",
                    "suggestion": "建议提高DPI设置或使用更高质量的OCR引擎",
                    "expected_improvement": 0.15,
                }
            )

        if quality_metrics["field_extraction_rate"] < 0.7:
            suggestions.append(
                {
                    "category": "字段提取",
                    "priority": "high",
                    "suggestion": "建议优化字段识别规则或增加自定义字段模板",
                    "expected_improvement": 0.20,
                }
            )

        if quality_metrics["confidence_score"] < 0.75:
            suggestions.append(
                {
                    "category": "置信度",
                    "priority": "medium",
                    "suggestion": "建议使用多引擎验证或增加人工审核步骤",
                    "expected_improvement": 0.10,
                }
            )

        if quality_metrics["ocr_accuracy"] < 0.8:
            suggestions.append(
                {
                    "category": "OCR准确性",
                    "priority": "high",
                    "suggestion": "建议调整OCR预处理参数或使用更适合的OCR引擎",
                    "expected_improvement": 0.12,
                }
            )

        if quality_metrics["extracted_fields_count"] < 20:
            suggestions.append(
                {
                    "category": "提取字段数量",
                    "priority": "medium",
                    "suggestion": "建议检查文档质量或扩大字段识别范围",
                    "expected_improvement": 0.15,
                }
            )

        return suggestions

    def _assess_logic_consistency(self, extracted_data: dict) -> float:
        """评估逻辑一致性
        
        Args:
            extracted_data: 提取的结构化数据
            
        Returns:
            逻辑一致性分数 (0-1)
        """
        if not extracted_data:
            return 0.0

        consistency_score = 0.0
        checks_performed = 0

        # 检查日期逻辑一致性
        start_date = extracted_data.get("start_date")
        end_date = extracted_data.get("end_date")
        
        if start_date and end_date:
            checks_performed += 1
            try:
                # 简单的日期格式验证
                start_str = str(start_date)
                end_str = str(end_date)
                
                # 检查结束日期是否晚于开始日期
                if len(start_str) > 6 and len(end_str) > 6:
                    # 提取年份进行比较
                    start_year_match = re.search(r"\d{4}", start_str)
                    end_year_match = re.search(r"\d{4}", end_str)
                    
                    if start_year_match and end_year_match:
                        start_year = int(start_year_match.group())
                        end_year = int(end_year_match.group())
                        
                        if end_year >= start_year:
                            consistency_score += 1.0
                        else:
                            consistency_score += 0.2
                    else:
                        consistency_score += 0.5
                else:
                    consistency_score += 0.3
            except (Exception, ValueError):
                consistency_score += 0.2

        # 检查金额合理性
        rent_amount = extracted_data.get("rent_amount")
        deposit = extracted_data.get("deposit")
        
        if rent_amount and deposit:
            checks_performed += 1
            try:
                # 清理金额字符串
                rent_val = float(re.sub(r"[^\d.]", "", str(rent_amount)))
                deposit_val = float(re.sub(r"[^\d.]", "", str(deposit)))
                # 押金通常是租金的2-3倍
                if 1.5 <= deposit_val / rent_val <= 4:
                    consistency_score += 1.0
                elif 1 <= deposit_val / rent_val <= 6:
                    consistency_score += 0.5
                else:
                    consistency_score += 0.2
            except (Exception, ValueError, TypeError):
                # 计算异常时使用保守分数
                consistency_score += 0.3

        # 检查地址信息完整性
        address = extracted_data.get("property_address")
        if address:
            checks_performed += 1
            address_str = str(address)
            # 检查地址是否包含基本要素
            if len(address_str) > 10 and re.search(r"[省市县区街道路号]", address_str):
                consistency_score += 1.0
            elif len(address_str) > 5:
                consistency_score += 0.6
            else:
                consistency_score += 0.2

        # 检查合同方信息
        party_a = extracted_data.get("party_a")
        party_b = extracted_data.get("party_b")
        
        if party_a and party_b:
            checks_performed += 1
            # 确保甲乙双方不同
            if str(party_a) != str(party_b) and len(str(party_a)) > 2 and len(str(party_b)) > 2:
                consistency_score += 1.0
            else:
                consistency_score += 0.3

        # 检查关键字段的互斥性
        contract_number = extracted_data.get("contract_number")
        if contract_number:
            checks_performed += 1
            contract_str = str(contract_number)
            if len(contract_str) >= 3 and re.search(r"[\w\-]", contract_str):
                consistency_score += 1.0
            else:
                consistency_score += 0.4

        return consistency_score / max(checks_performed, 1)

    def _generate_processing_recommendations(self, quality_metrics: dict, processing_metadata: dict) -> list[str]:
        """生成处理建议
        
        Args:
            quality_metrics: 质量指标字典
            processing_metadata: 处理元数据
            
        Returns:
            建议列表
        """
        recommendations = []

        # 基于处理引擎的推荐
        engine_used = processing_metadata.get("processing_engine", "unknown")
        if engine_used == "single_engine":
            recommendations.append("建议启用多引擎处理以提高提取准确率")

        # 基于页面数量的推荐
        page_count = processing_metadata.get("page_count", 1)
        if page_count > 10:
            recommendations.append("对于长文档，建议分页处理以提高准确率")

        # 基于OCR设置的推荐
        dpi_setting = processing_metadata.get("dpi", 150)
        if dpi_setting < 300:
            recommendations.append("建议将DPI设置提高到300以上以获得更好的OCR效果")

        # 基于质量的推荐
        if quality_metrics["text_completeness"] < 0.7:
            recommendations.append("文本完整性较低，建议检查PDF文件质量或重新扫描")

        if quality_metrics["ocr_accuracy"] < 0.8:
            recommendations.append("OCR准确度较低，建议尝试其他OCR引擎或调整参数")

        if quality_metrics["field_extraction_rate"] < 0.6:
            recommendations.append("字段提取率较低，建议使用更高级的处理模式或人工校验")

        # 通用建议
        if not recommendations:
            recommendations.append("当前处理质量良好，建议继续保持")

        return recommendations

    def _determine_quality_level(self, score: float) -> dict[str, any]:
        """确定质量等级
        
        Args:
            score: 质量分数
            
        Returns:
            质量等级信息
        """
        for level_name, level_info in self.quality_levels.items():
            if score >= level_info["min_score"]:
                return {
                    "level": level_name,
                    "description": level_info["description"],
                    "color": level_info["color"],
                    "score": score,
                }

        # 默认返回最低等级
        return {
            "level": "very_poor",
            "description": "很差",
            "color": "#ff4d4f",
            "score": score,
        }


# 创建全局质量评估器实�?
pdf_quality_assessor = PDFProcessingQualityAssessment()
