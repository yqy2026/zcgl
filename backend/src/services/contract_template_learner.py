"""
合同模板学习和匹配服务
通过机器学习识别标准合同格式和模板
"""

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import jieba
import numpy as np

logger = logging.getLogger(__name__)


class TemplateType(str, Enum):
    """模板类型"""

    PAYMENT_STRUCTURE = "payment_structure"  # 付款结构模板
    PARTY_INFO = "party_info"  # 当事人信息模板
    LEASE_TERMS = "lease_terms"  # 租赁条款模板
    TABLE_LAYOUT = "table_layout"  # 表格布局模板
    SIGNATURE_POSITION = "signature_position"  # 签名位置模板


class TemplateField:
    """模板字段"""

    field_name: str
    field_type: str  # text, number, date, address, etc.
    extraction_pattern: str  # 正则表达式
    validation_rules: dict[str, Any]  # 验证规则
    weight: float = 1.0
    required: bool = False


@dataclass
class ContractTemplate:
    """合同模板"""

    template_id: str
    template_name: str
    template_type: TemplateType
    fields: list[TemplateField]
    sample_texts: list[str]
    confidence_threshold: float
    created_at: str
    usage_count: int = 0
    success_count: int = 0


@dataclass
class TemplateMatch:
    """模板匹配结果"""

    template: ContractTemplate
    confidence: float
    matched_fields: dict[str, Any]
    unmatched_fields: list[str]
    score_breakdown: dict[str, float]


