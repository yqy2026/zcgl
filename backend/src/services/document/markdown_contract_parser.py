#!/usr/bin/env python3
"""
Markdown 合同解析器
从 PP-StructureV3 输出的 Markdown 格式中提取合同字段
"""

import logging
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RentTerm:
    """租金条款"""

    period_start: str | None = None
    period_end: str | None = None
    monthly_rent: Decimal | None = None
    management_fee: Decimal | None = None
    rent_adjustment_rate: float | None = None
    notes: str | None = None


@dataclass
class ContractParty:
    """合同当事人"""

    name: str | None = None
    legal_representative: str | None = None
    id_number: str | None = None
    address: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None


@dataclass
class PropertyInfo:
    """物业信息"""

    name: str | None = None
    address: str | None = None
    area: Decimal | None = None
    certificate_number: str | None = None
    usage: str | None = None


@dataclass
class ContractInfo:
    """合同信息汇总"""

    contract_number: str | None = None
    sign_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    duration_years: int | None = None

    landlord: ContractParty = field(default_factory=ContractParty)
    tenant: ContractParty = field(default_factory=ContractParty)
    property_info: PropertyInfo = field(default_factory=PropertyInfo)

    monthly_rent: Decimal | None = None
    deposit: Decimal | None = None
    rent_free_period: int | None = None  # 免租期（月）
    payment_cycle: str | None = None  # 月付/季付/年付

    rent_terms: list[RentTerm] = field(default_factory=list)

    confidence_score: float = 0.0
    extraction_method: str = "markdown_parser"
    raw_text: str = ""


