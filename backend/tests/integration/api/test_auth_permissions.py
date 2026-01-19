"""
Integration tests for auth permissions in login response
Tests that the login API returns user permissions
"""

import pytest


def test_login_returns_permissions(client, test_data):
    """Test that login response includes permissions array"""
    # Get test admin user from test_data
    admin_user = test_data["admin"]

    response = client.post("/api/v1/auth/login", data={
        "username": admin_user.username,
        "password": "Admin123!@#"  # Matches the password in conftest.py
    })

    assert response.status_code == 200
    data = response.json()
    assert "permissions" in data
    assert isinstance(data["permissions"], list)


def test_permission_structure(client, test_data):
    """Test that permissions have correct structure"""
    admin_user = test_data["admin"]

    response = client.post("/api/v1/auth/login", data={
        "username": admin_user.username,
        "password": "Admin123!@#"
    })

    assert response.status_code == 200
    data = response.json()
    permissions = data.get("permissions", [])

    # If permissions exist, they should have correct structure
    for perm in permissions:
        assert "resource" in perm, "Permission must have 'resource' field"
        assert "action" in perm, "Permission must have 'action' field"
        assert isinstance(perm["resource"], str), "Resource must be string"
        assert isinstance(perm["action"], str), "Action must be string"
