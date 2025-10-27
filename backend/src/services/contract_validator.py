"""
合同数据验证和匹配服务
验证提取的数据完整性，并与现有系统数据进行智能匹配
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from ..models import Asset, Ownership, RentContract
from ..database import get_db

# 导入fuzzywuzzy，如果不可用则使用简单替代方案
try:
    from fuzzywuzzy import fuzz, process
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("fuzzywuzzy not available, using simple string matching")

    def simple_ratio(s1: str, s2: str) -> int:
        """简单的字符串相似度计算"""
        if not s1 or not s2:
            return 0
        s1, s2 = s1.lower(), s2.lower()
        common_chars = set(s1) & set(s2)
        return int((len(common_chars) / max(len(set(s1)), len(set(s2)))) * 100)

    class Fuzz:
        @staticmethod
        def ratio(s1: str, s2: str) -> int:
            return simple_ratio(s1, s2)

    fuzz = Fuzz()

logger = logging.getLogger(__name__)


class ContractValidationError(Exception):
    """合同验证异常"""
    pass


class ContractValidator:
    """合同数据验证器"""

    def __init__(self):
        # 必填字段定义
        self.REQUIRED_FIELDS = {
            "contract_number": "合同编号",
            "tenant_name": "承租方名称",
            "start_date": "合同开始日期",
            "end_date": "合同结束日期",
            "monthly_rent": "月租金"
        }

        # 字段验证规则
        self.FIELD_VALIDATORS = {
            "contract_number": self._validate_contract_number,
            "tenant_name": self._validate_name,
            "landlord_name": self._validate_name,
            "asset_address": self._validate_address,
            "start_date": self._validate_date,
            "end_date": self._validate_date,
            "sign_date": self._validate_date,
            "monthly_rent": self._validate_money,
            "total_deposit": self._validate_money,
            "annual_income": self._validate_money,
            "total_area": self._validate_area,
            "rentable_area": self._validate_area,
            "rented_area": self._validate_area,
            "tenant_contact": self._validate_contact,
            "payment_method": self._validate_text,
            "payment_terms": self._validate_text,
            "contract_status": self._validate_status,
            "business_category": self._validate_text
        }

        # 合同状态标准值
        self.VALID_STATUSES = ["有效", "生效", "到期", "终止", "暂停", "草稿", "待生效"]

    def validate_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证提取的合同数据

        Args:
            data: 提取的合同数据

        Returns:
            验证结果字典，包含success, errors, warnings, validated_data
        """
        try:
            errors = []
            warnings = []
            validated_data = {}

            # 1. 验证必填字段
            missing_fields = self._check_required_fields(data)
            if missing_fields:
                for field in missing_fields:
                    errors.append(f"缺少必填字段: {self.REQUIRED_FIELDS[field]}")

            # 2. 验证每个字段的数据格式和有效性
            for field, value in data.items():
                try:
                    if field in self.FIELD_VALIDATORS:
                        validated_value = self.FIELD_VALIDATORS[field](value)
                        if validated_value is not None:
                            validated_data[field] = validated_value
                    else:
                        # 未定义验证规则的字段，进行基本清理
                        validated_data[field] = self._basic_clean(value)
                except ContractValidationError as e:
                    errors.append(f"字段 '{field}' 验证失败: {str(e)}")
                except Exception as e:
                    warnings.append(f"字段 '{field}' 处理时出现警告: {str(e)}")
                    validated_data[field] = value

            # 3. 业务逻辑验证
            business_errors = self._validate_business_logic(validated_data)
            errors.extend(business_errors)

            # 4. 数据一致性检查
            consistency_warnings = self._check_data_consistency(validated_data)
            warnings.extend(consistency_warnings)

            # 5. 计算验证分数
            validation_score = self._calculate_validation_score(validated_data, errors, warnings)

            return {
                "success": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "validated_data": validated_data,
                "validation_score": validation_score,
                "processed_fields": len(validated_data),
                "required_fields_count": len(self.REQUIRED_FIELDS),
                "missing_required_fields": missing_fields
            }

        except Exception as e:
            logger.error(f"Contract validation failed: {e}")
            return {
                "success": False,
                "errors": [f"验证过程出现异常: {str(e)}"],
                "warnings": [],
                "validated_data": {},
                "validation_score": 0.0
            }

    def match_with_existing_data(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        与现有系统数据进行智能匹配

        Args:
            validated_data: 验证后的合同数据

        Returns:
            匹配结果，包含匹配的资产、权属方等信息
        """
        try:
            db = next(get_db())
            result = {
                "matched_assets": [],
                "matched_ownerships": [],
                "duplicate_contracts": [],
                "recommendations": {}
            }

            # 1. 根据地址匹配资产
            if "asset_address" in validated_data:
                matched_assets = self._match_assets_by_address(
                    db, validated_data["asset_address"]
                )
                result["matched_assets"] = matched_assets
                if matched_assets:
                    result["recommendations"]["asset_id"] = matched_assets[0]["id"]

            # 2. 根据名称匹配权属方
            if "landlord_name" in validated_data:
                matched_ownerships = self._match_ownerships_by_name(
                    db, validated_data["landlord_name"]
                )
                result["matched_ownerships"] = matched_ownerships
                if matched_ownerships:
                    result["recommendations"]["ownership_id"] = matched_ownerships[0]["id"]

            # 3. 检查合同编号重复
            if "contract_number" in validated_data:
                duplicate_contracts = self._check_contract_duplicate(
                    db, validated_data["contract_number"]
                )
                result["duplicate_contracts"] = duplicate_contracts

            # 4. 计算匹配置信度
            result["match_confidence"] = self._calculate_match_confidence(result)

            return result

        except Exception as e:
            logger.error(f"Data matching failed: {e}")
            return {
                "matched_assets": [],
                "matched_ownerships": [],
                "duplicate_contracts": [],
                "recommendations": {},
                "match_confidence": 0.0,
                "error": str(e)
            }

    def _check_required_fields(self, data: Dict[str, Any]) -> List[str]:
        """检查必填字段是否缺失"""
        missing = []
        for field, display_name in self.REQUIRED_FIELDS.items():
            if field not in data or not data[field] or str(data[field]).strip() == "":
                missing.append(field)
        return missing

    def _validate_contract_number(self, value: Any) -> str:
        """验证合同编号"""
        if not value:
            raise ContractValidationError("合同编号不能为空")

        contract_number = str(value).strip()
        if len(contract_number) < 3:
            raise ContractValidationError("合同编号长度过短")

        # 检查是否包含基本字符
        if not any(c.isalnum() for c in contract_number):
            raise ContractValidationError("合同编号必须包含字母或数字")

        return contract_number

    def _validate_name(self, value: Any) -> str:
        """验证名称字段"""
        if not value:
            raise ContractValidationError("名称不能为空")

        name = str(value).strip()
        if len(name) < 2:
            raise ContractValidationError("名称长度过短")

        if len(name) > 100:
            raise ContractValidationError("名称长度过长")

        return name

    def _validate_address(self, value: Any) -> str:
        """验证地址"""
        if not value:
            raise ContractValidationError("地址不能为空")

        address = str(value).strip()
        if len(address) < 5:
            raise ContractValidationError("地址长度过短，可能不完整")

        return address

    def _validate_date(self, value: Any) -> str:
        """验证日期格式"""
        if not value:
            return ""

        date_str = str(value).strip()

        # 尝试解析日期
        date_formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y年%m月%d日",
            "%Y年%m月%d"
        ]

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # 尝试从复杂字符串中提取日期
        import re
        date_patterns = [
            r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?',
            r'(\d{4})年(\d{1,2})月(\d{1,2})日?'
        ]

        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                year, month, day = match.groups()
                try:
                    parsed_date = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue

        raise ContractValidationError(f"无法解析日期格式: {date_str}")

    def _validate_money(self, value: Any) -> str:
        """验证金额"""
        if not value:
            return "0"

        money_str = str(value).strip()

        # 移除常见符号
        money_str = money_str.replace("元", "").replace("￥", "").replace(",", "")
        money_str = money_str.replace("，", "").replace(" ", "")

        # 提取数字
        import re
        numbers = re.findall(r'\d+\.?\d*', money_str)
        if not numbers:
            raise ContractValidationError(f"无法解析金额: {value}")

        try:
            # 处理大单位
            money_value = float(numbers[0])
            if "万" in money_str:
                money_value *= 10000
            elif "千" in money_str:
                money_value *= 1000

            # 验证金额合理性
            if money_value < 0:
                raise ContractValidationError("金额不能为负数")
            if money_value > 999999999:
                raise ContractValidationError("金额过大")

            return str(money_value)

        except (ValueError, InvalidOperation) as e:
            raise ContractValidationError(f"金额格式错误: {value}")

    def _validate_area(self, value: Any) -> str:
        """验证面积"""
        if not value:
            return "0"

        area_str = str(value).strip()

        # 移除单位符号
        area_str = area_str.replace("㎡", "").replace("平方米", "")
        area_str = area_str.replace("M2", "").replace("m2", "").replace(",", "")

        # 提取数字
        import re
        numbers = re.findall(r'\d+\.?\d*', area_str)
        if not numbers:
            raise ContractValidationError(f"无法解析面积: {value}")

        try:
            area_value = float(numbers[0])

            # 验证面积合理性
            if area_value < 0:
                raise ContractValidationError("面积不能为负数")
            if area_value > 100000:
                raise ContractValidationError("面积过大")

            return str(area_value)

        except (ValueError, InvalidOperation) as e:
            raise ContractValidationError(f"面积格式错误: {value}")

    def _validate_contact(self, value: Any) -> str:
        """验证联系方式"""
        if not value:
            return ""

        contact_str = str(value).strip()

        # 基本长度检查
        if len(contact_str) > 50:
            raise ContractValidationError("联系方式过长")

        return contact_str

    def _validate_text(self, value: Any) -> str:
        """验证文本字段"""
        if not value:
            return ""

        text = str(value).strip()

        # 长度限制
        if len(text) > 500:
            raise ContractValidationError("文本内容过长")

        return text

    def _validate_status(self, value: Any) -> str:
        """验证合同状态"""
        if not value:
            return "草稿"

        status = str(value).strip()

        # 标准化状态值
        for valid_status in self.VALID_STATUSES:
            if fuzz.ratio(status, valid_status) >= 80:
                return valid_status

        # 如果相似度低，返回原始值
        return status

    def _basic_clean(self, value: Any) -> str:
        """基本数据清理"""
        if value is None:
            return ""

        if isinstance(value, str):
            return value.strip()

        return str(value)

    def _validate_business_logic(self, data: Dict[str, Any]) -> List[str]:
        """业务逻辑验证"""
        errors = []

        try:
            # 验证日期逻辑
            if "start_date" in data and "end_date" in data:
                start_date = datetime.strptime(data["start_date"], "%Y-%m-%d")
                end_date = datetime.strptime(data["end_date"], "%Y-%m-%d")

                if start_date >= end_date:
                    errors.append("合同开始日期必须早于结束日期")

                # 检查合同期限是否合理
                duration = (end_date - start_date).days
                if duration > 36500:  # 100年
                    errors.append("合同期限过长")
                elif duration < 1:
                    errors.append("合同期限过短")

            # 验证租金合理性
            if "monthly_rent" in data:
                monthly_rent = Decimal(data["monthly_rent"])
                if monthly_rent <= 0:
                    errors.append("月租金必须大于0")
                elif monthly_rent > 1000000:  # 100万
                    errors.append("月租金金额过大，请检查单位")

            # 验证面积逻辑
            if "total_area" in data and "rentable_area" in data:
                total_area = Decimal(data["total_area"])
                rentable_area = Decimal(data["rentable_area"])

                if rentable_area > total_area:
                    errors.append("租赁面积不能大于总面积")

            # 验证押金合理性
            if "monthly_rent" in data and "total_deposit" in data:
                monthly_rent = Decimal(data["monthly_rent"])
                deposit = Decimal(data["total_deposit"])

                # 押金通常不超过6个月租金
                max_reasonable_deposit = monthly_rent * 6
                if deposit > max_reasonable_deposit:
                    errors.append("押金金额过高，请检查")

        except (ValueError, KeyError, InvalidOperation) as e:
            errors.append(f"业务逻辑验证时出错: {str(e)}")

        return errors

    def _check_data_consistency(self, data: Dict[str, Any]) -> List[str]:
        """数据一致性检查"""
        warnings = []

        # 检查是否有重复的日期字段
        dates = {}
        for field in ["start_date", "end_date", "sign_date"]:
            if field in data and data[field]:
                if data[field] in dates.values():
                    warnings.append(f"发现重复的日期值: {field}")
                dates[field] = data[field]

        # 检查金额字段的一致性
        if "monthly_rent" in data and "annual_income" in data:
            try:
                monthly_rent = Decimal(data["monthly_rent"])
                annual_income = Decimal(data["annual_income"])
                expected_annual = monthly_rent * 12

                # 如果差异超过50%，发出警告
                ratio = annual_income / expected_annual if expected_annual > 0 else 0
                if ratio < 0.5 or ratio > 1.5:
                    warnings.append("年租金与月租金计算结果不一致，请检查")
            except (InvalidOperation, ValueError):
                pass

        return warnings

    def _calculate_validation_score(self, data: Dict[str, Any], errors: List[str], warnings: List[str]) -> float:
        """计算验证分数"""
        # 基础分数：必填字段完成度
        required_count = len(self.REQUIRED_FIELDS)
        completed_required = sum(1 for field in self.REQUIRED_FIELDS.keys() if field in data and data[field])
        base_score = (completed_required / required_count) * 0.6

        # 可选字段分数
        optional_fields = len(self.FIELD_VALIDATORS) - required_count
        completed_optional = len(data) - completed_required
        optional_score = 0
        if optional_fields > 0:
            optional_score = (completed_optional / optional_fields) * 0.2

        # 错误和警告扣分
        error_penalty = min(len(errors) * 0.1, 0.3)
        warning_penalty = min(len(warnings) * 0.05, 0.1)

        final_score = base_score + optional_score - error_penalty - warning_penalty
        return round(max(0.0, final_score), 2)

    def _match_assets_by_address(self, db: Session, address: str) -> List[Dict[str, Any]]:
        """根据地址匹配资产"""
        if not address:
            return []

        try:
            # 使用模糊搜索
            assets = db.query(Asset).all()
            asset_matches = []

            for asset in assets:
                if asset.address:
                    similarity = fuzz.ratio(address.lower(), asset.address.lower())
                    if similarity >= 60:  # 相似度阈值
                        asset_matches.append({
                            "id": asset.id,
                            "property_name": asset.property_name,
                            "address": asset.address,
                            "similarity": similarity
                        })

            # 按相似度排序
            asset_matches.sort(key=lambda x: x["similarity"], reverse=True)
            return asset_matches[:5]  # 返回前5个匹配结果

        except Exception as e:
            logger.error(f"Asset matching failed: {e}")
            return []

    def _match_ownerships_by_name(self, db: Session, name: str) -> List[Dict[str, Any]]:
        """根据名称匹配权属方"""
        if not name:
            return []

        try:
            from ..models.ownership import Ownership
            ownerships = db.query(Ownership).all()
            ownership_matches = []

            for ownership in ownerships:
                if ownership.ownership_name:
                    similarity = fuzz.ratio(name.lower(), ownership.ownership_name.lower())
                    if similarity >= 60:  # 相似度阈值
                        ownership_matches.append({
                            "id": ownership.id,
                            "ownership_name": ownership.ownership_name,
                            "similarity": similarity
                        })

            # 按相似度排序
            ownership_matches.sort(key=lambda x: x["similarity"], reverse=True)
            return ownership_matches[:3]  # 返回前3个匹配结果

        except Exception as e:
            logger.error(f"Ownership matching failed: {e}")
            return []

    def _check_contract_duplicate(self, db: Session, contract_number: str) -> List[Dict[str, Any]]:
        """检查合同编号重复"""
        if not contract_number:
            return []

        try:
            existing_contracts = db.query(RentContract).filter(
                RentContract.contract_number == contract_number
            ).all()

            duplicates = []
            for contract in existing_contracts:
                duplicates.append({
                    "id": contract.id,
                    "contract_number": contract.contract_number,
                    "tenant_name": contract.tenant_name,
                    "created_at": contract.created_at.isoformat() if contract.created_at else None
                })

            return duplicates

        except Exception as e:
            logger.error(f"Contract duplicate check failed: {e}")
            return []

    def _calculate_match_confidence(self, match_result: Dict[str, Any]) -> float:
        """计算匹配置信度"""
        score = 0.0

        # 资产匹配
        if match_result["matched_assets"]:
            best_asset_match = match_result["matched_assets"][0]
            score += (best_asset_match["similarity"] / 100) * 0.4

        # 权属方匹配
        if match_result["matched_ownerships"]:
            best_ownership_match = match_result["matched_ownerships"][0]
            score += (best_ownership_match["similarity"] / 100) * 0.3

        # 重复检查
        if match_result["duplicate_contracts"]:
            score -= 0.5  # 有重复扣分
        else:
            score += 0.3  # 无重复加分

        return round(max(0.0, score), 2)

    def get_validation_summary(self) -> Dict[str, Any]:
        """获取验证器配置摘要"""
        return {
            "required_fields": list(self.REQUIRED_FIELDS.keys()),
            "required_fields_display": self.REQUIRED_FIELDS,
            "total_validators": len(self.FIELD_VALIDATORS),
            "available_validators": list(self.FIELD_VALIDATORS.keys()),
            "valid_statuses": self.VALID_STATUSES
        }


# 创建全局实例
contract_validator = ContractValidator()