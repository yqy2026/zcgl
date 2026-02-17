"""
Integration tests for auth permissions in login response
Tests that the login API returns user permissions
"""


def _login_as_admin(client, test_data):
    admin_user = test_data["admin"]
    response = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": admin_user.username,
            "password": "Admin123!@#",
        },
    )
    return response


def test_login_returns_permissions(client, test_data):
    """Test login returns permission list and cookie auth metadata."""
    response = _login_as_admin(client, test_data)

    assert response.status_code == 200
    data = response.json()
    assert "permissions" in data
    assert isinstance(data["permissions"], list)
    assert data.get("auth_mode") == "cookie"
    assert data.get("user", {}).get("id") is not None
    assert response.cookies.get("auth_token") is not None
    assert response.cookies.get("csrf_token") is not None
    assert response.cookies.get("refresh_token") is not None


def test_permission_structure(client, test_data):
    """Test permission schema, uniqueness, and expected admin capability."""
    response = _login_as_admin(client, test_data)

    assert response.status_code == 200
    data = response.json()
    permissions = data.get("permissions", [])

    # If permissions exist, they should have correct structure
    for perm in permissions:
        assert "resource" in perm, "Permission must have 'resource' field"
        assert "action" in perm, "Permission must have 'action' field"
        assert isinstance(perm["resource"], str), "Resource must be string"
        assert isinstance(perm["action"], str), "Action must be string"

    permission_pairs = {
        (perm.get("resource"), perm.get("action"))
        for perm in permissions
        if isinstance(perm, dict)
    }
    assert len(permission_pairs) == len(permissions)
    assert ("system", "admin") in permission_pairs


def test_login_with_invalid_password_rejected(client, test_data):
    """Invalid password should be rejected and not issue auth cookies."""
    admin_user = test_data["admin"]
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": admin_user.username, "password": "WrongPass123!"},
    )
    assert response.status_code == 401
    payload = response.json()
    assert payload.get("success") is False
    assert response.cookies.get("auth_token") is None
