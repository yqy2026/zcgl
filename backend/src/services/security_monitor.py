"""
实时安全监控服务
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum

from ..services.audit_service import get_audit_logger


class SecurityEventType(Enum):
    """安全事件类型"""
    LOGIN_ATTEMPT = "login_attempt"
    FAILED_LOGIN = "failed_login"
    SUCCESSFUL_LOGIN = "successful_login"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    HIGH_FREQUENCY_ACTIVITY = "high_frequency_activity"
    SUSPICIOUS_IP = "suspicious_ip"
    ANOMALY_DETECTED = "anomaly_detected"


@dataclass
class SecurityEvent:
    """安全事件数据类"""
    event_type: SecurityEventType
    timestamp: datetime
    user_id: Optional[str]
    username: Optional[str]
    ip_address: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Dict[str, Any]
    severity: str  # low, medium, high, critical


class RealTimeSecurityMonitor:
    """实时安全监控器"""
    
    def __init__(self, alert_thresholds: Optional[Dict] = None):
        self.logger = logging.getLogger("security_monitor")
        self.audit_logger = get_audit_logger()
        
        # 事件缓冲区（保存最近1000个事件）
        self.event_buffer = deque(maxlen=1000)
        
        # 用户活动跟踪
        self.user_activities = defaultdict(deque)
        
        # IP地址活动跟踪
        self.ip_activities = defaultdict(deque)
        
        # 告警阈值
        self.alert_thresholds = alert_thresholds or {
            "failed_logins_per_minute": 5,
            "requests_per_minute": 100,
            "concurrent_sessions": 5,
            "data_modifications_per_hour": 50
        }
        
        # 告警历史
        self.alert_history = deque(maxlen=100)
        
        # 启动监控任务
        self.monitoring_task = None
    
    async def start_monitoring(self):
        """启动实时监控"""
        self.logger.info("启动实时安全监控")
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self):
        """停止实时监控"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        self.logger.info("停止实时安全监控")
    
    async def _monitoring_loop(self):
        """监控循环"""
        while True:
            try:
                await self._check_for_anomalies()
                await self._cleanup_old_data()
                await asyncio.sleep(60)  # 每分钟检查一次
            except Exception as e:
                self.logger.error(f"监控循环出错: {e}")
                await asyncio.sleep(60)
    
    async def record_event(self, event: SecurityEvent):
        """记录安全事件"""
        # 添加到缓冲区
        self.event_buffer.append(event)
        
        # 更新用户活动跟踪
        if event.user_id:
            self.user_activities[event.user_id].append(event)
        
        # 更新IP活动跟踪
        if event.ip_address:
            self.ip_activities[event.ip_address].append(event)
        
        # 检查是否需要立即告警
        alert = self._check_immediate_alert(event)
        if alert:
            await self._send_alert(alert)
        
        # 记录到审计日志
        self.audit_logger.log_security_event(
            user_id=event.user_id,
            username=event.username,
            user_role=None,  # 可以从用户服务获取
            action=event.event_type.value,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            ip_address=event.ip_address,
            additional_data=event.details
        )
    
    def _check_immediate_alert(self, event: SecurityEvent) -> Optional[Dict[str, Any]]:
        """检查是否需要立即告警"""
        # 关键事件立即告警
        if event.severity == "critical":
            return {
                "type": "immediate_critical",
                "event": event,
                "timestamp": datetime.now(),
                "message": f"关键安全事件: {event.event_type.value}"
            }
        
        return None
    
    async def _check_for_anomalies(self):
        """检查异常行为"""
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        one_hour_ago = now - timedelta(hours=1)
        
        # 检查高频失败登录
        await self._check_failed_login_anomalies(one_minute_ago)
        
        # 检查高频请求
        await self._check_request_anomalies(one_minute_ago)
        
        # 检查异常用户行为
        await self._check_user_behavior_anomalies(one_hour_ago)
    
    async def _check_failed_login_anomalies(self, cutoff_time: datetime):
        """检查失败登录异常"""
        recent_failed_logins = [
            event for event in self.event_buffer
            if (event.event_type == SecurityEventType.FAILED_LOGIN and 
                event.timestamp > cutoff_time)
        ]
        
        if len(recent_failed_logins) > self.alert_thresholds["failed_logins_per_minute"]:
            alert = {
                "type": "high_failed_logins",
                "count": len(recent_failed_logins),
                "threshold": self.alert_thresholds["failed_logins_per_minute"],
                "timestamp": datetime.now(),
                "message": f"1分钟内检测到 {len(recent_failed_logins)} 次失败登录尝试"
            }
            await self._send_alert(alert)
    
    async def _check_request_anomalies(self, cutoff_time: datetime):
        """检查请求异常"""
        recent_requests = [
            event for event in self.event_buffer
            if event.timestamp > cutoff_time
        ]
        
        if len(recent_requests) > self.alert_thresholds["requests_per_minute"]:
            alert = {
                "type": "high_request_rate",
                "count": len(recent_requests),
                "threshold": self.alert_thresholds["requests_per_minute"],
                "timestamp": datetime.now(),
                "message": f"1分钟内检测到 {len(recent_requests)} 个请求"
            }
            await self._send_alert(alert)
    
    async def _check_user_behavior_anomalies(self, cutoff_time: datetime):
        """检查用户行为异常"""
        for user_id, activities in self.user_activities.items():
            recent_activities = [
                event for event in activities
                if event.timestamp > cutoff_time
            ]
            
            # 检查数据修改频率
            data_modifications = [
                event for event in recent_activities
                if event.event_type == SecurityEventType.DATA_MODIFICATION
            ]
            
            if len(data_modifications) > self.alert_thresholds["data_modifications_per_hour"]:
                alert = {
                    "type": "high_data_modifications",
                    "user_id": user_id,
                    "count": len(data_modifications),
                    "threshold": self.alert_thresholds["data_modifications_per_hour"],
                    "timestamp": datetime.now(),
                    "message": f"用户 {user_id} 1小时内修改了 {len(data_modifications)} 条数据"
                }
                await self._send_alert(alert)
    
    async def _send_alert(self, alert: Dict[str, Any]):
        """发送告警"""
        # 检查是否为重复告警
        if self._is_duplicate_alert(alert):
            return
        
        # 添加到告警历史
        alert["id"] = len(self.alert_history) + 1
        self.alert_history.append({
            "alert": alert,
            "timestamp": datetime.now()
        })
        
        # 记录告警日志
        self.logger.warning(f"安全告警 [{alert['type']}]: {alert['message']}")
        
        # 这里可以集成到外部告警系统（如邮件、短信、Slack等）
        # 暂时只记录日志
    
    def _is_duplicate_alert(self, alert: Dict[str, Any]) -> bool:
        """检查是否为重复告警"""
        alert_type = alert.get("type")
        recent_alerts = [
            item for item in self.alert_history
            if item["alert"].get("type") == alert_type and
            item["timestamp"] > datetime.now() - timedelta(minutes=5)
        ]
        return len(recent_alerts) > 0
    
    async def _cleanup_old_data(self):
        """清理旧数据"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # 清理事件缓冲区
        while self.event_buffer and self.event_buffer[0].timestamp < cutoff_time:
            self.event_buffer.popleft()
        
        # 清理用户活动
        for user_id in list(self.user_activities.keys()):
            while (self.user_activities[user_id] and 
                   self.user_activities[user_id][0].timestamp < cutoff_time):
                self.user_activities[user_id].popleft()
            
            if not self.user_activities[user_id]:
                del self.user_activities[user_id]
        
        # 清理IP活动
        for ip in list(self.ip_activities.keys()):
            while (self.ip_activities[ip] and 
                   self.ip_activities[ip][0].timestamp < cutoff_time):
                self.ip_activities[ip].popleft()
            
            if not self.ip_activities[ip]:
                del self.ip_activities[ip]
    
    def get_user_security_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户安全档案"""
        user_events = list(self.user_activities.get(user_id, []))
        
        if not user_events:
            return {"user_id": user_id, "risk_level": "unknown", "activity_count": 0}
        
        # 计算风险等级
        failed_logins = len([
            event for event in user_events 
            if event.event_type == SecurityEventType.FAILED_LOGIN
        ])
        
        data_modifications = len([
            event for event in user_events 
            if event.event_type == SecurityEventType.DATA_MODIFICATION
        ])
        
        unique_ips = len(set(
            event.ip_address for event in user_events 
            if event.ip_address
        ))
        
        # 简单的风险评估算法
        risk_score = 0
        if failed_logins > 10:
            risk_score += 2
        elif failed_logins > 5:
            risk_score += 1
            
        if unique_ips > 5:
            risk_score += 2
        elif unique_ips > 3:
            risk_score += 1
            
        if data_modifications > 100:
            risk_score += 2
        elif data_modifications > 50:
            risk_score += 1
        
        risk_levels = {0: "low", 1: "low", 2: "medium", 3: "medium", 4: "high"}
        risk_level = risk_levels.get(risk_score, "high")
        
        return {
            "user_id": user_id,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "activity_count": len(user_events),
            "failed_logins": failed_logins,
            "data_modifications": data_modifications,
            "unique_ips": unique_ips,
            "first_activity": min(event.timestamp for event in user_events).isoformat(),
            "last_activity": max(event.timestamp for event in user_events).isoformat()
        }
    
    def get_system_security_status(self) -> Dict[str, Any]:
        """获取系统安全状态"""
        total_events = len(self.event_buffer)
        failed_logins = len([
            event for event in self.event_buffer
            if event.event_type == SecurityEventType.FAILED_LOGIN
        ])
        
        active_users = len(self.user_activities)
        active_ips = len(self.ip_activities)
        
        # 计算最近1小时的活动
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_events = [
            event for event in self.event_buffer
            if event.timestamp > one_hour_ago
        ]
        
        return {
            "total_events": total_events,
            "failed_logins": failed_logins,
            "active_users": active_users,
            "active_ips": active_ips,
            "recent_events": len(recent_events),
            "alert_count": len(self.alert_history),
            "status": "normal" if len(recent_events) < 1000 else "high_load"
        }


# 全局实例
security_monitor = RealTimeSecurityMonitor()


async def get_security_monitor() -> RealTimeSecurityMonitor:
    """获取安全监控器实例"""
    return security_monitor