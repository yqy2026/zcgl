import pytest
from src.core.role_normalizer import RoleNormalizer

def test_admin_role_lowercase_recognized():
    """Test that lowercase 'admin' role is recognized as admin"""
    # This should pass after fix
    assert RoleNormalizer.is_admin("admin") is True

def test_admin_role_uppercase_recognized():
    """Test that uppercase 'ADMIN' role is recognized as admin"""
    assert RoleNormalizer.is_admin("ADMIN") is True

def test_organization_permission_admin_access():
    """Test that admin users can access organizations"""
    # Will test actual middleware behavior
    # For now, just verify RoleNormalizer works
    assert RoleNormalizer.is_admin("admin") is True
    assert RoleNormalizer.is_admin("ADMIN") is True
    assert RoleNormalizer.is_admin("Admin") is True
