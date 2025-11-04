from typing import Any

"""
PDF数据验证和匹配服务
负责验证提取的数据并进行资产、权属方匹配
"""

import logging
import re
from datetime import datetime

from fuzzywuzzy import fuzz
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FieldValidator:
    """字段验证器"""

    @staticmethod
    def validate_phone_number(phone: str) -> dict[str, Any]:
        """验证电话号码"""
        phone = re.sub(r"[^\d]", "", phone)  # 移除非数字字符

        # 中国大陆手机号验证
        mobile_pattern = r"^1[3-9]\d{9}$"
        # 固定电话验证
        landline_pattern = r"^0\d{2,3}-?\d{7,8}$"

        is_valid = re.match(mobile_pattern, phone) or re.match(landline_pattern, phone)

        return {
            "is_valid": is_valid,
            "normalized_value": phone,
            "phone_type": "mobile"
            if re.match(mobile_pattern, phone)
            else "landline"
            if is_valid
            else "unknown",
            "errors": [] if is_valid else ["电话号码格式不正确"],
        }

    @staticmethod
    def validate_amount(amount: str) -> dict[str, Any]:
        """验证金额"""
        try:
            # 移除货币符号和空格
            clean_amount = re.sub(r"[^\d.]", "", str(amount))
            numeric_amount = float(clean_amount)

            is_valid = numeric_amount >= 0

            return {
                "is_valid": is_valid,
                "numeric_value": numeric_amount,
                "formatted_value": f"¥{numeric_amount:,.2f}" if is_valid else amount,
                "errors": [] if is_valid else ["金额必须为非负数"],
            }
        except (ValueError, TypeError):
            return {
                "is_valid": False,
                "numeric_value": 0,
                "formatted_value": amount,
                "errors": ["金额格式不正确"],
            }

    @staticmethod
    def validate_date(date_str: str) -> dict[str, Any]:
        """验证日期格式"""
        date_formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y年%m月%d日",
            "%Y.%m.%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
        ]

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return {
                    "is_valid": True,
                    "parsed_date": parsed_date,
                    "formatted_date": parsed_date.strftime("%Y-%m-%d"),
                    "errors": [],
                }
            except ValueError:
                continue

        return {
            "is_valid": False,
            "parsed_date": None,
            "formatted_date": date_str,
            "errors": [
                "日期格式不正确，支持的格式：YYYY-MM-DD, YYYY/MM/DD, YYYY年MM月DD日等"
            ],
        }

    @staticmethod
    def validate_area(area_str: str) -> dict[str, Any]:
        """验证面积数值"""
        try:
            # 提取数字部分
            area_match = re.search(r"(\d+\.?\d*)", str(area_str))
            if not area_match:
                raise ValueError("无法提取面积数值")

            area_value = float(area_match.group(1))

            is_valid = area_value > 0 and area_value <= 100000  # 最大10万平方米

            return {
                "is_valid": is_valid,
                "numeric_value": area_value,
                "formatted_value": f"{area_value:.2f}㎡",
                "errors": [] if is_valid else ["面积必须在0-100000平方米之间"],
            }
        except (ValueError, TypeError):
            return {
                "is_valid": False,
                "numeric_value": 0,
                "formatted_value": area_str,
                "errors": ["面积格式不正确"],
            }

    @staticmethod
    def validate_email(email: str) -> dict[str, Any]:
        """验证邮箱地址"""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        is_valid = re.match(email_pattern, email.strip()) is not None

        return {
            "is_valid": is_valid,
            "normalized_value": email.strip().lower(),
            "errors": [] if is_valid else ["邮箱格式不正确"],
        }


