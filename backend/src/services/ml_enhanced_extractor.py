"""
机器学习增强的合同信息提取器
集成NLP模型和规则引擎，提供智能化的中文租赁合同信息提取
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ExtractionMethod(Enum):
    """提取方法"""

    RULE_BASED = "rule_based"
    PATTERN_MATCHING = "pattern_matching"
    NLP_MODEL = "nlp_model"
    HYBRID = "hybrid"


class ConfidenceLevel(Enum):
    """置信度等级"""

    HIGH = "high"  # 0.8+
    MEDIUM = "medium"  # 0.6-0.8
    LOW = "low"  # 0.4-0.6
    VERY_LOW = "very_low"  # <0.4


@dataclass
class ExtractedField:
    """提取的字段"""

    name: str
    value: Any
    confidence: float
    method: ExtractionMethod
    source_text: str
    position: dict[str, int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """提取结果"""

    success: bool
    extracted_fields: dict[str, ExtractedField]
    overall_confidence: float
    method_used: ExtractionMethod
    processing_time: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class MLEnhancedExtractor:
    """机器学习增强的提取器"""

    def __init__(self):
        self.extraction_rules = self._load_enhanced_rules()
        self.field_patterns = self._load_field_patterns()
        self.validation_rules = self._load_validation_rules()
        self.context_analyzers = self._load_context_analyzers()

    def _load_enhanced_rules(self) -> Dict[str, Any][str, list[dict[str, Any]]]:
        """加载增强的提取规则"""
        return {
            # 合同基本信息
            "contract_number": [
                {
                    "pattern": r"合同编号[：:\s]*([A-Za-z0-9\-()（）]+)",
                    "confidence": 0.9,
                    "method": "pattern_matching",
                    "context_keywords": ["合同", "编号", "协议号"],
                    "post_process": "clean_contract_number",
                },
                {
                    "pattern": r"协议编号[：:\s]*([A-Za-z0-9\-()（）]+)",
                    "confidence": 0.85,
                    "method": "pattern_matching",
                    "context_keywords": ["协议", "编号"],
                    "post_process": "clean_contract_number",
                },
            ],
            # 当事人信息
            "landlord_name": [
                {
                    "pattern": r"出租方\s*[（(]甲方[）)][：:\s]*([^\n，,。；;]+?)(?=(?:法定代表人|统一社会|联系地址|联系人|联系电话|身份证|通讯地址))",
                    "confidence": 0.95,
                    "method": "pattern_matching",
                    "context_keywords": ["出租方", "甲方"],
                    "entity_type": "person_name",
                },
                {
                    "pattern": r"甲方[：:\s]*([^\n，,。；;]+?)(?=(?:法定代表人|统一社会|联系地址|联系人|联系电话|身份证|通讯地址))",
                    "confidence": 0.9,
                    "method": "pattern_matching",
                    "context_keywords": ["甲方"],
                    "entity_type": "person_name",
                },
            ],
            "tenant_name": [
                {
                    "pattern": r"承租方\s*[（(]乙方[）)][：:\s]*([^\n，,。；;]+?)(?=(?:身份证号码|通讯地址|联系电话|法定代表人))",
                    "confidence": 0.95,
                    "method": "pattern_matching",
                    "context_keywords": ["承租方", "乙方"],
                    "entity_type": "person_name",
                },
                {
                    "pattern": r"乙方[：:\s]*([^\n，,。；;]+?)(?=(?:身份证号码|通讯地址|联系电话|法定代表人))",
                    "confidence": 0.9,
                    "method": "pattern_matching",
                    "context_keywords": ["乙方"],
                    "entity_type": "person_name",
                },
            ],
            # 联系信息
            "landlord_phone": [
                {
                    "pattern": r"(?:出租方|甲方)[^：:]*?[：:\s]*([1][3-9]\d{9})",
                    "confidence": 0.9,
                    "method": "pattern_matching",
                    "context_keywords": ["出租方", "甲方", "联系电话", "电话"],
                    "entity_type": "phone",
                },
                {
                    "pattern": r"联系电话[：:\s]*([1][3-9]\d{9})",
                    "confidence": 0.85,
                    "method": "pattern_matching",
                    "context_keywords": ["联系电话", "电话"],
                    "entity_type": "phone",
                },
            ],
            "tenant_phone": [
                {
                    "pattern": r"(?:承租方|乙方)[^：:]*?[：:\s]*([1][3-9]\d{9})",
                    "confidence": 0.9,
                    "method": "pattern_matching",
                    "context_keywords": ["承租方", "乙方", "联系电话", "电话"],
                    "entity_type": "phone",
                }
            ],
            # 地址信息
            "property_address": [
                {
                    "pattern": r"租赁物业位于([^\n，,。；;]+?(?:省|市|区|县|镇|街道|路|号)[^\n，,。；;]*?(?:\d+号)?)",
                    "confidence": 0.9,
                    "method": "pattern_matching",
                    "context_keywords": ["租赁物业", "物业地址", "房屋地址"],
                    "entity_type": "address",
                },
                {
                    "pattern": r"房屋地址[：:\s]*([^\n，,。；;]+?(?:省|市|区|县|镇|街道|路|号)[^\n，,。；;]*)",
                    "confidence": 0.85,
                    "method": "pattern_matching",
                    "context_keywords": ["房屋地址", "物业地址"],
                    "entity_type": "address",
                },
            ],
            # 身份证信息
            "landlord_id": [
                {
                    "pattern": r"(?:出租方|甲方)[^：:]*?[：:\s]*([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])",
                    "confidence": 0.95,
                    "method": "pattern_matching",
                    "context_keywords": ["出租方", "甲方", "身份证"],
                    "entity_type": "id_card",
                }
            ],
            "tenant_id": [
                {
                    "pattern": r"(?:承租方|乙方)[^：:]*?[：:\s]*([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])",
                    "confidence": 0.95,
                    "method": "pattern_matching",
                    "context_keywords": ["承租方", "乙方", "身份证"],
                    "entity_type": "id_card",
                },
                {
                    "pattern": r"身份证号码[：:\s]*([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])",
                    "confidence": 0.9,
                    "method": "pattern_matching",
                    "context_keywords": ["身份证号码"],
                    "entity_type": "id_card",
                },
            ],
            # 日期信息
            "sign_date": [
                {
                    "pattern": r"签订日期[：:\s]*(\d{4})\s*[年\-/]\s*(\d{1,2})\s*[月\-/]\s*(\d{1,2})\s*[日]?",
                    "confidence": 0.9,
                    "method": "pattern_matching",
                    "context_keywords": ["签订日期", "签署日期", "签约日期"],
                    "entity_type": "date",
                },
                {
                    "pattern": r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*签订",
                    "confidence": 0.85,
                    "method": "pattern_matching",
                    "context_keywords": ["签订"],
                    "entity_type": "date",
                },
            ],
            "start_date": [
                {
                    "pattern": r"租赁期限.*?自\s*(\d{4})\s*[年\-/]\s*(\d{1,2})\s*[月\-/]\s*(\d{1,2})\s*[日]?",
                    "confidence": 0.9,
                    "method": "pattern_matching",
                    "context_keywords": ["租赁期限", "租期", "起租日期"],
                    "entity_type": "date",
                },
                {
                    "pattern": r"起租日期[：:\s]*(\d{4})\s*[年\-/]\s*(\d{1,2})\s*[月\-/]\s*(\d{1,2})\s*[日]?",
                    "confidence": 0.85,
                    "method": "pattern_matching",
                    "context_keywords": ["起租日期", "开始日期"],
                    "entity_type": "date",
                },
            ],
            "end_date": [
                {
                    "pattern": r"租赁期限.*?至\s*(\d{4})\s*[年\-/]\s*(\d{1,2})\s*[月\-/]\s*(\d{1,2})\s*[日]?",
                    "confidence": 0.9,
                    "method": "pattern_matching",
                    "context_keywords": ["租赁期限", "租期", "到期日期"],
                    "entity_type": "date",
                },
                {
                    "pattern": r"到期日期[：:\s]*(\d{4})\s*[年\-/]\s*(\d{1,2})\s*[月\-/]\s*(\d{1,2})\s*[日]?",
                    "confidence": 0.85,
                    "method": "pattern_matching",
                    "context_keywords": ["到期日期", "结束日期"],
                    "entity_type": "date",
                },
            ],
            # 金额信息
            "monthly_rent": [
                {
                    "pattern": r"月租金[：:\s]*([￥¥]?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*元)",
                    "confidence": 0.95,
                    "method": "pattern_matching",
                    "context_keywords": ["月租金", "每月租金", "房租"],
                    "entity_type": "amount",
                    "post_process": "extract_amount",
                },
                {
                    "pattern": r"租金[：:\s]*([￥¥]?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*元)\/月",
                    "confidence": 0.9,
                    "method": "pattern_matching",
                    "context_keywords": ["租金"],
                    "entity_type": "amount",
                    "post_process": "extract_amount",
                },
            ],
            "total_deposit": [
                {
                    "pattern": r"押金[：:\s]*([￥¥]?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*元)",
                    "confidence": 0.95,
                    "method": "pattern_matching",
                    "context_keywords": ["押金", "保证金", "押金金额"],
                    "entity_type": "amount",
                    "post_process": "extract_amount",
                },
                {
                    "pattern": r"保证金[：:\s]*([￥¥]?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*元)",
                    "confidence": 0.9,
                    "method": "pattern_matching",
                    "context_keywords": ["保证金"],
                    "entity_type": "amount",
                    "post_process": "extract_amount",
                },
            ],
            # 面积信息
            "property_area": [
                {
                    "pattern": r"租赁面积[：:\s]*(\d+(?:\.\d+)?)\s*平方米",
                    "confidence": 0.9,
                    "method": "pattern_matching",
                    "context_keywords": ["租赁面积", "建筑面积", "使用面积"],
                    "entity_type": "area",
                },
                {
                    "pattern": r"建筑面积[：:\s]*(\d+(?:\.\d+)?)\s*平方米",
                    "confidence": 0.85,
                    "method": "pattern_matching",
                    "context_keywords": ["建筑面积"],
                    "entity_type": "area",
                },
            ],
        }

    def _load_field_patterns(self) -> Dict[str, Any]:
        """加载字段模式"""
        return {
            "person_name": {
                "min_length": 2,
                "max_length": 10,
                "contains_chinese": True,
                "exclude_numbers": True,
                "exclude_special_chars": True,
            },
            "phone": {"pattern": r"^1[3-9]\d{9}$", "length": 11},
            "id_card": {
                "pattern": r"^[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]$",
                "length": 18,
            },
            "address": {
                "min_length": 10,
                "contains_location_keywords": True,
                "location_keywords": ["省", "市", "区", "县", "镇", "街道", "路", "号"],
            },
            "date": {
                "formats": [
                    r"(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})[日]?",
                    r"(\d{4})-(\d{2})-(\d{2})",
                ]
            },
            "amount": {
                "pattern": r"^\d+(?:,\d{3})*(?:\.\d{1,2})?$",
                "min_value": 0,
                "max_value": 10000000,  # 1千万上限
            },
            "area": {
                "pattern": r"^\d+(?:\.\d+)?$",
                "min_value": 0.1,
                "max_value": 10000,
            },
        }

    def _load_validation_rules(self) -> Dict[str, Any][str, callable]:
        """加载验证规则"""
        return {
            "person_name": self._validate_person_name,
            "phone": self._validate_phone,
            "id_card": self._validate_id_card,
            "address": self._validate_address,
            "date": self._validate_date,
            "amount": self._validate_amount,
            "area": self._validate_area,
        }

    def _load_context_analyzers(self) -> Dict[str, Any][str, callable]:
        """加载上下文分析器"""
        return {
            "contract_context": self._analyze_contract_context,
            "party_relationship": self._analyze_party_relationship,
            "financial_context": self._analyze_financial_context,
            "temporal_context": self._analyze_temporal_context,
        }

    async def extract_contract_info(
        self, text: str, method: str = "hybrid"
    ) -> ExtractionResult:
        """提取合同信息"""
        start_time = datetime.now()

        try:
            # 文本预处理
            cleaned_text = self._preprocess_text(text)

            # 根据方法选择提取策略
            if method == "rule_based":
                extracted_fields = await self._extract_with_rules(cleaned_text)
            elif method == "pattern_matching":
                extracted_fields = await self._extract_with_patterns(cleaned_text)
            elif method == "nlp_model":
                extracted_fields = await self._extract_with_nlp(cleaned_text)
            else:  # hybrid
                extracted_fields = await self._extract_hybrid(cleaned_text)

            # 后处理和验证
            validated_fields = await self._post_process_fields(
                extracted_fields, cleaned_text
            )

            # 计算总体置信度
            overall_confidence = self._calculate_overall_confidence(validated_fields)

            # 生成建议
            suggestions = self._generate_suggestions(validated_fields)

            processing_time = (datetime.now() - start_time).total_seconds()

            return ExtractionResult(
                success=True,
                extracted_fields={field.name: field for field in validated_fields},
                overall_confidence=overall_confidence,
                method_used=ExtractionMethod(method),
                processing_time=processing_time,
                suggestions=suggestions,
            )

        except Exception as e:
            logger.error(f"合同信息提取失败: {str(e)}")
            return ExtractionResult(
                success=False,
                extracted_fields={},
                overall_confidence=0.0,
                method_used=ExtractionMethod(method),
                processing_time=(datetime.now() - start_time).total_seconds(),
                errors=[str(e)],
            )

    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        if not text:
            return text

        # 标准化空白字符
        text = re.sub(r"\s+", " ", text)

        # 修复常见的OCR错误
        ocr_fixes = {
            "，。": "，",
            "。。": "。",
            "，，": "，",
            "？？": "？",
            "！！": "！",
            "（ ": "（",
            " ）": "）",
            "甲方：": "甲方：",
            "乙方：": "乙方：",
        }

        for old, new in ocr_fixes.items():
            text = text.replace(old, new)

        # 移除多余空行
        text = "\n".join(line for line in text.split("\n") if line.strip())

        return text.strip()

    async def _extract_with_rules(self, text: str) -> List[ExtractedField]:
        """基于规则提取"""
        extracted_fields = []

        for field_name, rules in self.extraction_rules.items():
            for rule in rules:
                try:
                    pattern = rule["pattern"]
                    matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)

                    for match in matches:
                        value = self._extract_match_value(match, rule)
                        if value:
                            field = ExtractedField(
                                name=field_name,
                                value=value,
                                confidence=rule["confidence"],
                                method=ExtractionMethod.RULE_BASED,
                                source_text=match.group(0),
                                position={"start": match.start(), "end": match.end()},
                                metadata={
                                    "rule_pattern": pattern,
                                    "context_keywords": rule.get(
                                        "context_keywords", []
                                    ),
                                },
                            )
                            extracted_fields.append(field)
                            break  # 只取第一个匹配

                except Exception as e:
                    logger.warning(f"规则提取失败 {field_name}: {str(e)}")
                    continue

        return extracted_fields

    async def _extract_with_patterns(self, text: str) -> List[ExtractedField]:
        """基于模式匹配提取"""
        # 这里可以集成更复杂的模式匹配算法
        return await self._extract_with_rules(text)

    async def _extract_with_nlp(self, text: str) -> List[ExtractedField]:
        """基于NLP模型提取"""
        # 这里可以集成BERT、CRF等NLP模型
        # 目前先使用规则作为基础
        extracted_fields = await self._extract_with_rules(text)

        # 应用一些启发式NLP分析
        for extracted_field in extracted_fields:
            if extracted_field.name.endswith("_name"):
                # 姓名长度合理性检查
                if isinstance(extracted_field.value, str):
                    if (
                        len(extracted_field.value) < 2
                        or len(extracted_field.value) > 10
                    ):
                        extracted_field.confidence *= 0.7
                    # 检查是否包含常见姓氏
                    common_surnames = [
                        "王",
                        "李",
                        "张",
                        "刘",
                        "陈",
                        "杨",
                        "黄",
                        "赵",
                        "周",
                        "吴",
                    ]
                    if extracted_field.value[0] not in common_surnames:
                        extracted_field.confidence *= 0.9

        return extracted_fields

    async def _extract_hybrid(self, text: str) -> List[ExtractedField]:
        """混合方法提取"""
        # 先用规则提取
        rule_fields = await self._extract_with_rules(text)

        # 再用NLP增强
        nlp_fields = await self._extract_with_nlp(text)

        # 合并结果，选择置信度最高的
        field_map = defaultdict(list)
        for rule_field in rule_fields + nlp_fields:
            field_map[rule_field.name].append(rule_field)

        # 选择每个字段的最佳结果
        best_fields = []
        for field_name, fields in field_map.items():
            best_field = max(fields, key=lambda f: f.confidence)
            best_fields.append(best_field)

        return best_fields

    def _extract_match_value(self, match, rule: dict[str, Any]) -> Any:
        """提取匹配值"""
        try:
            if rule.get("entity_type") == "date":
                # 处理日期
                groups = match.groups()
                if len(groups) >= 3:
                    return f"{groups[0]}-{groups[1].zfill(2)}-{groups[2].zfill(2)}"
            elif rule.get("entity_type") in ["amount", "area"]:
                # 处理数字
                groups = match.groups()
                if groups:
                    # 取最后一个数字组
                    for group in reversed(groups):
                        if group and re.match(r"\d", group):
                            # 清理数字格式
                            clean_number = re.sub(r"[^\d.]", "", group)
                            try:
                                return float(clean_number)
                            except ValueError:
                                continue
                return None
            else:
                # 处理文本
                value = match.group(1) if match.groups() else match.group(0)
                if value:
                    value = value.strip()
                    # 应用后处理
                    post_process = rule.get("post_process")
                    if post_process:
                        value = self._apply_post_processing(value, post_process)
                return value

        except Exception as e:
            logger.warning(f"提取匹配值失败: {str(e)}")
            return None

    def _apply_post_processing(self, value: str, process_type: str) -> str:
        """应用后处理"""
        if process_type == "clean_contract_number":
            # 清理合同编号
            value = re.sub(r"[^\w\-()（）]", "", value)
            return value.upper()
        elif process_type == "extract_amount":
            # 提取金额数值
            value = re.sub(r"[^\d.]", "", value)
            return value
        else:
            return value

    async def _post_process_fields(
        self, fields: list[ExtractedField], text: str
    ) -> List[ExtractedField]:
        """后处理字段"""
        processed_fields = []

        for processed_field in fields:
            # 验证字段
            validation_result = self._validate_field(processed_field, text)
            processed_field.confidence *= validation_result["confidence_multiplier"]
            processed_field.metadata.update(validation_result.get("metadata", {}))

            # 应用业务逻辑验证
            business_validation = self._validate_business_logic(
                processed_field, fields, text
            )
            processed_field.confidence *= business_validation["confidence_multiplier"]
            processed_field.metadata.update(business_validation.get("metadata", {}))

            if processed_field.confidence > 0.3:  # 过滤低置信度字段
                processed_fields.append(processed_field)

        return processed_fields

    def _validate_field(self, field: ExtractedField, text: str) -> Dict[str, Any]:
        """验证字段"""
        result = {"confidence_multiplier": 1.0, "metadata": {}}

        entity_type = field.metadata.get("entity_type")
        if entity_type and entity_type in self.validation_rules:
            validator = self.validation_rules[entity_type]
            validation_result = validator(field.value)
            result.update(validation_result)

        return result

    def _validate_person_name(self, value: str) -> Dict[str, Any]:
        """验证姓名"""
        result = {"confidence_multiplier": 1.0, "metadata": {}}

        if not value or len(value) < 2 or len(value) > 10:
            result["confidence_multiplier"] = 0.5
            result["metadata"]["validation_error"] = "姓名长度不合理"

        # 检查是否包含数字或特殊字符
        if re.search(r"[0-9@#$%^&*()]", value):
            result["confidence_multiplier"] = 0.3
            result["metadata"]["validation_error"] = "姓名包含特殊字符"

        # 检查中文字符比例
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", value))
        if chinese_chars / len(value) < 0.7:
            result["confidence_multiplier"] = 0.8
            result["metadata"]["validation_warning"] = "中文字符比例较低"

        return result

    def _validate_phone(self, value: str) -> Dict[str, Any]:
        """验证电话号码"""
        result = {"confidence_multiplier": 1.0, "metadata": {}}

        if not re.match(r"^1[3-9]\d{9}$", value):
            result["confidence_multiplier"] = 0.3
            result["metadata"]["validation_error"] = "手机号码格式不正确"

        return result

    def _validate_id_card(self, value: str) -> Dict[str, Any]:
        """验证身份证号"""
        result = {"confidence_multiplier": 1.0, "metadata": {}}

        if not re.match(
            r"^[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]$",
            value,
        ):
            result["confidence_multiplier"] = 0.3
            result["metadata"]["validation_error"] = "身份证号码格式不正确"
        else:
            # 验证校验码
            if len(value) == 18:
                weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
                checksum_map = ["1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2"]
                try:
                    total = 0
                    for i in range(17):
                        total += int(value[i]) * weights[i]
                    checksum = checksum_map[total % 11]
                    if value[17].upper() != checksum:
                        result["confidence_multiplier"] = 0.5
                        result["metadata"]["validation_warning"] = (
                            "身份证校验码可能有误"
                        )
                except (ValueError, IndexError, AttributeError):
                    # 身份证验证异常时降低置信度
                    result["confidence_multiplier"] = 0.7
                    result["metadata"]["validation_warning"] = "身份证校验失败"

        return result

    def _validate_address(self, value: str) -> Dict[str, Any]:
        """验证地址"""
        result = {"confidence_multiplier": 1.0, "metadata": {}}

        if len(value) < 5:
            result["confidence_multiplier"] = 0.6
            result["metadata"]["validation_warning"] = "地址过短"

        # 检查是否包含地址关键词
        location_keywords = ["省", "市", "区", "县", "镇", "街道", "路", "号"]
        has_keywords = any(keyword in value for keyword in location_keywords)
        if not has_keywords:
            result["confidence_multiplier"] = 0.7
            result["metadata"]["validation_warning"] = "地址缺少位置关键词"

        return result

    def _validate_date(self, value: str) -> Dict[str, Any]:
        """验证日期"""
        result = {"confidence_multiplier": 1.0, "metadata": {}}

        try:
            parsed_date = datetime.strptime(value, "%Y-%m-%d")
            # 检查日期合理性
            now = datetime.now()
            if parsed_date.year < 1990 or parsed_date.year > now.year + 10:
                result["confidence_multiplier"] = 0.7
                result["metadata"]["validation_warning"] = "日期年份可能不正确"
        except ValueError:
            result["confidence_multiplier"] = 0.3
            result["metadata"]["validation_error"] = "日期格式不正确"

        return result

    def _validate_amount(self, value: str | float) -> Dict[str, Any]:
        """验证金额"""
        result = {"confidence_multiplier": 1.0, "metadata": {}}

        try:
            amount = float(value)
            if amount < 0:
                result["confidence_multiplier"] = 0.1
                result["metadata"]["validation_error"] = "金额不能为负数"
            elif amount > 10000000:  # 1千万
                result["confidence_multiplier"] = 0.8
                result["metadata"]["validation_warning"] = "金额较大，请确认正确性"
        except (ValueError, TypeError):
            result["confidence_multiplier"] = 0.1
            result["metadata"]["validation_error"] = "金额格式不正确"

        return result

    def _validate_area(self, value: str | float) -> Dict[str, Any]:
        """验证面积"""
        result = {"confidence_multiplier": 1.0, "metadata": {}}

        try:
            area = float(value)
            if area <= 0:
                result["confidence_multiplier"] = 0.1
                result["metadata"]["validation_error"] = "面积必须大于0"
            elif area > 10000:  # 1万平方米
                result["confidence_multiplier"] = 0.8
                result["metadata"]["validation_warning"] = "面积较大，请确认单位"
        except (ValueError, TypeError):
            result["confidence_multiplier"] = 0.1
            result["metadata"]["validation_error"] = "面积格式不正确"

        return result

    def _validate_business_logic(
        self, field: ExtractedField, all_fields: list[ExtractedField], text: str
    ) -> Dict[str, Any]:
        """验证业务逻辑"""
        result = {"confidence_multiplier": 1.0, "metadata": {}}

        # 日期逻辑验证
        if field.name in ["start_date", "end_date", "sign_date"]:
            other_dates = {
                f.name: f.value
                for f in all_fields
                if f.name in ["start_date", "end_date", "sign_date"]
            }

            if field.name == "start_date" and "end_date" in other_dates:
                try:
                    start_date = datetime.strptime(field.value, "%Y-%m-%d")
                    end_date = datetime.strptime(other_dates["end_date"], "%Y-%m-%d")
                    if start_date >= end_date:
                        result["confidence_multiplier"] *= 0.7
                        result["metadata"]["business_warning"] = "开始日期晚于结束日期"
                except (ValueError, TypeError, AttributeError):
                    # 数据提取异常时静默处理
                    pass

            if field.name == "sign_date" and "start_date" in other_dates:
                try:
                    sign_date = datetime.strptime(field.value, "%Y-%m-%d")
                    start_date = datetime.strptime(
                        other_dates["start_date"], "%Y-%m-%d"
                    )
                    if sign_date > start_date:
                        result["confidence_multiplier"] *= 0.8
                        result["metadata"]["business_warning"] = "签署日期晚于起租日期"
                except (ValueError, TypeError, AttributeError):
                    # 数据提取异常时静默处理
                    pass

        # 金额逻辑验证
        if field.name == "monthly_rent" and "total_deposit" in {
            f.name: f.value for f in all_fields
        }:
            try:
                rent = float(field.value)
                deposit = float(
                    next(f.value for f in all_fields if f.name == "total_deposit")
                )
                # 押金通常是1-3个月租金
                deposit_months = deposit / rent
                if deposit_months > 6:
                    result["confidence_multiplier"] *= 0.8
                    result["metadata"]["business_warning"] = "押金金额异常高"
                elif deposit_months < 0.5:
                    result["confidence_multiplier"] *= 0.9
                    result["metadata"]["business_warning"] = "押金金额异常低"
            except (ValueError, TypeError, AttributeError):
                # 数据提取异常时静默处理
                pass

        return result

    def _analyze_contract_context(self, text: str) -> Dict[str, Any]:
        """分析合同上下文"""
        return {
            "is_rental_contract": any(
                keyword in text for keyword in ["租赁合同", "房屋租赁", "租房协议"]
            ),
            "has_landlord_tenant": "甲方" in text and "乙方" in text,
            "text_length": len(text),
            "complexity": "high"
            if len(text) > 2000
            else "medium"
            if len(text) > 500
            else "low",
        }

    def _analyze_party_relationship(self, text: str) -> Dict[str, Any]:
        """分析当事方关系"""
        return {
            "party_structure": "bilateral"
            if "甲方" in text and "乙方" in text
            else "unknown",
            "has_legal_representative": "法定代表人" in text,
            "has_contact_info": "联系电话" in text or "联系地址" in text,
        }

    def _analyze_financial_context(self, text: str) -> Dict[str, Any]:
        """分析财务上下文"""
        return {
            "has_rent_info": "租金" in text,
            "has_deposit_info": "押金" in text,
            "payment_terms_mentioned": "付款方式" in text or "支付方式" in text,
        }

    def _analyze_temporal_context(self, text: str) -> Dict[str, Any]:
        """分析时间上下文"""
        return {
            "has_lease_term": "租赁期限" in text,
            "has_specific_dates": bool(re.search(r"\d{4}年\d{1,2}月\d{1,2}日", text)),
            "time_structure": "standard"
            if "起租" in text and "到期" in text
            else "custom",
        }

    def _calculate_overall_confidence(self, fields: list[ExtractedField]) -> float:
        """计算总体置信度"""
        if not fields:
            return 0.0

        # 根据字段重要性加权
        field_weights = {
            "contract_number": 0.1,
            "landlord_name": 0.15,
            "tenant_name": 0.15,
            "property_address": 0.15,
            "monthly_rent": 0.15,
            "start_date": 0.1,
            "end_date": 0.1,
            "sign_date": 0.05,
            "total_deposit": 0.05,
        }

        weighted_confidence = 0.0
        total_weight = 0.0

        for weighted_field in fields:
            weight = field_weights.get(weighted_field.name, 0.05)
            weighted_confidence += weighted_field.confidence * weight
            total_weight += weight

        return weighted_confidence / total_weight if total_weight > 0 else 0.0

    def _generate_suggestions(self, fields: list[ExtractedField]) -> List[str]:
        """生成建议"""
        suggestions = []

        field_names = {f.name for f in fields}

        # 检查关键字段缺失
        key_fields = [
            "landlord_name",
            "tenant_name",
            "property_address",
            "monthly_rent",
        ]
        missing_fields = key_fields - field_names
        if missing_fields:
            suggestions.append(f"关键字段缺失: {', '.join(missing_fields)}")

        # 检查低置信度字段
        low_confidence_fields = [f.name for f in fields if f.confidence < 0.6]
        if low_confidence_fields:
            suggestions.append(
                f"以下字段置信度较低，建议人工核对: {', '.join(low_confidence_fields)}"
            )

        # 检查金额合理性
        rent_fields = [f for f in fields if f.name == "monthly_rent"]
        if rent_fields:
            try:
                rent = float(rent_fields[0].value)
                if rent > 50000:  # 月租金5万以上
                    suggestions.append("月租金金额较高，请确认是否正确")
                elif rent < 100:  # 月租金100以下
                    suggestions.append("月租金金额较低，请确认是否正确")
            except (ValueError, TypeError, AttributeError):
                # 数据验证异常时添加建议
                suggestions.append("数据格式异常，请检查")

        # 检查日期合理性
        date_fields = [f for f in fields if f.name in ["start_date", "end_date"]]
        if len(date_fields) == 2:
            try:
                start_date = datetime.strptime(
                    next(f.value for f in date_fields if f.name == "start_date"),
                    "%Y-%m-%d",
                )
                end_date = datetime.strptime(
                    next(f.value for f in date_fields if f.name == "end_date"),
                    "%Y-%m-%d",
                )
                if (end_date - start_date).days > 365 * 10:  # 超过10年
                    suggestions.append("租赁期限超过10年，请确认是否正确")
                elif (end_date - start_date).days < 30:  # 少于1个月
                    suggestions.append("租赁期限过短，请确认是否正确")
            except (ValueError, TypeError, AttributeError):
                # 数据验证异常时添加建议
                suggestions.append("数据格式异常，请检查")

        return suggestions


# 创建全局实例
ml_enhanced_extractor = MLEnhancedExtractor()
