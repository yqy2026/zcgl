#!/usr/bin/env python3
"""
重试机制单元测试
测试 retry.py 中的装饰器和函数
"""

from unittest.mock import Mock

import httpx
import pytest

from src.services.document.retry import (
    RetryContext,
    retry_async_call,
    retry_on_api_error,
    retry_on_network_error,
    retry_on_vision_api,
)

# ============================================================================
# retry_on_network_error 装饰器测试
# ============================================================================

class TestRetryOnNetworkError:
    """网络错误重试装饰器测试"""

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """测试成功调用无需重试"""
        call_count = 0

        @retry_on_network_error(max_attempts=3)
        async def mock_api_call():
            nonlocal call_count
            call_count += 1
            return {"success": True}

        result = await mock_api_call()
        assert call_count == 1
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_timeout_error_retry_success(self):
        """测试超时错误重试后成功"""
        call_count = 0

        @retry_on_network_error(max_attempts=3, wait_min=0.01, wait_max=0.1)
        async def mock_api_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Request timeout")
            return {"success": True}

        result = await mock_api_call()
        assert call_count == 2  # 失败1次，成功1次
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_network_error_retry_success(self):
        """测试网络错误重试后成功"""
        call_count = 0

        @retry_on_network_error(max_attempts=3, wait_min=0.01, wait_max=0.1)
        async def mock_api_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.NetworkError("Connection failed")
            return {"success": True}

        result = await mock_api_call()
        assert call_count == 2
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        call_count = 0

        @retry_on_network_error(max_attempts=3, wait_min=0.01, wait_max=0.1)
        async def mock_api_call():
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Request timeout")

        with pytest.raises(httpx.TimeoutException):
            await mock_api_call()

        assert call_count == 3  # 尝试3次

    @pytest.mark.asyncio
    async def test_non_retryable_error(self):
        """测试不可重试的错误立即抛出"""
        call_count = 0

        @retry_on_network_error(max_attempts=3)
        async def mock_api_call():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")

        with pytest.raises(ValueError):
            await mock_api_call()

        assert call_count == 1  # 没有重试


# ============================================================================
# retry_on_api_error 装饰器测试
# ============================================================================

class TestRetryOnAPIError:
    """API 错误重试装饰器测试"""

    @pytest.mark.asyncio
    async def test_retry_on_500_error(self):
        """测试重试 500 服务器错误"""
        call_count = 0

        @retry_on_api_error(max_attempts=3, wait_min=0.01, wait_max=0.1)
        async def mock_api_call():
            nonlocal call_count
            call_count += 1

            if call_count < 2:
                response = Mock()
                response.status_code = 500
                raise httpx.HTTPStatusError(
                    "Internal Server Error",
                    request=Mock(),
                    response=response
                )

            return {"success": True}

        result = await mock_api_call()
        assert call_count == 2
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_retry_on_429_rate_limit(self):
        """测试重试 429 限流错误"""
        call_count = 0

        @retry_on_api_error(max_attempts=3, wait_min=0.01, wait_max=0.1)
        async def mock_api_call():
            nonlocal call_count
            call_count += 1

            if call_count < 2:
                response = Mock()
                response.status_code = 429
                raise httpx.HTTPStatusError(
                    "Too Many Requests",
                    request=Mock(),
                    response=response
                )

            return {"success": True}

        result = await mock_api_call()
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_404_error(self):
        """测试 404 错误不重试"""
        call_count = 0

        @retry_on_api_error(max_attempts=3, wait_min=0.01, wait_max=0.1)
        async def mock_api_call():
            nonlocal call_count
            call_count += 1

            response = Mock()
            response.status_code = 404
            raise httpx.HTTPStatusError(
                "Not Found",
                request=Mock(),
                response=response
            )

        with pytest.raises(httpx.HTTPStatusError):
            await mock_api_call()

        assert call_count == 1  # 404 不重试


# ============================================================================
# retry_on_vision_api 装饰器测试
# ============================================================================

class TestRetryOnVisionAPI:
    """视觉 API 重试装饰器测试"""

    @pytest.mark.asyncio
    async def test_vision_api_retry_on_timeout(self):
        """测试视觉 API 超时重试"""
        call_count = 0

        @retry_on_vision_api(max_attempts=3, timeout=180.0)
        async def mock_vision_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Vision API timeout")
            return {"success": True}

        result = await mock_vision_call()
        assert call_count == 2
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_vision_api_retry_on_network_error(self):
        """测试视觉 API 网络错误重试"""
        call_count = 0

        @retry_on_vision_api(max_attempts=3)
        async def mock_vision_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.RemoteProtocolError("Connection reset")
            return {"success": True}

        result = await mock_vision_call()
        assert call_count == 2


# ============================================================================
# retry_async_call 函数测试
# ============================================================================

