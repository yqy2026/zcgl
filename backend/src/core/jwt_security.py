"""
JWT安全配置和最佳实践
集中管理JWT相关的安全设置和验证逻辑
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt

from ..config import settings

logger = logging.getLogger(__name__)


class JWTSecurityConfig:
    """JWT安全配置类"""

    # JWT安全最佳实践配置
    MIN_SECRET_KEY_LENGTH = 32  # 最小密钥长度
    MAX_TOKEN_LIFETIME = timedelta(hours=1)  # 最大token有效期
    DEFAULT_ACCESS_TOKEN_LIFETIME = timedelta(minutes=30)  # 默认访问token有效期
    DEFAULT_REFRESH_TOKEN_LIFETIME = timedelta(days=7)  # 默认刷新token有效期

    # 推荐的JWT算法（按安全性排序）
    RECOMMENDED_ALGORITHMS = [
        "HS256",  # HMAC-SHA256 (当前使用)
        "HS384",  # HMAC-SHA384
        "HS512",  # HMAC-SHA512
    ]

    @classmethod
    def validate_secret_key(cls, secret_key: str) -> dict[str, Any]:
        """
        验证JWT密钥安全性

        Returns:
            dict: 验证结果包含is_valid, issues, suggestions
        """
        result = {
            "is_valid": True,
            "issues": [],
            "suggestions": [],
            "strength_score": 0,
        }

        # 检查长度
        if len(secret_key) < cls.MIN_SECRET_KEY_LENGTH:
            result["is_valid"] = False
            result["issues"].append(f"密钥长度不足{cls.MIN_SECRET_KEY_LENGTH}字符")
        else:
            result["strength_score"] += min(
                len(secret_key) - cls.MIN_SECRET_KEY_LENGTH, 3
            )

        # 检查是否为默认密钥
        default_keys = [
            "EMERGENCY-ONLY-REPLACE-WITH-ENV-SECRET-KEY-NOW",
            "dev-secret-key-DO-NOT-USE-IN-PRODUCTION-REPLACE-WITH-ENV-VAR",
            "dev-secret-key-change-in-production",
            "your-secret-key-change-in-production",
            "secret-key",
        ]

        if secret_key in default_keys:
            result["is_valid"] = False
            result["issues"].append("使用了默认或不安全的密钥")

        # 检查字符复杂度
        has_upper = any(c.isupper() for c in secret_key)
        has_lower = any(c.islower() for c in secret_key)
        has_digit = any(c.isdigit() for c in secret_key)
        has_special = any(c in "-._~" for c in secret_key)

        complexity_score = sum([has_upper, has_lower, has_digit, has_special])
        result["strength_score"] += complexity_score

        if complexity_score < 3:
            result["suggestions"].append("建议使用包含大小写字母、数字和特殊字符的密钥")

        # 检查是否为常见弱密钥
        weak_patterns = ["123", "abc", "test", "dev", "password", "secret"]
        if any(pattern in secret_key.lower() for pattern in weak_patterns):
            result["is_valid"] = False
            result["issues"].append("密钥包含常见的弱模式")

        return result

    @classmethod
    def generate_secure_secret(cls) -> str:
        """生成安全的JWT密钥"""
        return secrets.token_urlsafe(32)

    @classmethod
    def create_token_with_claims(
        cls, payload: dict[str, Any], token_type: str = "access"
    ) -> str:
        """
        创建包含标准声明和自定义声明的JWT令牌

        Args:
            payload: 自定义payload
            token_type: 令牌类型 (access/refresh)

        Returns:
            JWT令牌字符串
        """
        now = datetime.now(UTC)

        # 根据令牌类型设置过期时间
        if token_type == "access":
            expire_time = now + cls.DEFAULT_ACCESS_TOKEN_LIFETIME
        elif token_type == "refresh":
            expire_time = now + cls.DEFAULT_REFRESH_TOKEN_LIFETIME
        else:
            expire_time = now + cls.DEFAULT_ACCESS_TOKEN_LIFETIME

        # 标准声明
        standard_claims = {
            "iat": now,  # 签发时间
            "exp": expire_time,  # 过期时间
            "jti": secrets.token_urlsafe(32),  # JWT ID
            "type": token_type,  # 令牌类型
        }

        # 合并标准声明和自定义声明
        full_payload = {**standard_claims, **payload}

        # 创建令牌
        token = jwt.encode(
            full_payload, settings.SECRET_KEY, algorithm=getattr(settings, 'ALGORITHM', 'HS256')
        )

        logger.debug(f"Created {token_type} token with JTI: {full_payload['jti']}")
        return token

    @classmethod
    def verify_token_enhanced(cls, token: str) -> dict[str, Any]:
        """
        增强的JWT令牌验证

        Args:
            token: JWT令牌字符串

        Returns:
            验证结果和payload

        Raises:
            JWTError: 令牌无效
        """
        try:
            # 解码令牌
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[getattr(settings, 'ALGORITHM', 'HS256')]
            )

            # 验证标准声明
            now = datetime.now(UTC)

            # 检查过期时间
            exp = payload.get("exp")
            if exp is None:
                raise jwt.JWTError("Token missing expiration time")

            exp_datetime = datetime.fromtimestamp(exp, UTC)
            if exp_datetime <= now:
                raise jwt.JWTError("Token has expired")

            # 检查签发时间
            iat = payload.get("iat")
            if iat is None:
                raise jwt.JWTError("Token missing issued at time")

            # 检查令牌类型
            token_type = payload.get("type")
            if token_type not in ["access", "refresh"]:
                logger.warning(f"Unknown token type: {token_type}")

            # 检查JWT ID
            jti = payload.get("jti")
            if jti is None:
                logger.warning("Token missing JWT ID (jti)")

            return {
                "valid": True,
                "payload": payload,
                "token_type": token_type,
                "expires_at": exp_datetime,
                "jti": jti,
            }

        except jwt.ExpiredSignatureError:
            raise jwt.JWTError("Token has expired")
        except jwt.JWTError as e:
            raise jwt.JWTError(f"Token validation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {e}")
            raise jwt.JWTError("Token verification failed")

    @classmethod
    def get_token_security_info(cls, token: str) -> dict[str, Any]:
        """
        获取令牌的安全信息（不验证签名，仅解析）

        Args:
            token: JWT令牌字符串

        Returns:
            令牌安全信息
        """
        try:
            # 不验证签名，仅解析payload - 需要提供key参数
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                options={"verify_signature": False, "verify_exp": False},
                algorithms=[getattr(settings, 'ALGORITHM', 'HS256')]
            )

            now = datetime.now(UTC)
            exp = payload.get("exp")
            iat = payload.get("iat")
            jti = payload.get("jti")
            token_type = payload.get("type")

            security_info = {
                "has_jti": jti is not None,
                "has_exp": exp is not None,
                "has_iat": iat is not None,
                "has_type": token_type is not None,
                "token_type": token_type,
                "jti": jti,
            }

            if exp:
                exp_datetime = datetime.fromtimestamp(exp, UTC)
                security_info["expires_at"] = exp_datetime
                security_info["is_expired"] = exp_datetime <= now
                security_info["time_to_expiry"] = exp_datetime - now

            if iat:
                iat_datetime = datetime.fromtimestamp(iat, UTC)
                security_info["issued_at"] = iat_datetime
                security_info["token_age"] = now - iat_datetime

            return security_info

        except Exception as e:
            return {"error": str(e), "parse_failed": True}


# 创建全局实例
jwt_security = JWTSecurityConfig()


def validate_current_jwt_config() -> dict[str, Any]:
    """
    验证当前JWT配置的安全性

    Returns:
        配置验证结果
    """
    result = {
        "config_valid": True,
        "issues": [],
        "recommendations": [],
        "secret_key_analysis": jwt_security.validate_secret_key(settings.SECRET_KEY),
    }

    # 检查算法 - 使用安全访问避免属性错误
    algorithm = getattr(settings, 'ALGORITHM', 'HS256')
    if algorithm not in jwt_security.RECOMMENDED_ALGORITHMS:
        result["issues"].append(f"使用的算法 {algorithm} 不在推荐列表中")

    # 检查令牌有效期 - 使用安全访问避免属性错误
    access_token_minutes = getattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30)
    if access_token_minutes > 60:  # 超过1小时
        result["recommendations"].append("访问令牌有效期建议不超过60分钟")

    if access_token_minutes < 5:  # 少于5分钟
        result["recommendations"].append("访问令牌有效期建议不少于5分钟")

    # 综合评估
    if not result["secret_key_analysis"]["is_valid"]:
        result["config_valid"] = False
        result["issues"].extend(result["secret_key_analysis"]["issues"])

    result["recommendations"].extend(result["secret_key_analysis"]["suggestions"])

    return result
