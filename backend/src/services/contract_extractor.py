#!/usr/bin/env python3
"""
合同信息提取器
智能PDF导入功能的核心提取器，支持真实合同信息的准确提取
包含防虚假数据验证和字段验证功能
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ExtractionMethod(Enum):
    """提取方法"""

    RULE_BASED = "rule_based"
    PATTERN_MATCHING = "pattern_matching"


@dataclass
class ExtractedField:
    """提取的字段"""

    name: str
    value: Any
    confidence: float
    source_text: str
    extraction_method: ExtractionMethod


class ContractExtractor:
    """合同信息提取器 - 智能PDF导入的核心组件"""

    def __init__(self):
        """初始化提取器"""
        self.extraction_rules = self._load_fixed_extraction_rules()

    def _load_fixed_extraction_rules(self) -> dict[str, list[str]]:
        """加载修复后的提取规则"""
        return {
            # 基本信息
            "contract_number": [
                r"合同编号[：:]([^\\s出租方承租方]+)",
                r"合同编号[：:]([^出租方承租方，,。\n]+)",
            ],
            # 出租方信息
            "landlord_name": [
                r"出租方[（(]甲方[）)][：:]([^，,。\n]+?)(?=法定代表人|统一社会|联系地址|联系人|联系电话)",
                r"出租方[（(]甲方[）)][：:]([^，,。\n]+?)(?=统一社会信用代码|联系地址|联系人|联系电话)",
                r"甲方[：:]([^，,。\n]+?)(?=法定代表人|统一社会|联系地址|联系人|联系电话)",
            ],
            "landlord_legal_rep": [
                r"法定代表人[：:]([^，,。\n]+?)(?=统一社会信用代码|联系地址|联系人|联系电话)",
                r"出租方.*?法定代表人[：:]([^，,。\n]+?)(?=统一社会信用代码|联系地址|联系人|联系电话)",
            ],
            "landlord_contact": [
                r"联系人[：:]([^，,。\n]+?)(?=联系电话|电子邮箱)",
                r"出租方.*?联系人[：:]([^，,。\n]+?)(?=联系电话|电子邮箱)",
            ],
            "landlord_phone": [
                r"联系电话[：:]([0-9-]+?)(?=[^\d-]|$)",
                r"出租方.*?联系电话[：:]([0-9-]+?)(?=[^\d-]|$)",
                r"甲方.*?联系电话[：:]([0-9-]+?)(?=[^\d-]|$)",
            ],
            "landlord_address": [
                r"联系地址[：:]([^，,。\n]+?)(?=联系人|联系电话|电子邮箱)",
                r"出租方.*?联系地址[：:]([^，,。\n]+?)(?=联系人|联系电话|电子邮箱)",
            ],
            # 承租方信息
            "tenant_name": [
                r"承租方[（(]乙方[）)][：:]([^，,。\n]+?)(?=身份证号码[:：]|通讯地址[:：]|联系电话[:：])",
                r"承租方[（(]乙方[）)][：:]([^，,。\n]+?)(?=身份证|通讯地址|联系电话)",
                r"承租方[（(]乙方[）)][：:]([^，,。\n]+)",
            ],
            "tenant_id": [
                r"身份证号码[：:]([0-9Xx]+?)(?=通讯地址|联系电话)",
                r"承租方.*?身份证号码[：:]([0-9Xx]+?)(?=通讯地址|联系电话)",
                r"乙方.*?身份证号码[：:]([0-9Xx]+?)(?=通讯地址|联系电话)",
            ],
            "tenant_phone": [
                r"联系电话[：:]([0-9-]+?)(?=[^\d-]|$)",
                r"承租方.*?联系电话[：:]([0-9-]+?)(?=[^\d-]|$)",
                r"乙方.*?联系电话[：:]([0-9-]+?)(?=[^\d-]|$)",
            ],
            "tenant_address": [
                r"通讯地址[：:]([^，,。\n]+?)(?=联系电话)",
                r"承租方.*?通讯地址[：:]([^，,。\n]+?)(?=联系电话)",
                r"乙方.*?通讯地址[：:]([^，,。\n]+?)(?=联系电话)",
            ],
            # 物业信息
            "property_address": [
                r"租赁物业位于([^，,。\n]+?)(?:\d+\.\d*|\d*\.?\d+).*?平方米",
                r"物业地址[：:]([^，,。\n]+?)(?:\d+\.\d*|\d*\.?\d+).*?平方米",
                r"租赁房屋地址[：:]([^，,。\n]+?)(?:\d+\.\d*|\d*\.?\d+).*?平方米",
            ],
            "property_area": [
                r"建筑面积为(\d+(?:\.\d+)?)平方米",
                r"建筑面积[：:](\d+(?:\.\d+)?)平方米",
                r"面积[：:](\d+(?:\.\d+)?)平方米",
            ],
            "property_certificate": [
                r"权属证号[：:]([^，,。\n]+?)(?=\d|第|号|$)",
                r"不动产权证号[：:]([^，,。\n]+?)(?=\d|第|号|$)",
            ],
            # 租赁期限
            "lease_start_date": [
                r"自(\d{4}年\d{1,2}月\d{1,2}日)起",
                r"租赁期限[：:][^自]*自(\d{4}年\d{1,2}月\d{1,2}日)",
                r"起租日期[：:](\d{4}年\d{1,2}月\d{1,2}日)",
            ],
            "lease_end_date": [
                r"至(\d{4}年\d{1,2}月\d{1,2}日)止",
                r"至(\d{4}年\d{1,2}月\d{1,2}日)",
                r"终止日期[：:](\d{4}年\d{1,2}月\d{1,2}日)",
            ],
            "lease_duration_years": [
                r"租赁期限为(\d+)年",
                r"租期[：:](\d+)年",
                r"期限为(\d+)年",
            ],
            # 金额信息
            "monthly_rent": [
                r"月租金为人民币(\d+(?:\.\d+)?)元",
                r"月租金[为：:](\d+(?:\.\d+)?)元",
                r"租金[为：:](\d+(?:\.\d+)?)元/月",
                r"(\d+(?:\.\d+)?)元/月",
            ],
            "security_deposit": [
                r"保证金金额[为]*人民币(\d+(?:\.\d+)?)元",
                r"保证金[为：:]人民币(\d+(?:\.\d+)?)元",
                r"租赁保证金为(\d+(?:\.\d+)?)元",
                r"押金[：:](\d+(?:\.\d+)?)元",
            ],
            "annual_rent": [r"年租金为(\d+(?:\.\d+)?)元", r"年租金[：:]([0-9.]+)元"],
            "contract_date": [
                r"签订日期[：:](\d{4}年\d{1,2}月\d{1,2}日)",
                r"日期[：:](\d{4}年\d{1,2}月\d{1,2}日)",
                r"于(\d{4}年\d{1,2}月\d{1,2}日)签订",
            ],
            # 其他条款
            "rent_free_period": [
                r"免租期为(\d+)天",
                r"免租期[：:](\d+)天",
                r"免租(\d+)天",
            ],
            "payment_method": [
                r"支付方式[：:]([^。\n]+)",
                r"付款方式[：:]([^。\n]+)",
                r"租金支付[：:]([^。\n]+)",
            ],
            "sign_date": [
                r"签订日期[：:](\d{4}年\d{1,2}月\d{1,2}日)",
                r"签署日期[：:](\d{4}年\d{1,2}月\d{1,2}日)",
                r"合同签订日期[：:](\d{4}年\d{1,2}月\d{1,2}日)",
            ],
        }

    def extract_contract_info(self, text: str) -> dict[str, Any]:
        """
        从合同文本中提取信息

        Args:
            text: 合同文本内容

        Returns:
            提取结果字典
        """
        logger.info("开始使用修复后的提取器处理合同文本")

        # 验证输入文本
        if not text or not isinstance(text, str):
            logger.error("输入文本无效")
            return {
                "success": False,
                "error": "输入文本无效",
                "extracted_fields": {},
                "overall_confidence": 0.0,
            }

        # 检查是否包含真实的合同信息（防止返回虚假数据）
        if not self._validate_real_contract_text(text):
            logger.warning("输入文本可能不是真实的合同内容")
            return {
                "success": False,
                "error": "输入文本可能不是真实的合同内容",
                "extracted_fields": {},
                "overall_confidence": 0.0,
            }

        try:
            # 预处理文本
            cleaned_text = self._preprocess_text(text)

            # 提取字段
            extracted_fields = {}
            total_confidence = 0.0
            field_count = 0

            for field_name, patterns in self.extraction_rules.items():
                for pattern in patterns:
                    try:
                        match = re.search(
                            pattern, cleaned_text, re.IGNORECASE | re.MULTILINE
                        )
                        if match:
                            value = self._clean_extracted_value(
                                field_name, match.group(1).strip()
                            )

                            if value and self._validate_field_value(field_name, value):
                                confidence = self._calculate_confidence(
                                    field_name, match.group(0)
                                )

                                extracted_fields[field_name] = {
                                    "value": value,
                                    "confidence": confidence,
                                    "source_text": match.group(0),
                                    "extraction_method": "rule_based",
                                }

                                total_confidence += confidence
                                field_count += 1
                                logger.info(
                                    f"成功提取字段 {field_name}: {value} (置信度: {confidence:.2f})"
                                )
                                break
                    except Exception as e:
                        logger.warning(f"提取字段 {field_name} 时出错: {e}")
                        continue

            # 计算总体置信度
            overall_confidence = (
                total_confidence / field_count if field_count > 0 else 0.0
            )

            # 构建响应
            result = {
                "success": True,
                "extracted_fields": extracted_fields,
                "overall_confidence": overall_confidence,
                "fields_extracted": field_count,
                "extraction_method": "fixed_rental_contract_extractor",
                "validation_passed": True,
            }

            logger.info(
                f"提取完成，共提取 {field_count} 个字段，总体置信度: {overall_confidence:.2f}"
            )
            return result

        except Exception as e:
            logger.error(f"合同信息提取失败: {e}")
            return {
                "success": False,
                "error": f"提取失败: {str(e)}",
                "extracted_fields": {},
                "overall_confidence": 0.0,
            }

    def _validate_real_contract_text(self, text: str) -> bool:
        """验证是否为真实的合同文本（防止返回虚假数据）"""

        # 检查是否包含基本的合同关键词
        contract_keywords = ["出租方", "承租方", "租赁", "租金", "合同"]
        keyword_count = sum(1 for keyword in contract_keywords if keyword in text)

        if keyword_count < 3:
            logger.warning("文本中缺少基本合同关键词")
            return False

        # 检查是否包含示例数据特征（这些是已知的虚假数据标识）
        fake_data_patterns = [
            r"张三",
            r"李四",
            r"王五",  # 常见示例姓名
            r"北京某某",
            r"某某小区",
            r"某某街道",  # 示例地址
            r"13800138000",
            r"HT-2024",  # 示例电话和合同编号
            r"示例",
            r"test",  # 测试标识 (保留中文"测试"用于正常测试)
        ]

        for pattern in fake_data_patterns:
            if re.search(pattern, text):
                logger.warning(f"检测到可能的示例数据: {pattern}")
                return False

        # 检查文本长度 - 真实合同通常较长
        if len(text.strip()) < 20:
            logger.warning("文本过短，可能不是真实合同")
            return False

        return True

    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 移除多余的空白字符
        text = re.sub(r"\s+", " ", text)

        # 修复常见的OCR错误
        text = text.replace(" ", "")

        return text.strip()

    def _clean_extracted_value(self, field_name: str, value: str) -> Any:
        """清洗提取的字段值"""
        if not value:
            return None

        # 移除多余的空白字符
        value = re.sub(r"\s+", "", value).strip()

        # 根据字段类型进行特殊处理
        if field_name in ["monthly_rent", "security_deposit", "annual_rent"]:
            # 金额字段：提取数字
            amount_match = re.search(r"(\d+(?:\.\d+)?)", value)
            if amount_match:
                return float(amount_match.group(1))

        elif field_name in ["lease_duration_years", "rent_free_period"]:
            # 数字字段
            number_match = re.search(r"(\d+)", value)
            if number_match:
                return int(number_match.group(1))

        elif field_name.endswith("_date"):
            # 日期字段保持原样
            return value

        else:
            # 文本字段
            return value if value else None

    def _validate_field_value(self, field_name: str, value: Any) -> bool:
        """验证字段值的有效性"""
        if value is None:
            return False

        value_str = str(value).strip()

        # 检查是否包含虚假数据模式
        if self._contains_fake_data(value_str):
            return False

        if field_name in ["monthly_rent", "security_deposit", "annual_rent"]:
            # 金额必须为正数且在合理范围内
            try:
                amount = float(value_str)
                return 0 < amount <= 10000000  # 10万元以下合理
            except (ValueError, TypeError):
                return False

        elif field_name in ["lease_duration_years", "rent_free_period"]:
            # 年限和天数必须为正整数且在合理范围内
            try:
                num = int(value_str)
                if field_name == "lease_duration_years":
                    return 0 < num <= 50  # 租期不超过50年
                else:  # rent_free_period
                    return 0 <= num <= 365  # 免租期不超过一年
            except (ValueError, TypeError):
                return False

        elif field_name.endswith("_phone"):
            # 电话号码格式验证
            phone_patterns = [
                r"^1[3-9]\d{9}$",  # 手机号
                r"^0\d{2,3}-?\d{7,8}$",  # 固定电话
                r"^\d{3,4}-\d{7,8}$",  # 带区号的固定电话
            ]
            return any(re.match(pattern, value_str) for pattern in phone_patterns)

        elif field_name.endswith("_name"):
            # 姓名不能包含特殊字符，长度合理
            if len(value_str) < 2 or len(value_str) > 50:
                return False
            # 检查是否包含数字或特殊字符
            if re.search(r'[0-9@#$%^&*()+=\[\]{}|\\:";\'<>?,./]', value_str):
                return False
            # 检查是否为常见的虚假姓名
            fake_names = ["张三", "李四", "王五", "赵六", "测试", "test", "demo"]
            if value_str in fake_names:
                return False

        elif field_name.endswith("_id") or field_name == "tenant_id":
            # 身份证号验证
            id_pattern = r"^\d{17}[\dXx]$"
            return bool(re.match(id_pattern, value_str))

        elif field_name == "contract_number":
            # 合同编号验证 - 不能太短或包含明显虚假内容
            if len(value_str) < 3:
                return False
            fake_patterns = ["HT-2024", "TEST", "示例", "test"]
            if any(fake in value_str.upper() for fake in fake_patterns):
                return False

        elif field_name.endswith("_area"):
            # 面积验证 - 必须为正数且在合理范围内
            try:
                area = float(value_str)
                return 1 <= area <= 10000  # 1-10000平方米合理
            except (ValueError, TypeError):
                return False

        elif field_name.endswith("_date"):
            # 日期格式验证
            date_pattern = r"^\d{4}年\d{1,2}月\d{1,2}日$"
            if not re.match(date_pattern, value_str):
                return False
            # 验证日期的合理性
            try:
                import datetime

                year = int(re.search(r"(\d{4})年", value_str).group(1))
                month = int(re.search(r"(\d{1,2})月", value_str).group(1))
                day = int(re.search(r"(\d{1,2})日", value_str).group(1))
                datetime.date(year, month, day)
                return True
            except (ValueError, AttributeError, TypeError):
                return False

        return len(value_str) > 0 and len(value_str) <= 500  # 基本长度检查

    def _contains_fake_data(self, text: str) -> bool:
        """检查文本是否包含虚假数据模式"""
        fake_patterns = [
            r"张三|李四|王五|赵六",  # 常见测试姓名
            r"北京某某|上海某某|广州某某",  # 模糊地名
            r"某某小区|某某街道|某某公司",  # 模糊机构名
            r"13800138000|13900139000",  # 常见测试手机号
            r"HT-2024|TEST|示例|test|demo",  # 测试标识
            r"示例公司|测试公司",  # 测试公司名
        ]

        return any(re.search(pattern, text, re.IGNORECASE) for pattern in fake_patterns)

    def _calculate_confidence(self, field_name: str, source_text: str) -> float:
        """计算字段提取的置信度"""
        base_confidence = 0.8

        # 根据源文本的完整性调整置信度
        if len(source_text) > 20:
            base_confidence += 0.1

        # 根据字段重要性调整置信度
        important_fields = [
            "contract_number",
            "tenant_name",
            "landlord_name",
            "monthly_rent",
        ]
        if field_name in important_fields:
            base_confidence += 0.1

        # 确保置信度不超过1.0
        return min(base_confidence, 1.0)


def extract_contract_info(text: str) -> dict[str, Any]:
    """
    便捷函数：使用合同提取器提取合同信息

    Args:
        text: 合同文本内容

    Returns:
        提取结果字典
    """
    extractor = ContractExtractor()
    return extractor.extract_contract_info(text)


if __name__ == "__main__":
    # 测试代码
    test_text = """
    第1页:
    租赁合同 合同编号:包装合字（225）第22号 出租方（甲方）:广州包装制品厂发展有限公司
    法定代表人:朱明 联系地址:广州市荔湾区花地涌岸街36号 联系人:章培德 联系电话:20-83178453
    承租方（乙方）:王军 身份证号码:448231979070919 通讯地址:广州市番禺区洛浦街南浦环岛西路29号1号商业楼14号 联系电话:13352841666

    第一条租赁标的
    1.1．租赁物业位于广州市番禺区南浦环岛西路29号1号商业楼14号，建筑面积为110.5平方米

    第二条租赁期限
    2.1 租赁期限为3年，自2025年4月1日起至2028年3月31日止。

    第三条租金及支付方式
    3.1 月租金为7483元，免租期优惠后实际为7172元/月
    3.2 租赁保证金为10000元
    """

    # TODO: 实现extract_fixed_rent_contract_info函数
    # result = extract_fixed_rent_contract_info(test_text)
    # print("修复后的提取器测试结果:")
    # print(json.dumps(result, ensure_ascii=False, indent=2))
