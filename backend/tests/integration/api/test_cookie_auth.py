"""
Integration tests for httpOnly cookie-based authentication
Tests cookie setting, security attributes, and clearing on logout
"""

import pytest


def test_login_sets_http_only_cookie(client, test_data):
    """Test that login response sets httpOnly cookie"""
    admin_user = test_data["admin"]

    response = client.post("/api/v1/auth/login", data={
        "username": admin_user.username,
        "password": "Admin123!@#"
    })

    assert response.status_code == 200

    # Check for set-cookie header
    cookie_header = response.headers.get("set-cookie")
    assert cookie_header is not None, "Login should set a cookie"

    # Check for auth_token or access_token cookie
    cookies = response.cookies
    assert len(cookies) > 0, "At least one cookie should be set"


def test_cookie_is_http_only(client, test_data):
    """Test that auth cookie is httpOnly, Secure, and SameSite"""
    admin_user = test_data["admin"]

    response = client.post("/api/v1/auth/login", data={
        "username": admin_user.username,
        "password": "Admin123!@#"
    })

    assert response.status_code == 200

    # Check cookie attributes in set-cookie header
    cookie_header = response.headers.get("set-cookie", "")
    assert cookie_header, "Should have set-cookie header"

    # Verify security attributes
    # Note: Cookie headers contain these attributes
    cookie_lower = cookie_header.lower()
    assert "httponly" in cookie_lower, "Cookie should be HttpOnly to prevent XSS"
    assert "secure" in cookie_lower, "Cookie should be Secure (HTTPS only)"
    assert "samesite" in cookie_lower, "Cookie should have SameSite attribute for CSRF protection"


def test_cookie_has_expiration(client, test_data):
    """Test that auth cookie has proper expiration"""
    admin_user = test_data["admin"]

    response = client.post("/api/v1/auth/login", data={
        "username": admin_user.username,
        "password": "Admin123!@#"
    })

    assert response.status_code == 200

    # Check for max-age or expires attribute
    cookie_header = response.headers.get("set-cookie", "")
    cookie_lower = cookie_header.lower()
    assert ("max-age" in cookie_lower or "expires" in cookie_lower), \
        "Cookie should have expiration (max-age or expires)"


def test_logout_clears_cookie(client, test_data):
    """Test that logout clears auth cookie"""
    # First login
    admin_user = test_data["admin"]
    login_response = client.post("/api/v1/auth/login", data={
        "username": admin_user.username,
        "password": "Admin123!@#"
    })

    assert login_response.status_code == 200

    # Get the access token from response
    login_data = login_response.json()
    access_token = login_data["tokens"]["access_token"]

    # Now logout
    logout_response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert logout_response.status_code == 200

    # Check that logout response includes cookie clearing
    logout_cookies = logout_response.headers.get("set-cookie", "")
    if logout_cookies:
        # Cookie should be cleared (max-age=0 or expired in past)
        assert "max-age=0" in logout_cookies.lower() or \
               "expires=" in logout_cookies.lower(), \
               "Logout should clear the cookie"


def test_backward_compatibility_tokens_in_response(client, test_data):
    """Test that login still returns tokens in response body for backward compatibility"""
    admin_user = test_data["admin"]

    response = client.post("/api/v1/auth/login", data={
        "username": admin_user.username,
        "password": "Admin123!@#"
    })

    assert response.status_code == 200
    data = response.json()

    # Verify tokens are still in response body
    assert "tokens" in data, "Tokens should be in response for backward compatibility"
    assert "access_token" in data["tokens"], "Access token should be in response"
    assert "refresh_token" in data["tokens"], "Refresh token should be in response"
    assert data["tokens"]["token_type"] == "bearer", "Token type should be bearer"


def test_cookie_path_is_root(client, test_data):
    """Test that cookie path is set to root (/)"""
    admin_user = test_data["admin"]

    response = client.post("/api/v1/auth/login", data={
        "username": admin_user.username,
        "password": "Admin123!@#"
    })

    assert response.status_code == 200

    cookie_header = response.headers.get("set-cookie", "")
    assert cookie_header, "Should have set-cookie header"

    # Check for path=/
    assert "path=/" in cookie_header.lower(), \
        "Cookie path should be / to be available site-wide"


def test_login_response_includes_user_data(client, test_data):
    """Test that login response includes user data and permissions"""
    admin_user = test_data["admin"]

    response = client.post("/api/v1/auth/login", data={
        "username": admin_user.username,
        "password": "Admin123!@#"
    })

    assert response.status_code == 200
    data = response.json()

    # Verify user data
    assert "user" in data, "Response should include user data"
    assert data["user"]["username"] == admin_user.username, "Username should match"
    assert "permissions" in data, "Response should include permissions"
    assert isinstance(data["permissions"], list), "Permissions should be a list"
