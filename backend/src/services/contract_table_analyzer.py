"""
合同表格数据提取和分析服务
专门处理租赁合同中的复杂表格结构
"""

import cv2
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from pathlib import Path
import re
from dataclasses import dataclass
from enum import Enum
import jieba
from collections import defaultdict

logger = logging.getLogger(__name__)


class TableType(str, Enum):
    """表格类型"""
    PAYMENT_SCHEDULE = "payment_schedule"      # 付款计划表
    PARTY_INFO = "party_info"              # 当事人信息表
    LEASE_TERMS = "lease_terms"            # 租赁条款表
    FEES_BREAKDOWN = "fees_breakdown"          # 费用明细表
    PAYMENT_METHOD = "payment_method"           # 付款方式表
    PROPERTY_DETAILS = "property_details"         # 物业详情表


class CellType(str, Enum):
    """单元格类型"""
    HEADER = "header"                    # 表头
    DATA = "data"                      # 数据单元格
    MERGED = "merged"                  # 合并单元格
    EMPTY = "empty"                    # 空单元格
    CALCULATION = "calculation"            # 计算单元格


@dataclass
class TableCell:
    """表格单元格"""
    row: int
    col: int
    text: str
    cell_type: CellType
    merged_range: Optional[str] = None
    confidence: float = 0.0
    bbox: Optional[Tuple[int, int, int, int]] = None


@dataclass
class TableStructure:
    """表格结构"""
    table_type: TableType
    headers: List[str]
    rows: List[List[TableCell]]
    metadata: Dict[str, Any]
    confidence: float = 0.0


