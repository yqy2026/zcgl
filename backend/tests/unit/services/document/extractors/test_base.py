#!/usr/bin/env python3
"""
Unit Tests for Base Extractor Classes
基础提取器类单元测试

Tests for:
- ContractExtractorInterface (abstract interface)
- BaseVisionAdapter (base class with common utilities)

NOTE: Tests for extract() method are skipped because pdf_to_images module
is not yet implemented (as noted in test_pdf_edge_cases.py).
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.document.extractors.base import (
    BaseVisionAdapter,
    ContractExtractorInterface,
)


# ============================================================================
# Test Fixtures
# ============================================================================


class MockVisionService:
    """Mock vision service for testing"""

    def __init__(self, is_available: bool = True):
        self.is_available = is_available
        self.extract_from_images = AsyncMock()


class ConcreteAdapter(BaseVisionAdapter):
    """Concrete implementation of BaseVisionAdapter for testing"""

    def __init__(self, is_available: bool = True):
        self._vision_service = MockVisionService(is_available)

    @property
    def vision_service(self):
        return self._vision_service

    @property
    def provider_name(self) -> str:
        return "TestProvider"

    @property
    def api_key_env_name(self) -> str:
        return "TEST_API_KEY"


# ============================================================================
# ContractExtractorInterface Tests
# ============================================================================


class TestContractExtractorInterface:
    """Tests for ContractExtractorInterface abstract base class"""

    @pytest.mark.unit
    def test_interface_cannot_be_instantiated(self):
        """Interface should not be directly instantiable"""
        with pytest.raises(TypeError):
            ContractExtractorInterface()  # type: ignore

    @pytest.mark.unit
    def test_interface_has_abstract_extract_method(self):
        """Interface should have abstract extract method"""
        assert hasattr(ContractExtractorInterface, "extract")
        # Check that it's abstract
        assert getattr(ContractExtractorInterface.extract, "__isabstractmethod__", False)


# ============================================================================
# BaseVisionAdapter - Property Tests
# ============================================================================


class TestBaseVisionAdapterProperties:
    """Tests for BaseVisionAdapter abstract properties"""

    @pytest.mark.unit
    def test_vision_service_property_is_abstract(self):
        """vision_service property should be abstract"""
        assert hasattr(BaseVisionAdapter, "vision_service")
        prop = getattr(BaseVisionAdapter, "vision_service")
        assert isinstance(prop, property)
        assert prop.fget.__isabstractmethod__

    @pytest.mark.unit
    def test_provider_name_property_is_abstract(self):
        """provider_name property should be abstract"""
        assert hasattr(BaseVisionAdapter, "provider_name")
        prop = getattr(BaseVisionAdapter, "provider_name")
        assert isinstance(prop, property)
        assert prop.fget.__isabstractmethod__

    @pytest.mark.unit
    def test_api_key_env_name_property_is_abstract(self):
        """api_key_env_name property should be abstract"""
        assert hasattr(BaseVisionAdapter, "api_key_env_name")
        prop = getattr(BaseVisionAdapter, "api_key_env_name")
        assert isinstance(prop, property)
        assert prop.fget.__isabstractmethod__

    @pytest.mark.unit
    def test_base_adapter_cannot_be_instantiated(self):
        """BaseVisionAdapter should not be directly instantiable"""
        with pytest.raises(TypeError):
            BaseVisionAdapter()  # type: ignore


# ============================================================================
# BaseVisionAdapter - extract() Method Tests
# ============================================================================


class TestBaseVisionAdapterExtract:
    """Tests for BaseVisionAdapter.extract() method

    All tests skipped because pdf_to_images module is not yet implemented.
    """

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="pdf_to_images module not yet implemented")
    async def test_extract_returns_error_when_service_unavailable(self):
        """Should return error when vision service is not available"""
        adapter = ConcreteAdapter(is_available=False)

        result = await adapter.extract("/fake/path.pdf")

        assert result["success"] is False
        assert "TEST_API_KEY not configured" in result["error"]
        assert result["extraction_method"] == "TestProvider_unavailable"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="pdf_to_images module not yet implemented")
    async def test_extract_returns_error_when_no_images_converted(self):
        """Should return error when PDF conversion produces no images"""
        adapter = ConcreteAdapter(is_available=True)

        with patch(
            "src.services.document.extractors.base.pdf_to_images", return_value=[]
        ):
            result = await adapter.extract("/fake/path.pdf")

        assert result["success"] is False
        assert result["error"] == "No images extracted from PDF"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="pdf_to_images module not yet implemented")
    async def test_extract_successful_single_page(self):
        """Should successfully extract from single page"""
        adapter = ConcreteAdapter(is_available=True)

        # Mock PDF to images conversion
        image_paths = ["page1.png"]
        mock_response = MagicMock()
        mock_response.content = '{"contract_number": "CT001"}'
        mock_response.usage = {"total_tokens": 100}

        adapter.vision_service.extract_from_images.return_value = mock_response

        with patch(
            "src.services.document.extractors.base.pdf_to_images", return_value=image_paths
        ):
            result = await adapter.extract("/fake/path.pdf")

        assert result["success"] is True
        assert result["extracted_fields"]["contract_number"] == "CT001"
        assert result["pages_processed"] == 1
        assert result["batches_processed"] == 1
        assert result["extraction_method"] == "vision_TestProvider"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="pdf_to_images module not yet implemented")
    async def test_extract_successful_multiple_pages_batching(self):
        """Should successfully extract from multiple pages with batching"""
        adapter = ConcreteAdapter(is_available=True)

        # Mock 5 pages
        image_paths = [f"page{i}.png" for i in range(1, 6)]
        mock_response = MagicMock()
        mock_response.content = '{"page": "data"}'
        mock_response.usage = {"total_tokens": 50}

        adapter.vision_service.extract_from_images.return_value = mock_response

        with patch(
            "src.services.document.extractors.base.pdf_to_images", return_value=image_paths
        ):
            result = await adapter.extract("/fake/path.pdf", batch_size=2)

        assert result["success"] is True
        assert result["pages_processed"] == 5
        assert result["batches_processed"] == 3  # 5 pages / batch_size 2 = 3 batches

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="pdf_to_images module not yet implemented")
    async def test_extract_with_custom_parameters(self):
        """Should pass custom parameters correctly"""
        adapter = ConcreteAdapter(is_available=True)

        image_paths = ["page1.png"]
        mock_response = MagicMock()
        mock_response.content = "{}"
        mock_response.usage = {}

        adapter.vision_service.extract_from_images.return_value = mock_response

        with patch(
            "src.services.document.extractors.base.pdf_to_images", return_value=image_paths
        ) as mock_convert:
            result = await adapter.extract(
                "/fake/path.pdf", max_pages=5, dpi=300, batch_size=2
            )

            # Verify pdf_to_images was called with correct parameters
            mock_convert.assert_called_once_with("/fake/path.pdf", dpi=300, max_pages=5)

        assert result["success"] is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="pdf_to_images module not yet implemented")
    async def test_extract_handles_batch_failure(self):
        """Should handle batch failures gracefully"""
        adapter = ConcreteAdapter(is_available=True)

        image_paths = ["page1.png", "page2.png"]

        # First call fails, second succeeds
        adapter.vision_service.extract_from_images.side_effect = [
            Exception("API Error"),
            MagicMock(content='{"data": "value"}', usage={}),
        ]

        with patch(
            "src.services.document.extractors.base.pdf_to_images", return_value=image_paths
        ):
            result = await adapter.extract("/fake/path.pdf", batch_size=1)

        # Should succeed with one batch
        assert result["success"] is True
        assert result["batches_processed"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="pdf_to_images module not yet implemented")
    async def test_extract_returns_error_when_all_batches_fail(self):
        """Should return error when all batches fail"""
        adapter = ConcreteAdapter(is_available=True)

        image_paths = ["page1.png", "page2.png"]
        adapter.vision_service.extract_from_images.side_effect = Exception("API Error")

        with patch(
            "src.services.document.extractors.base.pdf_to_images", return_value=image_paths
        ):
            result = await adapter.extract("/fake/path.pdf", batch_size=1)

        assert result["success"] is False
        assert result["error"] == "All batches failed to extract data"
        assert result["extraction_method"] == "TestProvider_failed"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="pdf_to_images module not yet implemented")
    async def test_extract_cleans_up_temp_images_on_success(self):
        """Should clean up temporary images on success"""
        adapter = ConcreteAdapter(is_available=True)

        image_paths = ["page1.png"]
        mock_response = MagicMock()
        mock_response.content = "{}"
        mock_response.usage = {}

        adapter.vision_service.extract_from_images.return_value = mock_response

        with patch(
            "src.services.document.extractors.base.pdf_to_images", return_value=image_paths
        ):
            with patch(
                "src.services.document.extractors.base.cleanup_temp_images"
            ) as mock_cleanup:
                result = await adapter.extract("/fake/path.pdf")

                mock_cleanup.assert_called_once_with(image_paths)

        assert result["success"] is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="pdf_to_images module not yet implemented")
    async def test_extract_cleans_up_temp_images_on_failure(self):
        """Should clean up temporary images even on failure"""
        adapter = ConcreteAdapter(is_available=True)

        image_paths = ["page1.png"]
        adapter.vision_service.extract_from_images.side_effect = Exception("API Error")

        with patch(
            "src.services.document.extractors.base.pdf_to_images", return_value=image_paths
        ):
            with patch(
                "src.services.document.extractors.base.cleanup_temp_images"
            ) as mock_cleanup:
                result = await adapter.extract("/fake/path.pdf")

                mock_cleanup.assert_called_once_with(image_paths)

        assert result["success"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="pdf_to_images module not yet implemented")
    async def test_extract_handles_exception_in_conversion(self):
        """Should handle exceptions during PDF conversion"""
        adapter = ConcreteAdapter(is_available=True)

        with patch(
            "src.services.document.extractors.base.pdf_to_images",
            side_effect=Exception("Conversion failed"),
        ):
            result = await adapter.extract("/fake/path.pdf")

        assert result["success"] is False
        assert "Conversion failed" in result["error"]
        assert result["extraction_method"] == "TestProvider_failed"


# ============================================================================
# BaseVisionAdapter - _extract_with_retry() Tests
# ============================================================================


class TestBaseVisionAdapterExtractWithRetry:
    """Tests for BaseVisionAdapter._extract_with_retry() method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_succeeds_on_first_attempt(self):
        """Should succeed on first attempt"""
        adapter = ConcreteAdapter(is_available=True)

        mock_response = MagicMock()
        adapter.vision_service.extract_from_images.return_value = mock_response

        result = await adapter._extract_with_retry(
            image_paths=["page1.png"], prompt="test"
        )

        assert result is mock_response
        adapter.vision_service.extract_from_images.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_retries_on_connection_error(self):
        """Should retry on ConnectionError"""
        adapter = ConcreteAdapter(is_available=True)

        mock_response = MagicMock()
        adapter.vision_service.extract_from_images.side_effect = [
            ConnectionError("Network error"),
            mock_response,
        ]

        result = await adapter._extract_with_retry(
            image_paths=["page1.png"], prompt="test"
        )

        assert result is mock_response
        assert adapter.vision_service.extract_from_images.call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_retries_on_timeout_error(self):
        """Should retry on TimeoutError"""
        adapter = ConcreteAdapter(is_available=True)

        mock_response = MagicMock()
        adapter.vision_service.extract_from_images.side_effect = [
            TimeoutError("Request timeout"),
            mock_response,
        ]

        result = await adapter._extract_with_retry(
            image_paths=["page1.png"], prompt="test"
        )

        assert result is mock_response
        assert adapter.vision_service.extract_from_images.call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_retries_on_rate_limit_error(self):
        """Should retry on RateLimitError"""
        adapter = ConcreteAdapter(is_available=True)

        mock_response = MagicMock()

        # Create a custom RateLimitError
        class RateLimitError(Exception):
            pass

        adapter.vision_service.extract_from_images.side_effect = [
            RateLimitError("Rate limit exceeded"),
            mock_response,
        ]

        result = await adapter._extract_with_retry(
            image_paths=["page1.png"], prompt="test"
        )

        assert result is mock_response
        assert adapter.vision_service.extract_from_images.call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_uses_exponential_backoff(self):
        """Should use exponential backoff between retries"""
        adapter = ConcreteAdapter(is_available=True)

        mock_response = MagicMock()
        adapter.vision_service.extract_from_images.side_effect = [
            ConnectionError("Error 1"),
            ConnectionError("Error 2"),
            mock_response,
        ]

        with patch("asyncio.sleep") as mock_sleep:
            result = await adapter._extract_with_retry(
                image_paths=["page1.png"], prompt="test"
            )

            assert result is mock_response
            # Check exponential backoff: 1s, 2s
            assert mock_sleep.call_args_list[0][0][0] == 1
            assert mock_sleep.call_args_list[1][0][0] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_raises_after_max_attempts(self):
        """Should raise RuntimeError after max retry attempts"""
        adapter = ConcreteAdapter(is_available=True)

        adapter.vision_service.extract_from_images.side_effect = ConnectionError(
            "Persistent error"
        )

        with pytest.raises(RuntimeError, match="failed after 3 attempts"):
            await adapter._extract_with_retry(
                image_paths=["page1.png"], prompt="test"
            )

        assert adapter.vision_service.extract_from_images.call_count == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_does_not_retry_non_retryable_errors(self):
        """Should not retry on non-retryable errors"""
        adapter = ConcreteAdapter(is_available=True)

        adapter.vision_service.extract_from_images.side_effect = ValueError(
            "Invalid input"
        )

        with pytest.raises(ValueError, match="Invalid input"):
            await adapter._extract_with_retry(
                image_paths=["page1.png"], prompt="test"
            )

        # Should only call once (no retries)
        assert adapter.vision_service.extract_from_images.call_count == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_with_custom_temperature(self):
        """Should pass temperature parameter correctly"""
        adapter = ConcreteAdapter(is_available=True)

        mock_response = MagicMock()
        adapter.vision_service.extract_from_images.return_value = mock_response

        await adapter._extract_with_retry(
            image_paths=["page1.png"], prompt="test", temperature=0.5
        )

        # Verify temperature was passed
        adapter.vision_service.extract_from_images.assert_called_once()
        call_kwargs = adapter.vision_service.extract_from_images.call_args.kwargs
        assert call_kwargs.get("temperature") == 0.5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_with_read_timeout(self):
        """Should retry on ReadTimeout errors"""
        adapter = ConcreteAdapter(is_available=True)

        # Create a custom ReadTimeout error
        class ReadTimeout(Exception):
            pass

        mock_response = MagicMock()
        adapter.vision_service.extract_from_images.side_effect = [
            ReadTimeout("Read timeout"),
            mock_response,
        ]

        result = await adapter._extract_with_retry(
            image_paths=["page1.png"], prompt="test"
        )

        assert result is mock_response
        assert adapter.vision_service.extract_from_images.call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_with_connect_timeout(self):
        """Should retry on ConnectTimeout errors"""
        adapter = ConcreteAdapter(is_available=True)

        # Create a custom ConnectTimeout error
        class ConnectTimeout(Exception):
            pass

        mock_response = MagicMock()
        adapter.vision_service.extract_from_images.side_effect = [
            ConnectTimeout("Connection timeout"),
            mock_response,
        ]

        result = await adapter._extract_with_retry(
            image_paths=["page1.png"], prompt="test"
        )

        assert result is mock_response
        assert adapter.vision_service.extract_from_images.call_count == 2


