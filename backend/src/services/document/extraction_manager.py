"""
Document Extraction Manager
统一的文档提取管理器

提供多文档类型支持和 LLM Vision 统一入口
Provides multi-document-type support with unified LLM Vision entry point

2026-01 重构: 移除传统识别依赖，专注 LLM Vision
"""

import logging
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..llm_prompt.prompt_manager import PromptManager
from .extractors.factory import ExtractorFactory

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ============================================================================
# 文档类型定义
# ============================================================================


class DocumentType(str, Enum):
    """支持的文档类型"""

    CONTRACT = "contract"  # 租赁合同
    PROPERTY_CERT = "property_cert"  # 产权证/不动产权证
    UNKNOWN = "unknown"  # 未知类型


class ExtractionResult(BaseModel):
    """统一提取结果"""

    success: bool
    document_type: DocumentType
    confidence_score: float = 0.0
    extracted_fields: dict[str, Any] = {}
    extraction_method: str = ""
    processing_time_ms: float = 0.0
    warnings: list[str] = []
    error: str | None = None


# ============================================================================
# 文档分类器
# ============================================================================


class KeywordClassifier:
    """基于关键词的文档分类器"""

    CONTRACT_KEYWORDS = [
        "出租方",
        "承租方",
        "租赁合同",
        "租赁期限",
        "月租金",
        "租金",
        "甲方",
        "乙方",
        "租赁",
        "合同编号",
    ]

    PROPERTY_CERT_KEYWORDS = [
        "不动产权证",
        "房屋所有权证",
        "权利人",
        "坐落",
        "建筑面积",
        "土地使用权",
        "登记日期",
        "不动产单元号",
        "共有情况",
    ]

    @classmethod
    def classify(cls, text: str) -> DocumentType:
        """根据文本内容分类文档类型"""
        text_lower = text.lower()

        contract_score = sum(1 for kw in cls.CONTRACT_KEYWORDS if kw in text_lower)
        property_score = sum(1 for kw in cls.PROPERTY_CERT_KEYWORDS if kw in text_lower)

        logger.debug(
            f"Classification scores - Contract: {contract_score}, Property: {property_score}"
        )

        if contract_score > property_score and contract_score >= 2:
            return DocumentType.CONTRACT
        elif property_score > contract_score and property_score >= 2:
            return DocumentType.PROPERTY_CERT
        else:
            return DocumentType.UNKNOWN


# ============================================================================
# 提取管理器
# ============================================================================


class DocumentExtractionManager:
    """
    统一文档提取管理器

    负责:
    - 文档类型检测
    - 调用对应的 LLM Vision Adapter
    - 结果标准化
    """

    _contract_extractor: Any
    _property_cert_extractor: (
        Any  # PropertyCertAdapter | None (use Any to avoid TYPE_CHECKING issues)
    )
    classifier: KeywordClassifier

    def __init__(self) -> None:
        # 默认使用合同提取器
        self._contract_extractor = ExtractorFactory.get_extractor()
        self._property_cert_extractor = None  # 懒加载
        self.classifier = KeywordClassifier()
        logger.info("DocumentExtractionManager initialized")

    def _get_property_cert_extractor(self) -> Any:
        """懒加载产权证提取器"""
        if self._property_cert_extractor is None:
            from .extractors.property_cert_adapter import PropertyCertAdapter

            self._property_cert_extractor = PropertyCertAdapter()
        return self._property_cert_extractor

    async def extract(
        self,
        file_path: str,
        doc_type: DocumentType | str | None = None,
        db: AsyncSession | None = None,
    ) -> ExtractionResult:
        """
        统一提取入口

        Args:
            file_path: 文件路径 (PDF/图片)
            doc_type: 文档类型 (可选，不指定则自动检测)

        Returns:
            ExtractionResult: 标准化提取结果
        """
        import time

        start_time = time.time()

        # 验证文件存在
        path = Path(file_path)
        if not path.exists():
            return ExtractionResult(
                success=False,
                document_type=DocumentType.UNKNOWN,
                error=f"File not found: {file_path}",
            )

        # 解析文档类型
        if doc_type is None:
            detected_type = DocumentType.CONTRACT  # 默认合同
        elif isinstance(doc_type, str):
            try:
                detected_type = DocumentType(doc_type)
            except ValueError:
                detected_type = DocumentType.UNKNOWN
        else:
            detected_type = doc_type

        logger.info(f"Extracting {file_path} as {detected_type.value}")

        try:
            # 根据文档类型选择提取器
            if detected_type == DocumentType.PROPERTY_CERT:
                extractor = self._get_property_cert_extractor()
            else:
                extractor = self._contract_extractor

            prompt = None
            if detected_type == DocumentType.PROPERTY_CERT and db is not None:
                prompt_manager = PromptManager()
                prompt = await prompt_manager.get_active_prompt_async(
                    db, doc_type="PROPERTY_CERT", provider="qwen"
                )

            if prompt is not None:
                result = await extractor.extract(file_path, prompt=prompt)
            else:
                result = await extractor.extract(file_path)

            processing_time = (time.time() - start_time) * 1000

            return ExtractionResult(
                success=result.get("success", False),
                document_type=detected_type,
                confidence_score=result.get("confidence", 0.0),
                extracted_fields=result.get("extracted_fields", result.get("data", {})),
                extraction_method=result.get("extraction_method", "vision"),
                processing_time_ms=processing_time,
                warnings=result.get("warnings", []),
            )

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            processing_time = (time.time() - start_time) * 1000

            return ExtractionResult(
                success=False,
                document_type=detected_type,
                processing_time_ms=processing_time,
                error=str(e),
            )


# ============================================================================
# 单例和便捷函数
# ============================================================================

_manager: DocumentExtractionManager | None = None


def get_extraction_manager() -> DocumentExtractionManager:
    """获取或创建提取管理器单例"""
    global _manager
    if _manager is None:
        _manager = DocumentExtractionManager()
    return _manager


def reset_extraction_manager() -> None:
    """重置提取管理器单例"""
    global _manager
    _manager = None
