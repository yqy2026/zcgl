import base64
import binascii  # pylint: disable=unused-import
import json
from datetime import datetime, timedelta
from typing import cast

import bcrypt

from ...core.config import settings
from ...models.auth import User

# 密码策略
MIN_PASSWORD_LENGTH = settings.MIN_PASSWORD_LENGTH
# 密码过期策略（天数）
PASSWORD_EXPIRE_DAYS = int(getattr(settings, "PASSWORD_EXPIRE_DAYS", 90))


class PasswordService:
    """密码相关服务"""

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        try:
            # 处理base64编码的哈希
            if isinstance(hashed_password, str):
                if hashed_password.startswith("$2b$"):
                    # 标准bcrypt哈希
                    return bcrypt.checkpw(
                        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
                    )
                else:
                    # 可能是base64编码的
                    try:
                        decoded_hash = base64.b64decode(hashed_password)
                        return bcrypt.checkpw(
                            plain_password.encode("utf-8"), decoded_hash
                        )
                    except (binascii.Error, ValueError):  # pragma: no cover
                        return bcrypt.checkpw(  # pragma: no cover
                            plain_password.encode("utf-8"),
                            hashed_password.encode("utf-8"),
                        )
            else:  # pragma: no cover
                return bcrypt.checkpw(
                    plain_password.encode("utf-8"), hashed_password
                )  # pragma: no cover
        except Exception:  # pragma: no cover
            return False  # pragma: no cover

    def get_password_hash(self, password: str) -> str:
        """生成密码哈希"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def validate_password_strength(self, password: str) -> bool:
        """验证密码强度"""
        if len(password) < MIN_PASSWORD_LENGTH:
            return False

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        return has_upper and has_lower and has_digit and has_special

    def is_password_in_history(self, user: User, password: str) -> bool:
        """检查密码是否在历史记录中"""
        password_history_value = user.password_history
        if not password_history_value:  # pragma: no cover
            return False  # pragma: no cover

        try:
            # 解析密码历史记录
            if isinstance(password_history_value, str):
                password_history: list[str] = json.loads(password_history_value)
            else:  # pragma: no cover
                password_history = cast(list[str], password_history_value)  # pragma: no cover

            # 检查密码是否与历史记录中的任何密码匹配
            for old_hash in password_history:
                if self.verify_password(password, old_hash):
                    return True
        except (json.JSONDecodeError, TypeError):  # pragma: no cover
            # 如果解析失败，返回False
            return False  # pragma: no cover

        return False

    def add_password_to_history(self, user: User, password_hash: str) -> None:
        """将密码哈希添加到历史记录中"""
        # 获取现有历史记录或创建空列表
        password_history_value = user.password_history
        if password_history_value:
            try:
                if isinstance(password_history_value, str):
                    password_history = json.loads(password_history_value)
                else:  # pragma: no cover
                    password_history = cast(list[str], password_history_value)  # pragma: no cover
            except (json.JSONDecodeError, TypeError):  # pragma: no cover
                password_history = []  # pragma: no cover
        else:
            password_history = []

        # 添加新密码哈希到历史记录
        password_history.append(password_hash)

        # 保留最近10个密码
        if len(password_history) > 10:
            password_history = password_history[-10:]

        # 更新用户记录
        user.password_history = json.dumps(password_history)  # type: ignore[assignment]
        user.password_last_changed = datetime.now()  # type: ignore[assignment]

    def is_password_expired(self, user: User) -> bool:
        """检查密码是否过期"""
        password_last_changed_value = user.password_last_changed
        if not password_last_changed_value:  # pragma: no cover
            return False  # pragma: no cover

        # 如果PASSWORD_EXPIRE_DAYS为0或负数，表示不启用密码过期策略
        if PASSWORD_EXPIRE_DAYS <= 0:  # pragma: no cover
            return False  # pragma: no cover

        # 计算密码过期时间
        expire_time = password_last_changed_value + timedelta(days=PASSWORD_EXPIRE_DAYS)
        return bool(datetime.now() > expire_time)
