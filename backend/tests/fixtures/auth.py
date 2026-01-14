"""
认证测试fixtures
提供认证相关的测试辅助函数
"""

from datetime import datetime, timedelta

import jwt


class AuthFixture:
    """认证fixture类"""

    @staticmethod
    def create_token(
        user_id: str, secret: str = "test-secret", expires_hours: int = 1
    ) -> str:
        """创建JWT token"""
        token_data = {
            "sub": "testuser",
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(hours=expires_hours),
        }
        return jwt.encode(token_data, secret, algorithm="HS256")

    @staticmethod
    def create_auth_headers(token: str) -> dict[str, str]:
        """创建认证头"""
        return {"Authorization": f"Bearer {token}"}
