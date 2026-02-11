"""
Integration tests for httpOnly cookie-based authentication
Tests cookie setting, security attributes, and clearing on logout
"""

from fastapi.testclient import TestClient

from src.core.environment import is_production


def _set_auth_cookies(
    client: TestClient, *, auth_token: str, csrf_token: str | None = None
) -> None:
    client.cookies.set("auth_token", auth_token)
    if csrf_token is not None:
        client.cookies.set("csrf_token", csrf_token)


def test_login_sets_http_only_cookie(client, test_data):
    """Test that login response sets httpOnly cookie"""
    admin_user = test_data["admin"]

    response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
    )

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

    response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
    )

    assert response.status_code == 200

    # Check cookie attributes in set-cookie header
    cookie_header = response.headers.get("set-cookie", "")
    assert cookie_header, "Should have set-cookie header"

    # Verify security attributes
    # Note: Cookie headers contain these attributes
    cookie_lower = cookie_header.lower()
    assert "httponly" in cookie_lower, "Cookie should be HttpOnly to prevent XSS"
    if is_production():
        assert "secure" in cookie_lower, "Cookie should be Secure (HTTPS only)"
    assert "samesite" in cookie_lower, (
        "Cookie should have SameSite attribute for CSRF protection"
    )


def test_cookie_has_expiration(client, test_data):
    """Test that auth cookie has proper expiration"""
    admin_user = test_data["admin"]

    response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
    )

    assert response.status_code == 200

    # Check for max-age or expires attribute
    cookie_header = response.headers.get("set-cookie", "")
    cookie_lower = cookie_header.lower()
    assert "max-age" in cookie_lower or "expires" in cookie_lower, (
        "Cookie should have expiration (max-age or expires)"
    )


def test_logout_clears_cookie(client, test_data):
    """Test that logout clears auth cookie"""
    # First login
    admin_user = test_data["admin"]
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
    )

    assert login_response.status_code == 200

    auth_cookie = login_response.cookies.get("auth_token")
    csrf_cookie = login_response.cookies.get("csrf_token")
    assert auth_cookie is not None
    assert csrf_cookie is not None
    _set_auth_cookies(client, auth_token=auth_cookie, csrf_token=csrf_cookie)

    # Now logout
    logout_response = client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert logout_response.status_code == 200

    # Check that logout response includes cookie clearing
    logout_cookies = logout_response.headers.get("set-cookie", "")
    if logout_cookies:
        # Cookie should be cleared (max-age=0 or expired in past)
        assert (
            "max-age=0" in logout_cookies.lower()
            or "expires=" in logout_cookies.lower()
        ), "Logout should clear the cookie"


def test_login_response_does_not_include_tokens(client, test_data):
    """Test that login does not return tokens in response body"""
    admin_user = test_data["admin"]

    response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "tokens" not in data, "Tokens should not be exposed in response body"


def test_cookie_path_is_root(client, test_data):
    """Test that cookie path is set to root (/)"""
    admin_user = test_data["admin"]

    response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
    )

    assert response.status_code == 200

    cookie_header = response.headers.get("set-cookie", "")
    assert cookie_header, "Should have set-cookie header"

    # Check for path=/
    assert "path=/" in cookie_header.lower(), (
        "Cookie path should be / to be available site-wide"
    )


def test_login_response_includes_user_data(client, test_data):
    """Test that login response includes user data and permissions"""
    admin_user = test_data["admin"]

    response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify user data
    assert "user" in data, "Response should include user data"
    assert data["user"]["username"] == admin_user.username, "Username should match"
    assert "permissions" in data, "Response should include permissions"
    assert isinstance(data["permissions"], list), "Permissions should be a list"


def test_protected_endpoint_authenticates_via_cookie(client, test_data):
    """Test that protected endpoints can authenticate using httpOnly cookie"""

    admin_user = test_data["admin"]

    # Login to set the httpOnly cookie
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
    )
    assert login_response.status_code == 200

    auth_cookie = login_response.cookies.get("auth_token")
    assert auth_cookie is not None, "Login should set auth_token cookie"
    _set_auth_cookies(client, auth_token=auth_cookie)

    # Access a protected endpoint WITHOUT Authorization header
    protected_response = client.get("/api/v1/auth/me")

    # Should succeed because cookie is being sent
    assert protected_response.status_code == 200
    data = protected_response.json()
    assert data["username"] == admin_user.username


def test_csrf_blocks_cookie_post_without_header(client, test_data):
    """CSRF protection should block cookie-authenticated state changes without header."""
    admin_user = test_data["admin"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
    )
    assert login_response.status_code == 200

    auth_cookie = login_response.cookies.get("auth_token")
    csrf_cookie = login_response.cookies.get("csrf_token")
    assert auth_cookie is not None
    assert csrf_cookie is not None
    _set_auth_cookies(client, auth_token=auth_cookie, csrf_token=csrf_cookie)

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 403


def test_csrf_allows_cookie_post_with_header(client, test_data):
    """CSRF protection should allow cookie-authenticated state changes with header."""
    admin_user = test_data["admin"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
    )
    assert login_response.status_code == 200

    auth_cookie = login_response.cookies.get("auth_token")
    csrf_cookie = login_response.cookies.get("csrf_token")
    assert auth_cookie is not None
    assert csrf_cookie is not None
    _set_auth_cookies(client, auth_token=auth_cookie, csrf_token=csrf_cookie)

    response = client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 200


def test_bearer_rejected_in_cookie_only_mode(client, test_data):
    """Test that Authorization header is rejected in cookie-only auth"""
    admin_user = test_data["admin"]

    # Login
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
    )
    assert login_response.status_code == 200

    # Get the token from cookie (avoid response body)
    access_token = login_response.cookies.get("auth_token")
    assert access_token is not None

    stateless_client = TestClient(client.app)

    # Access protected endpoint with Authorization header but NO cookie
    # (simulate browser with cookies disabled)
    protected_response = stateless_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    # Should be rejected in cookie-only mode
    assert protected_response.status_code in [401, 403]
