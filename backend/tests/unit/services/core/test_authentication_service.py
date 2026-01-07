"""
测试 AuthenticationService (认证服务) 安全相关功能
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from src.exceptions import BusinessLogicError
from src.services.core.authentication_service import AuthenticationService


@pytest.fixture
def mock_db():
    """创建模拟数据库会话"""
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.first.return_value = None
    return db


@pytest.fixture
def auth_service(mock_db):
    """创建 AuthenticationService 实例"""
    with patch("src.services.core.authentication_service.UserManagementService"):
        with patch("src.services.core.authentication_service.SessionService"):
            with patch("src.services.core.authentication_service.PasswordService"):
                return AuthenticationService(mock_db)


class TestAuthenticationServiceSecurity:
    """测试 AuthenticationService 安全相关功能"""

    def test_init(self, mock_db):
        """测试服务初始化"""
        with patch("src.services.core.authentication_service.UserManagementService"):
            with patch("src.services.core.authentication_service.SessionService"):
                with patch("src.services.core.authentication_service.PasswordService"):
                    service = AuthenticationService(mock_db)
                    assert service.db == mock_db

    def test_authenticate_user_nonexistent(self, auth_service, mock_db):
        """测试不存在用户的认证"""
        # 用户不存在
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = auth_service.authenticate_user("nonexistent", "password")

        assert result is None

    def test_authenticate_user_wrong_password(self, auth_service, mock_db):
        """测试错误密码认证失败"""
        mock_user = MagicMock(
            id="user_1",
            username="testuser",
            password_hash="hashed_password",
            is_active=True,
            failed_login_attempts=0,
        )
        mock_user.is_locked_now.return_value = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        # 密码验证失败
        auth_service.password_service.verify_password.return_value = False

        result = auth_service.authenticate_user("testuser", "wrong_password")

        assert result is None
        # 失败次数应增加
        assert mock_user.failed_login_attempts == 1

    def test_authenticate_user_locked_account(self, auth_service, mock_db):
        """测试锁定账户无法登录"""
        mock_user = MagicMock(
            id="user_1",
            username="testuser",
            password_hash="hashed_password",
            is_active=True,
            failed_login_attempts=5,
        )
        mock_user.is_locked_now.return_value = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        with pytest.raises(BusinessLogicError) as excinfo:
            auth_service.authenticate_user("testuser", "any_password")

        assert "锁定" in str(excinfo.value)

    def test_authenticate_user_success(self, auth_service, mock_db):
        """测试成功认证"""
        mock_user = MagicMock(
            id="user_1",
            username="testuser",
            password_hash="hashed_password",
            is_active=True,
            failed_login_attempts=2,
        )
        mock_user.is_locked_now.return_value = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        # 密码验证成功
        auth_service.password_service.verify_password.return_value = True
        auth_service.password_service.is_password_expired.return_value = False

        result = auth_service.authenticate_user("testuser", "correct_password")

        assert result == mock_user
        # 失败次数应重置
        assert mock_user.failed_login_attempts == 0

    def test_validate_refresh_token_invalid(self, auth_service):
        """测试无效刷新令牌"""
        result = auth_service.validate_refresh_token("invalid_token")
        assert result is None

    @patch("src.services.core.authentication_service.jwt")
    def test_create_tokens_generates_valid_structure(self, mock_jwt, auth_service):
        """测试创建令牌返回正确结构"""
        mock_jwt.encode.return_value = "encoded_token"

        mock_user = MagicMock(
            id="user_1",
            username="testuser",
            role=MagicMock(value="admin"),
        )

        result = auth_service.create_tokens(mock_user)

        assert hasattr(result, "access_token")
        assert hasattr(result, "refresh_token")
        assert result.token_type == "bearer"

    def test_generate_jti_uniqueness(self, auth_service):
        """测试JWT ID生成唯一性"""
        jti1 = auth_service._generate_jti()
        jti2 = auth_service._generate_jti()

        assert jti1 != jti2
        assert len(jti1) > 20  # 足够长度