class TestRetryAsyncCall:
    """retry_async_call 函数测试"""

    @pytest.mark.asyncio
    async def test_successful_call(self):
        """测试成功调用"""
        async def mock_func(x, y):
            return x + y

        result = await retry_async_call(mock_func, 2, 3, max_attempts=3)
        assert result == 5

    @pytest.mark.asyncio
    async def test_retry_on_exception(self):
        """测试异常重试"""
        call_count = 0

        async def mock_func(x):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Timeout")
            return x * 2

        result = await retry_async_call(mock_func, 5, max_attempts=3, wait_min=0.01)
        assert result == 10
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """测试超过最大尝试次数"""
        async def mock_func():
            raise httpx.NetworkError("Network error")

        with pytest.raises(httpx.NetworkError):
            await retry_async_call(mock_func, max_attempts=3, wait_min=0.01)

    @pytest.mark.asyncio
    async def test_retry_on_http_status_error(self):
        """测试 HTTP 状态错误重试"""
        call_count = 0

        async def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                response = Mock()
                response.status_code = 503
                raise httpx.HTTPStatusError(
                    "Service Unavailable",
                    request=Mock(),
                    response=response
                )
            return {"success": True}

        result = await retry_async_call(mock_func, max_attempts=3, wait_min=0.01)
        assert result["success"] is True
        assert call_count == 2


# ============================================================================
# RetryContext 测试
# ============================================================================

class TestRetryContext:
    """RetryContext 上下文管理器测试"""

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """测试成功执行"""
        attempt_count = 0

        async with RetryContext(max_attempts=3) as retry:
            while retry.should_continue():
                attempt_count += 1
                try:
                    result = "success"
                    retry.success()
                    break
                except Exception:
                    await retry.record_error(Exception("Test"))

        assert attempt_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_error(self):
        """测试错误重试"""
        attempt_count = 0

        async with RetryContext(
            max_attempts=3,
            wait_min=0.01,
            wait_max=0.1,
            retry_on=(httpx.TimeoutException,)
        ) as retry:
            while retry.should_continue():
                attempt_count += 1
                try:
                    if attempt_count < 2:
                        raise httpx.TimeoutException("Timeout")
                    result = "success"
                    retry.success()
                    break
                except Exception as e:
                    await retry.record_error(e)

        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """测试超过最大尝试次数"""
        attempt_count = 0

        with pytest.raises(httpx.TimeoutException):
            async with RetryContext(
                max_attempts=3,
                wait_min=0.01,
                retry_on=(httpx.TimeoutException,)
            ) as retry:
                while retry.should_continue():
                    attempt_count += 1
                    try:
                        raise httpx.TimeoutException("Timeout")
                    except Exception as e:
                        await retry.record_error(e)

        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_error(self):
        """测试不可重试错误立即抛出"""
        attempt_count = 0

        with pytest.raises(ValueError):
            async with RetryContext(
                max_attempts=3,
                retry_on=(httpx.TimeoutException,)
            ) as retry:
                while retry.should_continue():
                    attempt_count += 1
                    try:
                        raise ValueError("Non-retryable")
                    except Exception as e:
                        await retry.record_error(e)

        assert attempt_count == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """测试指数退避"""
        import time

        attempt_times = []

        async with RetryContext(
            max_attempts=3,
            wait_min=0.05,
            wait_max=1.0,
            retry_on=(httpx.TimeoutException,)
        ) as retry:
            while retry.should_continue():
                start = time.time()
                attempt_times.append(start)
                try:
                    if len(attempt_times) < 3:
                        raise httpx.TimeoutException("Timeout")
                    retry.success()
                    break
                except Exception as e:
                    await retry.record_error(e)

        assert len(attempt_times) == 3

        # 验证等待时间指数增长
        wait1 = attempt_times[1] - attempt_times[0]
        wait2 = attempt_times[2] - attempt_times[1]
        assert wait2 > wait1  # 第二次等待时间应更长


# ============================================================================
# 集成测试示例
# ============================================================================

class TestRetryIntegration:
    """重试机制集成测试"""

    @pytest.mark.asyncio
    async def test_full_api_call_workflow(self):
        """测试完整的 API 调用工作流"""
        call_log = []

        @retry_on_api_error(max_attempts=3, wait_min=0.01, wait_max=0.1)
        async def fetch_data():
            call_log.append("attempt")
            # 模拟间歇性失败
            if len(call_log) == 1:
                response = Mock()
                response.status_code = 503
                raise httpx.HTTPStatusError(
                    "Service Unavailable",
                    request=Mock(),
                    response=response
                )
            return {"data": "success"}

        result = await fetch_data()
        assert result["data"] == "success"
        assert len(call_log) == 2

    @pytest.mark.asyncio
    async def test_nested_retry_decorators(self):
        """测试嵌套重试装饰器"""
        call_count = 0

        @retry_on_network_error(max_attempts=2, wait_min=0.01)
        @retry_on_api_error(max_attempts=2, wait_min=0.01)
        async def complex_api_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Timeout")
            return {"success": True}

        result = await complex_api_call()
        assert result["success"] is True
        assert call_count == 2
