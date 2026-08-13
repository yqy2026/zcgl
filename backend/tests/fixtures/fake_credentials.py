"""假凭证值生成器：测试夹具统一入口。

背景：Mimosa L3 git-gate 将「凭证名 + 字符串字面量」的赋值形态视为高危硬编码凭据
（见 #86）。测试代码需要假 token / 假密码时，一律调用本模块的生成函数——运行时由
单调计数器生成、源码中不含任何字面量，从根上避免误报，同时满足 testing-standards
「测试不使用随机数据」的确定性约定（单次运行内值唯一，跨运行可复现）。

约定：禁止在测试中再硬编码凭证形状的假值（如 refresh_token 直接赋字符串），防回归由
scripts/check_test_credentials.py 门禁兜底。
"""

from __future__ import annotations

import itertools

__all__ = [
    "fake_access_token",
    "fake_api_key",
    "fake_bcrypt_hash",
    "fake_identifier",
    "fake_password",
    "fake_refresh_token",
    "fake_secret_key",
    "fake_weak_password",
]

_seq = itertools.count(1)


def _next() -> int:
    """单调递增序号，保证单次运行内生成值唯一且可复现。"""
    return next(_seq)


def fake_refresh_token() -> str:
    """确定性假 refresh token。"""
    return f"test-refresh-token-{_next():08d}"


def fake_access_token() -> str:
    """确定性假 access token。"""
    return f"test-access-token-{_next():08d}"


def fake_api_key() -> str:
    """确定性假 API key。"""
    return f"sk-test-{_next():024d}"


def fake_password() -> str:
    """满足常规复杂度（大写/小写/数字/特殊字符）的确定性假密码。"""
    return f"T9!a{_next():08d}"


def fake_weak_password() -> str:
    """明显不合规的弱密码（纯小写+数字，用于弱口令校验路径）。"""
    return f"weak{_next():08d}"


def fake_bcrypt_hash() -> str:
    """确定性假 bcrypt 哈希（60 字符，仅作不透明字符串使用，不做真实校验）。"""
    return f"$2b$12${_next():053d}"


def fake_secret_key() -> str:
    """满足最小长度要求的确定性假密钥。"""
    return f"test-secret-key-{_next():016d}"


def fake_identifier(prefix: str) -> str:
    """带前缀的确定性假标识，替代 user_123 / device_123 类字面量。"""
    return f"{prefix}-{_next():08d}"
