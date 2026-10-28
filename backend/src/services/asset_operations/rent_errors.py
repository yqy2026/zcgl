"""Stable business failures for rent facts and corrections."""

from ...core.exception_handler import BaseBusinessError


def rent_error(code: str, message: str, *, status: int = 409) -> BaseBusinessError:
    return BaseBusinessError(message=message, code=code, status_code=status)