# ============================================================================
# BaseVisionAdapter - _parse_json() Tests
# ============================================================================


class TestBaseVisionAdapterParseJson:
    """Tests for BaseVisionAdapter._parse_json() method"""

    @pytest.mark.unit
    def test_parse_json_valid_json(self):
        """Should parse valid JSON successfully"""
        adapter = ConcreteAdapter()

        result = adapter._parse_json('{"key": "value"}')

        assert result == {"key": "value"}

    @pytest.mark.unit
    def test_parse_json_with_extra_text(self):
        """Should extract JSON from response with extra text"""
        adapter = ConcreteAdapter()

        content = 'Here is the result: {"key": "value"} - end of response'
        result = adapter._parse_json(content)

        assert result == {"key": "value"}

    @pytest.mark.unit
    def test_parse_json_with_multiple_braces(self):
        """Should extract JSON when text has multiple braces"""
        adapter = ConcreteAdapter()

        content = 'Text before {"key": "value", "nested": {"data": true}} text after'
        result = adapter._parse_json(content)

        # Should extract the complete JSON object
        assert result["key"] == "value"
        assert result["nested"]["data"] is True

    @pytest.mark.unit
    def test_parse_json_with_array_response(self):
        """Should parse JSON array responses"""
        adapter = ConcreteAdapter()

        content = '{"items": [1, 2, 3], "count": 3}'
        result = adapter._parse_json(content)

        assert result["items"] == [1, 2, 3]
        assert result["count"] == 3

    @pytest.mark.unit
    def test_parse_json_with_multiline_json(self):
        """Should parse multiline JSON using regex"""
        adapter = ConcreteAdapter()

        content = """
        Some text before
        {
            "contract_number": "CT001",
            "sign_date": "2026-01-01"
        }
        Some text after
        """
        result = adapter._parse_json(content)

        assert result["contract_number"] == "CT001"
        assert result["sign_date"] == "2026-01-01"

    @pytest.mark.unit
    def test_parse_json_raises_on_invalid_json(self):
        """Should raise ValueError on completely invalid JSON"""
        adapter = ConcreteAdapter()

        with pytest.raises(ValueError, match="Could not parse JSON"):
            adapter._parse_json("This is not JSON at all")

    @pytest.mark.unit
    def test_parse_json_includes_content_snippet_in_error(self):
        """Error message should include snippet of content"""
        adapter = ConcreteAdapter()

        with pytest.raises(ValueError) as exc_info:
            adapter._parse_json("invalid json content here")

        error_msg = str(exc_info.value)
        assert "invalid json content here" in error_msg or "invalid json" in error_msg

    @pytest.mark.unit
    def test_parse_json_with_nested_json(self):
        """Should parse JSON with nested structures"""
        adapter = ConcreteAdapter()

        content = '{"rent_terms": [{"start_date": "2026-01-01", "monthly_rent": 1000}]}'
        result = adapter._parse_json(content)

        assert result["rent_terms"][0]["start_date"] == "2026-01-01"
        assert result["rent_terms"][0]["monthly_rent"] == 1000

    @pytest.mark.unit
    def test_parse_json_empty_dict(self):
        """Should parse empty JSON object"""
        adapter = ConcreteAdapter()

        result = adapter._parse_json("{}")

        assert result == {}

    @pytest.mark.unit
    def test_parse_json_with_unicode(self):
        """Should parse JSON with unicode characters"""
        adapter = ConcreteAdapter()

        content = '{"landlord": "张三", "tenant": "李四"}'
        result = adapter._parse_json(content)

        assert result["landlord"] == "张三"
        assert result["tenant"] == "李四"


