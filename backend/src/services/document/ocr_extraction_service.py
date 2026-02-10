"""
OCR extraction service for contracts and property certificates.

Pipeline:
1) GLM-OCR layout parsing -> Markdown text
2) LLM text extraction (optional) or regex fallback
"""

from __future__ import annotations

import logging
import os
from typing import Any

from ...core.exception_handler import ConfigurationError
from ...schemas.property_certificate import PROPERTY_CERT_EXTRACTION_PROMPT
from ..core.glm_ocr_service import get_glm_ocr_service
from ..core.llm_service import create_llm_service
from .config import LLMProvider
from .contract_extractor import ContractExtractor
from .utils import build_field_evidence, extract_json_from_response

logger = logging.getLogger(__name__)


CONTRACT_OCR_PROMPT = """请根据以下租赁合同OCR文本提取信息，并严格返回JSON格式：

{
  "contract_number": "合同编号",
  "sign_date": "签订日期(YYYY-MM-DD)",
  "landlord_name": "出租方/甲方名称",
  "landlord_legal_rep": "法定代表人",
  "landlord_phone": "甲方联系电话",
  "landlord_address": "甲方地址",
  "tenant_name": "承租方/乙方名称",
  "tenant_id": "身份证号或统一社会信用代码",
  "tenant_phone": "乙方联系电话",
  "tenant_address": "乙方地址",
  "tenant_usage": "租赁用途",
  "property_address": "租赁物业地址",
  "property_area": "建筑面积(数字,平方米)",
  "lease_start_date": "合同开始日期(YYYY-MM-DD)",
  "lease_end_date": "合同结束日期(YYYY-MM-DD)",
  "deposit": "押金/保证金(数字)",
  "payment_cycle": "付款周期(月付/季付/半年付/年付)",
  "rent_terms": [
    {
      "start_date": "该条款开始日期(YYYY-MM-DD)",
      "end_date": "该条款结束日期(YYYY-MM-DD)",
      "monthly_rent": "月租金(数字)",
      "management_fee": "物业管理费(数字,可选)",
      "description": "条款说明(如:第一年/年递增5%等)"
    }
  ]
}

规则：
1. 若无法识别字段，返回 null
2. 日期格式统一 YYYY-MM-DD
3. 金额只返回数字
4. 仅输出JSON，不要额外说明
"""


PROPERTY_CERT_OCR_PROMPT = (
    PROPERTY_CERT_EXTRACTION_PROMPT.replace("图像", "OCR文本").strip()
)