class MarkdownContractParser:
    """
    Markdown 合同解析器

    从 PP-StructureV3 输出的 Markdown 中提取合同关键字段
    """

    def __init__(self) -> None:
        """初始化解析器"""
        self.patterns = self._build_patterns()

    def _build_patterns(self) -> dict[str, list[str]]:
        """构建提取模式"""
        return {
            # 合同编号
            "contract_number": [
                r"合同编号[：:]\s*([^\s\n]+)",
                r"编号[：:]\s*([^\s\n]+)",
                r"合字[（(](\d+)[)）]第(\d+)号",
            ],
            # 日期
            "sign_date": [
                r"签订日期[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)",
                r"签署日期[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)",
            ],
            "start_date": [
                r"自\s*(\d{4}年\d{1,2}月\d{1,2}日)\s*起",
                r"起租日[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)",
                r"租赁期限.*?自\s*(\d{4}年\d{1,2}月\d{1,2}日)",
            ],
            "end_date": [
                r"至\s*(\d{4}年\d{1,2}月\d{1,2}日)\s*止",
                r"到期日[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)",
                r"租赁期限.*?至\s*(\d{4}年\d{1,2}月\d{1,2}日)",
            ],
            # 金额 - 使用更灵活的模式
            "monthly_rent": [
                r"月租金[为是]?\s*(?:人民币)?\s*(\d+(?:[,，]\d{3})*(?:\.\d+)?)\s*元",
                r"每月租金[为是]?\s*(?:人民币)?\s*(\d+(?:[,，]\d{3})*(?:\.\d+)?)\s*元",
            ],
            "deposit": [
                r"(?:租赁)?保证金[为是]?\s*(?:人民币)?\s*(\d+(?:[,，]\d{3})*(?:\.\d+)?)\s*元",
                r"押金[为是]?\s*(?:人民币)?\s*(\d+(?:[,，]\d{3})*(?:\.\d+)?)\s*元",
            ],
            # 当事人 - 使用更精确的边界
            "landlord_name": [
                r"出租方[（(]甲方[)）][：:：]?\s*([\u4e00-\u9fa5]+(?:公司|企业|中心|店|厂))",
                r"甲方[：:：]\s*([\u4e00-\u9fa5]+(?:公司|企业|中心|店|厂))",
            ],
            "tenant_name": [
                r"承租方[（(]乙方[)）][：:：]?\s*([\u4e00-\u9fa5]{2,4})(?=\s|身份|地址|$)",
                r"乙方[：:：]\s*([\u4e00-\u9fa5]{2,4})(?=\s|身份|地址|租赁|$)",
            ],
            # 物业
            "property_address": [
                r"租赁物业位于\s*([^\n]+?)(?=，|,|建筑面积)",
                r"物业地址[：:]\s*([^\n]+)",
                r"房屋座落[：:]\s*([^\n]+)",
            ],
            "property_area": [
                r"建筑面积[为：:]\s*(\d+(?:\.\d+)?)\s*平方米",
                r"面积[为：:]\s*(\d+(?:\.\d+)?)\s*平方米",
                r"(\d+(?:\.\d+)?)\s*平方米",
            ],
            # 期限
            "duration_years": [
                r"租赁期限[为：:]\s*(\d+)\s*年",
                r"租期[为：:]\s*(\d+)\s*年",
            ],
            # 免租期
            "rent_free_period": [
                r"免租期[为：:]\s*(\d+)\s*个月",
                r"免租\s*(\d+)\s*个月",
            ],
        }

    def parse(self, text: str) -> ContractInfo:
        """
        解析合同文本

        Args:
            text: Markdown 格式或纯文本的合同内容

        Returns:
            ContractInfo 对象
        """
        logger.info("开始解析合同文本")

        # 预处理文本
        cleaned_text = self._preprocess(text)

        # 创建结果对象
        contract = ContractInfo(raw_text=cleaned_text)

        # 提取基本字段
        contract.contract_number = self._extract_field("contract_number", cleaned_text)
        contract.sign_date = self._extract_field("sign_date", cleaned_text)
        contract.start_date = self._extract_field("start_date", cleaned_text)
        contract.end_date = self._extract_field("end_date", cleaned_text)

        # 提取金额
        monthly_rent = self._extract_field("monthly_rent", cleaned_text)
        if monthly_rent:
            contract.monthly_rent = self._parse_amount(monthly_rent)

        deposit = self._extract_field("deposit", cleaned_text)
        if deposit:
            contract.deposit = self._parse_amount(deposit)

        # 提取当事人
        contract.landlord.name = self._extract_field("landlord_name", cleaned_text)
        contract.tenant.name = self._extract_field("tenant_name", cleaned_text)

        # 提取物业信息
        contract.property_info.address = self._extract_field(
            "property_address", cleaned_text
        )
        area = self._extract_field("property_area", cleaned_text)
        if area:
            try:
                contract.property_info.area = Decimal(area)
            except Exception:  # nosec B110  # Intentional: skip field if parsing fails
                pass

        # 提取期限
        duration = self._extract_field("duration_years", cleaned_text)
        if duration:
            try:
                contract.duration_years = int(duration)
            except Exception:  # nosec B110  # Intentional: skip field if parsing fails
                pass

        # 提取免租期
        rent_free = self._extract_field("rent_free_period", cleaned_text)
        if rent_free:
            try:
                contract.rent_free_period = int(rent_free)
            except Exception:  # nosec B110  # Intentional: skip field if parsing fails
                pass

        # 提取阶梯租金表格
        contract.rent_terms = self._extract_rent_terms_from_tables(cleaned_text)

        # 计算置信度
        contract.confidence_score = self._calculate_confidence(contract)

        logger.info(f"合同解析完成，置信度: {contract.confidence_score:.2f}")

        return contract

    def _preprocess(self, text: str) -> str:
        """预处理文本"""
        # 保留换行符的同时移除多余空白
        lines = text.split("\n")
        cleaned_lines = [re.sub(r"[ \t]+", " ", line.strip()) for line in lines]
        text = " ".join(line for line in cleaned_lines if line)
        # 统一标点 - 保留中文标点以便正则匹配
        return text.strip()

    def _extract_field(self, field_name: str, text: str) -> str | None:
        """提取单个字段"""
        patterns = self.patterns.get(field_name, [])

        for pattern in patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    # 返回第一个捕获组
                    value = match.group(1).strip()
                    if value:
                        logger.debug(f"提取字段 {field_name}: {value}")
                        return value
            except Exception as e:
                logger.warning(f"提取 {field_name} 时出错: {e}")

        return None

    def _parse_amount(self, amount_str: str) -> Decimal | None:
        """解析金额字符串"""
        try:
            # 移除逗号
            cleaned = amount_str.replace(",", "").replace("，", "")
            return Decimal(cleaned)
        except Exception:
            return None

    def _extract_rent_terms_from_tables(self, text: str) -> list[RentTerm]:
        """
        从表格中提取阶梯租金条款

        支持 Markdown 表格格式
        """
        rent_terms = []

        # 匹配 Markdown 表格
        table_pattern = r"\|[^\n]+\|(?:\n\|[^\n]+\|)+"

        for table_match in re.finditer(table_pattern, text):
            table_text = table_match.group()

            # 检查是否为租金相关表格
            if any(
                keyword in table_text for keyword in ["租金", "月租", "年租", "期限"]
            ):
                terms = self._parse_rent_table(table_text)
                rent_terms.extend(terms)

        return rent_terms

    def _parse_rent_table(self, table_text: str) -> list[RentTerm]:
        """解析租金表格"""
        terms: list[RentTerm] = []

        # 按行分割
        lines = [line.strip() for line in table_text.split("\n") if line.strip()]

        if len(lines) < 3:  # 至少需要表头、分隔符、一行数据
            return terms

        # 解析表头
        header = [cell.strip() for cell in lines[0].split("|") if cell.strip()]

        # 跳过分隔行 (---)
        data_lines = [
            line for line in lines[2:] if not re.match(r"^\|[\s\-:]+\|$", line)
        ]

        # 解析数据行
        for line in data_lines:
            cells = [cell.strip() for cell in line.split("|") if cell.strip()]
            if len(cells) >= 2:
                term = RentTerm()

                for i, cell in enumerate(cells):
                    if i < len(header):
                        col_name = header[i].lower()

                        if "期限" in col_name or "阶段" in col_name or "年" in col_name:
                            # 解析期限
                            dates = re.findall(
                                r"\d{4}[年.\-/]\d{1,2}[月.\-/]?\d{0,2}日?", cell
                            )
                            if len(dates) >= 2:
                                term.period_start = dates[0]
                                term.period_end = dates[1]
                            elif len(dates) == 1:
                                term.period_start = dates[0]

                        elif "月租" in col_name or "租金" in col_name:
                            amount = self._parse_amount(re.sub(r"[^\d.,]", "", cell))
                            if amount:
                                term.monthly_rent = amount

                if term.monthly_rent or term.period_start:
                    terms.append(term)

        return terms

    def _calculate_confidence(self, contract: ContractInfo) -> float:
        """计算提取置信度"""
        required_fields = [
            contract.contract_number,
            contract.landlord.name,
            contract.tenant.name,
            contract.start_date,
            contract.end_date,
            contract.monthly_rent,
        ]

        extracted_count = sum(1 for f in required_fields if f)
        total_count = len(required_fields)

        base_score = extracted_count / total_count if total_count > 0 else 0

        # 额外加分
        if contract.rent_terms:
            base_score += 0.1
        if contract.property_info.address:
            base_score += 0.05
        if contract.deposit:
            base_score += 0.05

        return min(base_score, 1.0)

    def to_dict(self, contract: ContractInfo) -> dict[str, Any]:
        """
        将 ContractInfo 转换为字典

        Args:
            contract: ContractInfo 对象

        Returns:
            字典格式的合同信息
        """
        rent_terms_list = []
        for term in contract.rent_terms:
            rent_terms_list.append(
                {
                    "period_start": term.period_start,
                    "period_end": term.period_end,
                    "monthly_rent": float(term.monthly_rent)
                    if term.monthly_rent
                    else None,
                    "management_fee": float(term.management_fee)
                    if term.management_fee
                    else None,
                    "notes": term.notes,
                }
            )

        return {
            "contract_number": contract.contract_number,
            "sign_date": contract.sign_date,
            "start_date": contract.start_date,
            "end_date": contract.end_date,
            "duration_years": contract.duration_years,
            "landlord": {
                "name": contract.landlord.name,
                "legal_representative": contract.landlord.legal_representative,
                "address": contract.landlord.address,
                "contact_person": contract.landlord.contact_person,
                "phone": contract.landlord.phone,
            },
            "tenant": {
                "name": contract.tenant.name,
                "id_number": contract.tenant.id_number,
                "address": contract.tenant.address,
                "phone": contract.tenant.phone,
            },
            "property": {
                "address": contract.property_info.address,
                "area": float(contract.property_info.area)
                if contract.property_info.area
                else None,
                "certificate_number": contract.property_info.certificate_number,
            },
            "monthly_rent": float(contract.monthly_rent)
            if contract.monthly_rent
            else None,
            "deposit": float(contract.deposit) if contract.deposit else None,
            "rent_free_period": contract.rent_free_period,
            "payment_cycle": contract.payment_cycle,
            "rent_terms": rent_terms_list,
            "confidence_score": contract.confidence_score,
            "extraction_method": contract.extraction_method,
        }


# 单例实例
_parser = None


def get_markdown_contract_parser() -> MarkdownContractParser:
    """获取解析器单例"""
    global _parser
    if _parser is None:
        _parser = MarkdownContractParser()
    return _parser


def parse_contract_markdown(text: str) -> dict[str, Any]:
    """
    便捷函数：解析合同 Markdown

    Args:
        text: 合同文本

    Returns:
        字典格式的合同信息
    """
    parser = get_markdown_contract_parser()
    contract = parser.parse(text)
    return parser.to_dict(contract)
