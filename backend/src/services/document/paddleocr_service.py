#!/usr/bin/env python3
"""
PaddleOCR 3.3 服务模块
封装 PP-StructureV3 版面分析和 OCR 能力
支持中文合同的智能识别和结构化输出
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 尝试导入 PaddleOCR
try:
    from paddleocr import PaddleOCR
    # PaddleOCR 3.3+ 使用 PPStructureV3
    try:
        from paddleocr import PPStructureV3 as PPStructure
    except ImportError:
        # 旧版本使用 PPStructure
        from paddleocr import PPStructure

    PADDLEOCR_AVAILABLE = True
except ImportError:
    logger.warning("PaddleOCR 未安装，请运行: pip install paddleocr>=3.3.0")
    PPStructure = None
    PaddleOCR = None
    PADDLEOCR_AVAILABLE = False


class PaddleOCRService:
    """
    PaddleOCR 服务类

    使用 PP-StructureV3 进行版面分析和表格识别
    使用 PP-OCRv5 进行文字识别
    """

    def __init__(
        self,
        use_gpu: bool = False,
        lang: str = "ch",
        show_log: bool = False,
    ):
        """
        初始化 PaddleOCR 服务

        Args:
            use_gpu: 是否使用 GPU 加速
            lang: 语言，默认中文
            show_log: 是否显示日志
        """
        self.use_gpu = use_gpu
        self.lang = lang
        self.show_log = show_log
        self._structure_engine = None
        self._ocr_engine = None

        if not PADDLEOCR_AVAILABLE:
            logger.error("PaddleOCR 不可用")
            return

        self._init_engines()

    def _init_engines(self):
        """初始化引擎"""
        # 尝试初始化 PP-StructureV3 (需要 paddlex[ocr] 依赖)
        try:
            self._structure_engine = PPStructure(
                lang=self.lang,
                use_table_recognition=True,
            )
            logger.info("PP-StructureV3 引擎初始化成功")
        except Exception as e:
            # PP-StructureV3 需要额外依赖,记录警告但继续
            logger.warning(f"PP-StructureV3 初始化失败 (需要 paddlex[ocr]): {e}")
            self._structure_engine = None

        # 初始化基础 OCR 引擎
        try:
            self._ocr_engine = PaddleOCR(lang=self.lang)
            logger.info("PaddleOCR 引擎初始化成功")
        except Exception as e:
            logger.error(f"PaddleOCR 引擎初始化失败: {e}")
            self._ocr_engine = None

    @property
    def is_available(self) -> bool:
        """检查服务是否可用 (至少有基础 OCR)"""
        return PADDLEOCR_AVAILABLE and (
            self._structure_engine is not None or self._ocr_engine is not None
        )

    @property
    def has_structure_engine(self) -> bool:
        """检查 PP-StructureV3 版面分析是否可用"""
        return self._structure_engine is not None

    def extract_structure(self, file_path: str) -> dict[str, Any]:
        """
        使用 PP-StructureV3 提取文档结构

        Args:
            file_path: PDF 或图片文件路径

        Returns:
            包含版面分析结果的字典
        """
        if not self.is_available:
            return {
                "success": False,
                "error": "PaddleOCR 服务不可用",
                "structure": [],
            }

        file_path = Path(file_path)
        if not file_path.exists():
            return {
                "success": False,
                "error": f"文件不存在: {file_path}",
                "structure": [],
            }

        try:
            logger.info(f"开始处理文件: {file_path}")

            # 调用 PP-StructureV3 处理
            result = self._structure_engine(str(file_path))

            # 解析结果
            parsed_result = self._parse_structure_result(result)

            logger.info(f"文件处理完成，识别到 {len(parsed_result['elements'])} 个元素")

            return {
                "success": True,
                "file_path": str(file_path),
                "structure": parsed_result,
            }

        except Exception as e:
            logger.error(f"文档结构提取失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "structure": [],
            }

    def _parse_structure_result(self, result: list) -> dict[str, Any]:
        """
        解析 PP-StructureV3 返回结果

        Args:
            result: PP-StructureV3 原始结果

        Returns:
            解析后的结构化数据
        """
        elements = []
        tables = []
        text_blocks = []

        for page_idx, page_result in enumerate(result):
            for item in page_result:
                element_type = item.get("type", "unknown")

                if element_type == "table":
                    # 表格数据
                    table_data = {
                        "page": page_idx + 1,
                        "type": "table",
                        "html": item.get("res", {}).get("html", ""),
                        "cells": self._extract_table_cells(item),
                    }
                    tables.append(table_data)
                    elements.append(table_data)

                elif element_type in ["text", "title", "figure_caption"]:
                    # 文本块
                    text_data = {
                        "page": page_idx + 1,
                        "type": element_type,
                        "text": self._extract_text_from_item(item),
                        "bbox": item.get("bbox", []),
                    }
                    text_blocks.append(text_data)
                    elements.append(text_data)

                else:
                    # 其他元素
                    elements.append(
                        {
                            "page": page_idx + 1,
                            "type": element_type,
                            "data": item.get("res", {}),
                        }
                    )

        return {
            "elements": elements,
            "tables": tables,
            "text_blocks": text_blocks,
            "page_count": len(result),
        }

    def _extract_text_from_item(self, item: dict) -> str:
        """从结构项中提取文本"""
        res = item.get("res", [])
        if isinstance(res, list):
            texts = []
            for line in res:
                if isinstance(line, dict):
                    texts.append(line.get("text", ""))
                elif isinstance(line, (list, tuple)) and len(line) >= 2:
                    texts.append(
                        str(line[1][0]) if isinstance(line[1], tuple) else str(line[1])
                    )
            return "\n".join(texts)
        return str(res)

    def _extract_table_cells(self, item: dict) -> list[list[str]]:
        """从表格项中提取单元格数据"""
        res = item.get("res", {})
        if isinstance(res, dict):
            # 尝试解析 HTML 表格
            html = res.get("html", "")
            if html:
                return self._parse_html_table(html)
        return []

    def _parse_html_table(self, html: str) -> list[list[str]]:
        """解析 HTML 表格为二维数组"""
        try:
            import re

            rows = []
            # 简单的 HTML 表格解析
            row_pattern = r"<tr[^>]*>(.*?)</tr>"
            cell_pattern = r"<t[dh][^>]*>(.*?)</t[dh]>"

            for row_match in re.finditer(row_pattern, html, re.DOTALL | re.IGNORECASE):
                row_html = row_match.group(1)
                cells = []
                for cell_match in re.finditer(
                    cell_pattern, row_html, re.DOTALL | re.IGNORECASE
                ):
                    cell_text = re.sub(r"<[^>]+>", "", cell_match.group(1))
                    cells.append(cell_text.strip())
                if cells:
                    rows.append(cells)
            return rows
        except Exception as e:
            logger.warning(f"HTML 表格解析失败: {e}")
            return []

    def extract_text_only(self, file_path: str) -> dict[str, Any]:
        """
        仅提取文本（不进行版面分析）

        Args:
            file_path: 文件路径

        Returns:
            OCR 结果
        """
        if not self.is_available:
            return {
                "success": False,
                "error": "PaddleOCR 服务不可用",
                "text": "",
            }

        try:
            result = self._ocr_engine.ocr(str(file_path), cls=True)

            # 合并所有文本
            all_text = []
            for page_result in result:
                if page_result:
                    for line in page_result:
                        if line and len(line) >= 2:
                            text = line[1][0] if isinstance(line[1], tuple) else line[1]
                            all_text.append(str(text))

            return {
                "success": True,
                "text": "\n".join(all_text),
                "line_count": len(all_text),
            }

        except Exception as e:
            logger.error(f"文本提取失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
            }

    def to_markdown(self, file_path: str) -> dict[str, Any]:
        """
        将文档转换为 Markdown 格式

        Args:
            file_path: 文件路径

        Returns:
            包含 Markdown 内容的结果
        """
        # 先提取结构
        structure_result = self.extract_structure(file_path)

        if not structure_result["success"]:
            return {
                "success": False,
                "error": structure_result.get("error", "结构提取失败"),
                "markdown": "",
            }

        # 转换为 Markdown
        markdown_lines = []
        structure = structure_result["structure"]

        for element in structure.get("elements", []):
            elem_type = element.get("type", "")

            if elem_type == "title":
                markdown_lines.append(f"## {element.get('text', '')}")
                markdown_lines.append("")

            elif elem_type == "text":
                markdown_lines.append(element.get("text", ""))
                markdown_lines.append("")

            elif elem_type == "table":
                # 转换表格为 Markdown
                cells = element.get("cells", [])
                if cells:
                    table_md = self._cells_to_markdown_table(cells)
                    markdown_lines.append(table_md)
                    markdown_lines.append("")

        markdown_content = "\n".join(markdown_lines)

        return {
            "success": True,
            "markdown": markdown_content,
            "structure": structure,
        }

    def _cells_to_markdown_table(self, cells: list[list[str]]) -> str:
        """将单元格数据转换为 Markdown 表格"""
        if not cells:
            return ""

        lines = []

        # 表头
        header = cells[0]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")

        # 表体
        for row in cells[1:]:
            # 确保列数一致
            while len(row) < len(header):
                row.append("")
            lines.append("| " + " | ".join(row[: len(header)]) + " |")

        return "\n".join(lines)


# 单例实例
_paddleocr_service = None


def get_paddleocr_service(use_gpu: bool = False) -> PaddleOCRService:
    """
    获取 PaddleOCR 服务单例

    Args:
        use_gpu: 是否使用 GPU

    Returns:
        PaddleOCRService 实例
    """
    global _paddleocr_service

    if _paddleocr_service is None:
        _paddleocr_service = PaddleOCRService(use_gpu=use_gpu)

    return _paddleocr_service


# 便捷函数
def extract_contract_structure(file_path: str, use_gpu: bool = False) -> dict[str, Any]:
    """
    提取合同文档结构

    Args:
        file_path: 合同文件路径
        use_gpu: 是否使用 GPU

    Returns:
        结构化提取结果
    """
    service = get_paddleocr_service(use_gpu=use_gpu)
    return service.extract_structure(file_path)


def contract_to_markdown(file_path: str, use_gpu: bool = False) -> dict[str, Any]:
    """
    将合同文档转换为 Markdown

    Args:
        file_path: 合同文件路径
        use_gpu: 是否使用 GPU

    Returns:
        Markdown 转换结果
    """
    service = get_paddleocr_service(use_gpu=use_gpu)
    return service.to_markdown(file_path)
