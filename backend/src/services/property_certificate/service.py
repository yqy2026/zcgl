"""
Property Certificate Service
产权证服务层

业务逻辑：
- extract_from_file: 上传并提取产权证信息
- confirm_import: 确认导入，创建产权证记录
"""

import logging
import os
import tempfile
from typing import Any

from sqlalchemy.orm import Session

from ...database import get_db
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

    async def extract_from_file(
        self, file_path: str, filename: str
    ) -> dict[str, Any]:
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

            logger.info(f"产权证提取完成: {filename}, confidence={result.get('confidence', 0)}")

            return {
                "success": result.get("success", False),
                "data": result.get("extracted_fields", {}),
                "confidence": result.get("confidence", 0.0),
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

    async def confirm_import(self, data: dict[str, Any]) -> Any:
        """
        确认导入，创建产权证记录

        Args:
            data: 包含提取字段和用户确认信息的字典

        Returns:
            创建的产权证模型实例
        """
        # TODO: 实现 actual database persistence
        # 这个方法将在后续任务中实现完整的 CRUD 操作
        logger.info(f"确认导入产权证: {data.get('certificate_number')}")

        # Placeholder - 返回一个模拟对象
        class MockCertificate:
            def __init__(self, data: dict[str, Any]):
                self.id = 1  # Placeholder ID
                self.data = data

        return MockCertificate(data)
