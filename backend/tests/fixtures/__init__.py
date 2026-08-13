"""
测试fixtures包
提供可复用的测试辅助函数和数据生成器
"""

from .auth import AuthFixture
from .database import DatabaseFixture
from .fake_credentials import (
    fake_access_token,
    fake_api_key,
    fake_bcrypt_hash,
    fake_identifier,
    fake_password,
    fake_refresh_token,
    fake_secret_key,
    fake_weak_password,
)
from .test_data_generator import TestDataGenerator

__all__ = [
    "DatabaseFixture",
    "AuthFixture",
    "TestDataGenerator",
    "fake_access_token",
    "fake_api_key",
    "fake_bcrypt_hash",
    "fake_identifier",
    "fake_password",
    "fake_refresh_token",
    "fake_secret_key",
    "fake_weak_password",
]