class ContractTemplateLearner:
    """合同模板学习器"""

    def __init__(self):
        self.templates: dict[str, ContractTemplate] = {}
        self.field_weights = {
            "contract_number": 2.0,
            "party_name": 2.0,
            "property_address": 2.0,
            "lease_amount": 2.0,
            "lease_dates": 2.0,
            "signature": 1.5,
            "contact_info": 1.5,
        }

        # 加载或初始化默认模板
        self._load_default_templates()

    def _load_default_templates(self):
        """加载默认合同模板"""
        try:
            # 付款结构模板
            payment_template = ContractTemplate(
                template_id="payment_2024",
                template_name="标准付款结构模板",
                template_type=TemplateType.PAYMENT_STRUCTURE,
                fields=[
                    TemplateField(
                        field_name="payment_method",
                        field_type="text",
                        extraction_pattern=r"(?:支付|付款|缴纳)(?:方式|方法)",
                        validation_rules={
                            "options": ["现金", "银行转账", "支票"],
                            "required": True,
                        },
                        weight=1.0,
                    ),
                    TemplateField(
                        field_name="payment_schedule",
                        field_type="text",
                        extraction_pattern=r"(?:第\d+期|期数)",
                        validation_rules={
                            "min_length": 3,
                            "max_length": 6,
                            "required": True,
                        },
                        weight=0.8,
                    ),
                    TemplateField(
                        field_name="amount",
                        field_type="number",
                        extraction_pattern=r"(\d+(?:\.\d+)?)\s*(?:元|人民币)",
                        validation_rules={
                            "min_value": 0,
                            "max_value": 1000000,
                            "required": True,
                        },
                        weight=1.0,
                    ),
                ],
                sample_texts=[
                    "第1期：通过银行转账支付租金5000.00元",
                    "第2期：支票支付2500.00元",
                    "支付方式：银行转账、支票",
                ],
            )

            # 当事人信息模板
            party_template = ContractTemplate(
                template_id="party_2024",
                template_name="标准当事方信息模板",
                template_type=TemplateType.PARTY_INFO,
                fields=[
                    TemplateField(
                        field_name="party_type",
                        field_type="text",
                        extraction_pattern=r"(?:甲|乙)(?:方|侧)",
                        validation_rules={
                            "options": ["出租方", "承租方", "买方", "卖方"],
                            "required": True,
                        },
                        weight=1.0,
                    ),
                    TemplateField(
                        field_name="party_name",
                        field_type="text",
                        extraction_pattern=r"(?:姓名|名称|公司名称)[：:]([^\n\r，。]{2,20})",
                        validation_rules={
                            "min_length": 2,
                            "max_length": 50,
                            "chinese_name": True,
                        },
                        weight=2.0,
                    ),
                    TemplateField(
                        field_name="contact_info",
                        field_type="text",
                        extraction_pattern=r"(?:联系|电话)(?:方式|号码)",
                        validation_rules={"phone_format": True, "required": True},
                        weight=1.5,
                    ),
                    TemplateField(
                        field_name="id_number",
                        field_type="text",
                        extraction_pattern=r"(?:证件|身份)(?:号|号码)[：:]([0-9Xx]{15,18})",
                        validation_rules={"id_format": True, "required": False},
                        weight=1.0,
                    ),
                ],
                sample_texts=[
                    "甲方：北京物业管理有限公司\n乙方：张三\n联系电话：13800138000",
                    "联系人：李四\n身份证号：110101199001012345",
                    "法定代表人：王五",
                ],
            )

            # 租赁条款模板
            lease_template = ContractTemplate(
                template_id="lease_2024",
                template_name="标准租赁条款模板",
                template_type=TemplateType.LEASE_TERMS,
                fields=[
                    TemplateField(
                        field_name="lease_period",
                        field_type="text",
                        extraction_pattern=r"租赁期限[：:]([^\n\r，。]+?)(?:\d+\s*年|年)",
                        validation_rules={
                            "min_years": 1,
                            "max_years": 20,
                            "required": True,
                        },
                        weight=1.0,
                    ),
                    TemplateField(
                        field_name="start_date",
                        field_type="date",
                        extraction_pattern=r"(?:自|从)(\d{4})年(\d{1,2})\s*月(\d{1,2})\s*日)起",
                        validation_rules={"recent_date": True, "required": True},
                        weight=0.9,
                    ),
                    TemplateField(
                        field_name="end_date",
                        field_type="date",
                        extraction_pattern=r"(?:至|到)(\d{4})年(\d{1,2})\s*月(\d{1,2})\s*日)止",
                        validation_rules={"end_after_start": True, "required": True},
                        weight=0.9,
                    ),
                    TemplateField(
                        field_name="rent_amount",
                        field_type="number",
                        extraction_pattern=r"(?:月租金|租金|费用)[为：:]([^\n\r，。]*\d+(?:\.\d+)?\s*(?:元|人民币))",
                        validation_rules={
                            "positive": True,
                            "min_value": 0,
                            "required": True,
                        },
                        weight=1.5,
                    ),
                    TemplateField(
                        field_name="payment_frequency",
                        field_type="text",
                        extraction_pattern=r"(?:支付|缴纳)(?:周期|频率)",
                        validation_rules={
                            "options": ["月", "季", "半年", "年", "一次性"],
                            "required": True,
                        },
                        weight=0.7,
                    ),
                ],
                sample_texts=[
                    "租赁期限：3年",
                    "自2024年1月1日起至2027年1月31日止",
                    "月租金：5000元",
                    "支付方式：按季度支付",
                    "付款周期：每季度一次",
                ],
            )

            self.templates = {
                "payment_2024": payment_template,
                "party_2024": party_template,
                "lease_2024": lease_template,
            }

            logger.info(f"已加载{len(self.templates)}个默认合同模板")

        except Exception as e:
            logger.error(f"加载默认模板失败: {e}")

    async def learn_from_contracts(
        self, contract_texts: list[str], feedback_scores: list[float] | None = None
    ) -> bool:
        """从合同文本中学习模板"""
        try:
            # 分析合同文本中的关键字段
            all_patterns = self._discover_patterns(contract_texts)

            # 基于模式频率和重要性创建模板
            new_templates = self._create_templates_from_patterns(
                all_patterns, feedback_scores
            )

            # 更新模板
            for template in new_templates:
                self.templates[template.template_id] = template

            logger.info(f"成功学习{len(new_templates)}个新模板")
            return True

        except Exception as e:
            logger.error(f"模板学习失败: {e}")
            return False

    def _discover_patterns(self, contract_texts: list[str]) -> dict[str, Any]:
        """发现合同文本中的模式"""
        try:
            patterns = {
                "payment_structure": defaultdict(list),
                "party_info": defaultdict(list),
                "lease_terms": defaultdict(list),
                "table_layout": defaultdict(list),
                "signature_position": defaultdict(list),
            }

            for text in contract_texts:
                # 使用jieba分词和词性标注
                words = jieba.cut(text, HMM=True)
                pos_tags = jieba.posseg.cut(text, HMM=True)

                # 分析每个词
                for word, pos in zip(words, pos_tags):
                    if len(word.strip()) > 1:
                        # 付款相关模式
                        if pos.startswith("v") and any(
                            keyword in word
                            for keyword in ["支付", "付款", "缴纳", "期数", "金额"]
                        ):
                            patterns["payment_structure"][word].append(
                                {
                                    "word": word,
                                    "pos": pos,
                                    "context": self._get_context_word(
                                        word, words, pos_tags, i
                                    ),
                                }
                            )

                        # 当事人相关模式
                        elif any(
                            keyword in word
                            for keyword in [
                                "甲方",
                                "乙方",
                                "出租",
                                "承租",
                                "公司",
                                "法定代表人",
                            ]
                        ):
                            patterns["party_info"][word].append(
                                {
                                    "word": word,
                                    "pos": pos,
                                    "context": self._get_context_word(
                                        word, words, pos_tags, i
                                    ),
                                }
                            )

                        # 租赁条款相关模式
                        elif any(
                            keyword in word
                            for keyword in [
                                "租赁",
                                "期限",
                                "租金",
                                "面积",
                                "用途",
                                "违约",
                                "起",
                                "止",
                            ]
                        ):
                            patterns["lease_terms"][word].append(
                                {
                                    "word": word,
                                    "pos": pos,
                                    "context": self._get_context_word(
                                        word, words, pos_tags, i
                                    ),
                                }
                            )

            return dict(patterns)

        except Exception as e:
            logger.error(f"模式发现失败: {e}")
            return {}

    def _create_templates_from_patterns(
        self, patterns: dict[str, Any], feedback_scores: list[float] | None = None
    ) -> list[ContractTemplate]:
        """从模式中创建模板"""
        new_templates = []

        for template_type, pattern_data in patterns.items():
            if not pattern_data:
                continue

            try:
                # 计算模式重要性
                pattern_importance = self._calculate_pattern_importance(
                    pattern_data, feedback_scores
                )

                if pattern_importance < 0.1:
                    continue  # 忽略不太重要的模式

                # 分析模式并提取字段
                template_fields = self._analyze_pattern_for_fields(pattern_data)

                if not template_fields:
                    continue

                # 生成模板ID和名称
                template_id = (
                    f"{template_type}_auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                template_name = f"自动生成{self._get_template_type_name(template_type)}"

                # 创建模板
                template = ContractTemplate(
                    template_id=template_id,
                    template_name=template_name,
                    template_type=TemplateType(template_type),
                    fields=template_fields,
                    confidence_threshold=self._calculate_confidence_threshold(
                        pattern_importance
                    ),
                    sample_texts=pattern_data["sample_texts"][:3],  # 使用前3个样本
                    created_at=datetime.now().isoformat(),
                    usage_count=0,
                    success_count=0,
                )

                new_templates.append(template)

            except Exception as e:
                logger.error(f"生成模板失败: {e}")
                continue

        return new_templates

    def _analyze_pattern_for_fields(
        self, pattern_data: dict[str, Any]
    ) -> list[TemplateField]:
        """分析模式以提取字段"""
        template_fields = []

        # 常见的合同字段模式
        field_patterns = {
            "contract_number": [
                (r"合同编号[：:]", "text"),
                (r"合同号[：:]", "text"),
                (r"第\d+号", "text"),
            ],
            "party_name": [
                (r"(?:甲|乙)(?:方|侧)[：:]", "text"),
                (r"(?=|名|名称)[：:]", "text"),
                (r"公司(?:有限公司|股份|责任)", "text"),
            ],
            "id_number": [
                (r"(?:身份|证件)(?:号|号码)[：:]", "text"),
                (r"[0-9Xx]{15,18}", "text"),
            ],
            "property_address": [
                (r"(?=地址|位于|房屋地址)[：:]", "text"),
                (r"[^\n\r，。]+?(?:省|市|区|县|镇|街道|路|号)([^,。\n]{2,30})", "text"),
                (r"(\d+(?:\.\d+)?)\s*(?:平方米|㎡)", "text"),
            ],
            "lease_amount": [
                (r"(?:月租金|租金|费用)[为：:]", "number"),
                (r"(\d+(?:\.\d+)?)\s*(?:元|人民币)", "number"),
            ],
            "lease_dates": [
                (r"(?:自|从)(\d{4})年(\d{1,2})\s*月(\d{1,2})\s*日)起", "date"),
                (r"(?:至|到)(\d{4})年(\d{1,2})\s*月(\d{1,2})\s*日)止", "date"),
            ],
            "payment_method": [
                (r"(?:支付|付款)(?:方式|方法)", "text"),
                (r"(?:银行转账|现金|支票)", "text"),
            ],
        }

        # 从模式数据中提取字段
        for field_name, pattern_list in field_patterns.items():
            best_pattern = None
            max_frequency = 0

            for pattern in pattern_list:
                frequency = len(pattern_data["word_list"][pattern])
                if frequency > max_frequency:
                    max_frequency = frequency
                    best_pattern = pattern

            if best_pattern:
                template_fields.append(
                    TemplateField(
                        field_name=field_name,
                        field_type=self._get_field_type(field_name),
                        extraction_pattern=best_pattern[0],
                        validation_rules=self._get_field_validation_rules(field_name),
                        weight=self.field_weights.get(field_name, 1.0),
                        required=self._is_field_required(field_name),
                    )
                )

        return template_fields

    def _get_context_word(
        self, word: str, words: list[str], pos_tags: list[str], index: int
    ) -> str:
        """获取上下文词汇"""
        # 获取前后词汇
        context_words = []
        start_idx = max(0, index - 5)
        end_idx = min(len(words) - 1, index + 5)

        for i in range(start_idx, end_idx + 1):
            if 0 <= i < len(words) and len(words[i].strip()) > 1:
                context_words.append(words[i])

        return " ".join(context_words)

    def _get_field_type(self, field_name: str) -> str:
        """获取字段类型"""
        type_mapping = {
            "contract_number": "text",
            "party_name": "text",
            "id_number": "text",
            "property_address": "text",
            "lease_amount": "number",
            "lease_dates": "date",
            "payment_method": "text",
        }
        return type_mapping.get(field_name, "text")

    def _get_field_validation_rules(self, field_name: str) -> dict[str, Any]:
        """获取字段验证规则"""
        rules_mapping = {
            "contract_number": {
                "min_length": 3,
                "max_length": 50,
                "format": "alphanumeric",
                "unique": True,
            },
            "party_name": {
                "min_length": 2,
                "max_length": 50,
                "chinese_name": True,
                "company_suffix": True,
            },
            "id_number": {
                "min_length": 15,
                "max_length": 18,
                "format": "id_format",
                "checksum": True,
            },
            "property_address": {
                "min_length": 5,
                "max_length": 100,
                "contains_address_elements": True,
            },
            "lease_amount": {
                "positive": True,
                "min_value": 0,
                "max_value": 10000000,
                "required": True,
            },
            "lease_dates": {
                "date_order": True,
                "recent_date": True,
                "future_date": True,
            },
            "payment_method": {
                "options": ["现金", "银行转账", "支票", "微信", "支付宝"]
            },
        }
        return rules_mapping.get(field_name, {})

    def _is_field_required(self, field_name: str) -> bool:
        """判断字段是否必填"""
        required_fields = [
            "party_name",
            "property_address",
            "lease_amount",
            "lease_dates",
        ]
        return field_name in required_fields

    def _get_template_type_name(self, template_type: TemplateType) -> str:
        """获取模板类型名称"""
        name_mapping = {
            TemplateType.PAYMENT_STRUCTURE: "付款结构",
            TemplateType.PARTY_INFO: "当事方信息",
            TemplateType.LEASE_TERMS: "租赁条款",
            TemplateType.TABLE_LAYOUT: "表格布局",
            TemplateType.SIGNATURE_POSITION: "签名位置",
        }
        return name_mapping.get(template_type, "未知模板")

    def _calculate_pattern_importance(
        self, pattern_data: dict[str, Any], feedback_scores: list[float] | None
    ) -> float:
        """计算模式重要性"""
        base_importance = 0.1

        # 基于频率的重要性
        frequency = len(pattern_data["word_list"][pattern])
        frequency_score = min(frequency / 10.0, 1.0)

        # 基于字段类型的权重
        word_types = pattern_data.get("word_types", [])
        if word_types:
            type_scores = [
                self.field_weights.get(word_type, 0.5) for word_type in word_types
            ]
            type_score = max(type_scores)
            base_importance += type_score * 0.3

        # 基于反馈的调整
        if feedback_scores:
            feedback_score = np.mean(feedback_scores)
            base_importance += feedback_score * 0.2

        return min(base_importance + frequency_score + type_score, 1.0)

    def _calculate_confidence_threshold(self, importance: float) -> float:
        """计算置信度阈值"""
        # 重要性越高，阈值越严格
        base_threshold = 0.7
        adjustment = importance * 0.2
        return max(base_threshold + adjustment, 0.9)

    async def match_contract_to_templates(
        self, contract_text: str
    ) -> list[TemplateMatch]:
        """匹配合同到模板"""
        try:
            matches = []

            # 提取合同中的字段
            extracted_fields = self._extract_contract_fields(contract_text)

            # 与每个模板进行匹配
            for template_id, template in self.templates.items():
                match = await self._match_template_to_fields(extracted_fields, template)

                if match and match.confidence > 0.3:
                    matches.append(match)

            # 按置信度排序
            matches.sort(key=lambda x: x.confidence, reverse=True)

            return matches

        except Exception as e:
            logger.error(f"模板匹配失败: {e}")
            return []

    def _extract_contract_fields(self, contract_text: str) -> dict[str, Any]:
        """从合同文本中提取字段"""
        fields = {}

        # 使用模板提取字段
        for template in self.templates.values():
            for field in template.fields:
                value = self._extract_field_by_template(contract_text, field)
                if value:
                    fields[field.field_name] = value

        return fields

    def _extract_field_by_template(self, text: str, field: TemplateField) -> Any:
        """使用模板提取字段值"""
        try:
            match = re.search(field.extraction_pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()

                # 验证字段
                if self._validate_field_value(value, field):
                    return self._normalize_field_value(value, field.field_type)

                return None

            return None

        except Exception as e:
            logger.error(f"字段提取失败: {e}")
            return None

    def _validate_field_value(self, value: str, field_type: str) -> bool:
        """验证字段值有效性"""
        value = value.strip()

        if not value:
            return False

        # 根据字段类型进行验证
        if field.field_type == "text":
            return len(value) > 0

        elif field.field_type == "number":
            try:
                # 提取数字
                number = float(re.sub(r"[^\d.]", "", value))
                return (
                    field.validation_rules.get("min_value", 0)
                    <= number
                    <= field.validation_rules.get("max_value", 10000000)
                )
            except ValueError:
                return False

        elif field.field_type == "date":
            # 日期格式验证
            date_formats = ["%Y-%m-%d", "%Y年%m月%d日"]
            for fmt in date_formats:
                try:
                    datetime.strptime(value, fmt)
                    return True
                except ValueError:
                    continue

        elif field_type == "id_number":
            # 证件号格式验证
            return len(value) >= 15 and len(value) <= 18

        elif field.field_type == "phone":
            # 电话号码格式验证
            phone_pattern = r"^1[3-9]\d{9}$"
            return bool(re.match(phone_pattern, value))

        return True

    def _normalize_field_value(self, value: str, field_type: str) -> Any:
        """标准化字段值"""
        value = value.strip()

        if field_type == "number":
            # 提取数字并转换为整数
            try:
                number = float(re.sub(r"[^\d.]", "", value))
                return int(number)
            except ValueError:
                return value

        elif field_type == "date":
            # 标准化日期格式
            date_formats = ["%Y-%m-%d", "%Y年%m月%d日"]
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(value, fmt)
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    return value

        return value

        return value

    def save_template(self, template: ContractTemplate) -> bool:
        """保存模板"""
        try:
            template_data = {
                "template_id": template.template_id,
                "template_name": template.template_name,
                "template_type": template.template_type.value,
                "fields": [asdict(f) for f in template.fields],
                "confidence_threshold": template.confidence_threshold,
                "created_at": template.created_at,
                "usage_count": template.usage_count,
                "success_count": template.success_count,
            }

            template_file = f"templates/{template.template_id}.json"

            # 确保目录存在
            import os

            os.makedirs("templates", exist_ok=True)

            # 保存模板数据
            with open(template_file, "w", encoding="utf-8") as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2)

            logger.info(f"保存模板: {template.template_id}")
            return True

        except Exception as e:
            logger.error(f"保存模板失败: {e}")
            return False

    def load_templates(self):
        """加载所有模板"""
        try:
            template_files = glob.glob("templates/*.json")
            for file_path in template_files:
                with open(file_path, encoding="utf-8") as f:
                    template_data = json.load(f)
                    template = ContractTemplate(**template_data)
                    self.templates[template.template_id] = template
                    logger.info(f"加载模板: {template.template_id}")

            logger.info(f"总共加载了{len(self.templates)}个模板")

        except Exception as e:
            logger.error(f"加载模板失败: {e}")


# 全局模板学习器实例
contract_template_learner = ContractTemplateLearner()
