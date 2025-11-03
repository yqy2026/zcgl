"""
中文自然语言处理服务
专门处理中文合同中的姓名、地址、电话等信息的提取和标准化
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

import jieba

logger = logging.getLogger(__name__)


@dataclass
class StructuredAddress:
    """结构化地址"""

    original_text: str
    confidence: float = 0.0
    country: str | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None
    street: str | None = None
    building: str | None = None
    room: str | None = None
    number: str | None = None
    postal_code: str | None = None


@dataclass
class StructuredName:
    """结构化姓名"""

    original_text: str
    full_name: str  # 全名
    confidence: float = 0.0
    family_name: str | None = None  # 姓
    given_name: str | None = None  # 名
    gender: str | None = None  # 性别


@dataclass
class StructuredPhone:
    """结构化电话"""

    original_text: str
    phone_number: str
    confidence: float = 0.0
    phone_type: str = "mobile"  # mobile, landline, fax
    is_valid: bool = True
    country_code: str | None = "+86"


@dataclass
class StructuredIDCard:
    """结构化身份证"""

    original_text: str
    id_number: str
    confidence: float = 0.0
    birth_date: str | None = None
    gender: str | None = None
    region: str | None = None
    age: int | None = None
    is_valid: bool = True


@dataclass
class ExtractionEntity:
    """提取的实体"""

    text: str
    entity_type: str  # name, phone, address, id_card, amount, date, etc.
    start_pos: int
    end_pos: int
    confidence: float = 0.0
    metadata: dict[str, Any] = None


class ChineseNLPProcessor:
    """中文自然语言处理服务"""

    def __init__(self):
        # 初始化jieba分词器
        try:
            import jieba

            jieba.initialize()
            logger.info("jieba分词器初始化成功")
        except Exception as e:
            logger.warning(f"jieba初始化失败: {e}")

        # 常见的中文名字
        self.common_family_names = [
            "王",
            "李",
            "张",
            "刘",
            "陈",
            "杨",
            "黄",
            "赵",
            "吴",
            "周",
            "徐",
            "孙",
            "马",
            "朱",
            "胡",
            "郭",
            "何",
            "林",
            "高",
            "罗",
            "郑",
            "梁",
            "谢",
            "宋",
            "唐",
            "许",
            "韩",
            "冯",
            "邓",
            "曹",
            "彭",
            "曾",
            "萧",
            "田",
            "董",
            "袁",
            "潘",
            "于",
            "蒋",
            "蔡",
            "余",
            "杜",
            "叶",
            "程",
            "魏",
            "苏",
            "吕",
            "丁",
            "任",
            "沈",
            "姚",
            "卢",
            "姜",
            "钟",
            "崔",
            "谭",
            "廖",
            "汪",
            "石",
            "金",
            "秦",
            "史",
            "江",
            "范",
            "方",
            "白",
            "邹",
            "孟",
            "章",
            "尹",
            "常",
            "武",
            "乔",
            "贺",
            "龚",
            "庞",
            "庞",
            "康",
        ]

        # 常见的中文名字
        self.common_given_names = [
            "伟",
            "芳",
            "娜",
            "敏",
            "静",
            "丽",
            "强",
            "磊",
            "洋",
            "勇",
            "艳",
            "杰",
            "洁",
            "文",
            "婷",
            "慧",
            "君",
            "小",
            "晓",
            "燕",
            "军",
            "华",
            "平",
            "健",
            "梅",
            "红",
            "新",
            "春",
            "兰",
            "宁",
            "萍",
            "桂",
            "阳",
            "蓉",
            "雪",
            "婷",
            "娟",
            "彦",
            "斌",
            "超",
            "雄",
            "飞",
            "龙",
            "玲",
            "琳",
            "玲",
            "欢",
            "英",
            "颖",
            "红",
            "军",
            "成",
            "芳",
            "琴",
            "瑶",
            "霞",
            "卫",
            "萍",
            "婷",
        ]

    def extract_chinese_names(self, text: str) -> List[StructuredName]:
        """提取中文姓名"""
        names = []

        # 使用正则表达式匹配中文姓名模式
        name_patterns = [
            r"([一-龥]{2,4})(?:[先生|女士|同学|老师|师傅|师傅])?",
            r"(?:姓|名)[：:]\s*([一-龥]{1,3})\s*([一-龥]{1,2})",
            r"([一-龥]{1,2})\s*[、，]\s*([一-龥]{1,2})",
        ]

        for pattern in name_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    # 简单的姓名提取
                    if pattern == name_patterns[0]:  # 主要模式
                        full_name = match.group(1)
                        if len(match.groups()) >= 3:
                            family_name = match.group(1)
                            given_name = match.group(2)
                        else:
                            family_name = None
                            given_name = None
                            full_name = (
                                full_name[:2] if len(full_name) > 2 else full_name
                            )
                    else:
                        continue

                    # 计算置信度
                    confidence = 0.8

                    # 姓名验证
                    if family_name and family_name in self.common_family_names:
                        confidence += 0.1

                    if given_name and given_name in self.common_given_names:
                        confidence += 0.05

                    names.append(
                        StructuredName(
                            original_text=match.group(0),
                            confidence=confidence,
                            family_name=family_name,
                            given_name=given_name,
                            full_name=full_name,
                        )
                    )
                except Exception as e:
                    logger.warning(f"姓名提取失败: {e}")
                    continue

        return names

    def extract_chinese_addresses(self, text: str) -> List[StructuredAddress]:
        """提取中文地址"""
        addresses = []

        # 中文地址正则表达式模式
        address_patterns = [
            r"([^。，\n]*?[省市区县旗区州][：:])\s*([^，。\n]+)",
            r"([^。，\n]*?[市辖区县][：:])\s*([^，。\n]+)",
            r"([^。，\n]*?[路街道巷弄里胡同村][：:])\s*([^，。\n]+)",
            r"([^。，\n]*?[号楼栋层室][：:])\s*([^，。\n]+)",
            r"([一-龥]{2,}[省市区县][一-龥]*?[市辖区县])[^，。\n]*[路街道巷弄里胡同村][一-龥]*?\d+号",
        ]

        for pattern in address_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    # 提取地址各部分
                    groups = match.groups()
                    if len(groups) >= 3:
                        province = groups[0] if len(groups) > 0 else None
                        city = groups[1] if len(groups) > 1 else None
                        street = groups[2] if len(groups) > 2 else None
                    else:
                        province = None
                        city = None
                        street = None

                    confidence = 0.85

                    addresses.append(
                        StructuredAddress(
                            original_text=match.group(0),
                            confidence=confidence,
                            country="中国",
                            province=self._normalize_address_part(province),
                            city=self._normalize_address_part(city),
                            district=None,
                            street=self._normalize_address_part(street),
                            building=None,
                            room=None,
                            number=None,
                            postal_code=None,
                        )
                    )
                except Exception as e:
                    logger.warning(f"地址提取失败: {e}")
                    continue

        return addresses

    def extract_chinese_phones(self, text: str) -> List[StructuredPhone]:
        """提取中文电话号码"""
        phones = []

        # 中国电话号码正则表达式
        phone_patterns = [
            r"1[3-9]\d{9}",  # 13位手机号
            r"\d{3,4}-\d{7,8}",  # 固定电话格式
            r"[+]?\d{1,3}-\d{7,8}",  # 带国际区号
            r"(?:手机|电话|TEL)[：:]?\s*(1[3-9]\d{9})",
            r"(?:手机|电话|TEL)[：:]?\s*(\d{3,4}-\d{7,8})",
        ]

        for pattern in phone_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    phone_number = re.sub(r"[^\d]", "", match.group(0))

                    # 验证手机号
                    if len(phone_number) == 11 and phone_number.startswith("1"):
                        phone_type = "mobile"
                    elif len(phone_number) >= 7 and len(phone_number) <= 12:
                        phone_type = "landline"
                    else:
                        phone_type = "unknown"

                    phones.append(
                        StructuredPhone(
                            original_text=match.group(0),
                            confidence=0.9,
                            phone_number=phone_number,
                            phone_type=phone_type,
                            is_valid=True,
                            country_code="+86",
                        )
                    )
                except Exception as e:
                    logger.warning(f"电话提取失败: {e}")
                    continue

        return phones

    def extract_chinese_id_cards(self, text: str) -> List[StructuredIDCard]:
        """提取中国身份证号码"""
        id_cards = []

        # 18位身份证正则表达式
        id_pattern = r"[1-9]\d{16}[\dXx]"

        matches = re.finditer(id_pattern, text)
        for match in matches:
            try:
                id_number = match.group(0)

                # 简单验证
                is_valid = (
                    len(id_number) == 18
                    and id_number[:17].isdigit()
                    and id_number[-1] in "0123456789X"
                )

                # 提取出生日期
                if len(id_number) >= 14:
                    birth_date = f"19{id_number[6:10]}"
                    gender = "女" if int(id_number[-2]) % 2 == 1 else "男"
                else:
                    birth_date = None
                    gender = None

                # 计算年龄
                age = 2025 - int(birth_date[:4]) if birth_date else None

                id_cards.append(
                    StructuredIDCard(
                        original_text=match.group(0),
                        confidence=0.95 if is_valid else 0.6,
                        id_number=id_number,
                        birth_date=birth_date,
                        gender=gender,
                        region=None,
                        age=age,
                        is_valid=is_valid,
                    )
                )
            except Exception as e:
                logger.warning(f"身份证提取失败: {e}")
                continue

        return id_cards

    def extract_chinese_amounts(self, text: str) -> List[ExtractionEntity]:
        """提取金额信息"""
        amounts = []

        # 中文金额正则表达式
        amount_patterns = [
            r"([一二三四五六七八九十百千万亿]+[零一二三四五六七八九]+元)",
            r"￥\s*(\d+(?:\.\d{1,2})?)\s*元",
            r"(\d+(?:\.\d{1,2})?)\s*万元",
            r"人民币\s*(\d+(?:\.\d{1,2})?)\s*元",
            r"([一二三四五六七八九十百千万亿]+点[一二三四五六七八九十]+元)",
        ]

        for pattern in amount_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    amount_text = match.group(0)
                    confidence = 0.8

                    amounts.append(
                        ExtractionEntity(
                            text=amount_text,
                            entity_type="amount",
                            confidence=confidence,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            metadata={"unit": "元", "pattern": pattern},
                        )
                    )
                except Exception as e:
                    logger.warning(f"金额提取失败: {e}")
                    continue

        return amounts

    def extract_chinese_dates(self, text: str) -> List[ExtractionEntity]:
        """提取日期信息"""
        dates = []

        # 中文日期正则表达式
        date_patterns = [
            r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
            r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",
            r"([二〇一二三四五六七八九]+年[二〇一二三四五六七八九]+月[二〇一二三四五六七八九]+日)",
            r"(\d{1,2})\s*月\s*(\d{1,2})\s*日",
        ]

        for pattern in date_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    date_text = match.group(0)
                    confidence = 0.85

                    dates.append(
                        ExtractionEntity(
                            text=date_text,
                            entity_type="date",
                            confidence=confidence,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            metadata={"format": "chinese"},
                        )
                    )
                except Exception as e:
                    logger.warning(f"日期提取失败: {e}")
                    continue

        return dates

    def _normalize_address_part(self, part: str | None) -> str | None:
        """标准化地址部分"""
        if not part:
            return None

        # 移除空格和特殊字符
        normalized = re.sub(r"\s+", "", part.strip())

        # 标准化省份名称
        province_mapping = {
            "北京": "北京市",
            "天津": "天津市",
            "上海": "上海市",
            "重庆": "重庆市",
            "河北": "河北省",
            "山西": "山西省",
            "辽宁": "辽宁省",
            "吉林": "吉林省",
            "黑龙江": "黑龙江省",
            "江苏": "江苏省",
            "浙江": "浙江省",
            "安徽": "安徽省",
            "福建": "福建省",
            "江西": "江西省",
            "山东": "山东省",
            "河南": "河南省",
            "湖北": "湖北省",
            "湖南": "湖南省",
            "广东": "广东省",
            "海南": "海南省",
            "四川": "四川省",
            "贵州": "贵州省",
            "云南": "云南省",
            "陕西": "陕西省",
            "甘肃": "甘肃省",
            "青海": "青海省",
            "台湾": "台湾省",
        }

        for short_name, full_name in province_mapping.items():
            if short_name in normalized:
                return full_name

        return normalized

    def process_chinese_text(self, text: str) -> Dict[str, Any]:
        """处理中文文本，提取各种实体"""
        if not text or not text.strip():
            return {
                "names": [],
                "addresses": [],
                "phones": [],
                "id_cards": [],
                "amounts": [],
                "dates": [],
                "entities": [],
                "word_count": 0,
                "language": "unknown",
            }

        # 分词
        words = list(jieba.cut(text))
        word_count = len(words)

        # 提取各种实体
        names = self.extract_chinese_names(text)
        addresses = self.extract_chinese_addresses(text)
        phones = self.extract_chinese_phones(text)
        id_cards = self.extract_chinese_id_cards(text)
        amounts = self.extract_chinese_amounts(text)
        dates = self.extract_chinese_dates(text)

        # 合并所有实体
        all_entities = []
        for entity_list in [names, addresses, phones, id_cards, amounts, dates]:
            for entity in entity_list:
                if isinstance(
                    entity,
                    (
                        StructuredName,
                        StructuredAddress,
                        StructuredPhone,
                        StructuredIDCard,
                    ),
                ):
                    all_entities.append(
                        ExtractionEntity(
                            text=entity.original_text,
                            entity_type=entity.__class__.__name__.lower().replace(
                                "structured", ""
                            ),
                            confidence=entity.confidence,
                            start_pos=text.find(entity.original_text),
                            end_pos=text.find(entity.original_text)
                            + len(entity.original_text),
                            metadata={"structured_data": entity},
                        )
                    )
                else:
                    all_entities.append(entity)

        return {
            "names": [name.__dict__ for name in names],
            "addresses": [addr.__dict__ for addr in addresses],
            "phones": [phone.__dict__ for phone in phones],
            "id_cards": [id_card.__dict__ for id_card in id_cards],
            "amounts": [amount.__dict__ for amount in amounts],
            "dates": [date.__dict__ for date in dates],
            "entities": [entity.__dict__ for entity in all_entities],
            "word_count": word_count,
            "language": "chinese",
            "text_stats": {
                "total_length": len(text),
                "chinese_ratio": len([c for c in text if "\u4e00" <= c <= "\u9fff"])
                / len(text),
                "has_chinese": any("\u4e00" <= c <= "\u9fff" for c in text),
            },
        }


# 全局中文NLP处理器实例
# chinese_nlp_processor = ChineseNLPProcessor()  # 注释掉全局实例化


# 创建全局实例的函数
def get_chinese_nlp_processor() -> ChineseNLPProcessor:
    """获取中文NLP处理器实例（延迟初始化）"""
    return ChineseNLPProcessor()