# ============================================================================
# BaseVisionAdapter - _build_extraction_prompt() Tests
# ============================================================================


class TestBaseVisionAdapterBuildExtractionPrompt:
    """Tests for BaseVisionAdapter._build_extraction_prompt() method"""

    @pytest.mark.unit
    def test_build_prompt_single_page(self):
        """Should build prompt without pages hint for single page"""
        adapter = ConcreteAdapter()

        prompt = adapter._build_extraction_prompt(1)

        # Should not contain pages hint
        assert "共1页" not in prompt
        assert "注意：共" not in prompt

    @pytest.mark.unit
    def test_build_prompt_multiple_pages(self):
        """Should build prompt with pages hint for multiple pages"""
        adapter = ConcreteAdapter()

        prompt = adapter._build_extraction_prompt(3)

        # Should contain pages hint
        assert "共3页" in prompt
        assert "请分析所有页面" in prompt

    @pytest.mark.unit
    def test_build_prompt_contains_required_fields(self):
        """Prompt should contain all required field names"""
        adapter = ConcreteAdapter()

        prompt = adapter._build_extraction_prompt(1)

        # Check for key fields
        assert "contract_number" in prompt
        assert "sign_date" in prompt
        assert "landlord_name" in prompt
        assert "tenant_name" in prompt
        assert "property_address" in prompt
        assert "rent_terms" in prompt

    @pytest.mark.unit
    def test_build_prompt_contains_format_instructions(self):
        """Prompt should contain JSON format instructions"""
        adapter = ConcreteAdapter()

        prompt = adapter._build_extraction_prompt(1)

        assert "JSON格式" in prompt
        assert "只返回JSON" in prompt


