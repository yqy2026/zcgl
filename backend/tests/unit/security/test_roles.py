"""
Test suite for RoleNormalizer utility
Tests case-insensitive role comparison and normalization
"""

import pytest

from src.core.exception_handler import BusinessValidationError
from src.models.auth import UserRole
from src.security.roles import Role, RoleNormalizer


def test_role_enum_matches_user_role():
    """Test that Role enum matches UserRole enum values"""
    assert Role.ADMIN.value == UserRole.ADMIN.value
    assert Role.USER.value == UserRole.USER.value


def test_role_normalizer_case_insensitive():
    """Test that role comparison is case-insensitive"""
    assert RoleNormalizer.is_admin("admin") is True
    assert RoleNormalizer.is_admin("ADMIN") is True
    assert RoleNormalizer.is_admin("Admin") is True
    assert RoleNormalizer.is_admin("user") is False


def test_role_normalizer_standardizes():
    """Test that roles are standardized to lowercase"""
    assert RoleNormalizer.normalize("ADMIN") == "admin"
    assert RoleNormalizer.normalize("Admin") == "admin"
    assert RoleNormalizer.normalize("admin") == "admin"


def test_role_normalizer_validates():
    """Test that invalid roles raise errors"""
    with pytest.raises(BusinessValidationError, match="Invalid role"):
        RoleNormalizer.validate("superadmin")


def test_role_normalizer_from_string():
    """Test creating Role from string (case-insensitive)"""
    assert Role.from_string("admin") == Role.ADMIN
    assert Role.from_string("ADMIN") == Role.ADMIN
    assert Role.from_string("user") == Role.USER


def test_role_normalizer_is_user():
    """Test is_user method with case variations"""
    assert RoleNormalizer.is_user("user") is True
    assert RoleNormalizer.is_user("USER") is True
    assert RoleNormalizer.is_user("User") is True
    assert RoleNormalizer.is_user("admin") is False


def test_role_normalizer_equals():
    """Test equals method for comparing two roles"""
    assert RoleNormalizer.equals("admin", "ADMIN") is True
    assert RoleNormalizer.equals("Admin", "admin") is True
    assert RoleNormalizer.equals("admin", "user") is False


def test_role_from_string_invalid():
    """Test that from_string raises BusinessValidationError for invalid roles"""
    with pytest.raises(BusinessValidationError, match="Invalid role"):
        Role.from_string("superadmin")

    with pytest.raises(BusinessValidationError, match="Invalid role"):
        Role.from_string("")


def test_role_normalizer_whitespace_handling():
    """Test that whitespace is properly handled"""
    assert RoleNormalizer.normalize("  admin  ") == "admin"
    assert RoleNormalizer.is_admin("  ADMIN  ") is True
    assert Role.from_string("  user  ") == Role.USER
