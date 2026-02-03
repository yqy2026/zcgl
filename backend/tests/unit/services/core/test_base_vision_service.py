"""
Vision 服务基类和工具函数测试

测试 base_vision_service.py 中的异常类、基类和工具函数
"""

from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest


class TestVisionAPIError:
    """VisionAPIError 异常类测试"""

    def test_basic_initialization(self):
        """测试基本初始化"""
        from src.services.core.base_vision_service import VisionAPIError

        error = VisionAPIError("Test error")
        assert str(error) == "Test error"
        assert error.status_code is None
        assert error.retryable is False
        assert error.details == {}

    def test_with_status_code(self):
        """测试带状态码的初始化"""
        from src.services.core.base_vision_service import VisionAPIError

        error = VisionAPIError("Test error", status_code=500)
        assert "[HTTP 500]" in str(error)
        assert error.status_code == 500

    def test_with_retryable(self):
        """测试可重试标志"""
        from src.services.core.base_vision_service import VisionAPIError

        error = VisionAPIError("Test error", retryable=True)
        assert "(retryable)" in str(error)
        assert error.retryable is True

    def test_with_details(self):
        """测试额外详情"""
        from src.services.core.base_vision_service import VisionAPIError

        details = {"key": "value"}
        error = VisionAPIError("Test error", details=details)
        assert error.details == details

    def test_to_dict(self):
        """测试转换为字典"""
        from src.services.core.base_vision_service import VisionAPIError

        error = VisionAPIError("Test error", status_code=429, retryable=True)
        result = error.to_dict()

        assert "error" in result
        assert result["error_code"] == "HTTP_429"
        assert result["retryable"] is True
        assert "suggested_action" in result

    def test_to_dict_without_status_code(self):
        """测试无状态码时的字典转换"""
        from src.services.core.base_vision_service import VisionAPIError

        error = VisionAPIError("Test error")
        result = error.to_dict()

        assert result["error_code"] == "API_ERROR"


class TestBaseVisionService:
    """BaseVisionService 基类测试"""

    def test_mime_map_exists(self):
        """测试 MIME 映射表存在"""
        from src.services.core.base_vision_service import BaseVisionService

        assert hasattr(BaseVisionService, "MIME_MAP")
        assert ".png" in BaseVisionService.MIME_MAP
        assert ".jpg" in BaseVisionService.MIME_MAP
        assert ".jpeg" in BaseVisionService.MIME_MAP

    def test_mime_map_values(self):
        """测试 MIME 类型值正确"""
        from src.services.core.base_vision_service import BaseVisionService

        assert BaseVisionService.MIME_MAP[".png"] == "image/png"
        assert BaseVisionService.MIME_MAP[".jpg"] == "image/jpeg"
        assert BaseVisionService.MIME_MAP[".jpeg"] == "image/jpeg"
        assert BaseVisionService.MIME_MAP[".gif"] == "image/gif"
        assert BaseVisionService.MIME_MAP[".webp"] == "image/webp"


class TestHandleHttpStatusError:
    """handle_http_status_error 函数测试"""

    def test_retryable_status_codes(self):
        """测试可重试的状态码"""
        from src.services.core.base_vision_service import handle_http_status_error

        retryable_codes = [408, 429, 500, 502, 503, 504]

        for code in retryable_codes:
            mock_response = MagicMock()
            mock_response.status_code = code
            mock_response.json.return_value = {}

            mock_error = httpx.HTTPStatusError(
                "Error", request=MagicMock(), response=mock_response
            )

            result = handle_http_status_error(mock_error)
            assert result.retryable is True, f"Status {code} should be retryable"

    def test_non_retryable_status_codes(self):
        """测试不可重试的状态码"""
        from src.services.core.base_vision_service import handle_http_status_error

        non_retryable_codes = [400, 401, 403, 404]

        for code in non_retryable_codes:
            mock_response = MagicMock()
            mock_response.status_code = code
            mock_response.json.return_value = {}

            mock_error = httpx.HTTPStatusError(
                "Error", request=MagicMock(), response=mock_response
            )

            result = handle_http_status_error(mock_error)
            assert result.retryable is False, f"Status {code} should not be retryable"

    def test_status_code_preserved(self):
        """测试状态码被保留"""
        from src.services.core.base_vision_service import handle_http_status_error

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {}

        mock_error = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=mock_response
        )

        result = handle_http_status_error(mock_error)
        assert result.status_code == 401


class TestHandleNetworkError:
    """handle_network_error 函数测试"""

    def test_connect_error(self):
        """测试连接错误"""
        from src.services.core.base_vision_service import handle_network_error

        error = httpx.ConnectError("Connection failed")
        result = handle_network_error(error)

        assert result.retryable is True
        assert "Connection" in str(result)

    def test_timeout_error(self):
        """测试超时错误"""
        from src.services.core.base_vision_service import handle_network_error

        error = TimeoutError("Request timed out")
        result = handle_network_error(error)

        assert result.retryable is True
        assert "timeout" in str(result).lower()

    def test_generic_network_error(self):
        """测试通用网络错误"""
        from src.services.core.base_vision_service import handle_network_error

        error = ConnectionError("Network problem")
        result = handle_network_error(error)

        assert result.retryable is True


class TestValidateImagePath:
    """validate_image_path 函数测试"""

    def test_nonexistent_file(self, tmp_path):
        """测试不存在的文件"""
        from src.core.exception_handler import ResourceNotFoundError
        from src.services.core.base_vision_service import validate_image_path

        with pytest.raises(ResourceNotFoundError):
            validate_image_path(str(tmp_path / "nonexistent.png"))

    def test_directory_path(self, tmp_path):
        """测试目录路径"""
        from src.core.exception_handler import BusinessValidationError
        from src.services.core.base_vision_service import validate_image_path

        with pytest.raises(BusinessValidationError):
            validate_image_path(str(tmp_path))

    def test_valid_image_path(self, tmp_path):
        """测试有效的图像路径"""
        from src.services.core.base_vision_service import validate_image_path

        image_file = tmp_path / "test.png"
        image_file.write_bytes(b"fake image data")

        result = validate_image_path(str(image_file))
        assert isinstance(result, Path)
        assert result.exists()


class TestValidateImagePaths:
    """validate_image_paths 函数测试"""

    def test_empty_list(self):
        """测试空列表"""
        from src.core.exception_handler import BusinessValidationError
        from src.services.core.base_vision_service import validate_image_paths

        with pytest.raises(BusinessValidationError) as exc_info:
            validate_image_paths([])
        assert "cannot be empty" in str(exc_info.value)

    def test_valid_paths(self, tmp_path):
        """测试有效的路径列表"""
        from src.services.core.base_vision_service import validate_image_paths

        image1 = tmp_path / "test1.png"
        image2 = tmp_path / "test2.jpg"
        image1.write_bytes(b"fake image 1")
        image2.write_bytes(b"fake image 2")

        result = validate_image_paths([str(image1), str(image2)])
        assert len(result) == 2
        assert all(isinstance(p, Path) for p in result)

    def test_mixed_valid_invalid(self, tmp_path):
        """测试混合有效和无效路径"""
        from src.core.exception_handler import ResourceNotFoundError
        from src.services.core.base_vision_service import validate_image_paths

        valid_image = tmp_path / "valid.png"
        valid_image.write_bytes(b"fake image")

        with pytest.raises(ResourceNotFoundError):
            validate_image_paths([str(valid_image), str(tmp_path / "invalid.png")])