# ============================================================================
# BaseVisionAdapter - _merge_multi_page_results() Tests
# ============================================================================


class TestBaseVisionAdapterMergeMultiPageResults:
    """Tests for BaseVisionAdapter._merge_multi_page_results() method"""

    @pytest.mark.unit
    def test_merge_single_result(self):
        """Should return single result as-is"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True, "data": {"contract_number": "CT001"}, "images_count": 1}
        ]

        merged = adapter._merge_multi_page_results(results)

        assert merged == {"contract_number": "CT001"}

    @pytest.mark.unit
    def test_merge_multiple_results_keeps_non_null_values(self):
        """Should merge multiple results, keeping non-null values"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True, "data": {"contract_number": "CT001", "landlord": "Alice"}, "images_count": 1},
            {"success": True, "data": {"tenant": "Bob", "landlord": None}, "images_count": 1},
        ]

        merged = adapter._merge_multi_page_results(results)

        assert merged["contract_number"] == "CT001"
        assert merged["landlord"] == "Alice"  # First non-null value
        assert merged["tenant"] == "Bob"

    @pytest.mark.unit
    def test_merge_prefers_longer_string_values(self):
        """Should prefer longer string values for the same key"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True, "data": {"address": "123 Main St"}, "images_count": 1},
            {
                "success": True,
                "data": {"address": "123 Main Street, Suite 100, New York, NY 10001"},
                "images_count": 1,
            },
        ]

        merged = adapter._merge_multi_page_results(results)

        # Should prefer the longer, more complete address
        assert "Suite 100" in merged["address"]

    @pytest.mark.unit
    def test_merge_handles_empty_results(self):
        """Should handle empty results list"""
        adapter = ConcreteAdapter()

        merged = adapter._merge_multi_page_results([])

        assert merged == {}

    @pytest.mark.unit
    def test_merge_skips_unsuccessful_results(self):
        """Should skip results that are not successful"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True, "data": {"contract_number": "CT001"}, "images_count": 1},
            {"success": False, "error": "Failed to extract"},
            {"success": True, "data": {"tenant": "Bob"}, "images_count": 1},
        ]

        merged = adapter._merge_multi_page_results(results)

        assert merged["contract_number"] == "CT001"
        assert merged["tenant"] == "Bob"

    @pytest.mark.unit
    def test_merge_skips_results_with_no_data(self):
        """Should skip results with no data field"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True, "data": {"contract_number": "CT001"}, "images_count": 1},
            {"success": True},  # No data field
            {"success": True, "data": None},  # Explicit None data
        ]

        merged = adapter._merge_multi_page_results(results)

        assert merged == {"contract_number": "CT001"}

    @pytest.mark.unit
    def test_merge_handles_null_values_in_data(self):
        """Should handle null values within data dict"""
        adapter = ConcreteAdapter()

        results = [
            {
                "success": True,
                "data": {"contract_number": "CT001", "landlord": None, "tenant": "Bob"},
                "images_count": 1,
            },
        ]

        merged = adapter._merge_multi_page_results(results)

        assert merged["contract_number"] == "CT001"
        assert merged["tenant"] == "Bob"
        assert "landlord" not in merged  # None values should not be added

    @pytest.mark.unit
    def test_merge_overwrites_shorter_strings(self):
        """Should overwrite shorter strings with longer ones"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True, "data": {"address": "123 Main St"}, "images_count": 1},
            {
                "success": True,
                "data": {"address": "123 Main Street, Apt 4B"},
                "images_count": 1,
            },
        ]

        merged = adapter._merge_multi_page_results(results)

        assert "Apt 4B" in merged["address"]

    @pytest.mark.unit
    def test_merge_keeps_first_non_string_value(self):
        """Should keep first non-string value (not overwrite)"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True, "data": {"rent": 1000}, "images_count": 1},
            {"success": True, "data": {"rent": 2000}, "images_count": 1},
        ]

        merged = adapter._merge_multi_page_results(results)

        # Non-string values keep the first occurrence
        assert merged["rent"] == 1000

    @pytest.mark.unit
    def test_merge_mixed_string_and_non_string(self):
        """Should handle mixed string and non-string values"""
        adapter = ConcreteAdapter()

        results = [
            {
                "success": True,
                "data": {"rent": 1000, "address": "123 Main St"},
                "images_count": 1,
            },
            {
                "success": True,
                "data": {"rent": 2000, "address": "123 Main Street, Apt 4B"},
                "images_count": 1,
            },
        ]

        merged = adapter._merge_multi_page_results(results)

        # Rent keeps first value (non-string)
        assert merged["rent"] == 1000
        # Address gets longer string
        assert "Apt 4B" in merged["address"]


# ============================================================================
# BaseVisionAdapter - _calculate_confidence() Tests
# ============================================================================


class TestBaseVisionAdapterCalculateConfidence:
    """Tests for BaseVisionAdapter._calculate_confidence() method"""

    @pytest.mark.unit
    def test_confidence_empty_results(self):
        """Should return 0.0 for empty results"""
        adapter = ConcreteAdapter()

        confidence = adapter._calculate_confidence([])

        assert confidence == 0.0

    @pytest.mark.unit
    def test_confidence_all_successful(self):
        """Should return high confidence when all batches succeed"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True},
            {"success": True},
            {"success": True},
        ]

        confidence = adapter._calculate_confidence(results)

        # All 3/3 successful: 0.7 + 0.25 * 1.0 = 0.95 (capped)
        assert confidence == 0.95

    @pytest.mark.unit
    def test_confidence_partial_success(self):
        """Should return moderate confidence for partial success"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True},
            {"success": False},
            {"success": True},
        ]

        confidence = adapter._calculate_confidence(results)

        # 2/3 successful: 0.7 + 0.25 * (2/3) ≈ 0.87
        assert 0.86 < confidence < 0.88

    @pytest.mark.unit
    def test_confidence_none_successful(self):
        """Should return low confidence when no batches succeed"""
        adapter = ConcreteAdapter()

        results = [
            {"success": False},
            {"success": False},
        ]

        confidence = adapter._calculate_confidence(results)

        # 0/2 successful: 0.7 + 0.25 * 0 = 0.7
        assert confidence == 0.7

    @pytest.mark.unit
    def test_confidence_never_exceeds_0_95(self):
        """Confidence should be capped at 0.95"""
        adapter = ConcreteAdapter()

        # Even with many successful results, confidence should not exceed 0.95
        results = [{"success": True} for _ in range(100)]

        confidence = adapter._calculate_confidence(results)

        assert confidence == 0.95

    @pytest.mark.unit
    def test_confidence_single_successful(self):
        """Should calculate correct confidence for single successful batch"""
        adapter = ConcreteAdapter()

        results = [{"success": True}]

        confidence = adapter._calculate_confidence(results)

        # 1/1 successful: 0.7 + 0.25 * 1.0 = 0.95 (capped)
        assert confidence == 0.95

    @pytest.mark.unit
    def test_confidence_half_successful(self):
        """Should calculate correct confidence for half successful batches"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True},
            {"success": False},
        ]

        confidence = adapter._calculate_confidence(results)

        # 1/2 successful: 0.7 + 0.25 * 0.5 = 0.825
        assert 0.82 < confidence < 0.83


