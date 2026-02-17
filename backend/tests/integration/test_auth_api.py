"""
Auth API 集成测试 - 测试重构后的认证模块

测试认证相关的所有API端点，包括：
- authentication.py: 登录、登出、刷新令牌
- users.py: 用户管理
- sessions.py: 会话管理
- audit.py: 审计日志
- security.py: 安全配置
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def authenticated_client(client: TestClient, test_data) -> TestClient:
    """使用真实登录 cookie 认证测试客户端。"""
    admin_user = test_data["admin"]
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": admin_user.username, "password": "Admin123!@#"},
    )
    assert response.status_code == 200
    auth_token = response.cookies.get("auth_token")
    csrf_token = response.cookies.get("csrf_token")
    refresh_token = response.cookies.get("refresh_token")
    assert auth_token is not None
    assert csrf_token is not None
    assert refresh_token is not None
    client.cookies.set("auth_token", auth_token)
    client.cookies.set("csrf_token", csrf_token)
    client.cookies.set("refresh_token", refresh_token)
    setattr(client, "_csrf_token", csrf_token)
    return client


@pytest.fixture
def csrf_headers(authenticated_client: TestClient) -> dict[str, str]:
    csrf_token = getattr(authenticated_client, "_csrf_token", None)
    if csrf_token is None:
        return {}
    return {"X-CSRF-Token": csrf_token}


class TestAuthenticationEndpoints:
    """测试认证相关端点 (authentication.py)"""

    def test_login_endpoint_exists(self, client):
        """测试登录端点是否存在"""
        response = client.post(
            "/api/v1/auth/login",
            json={"identifier": "admin", "password": "wrong_password"},
        )
        # 无效凭证应返回统一认证错误
        assert response.status_code == 401
        payload = response.json()
        assert payload.get("success") is False
        error = payload.get("error", {})
        assert isinstance(error, dict)
        assert error.get("code") == "AUTHENTICATION_ERROR"

    def test_login_with_valid_credentials(self, client, test_data):
        """测试使用有效凭证登录"""
        admin_user = test_data["admin"]
        response = client.post(
            "/api/v1/auth/login",
            json={"identifier": admin_user.username, "password": "Admin123!@#"},
        )
        assert response.status_code == 200

        payload = response.json()
        assert payload.get("auth_mode") == "cookie"
        assert payload.get("message") == "登录成功"
        user_info = payload.get("user", {})
        assert user_info.get("username") == admin_user.username
        assert user_info.get("id") is not None
        assert isinstance(payload.get("permissions"), list)

        assert response.cookies.get("auth_token") is not None
        assert response.cookies.get("csrf_token") is not None
        assert response.cookies.get("refresh_token") is not None

    def test_login_with_formatted_phone_identifier(self, client, test_data):
        """测试使用格式化手机号登录（+86 + 连字符）。"""
        admin_user = test_data["admin"]
        phone = admin_user.phone
        formatted_phone = f"+86 {phone[:3]}-{phone[3:7]}-{phone[7:]}"

        response = client.post(
            "/api/v1/auth/login",
            json={"identifier": formatted_phone, "password": "Admin123!@#"},
        )

        assert response.status_code == 200
        payload = response.json()
        user_info = payload.get("user", {})
        assert user_info.get("username") == admin_user.username
        assert response.cookies.get("auth_token") is not None

    def test_logout_endpoint_exists(self, client):
        """测试登出端点是否存在"""
        # 登出需要认证，所以预期返回 401
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401

    def test_refresh_token_endpoint_exists(self, client):
        """测试刷新令牌端点是否存在"""
        response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "invalid_token"}
        )
        # 无 cookie 场景返回 400（刷新令牌缺失）
        assert response.status_code == 400
        payload = response.json()
        assert payload.get("success") is False
        error = payload.get("error", {})
        assert isinstance(error, dict)
        assert error.get("code") == "INVALID_REQUEST"

    def test_me_endpoint_exists(self, client):
        """测试获取当前用户信息端点是否存在"""
        response = client.get("/api/v1/auth/me")
        # 需要认证，所以预期返回 401
        assert response.status_code == 401

    def test_me_endpoint_with_authenticated_cookie(self, authenticated_client, test_data):
        """测试登录后 /me 返回当前用户信息。"""
        response = authenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get("username") == test_data["admin"].username
        assert payload.get("session_status") == "active"
        assert isinstance(payload.get("roles"), list)

    def test_refresh_token_with_cookie(self, authenticated_client, csrf_headers):
        """测试带 cookie 的刷新令牌链路。"""
        response = authenticated_client.post(
            "/api/v1/auth/refresh",
            headers=csrf_headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload.get("message") == "令牌刷新成功"
        assert payload.get("auth_mode") == "cookie"

    def test_logout_with_csrf_revokes_session(self, authenticated_client, csrf_headers):
        """测试登出后当前会话被撤销。"""
        response = authenticated_client.post(
            "/api/v1/auth/logout",
            headers=csrf_headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload.get("message") == "登出成功"

        me_response = authenticated_client.get("/api/v1/auth/me")
        assert me_response.status_code == 401


class TestUserManagementEndpoints:
    """测试用户管理端点 (users.py)"""

    def test_get_users_list_exists(self, client):
        """测试获取用户列表端点是否存在"""
        response = client.get("/api/v1/auth/users")
        # 需要管理员权限，所以预期返回 401
        assert response.status_code == 401

    def test_search_users_exists(self, client):
        """测试搜索用户端点是否存在"""
        response = client.get("/api/v1/auth/users/search?search=admin")
        # 需要管理员权限
        assert response.status_code == 401

    def test_create_user_endpoint_exists(self, client):
        """测试创建用户端点是否存在"""
        response = client.post(
            "/api/v1/auth/users",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "Test123!@#",
                "full_name": "Test User",
                "role_id": "role-user-id",
            },
        )
        # 需要管理员权限
        assert response.status_code == 401

    def test_get_user_by_id_exists(self, client):
        """测试获取用户详情端点是否存在"""
        response = client.get("/api/v1/auth/users/123")
        # 需要认证
        assert response.status_code == 401

    def test_update_user_exists(self, client):
        """测试更新用户端点是否存在"""
        response = client.put(
            "/api/v1/auth/users/123", json={"full_name": "Updated Name"}
        )
        # 需要认证
        assert response.status_code == 401

    def test_change_password_exists(self, client):
        """测试修改密码端点是否存在"""
        response = client.post(
            "/api/v1/auth/users/123/change-password",
            json={"current_password": "old_password", "new_password": "New123!@#"},
        )
        # 需要认证
        assert response.status_code == 401

    def test_deactivate_user_exists(self, client):
        """测试停用用户端点是否存在"""
        response = client.post("/api/v1/auth/users/123/deactivate")
        # 需要管理员权限
        assert response.status_code == 401

    def test_activate_user_exists(self, client):
        """测试激活用户端点是否存在"""
        response = client.post("/api/v1/auth/users/123/activate")
        # 需要管理员权限
        assert response.status_code == 401

    def test_lock_user_exists(self, client):
        """测试锁定用户端点是否存在"""
        response = client.post("/api/v1/auth/users/123/lock")
        # 需要管理员权限
        assert response.status_code == 401

    def test_unlock_user_exists(self, client):
        """测试解锁用户端点是否存在"""
        response = client.post("/api/v1/auth/users/123/unlock")
        # 需要管理员权限
        assert response.status_code == 401

    def test_reset_password_exists(self, client):
        """测试重置密码端点是否存在"""
        response = client.post(
            "/api/v1/auth/users/123/reset-password",
            json={"new_password": "Reset123!@#"},
        )
        # 需要管理员权限
        assert response.status_code == 401

    def test_get_user_statistics_exists(self, client):
        """测试获取用户统计端点是否存在"""
        response = client.get("/api/v1/auth/users/statistics/summary")
        # 需要管理员权限
        assert response.status_code == 401

    def test_get_users_list_with_admin(self, authenticated_client, test_data):
        """测试管理员可获取用户列表，且包含当前管理员。"""
        response = authenticated_client.get("/api/v1/auth/users?page=1&page_size=20")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True
        items = payload.get("data", {}).get("items", [])
        assert isinstance(items, list)
        assert any(
            item.get("username") == test_data["admin"].username
            for item in items
            if isinstance(item, dict)
        )

    def test_get_user_statistics_with_admin(self, authenticated_client):
        """测试管理员可获取用户统计。"""
        response = authenticated_client.get("/api/v1/auth/users/statistics/summary")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True
        assert isinstance(payload.get("data"), dict)


class TestSessionManagementEndpoints:
    """测试会话管理端点 (sessions.py)"""

    def test_get_sessions_exists(self, client):
        """测试获取会话列表端点是否存在"""
        response = client.get("/api/v1/auth/sessions")
        # 需要认证
        assert response.status_code == 401

    def test_revoke_session_exists(self, client):
        """测试撤销会话端点是否存在"""
        response = client.delete("/api/v1/auth/sessions/123")
        # 需要认证
        assert response.status_code == 401

    def test_get_sessions_with_authenticated_user(self, authenticated_client):
        """测试登录后可获取当前用户会话列表。"""
        response = authenticated_client.get("/api/v1/auth/sessions")
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        if payload:
            first = payload[0]
            assert first.get("id") is not None
            assert first.get("user_id") is not None
            assert isinstance(first.get("is_active"), bool)


class TestAuditEndpoints:
    """测试审计日志端点 (audit.py)"""

    def test_get_audit_logs_exists(self, client):
        """测试获取审计日志端点是否存在"""
        response = client.get("/api/v1/auth/audit/logs?days=30")
        # 需要管理员权限
        assert response.status_code == 401

    def test_get_audit_logs_with_admin(self, authenticated_client):
        """测试管理员可访问审计统计。"""
        response = authenticated_client.get("/api/v1/auth/audit/logs?days=30")
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, dict)


class TestSecurityEndpoints:
    """测试安全配置端点 (security.py)"""

    def test_get_security_config_exists(self, client):
        """测试获取安全配置端点是否存在"""
        response = client.get("/api/v1/auth/security/config")
        # 需要管理员权限
        assert response.status_code == 401

    def test_get_security_config_with_admin(self, authenticated_client):
        """测试管理员可访问安全配置。"""
        response = authenticated_client.get("/api/v1/auth/security/config")
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload.get("password_policy"), dict)
        assert isinstance(payload.get("token_config"), dict)
        assert isinstance(payload.get("session_config"), dict)


class TestRouterStructure:
    """测试路由结构是否正确"""

    def test_all_routes_accessible(self, client):
        """测试所有路由返回与未认证场景一致的明确状态码。"""
        routes_to_test = [
            # Authentication routes
            ("POST", "/api/v1/auth/login", 422),
            ("POST", "/api/v1/auth/logout", 401),
            ("POST", "/api/v1/auth/refresh", 400),
            ("GET", "/api/v1/auth/me", 401),
            # User management routes
            ("GET", "/api/v1/auth/users", 401),
            ("GET", "/api/v1/auth/users/search", 401),
            ("POST", "/api/v1/auth/users", 401),
            ("GET", "/api/v1/auth/users/123", 401),
            ("PUT", "/api/v1/auth/users/123", 401),
            ("POST", "/api/v1/auth/users/123/change-password", 401),
            ("POST", "/api/v1/auth/users/123/deactivate", 401),
            ("POST", "/api/v1/auth/users/123/activate", 401),
            ("POST", "/api/v1/auth/users/123/lock", 401),
            ("POST", "/api/v1/auth/users/123/unlock", 401),
            ("POST", "/api/v1/auth/users/123/reset-password", 401),
            ("GET", "/api/v1/auth/users/statistics/summary", 401),
            # Session management routes
            ("GET", "/api/v1/auth/sessions", 401),
            ("DELETE", "/api/v1/auth/sessions/123", 401),
            # Audit routes
            ("GET", "/api/v1/auth/audit/logs", 401),
            # Security routes
            ("GET", "/api/v1/auth/security/config", 401),
        ]

        for method, route, expected_status in routes_to_test:
            if method == "GET":
                response = client.get(route)
            elif method == "POST":
                response = client.post(route, json={} if route == "/api/v1/auth/login" else None)
            elif method == "PUT":
                response = client.put(route)
            elif method == "DELETE":
                response = client.delete(route)

            assert response.status_code == expected_status, (
                f"Route {method} {route} expected {expected_status}, got {response.status_code}"
            )

    def test_no_duplicate_routes(self):
        """测试没有真正重复的路由（不同方法的路由可以有相同路径）"""
        from src.api.v1.auth.auth import router

        # 收集所有路由路径和方法
        route_signatures = []
        for route in router.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                for method in route.methods:
                    # 创建路由签名（路径+方法）
                    signature = f"{method} {route.path}"
                    route_signatures.append(signature)

        # 检查是否有完全相同的路由签名
        duplicates = [
            sig for sig in set(route_signatures) if route_signatures.count(sig) > 1
        ]

        assert len(duplicates) == 0, f"Found duplicate routes: {duplicates}"

    def test_router_includes_all_sub_routers(self):
        """测试主路由器包含所有子路由器"""
        from src.api.v1.auth.auth import router

        # 主路由器应该有多个子路由
        # 24个路由 = 7个认证 + 14个用户 + 2个会话 + 1个审计 + 1个安全
        assert len(router.routes) >= 20, (
            f"Expected at least 20 routes, got {len(router.routes)}"
        )


class TestBackwardCompatibility:
    """测试向后兼容性"""

    def test_old_urls_still_work(self, client):
        """测试旧的API URL仍然工作"""
        old_urls = [
            ("POST", "/api/v1/auth/login", 422),
            ("POST", "/api/v1/auth/users", 401),
            ("GET", "/api/v1/auth/sessions", 401),
        ]

        for method, url, expected_status in old_urls:
            if method == "GET":
                response = client.get(url)
            else:
                response = client.post(url, json={})

            assert response.status_code == expected_status, (
                f"Old URL {method} {url} expected {expected_status}, got {response.status_code}"
            )


class TestModuleImports:
    """测试模块导入"""

    def test_auth_router_imports(self):
        """测试认证路由器可以正确导入"""
        from src.api.v1.auth.auth import router

        assert router is not None
        assert len(router.routes) > 0

    def test_auth_modules_imports(self):
        """测试所有auth子模块可以正确导入"""
        from src.api.v1.auth.auth_modules import (
            audit,
            authentication,
            security,
            sessions,
            users,
        )

        assert authentication.router is not None
        assert users.router is not None
        assert sessions.router is not None
        assert audit.router is not None
        assert security.router is not None

    def test_service_imports(self):
        """测试服务层导入"""
        from src.services.core.audit_service import AuditService
        from src.services.core.authentication_service import AsyncAuthenticationService
        from src.services.core.password_service import PasswordService
        from src.services.core.session_service import AsyncSessionService
        from src.services.core.user_management_service import AsyncUserManagementService

        assert AsyncAuthenticationService is not None
        assert AsyncUserManagementService is not None
        assert AsyncSessionService is not None
        assert PasswordService is not None
        assert AuditService is not None