class AssetMatcher:
    """资产匹配器"""

    def __init__(self, db: Session):
        self.db = db

    async def find_matching_assets(
        self,
        property_name: str,
        address: str = "",
        property_nature: str = "",
        min_confidence: float = 0.6,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """查找匹配的资产"""
        from ..models.asset import Asset

        try:
            # 获取所有资产（可以根据组织ID过滤）
            query = self.db.query(Asset).filter(not Asset.is_deleted)
            assets = query.all()

            matches = []

            for asset in assets:
                # 计算物业名称匹配度
                name_score = (
                    fuzz.partial_ratio(
                        property_name.lower(), (asset.property_name or "").lower()
                    )
                    / 100.0
                )

                # 计算地址匹配度
                address_score = 0
                if address and asset.address:
                    address_score = (
                        fuzz.partial_ratio(address.lower(), asset.address.lower())
                        / 100.0
                    )

                # 计算性质匹配度
                nature_score = 0
                if property_nature and asset.property_nature:
                    nature_score = (
                        fuzz.ratio(
                            property_nature.lower(),
                            (asset.property_nature or "").lower(),
                        )
                        / 100.0
                    )

                # 计算综合匹配度
                total_score = (
                    name_score * 0.6 + address_score * 0.3 + nature_score * 0.1
                )

                if total_score >= min_confidence:
                    matches.append(
                        {
                            "asset_id": asset.id,
                            "property_name": asset.property_name,
                            "address": asset.address,
                            "property_nature": asset.property_nature,
                            "total_area": asset.total_area,
                            "rentable_area": asset.rentable_area,
                            "ownership_status": asset.ownership_status,
                            "match_confidence": total_score,
                            "name_match_score": name_score,
                            "address_match_score": address_score,
                            "nature_match_score": nature_score,
                            "match_details": {
                                "name_similarity": name_score,
                                "address_similarity": address_score,
                                "nature_similarity": nature_score,
                            },
                        }
                    )

            # 按匹配度排序
            matches.sort(key=lambda x: x["match_confidence"], reverse=True)

            return matches[:max_results]

        except Exception as e:
            logger.error(f"资产匹配失败: {str(e)}")
            return []


class OwnershipMatcher:
    """权属方匹配器"""

    def __init__(self, db: Session):
        self.db = db

    async def find_matching_ownerships(
        self,
        ownership_name: str,
        contact_info: str = "",
        min_confidence: float = 0.6,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """查找匹配的权属方"""
        from ..models.ownership import Ownership

        try:
            # 获取所有权属方
            query = self.db.query(Ownership).filter(not Ownership.is_deleted)
            ownerships = query.all()

            matches = []

            for ownership in ownerships:
                # 计算名称匹配度
                name_score = (
                    fuzz.partial_ratio(
                        ownership_name.lower(), (ownership.ownership_name or "").lower()
                    )
                    / 100.0
                )

                # 计算联系方式匹配度
                contact_score = 0
                if contact_info and ownership.contact_info:
                    contact_score = (
                        fuzz.partial_ratio(
                            contact_info.lower(), ownership.contact_info.lower()
                        )
                        / 100.0
                    )

                # 计算综合匹配度
                total_score = name_score * 0.8 + contact_score * 0.2

                if total_score >= min_confidence:
                    matches.append(
                        {
                            "ownership_id": ownership.id,
                            "ownership_name": ownership.ownership_name,
                            "contact_info": ownership.contact_info,
                            "ownership_type": ownership.ownership_type,
                            "match_confidence": total_score,
                            "name_match_score": name_score,
                            "contact_match_score": contact_score,
                            "match_details": {
                                "name_similarity": name_score,
                                "contact_similarity": contact_score,
                            },
                        }
                    )

            # 按匹配度排序
            matches.sort(key=lambda x: x["match_confidence"], reverse=True)

            return matches[:max_results]

        except Exception as e:
            logger.error(f"权属方匹配失败: {str(e)}")
            return []


class DuplicateChecker:
    """重复合同检查器"""

    def __init__(self, db: Session):
        self.db = db

    async def find_duplicate_contracts(
        self,
        contract_number: str,
        tenant_name: str,
        property_address: str = "",
        start_date: str = "",
        min_confidence: float = 0.8,
    ) -> list[dict[str, Any]]:
        """查找重复合同"""
        from ..models.rent_contract import RentContract

        try:
            # 获取所有合同
            query = self.db.query(RentContract).filter(not RentContract.is_deleted)
            contracts = query.all()

            duplicates = []

            for contract in contracts:
                # 合同编号精确匹配
                contract_number_match = (
                    contract.contract_number
                    and contract.contract_number.strip().lower()
                    == contract_number.strip().lower()
                )

                # 承租方名称匹配
                tenant_match = 0
                if tenant_name and contract.tenant_name:
                    tenant_match = (
                        fuzz.ratio(tenant_name.lower(), contract.tenant_name.lower())
                        / 100.0
                    )

                # 地址匹配
                address_match = 0
                if property_address and contract.property_address:
                    address_match = (
                        fuzz.partial_ratio(
                            property_address.lower(), contract.property_address.lower()
                        )
                        / 100.0
                    )

                # 开始日期匹配
                date_match = 0
                if start_date and contract.start_date:
                    try:
                        input_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                        contract_date = contract.start_date.date()
                        date_diff = abs((input_date - contract_date).days)
                        date_match = max(0, 1 - date_diff / 365)  # 一年内为高匹配
                    except Exception:
                        # 通用异常处理，静默处理
                        pass

                # 计算重复概率
                duplicate_probability = 0
                if contract_number_match:
                    duplicate_probability = 1.0  # 合同编号相同，高度重复
                else:
                    # 综合判断
                    duplicate_probability = (
                        tenant_match * 0.4 + address_match * 0.3 + date_match * 0.3
                    )

                if duplicate_probability >= min_confidence:
                    duplicates.append(
                        {
                            "contract_id": contract.id,
                            "contract_number": contract.contract_number,
                            "tenant_name": contract.tenant_name,
                            "property_address": contract.property_address,
                            "start_date": contract.start_date.strftime("%Y-%m-%d")
                            if contract.start_date
                            else None,
                            "end_date": contract.end_date.strftime("%Y-%m-%d")
                            if contract.end_date
                            else None,
                            "monthly_rent": contract.monthly_rent,
                            "duplicate_probability": duplicate_probability,
                            "match_details": {
                                "contract_number_match": contract_number_match,
                                "tenant_similarity": tenant_match,
                                "address_similarity": address_match,
                                "date_similarity": date_match,
                            },
                        }
                    )

            # 按重复概率排序
            duplicates.sort(key=lambda x: x["duplicate_probability"], reverse=True)

            return duplicates

        except Exception as e:
            logger.error(f"重复合同检查失败: {str(e)}")
            return []


class PDFValidationMatchingService:
    """PDF验证和匹配服务"""

    def __init__(self, db: Session):
        self.db = db
        self.field_validator = FieldValidator()
        self.asset_matcher = AssetMatcher(db)
        self.ownership_matcher = OwnershipMatcher(db)
        self.duplicate_checker = DuplicateChecker(db)

    async def validate_extracted_data(
        self, extracted_data: dict[str, Any]
    ) -> dict[str, Any]:
        """验证提取的数据"""

        validation_results = {}
        validation_errors = []
        validation_warnings = []
        validated_data = {}

        # 定义验证规则映射
        validation_rules = {
            "tenant_phone": self.field_validator.validate_phone_number,
            "tenant_email": self.field_validator.validate_email,
            "monthly_rent": self.field_validator.validate_amount,
            "security_deposit": self.field_validator.validate_amount,
            "total_area": self.field_validator.validate_area,
            "rentable_area": self.field_validator.validate_area,
            "start_date": self.field_validator.validate_date,
            "end_date": self.field_validator.validate_date,
            "sign_date": self.field_validator.validate_date,
        }

        # 执行验证
        for field_name, validation_func in validation_rules.items():
            if field_name in extracted_data:
                value = extracted_data[field_name]
                if value is not None and str(value).strip():
                    result = validation_func(str(value))
                    validation_results[field_name] = result

                    if result["is_valid"]:
                        validated_data[field_name] = (
                            result.get("numeric_value")
                            or result.get("parsed_date")
                            or result.get("normalized_value")
                            or value
                        )
                    else:
                        validation_errors.extend(
                            [
                                f"{field_name}: {error}"
                                for error in result.get("errors", [])
                            ]
                        )

        # 计算验证分数
        total_fields = len(validation_rules)
        valid_fields = sum(
            1 for result in validation_results.values() if result.get("is_valid", False)
        )
        validation_score = valid_fields / total_fields if total_fields > 0 else 0

        # 检查必填字段
        required_fields = ["tenant_name", "property_address"]
        missing_required = [
            field for field in required_fields if not extracted_data.get(field)
        ]

        if missing_required:
            validation_errors.extend(
                [f"缺少必填字段: {field}" for field in missing_required]
            )

        return {
            "validation_results": validation_results,
            "validated_data": validated_data,
            "validation_errors": validation_errors,
            "validation_warnings": validation_warnings,
            "validation_score": validation_score,
            "processed_fields": len(validation_results),
            "required_fields_count": len(required_fields),
            "missing_required_fields": missing_required,
            "is_valid": len(validation_errors) == 0 and len(missing_required) == 0,
        }

    async def perform_data_matching(
        self, extracted_data: dict[str, Any]
    ) -> dict[str, Any]:
        """执行数据匹配"""

        # 资产匹配
        asset_matches = []
        if extracted_data.get("property_name"):
            asset_matches = await self.asset_matcher.find_matching_assets(
                property_name=extracted_data["property_name"],
                address=extracted_data.get("property_address", ""),
                property_nature=extracted_data.get("property_nature", ""),
                min_confidence=0.6,
            )

        # 权属方匹配
        ownership_matches = []
        if extracted_data.get("landlord_name") or extracted_data.get(
            "ownership_entity"
        ):
            ownership_name = extracted_data.get("landlord_name") or extracted_data.get(
                "ownership_entity", ""
            )
            ownership_matches = await self.ownership_matcher.find_matching_ownerships(
                ownership_name=ownership_name,
                contact_info=extracted_data.get("landlord_contact", ""),
                min_confidence=0.6,
            )

        # 重复合同检查
        duplicate_contracts = []
        if extracted_data.get("contract_number") or extracted_data.get("tenant_name"):
            duplicate_contracts = await self.duplicate_checker.find_duplicate_contracts(
                contract_number=extracted_data.get("contract_number", ""),
                tenant_name=extracted_data.get("tenant_name", ""),
                property_address=extracted_data.get("property_address", ""),
                start_date=extracted_data.get("start_date", ""),
                min_confidence=0.7,
            )

        # 计算综合匹配置信度
        max_asset_confidence = max(
            [m["match_confidence"] for m in asset_matches], default=0
        )
        max_ownership_confidence = max(
            [m["match_confidence"] for m in ownership_matches], default=0
        )
        max_duplicate_confidence = max(
            [m["duplicate_probability"] for m in duplicate_contracts], default=0
        )

        overall_match_confidence = (
            max_asset_confidence * 0.4
            + max_ownership_confidence * 0.3
            + (1 - max_duplicate_confidence) * 0.3  # 重复合同风险越低越好
        )

        # 生成推荐
        recommendations = []
        if asset_matches:
            best_asset = asset_matches[0]
            if best_asset["match_confidence"] > 0.8:
                recommendations.append(
                    f"建议选择资产: {best_asset['property_name']} (匹配度: {best_asset['match_confidence']:.1%})"
                )

        if ownership_matches:
            best_ownership = ownership_matches[0]
            if best_ownership["match_confidence"] > 0.8:
                recommendations.append(
                    f"建议选择权属方: {best_ownership['ownership_name']} (匹配度: {best_ownership['match_confidence']:.1%})"
                )

        if duplicate_contracts:
            best_duplicate = duplicate_contracts[0]
            if best_duplicate["duplicate_probability"] > 0.8:
                recommendations.append(
                    f"警告: 可能与现有合同重复 (概率: {best_duplicate['duplicate_probability']:.1%})"
                )

        return {
            "matched_assets": asset_matches,
            "matched_ownerships": ownership_matches,
            "duplicate_contracts": duplicate_contracts,
            "overall_match_confidence": overall_match_confidence,
            "recommendations": recommendations,
            "matching_summary": {
                "assets_found": len(asset_matches),
                "ownerships_found": len(ownership_matches),
                "potential_duplicates": len(duplicate_contracts),
                "best_asset_match": max_asset_confidence,
                "best_ownership_match": max_ownership_confidence,
                "highest_duplicate_risk": max_duplicate_confidence,
            },
        }

    async def validate_and_match(
        self, extracted_data: dict[str, Any]
    ) -> dict[str, Any]:
        """执行完整的验证和匹配流程"""

        # 数据验证
        validation_result = await self.validate_extracted_data(extracted_data)

        # 数据匹配
        matching_result = await self.perform_data_matching(extracted_data)

        # 综合评估
        overall_confidence = (
            validation_result["validation_score"] * 0.4
            + matching_result["overall_match_confidence"] * 0.6
        )

        return {
            "validation_result": validation_result,
            "matching_result": matching_result,
            "overall_confidence": overall_confidence,
            "ready_for_import": (
                validation_result["is_valid"]
                and len(matching_result["duplicate_contracts"]) == 0
                and overall_confidence > 0.6
            ),
            "processing_time": datetime.now().isoformat(),
        }
