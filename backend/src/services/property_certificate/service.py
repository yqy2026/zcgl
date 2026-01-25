"""
Property Certificate Service
产权证服务层

业务逻辑：
- extract_from_file: 上传并提取产权证信息
- confirm_import: 确认导入，创建产权证记录
"""

import logging
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from ...crud.property_certificate import property_certificate_crud, property_owner_crud
from ...models.property_certificate import PropertyCertificate
from ...schemas.property_certificate import (
    PropertyCertificateCreate,
    PropertyOwnerCreate,
)
from ...services.document.extractors.property_cert_adapter import PropertyCertAdapter

logger = logging.getLogger(__name__)


class PropertyCertificateService:
    """
    产权证服务

    负责产权证文件的AI提取和导入流程
    """

    def __init__(self, db: Session):
        """
        初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.extractor = PropertyCertAdapter()

    async def extract_from_file(self, file_path: str, filename: str) -> dict[str, Any]:
        """
        从文件提取产权证信息

        Args:
            file_path: 上传文件的临时路径
            filename: 原始文件名

        Returns:
            提取结果字典，包含：
            - success: bool
            - data: dict (提取的字段)
            - confidence: float
            - raw_response: Any
            - extraction_method: str
        """
        try:
            logger.info(f"开始提取产权证: {filename}")

            # 使用 PropertyCertAdapter 提取信息
            result = await self.extractor.extract(file_path)

            logger.info(
                f"产权证提取完成: {filename}, confidence={result.get('confidence', 0)}"
            )

            return {
                "success": result.get("success", False),
                "data": result.get("extracted_fields", {}),
                "confidence": result.get("confidence") or 0.0,
                "raw_response": result.get("raw_response"),
                "extraction_method": result.get("extraction_method", "unknown"),
                "filename": filename,
            }

        except Exception as e:
            logger.error(f"提取产权证失败: {filename}, error={str(e)}")
            return {
                "success": False,
                "error": str(e),
                "filename": filename,
            }

    async def confirm_import(self, data: dict[str, Any]) -> PropertyCertificate:
        """
        确认导入，创建产权证记录

        Args:
            data: 包含提取字段和用户确认信息的字典
                - certificate_number: 证书编号
                - certificate_type: 证书类型
                - extraction_data: 提取的字段数据
                - owners: 权利人信息列表 (可选)

        Returns:
            PropertyCertificate: 创建的产权证对象

        Raises:
            ValueError: 数据验证失败
            Exception: 数据库操作失败
        """
        try:
            # 提取数据
            certificate_number = data.get("certificate_number")
            extraction_data = data.get("extraction_data", {})
            owners_data = data.get("owners", [])

            if not certificate_number:
                raise ValueError("缺少证书编号")

            logger.info(f"确认导入产权证: {certificate_number}")

            # 🔒 功能修复: 实现实际的数据库持久化

            # 1. 检查证书是否已存在
            existing = property_certificate_crud.get_by_certificate_number(
                self.db, certificate_number
            )
            if existing:
                logger.warning(f"产权证已存在: {certificate_number}")
                return existing

            # 2. 准备产权证数据
            certificate_create_data = {
                "certificate_number": certificate_number,
                "certificate_type": extraction_data.get("certificate_type", "房产证"),
                "extraction_confidence": extraction_data.get("confidence", 0.0),
                "extraction_source": "llm",
                "is_verified": False,  # 需要人工审核
                # 基本信息
                "registration_date": self._parse_date(
                    extraction_data.get("registration_date")
                ),
                "property_address": extraction_data.get("property_address"),
                "property_type": extraction_data.get("property_type"),
                # 房屋信息
                "building_area": extraction_data.get("building_area"),
                "floor_info": extraction_data.get("floor_info"),
                # 土地信息
                "land_area": extraction_data.get("land_area"),
                "land_use_type": extraction_data.get("land_use_type"),
                "land_use_term_start": self._parse_date(
                    extraction_data.get("land_use_term_start")
                ),
                "land_use_term_end": self._parse_date(
                    extraction_data.get("land_use_term_end")
                ),
                # 其他信息
                "co_ownership": extraction_data.get("co_ownership"),
                "restrictions": extraction_data.get("restrictions"),
                "remarks": extraction_data.get("remarks"),
            }

            # 3. 创建权利人记录（如果有）
            owner_ids = []
            for owner_data in owners_data:
                owner_create_data = PropertyOwnerCreate(
                    owner_type=owner_data.get("owner_type", "个人"),
                    name=owner_data.get("name"),
                    id_type=owner_data.get("id_type"),
                    id_number=owner_data.get("id_number"),  # 🔒 会被CRUD层加密
                    phone=owner_data.get("phone"),  # 🔒 会被CRUD层加密
                    address=owner_data.get("address"),
                    organization_id=owner_data.get("organization_id"),
                )

                # 🔒 安全修复: 使用property_owner_crud创建权利人（自动加密PII）
                owner = property_owner_crud.create(self.db, obj_in=owner_create_data)
                owner_ids.append(owner.id)

            # 4. 创建产权证记录
            certificate_create = PropertyCertificateCreate(**certificate_create_data)
            certificate = property_certificate_crud.create_with_owners(
                self.db,
                obj_in=certificate_create,
                owner_ids=owner_ids if owner_ids else None,
            )

            logger.info(f"产权证创建成功: {certificate.id} - {certificate_number}")
            return certificate

        except ValueError as e:
            logger.error(f"数据验证失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"创建产权证失败: certificate_number={data.get('certificate_number')}, error={str(e)}"
            )
            raise

    def _parse_date(self, date_str: str | None) -> date | None:
        """
        解析日期字符串

        Args:
            date_str: 日期字符串 (格式: YYYY-MM-DD 或 YYYY/MM/DD)

        Returns:
            date | None: 解析后的日期对象
        """
        if not date_str:
            return None

        from datetime import datetime

        # 尝试常见日期格式
        formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        logger.warning(f"无法解析日期: {date_str}")
        return None