class ContractTableAnalyzer:
    """合同表格分析器"""

    def __init__(self):
        # 初始化表格识别模板
        self.table_patterns = self._load_table_patterns()
        self.chinese_keywords = self._load_chinese_keywords()

    def _load_table_patterns(self) -> Dict[str, Any]:
        """加载表格识别模式"""
        return {
            # 付款计划表模式
            'payment_schedule': {
                'keywords': ['付款', '期数', '日期', '金额', '付款方式'],
                'headers': ['期数', '付款日期', '应付金额', '实付金额', '付款方式', '备注'],
                'min_columns': 3,
                'max_columns': 8
            },

            # 当事人信息表模式
            'party_info': {
                'keywords': ['甲方', '乙方', '姓名', '身份证号', '地址', '电话', '法定代表人'],
                'headers': ['项目', '甲方/乙方', '姓名', '证件号码', '联系地址', '联系电话'],
                'min_columns': 4,
                'max_columns': 6
            },

            # 租赁条款表模式
            'lease_terms': {
                'keywords': ['租赁', '面积', '租金', '期限', '起止', '用途', '违约'],
                'headers': ['条款', '内容', '备注'],
                'min_columns': 2,
                'max_columns': 4
            },

            # 费用明细表模式
            'fees_breakdown': {
                'keywords': ['费用', '物业费', '管理费', '水电费', '其他', '金额'],
                'headers': ['费用项目', '计算方式', '金额', '支付周期'],
                'min_columns': 3,
                'max_columns': 6
            }
        }

    def _load_chinese_keywords(self) -> Dict[str, List[str]]:
        """加载中文关键词"""
        return {
            'lease': ['租赁', '出租', '承租', '租期', '租金', '押金', '保证金'],
            'party': ['甲方', '乙方', '出租方', '承租方', '法定代表人', '身份证号'],
            'property': ['房屋', '物业', '地址', '面积', '平方米', '套内'],
            'payment': ['付款', '支付', '期数', '金额', '人民币', '元'],
            'time': ['年', '月', '日', '起', '止', '至', '期限', '到期'],
            'fees': ['管理', '物业', '水电', '费用', '其他', '杂项']
        }

    async def extract_tables_from_image(self, image_path: str) -> List[TableStructure]:
        """从图像中提取表格"""
        try:
            # 读取图像
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"无法读取图像: {image_path}")
                return []

            # 图像预处理
            processed_image = self._preprocess_table_image(image)

            # 检测表格
            tables = await self._detect_tables(processed_image)

            # 分析每个表格
            table_structures = []
            for i, table in enumerate(tables):
                table_structure = await self._analyze_table_structure(table, processed_image)
                if table_structure:
                    table_structure.table_index = i + 1
                    table_structures.append(table_structure)

            logger.info(f"检测到{len(table_structures)}个表格")
            return table_structures

        except Exception as e:
            logger.error(f"表格提取失败: {e}")
            return []

    def _preprocess_table_image(self, image: np.ndarray) -> np.ndarray:
        """表格图像预处理"""
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # 增强对比度
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # 去噪
        denoised = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7)

        # 二值化
        _, binary = cv2.threshold(denoised, 0, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return binary

    async def _detect_tables(self, image: np.ndarray) -> List[np.ndarray]:
        """检测表格区域"""
        try:
            # 使用多种方法检测表格
            tables = []

            # 方法1: OpenCV轮廓检测
            contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                # 过滤掉太小的轮廓
                area = cv2.contourArea(contour)
                if area > 5000:  # 最小面积阈值
                    # 获取最小包围矩形
                    x, y, w, h = cv2.boundingRect(contour)
                    if w > 100 and h > 50:  # 最小尺寸阈值
                        table_region = image[y:y+h, x:x+w]
                        tables.append(table_region)

            # 方法2: 使用形态学操作
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 3))
            morphed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
            contours_morphed, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours_morphed:
                x, y, w, h = cv2.boundingRect(contour)
                if w > 150 and h > 100:
                    table_region = morphed[y:y+h, x:x+w]
                    tables.append(table_region)

            # 去重
            unique_tables = []
            for table in tables:
                is_duplicate = False
                for existing in unique_tables:
                    # 计算IoU（交并比）
                    intersection = cv2.intersectionRect(
                        (x, y, x + w, y + h),
                        (existing['x'], existing['y'], existing['x'] + existing['w'], existing['y'] + existing['h'])
                    )
                    union = cv2.unionRect(
                        (x, y, x + w, y + h),
                        (existing['x'], existing['y'], existing['x'] + existing['w'], existing['y'] + existing['h'])
                    )
                    iou = intersection.area / union.area if union.area > 0 else 0
                    if iou > 0.7:  # IoU阈值
                        is_duplicate = True
                        break

                if not is_duplicate:
                    unique_tables.append({
                        'image': table,
                        'x': x, 'y': y, 'w': w, 'h': h
                    })

            return unique_tables

        except Exception as e:
            logger.error(f"表格检测失败: {e}")
            return []

    async def _analyze_table_structure(self, table_region: Dict, original_image: np.ndarray) -> Optional[TableStructure]:
        """分析表格结构"""
        try:
            table_image = table_region['image']
            x, y, w, h = table_region['x'], table_region['y'], table_region['w'], table_region['h']

            # OCR识别文本
            text_data = await self._ocr_table_content(table_image)

            if not text_data:
                return None

            # 识别表格类型
            table_type = self._identify_table_type(text_data)

            # 分割文本为单元格
            cells = await self._segment_table_cells(table_image, text_data)

            # 识别表头
            headers = self._extract_table_headers(cells, table_type)

            # 构建表格结构
            table_structure = TableStructure(
                table_type=table_type,
                headers=headers,
                rows=cells,
                metadata={
                    'bbox': (x, y, w, h),
                    'cell_count': len(cells),
                    'chinese_content_detected': self._detect_chinese_content(text_data)
                },
                confidence=self._calculate_table_confidence(cells, text_data)
            )

            return table_structure

        except Exception as e:
            logger.error(f"表格结构分析失败: {e}")
            return None

    async def _ocr_table_content(self, table_image: np.ndarray) -> Dict[str, str]:
        """OCR识别表格内容"""
        try:
            # 使用Tesseract进行表格识别
            import pytesseract
            config = '--psm 6 --oem 3 -c tessedit_char_whitelist 0123456789年月日，。；：""''（）【】《》""''—–至起止面积平方米元'
            custom_config = r'--psm 6 --oem 3 -c tessedit_char_whitelist 0123456789年月日，。；：""''（）【】《》""''—–至起止面积平方米元甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥'

            # 识别文本并保留位置信息
            data = pytesseract.image_to_data(table_image, config=config)

            # 转换为更易用的格式
            text_info = {}
            for i, item in enumerate(data['text'].split('\n')):
                if item.strip():
                    text_info[f'line_{i}'] = item.strip()

            return text_info

        except Exception as e:
            logger.error(f"表格OCR失败: {e}")
            return {}

    def _identify_table_type(self, text_data: Dict[str, str]) -> TableType:
        """识别表格类型"""
        text = ' '.join(text_data.values()).lower()
        scores = {}

        for table_type, pattern_info in self.table_patterns.items():
            score = 0
            keywords = pattern_info['keywords']
            headers = pattern_info.get('headers', [])

            # 关键词匹配分数
            for keyword in keywords:
                if keyword in text:
                    score += 2

            # 表头匹配分数
            for header in headers:
                for line_text in text_data.values():
                    if header.lower() in line_text.lower():
                        score += 3
                        break

            scores[table_type] = score

        # 返回分数最高的类型
        if scores:
            best_type = max(scores.keys(), key=scores.get)
            return TableType(best_type)

        return TableType.LEASE_TERMS  # 默认类型

    async def _segment_table_cells(self, table_image: np.ndarray, text_data: Dict[str, str]) -> List[List[TableCell]]:
        """分割表格为单元格"""
        try:
            # 获取图像尺寸
            height, width = table_image.shape[:2]

            # 使用OCR的box信息来分割单元格
            import pytesseract
            boxes = pytesseract.image_to_string(table_image, config='--psm 6').split('\n')

            cells = []
            current_row = 0
            current_col = 0
            max_row = 0
            max_col = 0

            for i, line in enumerate(boxes):
                if line.strip():
                    # 简单的按行分割（需要改进）
                    cell = TableCell(
                        row=current_row,
                        col=current_col,
                        text=line.strip(),
                        cell_type=CellType.DATA,
                        confidence=0.8
                    )
                    cells.append(cell)
                    current_col += 1
                    max_col = max(max_col, current_col)
                else:
                    current_row += 1
                    current_col = 0
                    max_row = max(max_row, current_row)

            # 如果只有一行，尝试按列分割
            if max_row == 0:
                cells = await self._segment_by_columns(table_image, text_data)

            # 限制表格大小，避免过大的表格
            # 将cells按行分组，然后过滤
            rows = {}
            for cell in cells:
                if cell.row not in rows:
                    rows[cell.row] = []
                if cell.col < 10 and cell.row < 20:
                    rows[cell.row].append(cell)

            # 转换为列表格式，并确保按行列排序
            result = []
            for row_idx in sorted(rows.keys()):
                row_cells = sorted(rows[row_idx], key=lambda x: x.col)
                result.append(row_cells)

            return result

        except Exception as e:
            logger.error(f"单元格分割失败: {e}")
            return []

    async def _segment_by_columns(self, table_image: np.ndarray, text_data: Dict[str, str]) -> List[List[TableCell]]:
        """按列分割表格（针对简单表格）"""
        # 这里可以实现更复杂的列分割算法
        # 暂时返回简单结构
        return []

    def _extract_table_headers(self, cells: List[List[TableCell]], table_type: TableType) -> List[str]:
        """提取表头"""
        if not cells:
            return []

        # 对于不同的表格类型使用不同的表头识别策略
        if table_type == TableType.PAYMENT_SCHEDULE:
            return self._extract_payment_schedule_headers(cells)
        elif table_type == TableType.PARTY_INFO:
            return self._extract_party_info_headers(cells)
        elif table_type == TableType.LEASE_TERMS:
            return self._extract_lease_terms_headers(cells)
        else:
            # 默认策略：第一行作为表头
            return self._extract_first_row_as_headers(cells)

    def _extract_payment_schedule_headers(self, cells: List[List[TableCell]]) -> List[str]:
        """提取付款计划表的表头"""
        if not cells:
            return []

        first_row = [cell for cell in cells[0] if cell.col < 6]
        headers = [cell.text.strip() for cell in first_row if cell.text.strip()]

        # 标准化表头
        standard_headers = []
        header_mapping = {
            '期数': ['期', '期数', '付款期'],
            '日期': ['日期', '付款日期', '应付日期', '收款日期'],
            '金额': ['金额', '应付金额', '实付金额', '租金', '费用'],
            '方式': ['方式', '付款方式', '支付方式'],
            '备注': ['备注', '说明', '其他']
        }

        for header in headers:
            normalized = self._normalize_header(header, header_mapping)
            if normalized and normalized not in standard_headers:
                standard_headers.append(normalized)

        return standard_headers

    def _extract_party_info_headers(self, cells: List[List[TableCell]]) -> List[str]:
        """提取当事方信息表的表头"""
        if not cells:
            return []

        first_row = [cell for cell in cells[0] if cell.col < 5]
        headers = [cell.text.strip() for cell in first_row if cell.text.strip()]

        # 标准化表头
        standard_headers = []
        header_mapping = {
            '项目': ['项目', '信息', '事项'],
            '甲乙': ['甲方', '乙方', '出租方', '承租方'],
            '姓名': ['姓名', '名称', '当事人'],
            '证件': ['证件', '身份证', '证件号'],
            '地址': ['地址', '联系地址', '住址'],
            '电话': ['电话', '联系电话', '手机号']
        }

        for header in headers:
            normalized = self._normalize_header(header, header_mapping)
            if normalized and normalized not in standard_headers:
                standard_headers.append(normalized)

        return standard_headers

    def _extract_lease_terms_headers(self, cells: List[List[TableCell]]) -> List[str]:
        """提取租赁条款表的表头"""
        if not cells:
            return []

        first_col = [cell.text.strip() for cell in cells if cell.col == 0 and cell.text.strip()]
        headers = first_col

        # 标准化表头
        standard_headers = []
        header_mapping = {
            '租赁期限': ['租赁', '租期', '期限', '时间'],
            '面积': ['面积', '建筑面积', '房屋面积'],
            '租金': ['租金', '费用', '金额'],
            '支付方式': ['支付', '付款', '方式']
        }

        for header in headers:
            normalized = self._normalize_header(header, header_mapping)
            if normalized and normalized not in standard_headers:
                standard_headers.append(normalized)

        return standard_headers

    def _extract_first_row_as_headers(self, cells: List[List[TableCell]]) -> List[str]:
        """提取第一行作为表头"""
        if not cells or len(cells) == 0:
            return []

        first_row = [cell for cell in cells[0] if cell.col < 8]
        headers = [cell.text.strip() for cell in first_row if cell.text.strip()]

        return headers

    def _normalize_header(self, header: str, mapping: Dict[str, List[str]]) -> str:
        """标准化表头"""
        for key, variants in mapping.items():
            for variant in variants:
                if variant in header:
                    return key
        return header

    def _detect_chinese_content(self, text_data: Dict[str, str]) -> bool:
        """检测中文内容"""
        text = ' '.join(text_data.values())
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(re.sub(r'\s', '', text))

        return chinese_chars / total_chars > 0.3 if total_chars > 0 else False

    def _calculate_table_confidence(self, cells: List[List[TableCell]], text_data: Dict[str, str]) -> float:
        """计算表格识别置信度"""
        if not cells:
            return 0.0

        total_cells = sum(len(row) for row in cells)
        filled_cells = sum(len([cell for cell in row if cell.cell_type == CellType.DATA]) for row in cells)

        # 基于填充率的基础置信度
        density_confidence = filled_cells / max(total_cells, 1)

        # 中文内容检测加分
        chinese_bonus = 0.1 if self._detect_chinese_content(text_data) else 0.0

        # 规整性检测
        regularity_score = self._assess_table_regularity(cells)

        return min(density_confidence + chinese_bonus + regularity_score, 1.0)

    def _assess_table_regularity(self, cells: List[List[TableCell]]) -> float:
        """评估表格规整性"""
        if len(cells) < 2:
            return 0.0

        # 计算每行的单元格数量
        row_counts = [len(row) for row in cells]
        avg_count = sum(row_counts) / len(row_counts)

        # 计算标准差
        if len(row_counts) > 1:
            variance = sum((count - avg_count) ** 2 for count in row_counts) / (len(row_counts) - 1)
            # 标准差越小，表格越规整
            regularity = 1.0 / (1 + variance)
        else:
            regularity = 1.0

        return regularity

    async def extract_structured_data_from_tables(self, table_structures: List[TableStructure]) -> Dict[str, Any]:
        """从表格结构中提取结构化数据"""
        structured_data = {
            'tables_found': len(table_structures),
            'payment_schedule': None,
            'party_info': None,
            'lease_terms': None,
            'fees_breakdown': None
        }

        for table in table_structures:
            if table.table_type == TableType.PAYMENT_SCHEDULE:
                structured_data['payment_schedule'] = await self._extract_payment_schedule_data(table)
            elif table.table_type == TableType.PARTY_INFO:
                structured_data['party_info'] = await self._extract_party_info_data(table)
            elif table.table_type == TableType.LEASE_TERMS:
                structured_data['lease_terms'] = await self._extract_lease_terms_data(table)
            elif table.table_type == TableType.FEES_BREAKDOWN:
                structured_data['fees_breakdown'] = await self._extract_fees_data(table)

        return structured_data

    async def _extract_payment_schedule_data(self, table: TableStructure) -> Dict[str, Any]:
        """提取付款计划数据"""
        # 实现具体的付款计划数据提取逻辑
        return {
            'confidence': table.confidence,
            'data': {}
        }

    async def _extract_party_info_data(self, table: TableStructure) -> Dict[str, Any]:
        """提取当事方信息数据"""
        # 实现具体的当事方信息数据提取逻辑
        return {
            'confidence': table.confidence,
            'data': {}
        }

    async def _extract_lease_terms_data(self, table: TableStructure) -> Dict[str, Any]:
        """提取租赁条款数据"""
        # 实现具体的租赁条款数据提取逻辑
        return {
            'confidence': table.confidence,
            'data': {}
        }

    async def _extract_fees_data(self, table: TableStructure) -> Dict[str, Any]:
        """提取费用明细数据"""
        # 实现具体的费用明细数据提取逻辑
        return {
            'confidence': table.confidence,
            'data': {}
        }


# 全局表格分析器实例
contract_table_analyzer = ContractTableAnalyzer()