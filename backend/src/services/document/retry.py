#!/usr/bin/env python3
"""
重试机制模块
为 PDF 处理相关的 API 调用提供智能重试功能
"""

import asyncio
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import httpx

# 尝试导入 tenacity，如果不可用则使用简单的重试逻辑
try:
    from tenacity import (
        before_sleep_log,
        retry,
        retry_if,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )

    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    logging.warning(
        "tenacity 库未安装，将使用简化版重试机制。建议安装: uv sync --extra pdf-ocr"
    )


logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# 使用 tenacity 的装饰器（推荐）
# ============================================================================

if TENACITY_AVAILABLE:

    def retry_on_network_error(  # type: ignore[misc]
        max_attempts: int = 3,
        wait_min: float = 1.0,
        wait_max: float = 10.0,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        网络错误重试装饰器

        Args:
            max_attempts: 最大重试次数
            wait_min: 最小等待时间（秒）
            wait_max: 最大等待时间（秒）

        Example:
            @retry_on_network_error(max_attempts=3)  # type: ignore[misc]  # type: ignore[misc]
            async def call_api():
                return await httpx.AsyncClient().get(url)
        """
        return retry(  # type: ignore[return-value]
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
            retry=retry_if_exception_type(
                (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

    def retry_on_api_error(  # type: ignore[misc]
        max_attempts: int = 3,
        wait_min: float = 2.0,
        wait_max: float = 30.0,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        API 错误重试装饰器
        重试 HTTP 5xx 错误和 429 限流错误

        Args:
            max_attempts: 最大重试次数
            wait_min: 最小等待时间（秒）
            wait_max: 最大等待时间（秒）

        Example:
            @retry_on_api_error(max_attempts=3)  # type: ignore[misc]  # type: ignore[misc]
            async def call_llm_api():
                return await client.chat.completions.create(...)
        """

        def is_retryable_error(exception: Exception) -> bool:
            """判断是否为可重试的 API 错误"""
            if isinstance(exception, httpx.HTTPStatusError):
                # 重试 5xx 服务器错误和 429 限流
                return (
                    exception.response.status_code >= 500
                    or exception.response.status_code == 429
                )
            return False

        return retry(  # type: ignore[return-value]
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
            retry=retry_if_exception_type(
                (httpx.HTTPStatusError, httpx.TimeoutException, httpx.NetworkError)
            )
            & retry_if(is_retryable_error),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

    def retry_on_vision_api(  # type: ignore[misc]
        max_attempts: int = 3,
        timeout: float = 180.0,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        视觉 API 专用重试装饰器
        针对视觉模型的特殊重试策略

        Args:
            max_attempts: 最大重试次数
            timeout: 超时时间（秒）

        Example:
            @retry_on_vision_api(max_attempts=3)  # type: ignore[misc]  # type: ignore[misc]
            async def extract_from_images(images):
                return await vision_service.extract(images)
        """
        return retry(  # type: ignore[return-value]
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            retry=retry_if_exception_type(
                (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )


# ============================================================================
# 简化版重试（当 tenacity 不可用时）
# ============================================================================

else:

    def retry_on_network_error(
        max_attempts: int = 3,
        wait_min: float = 1.0,
        wait_max: float = 10.0,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """简化版网络错误重试装饰器"""

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                last_exception: Exception | None = None
                wait_time = wait_min

                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)  # type: ignore[misc]
                    except (
                        httpx.TimeoutException,
                        httpx.NetworkError,
                        httpx.RemoteProtocolError,
                    ) as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"Network error (attempt {attempt + 1}/{max_attempts}): {e}. "
                                f"Retrying in {wait_time:.1f}s..."
                            )
                            await asyncio.sleep(wait_time)
                            wait_time = min(wait_time * 2, wait_max)
                        else:
                            logger.error(f"Max retries ({max_attempts}) reached")

                if last_exception is None:
                    raise RuntimeError("Unexpected error in retry logic")
                raise last_exception

            return wrapper  # type: ignore[return-value]

        return decorator

    def retry_on_api_error(
        max_attempts: int = 3,
        wait_min: float = 2.0,
        wait_max: float = 30.0,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """简化版 API 错误重试装饰器"""

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                last_exception: Exception | None = None
                wait_time = wait_min

                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)  # type: ignore[misc]
                    except httpx.HTTPStatusError as e:
                        is_retryable = (
                            e.response.status_code >= 500
                            or e.response.status_code == 429
                        )
                        if is_retryable and attempt < max_attempts - 1:
                            logger.warning(
                                f"API error {e.response.status_code} "
                                f"(attempt {attempt + 1}/{max_attempts}). "
                                f"Retrying in {wait_time:.1f}s..."
                            )
                            await asyncio.sleep(wait_time)
                            wait_time = min(wait_time * 2, wait_max)
                            continue
                        last_exception = e
                    except (
                        httpx.TimeoutException,
                        httpx.NetworkError,
                        httpx.RemoteProtocolError,
                    ) as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"Network error (attempt {attempt + 1}/{max_attempts}): {e}. "
                                f"Retrying in {wait_time:.1f}s..."
                            )
                            await asyncio.sleep(wait_time)
                            wait_time = min(wait_time * 2, wait_max)
                        else:
                            logger.error(f"Max retries ({max_attempts}) reached")
                        continue

                    break

                if last_exception is None:
                    raise RuntimeError("Unexpected error in retry logic")
                raise last_exception

            return wrapper  # type: ignore[return-value]

        return decorator

    def retry_on_vision_api(
        max_attempts: int = 3,
        timeout: float = 180.0,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """简化版视觉 API 重试装饰器"""
        return retry_on_network_error(
            max_attempts=max_attempts, wait_min=2.0, wait_max=30.0
        )


# ============================================================================
# 便捷重试函数
# ============================================================================


async def retry_async_call(
    func: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    wait_min: float = 1.0,
    wait_max: float = 10.0,
    **kwargs: Any,
) -> Any:
    """
    通用异步函数重试包装器

    Args:
        func: 要重试的异步函数
        *args: 位置参数
        max_attempts: 最大重试次数
        wait_min: 最小等待时间
        wait_max: 最大等待时间
        **kwargs: 关键字参数

    Returns:
        函数执行结果

    Raises:
        最后一次尝试的异常

    Example:
        result = await retry_async_call(
            api_client.call,
            "endpoint",
            max_attempts=3
        )
    """
    last_exception: Exception | None = None
    wait_time = wait_min

    for attempt in range(max_attempts):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            is_network_error = isinstance(
                e,
                (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError),
            )
            is_retryable_api = isinstance(e, httpx.HTTPStatusError) and (
                e.response.status_code >= 500 or e.response.status_code == 429
            )

            should_retry = is_network_error or is_retryable_api

            if should_retry and attempt < max_attempts - 1:
                logger.warning(
                    f"Call failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                await asyncio.sleep(wait_time)
                wait_time = min(wait_time * 2, wait_max)
            else:
                logger.error(f"Max retries ({max_attempts}) reached")

    if last_exception is None:
        raise RuntimeError("Unexpected error in retry logic")
    raise last_exception


# ============================================================================
# 上下文管理器版本
# ============================================================================


class RetryContext:
    """
    重试上下文管理器
    用于更灵活的重试控制

    Example:
        async with RetryContext(max_attempts=3) as retry:
            while retry.should_continue():
                try:
                    result = await api_call()
                    retry.success()
                    break
                except Exception as e:
                    retry.record_error(e)
    """

    def __init__(
        self,
        max_attempts: int = 3,
        wait_min: float = 1.0,
        wait_max: float = 10.0,
        retry_on: tuple[type[Exception], ...] = (
            httpx.TimeoutException,
            httpx.NetworkError,
        ),
    ):
        self.max_attempts = max_attempts
        self.wait_min = wait_min
        self.wait_max = wait_max
        self.retry_on = retry_on
        self.attempts = 0
        self._succeeded = False

    async def __aenter__(self) -> "RetryContext":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        return False

    def should_continue(self) -> bool:
        """是否应该继续重试"""
        return self.attempts < self.max_attempts and not self._succeeded

    def success(self) -> None:
        """标记成功"""
        self._succeeded = True

    async def record_error(self, error: Exception) -> None:
        """
        记录错误并等待

        Args:
            error: 捕获的异常
        """
        self.attempts += 1

        if not isinstance(error, self.retry_on):
            raise error

        if self.attempts < self.max_attempts:
            wait_time = min(self.wait_min * (2 ** (self.attempts - 1)), self.wait_max)
            logger.warning(
                f"Error (attempt {self.attempts}/{self.max_attempts}): {error}. "
                f"Retrying in {wait_time:.1f}s..."
            )
            await asyncio.sleep(wait_time)
        else:
            logger.error(f"Max retries ({self.max_attempts}) reached")
            raise error


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":  # pragma: no cover
    # 装饰器使用示例
    @retry_on_network_error(max_attempts=3)  # type: ignore[misc]  # type: ignore[misc]
    async def example_api_call(url: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            return response.json()

    # 上下文管理器使用示例
    async def example_with_context():
        async with RetryContext(max_attempts=3) as retry:
            while retry.should_continue():
                try:
                    result = await example_api_call("https://api.example.com")
                    retry.success()
                    return result
                except Exception as e:
                    await retry.record_error(e)

    # 函数包装器使用示例
    async def example_with_wrapper():
        return await retry_async_call(
            example_api_call,
            "https://api.example.com",
            max_attempts=3,
        )
