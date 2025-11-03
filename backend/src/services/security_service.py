"""
增强安全服务
提供密码策略、JWT管理、安全审计等高级安全功能
"""

import re
import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.auth import AuditLog, User, UserSession
from .auth_service import AuthService


class SecurityService:
    """增强安全服务"""

    def __init__(self, db: Session):
        self.db = db
        self.auth_service = AuthService(db)

    # ==================== 密码策略增强 ====================

    def validate_password_strength_advanced(self, password: str) -> Dict[str, Any]:
        """
        高级密码强度验证
        返回详细的验证结果
        """
        result = {"is_valid": True, "score": 0, "issues": [], "suggestions": []}

        # 长度检查
        if len(password) < settings.MIN_PASSWORD_LENGTH:
            result["is_valid"] = False
            result["issues"].append(f"密码长度不能少于{settings.MIN_PASSWORD_LENGTH}位")
        else:
            result["score"] += min(len(password) - settings.MIN_PASSWORD_LENGTH, 3)

        # 字符类型检查
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        char_types = [has_upper, has_lower, has_digit, has_special]
        char_type_count = sum(char_types)

        if char_type_count < 3:
            result["is_valid"] = False
            missing_types = []
            if not has_upper:
                missing_types.append("大写字母")
            if not has_lower:
                missing_types.append("小写字母")
            if not has_digit:
                missing_types.append("数字")
            if not has_special:
                missing_types.append("特殊字符")
            result["issues"].append(
                f"密码必须包含以下字符类型中的至少3种：{', '.join(missing_types)}"
            )
        else:
            result["score"] += char_type_count

        # 常见弱密码检查
        weak_passwords = [
            "123456",
            "password",
            "12345678",
            "qwerty",
            "abc123",
            "111111",
            "1234567890",
            "admin",
            "letmein",
            "welcome",
        ]

        if password.lower() in weak_passwords:
            result["is_valid"] = False
            result["issues"].append("不能使用常见弱密码")

        # 重复字符检查
        if len(set(password)) < len(password) * 0.6:
            result["suggestions"].append("建议增加字符多样性，避免过多重复字符")

        # 连续字符检查
        consecutive_pattern = re.compile(r"(.)\1{2,}")  # 3个或更多连续相同字符
        if consecutive_pattern.search(password):
            result["suggestions"].append("避免连续使用相同字符")

        # 键盘模式检查
        keyboard_patterns = ["qwerty", "asdf", "1234", "abcd"]
        password_lower = password.lower()
        for pattern in keyboard_patterns:
            if pattern in password_lower:
                result["suggestions"].append("避免使用键盘连续字符模式")
                break

        # 计算最终得分
        result["score"] = min(result["score"], 10)

        # 根据得分给出建议
        if result["score"] < 6:
            result["suggestions"].append("建议使用更复杂的密码组合")

        return result

    def generate_secure_password(self, length: int = 12) -> str:
        """
        生成安全密码
        """
        # 确保包含所有字符类型
        alphabet = (
            string.ascii_uppercase  # 大写字母
            + string.ascii_lowercase  # 小写字母
            + string.digits  # 数字
            + "!@#$%^&*()_+-=[]{}|;:,.<>?"  # 特殊字符
        )

        while True:
            password = "".join(secrets.choice(alphabet) for _ in range(length))

            # 验证生成的密码
            validation = self.validate_password_strength_advanced(password)
            if validation["is_valid"] and validation["score"] >= 8:
                return password

    # ==================== JWT管理增强 ====================

    def create_tokens_enhanced(
        self, user: User, device_info: dict | None = None
    ) -> Dict[str, Any]:
        """
        创建增强的JWT令牌
        """
        now = datetime.now(UTC)

        # 访问令牌 - 增加更多信息
        access_token_data = {
            "sub": user.id,
            "username": user.username,
            "role": user.role.value if hasattr(user.role, "value") else user.role,
            "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": now,
            "jti": secrets.token_urlsafe(32),  # JWT ID
            "session_id": secrets.token_urlsafe(16),
            "device_fingerprint": self._generate_device_fingerprint(device_info)
            if device_info
            else None,
        }

        access_token = jwt.encode(
            access_token_data, settings.SECRET_KEY, algorithm="HS256"
        )

        # 刷新令牌 - 增强安全性
        refresh_token_data = {
            "sub": user.id,
            "type": "refresh",
            "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": now,
            "jti": secrets.token_urlsafe(32),
            "session_id": access_token_data["session_id"],
            "device_fingerprint": access_token_data["device_fingerprint"],
        }

        refresh_token = jwt.encode(
            refresh_token_data, settings.SECRET_KEY, algorithm="HS256"
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "session_id": access_token_data["session_id"],
            "issued_at": now.isoformat(),
        }

    def _generate_device_fingerprint(self, device_info: dict) -> str:
        """
        生成设备指纹
        """
        import hashlib

        fingerprint_data = [
            device_info.get("user_agent", ""),
            device_info.get("ip_address", ""),
            device_info.get("device_id", ""),
            device_info.get("platform", ""),
        ]

        fingerprint_string = "|".join(filter(None, fingerprint_data))
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]

    def validate_token_enhanced(
        self, token: str, expected_type: str = "access"
    ) -> Dict[str, Any]:
        """
        增强的令牌验证
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

            # 基础验证
            if payload.get("type") != expected_type:
                return {"valid": False, "error": "令牌类型不匹配"}

            # 检查JWT ID是否在黑名单中
            jti = payload.get("jti")
            if self._is_token_blacklisted(jti):
                return {"valid": False, "error": "令牌已被撤销"}

            # 检查会话状态
            session_id = payload.get("session_id")
            if session_id and not self._is_session_active(session_id):
                return {"valid": False, "error": "会话已过期或被撤销"}

            return {
                "valid": True,
                "payload": payload,
                "user_id": payload.get("sub"),
                "username": payload.get("username"),
                "role": payload.get("role"),
                "session_id": session_id,
            }

        except JWTError as e:
            return {"valid": False, "error": f"令牌验证失败: {str(e)}"}

    def _is_token_blacklisted(self, jti: str) -> bool:
        """
        检查令牌是否在黑名单中
        """
        # 这里可以结合Redis或数据库实现黑名单
        # 暂时返回False，实际项目中需要实现
        return False

    def _is_session_active(self, session_id: str) -> bool:
        """
        检查会话是否活跃
        """
        session = (
            self.db.query(UserSession)
            .filter(UserSession.session_id == session_id, UserSession.is_active)
            .first()
        )

        return session is not None and not session.is_expired()

    # ==================== 账户安全增强 ====================

    def check_account_security(self, user: User) -> Dict[str, Any]:
        """
        检查账户安全状态
        """
        security_status = {"overall_score": 0, "issues": [], "recommendations": []}

        # 检查密码年龄
        if user.password_last_changed:
            days_since_change = (datetime.now() - user.password_last_changed).days
            if days_since_change > 90:
                security_status["issues"].append("密码超过90天未更改")
                security_status["recommendations"].append("建议定期更改密码")
            else:
                security_status["overall_score"] += 2
        else:
            security_status["issues"].append("密码最后更改时间未知")

        # 检查活跃会话
        active_sessions = (
            self.db.query(UserSession)
            .filter(UserSession.user_id == user.id, UserSession.is_active)
            .count()
        )

        if active_sessions > 3:
            security_status["issues"].append(f"活跃会话过多({active_sessions}个)")
            security_status["recommendations"].append("建议定期检查并撤销不活跃的会话")
        else:
            security_status["overall_score"] += 2

        # 检查登录失败次数
        if user.failed_login_attempts and user.failed_login_attempts > 0:
            security_status["issues"].append(
                f"最近有{user.failed_login_attempts}次登录失败"
            )
            security_status["recommendations"].append("建议检查是否有异常登录尝试")
        else:
            security_status["overall_score"] += 1

        # 检查账户锁定状态
        if user.is_locked:
            security_status["issues"].append("账户当前被锁定")
            security_status["recommendations"].append("请联系管理员解锁账户")
        else:
            security_status["overall_score"] += 1

        return security_status

    def handle_suspicious_activity(
        self, user: User, activity_type: str, details: dict
    ) -> bool:
        """
        处理可疑活动
        """
        # 记录安全事件
        self._log_security_event(user.id, activity_type, details)

        # 根据活动类型采取措施
        if activity_type == "multiple_failed_logins":
            # 多次登录失败
            if user.failed_login_attempts >= settings.MAX_FAILED_ATTEMPTS:
                self._lock_account(user, "自动锁定：多次登录失败")
                return True

        elif activity_type == "unusual_location":
            # 异常地点登录
            security_status = self.check_account_security(user)
            if len(security_status["issues"]) > 2:
                self._require_additional_verification(user)
                return True

        elif activity_type == "concurrent_sessions":
            # 并发会话异常
            self._revoke_old_sessions(user)
            return True

        return False

    def _log_security_event(self, user_id: str, event_type: str, details: dict):
        """
        记录安全事件
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=f"security_{event_type}",
            details=str(details),
            ip_address=details.get("ip_address"),
            user_agent=details.get("user_agent"),
            timestamp=datetime.now(),
        )

        self.db.add(audit_log)
        self.db.commit()

    def _lock_account(self, user: User, reason: str):
        """
        锁定账户
        """
        user.is_locked = True
        user.locked_until = datetime.now() + timedelta(
            seconds=settings.LOCKOUT_DURATION
        )
        user.lock_reason = reason

        self.db.commit()

        self._log_security_event(user.id, "account_locked", {"reason": reason})

    def _require_additional_verification(self, user: User):
        """
        要求额外验证
        """
        # 这里可以实现双因素认证或其他验证机制
        self._log_security_event(user.id, "additional_verification_required", {})

    def _revoke_old_sessions(self, user: User):
        """
        撤销旧会话
        """
        # 保留最近的3个会话，撤销其他的
        old_sessions = (
            self.db.query(UserSession)
            .filter(UserSession.user_id == user.id, UserSession.is_active)
            .order_by(UserSession.last_accessed_at.desc())
            .offset(3)
            .all()
        )

        for session in old_sessions:
            session.is_active = False

        self.db.commit()

        self._log_security_event(
            user.id, "old_sessions_revoked", {"count": len(old_sessions)}
        )

    # ==================== 安全审计 ====================

    def get_security_audit_log(
        self,
        user_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> List[dict]:
        """
        获取安全审计日志
        """
        query = self.db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)

        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        # 只返回安全相关的事件
        query = query.filter(
            AuditLog.action.like("security_%")
            | AuditLog.action.in_(
                ["login", "logout", "password_change", "account_locked"]
            )
        )

        query = query.order_by(AuditLog.timestamp.desc()).limit(limit)

        logs = []
        for log in query.all():
            logs.append(
                {
                    "timestamp": log.timestamp.isoformat(),
                    "user_id": log.user_id,
                    "action": log.action,
                    "details": log.details,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                }
            )

        return logs

    def generate_security_report(self, user_id: str | None = None) -> Dict[str, Any]:
        """
        生成安全报告
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        audit_logs = self.get_security_audit_log(
            user_id=user_id, start_date=start_date, end_date=end_date, limit=1000
        )

        report = {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_events": len(audit_logs),
                "failed_logins": len(
                    [log for log in audit_logs if "failed_login" in log["action"]]
                ),
                "account_locks": len(
                    [log for log in audit_logs if log["action"] == "account_locked"]
                ),
                "suspicious_activities": len(
                    [log for log in audit_logs if "suspicious" in log["action"]]
                ),
            },
            "recent_events": audit_logs[:10],
        }

        if user_id:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                report["account_status"] = self.check_account_security(user)

        return report
