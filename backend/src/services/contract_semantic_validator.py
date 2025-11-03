from typing import Any

"""
合同关键字段语义理解和验证系统
对提取的合同字段进行语义分析、验证和标准化
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum

import jieba

logger = logging.getLogger(__name__)


class FieldType(str, Enum):
    """字段类型"""

    TEXT = "text"
    NUMBER = "number"
    DECIMAL = "decimal"
    DATE = "date"
    PHONE = "phone"
    ADDRESS = "address"
    PERSON_NAME = "person_name"
    ORGANIZATION = "organization"
    ID_CARD = "id_card"
    EMAIL = "email"
    URL = "url"
    BOOLEAN = "boolean"
    ENUM = "enum"


class ValidationLevel(str, Enum):
    """验证级别"""

    ERROR = "error"  # 错误，必须修正
    WARNING = "warning"  # 警告，建议修正
    INFO = "info"  # 信息，仅供参考
    SUCCESS = "success"  # 验证通过


@dataclass
class ValidationResult:
    """验证结果"""

    field_name: str
    original_value: str
    normalized_value: Any
    validation_level: ValidationLevel
    confidence: float
    error_messages: list[str] = field(default_factory=list)
    warning_messages: list[str] = field(default_factory=list)
    info_messages: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticAnalysisResult:
    """语义分析结果"""

    field_name: str
    field_type: FieldType
    semantic_meaning: str
    context_relevance: float
    confidence: float
    extracted_entities: dict[str, Any] = field(default_factory=dict)
    relationships: dict[str, str] = field(default_factory=dict)
    validation_result: ValidationResult | None = None


@dataclass
class ContractValidationReport:
    """合同验证报告"""

    contract_id: str | None
    total_fields: int
    valid_fields: int
    error_fields: int
    warning_fields: int
    overall_confidence: float
    field_results: dict[str, ValidationResult]
    semantic_analysis: dict[str, SemanticAnalysisResult]
    summary: str
    recommendations: list[str]


class ContractSemanticValidator:
    """合同语义验证器"""

    def __init__(self):
        # 初始化分词器
        jieba.initialize()

        # 加载字段类型定义
        self.field_types_config = self._load_field_types_config()

        # 加载验证规则
        self.validation_rules = self._load_validation_rules()

        # 加载语义模式
        self.semantic_patterns = self._load_semantic_patterns()

        # 加载业务规则
        self.business_rules = self._load_business_rules()

        # 字段间关系定义
        self.field_relationships = self._load_field_relationships()

    def _load_field_types_config(self) -> dict[str, dict[str, Any]]:
        """加载字段类型配置"""
        return {
            # 基础信息字段
            "contract_number": {
                "type": FieldType.TEXT,
                "pattern": r"^[A-Z0-9\-]{5,30}$",
                "required": True,
                "description": "合同编号",
            },
            "contract_name": {
                "type": FieldType.TEXT,
                "min_length": 2,
                "max_length": 100,
                "required": True,
                "description": "合同名称",
            },
            "signing_date": {
                "type": FieldType.DATE,
                "required": True,
                "description": "签署日期",
            },
            "effective_date": {
                "type": FieldType.DATE,
                "required": True,
                "description": "生效日期",
            },
            "expiry_date": {
                "type": FieldType.DATE,
                "required": True,
                "description": "到期日期",
            },
            # 当事人信息字段
            "party_a_name": {
                "type": FieldType.PERSON_NAME,
                "required": True,
                "description": "甲方姓名",
            },
            "party_a_id": {
                "type": FieldType.ID_CARD,
                "required": True,
                "description": "甲方身份证号",
            },
            "party_a_phone": {
                "type": FieldType.PHONE,
                "required": True,
                "description": "甲方联系电话",
            },
            "party_a_address": {
                "type": FieldType.ADDRESS,
                "required": True,
                "description": "甲方地址",
            },
            "party_b_name": {
                "type": FieldType.PERSON_NAME,
                "required": True,
                "description": "乙方姓名",
            },
            "party_b_id": {
                "type": FieldType.ID_CARD,
                "required": True,
                "description": "乙方身份证号",
            },
            "party_b_phone": {
                "type": FieldType.PHONE,
                "required": True,
                "description": "乙方联系电话",
            },
            "party_b_address": {
                "type": FieldType.ADDRESS,
                "required": True,
                "description": "乙方地址",
            },
            # 租赁物信息字段
            "property_address": {
                "type": FieldType.ADDRESS,
                "required": True,
                "description": "租赁物地址",
            },
            "property_area": {
                "type": FieldType.DECIMAL,
                "min_value": 0.1,
                "max_value": 10000,
                "required": True,
                "description": "租赁面积（平方米）",
            },
            "property_type": {
                "type": FieldType.ENUM,
                "enum_values": ["住宅", "商业", "办公", "工业", "仓储"],
                "required": True,
                "description": "物业类型",
            },
            # 租赁条款字段
            "monthly_rent": {
                "type": FieldType.DECIMAL,
                "min_value": 0,
                "required": True,
                "description": "月租金（元）",
            },
            "payment_method": {
                "type": FieldType.ENUM,
                "enum_values": ["月付", "季付", "半年付", "年付"],
                "required": True,
                "description": "付款方式",
            },
            "deposit_amount": {
                "type": FieldType.DECIMAL,
                "min_value": 0,
                "required": True,
                "description": "押金金额（元）",
            },
            "lease_term": {
                "type": FieldType.NUMBER,
                "min_value": 1,
                "max_value": 300,
                "required": True,
                "description": "租赁期限（月）",
            },
            "rent_increase_rate": {
                "type": FieldType.DECIMAL,
                "min_value": 0,
                "max_value": 100,
                "required": False,
                "description": "租金年增长率（%）",
            },
            # 其他费用字段
            "management_fee": {
                "type": FieldType.DECIMAL,
                "min_value": 0,
                "required": False,
                "description": "管理费（元/月）",
            },
            "property_fee": {
                "type": FieldType.DECIMAL,
                "min_value": 0,
                "required": False,
                "description": "物业费（元/月）",
            },
            "utility_fee": {
                "type": FieldType.DECIMAL,
                "min_value": 0,
                "required": False,
                "description": "水电费（元/月）",
            },
        }

    def _load_validation_rules(self) -> dict[str, Any][str, callable]:
        """加载验证规则"""
        return {
            FieldType.TEXT: self._validate_text,
            FieldType.NUMBER: self._validate_number,
            FieldType.DECIMAL: self._validate_decimal,
            FieldType.DATE: self._validate_date,
            FieldType.PHONE: self._validate_phone,
            FieldType.ADDRESS: self._validate_address,
            FieldType.PERSON_NAME: self._validate_person_name,
            FieldType.ORGANIZATION: self._validate_organization,
            FieldType.ID_CARD: self._validate_id_card,
            FieldType.EMAIL: self._validate_email,
            FieldType.URL: self._validate_url,
            FieldType.BOOLEAN: self._validate_boolean,
            FieldType.ENUM: self._validate_enum,
        }

    def _load_semantic_patterns(self) -> dict[str, Any][str, list[dict[str, Any]]]:
        """加载语义模式"""
        return {
            "contract_patterns": [
                {"pattern": r"租赁合同", "meaning": "租赁关系", "confidence": 0.9},
                {"pattern": r"房屋租赁", "meaning": "房屋租赁", "confidence": 0.95},
                {"pattern": r"租赁协议", "meaning": "租赁协议", "confidence": 0.8},
            ],
            "party_patterns": [
                {
                    "pattern": r"甲方[：:]\s*([^\n]+)",
                    "meaning": "出租方信息",
                    "confidence": 0.9,
                },
                {
                    "pattern": r"乙方[：:]\s*([^\n]+)",
                    "meaning": "承租方信息",
                    "confidence": 0.9,
                },
            ],
            "amount_patterns": [
                {
                    "pattern": r"租金[：:]\s*([^\n]+)",
                    "meaning": "租金金额",
                    "confidence": 0.85,
                },
                {
                    "pattern": r"押金[：:]\s*([^\n]+)",
                    "meaning": "押金金额",
                    "confidence": 0.85,
                },
                {
                    "pattern": r"(\d+(?:\.\d+)?)\s*元",
                    "meaning": "金额数值",
                    "confidence": 0.7,
                },
            ],
            "date_patterns": [
                {
                    "pattern": r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
                    "meaning": "中文日期",
                    "confidence": 0.95,
                },
                {
                    "pattern": r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
                    "meaning": "标准日期",
                    "confidence": 0.9,
                },
            ],
            "address_patterns": [
                {
                    "pattern": r"地址[：:]\s*([^\n]+)",
                    "meaning": "地址信息",
                    "confidence": 0.85,
                },
                {
                    "pattern": r"([^，。\n]*(?:省|市|区|县|镇|街道|路|号)[^，。\n]*)",
                    "meaning": "中文地址",
                    "confidence": 0.7,
                },
            ],
        }

    def _load_business_rules(self) -> dict[str, Any][str, callable]:
        """加载业务规则"""
        return {
            "date_consistency": self._check_date_consistency,
            "amount_reasonableness": self._check_amount_reasonableness,
            "party_completeness": self._check_party_completeness,
            "address_validity": self._check_address_validity,
            "term_consistency": self._check_term_consistency,
            "payment_logic": self._check_payment_logic,
            "id_card_validity": self._check_id_card_validity,
        }

    def _load_field_relationships(self) -> dict[str, list[str]]:
        """加载字段间关系"""
        return {
            "signing_date": ["effective_date", "expiry_date"],
            "effective_date": ["expiry_date"],
            "party_a_name": ["party_a_id", "party_a_phone", "party_a_address"],
            "party_b_name": ["party_b_id", "party_b_phone", "party_b_address"],
            "monthly_rent": ["payment_method", "deposit_amount", "lease_term"],
            "property_area": ["monthly_rent", "management_fee", "property_fee"],
            "lease_term": ["expiry_date", "rent_increase_rate"],
        }

    async def validate_contract_fields(
        self, contract_data: dict[str, Any], contract_text: str | None = None
    ) -> ContractValidationReport:
        """验证合同字段"""
        try:
            field_results = {}
            semantic_analysis = {}

            total_fields = len(contract_data)
            valid_fields = 0
            error_fields = 0
            warning_fields = 0

            # 逐个验证字段
            for field_name, field_value in contract_data.items():
                # 语义分析
                semantic_result = await self._analyze_field_semantics(
                    field_name, field_value, contract_text
                )
                semantic_analysis[field_name] = semantic_result

                # 字段验证
                validation_result = await self._validate_field(
                    field_name, field_value, semantic_result
                )
                field_results[field_name] = validation_result

                # 统计结果
                if validation_result.validation_level == ValidationLevel.SUCCESS:
                    valid_fields += 1
                elif validation_result.validation_level == ValidationLevel.ERROR:
                    error_fields += 1
                elif validation_result.validation_level == ValidationLevel.WARNING:
                    warning_fields += 1

            # 业务规则验证
            business_validation_results = await self._validate_business_rules(
                contract_data, field_results
            )

            # 计算总体置信度
            overall_confidence = self._calculate_overall_confidence(field_results)

            # 生成摘要和建议
            summary, recommendations = self._generate_summary_and_recommendations(
                field_results, business_validation_results, overall_confidence
            )

            return ContractValidationReport(
                contract_id=contract_data.get("contract_id"),
                total_fields=total_fields,
                valid_fields=valid_fields,
                error_fields=error_fields,
                warning_fields=warning_fields,
                overall_confidence=overall_confidence,
                field_results=field_results,
                semantic_analysis=semantic_analysis,
                summary=summary,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"合同字段验证失败: {e}")
            return self._create_error_report(str(e))

    async def _analyze_field_semantics(
        self, field_name: str, field_value: Any, contract_text: str | None = None
    ) -> SemanticAnalysisResult:
        """分析字段语义"""
        try:
            # 获取字段配置
            field_config = self.field_types_config.get(field_name, {})
            field_type = field_config.get("type", FieldType.TEXT)

            # 基础语义分析
            semantic_meaning = field_config.get("description", field_name)
            context_relevance = self._calculate_context_relevance(
                field_name, field_value, contract_text
            )

            # 提取实体
            extracted_entities = await self._extract_entities_from_field(
                field_value, field_type
            )

            # 分析字段关系
            relationships = self._analyze_field_relationships(
                field_name, field_value, contract_text
            )

            # 计算置信度
            confidence = self._calculate_semantic_confidence(
                field_name, field_value, extracted_entities
            )

            return SemanticAnalysisResult(
                field_name=field_name,
                field_type=field_type,
                semantic_meaning=semantic_meaning,
                context_relevance=context_relevance,
                confidence=confidence,
                extracted_entities=extracted_entities,
                relationships=relationships,
            )

        except Exception as e:
            logger.error(f"语义分析失败 {field_name}: {e}")
            return SemanticAnalysisResult(
                field_name=field_name,
                field_type=FieldType.TEXT,
                semantic_meaning="分析失败",
                context_relevance=0.0,
                confidence=0.0,
            )

    async def _validate_field(
        self, field_name: str, field_value: Any, semantic_result: SemanticAnalysisResult
    ) -> ValidationResult:
        """验证单个字段"""
        try:
            # 获取字段配置
            field_config = self.field_types_config.get(field_name, {})
            field_type = semantic_result.field_type

            # 类型转换和基础验证
            normalized_value = self._normalize_field_value(field_value, field_type)
            validation_result = ValidationResult(
                field_name=field_name,
                original_value=str(field_value),
                normalized_value=normalized_value,
                validation_level=ValidationLevel.SUCCESS,
                confidence=semantic_result.confidence,
            )

            # 执行类型特定验证
            if field_type in self.validation_rules:
                validation_func = self.validation_rules[field_type]
                type_validation = await validation_func(normalized_value, field_config)

                # 合并验证结果
                validation_result.validation_level = type_validation.get(
                    "level", ValidationLevel.SUCCESS
                )
                validation_result.error_messages.extend(
                    type_validation.get("errors", [])
                )
                validation_result.warning_messages.extend(
                    type_validation.get("warnings", [])
                )
                validation_result.info_messages.extend(type_validation.get("info", []))
                validation_result.suggestions.extend(
                    type_validation.get("suggestions", [])
                )

            # 字段配置验证
            config_validation = await self._validate_field_config(
                normalized_value, field_config
            )
            validation_result.error_messages.extend(config_validation.get("errors", []))
            validation_result.warning_messages.extend(
                config_validation.get("warnings", [])
            )

            # 重新计算置信度
            if validation_result.validation_level == ValidationLevel.ERROR:
                validation_result.confidence *= 0.5
            elif validation_result.validation_level == ValidationLevel.WARNING:
                validation_result.confidence *= 0.8

            return validation_result

        except Exception as e:
            logger.error(f"字段验证失败 {field_name}: {e}")
            return ValidationResult(
                field_name=field_name,
                original_value=str(field_value),
                normalized_value=field_value,
                validation_level=ValidationLevel.ERROR,
                confidence=0.0,
                error_messages=[f"验证过程中发生错误: {str(e)}"],
            )

    async def _validate_business_rules(
        self, contract_data: dict[str, Any], field_results: dict[str, ValidationResult]
    ) -> dict[str, Any]:
        """验证业务规则"""
        results = {}

        for rule_name, rule_func in self.business_rules.items():
            try:
                rule_result = await rule_func(contract_data, field_results)
                results[rule_name] = rule_result
            except Exception as e:
                logger.error(f"业务规则验证失败 {rule_name}: {e}")
                results[rule_name] = {
                    "status": "error",
                    "message": f"规则验证失败: {str(e)}",
                }

        return results

    def _normalize_field_value(self, value: Any, field_type: FieldType) -> Any:
        """标准化字段值"""
        if value is None:
            return None

        try:
            if field_type == FieldType.TEXT:
                return str(value).strip()
            elif field_type == FieldType.NUMBER:
                return float(str(value).replace(",", ""))
            elif field_type == FieldType.DECIMAL:
                return Decimal(str(value).replace(",", ""))
            elif field_type == FieldType.DATE:
                return self._parse_date(value)
            elif field_type == FieldType.BOOLEAN:
                if isinstance(value, bool):
                    return value
                str_val = str(value).lower()
                return str_val in ["true", "1", "是", "有", "yes"]
            else:
                return str(value).strip()

        except (ValueError, InvalidOperation):
            return value

    async def _validate_text(
        self, value: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """验证文本字段"""
        result = {
            "level": ValidationLevel.SUCCESS,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # 长度检查
        min_length = config.get("min_length", 0)
        max_length = config.get("max_length", 1000)

        if len(value) < min_length:
            result["level"] = ValidationLevel.ERROR
            result["errors"].append(f"文本长度不能少于{min_length}个字符")
        elif len(value) > max_length:
            result["level"] = ValidationLevel.WARNING
            result["warnings"].append(f"文本长度超过{max_length}个字符，可能影响显示")

        # 格式检查
        pattern = config.get("pattern")
        if pattern and not re.match(pattern, value):
            result["level"] = ValidationLevel.ERROR
            result["errors"].append("文本格式不符合要求")
            result["suggestions"].append("请检查文本格式是否正确")

        # 必填检查
        if config.get("required", False) and not value.strip():
            result["level"] = ValidationLevel.ERROR
            result["errors"].append("此字段为必填项")

        return result

    async def _validate_number(
        self, value: int | float, config: dict[str, Any]
    ) -> dict[str, Any]:
        """验证数字字段"""
        result = {
            "level": ValidationLevel.SUCCESS,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        if not isinstance(value, (int, float)):
            result["level"] = ValidationLevel.ERROR
            result["errors"].append("请输入有效的数字")
            return result

        # 范围检查
        min_value = config.get("min_value")
        max_value = config.get("max_value")

        if min_value is not None and value < min_value:
            result["level"] = ValidationLevel.ERROR
            result["errors"].append(f"数值不能小于{min_value}")
        elif max_value is not None and value > max_value:
            result["level"] = ValidationLevel.ERROR
            result["errors"].append(f"数值不能大于{max_value}")

        # 必填检查
        if config.get("required", False) and value is None:
            result["level"] = ValidationLevel.ERROR
            result["errors"].append("此字段为必填项")

        return result

    async def _validate_decimal(
        self, value: Decimal | float | str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """验证小数字段"""
        result = {
            "level": ValidationLevel.SUCCESS,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        try:
            if not isinstance(value, Decimal):
                value = Decimal(str(value))
        except (ValueError, InvalidOperation):
            result["level"] = ValidationLevel.ERROR
            result["errors"].append("请输入有效的小数")
            return result

        # 范围检查
        min_value = config.get("min_value")
        max_value = config.get("max_value")

        if min_value is not None and value < Decimal(str(min_value)):
            result["level"] = ValidationLevel.ERROR
            result["errors"].append(f"数值不能小于{min_value}")
        elif max_value is not None and value > Decimal(str(max_value)):
            result["level"] = ValidationLevel.ERROR
            result["errors"].append(f"数值不能大于{max_value}")

        # 小数位检查
        if value.as_tuple().exponent < -2:
            result["level"] = ValidationLevel.WARNING
            result["warnings"].append("建议保留两位小数")

        return result

    async def _validate_date(
        self, value: Any, config: dict[str, Any]
    ) -> dict[str, Any]:
        """验证日期字段"""
        result = {
            "level": ValidationLevel.SUCCESS,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        if isinstance(value, str):
            parsed_date = self._parse_date(value)
        elif isinstance(value, datetime):
            parsed_date = value
        else:
            result["level"] = ValidationLevel.ERROR
            result["errors"].append("请输入有效的日期")
            return result

        if not parsed_date:
            result["level"] = ValidationLevel.ERROR
            result["errors"].append("日期格式不正确")
            result["suggestions"].append("请使用YYYY-MM-DD格式")
            return result

        # 日期合理性检查
        if parsed_date.year < 1900 or parsed_date.year > 2100:
            result["level"] = ValidationLevel.WARNING
            result["warnings"].append("日期年份可能不正确")

        # 必填检查
        if config.get("required", False) and not parsed_date:
            result["level"] = ValidationLevel.ERROR
            result["errors"].append("此字段为必填项")

        return result

    async def _validate_phone(
        self, value: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """验证电话号码字段"""
        result = {
            "level": ValidationLevel.SUCCESS,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        if not isinstance(value, str):
            value = str(value)

        # 移除所有非数字字符
        digits = re.sub(r"[^\d]", "", value)

        # 长度检查
        if len(digits) == 11 and digits.startswith("1"):
            # 手机号验证
            if not re.match(r"^1[3-9]\d{9}$", digits):
                result["level"] = ValidationLevel.ERROR
                result["errors"].append("手机号码格式不正确")
        elif len(digits) in [10, 11, 12]:
            # 座机号码验证
            area_code = digits[:3] if len(digits) >= 10 else digits[:4]
            if not re.match(r"^0[1-9]\d{1,2}$", area_code):
                result["level"] = ValidationLevel.WARNING
                result["warnings"].append("座机区号可能不正确")
        else:
            result["level"] = ValidationLevel.ERROR
            result["errors"].append("电话号码长度不正确")
            result["suggestions"].append("手机号应为11位，座机号应包含区号")

        return result

    async def _validate_address(
        self, value: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """验证地址字段"""
        result = {
            "level": ValidationLevel.SUCCESS,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        if not isinstance(value, str):
            value = str(value)

        # 基础检查
        if len(value) < 5:
            result["level"] = ValidationLevel.WARNING
            result["warnings"].append("地址信息过短")
            result["suggestions"].append("请提供详细的地址信息")
        elif len(value) > 200:
            result["level"] = ValidationLevel.WARNING
            result["warnings"].append("地址信息过长")

        # 中文地址检查
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", value))
        if chinese_chars / len(value) < 0.5:
            result["level"] = ValidationLevel.WARNING
            result["warnings"].append("地址中中文字符较少，请检查是否正确")

        # 地址结构检查
        if not any(
            keyword in value
            for keyword in ["省", "市", "区", "县", "镇", "街道", "路", "号"]
        ):
            result["level"] = ValidationLevel.WARNING
            result["suggestions"].append("建议包含完整的地址信息（省市区街道门牌号）")

        return result

    async def _validate_person_name(
        self, value: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """验证姓名字段"""
        result = {
            "level": ValidationLevel.SUCCESS,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        if not isinstance(value, str):
            value = str(value)

        # 长度检查
        if len(value) < 2:
            result["level"] = ValidationLevel.ERROR
            result["errors"].append("姓名长度不能少于2个字符")
        elif len(value) > 10:
            result["level"] = ValidationLevel.WARNING
            result["warnings"].append("姓名过长，请检查是否正确")

        # 中文姓名检查
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", value))
        if chinese_chars == 0:
            result["level"] = ValidationLevel.WARNING
            result["warnings"].append("未检测到中文字符，请确认姓名是否正确")
        elif chinese_chars / len(value) < 0.7:
            result["level"] = ValidationLevel.WARNING
            result["warnings"].append("姓名中非中文字符较多")

        # 姓名格式检查
        if re.search(r"[0-9@#$%^&*()]", value):
            result["level"] = ValidationLevel.ERROR
            result["errors"].append("姓名包含特殊字符")

        return result

    async def _validate_id_card(
        self, value: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """验证身份证字段"""
        result = {
            "level": ValidationLevel.SUCCESS,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        if not isinstance(value, str):
            value = str(value)

        # 长度检查
        if len(value) not in [15, 18]:
            result["level"] = ValidationLevel.ERROR
            result["errors"].append("身份证号码长度不正确（应为15位或18位）")
            return result

        # 格式检查
        if len(value) == 18:
            # 18位身份证验证
            if not re.match(
                r"^[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$",
                value,
            ):
                result["level"] = ValidationLevel.ERROR
                result["errors"].append("18位身份证号码格式不正确")
            else:
                # 校验码验证
                if not self._validate_id_card_checksum(value):
                    result["level"] = ValidationLevel.ERROR
                    result["errors"].append("身份证号码校验码错误")
        else:
            # 15位身份证验证
            if not re.match(
                r"^[1-9]\d{5}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}$", value
            ):
                result["level"] = ValidationLevel.ERROR
                result["errors"].append("15位身份证号码格式不正确")

        return result

    async def _validate_email(
        self, value: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """验证邮箱字段"""
        result = {
            "level": ValidationLevel.SUCCESS,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        if not isinstance(value, str):
            value = str(value)

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, value):
            result["level"] = ValidationLevel.ERROR
            result["errors"].append("邮箱格式不正确")
            result["suggestions"].append("请使用标准邮箱格式，如：example@domain.com")

        return result

    async def _validate_enum(
        self, value: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """验证枚举字段"""
        result = {
            "level": ValidationLevel.SUCCESS,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        if not isinstance(value, str):
            value = str(value)

        enum_values = config.get("enum_values", [])
        if enum_values and value not in enum_values:
            result["level"] = ValidationLevel.ERROR
            result["errors"].append(f"请选择有效的值：{', '.join(enum_values)}")
            result["suggestions"].append(f"可选值：{', '.join(enum_values)}")

        return result

    async def _validate_organization(
        self, value: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """验证机构名称字段"""
        result = {
            "level": ValidationLevel.SUCCESS,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        if not isinstance(value, str):
            value = str(value)

        # 长度检查
        if len(value) < 2:
            result["level"] = ValidationLevel.ERROR
            result["errors"].append("机构名称过短")
        elif len(value) > 100:
            result["level"] = ValidationLevel.WARNING
            result["warnings"].append("机构名称过长")

        # 机构后缀检查
        company_suffixes = [
            "公司",
            "有限",
            "股份",
            "集团",
            "企业",
            "工厂",
            "店",
            "中心",
        ]
        if not any(suffix in value for suffix in company_suffixes):
            result["level"] = ValidationLevel.WARNING
            result["warnings"].append("机构名称可能不完整")

        return result

    async def _validate_url(self, value: str, config: dict[str, Any]) -> dict[str, Any]:
        """验证URL字段"""
        result = {
            "level": ValidationLevel.SUCCESS,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        if not isinstance(value, str):
            value = str(value)

        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        if not re.match(url_pattern, value):
            result["level"] = ValidationLevel.ERROR
            result["errors"].append("URL格式不正确")
            result["suggestions"].append("请输入完整的URL，如：https://www.example.com")

        return result

    async def _validate_boolean(
        self, value: Any, config: dict[str, Any]
    ) -> dict[str, Any]:
        """验证布尔字段"""
        result = {
            "level": ValidationLevel.SUCCESS,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        if not isinstance(value, bool):
            str_value = str(value).lower()
            if str_value not in [
                "true",
                "false",
                "1",
                "0",
                "yes",
                "no",
                "是",
                "否",
                "有",
                "无",
            ]:
                result["level"] = ValidationLevel.ERROR
                result["errors"].append("请输入有效的布尔值")
                result["suggestions"].append("可选值：true/false, 1/0, yes/no, 是/否")

        return result

    async def _validate_field_config(
        self, value: Any, config: dict[str, Any]
    ) -> dict[str, Any]:
        """验证字段配置"""
        result = {"errors": [], "warnings": []}

        # 必填检查
        if config.get("required", False) and (value is None or value == ""):
            result["errors"].append("此字段为必填项")

        return result

    def _parse_date(self, date_str: str) -> datetime | None:
        """解析日期字符串"""
        if not date_str or date_str == "":
            return None

        date_formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y年%m月%d日",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    def _validate_id_card_checksum(self, id_card: str) -> bool:
        """验证身份证校验码"""
        if len(id_card) != 18:
            return False

        # 权重
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        # 校验码对应
        checksum_map = ["1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2"]

        try:
            total = 0
            for i in range(17):
                total += int(id_card[i]) * weights[i]

            checksum = checksum_map[total % 11]
            return id_card[17].upper() == checksum
        except (ValueError, IndexError):
            return False

    def _calculate_context_relevance(
        self, field_name: str, field_value: Any, contract_text: str | None
    ) -> float:
        """计算上下文相关性"""
        if not contract_text:
            return 0.5

        relevance_score = 0.0

        # 字段名相关性
        field_synonyms = self._get_field_synonyms(field_name)
        for synonym in field_synonyms:
            if synonym in contract_text:
                relevance_score += 0.3

        # 字段值相关性
        if isinstance(field_value, str):
            value_words = jieba.cut(field_value)
            contract_words = jieba.cut(contract_text)

            # 计算词重叠度
            value_word_set = set(value_words)
            contract_word_set = set(contract_words)

            if value_word_set and contract_word_set:
                overlap = len(value_word_set & contract_word_set)
                relevance_score += overlap / len(value_word_set) * 0.4

        # 位置相关性
        field_position = contract_text.find(str(field_value))
        if field_position != -1:
            # 字段值在合同中的位置越靠前，相关性越高
            position_score = 1.0 - (field_position / len(contract_text))
            relevance_score += position_score * 0.3

        return min(relevance_score, 1.0)

    def _get_field_synonyms(self, field_name: str) -> list[str]:
        """获取字段同义词"""
        synonym_map = {
            "party_a_name": ["甲方", "出租方", "房东"],
            "party_b_name": ["乙方", "承租方", "租客"],
            "monthly_rent": ["租金", "月租金", "房租"],
            "property_address": ["地址", "房屋地址", "租赁物地址"],
            "signing_date": ["签署日期", "签订日期", "签约日期"],
            "effective_date": ["生效日期", "开始日期"],
            "expiry_date": ["到期日期", "结束日期", "终止日期"],
        }
        return synonym_map.get(field_name, [field_name])

    async def _extract_entities_from_field(
        self, field_value: Any, field_type: FieldType
    ) -> dict[str, Any]:
        """从字段中提取实体"""
        entities = {}

        if not isinstance(field_value, str):
            field_value = str(field_value)

        if field_type == FieldType.ADDRESS:
            entities = self._extract_address_entities(field_value)
        elif field_type == FieldType.PERSON_NAME:
            entities = self._extract_name_entities(field_value)
        elif field_type == FieldType.PHONE:
            entities = self._extract_phone_entities(field_value)
        elif field_type == FieldType.DECIMAL:
            entities = self._extract_amount_entities(field_value)
        elif field_type == FieldType.DATE:
            entities = self._extract_date_entities(field_value)

        return entities

    def _extract_address_entities(self, address: str) -> dict[str, Any]:
        """提取地址实体"""
        entities = {}

        # 省份
        province_pattern = r"(北京|天津|上海|重庆|河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|海南|四川|贵州|云南|陕西|甘肃|青海|台湾|内蒙古|广西|西藏|宁夏|新疆|香港|澳门)"
        province_match = re.search(province_pattern, address)
        if province_match:
            entities["province"] = province_match.group(1)

        # 城市
        city_pattern = r"([^省]+市|[^自治区]+市)"
        city_match = re.search(city_pattern, address)
        if city_match:
            entities["city"] = city_match.group(1)

        # 区县
        district_pattern = r"([^市]+区|[^市]+县)"
        district_match = re.search(district_pattern, address)
        if district_match:
            entities["district"] = district_match.group(1)

        # 街道
        street_pattern = r"([^区县]+[街道路巷弄里])"
        street_match = re.search(street_pattern, address)
        if street_match:
            entities["street"] = street_match.group(1)

        # 门牌号
        number_pattern = r"(\d+号)"
        number_match = re.search(number_pattern, address)
        if number_match:
            entities["number"] = number_match.group(1)

        return entities

    def _extract_name_entities(self, name: str) -> dict[str, Any]:
        """提取姓名实体"""
        entities = {}

        # 姓氏
        common_surnames = ["王", "李", "张", "刘", "陈", "杨", "黄", "赵", "周", "吴"]
        if name and name[0] in common_surnames:
            entities["surname"] = name[0]
            entities["given_name"] = name[1:]

        # 姓名长度
        entities["length"] = len(name)

        return entities

    def _extract_phone_entities(self, phone: str) -> dict[str, Any]:
        """提取电话实体"""
        entities = {}

        # 提取数字
        digits = re.sub(r"[^\d]", "", phone)
        entities["digits"] = digits

        # 类型判断
        if len(digits) == 11 and digits.startswith("1"):
            entities["type"] = "mobile"
        else:
            entities["type"] = "landline"

        return entities

    def _extract_amount_entities(self, amount: str) -> dict[str, Any]:
        """提取金额实体"""
        entities = {}

        try:
            # 提取数字
            number_match = re.search(r"(\d+(?:\.\d+)?)", amount)
            if number_match:
                entities["numeric_value"] = float(number_match.group(1))

            # 货币单位
            if "元" in amount:
                entities["currency_unit"] = "CNY"
            elif "万" in amount:
                entities["currency_unit"] = "WAN"

            # 大写金额检查
            if re.search(r"[零一二三四五六七八九十百千万亿]", amount):
                entities["is_chinese_numerals"] = True

        except (ValueError, AttributeError):
            pass

        return entities

    def _extract_date_entities(self, date_str: str) -> dict[str, Any]:
        """提取日期实体"""
        entities = {}

        try:
            parsed_date = self._parse_date(date_str)
            if parsed_date:
                entities["year"] = parsed_date.year
                entities["month"] = parsed_date.month
                entities["day"] = parsed_date.day
                entities["weekday"] = parsed_date.weekday()

            # 日期格式
            if re.search(r"\d{4}年\d{1,2}月\d{1,2}日", date_str):
                entities["format"] = "chinese"
            elif re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", date_str):
                entities["format"] = "standard"

        except (ValueError, AttributeError):
            pass

        return entities

    def _analyze_field_relationships(
        self, field_name: str, field_value: Any, contract_text: str | None
    ) -> dict[str, Any][str, str]:
        """分析字段关系"""
        relationships = {}

        related_fields = self.field_relationships.get(field_name, [])
        for related_field in related_fields:
            relationships[related_field] = "related"

        return relationships

    def _calculate_semantic_confidence(
        self, field_name: str, field_value: Any, entities: dict[str, Any]
    ) -> float:
        """计算语义置信度"""
        base_confidence = 0.7

        # 实体提取完整性加分
        if entities:
            entity_completeness = len(entities) / 3.0  # 假设期望3个实体
            base_confidence += entity_completeness * 0.2

        # 字段值长度合理性
        if isinstance(field_value, str):
            length_score = 1.0
            if len(field_value) < 2:
                length_score = 0.5
            elif len(field_value) > 100:
                length_score = 0.8
            base_confidence += length_score * 0.1

        return min(base_confidence, 1.0)

    # 业务规则验证方法
    async def _check_date_consistency(
        self, contract_data: dict[str, Any], field_results: dict[str, ValidationResult]
    ) -> dict[str, Any]:
        """检查日期一致性"""
        result = {"status": "pass", "message": ""}

        signing_date = contract_data.get("signing_date")
        effective_date = contract_data.get("effective_date")
        expiry_date = contract_data.get("expiry_date")

        # 检查逻辑关系
        if signing_date and effective_date and signing_date > effective_date:
            result = {
                "status": "error",
                "message": "生效日期不能早于签署日期",
                "fields": ["signing_date", "effective_date"],
            }

        if effective_date and expiry_date and effective_date >= expiry_date:
            result = {
                "status": "error",
                "message": "到期日期必须晚于生效日期",
                "fields": ["effective_date", "expiry_date"],
            }

        return result

    async def _check_amount_reasonableness(
        self, contract_data: dict[str, Any], field_results: dict[str, ValidationResult]
    ) -> dict[str, Any]:
        """检查金额合理性"""
        result = {"status": "pass", "message": ""}

        monthly_rent = contract_data.get("monthly_rent")
        deposit_amount = contract_data.get("deposit_amount")
        property_area = contract_data.get("property_area")

        try:
            if monthly_rent and property_area:
                rent_per_sqm = float(monthly_rent) / float(property_area)
                # 租金合理性检查（1-1000元/平方米）
                if rent_per_sqm > 1000:
                    result = {
                        "status": "warning",
                        "message": f"单位面积租金较高（{rent_per_sqm:.2f}元/平方米），请确认",
                        "fields": ["monthly_rent", "property_area"],
                    }
                elif rent_per_sqm < 1:
                    result = {
                        "status": "warning",
                        "message": "单位面积租金过低，请确认是否正确",
                        "fields": ["monthly_rent", "property_area"],
                    }

            if monthly_rent and deposit_amount:
                # 押金合理性检查（通常为1-3个月租金）
                deposit_months = float(deposit_amount) / float(monthly_rent)
                if deposit_months > 6:
                    result = {
                        "status": "warning",
                        "message": f"押金金额较高（相当于{deposit_months:.1f}个月租金）",
                        "fields": ["monthly_rent", "deposit_amount"],
                    }

        except (ValueError, TypeError, ZeroDivisionError):
            result = {"status": "error", "message": "金额计算错误"}

        return result

    async def _check_party_completeness(
        self, contract_data: dict[str, Any], field_results: dict[str, ValidationResult]
    ) -> dict[str, Any]:
        """检查当事方完整性"""
        result = {"status": "pass", "message": ""}

        # 检查甲方完整性
        party_a_fields = [
            "party_a_name",
            "party_a_id",
            "party_a_phone",
            "party_a_address",
        ]
        party_a_complete = all(contract_data.get(field) for field in party_a_fields)

        # 检查乙方完整性
        party_b_fields = [
            "party_b_name",
            "party_b_id",
            "party_b_phone",
            "party_b_address",
        ]
        party_b_complete = all(contract_data.get(field) for field in party_b_fields)

        if not party_a_complete:
            result = {
                "status": "warning",
                "message": "甲方信息不完整，建议补充完整信息",
                "fields": party_a_fields,
            }

        if not party_b_complete:
            result = {
                "status": "warning",
                "message": "乙方信息不完整，建议补充完整信息",
                "fields": party_b_fields,
            }

        return result

    async def _check_address_validity(
        self, contract_data: dict[str, Any], field_results: dict[str, ValidationResult]
    ) -> dict[str, Any]:
        """检查地址有效性"""
        result = {"status": "pass", "message": ""}

        party_a_address = contract_data.get("party_a_address")
        party_b_address = contract_data.get("party_b_address")
        property_address = contract_data.get("property_address")

        # 检查地址重复
        addresses = [
            addr
            for addr in [party_a_address, party_b_address, property_address]
            if addr
        ]
        if len(set(addresses)) < len(addresses):
            result = {
                "status": "warning",
                "message": "检测到重复地址，请确认是否正确",
                "fields": ["party_a_address", "party_b_address", "property_address"],
            }

        return result

    async def _check_term_consistency(
        self, contract_data: dict[str, Any], field_results: dict[str, ValidationResult]
    ) -> dict[str, Any]:
        """检查期限一致性"""
        result = {"status": "pass", "message": ""}

        effective_date = contract_data.get("effective_date")
        expiry_date = contract_data.get("expiry_date")
        lease_term = contract_data.get("lease_term")

        try:
            if effective_date and expiry_date and lease_term:
                # 计算日期差异
                if isinstance(effective_date, str):
                    effective_date = self._parse_date(effective_date)
                if isinstance(expiry_date, str):
                    expiry_date = self._parse_date(expiry_date)

                if effective_date and expiry_date:
                    actual_months = (expiry_date.year - effective_date.year) * 12 + (
                        expiry_date.month - effective_date.month
                    )

                    if abs(actual_months - int(lease_term)) > 1:
                        result = {
                            "status": "warning",
                            "message": f"租赁期限({lease_term}个月)与日期计算结果({actual_months}个月)不符",
                            "fields": ["lease_term", "effective_date", "expiry_date"],
                        }

        except (ValueError, TypeError, AttributeError):
            result = {"status": "error", "message": "期限计算错误"}

        return result

    async def _check_payment_logic(
        self, contract_data: dict[str, Any], field_results: dict[str, ValidationResult]
    ) -> dict[str, Any]:
        """检查付款逻辑"""
        result = {"status": "pass", "message": ""}

        payment_method = contract_data.get("payment_method")
        monthly_rent = contract_data.get("monthly_rent")

        # 检查付款方式与金额的一致性
        if payment_method == "年付" and monthly_rent:
            try:
                annual_rent = float(monthly_rent) * 12
                if annual_rent > 1000000:  # 100万以上
                    result = {
                        "status": "warning",
                        "message": "年付金额较大，请确认付款方式",
                        "fields": ["payment_method", "monthly_rent"],
                    }
            except (ValueError, TypeError):
                pass

        return result

    async def _check_id_card_validity(
        self, contract_data: dict[str, Any], field_results: dict[str, ValidationResult]
    ) -> dict[str, Any]:
        """检查身份证有效性"""
        result = {"status": "pass", "message": ""}

        party_a_id = contract_data.get("party_a_id")
        party_b_id = contract_data.get("party_b_id")

        # 检查身份证重复
        if party_a_id and party_b_id and party_a_id == party_b_id:
            result = {
                "status": "error",
                "message": "甲乙双方身份证号码相同，请确认",
                "fields": ["party_a_id", "party_b_id"],
            }

        return result

    def _calculate_overall_confidence(
        self, field_results: dict[str, ValidationResult]
    ) -> float:
        """计算总体置信度"""
        if not field_results:
            return 0.0

        confidences = [result.confidence for result in field_results.values()]
        return sum(confidences) / len(confidences)

    def _generate_summary_and_recommendations(
        self,
        field_results: dict[str, ValidationResult],
        business_validation_results: dict[str, Any],
        overall_confidence: float,
    ) -> tuple[str, list[str]]:
        """生成摘要和建议"""
        error_count = sum(
            1
            for r in field_results.values()
            if r.validation_level == ValidationLevel.ERROR
        )
        warning_count = sum(
            1
            for r in field_results.values()
            if r.validation_level == ValidationLevel.WARNING
        )

        # 生成摘要
        if overall_confidence >= 0.9:
            summary = "合同验证结果优秀，所有关键字段信息完整准确"
        elif overall_confidence >= 0.7:
            summary = "合同验证结果良好，大部分字段信息正确"
        elif overall_confidence >= 0.5:
            summary = "合同验证结果一般，存在部分问题需要修正"
        else:
            summary = "合同验证结果较差，存在较多问题需要重点检查"

        # 生成建议
        recommendations = []

        if error_count > 0:
            recommendations.append(f"有{error_count}个字段存在错误，必须修正后才能继续")

        if warning_count > 0:
            recommendations.append(
                f"有{warning_count}个字段需要关注，建议核实信息准确性"
            )

        # 基于业务规则的建议
        for rule_name, rule_result in business_validation_results.items():
            if rule_result.get("status") == "error":
                recommendations.append(
                    f"业务规则错误：{rule_result.get('message', '')}"
                )
            elif rule_result.get("status") == "warning":
                recommendations.append(f"业务建议：{rule_result.get('message', '')}")

        # 置信度相关建议
        if overall_confidence < 0.7:
            recommendations.append(
                "建议仔细检查所有字段的准确性，特别是关键日期和金额信息"
            )

        if not recommendations:
            recommendations.append("合同信息验证通过，可以继续后续处理")

        return summary, recommendations

    def _create_error_report(self, error_message: str) -> ContractValidationReport:
        """创建错误报告"""
        return ContractValidationReport(
            contract_id=None,
            total_fields=0,
            valid_fields=0,
            error_fields=0,
            warning_fields=0,
            overall_confidence=0.0,
            field_results={},
            semantic_analysis={},
            summary=f"验证过程中发生错误：{error_message}",
            recommendations=["请检查输入数据格式，重新提交验证"],
        )


# 全局合同语义验证器实例
contract_semantic_validator = ContractSemanticValidator()
