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

pytestmark = pytest.mark.skip(
    reason="Integration API tests require real JWT authentication setup"
)


@pytest.fixture
def client():
    """创建测试客户端"""
    from src.main import app

    return TestClient(app)


class TestAuthenticationEndpoints:
    """测试认证相关端点 (authentication.py)"""

    def test_login_endpoint_exists(self, client):
        """测试登录端点是否存在"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong_password"},
        )
        # 应该返回 401 (密码错误) 或 422 (验证错误)，但不应该是 404
        assert response.status_code != 404
        assert response.status_code in [401, 422]

    def test_login_with_valid_credentials(self, client):
        """测试使用有效凭证登录"""
        # 注意：这需要数据库中有admin用户
        # 如果测试环境没有admin用户，这个测试会失败
        response = client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "Admin123!@#"}
        )
        # 可能的响应: 200 (成功), 401 (密码错误), 404 (用户不存在)
        assert response.status_code in [200, 401, 404]

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
        # 应该返回 401 (无效令牌) 或 422 (验证错误)
        assert response.status_code in [401, 422]

    def test_me_endpoint_exists(self, client):
        """测试获取当前用户信息端点是否存在"""
        response = client.get("/api/v1/auth/me")
        # 需要认证，所以预期返回 401
        assert response.status_code == 401


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
                "role": "user",
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


class TestAuditEndpoints:
    """测试审计日志端点 (audit.py)"""

    def test_get_audit_logs_exists(self, client):
        """测试获取审计日志端点是否存在"""
        response = client.get("/api/v1/auth/audit/logs?days=30")
        # 需要管理员权限
        assert response.status_code == 401


class TestSecurityEndpoints:
    """测试安全配置端点 (security.py)"""

    def test_get_security_config_exists(self, client):
        """测试获取安全配置端点是否存在"""
        response = client.get("/api/v1/auth/security/config")
        # 需要管理员权限
        assert response.status_code == 401


class TestRouterStructure:
    """测试路由结构是否正确"""

    def test_all_routes_accessible(self, client):
        """测试所有路由都可以访问（不会返回404）"""
        routes_to_test = [
            # Authentication routes
            ("POST", "/api/v1/auth/login"),
            ("POST", "/api/v1/auth/logout"),
            ("POST", "/api/v1/auth/refresh"),
            ("GET", "/api/v1/auth/me"),
            # User management routes
            ("GET", "/api/v1/auth/users"),
            ("GET", "/api/v1/auth/users/search"),
            ("POST", "/api/v1/auth/users"),
            ("GET", "/api/v1/auth/users/123"),
            ("PUT", "/api/v1/auth/users/123"),
            ("POST", "/api/v1/auth/users/123/change-password"),
            ("POST", "/api/v1/auth/users/123/deactivate"),
            ("POST", "/api/v1/auth/users/123/activate"),
            ("POST", "/api/v1/auth/users/123/lock"),
            ("POST", "/api/v1/auth/users/123/unlock"),
            ("POST", "/api/v1/auth/users/123/reset-password"),
            ("GET", "/api/v1/auth/users/statistics/summary"),
            # Session management routes
            ("GET", "/api/v1/auth/sessions"),
            ("DELETE", "/api/v1/auth/sessions/123"),
            # Audit routes
            ("GET", "/api/v1/auth/audit/logs"),
            # Security routes
            ("GET", "/api/v1/auth/security/config"),
        ]

        for method, route in routes_to_test:
            if method == "GET":
                response = client.get(route)
            elif method == "POST":
                response = client.post(route)
            elif method == "PUT":
                response = client.put(route)
            elif method == "DELETE":
                response = client.delete(route)

            # 所有路由都应该存在（不返回404）
            # 可能返回 401 (需要认证), 422 (验证错误), 但不应该是 404
            assert response.status_code != 404, f"Route {method} {route} returned 404"

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
        # 这些URL在重构前就存在，重构后应该仍然可以访问
        old_urls = [
            "/api/v1/auth/login",  # 旧的登录URL
            "/api/v1/auth/users",  # 旧的用户列表URL
            "/api/v1/auth/sessions",  # 旧的会话URL
        ]

        for url in old_urls:
            response = (
                client.get(url)
                if url.startswith("/api/v1/auth/sessions")
                else client.post(url, json={})
            )
            # 不应该返回404
            assert response.status_code != 404, f"Old URL {url} is broken"


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
        from src.services.core.authentication_service import AuthenticationService
        from src.services.core.password_service import PasswordService
        from src.services.core.session_service import SessionService
        from src.services.core.user_management_service import UserManagementService

        assert AuthenticationService is not None
        assert UserManagementService is not None
        assert SessionService is not None
        assert PasswordService is not None
        assert AuditService is not None
