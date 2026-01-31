"""
JWT令牌黑名单管理器
用于管理被撤销的JWT令牌，防止令牌重放攻击
"""

import fnmatch
import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from ..core.cache_manager import RedisCache, cache_manager
from ..core.config import settings

logger = logging.getLogger(__name__)


class TokenBlacklistManager:
    """令牌黑名单管理器"""

    def __init__(self) -> None:
        self._blacklisted_tokens: set[str] = set()
        self._blacklist_expiry: dict[str, float] = {}
        self._revoked_users: dict[str, float] = {}
        self._cleanup_interval = 3600  # 1小时清理一次过期令牌
        self._last_cleanup = time.time()
        self._cache_namespace = "token_blacklist"
        self._use_cache = isinstance(cache_manager.backend, RedisCache)

    def _cache_key_token(self, jti: str) -> str:
        return f"token:{jti}"

    def _cache_key_user(self, user_id: str) -> str:
        return f"user:{user_id}"

    def add_token(self, jti: str, expires_at: float | datetime) -> None:
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

        if self._use_cache:
            ttl = max(0, int(expiry_timestamp - time.time()))
            if ttl > 0:
                cache_manager.set(
                    self._cache_key_token(jti),
                    True,
                    ttl=ttl,
                    namespace=self._cache_namespace,
                )

        # 定期清理过期令牌
        self._cleanup_expired_tokens()

    def is_blacklisted(
        self, jti: str | None = None, user_id: str | None = None
    ) -> bool:
        """检查令牌是否在黑名单中"""
        # 定期清理过期令牌
        self._cleanup_expired_tokens()

        # 用户级撤销优先
        if user_id and user_id in self._revoked_users:
            if self._revoked_users[user_id] > time.time():
                return True
            # 过期则移除
            self._revoked_users.pop(user_id, None)

        if self._use_cache and user_id:
            if cache_manager.exists(
                self._cache_key_user(user_id), namespace=self._cache_namespace
            ):
                return True

        if jti is None:
            return False

        # 直接命中
        if jti in self._blacklisted_tokens:
            return True

        # 支持通配符模式（兼容历史调用）
        for token in self._blacklisted_tokens:
            if "*" in token or "?" in token or "[" in token:
                if fnmatch.fnmatch(jti, token):
                    return True

        if self._use_cache:
            return cache_manager.exists(
                self._cache_key_token(jti), namespace=self._cache_namespace
            )

        return False

    def remove_token(self, jti: str) -> None:
        """从黑名单中移除令牌"""
        self._blacklisted_tokens.discard(jti)
        self._blacklist_expiry.pop(jti, None)
        if self._use_cache:
            cache_manager.delete(
                self._cache_key_token(jti), namespace=self._cache_namespace
            )

    def add_token_by_jti(self, jti: str, expires_in_seconds: int) -> None:
        """通过JTI和过期时间添加令牌到黑名单"""
        expires_at = time.time() + expires_in_seconds
        self.add_token(jti, expires_at)

    def revoke_all_user_tokens(
        self, user_id: str, token_patterns: list[str] | None = None
    ) -> None:
        """撤销用户的所有令牌"""
        current_time = time.time()
        # 设置较长的过期时间确保覆盖所有可能的令牌
        expiry_time = current_time + (settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)

        # 用户级撤销：访问令牌解析后可直接拒绝
        self._revoked_users[user_id] = expiry_time
        if self._use_cache:
            ttl = max(0, int(expiry_time - current_time))
            if ttl > 0:
                cache_manager.set(
                    self._cache_key_user(user_id),
                    True,
                    ttl=ttl,
                    namespace=self._cache_namespace,
                )

        # 兼容旧模式：如果提供了token_patterns，则继续记录模式
        for pattern in token_patterns or []:
            jti_pattern = f"{pattern}_{user_id}_*"
            self._blacklisted_tokens.add(jti_pattern)
            self._blacklist_expiry[jti_pattern] = expiry_time

    def _cleanup_expired_tokens(self) -> None:
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

        # 清理过期的用户撤销记录
        expired_users = [
            user_id
            for user_id, expiry in self._revoked_users.items()
            if expiry <= current_time
        ]
        for user_id in expired_users:
            self._revoked_users.pop(user_id, None)

        self._last_cleanup = current_time

        if expired_tokens:
            logger.info(f"清理了 {len(expired_tokens)} 个过期令牌")

    def get_blacklist_stats(self) -> dict[str, Any]:
        """获取黑名单统计信息"""
        self._cleanup_expired_tokens()

        return {
            "total_blacklisted": len(self._blacklisted_tokens),
            "expiry_count": len(self._blacklist_expiry),
            "revoked_users": len(self._revoked_users),
            "distributed_enabled": self._use_cache,
            "last_cleanup": datetime.fromtimestamp(
                self._last_cleanup, tz=UTC
            ).isoformat(),
        }

    def clear_blacklist(self) -> None:
        """清空黑名单（谨慎使用）"""
        self._blacklisted_tokens.clear()
        self._blacklist_expiry.clear()
        self._revoked_users.clear()
        if self._use_cache:
            cache_manager.clear(namespace=self._cache_namespace)

    def save_to_file(self, filepath: str) -> None:
        """保存黑名单到文件"""
        try:
            data = {
                "blacklisted_tokens": list(self._blacklisted_tokens),
                "blacklist_expiry": self._blacklist_expiry,
                "revoked_users": self._revoked_users,
                "last_cleanup": self._last_cleanup,
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存黑名单到文件失败: {e}")

    def load_from_file(self, filepath: str) -> None:
        """从文件加载黑名单"""
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

            self._blacklisted_tokens = set(data.get("blacklisted_tokens", []))
            self._blacklist_expiry = data.get("blacklist_expiry", {})
            self._revoked_users = data.get("revoked_users", {})
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
def blacklist_token_on_revoke(revoke_func: Callable[..., Any]) -> Callable[..., Any]:
    """装饰器：在撤销令牌时自动添加到黑名单"""

    def wrapper(self: Any, refresh_token: str, *args: Any, **kwargs: Any) -> Any:
        # 先执行原有的撤销逻辑
        result = revoke_func(self, refresh_token, *args, **kwargs)

        # 解析令牌并添加到黑名单
        try:
            import jwt

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
async def periodic_cleanup() -> None:
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
