#!/usr/bin/env python3
"""
NVIDIA Cloud OCR Service Unit Tests
"""

from unittest.mock import patch

import pytest


class TestNvidiaCloudOCRService:
    """Tests for NvidiaCloudOCRService"""

    def test_service_initialization_default(self):
        """Test service initialization with default config from environment"""
        from src.services.document.nvidia_cloud_ocr_service import (
            NvidiaCloudOCRService,
        )

        with patch.dict("os.environ", {"NVIDIA_API_KEY": ""}, clear=False):
            service = NvidiaCloudOCRService()
            assert service.config is not None
            assert (
                service.config.base_url
                == "https://ai.api.nvidia.com/v1/cv/baidu/paddleocr"
            )

    def test_service_initialization_with_config(self):
        """Test service initialization with custom config"""
        from src.services.document.nvidia_cloud_ocr_service import (
            NvidiaCloudOCRService,
            NvidiaOCRConfig,
        )

        config = NvidiaOCRConfig(
            api_key="test-api-key",
            base_url="https://custom-url.com/v1/ocr",
            timeout=30,
        )

        service = NvidiaCloudOCRService(config=config)

        assert service.config.api_key == "test-api-key"
        assert service.config.base_url == "https://custom-url.com/v1/ocr"
        assert service.config.timeout == 30

    def test_is_available_without_api_key(self):
        """Test is_available returns False without API key"""
        from src.services.document.nvidia_cloud_ocr_service import (
            NvidiaCloudOCRService,
            NvidiaOCRConfig,
        )

        config = NvidiaOCRConfig(api_key="", base_url="https://test.com")
        service = NvidiaCloudOCRService(config=config)

        assert service.is_available() is False

    def test_is_available_with_api_key(self):
        """Test is_available returns True with API key"""
        from src.services.document.nvidia_cloud_ocr_service import (
            NvidiaCloudOCRService,
            NvidiaOCRConfig,
        )

        config = NvidiaOCRConfig(api_key="nvapi-test-key", base_url="https://test.com")
        service = NvidiaCloudOCRService(config=config)

        assert service.is_available() is True

    def test_encode_image_to_base64(self):
        """Test image encoding to base64 data URL"""
        from src.services.document.nvidia_cloud_ocr_service import (
            NvidiaCloudOCRService,
            NvidiaOCRConfig,
        )

        config = NvidiaOCRConfig(api_key="test", base_url="https://test.com")
        service = NvidiaCloudOCRService(config=config)

        # Simple test image bytes
        test_bytes = b"\x89PNG\r\n\x1a\n"

        result = service._encode_image_to_base64(test_bytes, "png")

        assert result.startswith("data:image/png;base64,")
        assert "iVBORw0KGgo" in result  # PNG header in base64

    def test_parse_response_success(self):
        """Test parsing successful API response"""
        from src.services.document.nvidia_cloud_ocr_service import (
            NvidiaCloudOCRService,
            NvidiaOCRConfig,
        )

        config = NvidiaOCRConfig(api_key="test", base_url="https://test.com")
        service = NvidiaCloudOCRService(config=config)

        mock_response = {
            "data": [
                {
                    "text_detections": [
                        {
                            "text_prediction": {
                                "text": "合同编号: HT-2025-001",
                                "confidence": 0.95,
                            },
                            "bounding_box": {
                                "points": [
                                    {"x": 0.1, "y": 0.1},
                                    {"x": 0.5, "y": 0.1},
                                    {"x": 0.5, "y": 0.2},
                                    {"x": 0.1, "y": 0.2},
                                ]
                            },
                        },
                        {
                            "text_prediction": {
                                "text": "月租金为12000元",
                                "confidence": 0.92,
                            },
                            "bounding_box": {
                                "points": [
                                    {"x": 0.1, "y": 0.3},
                                    {"x": 0.6, "y": 0.3},
                                    {"x": 0.6, "y": 0.4},
                                    {"x": 0.1, "y": 0.4},
                                ]
                            },
                        },
                    ]
                }
            ]
        }

        result = service._parse_response(mock_response, 100.0)

        assert result.success is True
        assert len(result.text_detections) == 2
        assert "合同编号" in result.full_text
        assert "月租金" in result.full_text
        assert result.confidence_score > 0.9
        assert result.processing_time_ms == 100.0

    def test_parse_response_empty(self):
        """Test parsing empty API response"""
        from src.services.document.nvidia_cloud_ocr_service import (
            NvidiaCloudOCRService,
            NvidiaOCRConfig,
        )

        config = NvidiaOCRConfig(api_key="test", base_url="https://test.com")
        service = NvidiaCloudOCRService(config=config)

        mock_response = {"data": []}

        result = service._parse_response(mock_response, 50.0)

        assert result.success is True
        assert len(result.text_detections) == 0
        assert result.full_text == ""
        assert result.confidence_score == 0.0


