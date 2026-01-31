"""
Contract Extractor Base Classes and Utilities
合同提取器基类和工具函数
"""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, cast

from ....core.exception_handler import ExternalServiceError

logger = logging.getLogger(__name__)


class ContractExtractorInterface(ABC):
    """
    Abstract base class for Contract Extractors.
    All LLM/OCR providers (GLM-4V, Qwen-VL, DeepSeek) must implement this interface.
    """

    @abstractmethod
    async def extract(self, file_path: str, **kwargs: Any) -> dict[str, Any]:
        """
        Extract structured contract data from a file.

        Args:
            file_path: Absolute path to the file (PDF/Image)
            **kwargs: Additional model-specific parameters (e.g., max_pages, force_ocr)

        Returns:
            Dict containing:
            - success: bool
            - extracted_fields: Dict
            - raw_response: Any
            - confidence: float
            - extraction_method: str
            - usage: Dict (token usage etc.)
        """
        pass


class BaseVisionAdapter(ContractExtractorInterface):
    """
    Base class for Vision-based adapters with common utility methods.
    Subclasses only need to implement _get_vision_service() and optionally override methods.
    """

    # Standard extraction prompt (unified format for all adapters)
    # Aligned with RentContract and RentTerm database models
    EXTRACTION_PROMPT_TEMPLATE = """请分析这份中国房地产租赁合同图片，提取以下信息并返回JSON格式：

{{
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
        {{
            "start_date": "该条款开始日期(YYYY-MM-DD)",
            "end_date": "该条款结束日期(YYYY-MM-DD)",
            "monthly_rent": "月租金(数字)",
            "management_fee": "物业管理费(数字,可选)",
            "description": "条款说明(如:第一年/年递增5%等)"
        }}
    ]
}}

重要提示：
1. 如果合同有阶梯递增租金(如每年递增5%)，请在rent_terms数组中分别列出每个时间段的租金
2. 如果只有一个固定租金，rent_terms数组只需一项
3. 金额只填数字，日期格式YYYY-MM-DD，找不到的字段填null
4. 只返回JSON，不要其他说明{pages_hint}"""

    @property
    @abstractmethod
    def vision_service(self) -> Any:
        """Return the vision service instance (to be implemented by subclass)"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name for error messages"""
        pass

    @property
    @abstractmethod
    def api_key_env_name(self) -> str:
        """Return the env var name for API key (for error messages)"""
        pass

    async def extract(
        self,
        file_path: str,
        max_pages: int = 10,
        batch_size: int = 3,
        dpi: int = 200,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Common extraction logic for all vision adapters.
        """
        from ..pdf_to_images import cleanup_temp_images, pdf_to_images

        if not self.vision_service.is_available:
            return {
                "success": False,
                "error": f"{self.api_key_env_name} not configured",
                "extraction_method": f"{self.provider_name}_unavailable",
            }

        image_paths: list[str] = []
        try:
            logger.info(f"{self.provider_name}Adapter: Converting {file_path}")
            image_paths = pdf_to_images(file_path, dpi=dpi, max_pages=max_pages)

            if not image_paths:
                return {"success": False, "error": "No images extracted from PDF"}

            total_pages = len(image_paths)
            all_results = []

            for i in range(0, total_pages, batch_size):
                batch = image_paths[i : i + batch_size]
                batch_num = i // batch_size + 1

                logger.info(f"Processing batch {batch_num} ({len(batch)} images)")
                prompt = self._build_extraction_prompt(len(batch))

                try:
                    response = await self._extract_with_retry(
                        image_paths=batch, prompt=prompt, temperature=0.1
                    )

                    data = self._parse_json(response.content)
                    all_results.append(
                        {
                            "success": True,
                            "data": data,
                            "images_count": len(batch),
                            "usage": response.usage,
                        }
                    )

                except Exception as e:
                    logger.error(f"Batch {batch_num} failed: {e}")

            if not all_results:
                return {
                    "success": False,
                    "error": "All batches failed to extract data",
                    "extraction_method": f"{self.provider_name}_failed",
                }

            merged_data = self._merge_multi_page_results(all_results)

            return {
                "success": True,
                "extracted_fields": merged_data,
                "raw_llm_json": merged_data,
                "confidence": self._calculate_confidence(all_results),
                "extraction_method": f"vision_{self.provider_name}",
                "pages_processed": total_pages,
                "batches_processed": len(all_results),
                "usage": self._aggregate_usage(all_results),
            }

        except Exception as e:
            logger.error(f"{self.provider_name} extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "extraction_method": f"{self.provider_name}_failed",
            }

        finally:
            if image_paths:
                cleanup_temp_images(image_paths)

    async def _extract_with_retry(
        self, image_paths: list[str], prompt: str, temperature: float = 0.1
    ) -> Any:
        """
        Extract from images with automatic retry on transient errors

        Implements retry logic inline for vision API calls.
        Retries up to 3 times on transient errors (network, timeout, rate limit).
        """
        max_attempts = 3
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                return await self.vision_service.extract_from_images(
                    image_paths=image_paths, prompt=prompt, temperature=temperature
                )
            except Exception as e:
                last_error = e
                error_type = type(e).__name__

                # Check if error is retryable
                retryable_errors = (
                    "ConnectionError",
                    "TimeoutError",
                    "ConnectTimeout",
                    "ConnectTimeoutError",  # Full name for ConnectTimeout
                    "ReadTimeout",
                    "ReadTimeoutError",  # Full name for ReadTimeout
                    "RateLimitError",
                    "APIError",
                )

                if error_type not in retryable_errors:
                    # Non-retryable error, raise immediately
                    logger.warning(
                        f"Non-retryable error in vision API call: {error_type}: {e}"
                    )
                    raise

                if attempt < max_attempts:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** (attempt - 1)
                    logger.warning(
                        f"Vision API call failed (attempt {attempt}/{max_attempts}): "
                        f"{error_type}: {e}. Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Vision API call failed after {max_attempts} attempts: "
                        f"{error_type}: {e}"
                    )

        # All retries exhausted
        last_error_name = type(last_error).__name__ if last_error else "UnknownError"
        raise ExternalServiceError(
            message=f"Vision API call failed after {max_attempts} attempts",
            service_name=self.provider_name,
            service_error=last_error_name,
            details={
                "attempts": max_attempts,
                "last_error": str(last_error) if last_error else None,
            },
        ) from last_error

    def _parse_json(self, content: str) -> dict[str, Any]:
        """Parse JSON from model response (common logic)"""
        try:
            return cast(dict[str, Any], json.loads(content))
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return cast(dict[str, Any], json.loads(match.group(0)))
            raise ExternalServiceError(
                message="模型响应无法解析为JSON",
                service_name="LLM",
                service_error="INVALID_JSON",
                details={"content_preview": content[:200]},
            )

    def _build_extraction_prompt(self, num_images: int) -> str:
        """Build extraction prompt (unified format)"""
        pages_hint = (
            f"\n\n注意：共{num_images}页，请分析所有页面。" if num_images > 1 else ""
        )
        return self.EXTRACTION_PROMPT_TEMPLATE.format(pages_hint=pages_hint)

    def _merge_multi_page_results(
        self, results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Merge results from multiple pages (common logic)"""
        merged: dict[str, Any] = {}

        for result in results:
            if result.get("success") and result.get("data"):
                data = result["data"]
                for key, value in data.items():
                    if value is not None:
                        existing = merged.get(key)
                        if existing is None:
                            merged[key] = value
                        elif isinstance(value, str) and len(value) > len(str(existing)):
                            merged[key] = value

        return merged

    def _calculate_confidence(self, results: list[dict[str, Any]]) -> float:
        """Calculate confidence based on successful batches"""
        if not results:
            return 0.0
        success_count = sum(1 for r in results if r.get("success"))
        return min(0.95, 0.7 + 0.25 * (success_count / len(results)))

    def _aggregate_usage(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate token usage from all batches"""
        total_tokens = 0
        total_images = 0

        for result in results:
            if result.get("usage"):
                total_tokens += result["usage"].get("total_tokens", 0)
            total_images += result.get("images_count", 0)

        return {"total_tokens": total_tokens, "total_images_processed": total_images}
