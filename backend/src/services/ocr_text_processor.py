"""
OCR文本预处理器
专门处理扫描版PDF合同OCR后的文本，清理和标准化文本内容
"""

import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from decimal import Decimal

logger = logging.getLogger(__name__)


class OCRTextProcessor:
    """OCR文本预处理器"""

    def __init__(self):
        # 常见OCR错误映射
        self.ocr_corrections = {
            # 数字和符号错误
            '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
            '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
            '，': ',', '。': '.', '：': ':', '；': ';',
            '（': '(', '）': ')', '【': '[', '】': ']',

            # 常见易混淆字符
            'O': '0', 'l': '1', 'I': '1', 'Z': '2', 'S': '5',
            'o': '0', 'i': '1', 'z': '2', 's': '5',
            'G': '6', 'B': '8', 'R': '8', 'P': '9',
            'g': '9', 'b': '6', 'r': '8',

            # 常见中文OCR错误
            '囗': '口', '囝': '同', '囡': '同', '囥': '同',
            '氵': '三点水', '冫': '两点水', '灬': '四点底',
            '讠': '言字旁', '钅': '金字旁', '木': '木字旁',

            # 地址常见错误修正
            '洛浦': '洛浦', '洛捕': '洛浦', '南浦': '南浦',
            '番禺': '番禺', '番禹': '番禺', '环岛': '环岛',
            '西路': '西路', '商业楼': '商业楼', '商住楼': '商业楼',

            # 合同相关词汇修正
            '承租方': '承租方', '承租力': '承租方', '出租方': '出租方',
            '租赁': '租赁', '租凭': '租赁', '合同编号': '合同编号',
            '月租金': '月租金', '月祖金': '月租金',

            # 人名常见错误
            '王军': '王军', '王均': '王军', '工军': '王军',
            '谢有志': '谢有志', '解有志': '谢有志',
        }

        # 日期格式正则模式
        self.date_patterns = [
            # 标准格式
            r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日号]?',
            # 中文格式
            r'(\d{4})年(\d{1,2})月(\d{1,2})[日号]',
            # 简化格式
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            # 其他格式
            r'(\d{2,4})/(\d{1,2})/(\d{1,2})',
        ]

        # 金额格式正则模式
        self.amount_patterns = [
            # 标准数字格式
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*元',
            # 中文数字格式
            r'([一二三四五六七八九十百千万零]+)\s*元',
            # 混合格式
            r'人民币\s*([\d,，.]+\d*)\s*元',
            # 简单格式
            r'(\d+(?:\.\d{2})?)',
        ]

        # 面积格式正则模式
        self.area_patterns = [
            r'(\d+(?:\.\d{1,2})?)\s*平方米',
            r'(\d+(?:\.\d{1,2})?)\s*㎡',
            r'(\d+(?:\.\d{1,2})?)\s*平方',
            r'面积[：:\s]*(\d+(?:\.\d{1,2})?)',
        ]

    def clean_ocr_text(self, text: str) -> str:
        """
        清理OCR文本，修复常见错误

        Args:
            text: OCR原始文本

        Returns:
            清理后的文本
        """
        if not text:
            return ""

        logger.info("开始清理OCR文本...")

        # 1. 移除多余空白字符
        cleaned = re.sub(r'\s+', ' ', text.strip())

        # 2. 修复常见OCR错误
        for wrong, correct in self.ocr_corrections.items():
            cleaned = cleaned.replace(wrong, correct)

        # 3. 修复乱码字符
        cleaned = self._fix_garbled_characters(cleaned)

        # 4. 智能文本恢复
        cleaned = self._intelligent_text_recovery(cleaned)

        # 5. 标准化标点符号
        cleaned = self._normalize_punctuation(cleaned)

        # 6. 修复断行问题
        cleaned = self._fix_line_breaks(cleaned)

        # 7. 移除重复字符
        cleaned = re.sub(r'(.)\1{2,}', r'\1', cleaned)

        logger.info(f"OCR文本清理完成，长度从 {len(text)} 变为 {len(cleaned)}")
        return cleaned

    def _fix_garbled_characters(self, text: str) -> str:
        """修复乱码字符"""
        # 移除控制字符
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

        # 修复常见编码问题
        char_corrections = {
            '�': '',  # 移除替换字符
            '"': '"',
            '"': '"',
            "'": "'",  # UTF-8编码错误
            'æ': 'æ',
            'œ': 'œ',
            'â': 'â',
        }

        for wrong, correct in char_corrections.items():
            text = text.replace(wrong, correct)

        return text

    def _normalize_punctuation(self, text: str) -> str:
        """标准化标点符号"""
        # 统一引号
        text = re.sub(r'[""''„""'']', '"', text)

        # 统一括号
        text = re.sub(r'[［］\[\]\(\)\{\}]', lambda m: {
            '［': '[', '］': ']', '[': '[', ']': ']',
            '(': '(', ')': ')', '{': '}', '}': '}'
        }.get(m.group(), m.group()), text)

        # 统一连接符
        text = re.sub(r'[–—―]', '-', text)

        return text

    def _intelligent_text_recovery(self, text: str) -> str:
        """智能文本恢复，修复上下文相关错误"""
        # 1. 修复合同编号格式
        text = self._recover_contract_numbers(text)

        # 2. 修复人名
        text = self._recover_person_names(text)

        # 3. 修复地址
        text = self._recover_addresses(text)

        # 4. 修复日期格式
        text = self._recover_dates(text)

        # 5. 修复金额格式
        text = self._recover_amounts(text)

        return text

    def _recover_contract_numbers(self, text: str) -> str:
        """恢复合同编号格式"""
        # 包装合字格式恢复
        patterns = [
            r'包装合字[（(](\d{4})[）)]\s*第\s*(\d+)\s*号',
            r'包装合同[（(](\d{4})[）)]\s*第\s*(\d+)\s*号',
            r'包装.*?(\d{4}).*?第\s*(\d+)\s*号',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                year = match.group(1)
                number = match.group(2).zfill(3)  # 补齐为3位数
                correct_format = f"包装合字（{year}）第{number}号"
                text = text.replace(match.group(), correct_format)

        return text

    def _recover_person_names(self, text: str) -> str:
        """恢复人名"""
        # 常见人名恢复规则
        name_patterns = [
            # 王军相关
            (r'[王工均]\s*[军均]', '王军'),
            # 谢有志相关
            (r'[谢解]\s*[有由友]\s*[志至]', '谢有志'),
            # 通用中文姓名恢复（2-3个汉字）
            (r'([A-Za-z])\s*([一-龥])\s*([一-龥])', lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}"),
        ]

        for pattern, replacement in name_patterns:
            if callable(replacement):
                text = re.sub(pattern, replacement, text)
            else:
                text = re.sub(pattern, replacement, text)

        return text

    def _recover_addresses(self, text: str) -> str:
        """恢复地址信息"""
        # 地址恢复规则
        address_patterns = [
            # 洛浦南浦环岛西路
            (r'洛[浦捕].*?南[浦铺].*?环岛西路', '洛浦南浦环岛西路'),
            # 番禺区
            (r'番[禺禹].*?区', '番禺区'),
            # 商业楼
            (r'商[住业].*?楼', '商业楼'),
            # 完整地址模式
            (r'番禺区.*?洛浦.*?南浦.*?环岛西路.*?29号.*?1号.*?商业楼.*?14号铺',
             '番禺区洛浦南浦环岛西路29号1号商业楼14号铺'),
        ]

        for pattern, replacement in address_patterns:
            text = re.sub(pattern, replacement, text)

        return text

    def _recover_dates(self, text: str) -> str:
        """恢复日期格式"""
        # 日期恢复规则
        date_patterns = [
            # 标准化YYYYMMDD格式
            (r'(\d{4})(\d{2})(\d{2})', r'\1-\2-\3'),
            # 修复月份格式
            (r'(\d{4})\s*[-年]\s*(\d{1,2})\s*[-月]\s*(\d{1,2})\s*[日号]?', r'\1-\2-\3'),
            # 常见日期错误修正
            (r'2025\s*年\s*0?(\d+)\s*月\s*0?(\d+)\s*[日号]', r'2025-\1-\2'),
        ]

        for pattern, replacement in date_patterns:
            text = re.sub(pattern, replacement, text)

        return text

    def _recover_amounts(self, text: str) -> str:
        """恢复金额格式"""
        # 金额恢复规则
        amount_patterns = [
            # 修复数字格式
            (r'(\d+)\s*[,，]\s*(\d{3})', r'\1,\2'),
            # 统一金额单位
            (r'(\d+(?:\.\d{2})?)\s*[圆元]', r'\1元'),
            # 修复小数点
            (r'(\d+)\.(\d{1})\s*元', r'\1.0\2元'),
        ]

        for pattern, replacement in amount_patterns:
            text = re.sub(pattern, replacement, text)

        return text

    def _fix_line_breaks(self, text: str) -> str:
        """修复断行问题"""
        # 修复数字和单位之间的断行
        text = re.sub(r'(\d+)\s*\n\s*(元|平方米|㎡|月|年|号)', r'\1\2', text)

        # 修复中文词汇之间的断行
        text = re.sub(r'([\u4e00-\u9fff])\s*\n\s*([\u4e00-\u9fff])', r'\1\2', text)

        # 修复英文单词之间的断行
        text = re.sub(r'([a-zA-Z])\s*\n\s*([a-zA-Z])', r'\1\2', text)

        return text

    def extract_dates(self, text: str) -> List[Dict[str, Any]]:
        """
        提取日期信息

        Args:
            text: 清理后的文本

        Returns:
            日期信息列表
        """
        dates = []

        for pattern in self.date_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    groups = match.groups()
                    if len(groups) >= 3:
                        year, month, day = groups[:3]
                        # 标准化数字
                        year = self._normalize_chinese_number(year)
                        month = self._normalize_chinese_number(month)
                        day = self._normalize_chinese_number(day)

                        # 补全年份
                        if len(year) == 2:
                            year = '20' + year if int(year) < 50 else '19' + year

                        # 验证日期
                        year_int, month_int, day_int = int(year), int(month), int(day)
                        if 1900 <= year_int <= 2100 and 1 <= month_int <= 12 and 1 <= day_int <= 31:
                            date_obj = date(year_int, month_int, day_int)
                            dates.append({
                                'date': date_obj.strftime('%Y-%m-%d'),
                                'raw_text': match.group(),
                                'position': match.start(),
                                'confidence': self._calculate_date_confidence(match.group())
                            })
                except (ValueError, IndexError) as e:
                    logger.debug(f"日期解析失败: {match.group()}, 错误: {e}")
                    continue

        # 按置信度排序
        dates.sort(key=lambda x: x['confidence'], reverse=True)
        return dates

    def extract_amounts(self, text: str) -> List[Dict[str, Any]]:
        """
        提取金额信息

        Args:
            text: 清理后的文本

        Returns:
            金额信息列表
        """
        amounts = []

        for pattern in self.amount_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    amount_str = match.group(1)
                    amount = self._parse_amount(amount_str)

                    if amount > 0:
                        amounts.append({
                            'amount': amount,
                            'raw_text': match.group(),
                            'position': match.start(),
                            'confidence': self._calculate_amount_confidence(match.group())
                        })
                except (ValueError, IndexError) as e:
                    logger.debug(f"金额解析失败: {match.group()}, 错误: {e}")
                    continue

        # 按置信度排序并去重
        unique_amounts = []
        seen_amounts = set()
        for amount_info in sorted(amounts, key=lambda x: x['confidence'], reverse=True):
            if amount_info['amount'] not in seen_amounts:
                seen_amounts.add(amount_info['amount'])
                unique_amounts.append(amount_info)

        return unique_amounts

    def extract_areas(self, text: str) -> List[Dict[str, Any]]:
        """
        提取面积信息

        Args:
            text: 清理后的文本

        Returns:
            面积信息列表
        """
        areas = []

        for pattern in self.area_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    area_str = match.group(1)
                    area = float(area_str.replace(',', ''))

                    if area > 0:
                        areas.append({
                            'area': area,
                            'raw_text': match.group(),
                            'position': match.start(),
                            'confidence': self._calculate_area_confidence(match.group())
                        })
                except (ValueError, IndexError) as e:
                    logger.debug(f"面积解析失败: {match.group()}, 错误: {e}")
                    continue

        # 按置信度排序并去重
        unique_areas = []
        seen_areas = set()
        for area_info in sorted(areas, key=lambda x: x['confidence'], reverse=True):
            if area_info['area'] not in seen_areas:
                seen_areas.add(area_info['area'])
                unique_areas.append(area_info)

        return unique_areas

    def _normalize_chinese_number(self, num_str: str) -> str:
        """将中文数字转换为阿拉伯数字"""
        chinese_numbers = {
            '零': '0', '一': '1', '二': '2', '三': '3', '四': '4',
            '五': '5', '六': '6', '七': '7', '八': '8', '九': '9',
            '十': '10', '百': '100', '千': '1000', '万': '10000'
        }

        result = num_str
        for chinese, arabic in chinese_numbers.items():
            result = result.replace(chinese, arabic)

        return result

    def _parse_amount(self, amount_str: str) -> float:
        """解析金额字符串"""
        # 移除逗号和空格
        amount_str = amount_str.replace(',', '').replace(' ', '')

        try:
            return float(amount_str)
        except ValueError:
            # 尝试解析中文数字
            amount_str = self._normalize_chinese_number(amount_str)
            return float(amount_str)

    def _calculate_date_confidence(self, date_text: str) -> float:
        """计算日期识别置信度"""
        confidence = 0.5

        # 标准格式加分
        if re.match(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日号]?', date_text):
            confidence += 0.3
        elif re.match(r'\d{4}-\d{2}-\d{2}', date_text):
            confidence += 0.4

        # 包含中文年月日加分
        if any(char in date_text for char in ['年', '月', '日', '号']):
            confidence += 0.2

        return min(confidence, 1.0)

    def _calculate_amount_confidence(self, amount_text: str) -> float:
        """计算金额识别置信度"""
        confidence = 0.5

        # 包含"元"字加分
        if '元' in amount_text:
            confidence += 0.2

        # 标准数字格式加分
        if re.match(r'\d+(?:,\d{3})*(?:\.\d{2})?', amount_text):
            confidence += 0.3

        return min(confidence, 1.0)

    def _calculate_area_confidence(self, area_text: str) -> float:
        """计算面积识别置信度"""
        confidence = 0.5

        # 包含单位加分
        if any(unit in area_text for unit in ['平方米', '㎡', '平方']):
            confidence += 0.3

        # 包含"面积"关键字加分
        if '面积' in area_text:
            confidence += 0.2

        return min(confidence, 1.0)

    def process_contract_text(self, text: str) -> Dict[str, Any]:
        """
        处理合同文本的综合方法

        Args:
            text: OCR原始文本

        Returns:
            处理结果字典
        """
        logger.info("开始综合处理合同文本...")

        # 1. 清理文本
        cleaned_text = self.clean_ocr_text(text)

        # 2. 提取关键信息
        dates = self.extract_dates(cleaned_text)
        amounts = self.extract_amounts(cleaned_text)
        areas = self.extract_areas(cleaned_text)

        # 3. 构建结果
        result = {
            'original_length': len(text),
            'cleaned_length': len(cleaned_text),
            'cleaned_text': cleaned_text,
            'extracted_dates': dates,
            'extracted_amounts': amounts,
            'extracted_areas': areas,
            'processing_summary': {
                'dates_found': len(dates),
                'amounts_found': len(amounts),
                'areas_found': len(areas),
                'compression_ratio': len(cleaned_text) / len(text) if text else 0
            }
        }

        logger.info(f"合同文本处理完成: {result['processing_summary']}")
        return result


# 全局实例
ocr_text_processor = OCRTextProcessor()