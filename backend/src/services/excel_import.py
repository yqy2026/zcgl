"""
Excel数据导入服务
使用Polars进行高性能数据处理
"""

import pandas as pd
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
from datetime import datetime, timezone
import re

from src.schemas.asset import AssetCreate, OwnershipStatus, UsageStatus, PropertyNature
from src.crud.asset import AssetCRUD
from src.models.asset import Asset
from src.database import get_db
from sqlalchemy.orm import Session
from src.config.excel_config import STANDARD_SHEET_NAME

logger = logging.getLogger(__name__)


class ExcelImportError(Exception):
    """Excel导入异常"""
    pass


class AssetDataProcessor:
    """使用Polars进行高性能数据处理"""
    
    # Excel列名到数据库字段的映射 - 按照新增资产表单字段顺序排列，删除自动计算和高级选项字段
    COLUMN_MAPPING = {
        # 基本信息 - 按照表单顺序
        "权属方": "ownership_entity",
        "权属类别": "ownership_category",
        "项目名称": "project_name",
        "物业名称": "property_name",
        "物业地址": "address",

        # 面积信息 - 按照表单顺序，删除自动计算的未出租面积
        "土地面积(平方米)": "land_area",
        "土地面积\n(平方米)": "land_area",
        "实际房产面积(平方米)": "actual_property_area",
        "实际房产面积\n(平方米)": "actual_property_area",
        "非经营物业面积(平方米)": "non_commercial_area",
        "非经营物业面积\n(平方米)": "non_commercial_area",
        "可出租面积(平方米)": "rentable_area",
        "可出租面积\n(平方米)": "rentable_area",
        "已出租面积(平方米)": "rented_area",
        "已出租面积\n(平方米)": "rented_area",
        "经营性物业可出租面积(平方米)": "rentable_area",
        "经营性物业已出租面积(平方米)": "rented_area",
        "经营性物业未出租面积(平方米)": "unrented_area",

        # 状态信息 - 按照表单顺序，删除自动计算的出租率
        "确权状态（已确权、未确权、部分确权）": "ownership_status",
        "是否确权\n（已确权、未确权、部分确权）": "ownership_status",
        "确权状态": "ownership_status",
        "证载用途（商业、住宅、办公、厂房、车库等）": "certificated_usage",
        "证载用途\n（商业、住宅、办公、厂房、车库等）": "certificated_usage",
        "证载用途": "certificated_usage",
        "实际用途（商业、住宅、办公、厂房、车库等）": "actual_usage",
        "实际用途\n（商业、住宅、办公、厂房、车库等）": "actual_usage",
        "实际用途": "actual_usage",
        "业态类别": "business_category",
        "使用状态（出租、闲置、自用、公房、其他）": "usage_status",
        "物业使用状态\n（出租、闲置、自用、公房、其他）": "usage_status",
        "使用状态": "usage_status",
        "是否涉诉": "is_litigated",
        "物业性质（经营类、非经营类）": "property_nature",
        "物业性质": "property_nature",
        "是否计入出租率": "include_in_occupancy_rate",

        # 接收信息 - 按照表单顺序，删除文件上传字段
        "接收模式": "business_model",
        "(当前)接收协议开始日期": "operation_agreement_start_date",
        "接收协议开始日期": "operation_agreement_start_date",
        "(当前)接收协议结束日期": "operation_agreement_end_date",
        "接收协议结束日期": "operation_agreement_end_date",

        # 租户信息
        "租户名称": "tenant_name",
        "租户联系方式": "tenant_contact",
        "承租合同/代理协议": "lease_contract_number",
        "备注": "notes",
        "说明": "notes",

        # 管理信息
        "管理责任人（网格员）": "manager_name",

        # 合同信息
        "现合同结束日期": "contract_end_date",
        "现合同开始日期": "contract_start_date",
        "月租金（元）": "monthly_rent",
        "押金（元）": "deposit",
        "是否分租/转租": "is_sublease",
        "分租/转租备注": "sublease_notes",

        # 财务信息
        "年收益（元）": "annual_income",
        "年支出（元）": "annual_expense",
        "净收益（元）": "net_income",

        # 系统字段
        "更新人": "updated_by",
        "标签": "tags",

        # 审核字段
        "最后审核时间": "last_audit_date",
        "审核人": "auditor",
        "审核备注": "audit_notes",

        # 向后兼容的字段映射
        "所在地址": "address",
        "五羊运营项目名称": "project_name",
        "协议开始日期": "operation_agreement_start_date",
        "协议结束日期": "operation_agreement_end_date",
    }
    
    @staticmethod
    def read_excel_file(file_path: str, sheet_name: str = STANDARD_SHEET_NAME) -> pd.DataFrame:
        """从Excel文件读取数据"""
        try:
            # 使用Pandas读取Excel文件
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                engine='openpyxl'
            )

            logger.info(f"成功读取Excel文件: {file_path}, 行数: {len(df)}, 列数: {len(df.columns)}")
            return df

        except Exception as e:
            logger.error(f"读取Excel文件失败: {file_path}, 错误: {str(e)}")
            raise ExcelImportError(f"读取Excel文件失败: {str(e)}")
    
    @staticmethod
    def clean_and_transform_data(df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗和标准化"""
        try:
            # 重命名列
            rename_dict = {}
            for old_col in df.columns:
                # 清理列名中的空白字符和换行符（处理\r\n和\n）
                clean_col = str(old_col).strip().replace('\r\n', '\n').replace('\r', '\n')

                # 特殊处理常见的格式问题
                clean_col = clean_col.replace('\n（', '（').replace('\n..', '')

                # 标准化映射流程
                if clean_col in AssetDataProcessor.COLUMN_MAPPING:
                    rename_dict[old_col] = AssetDataProcessor.COLUMN_MAPPING[clean_col]
                else:
                    # 如果找不到精确匹配，尝试模糊匹配
                    for excel_col, db_col in AssetDataProcessor.COLUMN_MAPPING.items():
                        # 标准化比较：移除所有空白字符和换行符
                        excel_normalized = excel_col.replace('\n', '').replace('\r', '').replace(' ', '')
                        col_normalized = clean_col.replace('\n', '').replace('\r', '').replace(' ', '')
                        if excel_normalized == col_normalized:
                            rename_dict[old_col] = db_col
                            break

            if rename_dict:
                df = df.rename(columns=rename_dict)

            # 处理字符串字段的空值和空白
            string_fields = [
                "ownership_entity", "property_name", "address",
                "certificated_usage", "actual_usage",
                "ownership_category", "business_category",
                "project_name"
            ]

            for field in string_fields:
                if field in df.columns:
                    df[field] = df[field].fillna("").astype(str).str.strip()

            # 处理数值字段
            numeric_fields = [
                "land_area", "actual_property_area", "rentable_area",
                "rented_area", "unrented_area", "non_commercial_area",
                "monthly_rent", "deposit", "annual_income", "annual_expense", "net_income"
            ]

            for field in numeric_fields:
                if field in df.columns:
                    df[field] = pd.to_numeric(df[field].astype(str).str.replace(',', '').str.replace(' ', '0'), errors='coerce').fillna(0.0)

            # 处理枚举字段
            if "ownership_status" in df.columns:
                df["ownership_status"] = df["ownership_status"].fillna("未确权").astype(str).str.strip()
                df["ownership_status"] = df["ownership_status"].replace("", "未确权")

            if "usage_status" in df.columns:
                df["usage_status"] = df["usage_status"].fillna("其他").astype(str).str.strip()
                df["usage_status"] = df["usage_status"].replace("", "其他")

            if "property_nature" in df.columns:
                df["property_nature"] = df["property_nature"].fillna("经营性").astype(str).str.strip()
                df["property_nature"] = df["property_nature"].replace("", "经营性")
                # 处理物业性质映射 - 扩展映射以匹配用户Excel文件
                property_nature_mapping = {
                    "非经营类-配套": "非经营-配套",
                    "经营-配套设施": "经营-配套",
                    "非经营类-公配房": "非经营-公配房",
                    "非经营-配套镇": "非经营-配套",
                    "非经营类": "非经营类",
                    "经营类": "经营类"
                }

                # 应用所有映射
                for old_val, new_val in property_nature_mapping.items():
                    df["property_nature"] = df["property_nature"].replace(old_val, new_val)

                # 确保所有值都在枚举范围内
                valid_natures = ["经营性", "经营类", "经营-内部", "经营-外部", "经营-租赁",
                               "经营-配套", "经营-配套镇", "经营-处置类", "非经营性", "非经营类",
                               "非经营-配套", "非经营-公配房", "非经营-配套镇", "非经营-处置类"]

                # 将无效值设为默认值
                df["property_nature"] = df["property_nature"].apply(
                    lambda x: x if x in valid_natures else "经营性"
                )

            if "business_model" in df.columns:
                # 暂时设为None以避免枚举验证问题
                df["business_model"] = None

            if "is_litigated" in df.columns:
                df["is_litigated"] = df["is_litigated"].fillna(False)
                df["is_litigated"] = df["is_litigated"].astype(str).str.strip().isin(["是", "true", "1", "yes", "True", "TRUE"])

            if "include_in_occupancy_rate" in df.columns:
                df["include_in_occupancy_rate"] = df["include_in_occupancy_rate"].fillna(True)
                df["include_in_occupancy_rate"] = df["include_in_occupancy_rate"].astype(str).str.strip().isin(["是", "true", "1", "yes", "True", "TRUE", "正确"])

            if "is_sublease" in df.columns:
                df["is_sublease"] = df["is_sublease"].fillna(False)
                df["is_sublease"] = df["is_sublease"].astype(str).str.strip().isin(["是", "true", "1", "yes", "True", "TRUE"])

            # 处理日期字段
            date_fields = [
                "contract_start_date", "contract_end_date",
                "operation_agreement_start_date", "operation_agreement_end_date"
            ]

            for field in date_fields:
                if field in df.columns:
                    df[field] = pd.to_datetime(df[field], errors='coerce')

            logger.info(f"数据清洗完成，处理后行数: {len(df)}")
            return df

        except Exception as e:
            logger.error(f"数据清洗失败: {str(e)}")
            raise ExcelImportError(f"数据清洗失败: {str(e)}")
    
    @staticmethod
    def validate_data(df: pd.DataFrame) -> List[str]:
        """数据验证"""
        errors = []

        # 检查必填字段 - 与新增资产表单保持一致
        required_fields = ["ownership_entity", "property_name", "address", "ownership_status", "property_nature", "usage_status"]

        for field in required_fields:
            if field not in df.columns:
                errors.append(f"缺少必填字段: {field}")
                continue

            # 检查空值
            if field in ["ownership_entity", "property_name", "address"]:
                # 字符串字段检查
                null_count = df[df[field].isna() | (df[field] == "")].shape[0]
            else:
                # 枚举字段检查
                null_count = df[df[field].isna() | (df[field] == "")].shape[0]

            if null_count > 0:
                errors.append(f"字段 {field} 有 {null_count} 行数据为空")

        # 检查数值字段的有效性 - 删除自动计算的未出租面积
        numeric_fields = ["actual_property_area", "rentable_area", "rented_area", "non_commercial_area"]

        for field in numeric_fields:
            if field in df.columns:
                try:
                    negative_count = df[df[field] < 0].shape[0]
                    if negative_count > 0:
                        errors.append(f"字段 {field} 有 {negative_count} 行数据为负数")
                except Exception as e:
                    errors.append(f"验证数值字段 {field} 时出错: {str(e)}")

        return errors
    
    @staticmethod
    def convert_to_asset_models(df: pd.DataFrame) -> List[AssetCreate]:
        """将DataFrame转换为AssetCreate模型列表"""
        assets = []

        # 获取AssetCreate模型的有效字段
        valid_fields = set(AssetCreate.model_fields.keys())

        for index, row in df.iterrows():
            try:
                # 构建资产数据字典
                asset_data = {}

                # 只映射有效字段
                for db_field, value in row.items():
                    # 跳过None值和空字符串
                    if pd.isna(value) or value == "":
                        continue

                    # 跳过未知字段
                    if db_field not in valid_fields:
                        continue

                    if db_field in ["contract_start_date", "contract_end_date",
                                   "operation_agreement_start_date", "operation_agreement_end_date"]:
                        # 日期字段处理
                        if hasattr(value, 'date'):
                            asset_data[db_field] = value.date()
                    else:
                        asset_data[db_field] = value

                # 确保必填字段有默认值
                if "ownership_status" not in asset_data:
                    asset_data["ownership_status"] = "未确权"

                if "usage_status" not in asset_data:
                    asset_data["usage_status"] = "其他"

                if "property_nature" not in asset_data:
                    asset_data["property_nature"] = "经营类"

                # 处理布尔字段转换
                if "is_litigated" in asset_data:
                    if isinstance(asset_data["is_litigated"], str):
                        asset_data["is_litigated"] = asset_data["is_litigated"].lower() in ["是", "true", "1", "yes"]

                if "include_in_occupancy_rate" in asset_data:
                    if isinstance(asset_data["include_in_occupancy_rate"], str):
                        asset_data["include_in_occupancy_rate"] = asset_data["include_in_occupancy_rate"].lower() in ["是", "true", "1", "yes"]

                if "is_sublease" in asset_data:
                    if isinstance(asset_data["is_sublease"], str):
                        asset_data["is_sublease"] = asset_data["is_sublease"].lower() in ["是", "true", "1", "yes"]

                # 创建AssetCreate实例
                asset = AssetCreate(**asset_data)
                assets.append(asset)

            except Exception as e:
                logger.warning(f"转换第{index+1}行数据失败: {str(e)}, 数据: {row.to_dict()}")
                continue

        logger.info(f"成功转换 {len(assets)} 条资产数据")
        return assets


class ExcelImportService:
    """Excel导入服务"""
    
    def __init__(self):
        self.processor = AssetDataProcessor()
        self.asset_crud = AssetCRUD()
    
    async def import_assets_from_excel(
        self,
        file_path: str,
        sheet_name: str = STANDARD_SHEET_NAME,
        db: Session = None
    ) -> Dict[str, Any]:
        """从Excel导入资产数据"""
        try:
            # 读取Excel文件
            df = self.processor.read_excel_file(file_path, sheet_name)
            
            # 数据清洗和转换
            df = self.processor.clean_and_transform_data(df)
            
            # 数据验证
            validation_errors = self.processor.validate_data(df)
            if validation_errors:
                return {
                    "success": 0,
                    "failed": len(df),
                    "total": len(df),
                    "errors": validation_errors
                }
            
            # 转换为资产模型
            assets = self.processor.convert_to_asset_models(df)
            
            if not assets:
                return {
                    "success": 0,
                    "failed": 0,
                    "total": len(df),
                    "errors": ["没有有效的资产数据可以导入"]
                }
            
            # 保存到数据库
            if db is None:
                db = next(get_db())
            
            success_count, failed_count, errors = await self._save_assets(assets, db)
            
            return {
                "success": success_count,
                "failed": failed_count,
                "total": len(assets),
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Excel导入失败: {str(e)}")
            return {
                "success": 0,
                "failed": 0,
                "total": 0,
                "errors": [f"导入失败: {str(e)}"]
            }
    
    async def _save_assets(
        self,
        assets: List[AssetCreate],
        db: Session
    ) -> tuple[int, int, List[str]]:
        """批量保存资产到数据库 - 优化性能"""
        if not assets:
            return 0, 0, []

        success_count = 0
        failed_count = 0
        errors = []

        try:
            # 批量插入优化
            batch_size = 100  # 每批100条记录
            total_batches = (len(assets) + batch_size - 1) // batch_size

            logger.info(f"开始批量导入: 共 {len(assets)} 条记录, 分 {total_batches} 批处理")

            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min((batch_num + 1) * batch_size, len(assets))
                batch_assets = assets[start_idx:end_idx]

                try:
                    # 批量创建资产记录
                    asset_dicts = []
                    for asset in batch_assets:
                        asset_dict = asset.model_dump()
                        # 添加必要的时间戳
                        from datetime import datetime, timezone
                        asset_dict['created_at'] = datetime.now()
                        asset_dict['updated_at'] = datetime.now()
                        asset_dicts.append(asset_dict)

                    # 使用SQLAlchemy core进行批量插入
                    from sqlalchemy import insert
                    from src.models.asset import Asset

                    stmt = insert(Asset).values(asset_dicts)
                    result = db.execute(stmt)
                    batch_success = result.rowcount

                    success_count += batch_success
                    logger.info(f"第 {batch_num + 1}/{total_batches} 批插入成功: {batch_success} 条")

                except Exception as e:
                    # 批量插入失败，尝试逐条插入
                    logger.warning(f"第 {batch_num + 1} 批插入失败，尝试逐条插入: {str(e)}")

                    for i, asset in enumerate(batch_assets):
                        try:
                            self.asset_crud.create(db, obj_in=asset)
                            success_count += 1
                        except Exception as inner_e:
                            error_msg = f"第{start_idx + i + 1}行 保存失败 - {str(inner_e)}"
                            errors.append(error_msg)
                            failed_count += 1

                # 定期提交，避免大事务
                if batch_num % 5 == 0 or batch_num == total_batches - 1:
                    db.commit()
                    logger.info(f"已提交 {batch_num + 1}/{total_batches} 批数据")

            # 最终提交
            db.commit()
            logger.info(f"批量导入完成: 成功 {success_count}, 失败 {failed_count}")

        except Exception as e:
            db.rollback()
            logger.error(f"批量导入失败: {str(e)}")
            return 0, len(assets), [f"批量导入失败: {str(e)}"]

        return success_count, failed_count, errors
