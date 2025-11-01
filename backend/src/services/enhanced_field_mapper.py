"""
增强字段映射和验证服务
专门处理合同信息到58字段资产模型的映射和验证
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# from .chinese_nlp_processor import ChineseNLPProcessor  # 暂时注释
# from .contract_semantic_validator import contract_semantic_validator  # 暂时注释

logger = logging.getLogger(__name__)


class MappingConfidence(Enum):
    """映射置信度"""

    HIGH = "high"  # 0.8+
    MEDIUM = "medium"  # 0.6-0.8
    LOW = "low"  # 0.4-0.6
    VERY_LOW = "very_low"  # <0.4


class ValidationStatus(Enum):
    """验证状态"""

    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    PENDING = "pending"


@dataclass
class FieldMapping:
    """字段映射"""

    source_field: str
    target_field: str
    value: Any
    confidence: float
    validation_status: ValidationStatus
    transformation_applied: str | None = None
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MappingResult:
    """映射结果"""

    success: bool
    mappings: dict[str, FieldMapping]
    overall_confidence: float
    asset_data: dict[str, Any]
    contract_data: dict[str, Any]
    validation_summary: dict[str, Any]
    recommendations: list[str] = field(default_factory=list)
    processing_time: float = 0.0


class EnhancedFieldMapper:
    """增强字段映射器"""

    def __init__(self):
        self.field_mapping_rules = self._load_field_mapping_rules()
        self.transformation_rules = self._load_transformation_rules()
        self.validation_rules = self._load_validation_rules()
        self.completeness_rules = self._load_completeness_rules()

    def _load_field_mapping_rules(self) -> dict[str, dict[str, Any]]:
        """加载字段映射规则"""
        return {
            # 基础信息映射
            "contract_number": {
                "target_fields": ["lease_contract_number"],
                "priority": 1,
                "required": True,
                "transformations": ["clean_contract_number"],
            },
            "landlord_name": {
                "target_fields": [],
                "priority": 1,
                "note": "房东信息不直接映射到资产字段",
            },
            "tenant_name": {
                "target_fields": ["tenant_name"],
                "priority": 1,
                "required": True,
                "transformations": ["validate_person_name"],
            },
            "property_address": {
                "target_fields": ["address"],
                "priority": 1,
                "required": True,
                "transformations": ["validate_address", "extract_location_info"],
            },
            # 面积信息映射
            "property_area": {
                "target_fields": ["rentable_area", "actual_property_area"],
                "priority": 1,
                "required": True,
                "transformations": ["validate_area", "calculate_derived_areas"],
            },
            # 金额信息映射
            "monthly_rent": {
                "target_fields": ["monthly_rent"],
                "priority": 1,
                "required": True,
                "transformations": ["validate_amount", "normalize_amount"],
            },
            "total_deposit": {
                "target_fields": ["deposit"],
                "priority": 1,
                "required": False,
                "transformations": ["validate_amount", "normalize_amount"],
            },
            # 日期信息映射
            "sign_date": {
                "target_fields": [],
                "priority": 1,
                "note": "签署日期不直接映射到资产字段",
            },
            "start_date": {
                "target_fields": ["contract_start_date"],
                "priority": 1,
                "required": True,
                "transformations": ["validate_date", "normalize_date"],
            },
            "end_date": {
                "target_fields": ["contract_end_date"],
                "priority": 1,
                "required": True,
                "transformations": ["validate_date", "normalize_date"],
            },
            # 联系信息映射
            "landlord_phone": {
                "target_fields": [],
                "priority": 2,
                "note": "房东电话不映射到资产字段",
            },
            "tenant_phone": {
                "target_fields": [],
                "priority": 2,
                "note": "租户电话不映射到资产字段",
            },
            # 身份信息映射
            "landlord_id": {
                "target_fields": [],
                "priority": 2,
                "note": "房东身份证不映射到资产字段",
            },
            "tenant_id": {
                "target_fields": [],
                "priority": 2,
                "note": "租户身份证不映射到资产字段",
            },
        }

    def _load_transformation_rules(self) -> dict[str, callable]:
        """加载转换规则"""
        return {
            "clean_contract_number": self._clean_contract_number,
            "validate_person_name": self._validate_person_name,
            "validate_address": self._validate_address,
            "validate_area": self._validate_area,
            "validate_amount": self._validate_amount,
            "validate_date": self._validate_date,
            "normalize_amount": self._normalize_amount,
            "normalize_date": self._normalize_date,
            "extract_location_info": self._extract_location_info,
            "calculate_derived_areas": self._calculate_derived_areas,
        }

    def _load_validation_rules(self) -> dict[str, dict[str, Any]]:
        """加载验证规则"""
        return {
            "required_fields": {
                "asset": [
                    "ownership_entity",
                    "property_name",
                    "address",
                    "ownership_status",
                    "property_nature",
                    "usage_status",
                    "rentable_area",
                    "monthly_rent",
                    "contract_start_date",
                    "contract_end_date",
                ],
                "contract": [
                    "contract_number",
                    "tenant_name",
                    "start_date",
                    "end_date",
                ],
            },
            "field_constraints": {
                "rentable_area": {"min": 0.1, "max": 10000, "type": "decimal"},
                "monthly_rent": {"min": 0, "max": 1000000, "type": "decimal"},
                "property_name": {"min_length": 2, "max_length": 200},
                "address": {"min_length": 5, "max_length": 500},
            },
        }

    def _load_completeness_rules(self) -> dict[str, Any]:
        """加载完整性规则"""
        return {
            "minimum_required_ratio": 0.8,  # 至少80%必填字段
            "high_quality_threshold": 0.9,  # 90%以上字段为高质量
            "critical_fields": [
                "address",
                "tenant_name",
                "monthly_rent",
                "start_date",
                "end_date",
            ],
        }

    async def map_extracted_data(
        self,
        extracted_data: dict[str, Any],
        extraction_metadata: dict[str, Any] | None = None,
    ) -> MappingResult:
        """映射提取的数据到58字段模型"""
        start_time = datetime.now()

        try:
            # 第一步：执行字段映射
            mappings = await self._perform_field_mapping(extracted_data)

            # 第二步：数据转换和验证
            validated_mappings = await self._transform_and_validate_mappings(mappings)

            # 第三步：构建资产和合同数据
            asset_data, contract_data = await self._build_target_data(
                validated_mappings
            )

            # 第四步：完整性检查
            completeness_result = await self._check_completeness(
                asset_data, contract_data
            )

            # 第五步：生成建议
            recommendations = self._generate_recommendations(
                validated_mappings, completeness_result
            )

            # 计算总体置信度
            overall_confidence = self._calculate_overall_confidence(validated_mappings)

            processing_time = (datetime.now() - start_time).total_seconds()

            return MappingResult(
                success=True,
                mappings={m.source_field: m for m in validated_mappings},
                overall_confidence=overall_confidence,
                asset_data=asset_data,
                contract_data=contract_data,
                validation_summary=completeness_result,
                recommendations=recommendations,
                processing_time=processing_time,
            )

        except Exception as e:
            logger.error(f"字段映射失败: {str(e)}")
            return MappingResult(
                success=False,
                mappings={},
                overall_confidence=0.0,
                asset_data={},
                contract_data={},
                validation_summary={},
                recommendations=[f"映射失败: {str(e)}"],
                processing_time=(datetime.now() - start_time).total_seconds(),
            )

    async def _perform_field_mapping(
        self, extracted_data: dict[str, Any]
    ) -> list[FieldMapping]:
        """执行字段映射"""
        mappings = []

        for source_field, source_value in extracted_data.items():
            if not source_value:
                continue

            mapping_rule = self.field_mapping_rules.get(source_field)
            if not mapping_rule:
                # 未定义映射规则的字段，记录但不映射
                logger.debug(f"未找到映射规则: {source_field}")
                continue

            # 为每个目标字段创建映射
            target_fields = mapping_rule.get("target_fields", [])
            if not target_fields and mapping_rule.get("note"):
                # 有注释说明不映射的字段
                continue

            if target_fields:
                # 创建到第一个目标字段的映射
                target_field = target_fields[0]
                mapping = FieldMapping(
                    source_field=source_field,
                    target_field=target_field,
                    value=source_value,
                    confidence=0.8,  # 初始置信度
                    validation_status=ValidationStatus.PENDING,
                    metadata={
                        "priority": mapping_rule.get("priority", 2),
                        "required": mapping_rule.get("required", False),
                        "mapping_rule": mapping_rule,
                    },
                )
                mappings.append(mapping)

        return mappings

    async def _transform_and_validate_mappings(
        self, mappings: list[FieldMapping]
    ) -> list[FieldMapping]:
        """转换和验证映射"""
        validated_mappings = []

        for mapping in mappings:
            try:
                # 应用转换规则
                transformed_value = mapping.value
                transformation_history = []

                rule = mapping.metadata.get("mapping_rule", {})
                transformations = rule.get("transformations", [])

                for transformation in transformations:
                    if transformation in self.transformation_rules:
                        try:
                            transform_func = self.transformation_rules[transformation]
                            result = await transform_func(transformed_value, mapping)
                            if isinstance(result, tuple):
                                transformed_value, validation_info = result
                                mapping.validation_errors.extend(
                                    validation_info.get("errors", [])
                                )
                                mapping.validation_warnings.extend(
                                    validation_info.get("warnings", [])
                                )
                            else:
                                transformed_value = result
                            transformation_history.append(transformation)
                        except Exception as e:
                            logger.warning(f"转换失败 {transformation}: {str(e)}")
                            mapping.validation_warnings.append(
                                f"转换{transformation}失败: {str(e)}"
                            )
                            mapping.confidence *= 0.9

                # 更新映射值和转换历史
                mapping.value = transformed_value
                mapping.transformation_applied = (
                    " -> ".join(transformation_history)
                    if transformation_history
                    else None
                )
                mapping.metadata["transformed"] = True

                # 执行验证
                validation_result = await self._validate_mapping(mapping)
                mapping.validation_status = validation_result["status"]
                mapping.validation_errors.extend(validation_result["errors"])
                mapping.validation_warnings.extend(validation_result["warnings"])
                mapping.confidence *= validation_result["confidence_multiplier"]

                validated_mappings.append(mapping)

            except Exception as e:
                logger.error(f"映射验证失败 {mapping.source_field}: {str(e)}")
                mapping.validation_status = ValidationStatus.ERROR
                mapping.validation_errors.append(str(e))
                mapping.confidence = 0.1
                validated_mappings.append(mapping)

        return validated_mappings

    async def _validate_mapping(self, mapping: FieldMapping) -> dict[str, Any]:
        """验证单个映射"""
        result = {
            "status": ValidationStatus.VALID,
            "errors": [],
            "warnings": [],
            "confidence_multiplier": 1.0,
        }

        try:
            # 基础值验证
            if mapping.value is None or mapping.value == "":
                result["status"] = ValidationStatus.ERROR
                result["errors"].append("字段值为空")
                result["confidence_multiplier"] = 0.0
                return result

            # 暂时跳过语义验证
            # semantic_result = await contract_semantic_validator.validate_contract_fields(
            #     {mapping.target_field: mapping.value}
            # )
            semantic_result = None

            if semantic_result.field_results:
                field_result = semantic_result.field_results.get(mapping.target_field)
                if field_result:
                    if field_result.validation_level.value == "error":
                        result["status"] = ValidationStatus.ERROR
                        result["errors"].extend(field_result.error_messages)
                        result["confidence_multiplier"] = 0.3
                    elif field_result.validation_level.value == "warning":
                        if result["status"] == ValidationStatus.VALID:
                            result["status"] = ValidationStatus.WARNING
                        result["warnings"].extend(field_result.warning_messages)
                        result["confidence_multiplier"] = 0.8

                    result["confidence_multiplier"] *= field_result.confidence

        except Exception as e:
            logger.warning(f"语义验证失败: {str(e)}")
            result["warnings"].append(f"语义验证失败: {str(e)}")
            result["confidence_multiplier"] *= 0.9

        return result

    async def _build_target_data(
        self, mappings: list[FieldMapping]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """构建目标数据结构"""
        asset_data = {}
        contract_data = {}

        # 设置默认值
        asset_data.update(
            {
                "ownership_entity": "待确认",  # 需要后续手动确认
                "ownership_category": "租赁",
                "project_name": "导入项目",
                "property_name": "待确认",  # 需要从地址提取
                "ownership_status": "已确权",
                "property_nature": "商业",
                "usage_status": "已出租",
                "business_category": "租赁",
                "is_litigated": False,
                "is_sublease": False,
                "data_status": "正常",
                "version": 1,
                "include_in_occupancy_rate": True,
            }
        )

        contract_data.update(
            {"contract_status": "有效", "data_status": "正常", "version": 1}
        )

        # 应用映射
        for mapping in mappings:
            if mapping.validation_status in [
                ValidationStatus.VALID,
                ValidationStatus.WARNING,
            ]:
                if mapping.target_field in asset_data:
                    asset_data[mapping.target_field] = mapping.value
                elif mapping.target_field in contract_data:
                    contract_data[mapping.target_field] = mapping.value

        # 特殊处理：从地址提取物业名称
        if "address" in asset_data and asset_data["property_name"] == "待确认":
            asset_data["property_name"] = self._extract_property_name_from_address(
                asset_data["address"]
            )

        # 计算衍生字段
        await self._calculate_derived_fields(asset_data, contract_data)

        return asset_data, contract_data

    def _extract_property_name_from_address(self, address: str) -> str:
        """从地址提取物业名称"""
        if not address:
            return "待确认"

        # 简单的物业名称提取逻辑
        # 通常物业名称在地址的最后部分，包含路名+号数+具体位置
        try:
            # 寻找路名、街道等关键词后的内容
            patterns = [
                r"(?:路|街|大道|巷)[^，,。]*?(\d+[^，,。]*?)(?:号楼|栋|号|铺|室)",
                r"(?:小区|花园|广场|大厦|中心|商城)[^，,。]*",
                r"([^，,。]*?(?:号楼|栋|号|铺|室))",
            ]

            for pattern in patterns:
                match = re.search(pattern, address)
                if match:
                    property_name = match.group(1) if match.groups() else match.group(0)
                    if len(property_name) > 3 and len(property_name) < 50:
                        return property_name.strip()

            # 如果没有找到合适的名称，返回地址的后半部分
            parts = re.split(r"[，,。]", address)
            if len(parts) > 1:
                return parts[-1].strip()

        except Exception as e:
            logger.warning(f"物业名称提取失败: {str(e)}")

        return address[:30] + "..." if len(address) > 30 else address

    async def _calculate_derived_fields(
        self, asset_data: dict[str, Any], contract_data: dict[str, Any]
    ):
        """计算衍生字段"""
        # 计算租赁期限（月）
        if (
            "contract_start_date" in contract_data
            and "contract_end_date" in contract_data
        ):
            try:
                start_date = datetime.strptime(
                    contract_data["contract_start_date"], "%Y-%m-%d"
                )
                end_date = datetime.strptime(
                    contract_data["contract_end_date"], "%Y-%m-%d"
                )
                months = (end_date.year - start_date.year) * 12 + (
                    end_date.month - start_date.month
                )
                contract_data["lease_term_months"] = max(months, 1)
            except (ValueError, TypeError, KeyError):
                # 日期解析失败时静默处理，保持原有数据
                pass

        # 设置合同编号到资产数据（如果存在）
        if (
            "contract_number" in contract_data
            and "lease_contract_number" not in asset_data
        ):
            asset_data["lease_contract_number"] = contract_data["contract_number"]

        # 从合同数据同步日期到资产数据
        if "contract_start_date" in contract_data:
            asset_data["contract_start_date"] = contract_data["contract_start_date"]
        if "contract_end_date" in contract_data:
            asset_data["contract_end_date"] = contract_data["contract_end_date"]

    async def _check_completeness(
        self, asset_data: dict[str, Any], contract_data: dict[str, Any]
    ) -> dict[str, Any]:
        """检查数据完整性"""
        required_asset_fields = self.validation_rules["required_fields"]["asset"]
        required_contract_fields = self.validation_rules["required_fields"]["contract"]

        asset_completeness = self._calculate_field_completeness(
            asset_data, required_asset_fields
        )
        contract_completeness = self._calculate_field_completeness(
            contract_data, required_contract_fields
        )

        critical_fields = self.completeness_rules["critical_fields"]
        critical_completeness = self._check_critical_fields(
            asset_data, contract_data, critical_fields
        )

        overall_completeness = (asset_completeness + contract_completeness) / 2

        return {
            "asset_completeness": asset_completeness,
            "contract_completeness": contract_completeness,
            "critical_completeness": critical_completeness,
            "overall_completeness": overall_completeness,
            "missing_asset_fields": [
                f
                for f in required_asset_fields
                if f not in asset_data or not asset_data[f]
            ],
            "missing_contract_fields": [
                f
                for f in required_contract_fields
                if f not in contract_data or not contract_data[f]
            ],
            "quality_level": self._determine_quality_level(overall_completeness),
        }

    def _calculate_field_completeness(
        self, data: dict[str, Any], required_fields: list[str]
    ) -> float:
        """计算字段完整性"""
        if not required_fields:
            return 1.0

        present_fields = sum(
            1 for field in required_fields if field in data and data[field]
        )
        return present_fields / len(required_fields)

    def _check_critical_fields(
        self,
        asset_data: dict[str, Any],
        contract_data: dict[str, Any],
        critical_fields: list[str],
    ) -> float:
        """检查关键字段"""
        all_data = {**asset_data, **contract_data}
        present_critical = sum(
            1 for field in critical_fields if field in all_data and all_data[field]
        )
        return present_critical / len(critical_fields)

    def _determine_quality_level(self, completeness: float) -> str:
        """确定质量等级"""
        if completeness >= 0.9:
            return "high"
        elif completeness >= 0.7:
            return "medium"
        elif completeness >= 0.5:
            return "low"
        else:
            return "very_low"

    def _generate_recommendations(
        self, mappings: list[FieldMapping], completeness_result: dict[str, Any]
    ) -> list[str]:
        """生成建议"""
        recommendations = []

        # 完整性建议
        if completeness_result["overall_completeness"] < 0.8:
            recommendations.append("数据完整性较低，建议补充缺失字段")

        missing_fields = (
            completeness_result["missing_asset_fields"]
            + completeness_result["missing_contract_fields"]
        )
        if missing_fields:
            recommendations.append(f"缺失关键字段: {', '.join(missing_fields[:5])}")

        # 验证建议
        error_mappings = [
            m for m in mappings if m.validation_status == ValidationStatus.ERROR
        ]
        if error_mappings:
            recommendations.append(
                f"以下字段存在错误需要修正: {', '.join([m.target_field for m in error_mappings[:3]])}"
            )

        warning_mappings = [
            m for m in mappings if m.validation_status == ValidationStatus.WARNING
        ]
        if warning_mappings:
            recommendations.append(
                f"以下字段需要关注: {', '.join([m.target_field for m in warning_mappings[:3]])}"
            )

        # 置信度建议
        low_confidence_mappings = [m for m in mappings if m.confidence < 0.6]
        if low_confidence_mappings:
            recommendations.append(
                f"以下字段置信度较低，建议人工确认: {', '.join([m.target_field for m in low_confidence_mappings[:3]])}"
            )

        # 质量建议
        if completeness_result["quality_level"] in ["low", "very_low"]:
            recommendations.append("数据质量较低，建议仔细核对所有信息")

        # 默认值建议
        if "ownership_entity" in missing_fields:
            recommendations.append("需要确认权属方信息")
        if "property_name" in missing_fields:
            recommendations.append("建议完善物业名称信息")

        return recommendations

    def _calculate_overall_confidence(self, mappings: list[FieldMapping]) -> float:
        """计算总体置信度"""
        if not mappings:
            return 0.0

        # 根据字段重要性加权
        field_weights = {
            "address": 0.2,
            "tenant_name": 0.15,
            "monthly_rent": 0.15,
            "contract_start_date": 0.1,
            "contract_end_date": 0.1,
            "rentable_area": 0.1,
            "lease_contract_number": 0.05,
            "deposit": 0.05,
        }

        weighted_confidence = 0.0
        total_weight = 0.0

        for mapping in mappings:
            weight = field_weights.get(mapping.target_field, 0.02)
            # 根据验证状态调整权重
            if mapping.validation_status == ValidationStatus.ERROR:
                weight *= 0.1
            elif mapping.validation_status == ValidationStatus.WARNING:
                weight *= 0.7

            weighted_confidence += mapping.confidence * weight
            total_weight += weight

        return weighted_confidence / total_weight if total_weight > 0 else 0.0

    # 转换方法实现
    async def _clean_contract_number(self, value: Any, mapping: FieldMapping) -> Any:
        """清理合同编号"""
        if isinstance(value, str):
            # 移除特殊字符，保留字母数字和常用符号
            cleaned = re.sub(r"[^\w\-()（）]", "", value)
            return cleaned.upper()
        return value

    async def _validate_person_name(
        self, value: Any, mapping: FieldMapping
    ) -> tuple[Any, dict[str, Any]]:
        """验证姓名"""
        result = {"errors": [], "warnings": []}

        if isinstance(value, str):
            # 长度检查
            if len(value) < 2:
                result["errors"].append("姓名长度不能少于2个字符")
            elif len(value) > 10:
                result["warnings"].append("姓名较长，请确认是否正确")

            # 字符检查
            if re.search(r"[0-9@#$%^&*()]", value):
                result["errors"].append("姓名包含数字或特殊字符")

            # 中文字符检查
            chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", value))
            if chinese_chars == 0:
                result["warnings"].append("未检测到中文字符")

        return value, result

    async def _validate_address(
        self, value: Any, mapping: FieldMapping
    ) -> tuple[Any, dict[str, Any]]:
        """验证地址"""
        result = {"errors": [], "warnings": []}

        if isinstance(value, str):
            if len(value) < 5:
                result["warnings"].append("地址信息过短")
            elif len(value) > 500:
                result["warnings"].append("地址信息过长")

            # 地址关键词检查
            location_keywords = ["省", "市", "区", "县", "镇", "街道", "路", "号"]
            if not any(keyword in value for keyword in location_keywords):
                result["warnings"].append("地址缺少位置关键词")

        return value, result

    async def _validate_area(
        self, value: Any, mapping: FieldMapping
    ) -> tuple[Any, dict[str, Any]]:
        """验证面积"""
        result = {"errors": [], "warnings": []}

        try:
            area = float(value)
            if area <= 0:
                result["errors"].append("面积必须大于0")
            elif area > 10000:
                result["warnings"].append("面积较大，请确认单位")

            value = area
        except (ValueError, TypeError):
            result["errors"].append("面积格式不正确")

        return value, result

    async def _validate_amount(
        self, value: Any, mapping: FieldMapping
    ) -> tuple[Any, dict[str, Any]]:
        """验证金额"""
        result = {"errors": [], "warnings": []}

        try:
            amount = float(value)
            if amount < 0:
                result["errors"].append("金额不能为负数")
            elif amount > 1000000:
                result["warnings"].append("金额较大，请确认正确性")

            value = amount
        except (ValueError, TypeError):
            result["errors"].append("金额格式不正确")

        return value, result

    async def _validate_date(
        self, value: Any, mapping: FieldMapping
    ) -> tuple[Any, dict[str, Any]]:
        """验证日期"""
        result = {"errors": [], "warnings": []}

        if isinstance(value, str):
            try:
                parsed_date = datetime.strptime(value, "%Y-%m-%d")
                now = datetime.now()
                if parsed_date.year < 1990 or parsed_date.year > now.year + 10:
                    result["warnings"].append("日期年份可能不正确")
                value = value
            except ValueError:
                result["errors"].append("日期格式不正确")
        elif isinstance(value, datetime):
            value = value.strftime("%Y-%m-%d")

        return value, result

    async def _normalize_amount(self, value: Any, mapping: FieldMapping) -> Any:
        """标准化金额"""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            # 移除非数字字符（除了小数点）
            cleaned = re.sub(r"[^\d.]", "", value)
            try:
                return float(cleaned)
            except ValueError:
                return value
        return value

    async def _normalize_date(self, value: Any, mapping: FieldMapping) -> Any:
        """标准化日期"""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        elif isinstance(value, str):
            # 尝试解析并重新格式化
            date_formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"]
            for fmt in date_formats:
                try:
                    parsed = datetime.strptime(value, fmt)
                    return parsed.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        return value

    async def _extract_location_info(self, value: Any, mapping: FieldMapping) -> Any:
        """提取位置信息"""
        if isinstance(value, str):
            # 可以在这里添加地址解析逻辑
            # 比如提取省市区等信息
            pass
        return value

    async def _calculate_derived_areas(self, value: Any, mapping: FieldMapping) -> Any:
        """计算衍生面积"""
        # 这里可以添加面积计算逻辑
        return value


# 创建全局实例
enhanced_field_mapper = EnhancedFieldMapper()