class TestOCRDataClasses:
    """Tests for OCR data classes"""

    def test_nvidia_ocr_config_defaults(self):
        """Test NvidiaOCRConfig default values"""
        from src.services.document.nvidia_cloud_ocr_service import NvidiaOCRConfig

        config = NvidiaOCRConfig(api_key="test-key")

        assert config.api_key == "test-key"
        assert config.base_url == "https://ai.api.nvidia.com/v1/cv/baidu/paddleocr"
        assert config.timeout == 60
        assert config.max_retries == 3

    def test_text_detection_dataclass(self):
        """Test TextDetection dataclass"""
        from src.services.document.nvidia_cloud_ocr_service import TextDetection

        detection = TextDetection(
            text="测试文本",
            confidence=0.95,
            bounding_box=[{"x": 0.1, "y": 0.1}],
        )

        assert detection.text == "测试文本"
        assert detection.confidence == 0.95
        assert len(detection.bounding_box) == 1

    def test_ocr_result_dataclass(self):
        """Test OCRResult dataclass"""
        from src.services.document.nvidia_cloud_ocr_service import OCRResult

        result = OCRResult(
            success=True,
            full_text="测试内容",
            confidence_score=0.9,
        )

        assert result.success is True
        assert result.full_text == "测试内容"
        assert result.confidence_score == 0.9
        assert result.error is None


class TestAsyncMethods:
    """Tests for async methods"""

    @pytest.mark.asyncio
    async def test_process_image_without_api_key(self):
        """Test process_image returns error without API key"""
        from src.services.document.nvidia_cloud_ocr_service import (
            NvidiaCloudOCRService,
            NvidiaOCRConfig,
        )

        config = NvidiaOCRConfig(api_key="", base_url="https://test.com")
        service = NvidiaCloudOCRService(config=config)

        result = await service.process_image(b"test_image_bytes")

        assert result.success is False
        assert "NVIDIA_API_KEY" in result.error

    @pytest.mark.asyncio
    async def test_process_pdf_file_not_found(self):
        """Test process_pdf returns error for missing file"""
        from src.services.document.nvidia_cloud_ocr_service import (
            NvidiaCloudOCRService,
            NvidiaOCRConfig,
        )

        config = NvidiaOCRConfig(api_key="test-key", base_url="https://test.com")
        service = NvidiaCloudOCRService(config=config)

        result = await service.process_pdf("/nonexistent/path/to/file.pdf")

        assert result["success"] is False
        assert "not found" in result["error"] or "不存在" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test closing the HTTP client"""
        from src.services.document.nvidia_cloud_ocr_service import (
            NvidiaCloudOCRService,
            NvidiaOCRConfig,
        )

        config = NvidiaOCRConfig(api_key="test-key", base_url="https://test.com")
        service = NvidiaCloudOCRService(config=config)

        # Close should not raise even if client is not initialized
        await service.close()

        # Verify state
        assert service._client is None


class TestSingletonPattern:
    """Tests for singleton pattern"""

    def test_get_nvidia_ocr_service_returns_same_instance(self):
        """Test that get_nvidia_ocr_service returns singleton"""
        # Reset singleton for clean test
        import src.services.document.nvidia_cloud_ocr_service as module
        from src.services.document.nvidia_cloud_ocr_service import (
            get_nvidia_ocr_service,
        )

        module._nvidia_ocr_service = None

        with patch.dict("os.environ", {"NVIDIA_API_KEY": "test-key"}, clear=False):
            service1 = get_nvidia_ocr_service()
            service2 = get_nvidia_ocr_service()

            assert service1 is service2


class TestConfigIntegration:
    """Tests for config integration"""

    def test_config_settings_nvidia_fields(self):
        """Test that Settings class has NVIDIA OCR fields"""
        from src.core.config import Settings

        settings = Settings()

        assert hasattr(settings, "NVIDIA_API_KEY")
        assert hasattr(settings, "NVIDIA_OCR_BASE_URL")
        assert hasattr(settings, "NVIDIA_OCR_TIMEOUT")
        assert hasattr(settings, "OCR_PROVIDER")

        # Check defaults
        assert (
            settings.NVIDIA_OCR_BASE_URL
            == "https://ai.api.nvidia.com/v1/cv/baidu/paddleocr"
        )
        assert settings.NVIDIA_OCR_TIMEOUT == 60
        assert settings.OCR_PROVIDER == "auto"
