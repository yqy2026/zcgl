"""
JWT令牌黑名单管理器
用于管理被撤销的JWT令牌，防止令牌重放攻击
"""

import json
import logging
import time
from datetime import UTC, datetime

from ..core.config import settings

logger = logging.getLogger(__name__)


class TokenBlacklistManager:
    """令牌黑名单管理器"""

    def __init__(self):
        self._blacklisted_tokens: set[str] = set()
        self._blacklist_expiry: dict[str, float] = {}
        self._cleanup_interval = 3600  # 1小时清理一次过期令牌
        self._last_cleanup = time.time()

    def add_token(self, jti: str, expires_at: float | datetime):
        """添加令牌到黑名单"""
        # 统一转换为时间戳
        if isinstance(expires_at, datetime):
            expiry_timestamp = expires_at.timestamp()
        else:
            expiry_timestamp = float(expires_at)

        # 如果令牌已经过期，无需添加
        if expiry_timestamp <= time.time():
            return

        self._blacklisted_tokens.add(jti)
        self._blacklist_expiry[jti] = expiry_timestamp

        # 定期清理过期令牌
        self._cleanup_expired_tokens()

    def is_blacklisted(self, jti: str) -> bool:
        """检查令牌是否在黑名单中"""
        # 定期清理过期令牌
        self._cleanup_expired_tokens()

        return jti in self._blacklisted_tokens

    def remove_token(self, jti: str):
        """从黑名单中移除令牌"""
        self._blacklisted_tokens.discard(jti)
        self._blacklist_expiry.pop(jti, None)

    def add_token_by_jti(self, jti: str, expires_in_seconds: int):
        """通过JTI和过期时间添加令牌到黑名单"""
        expires_at = time.time() + expires_in_seconds
        self.add_token(jti, expires_at)

    def revoke_all_user_tokens(self, user_id: str, token_patterns: list[str]):
        """撤销用户的所有令牌"""
        current_time = time.time()
        for pattern in token_patterns:
            # 为用户的令牌模式创建黑名单条目
            jti_pattern = f"{pattern}_{user_id}_*"
            # 设置较长的过期时间确保覆盖所有可能的令牌
            expiry_time = current_time + (
                settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
            )
            self._blacklisted_tokens.add(jti_pattern)
            self._blacklist_expiry[jti_pattern] = expiry_time

    def _cleanup_expired_tokens(self):
        """清理过期的令牌"""
        current_time = time.time()

        # 检查是否需要清理
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        # 清理过期令牌
        expired_tokens = [
            jti
            for jti, expiry in self._blacklist_expiry.items()
            if expiry <= current_time
        ]

        for jti in expired_tokens:
            self._blacklisted_tokens.discard(jti)
            self._blacklist_expiry.pop(jti, None)

        self._last_cleanup = current_time

        if expired_tokens:
            logger.info(f"清理了 {len(expired_tokens)} 个过期令牌")

    def get_blacklist_stats(self) -> dict:
        """获取黑名单统计信息"""
        self._cleanup_expired_tokens()

        return {
            "total_blacklisted": len(self._blacklisted_tokens),
            "expiry_count": len(self._blacklist_expiry),
            "last_cleanup": datetime.fromtimestamp(
                self._last_cleanup, tz=UTC
            ).isoformat(),
        }

    def clear_blacklist(self):
        """清空黑名单（谨慎使用）"""
        self._blacklisted_tokens.clear()
        self._blacklist_expiry.clear()

    def save_to_file(self, filepath: str):
        """保存黑名单到文件"""
        try:
            data = {
                "blacklisted_tokens": list(self._blacklisted_tokens),
                "blacklist_expiry": self._blacklist_expiry,
                "last_cleanup": self._last_cleanup,
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存黑名单到文件失败: {e}")

    def load_from_file(self, filepath: str):
        """从文件加载黑名单"""
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

            self._blacklisted_tokens = set(data.get("blacklisted_tokens", []))
            self._blacklist_expiry = data.get("blacklist_expiry", {})
            self._last_cleanup = data.get("last_cleanup", time.time())

            # 清理过期令牌
            self._cleanup_expired_tokens()

        except FileNotFoundError:
            logger.warning(f"黑名单文件不存在: {filepath}")
        except Exception as e:
            logger.error(f"从文件加载黑名单失败: {e}")


# 全局黑名单管理器实例
blacklist_manager = TokenBlacklistManager()


# 黑名单装饰器
def blacklist_token_on_revoke(revoke_func):
    """装饰器：在撤销令牌时自动添加到黑名单"""

    def wrapper(self, refresh_token: str, *args, **kwargs):
        # 先执行原有的撤销逻辑
        result = revoke_func(self, refresh_token, *args, **kwargs)

        # 解析令牌并添加到黑名单
        try:
            from jose import jwt

            from ..core.config import settings

            payload = jwt.decode(
                refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                blacklist_manager.add_token(jti, exp)

        except Exception as e:
            logger.error(f"添加令牌到黑名单失败: {e}")

        return result

    return wrapper


# 定期清理任务
async def periodic_cleanup():
    """定期清理过期令牌的后台任务"""
    import asyncio

    while True:
        try:
            blacklist_manager._cleanup_expired_tokens()
            await asyncio.sleep(3600)  # 每小时清理一次
        except Exception as e:
            logger.error(f"定期清理令牌黑名单时出错: {e}")
            await asyncio.sleep(300)  # 出错时等5分钟再重试


# 导出主要接口
__all__ = [
    "TokenBlacklistManager",
    "blacklist_manager",
    "blacklist_token_on_revoke",
    "periodic_cleanup",
]
