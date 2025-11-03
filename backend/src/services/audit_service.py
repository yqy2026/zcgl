from typing import Any
"""
增强审计日志服务
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta


from ..core.config import settings
from ..database import SessionLocal
from ..models.auth import AuditLog


class EnhancedAuditLogger:
    """增强审计日志服务"""

    def __init__(self):
        self.logger = logging.getLogger("audit")
        self.session = SessionLocal()
        # 存储实时监控数据
        self.security_events = defaultdict(list)
        self.user_activity = defaultdict(list)

    def log_security_event(
        self,
        user_id: str | None,
        username: str | None,
        user_role: str | None,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        resource_name: str | None = None,
        api_endpoint: str | None = None,
        http_method: str | None = None,
        request_params: str | None = None,
        request_body: str | None = None,
        response_status: int | None = None,
        response_message: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> AuditLog | None:
        """记录安全事件"""
        try:
            # 记录到数据库
            audit_log = AuditLog(
                user_id=user_id or "",
                username=username or "anonymous",
                user_role=user_role or "",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                api_endpoint=api_endpoint,
                http_method=http_method,
                request_params=request_params,
                request_body=request_body,
                response_status=response_status,
                response_message=response_message,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
            )

            self.session.add(audit_log)
            self.session.commit()
            self.session.refresh(audit_log)

            # 记录到文件日志
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "username": username,
                "action": action,
                "resource_type": resource_type,
                "api_endpoint": api_endpoint,
                "http_method": http_method,
                "ip_address": ip_address,
                "response_status": response_status,
                "additional_data": additional_data,
            }

            self.logger.info(
                f"Security Event: {json.dumps(log_data, ensure_ascii=False)}"
            )

            # 存储到实时监控缓存
            event_data = {
                "timestamp": datetime.now(),
                "user_id": user_id,
                "username": username,
                "action": action,
                "ip_address": ip_address,
                "resource_type": resource_type,
            }

            self.security_events[action].append(event_data)
            if user_id:
                self.user_activity[user_id].append(event_data)

            # 清理过期的监控数据
            self._cleanup_expired_events()

            return audit_log

        except Exception as e:
            self.logger.error(f"记录安全事件失败: {e}")
            self.session.rollback()
            return None

    def _cleanup_expired_events(self):
        """清理过期的监控数据"""
        cutoff_time = datetime.now() - timedelta(hours=24)

        # 清理安全事件
        for action in list(self.security_events.keys()):
            self.security_events[action] = [
                event
                for event in self.security_events[action]
                if event["timestamp"] > cutoff_time
            ]
            if not self.security_events[action]:
                del self.security_events[action]

        # 清理用户活动
        for user_id in list(self.user_activity.keys()):
            self.user_activity[user_id] = [
                event
                for event in self.user_activity[user_id]
                if event["timestamp"] > cutoff_time
            ]
            if not self.user_activity[user_id]:
                del self.user_activity[user_id]

    def get_user_activity_summary(
        self, user_id: str, hours: int = 24
    ) -> dict[str, Any]:
        """获取用户活动摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        user_events = [
            event
            for event in self.user_activity.get(user_id, [])
            if event["timestamp"] > cutoff_time
        ]

        action_counts = defaultdict(int)
        for event in user_events:
            action_counts[event["action"]] += 1

        return {
            "user_id": user_id,
            "total_events": len(user_events),
            "time_range_hours": hours,
            "action_counts": dict(action_counts),
            "unique_ips": len(
                set(event["ip_address"] for event in user_events if event["ip_address"])
            ),
            "most_active_resource": self._get_most_active_resource(user_events),
        }

    def _get_most_active_resource(self, events: list[dict]) -> str | None:
        """获取最活跃的资源类型"""
        resource_counts = defaultdict(int)
        for event in events:
            if event["resource_type"]:
                resource_counts[event["resource_type"]] += 1

        if resource_counts:
            return max(resource_counts.items(), key=lambda x: x[1])[0]
        return None

    def detect_suspicious_activity(self, user_id: str) -> list[dict[str, Any]]:
        """检测可疑活动"""
        suspicious_events = []
        user_events = self.user_activity.get(user_id, [])

        if not user_events:
            return suspicious_events

        # 检测1: 短时间内大量操作
        recent_events = [
            event
            for event in user_events
            if event["timestamp"] > datetime.now() - timedelta(minutes=5)
        ]

        if len(recent_events) > 50:  # 5分钟内超过50次操作
            suspicious_events.append(
                {
                    "type": "high_frequency_activity",
                    "description": f"用户 {user_id} 在5分钟内执行了 {len(recent_events)} 次操作",
                    "severity": "medium",
                    "timestamp": datetime.now(),
                }
            )

        # 检测2: 异常时间登录
        login_events = [
            event for event in user_events if event["action"] in ["user_login", "login"]
        ]

        for event in login_events:
            hour = event["timestamp"].hour
            if hour >= 2 and hour <= 5:  # 凌晨2-5点登录
                suspicious_events.append(
                    {
                        "type": "unusual_login_time",
                        "description": f"用户 {user_id} 在异常时间({hour}点)登录",
                        "severity": "low",
                        "timestamp": event["timestamp"],
                    }
                )

        # 检测3: 多IP登录
        unique_ips = set(
            event["ip_address"] for event in user_events if event["ip_address"]
        )
        if len(unique_ips) > 3:  # 24小时内使用超过3个不同IP
            suspicious_events.append(
                {
                    "type": "multiple_ips",
                    "description": f"用户 {user_id} 在24小时内使用了 {len(unique_ips)} 个不同IP地址",
                    "severity": "medium",
                    "timestamp": datetime.now(),
                }
            )

        return suspicious_events

    def get_security_statistics(self, days: int = 30) -> dict[str, Any]:
        """获取安全统计信息"""
        cutoff_date = datetime.now() - timedelta(days=days)

        # 查询数据库获取统计信息
        total_logs = (
            self.session.query(AuditLog)
            .filter(AuditLog.created_at >= cutoff_date)
            .count()
        )

        failed_logins = (
            self.session.query(AuditLog)
            .filter(
                AuditLog.action == "user_login_failed",
                AuditLog.created_at >= cutoff_date,
            )
            .count()
        )

        successful_logins = (
            self.session.query(AuditLog)
            .filter(AuditLog.action == "user_login", AuditLog.created_at >= cutoff_date)
            .count()
        )

        # 获取活跃用户数
        active_users = (
            self.session.query(AuditLog.user_id)
            .filter(AuditLog.created_at >= cutoff_date)
            .distinct()
            .count()
        )

        return {
            "period_days": days,
            "total_logs": total_logs,
            "failed_logins": failed_logins,
            "successful_logins": successful_logins,
            "login_success_rate": successful_logins
            / (successful_logins + failed_logins)
            if (successful_logins + failed_logins) > 0
            else 0,
            "active_users": active_users,
            "average_daily_logs": total_logs / days if days > 0 else 0,
        }

    def cleanup_old_logs(self, retention_days: int | None = None) -> int:
        """清理旧日志"""
        if retention_days is None:
            retention_days = settings.AUDIT_LOG_RETENTION_DAYS

        cutoff_date = datetime.now() - timedelta(days=retention_days)

        deleted_count = (
            self.session.query(AuditLog)
            .filter(AuditLog.created_at < cutoff_date)
            .delete()
        )

        self.session.commit()

        self.logger.info(f"清理了 {deleted_count} 条超过 {retention_days} 天的审计日志")
        return deleted_count

    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()


# 创建全局实例
audit_logger = EnhancedAuditLogger()


def get_audit_logger() -> EnhancedAuditLogger:
    """获取审计日志服务实例"""
    return audit_logger