# ============================================================================
# BaseVisionAdapter - _aggregate_usage() Tests
# ============================================================================


class TestBaseVisionAdapterAggregateUsage:
    """Tests for BaseVisionAdapter._aggregate_usage() method"""

    @pytest.mark.unit
    def test_aggregate_usage_single_batch(self):
        """Should aggregate single batch usage"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True, "usage": {"total_tokens": 100}, "images_count": 2}
        ]

        aggregated = adapter._aggregate_usage(results)

        assert aggregated["total_tokens"] == 100
        assert aggregated["total_images_processed"] == 2

    @pytest.mark.unit
    def test_aggregate_usage_multiple_batches(self):
        """Should aggregate usage from multiple batches"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True, "usage": {"total_tokens": 100}, "images_count": 2},
            {"success": True, "usage": {"total_tokens": 150}, "images_count": 3},
            {"success": True, "usage": {"total_tokens": 200}, "images_count": 2},
        ]

        aggregated = adapter._aggregate_usage(results)

        assert aggregated["total_tokens"] == 450  # Sum of all tokens
        assert aggregated["total_images_processed"] == 7  # Sum of all images

    @pytest.mark.unit
    def test_aggregate_usage_missing_usage_field(self):
        """Should handle results without usage field"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True, "usage": {"total_tokens": 100}, "images_count": 2},
            {"success": True},  # No usage field
        ]

        aggregated = adapter._aggregate_usage(results)

        assert aggregated["total_tokens"] == 100
        assert aggregated["total_images_processed"] == 2

    @pytest.mark.unit
    def test_aggregate_usage_empty_results(self):
        """Should return zeros for empty results"""
        adapter = ConcreteAdapter()

        aggregated = adapter._aggregate_usage([])

        assert aggregated["total_tokens"] == 0
        assert aggregated["total_images_processed"] == 0

    @pytest.mark.unit
    def test_aggregate_usage_missing_images_count(self):
        """Should handle results without images_count"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True, "usage": {"total_tokens": 100}},  # No images_count
        ]

        aggregated = adapter._aggregate_usage(results)

        assert aggregated["total_tokens"] == 100
        assert aggregated["total_images_processed"] == 0

    @pytest.mark.unit
    def test_aggregate_usage_with_zero_tokens(self):
        """Should handle zero token counts"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True, "usage": {"total_tokens": 0}, "images_count": 1},
        ]

        aggregated = adapter._aggregate_usage(results)

        assert aggregated["total_tokens"] == 0
        assert aggregated["total_images_processed"] == 1

    @pytest.mark.unit
    def test_aggregate_usage_mixed_valid_and_missing(self):
        """Should handle mix of valid and missing usage data"""
        adapter = ConcreteAdapter()

        results = [
            {"success": True, "usage": {"total_tokens": 100}, "images_count": 1},
            {"success": True},  # No usage or images_count
            {"success": True, "usage": {}, "images_count": 0},  # Empty usage
        ]

        aggregated = adapter._aggregate_usage(results)

        assert aggregated["total_tokens"] == 100
        assert aggregated["total_images_processed"] == 1


# ============================================================================
# Integration Tests - Full Workflow
# ============================================================================


class TestBaseVisionAdapterIntegration:
    """Integration tests for full extraction workflow"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="pdf_to_images module not yet implemented")
    async def test_full_extraction_workflow_success(self):
        """Test complete successful extraction workflow"""
        adapter = ConcreteAdapter(is_available=True)

        image_paths = ["page1.png", "page2.png"]

        # Mock vision service responses
        mock_response1 = MagicMock()
        mock_response1.content = '{"contract_number": "CT001", "landlord": "Alice"}'
        mock_response1.usage = {"total_tokens": 100}

        mock_response2 = MagicMock()
        mock_response2.content = '{"tenant": "Bob", "property_address": "123 Main St"}'
        mock_response2.usage = {"total_tokens": 150}

        adapter.vision_service.extract_from_images.side_effect = [
            mock_response1,
            mock_response2,
        ]

        with patch(
            "src.services.document.extractors.base.pdf_to_images", return_value=image_paths
        ):
            result = await adapter.extract("/fake/path.pdf", batch_size=1)

        assert result["success"] is True
        assert result["extracted_fields"]["contract_number"] == "CT001"
        assert result["extracted_fields"]["landlord"] == "Alice"
        assert result["extracted_fields"]["tenant"] == "Bob"
        assert result["pages_processed"] == 2
        assert result["batches_processed"] == 2
        assert result["confidence"] > 0.8
        assert result["usage"]["total_tokens"] == 250
        assert result["usage"]["total_images_processed"] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="pdf_to_images module not yet implemented")
    async def test_full_extraction_workflow_with_retry(self):
        """Test extraction workflow with retry logic"""
        adapter = ConcreteAdapter(is_available=True)

        image_paths = ["page1.png"]

        # First call fails with retryable error, second succeeds
        mock_response = MagicMock()
        mock_response.content = '{"contract_number": "CT001"}'
        mock_response.usage = {"total_tokens": 100}

        adapter.vision_service.extract_from_images.side_effect = [
            ConnectionError("Network error"),
            mock_response,
        ]

        with patch(
            "src.services.document.extractors.base.pdf_to_images", return_value=image_paths
        ):
            result = await adapter.extract("/fake/path.pdf")

        assert result["success"] is True
        assert result["extracted_fields"]["contract_number"] == "CT001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