class OCRExtractionService:
    """OCR extraction pipeline for documents."""

    def __init__(self) -> None:
        self.ocr_service = get_glm_ocr_service()
        self.contract_extractor = ContractExtractor()
        try:
            from src.core.config import settings

            self.text_max_chars = int(settings.GLM_OCR_TEXT_MAX_CHARS)
        except Exception:
            self.text_max_chars = int(os.getenv("GLM_OCR_TEXT_MAX_CHARS", "12000"))

    def _normalize_ocr_text(self, md_results: Any) -> str:
        if isinstance(md_results, list):
            return "\n".join(str(item) for item in md_results if item)
        if isinstance(md_results, str):
            return md_results
        return ""

    def _trim_text(self, text: str) -> str:
        if not text:
            return ""
        if len(text) <= self.text_max_chars:
            return text
        return text[: self.text_max_chars]

    def _flatten_regex_fields(self, fields: dict[str, Any]) -> dict[str, Any]:
        flattened: dict[str, Any] = {}
        for key, value in fields.items():
            if isinstance(value, dict) and "value" in value:
                flattened[key] = value.get("value")
            else:
                flattened[key] = value
        return flattened

    def _build_regex_evidence(self, fields: dict[str, Any]) -> dict[str, Any]:
        evidence: dict[str, Any] = {}
        for key, value in fields.items():
            if not isinstance(value, dict):
                continue
            snippet = value.get("source_text")
            if snippet:
                evidence[key] = {
                    "snippet": snippet,
                    "match": value.get("value"),
                    "match_type": "regex",
                    "source": "regex",
                }
        return evidence

    def _estimate_confidence(self, fields: dict[str, Any]) -> float:
        if not fields:
            return 0.0
        total = len(fields)
        filled = sum(
            1 for value in fields.values() if value not in (None, "", [], {})
        )
        ratio = filled / total if total else 0.0
        return round(0.6 + 0.4 * ratio, 2)

    def _build_field_sources(self, fields: dict[str, Any], source: str) -> dict[str, str]:
        return {key: source for key in fields.keys()}

    async def _extract_with_llm(self, prompt: str, ocr_text: str) -> dict[str, Any]:
        try:
            from src.core.config import settings

            provider_name: str = (
                settings.EXTRACTION_LLM_PROVIDER or settings.LLM_PROVIDER or "hunyuan"
            )
        except Exception:
            provider_name = (
                os.getenv("EXTRACTION_LLM_PROVIDER")
                or os.getenv("LLM_PROVIDER")
                or "hunyuan"
            )
        provider = LLMProvider.normalize(provider_name)
        service = create_llm_service(provider)

        messages = [
            {"role": "system", "content": "你是信息抽取助手，只输出JSON。"},
            {"role": "user", "content": f"{prompt}\n\nOCR文本：\n{ocr_text}"},
        ]

        response = await service.chat_completion(messages=messages, temperature=0.0)
        json_data = extract_json_from_response(response.content)
        return json_data or {}

    async def extract_contract(self, file_path: str) -> dict[str, Any]:
        if not self.ocr_service.is_available:
            return {
                "success": False,
                "error": "GLM-OCR not configured or disabled",
                "extraction_method": "ocr_unavailable",
            }

        try:
            ocr_result = await self.ocr_service.layout_parsing(file_path=file_path)
        except ConfigurationError as exc:
            return {
                "success": False,
                "error": str(exc),
                "extraction_method": "ocr_unavailable",
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "extraction_method": "ocr_failed",
            }

        ocr_text = self._normalize_ocr_text(ocr_result.get("md_results"))
        ocr_text = self._trim_text(ocr_text)

        if not ocr_text:
            return {
                "success": False,
                "error": "OCR text empty",
                "extraction_method": "ocr_failed",
            }

        llm_fields: dict[str, Any] = {}
        try:
            llm_fields = await self._extract_with_llm(CONTRACT_OCR_PROMPT, ocr_text)
        except Exception as exc:
            logger.warning("OCR LLM extraction failed, fallback to regex: %s", exc)

        if llm_fields:
            confidence = self._estimate_confidence(llm_fields)
            return {
                "success": True,
                "extracted_fields": llm_fields,
                "raw_llm_json": llm_fields,
                "confidence": confidence,
                "extraction_method": "ocr_text",
                "markdown_content": ocr_text,
                "field_evidence": build_field_evidence(
                    ocr_text, llm_fields, source="ocr_llm"
                ),
                "field_sources": self._build_field_sources(llm_fields, "ocr_llm"),
                "usage": ocr_result.get("usage"),
                "ocr_metadata": {
                    "layout_details": ocr_result.get("layout_details"),
                    "layout_visualization": ocr_result.get("layout_visualization"),
                    "data_info": ocr_result.get("data_info"),
                },
            }

        regex_result = self.contract_extractor.extract_contract_info(ocr_text)
        raw_regex_fields = regex_result.get("extracted_fields", {})
        regex_fields = self._flatten_regex_fields(raw_regex_fields)
        regex_evidence = self._build_regex_evidence(raw_regex_fields)
        confidence = float(regex_result.get("overall_confidence", 0.0) or 0.0)

        return {
            "success": bool(regex_fields),
            "extracted_fields": regex_fields,
            "raw_llm_json": regex_fields,
            "confidence": confidence,
            "extraction_method": "ocr_regex",
            "markdown_content": ocr_text,
            "field_evidence": regex_evidence
            or build_field_evidence(ocr_text, regex_fields, source="ocr_regex"),
            "field_sources": self._build_field_sources(regex_fields, "ocr_regex"),
            "usage": ocr_result.get("usage"),
            "ocr_metadata": {
                "layout_details": ocr_result.get("layout_details"),
                "layout_visualization": ocr_result.get("layout_visualization"),
                "data_info": ocr_result.get("data_info"),
            },
        }

    async def extract_property_cert(self, file_path: str) -> dict[str, Any]:
        if not self.ocr_service.is_available:
            return {
                "success": False,
                "error": "GLM-OCR not configured or disabled",
                "extraction_method": "ocr_unavailable",
            }

        try:
            ocr_result = await self.ocr_service.layout_parsing(file_path=file_path)
        except ConfigurationError as exc:
            return {
                "success": False,
                "error": str(exc),
                "extraction_method": "ocr_unavailable",
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "extraction_method": "ocr_failed",
            }

        ocr_text = self._normalize_ocr_text(ocr_result.get("md_results"))
        ocr_text = self._trim_text(ocr_text)

        if not ocr_text:
            return {
                "success": False,
                "error": "OCR text empty",
                "extraction_method": "ocr_failed",
            }

        extracted: dict[str, Any] = {}
        try:
            extracted = await self._extract_with_llm(
                PROPERTY_CERT_OCR_PROMPT, ocr_text
            )
        except Exception as exc:
            logger.warning("Property cert OCR LLM extraction failed: %s", exc)

        confidence = self._estimate_confidence(extracted)

        return {
            "success": bool(extracted),
            "extracted_fields": extracted,
            "raw_llm_json": extracted,
            "confidence": confidence,
            "extraction_method": "ocr_text",
            "markdown_content": ocr_text,
            "field_evidence": build_field_evidence(
                ocr_text, extracted, source="ocr_llm"
            ),
            "field_sources": self._build_field_sources(extracted, "ocr_llm"),
            "usage": ocr_result.get("usage"),
            "ocr_metadata": {
                "layout_details": ocr_result.get("layout_details"),
                "layout_visualization": ocr_result.get("layout_visualization"),
                "data_info": ocr_result.get("data_info"),
            },
        }
