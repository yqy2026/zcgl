import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, cast

from ...core.exception_handler import BaseBusinessError, internal_error


def handle_api_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """统一API异常处理装饰器（同步/异步）"""
    is_async = inspect.iscoroutinefunction(func)
    if is_async:

        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await cast(Callable[..., Awaitable[Any]], func)(*args, **kwargs)
            except BaseBusinessError:
                raise
            except Exception as e:
                raise internal_error(str(e))

        wrapper: Callable[..., Any] = async_wrapper
    else:

        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except BaseBusinessError:
                raise
            except Exception as e:
                raise internal_error(str(e))

        wrapper = sync_wrapper

    wrapper = functools.wraps(func)(wrapper)
    setattr(wrapper, "__signature__", inspect.signature(func))
    return wrapper
