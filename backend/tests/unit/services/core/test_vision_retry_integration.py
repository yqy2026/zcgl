#!/usr/bin/env python3
"""
测试 VisionAPIError 的重试逻辑集成
验证 retryable 标志是否正确影响重试行为
"""

from unittest.mock import Mock

import httpx
import pytest

from src.services.core.base_vision_service import (
    VisionAPIError,
    handle_http_status_error,
    handle_network_error,
)


class TestVisionRetryIntegration:
    """测试视觉 API 错误的重试集成"""

    @pytest.mark.asyncio
    async def test_retryable_error_triggers_retry(self):
        """测试 retryable=True 的错误会触发重试"""

        # 创建一个会失败两次然后成功的模拟函数
        call_count = 0

        async def flaky_api_call():
            nonlocal call_count
            call_count += 1

            if call_count < 3:
                # 前两次调用抛出可重试错误（HTTP 429 - 速率限制）
                raise VisionAPIError(
                    message="Rate limit exceeded", status_code=429, retryable=True
                )

            # 第三次调用成功
            return {"success": True, "data": "extracted_content"}

        # 使用简单的重试逻辑
        max_attempts = 3
        result = None

        for attempt in range(max_attempts):
            try:
                result = await flaky_api_call()
                break
            except VisionAPIError as e:
                if not e.retryable or attempt == max_attempts - 1:
                    raise
                # 可重试错误，继续下一次尝试
                continue

        # 验证重试了 3 次并最终成功
        assert call_count == 3
        assert result is not None
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_non_retryable_error_fails_immediately(self):
        """测试 retryable=False 的错误立即失败，不重试"""

        call_count = 0

        async def failing_api_call():
            nonlocal call_count
            call_count += 1

            # 抛出不可重试错误（HTTP 401 - 认证失败）
            raise VisionAPIError(
                message="Authentication failed - Invalid API key",
                status_code=401,
                retryable=False,
            )

        max_attempts = 3

        with pytest.raises(VisionAPIError) as exc_info:
            for attempt in range(max_attempts):
                try:
                    await failing_api_call()
                    break
                except VisionAPIError as e:
                    if not e.retryable or attempt == max_attempts - 1:
                        raise
                    continue

        # 验证只调用了一次（没有重试）
        assert call_count == 1
        assert exc_info.value.retryable is False
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_handle_http_status_error_sets_retryable_correctly(self):
        """测试 handle_http_status_error 正确设置 retryable 标志"""

        # 测试 HTTP 429（速率限制）- 应该可重试
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Too many requests"}

        http_error_429 = httpx.HTTPStatusError(
            "Rate limit", request=Mock(), response=mock_response
        )

        error_429 = handle_http_status_error(http_error_429)
        assert error_429.retryable is True
        assert error_429.status_code == 429

        # 测试 HTTP 500（服务器错误）- 应该可重试
        mock_response_500 = Mock()
        mock_response_500.status_code = 500
        mock_response_500.json.side_effect = Exception("No JSON")

        http_error_500 = httpx.HTTPStatusError(
            "Server error", request=Mock(), response=mock_response_500
        )

        error_500 = handle_http_status_error(http_error_500)
        assert error_500.retryable is True
        assert error_500.status_code == 500

        # 测试 HTTP 401（认证失败）- 不应该重试
        mock_response_401 = Mock()
        mock_response_401.status_code = 401
        mock_response_401.json.return_value = {"error": "Invalid API key"}

        http_error_401 = httpx.HTTPStatusError(
            "Auth failed", request=Mock(), response=mock_response_401
        )

        error_401 = handle_http_status_error(http_error_401)
        assert error_401.retryable is False
        assert error_401.status_code == 401

    @pytest.mark.asyncio
    async def test_retry_exhaustion_with_retryable_errors(self):
        """测试重试耗尽时的行为（所有尝试都失败）"""

        call_count = 0

        async def always_failing_api_call():
            nonlocal call_count
            call_count += 1

            # 总是抛出可重试错误
            raise VisionAPIError(
                message="Service temporarily unavailable",
                status_code=503,
                retryable=True,
            )

        max_attempts = 3

        with pytest.raises(VisionAPIError) as exc_info:
            for attempt in range(max_attempts):
                try:
                    await always_failing_api_call()
                    break
                except VisionAPIError as e:
                    if not e.retryable or attempt == max_attempts - 1:
                        raise
                    continue

        # 验证重试了最大次数
        assert call_count == 3
        # 最后抛出的错误仍然是可重试的（只是耗尽了重试）
        assert exc_info.value.retryable is True
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_mixed_error_types_retry_logic(self):
        """测试混合错误类型的重试逻辑"""

        call_count = 0

        async def mixed_errors_api_call():
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # 第一次：可重试错误
                raise VisionAPIError(message="Timeout", status_code=504, retryable=True)
            elif call_count == 2:
                # 第二次：不可重试错误（应该立即失败）
                raise VisionAPIError(
                    message="Bad request", status_code=400, retryable=False
                )
            else:
                # 不应该到达这里
                return {"success": True}

        max_attempts = 5

        with pytest.raises(VisionAPIError) as exc_info:
            for attempt in range(max_attempts):
                try:
                    await mixed_errors_api_call()
                    break
                except VisionAPIError as e:
                    if not e.retryable or attempt == max_attempts - 1:
                        raise
                    continue

        # 验证只调用了 2 次（第一次重试，第二次不可重试）
        assert call_count == 2
        assert exc_info.value.retryable is False
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_network_errors_are_retryable(self):
        """测试网络错误被正确标记为可重试"""

        # 测试连接错误
        connect_error = httpx.ConnectError("Connection refused")
        vision_error = handle_network_error(connect_error)
        assert vision_error.retryable is True

        # 测试超时错误
        timeout_error = httpx.ReadTimeout("Read timeout")
        vision_error_timeout = handle_network_error(timeout_error)
        assert vision_error_timeout.retryable is True

        # 测试协议错误（可能不稳定，值得重试）
        protocol_error = httpx.RemoteProtocolError("Protocol error")
        vision_error_protocol = handle_network_error(protocol_error)
        assert vision_error_protocol.retryable is True
