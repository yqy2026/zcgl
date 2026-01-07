"""
Excel模板生成服务

提供Excel导入模板的生成功能
"""

import io
import logging

import pandas as pd
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ExcelTemplateService:
    """
    Excel模板生成服务

    负责生成Excel导入模板文件
    """

    def __init__(self, db: Session):
        """
        初始化模板服务

        Args:
            db: 数据库会话
        """
        self.db = db

    def generate_template(self) -> io.BytesIO:
        """
        生成Excel导入模板

        Returns:
            BytesIO: Excel文件的字节流
        """
        try:
            # 创建示例数据 - 按照新增资产表单字段顺序排列
            template_data = {
                # 基本信息
                "权属方": ["示例权属方1", "示例权属方2"],
                "权属类别": ["国有", "集体"],
                "项目名称": ["示例项目1", "示例项目2"],
                "物业名称": ["示例物业1", "示例物业2"],
                "物业地址": ["示例地址1", "示例地址2"],
                # 面积信息
                "土地面积(平方米)": [1000.0, 2000.0],
                "实际房产面积(平方米)": [800.0, 1800.0],
                "非经营物业面积(平方米)": [200.0, 300.0],
                "可出租面积(平方米)": [600.0, 1500.0],
                "已出租面积(平方米)": [400.0, 1200.0],
                # 状态信息
                "确权状态（已确权、未确权、部分确权）": ["已确权", "未确权"],
                "证载用途（商业、住宅、办公、厂房、车库等）": ["商业", "办公"],
                "实际用途（商业、住宅、办公、厂房、车库等）": ["商业", "办公"],
                "业态类别": ["零售", "餐饮"],
                "使用状态（出租、闲置、自用、公房、其他）": ["出租", "闲置"],
                "是否涉诉": ["否", "否"],
                "物业性质（经营类、非经营类）": ["经营类", "非经营类"],
                "是否计入出租率": ["是", "是"],
                # 接收信息
                "接收模式": ["自营", "合作"],
                "(当前)接收协议开始日期": ["2024-01-01", "2024-02-01"],
                "(当前)接收协议结束日期": ["2024-12-31", "2024-12-31"],
            }

            # 创建DataFrame
            df = pd.DataFrame(template_data)

            # 写入Excel文件
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="资产导入模板")

                # 获取工作簿和工作表
                worksheet = writer.sheets["资产导入模板"]

                # 设置列宽
                column_widths = {
                    "A": 20,  # 权属方
                    "B": 15,  # 权属类别
                    "C": 20,  # 项目名称
                    "D": 20,  # 物业名称
                    "E": 30,  # 物业地址
                    "F": 18,  # 土地面积
                    "G": 18,  # 实际房产面积
                    "H": 20,  # 非经营物业面积
                    "I": 18,  # 可出租面积
                    "J": 18,  # 已出租面积
                    "K": 20,  # 确权状态
                    "L": 25,  # 证载用途
                    "M": 25,  # 实际用途
                    "N": 15,  # 业态类别
                    "O": 20,  # 使用状态
                    "P": 12,  # 是否涉诉
                    "Q": 20,  # 物业性质
                    "R": 15,  # 是否计入出租率
                    "S": 12,  # 接收模式
                    "T": 20,  # 协议开始日期
                    "U": 20,  # 协议结束日期
                }

                for col, width in column_widths.items():
                    worksheet.column_dimensions[col].width = width

            buffer.seek(0)
            logger.info("Excel模板生成成功")

            return buffer

        except Exception as e:
            logger.error(f"生成Excel模板失败: {str(e)}")
            raise
