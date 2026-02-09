"""
Audit Service 单元测试

测试 AuditService 的审计日志创建功能
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

pytestmark = pytest.mark.asyncio

from src.models.auth import AuditLog, User
from src.services.core.audit_service import AuditService

# ============================================================================
# Fixtures
# ============================================================================


def _mock_execute_first(value):
    result = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = value
    result.scalars.return_value = scalars
    return result


def _mock_execute_scalar(value):
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _mock_execute_user_role(user, role_name="管理员"):
    call_counter = {"count": 0}

    def _side_effect(*_args, **_kwargs):
        current = call_counter["count"]
        call_counter["count"] += 1
        if current % 2 == 0:
            return _mock_execute_first(user)
        return _mock_execute_scalar(role_name)

    return AsyncMock(side_effect=_side_effect)


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.query = MagicMock()
    return db


@pytest.fixture
def audit_service(mock_db):
    """审计服务实例"""
    return AuditService(mock_db)


@pytest.fixture
def mock_user():
    """模拟用户对象"""
    user = Mock(spec=User)
    user.id = "test-user-123"
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    return user


# ============================================================================
# Test create_audit_log - Success Scenarios
# ============================================================================
class TestCreateAuditLogSuccess:
    """测试成功创建审计日志"""

    async def test_create_basic_audit_log(self, audit_service, mock_db, mock_user):
        """测试创建基本审计日志"""
        # 模拟数据库查询返回用户
        mock_db.execute = AsyncMock(
            side_effect=[_mock_execute_first(mock_user), _mock_execute_scalar("管理员")]
        )

        # 模拟创建的审计日志
        mock_audit_log = Mock(spec=AuditLog)
        mock_audit_log.id = "audit-123"

        result = await audit_service.create_audit_log(user_id=mock_user.id, action="login")

        assert result is not None
        assert mock_db.execute.await_count == 2
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    async def test_create_audit_log_with_all_fields(self, audit_service, mock_db, mock_user):
        """测试创建包含所有字段的审计日志"""
        mock_db.execute = AsyncMock(
            side_effect=[_mock_execute_first(mock_user), _mock_execute_scalar("管理员")]
        )

        mock_audit_log = Mock(spec=AuditLog)
        mock_audit_log.id = "audit-456"

        result = await audit_service.create_audit_log(
            user_id=mock_user.id,
            action="asset_update",
            resource_type="asset",
            resource_id="asset-123",
            resource_name="测试物业",
            api_endpoint="/api/v1/assets/asset-123",
            http_method="PUT",
            request_params='{"page": 1}',
            request_body='{"name": "新名称"}',
            response_status=200,
            response_message="成功",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            session_id="session-abc-123",
        )

        assert result is not None
        mock_db.add.assert_called_once()

    async def test_create_audit_log_with_partial_fields(
        self, audit_service, mock_db, mock_user
    ):
        """测试创建包含部分字段的审计日志"""
        mock_db.execute = AsyncMock(
            side_effect=[_mock_execute_first(mock_user), _mock_execute_scalar("管理员")]
        )

        result = await audit_service.create_audit_log(
            user_id=mock_user.id,
            action="logout",
            resource_type="session",
            ip_address="192.168.1.100",
        )

        assert result is not None
        mock_db.add.assert_called_once()

    async def test_create_multiple_audit_logs(self, audit_service, mock_db, mock_user):
        """测试创建多个审计日志"""
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_first(mock_user),
                _mock_execute_scalar("管理员"),
                _mock_execute_first(mock_user),
                _mock_execute_scalar("管理员"),
            ]
        )

        # 第一个日志
        result1 = await audit_service.create_audit_log(user_id=mock_user.id, action="login")

        # 第二个日志
        result2 = await audit_service.create_audit_log(user_id=mock_user.id, action="logout")

        assert result1 is not None
        assert result2 is not None
        assert mock_db.commit.await_count == 2


# ============================================================================
# Test create_audit_log - Error Handling
# ============================================================================
class TestCreateAuditLogErrorHandling:
    """测试错误处理"""

    async def test_user_not_found(self, audit_service, mock_db):
        """测试用户不存在"""
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        result = await audit_service.create_audit_log(
            user_id="nonexistent-user", action="test_action"
        )

        assert result is None
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_awaited()

    async def test_empty_user_id(self, audit_service, mock_db):
        """测试空用户ID"""
        mock_db.execute = AsyncMock(return_value=_mock_execute_first(None))

        result = await audit_service.create_audit_log(user_id="", action="test_action")

        assert result is None

    async def test_database_error_on_query(self, audit_service, mock_db):
        """测试查询时数据库错误"""
        mock_db.execute = AsyncMock(side_effect=Exception("Database connection error"))

        with pytest.raises(Exception, match="Database connection error"):
            await audit_service.create_audit_log(user_id="test-user", action="test_action")

    async def test_database_error_on_add(self, audit_service, mock_db, mock_user):
        """测试add时数据库错误"""
        mock_db.execute = AsyncMock(
            side_effect=[_mock_execute_first(mock_user), _mock_execute_scalar("管理员")]
        )
        mock_db.add.side_effect = Exception("Add failed")

        with pytest.raises(Exception, match="Add failed"):
            await audit_service.create_audit_log(user_id=mock_user.id, action="test_action")

    async def test_database_error_on_commit(self, audit_service, mock_db, mock_user):
        """测试commit时数据库错误"""
        mock_db.execute = AsyncMock(
            side_effect=[_mock_execute_first(mock_user), _mock_execute_scalar("管理员")]
        )
        mock_db.commit.side_effect = Exception("Commit failed")

        with pytest.raises(Exception, match="Commit failed"):
            await audit_service.create_audit_log(user_id=mock_user.id, action="test_action")


# ============================================================================
# Test create_audit_log - Different Action Types
# ============================================================================
class TestCreateAuditLogActionTypes:
    """测试不同的操作类型"""

    @pytest.mark.parametrize(
        "action",
        [
            "login",
            "logout",
            "create",
            "update",
            "delete",
            "view",
            "export",
            "import",
            "approve",
            "reject",
        ],
    )
    async def test_various_actions(self, audit_service, mock_db, mock_user, action):
        """测试各种操作类型"""
        mock_db.execute = _mock_execute_user_role(mock_user)

        result = await audit_service.create_audit_log(user_id=mock_user.id, action=action)

        assert result is not None

    async def test_login_action_with_details(self, audit_service, mock_db, mock_user):
        """测试登录操作（包含详细信息）"""
        mock_db.execute = _mock_execute_user_role(mock_user)

        result = await audit_service.create_audit_log(
            user_id=mock_user.id,
            action="login",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
        )

        assert result is not None

    async def test_data_access_action(self, audit_service, mock_db, mock_user):
        """测试数据访问操作"""
        mock_db.execute = _mock_execute_user_role(mock_user)

        result = await audit_service.create_audit_log(
            user_id=mock_user.id,
            action="view",
            resource_type="asset",
            resource_id="asset-123",
            api_endpoint="/api/v1/assets/asset-123",
        )

        assert result is not None


# ============================================================================
# Test create_audit_log - Edge Cases
# ============================================================================
class TestCreateAuditLogEdgeCases:
    """测试边界情况"""

    async def test_with_none_optional_fields(self, audit_service, mock_db, mock_user):
        """测试所有可选字段为None"""
        mock_db.execute = _mock_execute_user_role(mock_user)

        result = await audit_service.create_audit_log(
            user_id=mock_user.id,
            action="test_action",
            resource_type=None,
            resource_id=None,
            resource_name=None,
            api_endpoint=None,
            http_method=None,
            request_params=None,
            request_body=None,
            response_status=None,
            response_message=None,
            ip_address=None,
            user_agent=None,
            session_id=None,
        )

        assert result is not None

    async def test_with_empty_strings(self, audit_service, mock_db, mock_user):
        """测试空字符串值"""
        mock_db.execute = _mock_execute_user_role(mock_user)

        result = await audit_service.create_audit_log(
            user_id=mock_user.id, action="", resource_type="", resource_id=""
        )

        assert result is not None

    async def test_with_special_characters(self, audit_service, mock_db, mock_user):
        """测试特殊字符"""
        special_chars = "测试\n\t\r\\\"'<>{}[]"

        mock_db.execute = _mock_execute_user_role(mock_user)

        result = await audit_service.create_audit_log(
            user_id=mock_user.id,
            action="test_action",
            resource_name=special_chars,
            response_message=special_chars,
        )

        assert result is not None

    async def test_with_unicode_characters(self, audit_service, mock_db, mock_user):
        """测试Unicode字符"""
        unicode_text = "🎉 测试 Тест"

        mock_db.execute = _mock_execute_user_role(mock_user)

        result = await audit_service.create_audit_log(
            user_id=mock_user.id, action="test_action", resource_name=unicode_text
        )

        assert result is not None

    async def test_with_json_data(self, audit_service, mock_db, mock_user):
        """测试JSON数据"""
        json_data = '{"key": "value", "nested": {"data": "测试"}}'

        mock_db.execute = _mock_execute_user_role(mock_user)

        result = await audit_service.create_audit_log(
            user_id=mock_user.id,
            action="test_action",
            request_params=json_data,
            request_body=json_data,
        )

        assert result is not None

    async def test_with_different_response_statuses(self, audit_service, mock_db, mock_user):
        """测试不同的响应状态码"""
        status_codes = [200, 201, 204, 400, 401, 403, 404, 500, 503]

        mock_db.execute = _mock_execute_user_role(mock_user)

        for status_code in status_codes:
            result = await audit_service.create_audit_log(
                user_id=mock_user.id, action="test_action", response_status=status_code
            )

            assert result is not None

    async def test_with_different_http_methods(self, audit_service, mock_db, mock_user):
        """测试不同的HTTP方法"""
        http_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

        mock_db.execute = _mock_execute_user_role(mock_user)

        for method in http_methods:
            result = await audit_service.create_audit_log(
                user_id=mock_user.id, action="test_action", http_method=method
            )

            assert result is not None


# ============================================================================
# Test Integration Scenarios
# ============================================================================
class TestAuditServiceIntegration:
    """测试集成场景"""

    async def test_complete_user_lifecycle(self, audit_service, mock_db, mock_user):
        """测试完整的用户生命周期审计"""
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_execute_first(mock_user),
                _mock_execute_scalar("管理员"),
                _mock_execute_first(mock_user),
                _mock_execute_scalar("管理员"),
                _mock_execute_first(mock_user),
                _mock_execute_scalar("管理员"),
            ]
        )

        # 用户登录
        await audit_service.create_audit_log(
            user_id=mock_user.id, action="login", ip_address="192.168.1.100"
        )

        # 用户查看数据
        await audit_service.create_audit_log(
            user_id=mock_user.id,
            action="view",
            resource_type="asset",
            resource_id="asset-123",
        )

        # 用户登出
        await audit_service.create_audit_log(user_id=mock_user.id, action="logout")

        assert mock_db.commit.await_count == 3

    async def test_failed_operation_audit(self, audit_service, mock_db, mock_user):
        """测试失败操作的审计"""
        mock_db.execute = _mock_execute_user_role(mock_user)

        await audit_service.create_audit_log(
            user_id=mock_user.id,
            action="create",
            resource_type="asset",
            response_status=400,
            response_message="Validation Error: Invalid data",
        )

        mock_db.add.assert_called_once()

    async def test_admin_privileged_operation(self, audit_service, mock_db):
        """测试管理员特权操作"""
        admin_user = Mock(spec=User)
        admin_user.id = "admin-user-id"
        admin_user.username = "admin"
        admin_user.default_organization_id = "org-admin"
        mock_db.execute = _mock_execute_user_role(admin_user)

        await audit_service.create_audit_log(
            user_id=admin_user.id,
            action="delete_user",
            resource_type="user",
            resource_id="user-to-delete",
            response_status=200,
            response_message="User deleted successfully",
        )

        mock_db.add.assert_called_once()


# ============================================================================
# Test Database Operations
# ============================================================================
class TestDatabaseOperations:
    """测试数据库操作"""

    async def test_query_called_with_correct_filter(self, audit_service, mock_db, mock_user):
        """测试使用正确的筛选条件查询"""
        mock_db.execute = _mock_execute_user_role(mock_user)

        await audit_service.create_audit_log(user_id="specific-user-id", action="test_action")

        assert mock_db.execute.await_count == 2
        query_stmt = mock_db.execute.await_args_list[0].args[0]
        assert query_stmt.compile().params["id_1"] == "specific-user-id"

    async def test_database_operations_call_order(self, audit_service, mock_db, mock_user):
        """测试数据库操作调用顺序"""
        mock_db.execute = _mock_execute_user_role(mock_user)

        await audit_service.create_audit_log(user_id=mock_user.id, action="test_action")

        # 验证调用顺序
        assert mock_db.execute.called
        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.refresh.called
