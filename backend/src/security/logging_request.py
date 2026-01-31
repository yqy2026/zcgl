"""
Request logging helpers.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .logging_filters import SensitiveDataFilter


class RequestLogger:
    """请求日志记录器"""

    def __init__(self) -> None:
        self.log_file = "logs/request.log"
        self.enabled = True
        self._setup_logger()
        self.sensitive_filter = SensitiveDataFilter()

    def _setup_logger(self) -> None:
        """设置请求日志记录器"""
        self.logger = logging.getLogger("request_logger")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            log_dir = Path(self.log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)
            file_handler.addFilter(SensitiveDataFilter())

            self.logger.addHandler(file_handler)

    def log_request(self, **kwargs: Any) -> None:
        """记录请求信息"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_request_metrics(self, metrics: dict[str, Any]) -> None:
        """记录请求性能指标"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "metrics": metrics,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_exception(
        self, exception: Exception, context: dict[str, Any] | None = None
    ) -> None:
        """记录异常信息"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "exception": str(exception),
            "exception_type": type(exception).__name__,
            "context": context or {},
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.error(json.dumps(filtered_entry, ensure_ascii=False))

    def log_security_warning(self, warning: str, **kwargs: Any) -> None:
        """记录安全警告"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "warning": warning,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.warning(json.dumps(filtered_entry, ensure_ascii=False))

    def log_security_error(self, error: str, **kwargs: Any) -> None:
        """记录安全错误"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "error": error,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.error(json.dumps(filtered_entry, ensure_ascii=False))

    def log_security_audit(self, action: str, **kwargs: Any) -> None:
        """记录安全审计日志"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_system_event(self, event: str, **kwargs: Any) -> None:
        """记录系统事件"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_performance_metrics(self, metrics: dict[str, Any]) -> None:
        """记录性能指标"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "performance": metrics,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_user_action(self, user_id: str, action: str, **kwargs: Any) -> None:
        """记录用户操作"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "action": action,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_data_access(
        self, user_id: str, resource: str, action: str, **kwargs: Any
    ) -> None:
        """记录数据访问"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "resource": resource,
            "action": action,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_authentication_event(self, user_id: str, event: str, **kwargs: Any) -> None:
        """记录认证事件"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "event": event,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_security_scan(self, scan_type: str, result: str, **kwargs: Any) -> None:
        """记录安全扫描"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "scan_type": scan_type,
            "result": result,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_data_validation(
        self, validation_type: str, result: str, **kwargs: Any
    ) -> None:
        """记录数据验证"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "validation_type": validation_type,
            "result": result,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_audit_trail(self, action: str, details: dict[str, Any]) -> None:
        """记录审计轨迹"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "details": details,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_user_session(self, user_id: str, session_id: str, **kwargs: Any) -> None:
        """记录用户会话"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "session_id": session_id,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_api_access(
        self, endpoint: str, method: str, status_code: int, **kwargs: Any
    ) -> None:
        """记录API访问"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_rate_limit(self, key: str, limit: int, current: int, **kwargs: Any) -> None:
        """记录限流信息"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "key": key,
            "limit": limit,
            "current": current,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_permission_denied(
        self, user_id: str, permission: str, **kwargs: Any
    ) -> None:
        """记录权限拒绝"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "permission": permission,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_auth_failure(self, username: str, **kwargs: Any) -> None:
        """记录认证失败"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "username": username,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.warning(json.dumps(filtered_entry, ensure_ascii=False))

    def log_access_denied(self, resource: str, **kwargs: Any) -> None:
        """记录访问拒绝"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "resource": resource,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.warning(json.dumps(filtered_entry, ensure_ascii=False))

    def log_password_reset(self, user_id: str, **kwargs: Any) -> None:
        """记录密码重置"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_password_change(self, user_id: str, **kwargs: Any) -> None:
        """记录密码变更"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_device_registration(
        self, user_id: str, device_id: str, **kwargs: Any
    ) -> None:
        """记录设备注册"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "device_id": device_id,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_login_attempt(self, username: str, success: bool, **kwargs: Any) -> None:
        """记录登录尝试"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "username": username,
            "success": success,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_logout(self, user_id: str, **kwargs: Any) -> None:
        """记录登出"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_token_refresh(self, user_id: str, **kwargs: Any) -> None:
        """记录令牌刷新"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_role_change(
        self, user_id: str, old_role: str, new_role: str, **kwargs: Any
    ) -> None:
        """记录角色变更"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "old_role": old_role,
            "new_role": new_role,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_permission_change(
        self, user_id: str, permission: str, granted: bool, **kwargs: Any
    ) -> None:
        """记录权限变更"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "permission": permission,
            "granted": granted,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_audit_export(self, user_id: str, **kwargs: Any) -> None:
        """记录审计导出"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_system_start(self, version: str, **kwargs: Any) -> None:
        """记录系统启动"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "version": version,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_system_shutdown(self, reason: str, **kwargs: Any) -> None:
        """记录系统关闭"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "reason": reason,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_database_error(self, error: str, **kwargs: Any) -> None:
        """记录数据库错误"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "error": error,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.error(json.dumps(filtered_entry, ensure_ascii=False))

    def log_external_service_error(
        self, service: str, error: str, **kwargs: Any
    ) -> None:
        """记录外部服务错误"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "service": service,
            "error": error,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.error(json.dumps(filtered_entry, ensure_ascii=False))

    def log_file_upload(
        self, user_id: str, file_name: str, file_size: int, **kwargs: Any
    ) -> None:
        """记录文件上传"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "file_name": file_name,
            "file_size": file_size,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_file_download(self, user_id: str, file_name: str, **kwargs: Any) -> None:
        """记录文件下载"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "file_name": file_name,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_file_delete(self, user_id: str, file_name: str, **kwargs: Any) -> None:
        """记录文件删除"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "file_name": file_name,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_data_export(self, user_id: str, export_type: str, **kwargs: Any) -> None:
        """记录数据导出"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "export_type": export_type,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_data_import(self, user_id: str, import_type: str, **kwargs: Any) -> None:
        """记录数据导入"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "import_type": import_type,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_data_update(self, user_id: str, resource: str, **kwargs: Any) -> None:
        """记录数据更新"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "resource": resource,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_data_delete(self, user_id: str, resource: str, **kwargs: Any) -> None:
        """记录数据删除"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "resource": resource,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_configuration_change(
        self, user_id: str, setting: str, **kwargs: Any
    ) -> None:
        """记录配置变更"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "setting": setting,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_system_health(self, status: str, **kwargs: Any) -> None:
        """记录系统健康状态"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "status": status,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_backup_event(self, result: str, **kwargs: Any) -> None:
        """记录备份事件"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "result": result,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_restore_event(self, result: str, **kwargs: Any) -> None:
        """记录恢复事件"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "result": result,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_custom_event(self, event_type: str, message: str, **kwargs: Any) -> None:
        """记录自定义事件"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "message": message,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_security_settings(self, settings_data: dict[str, Any]) -> None:
        """记录安全设置"""
        if not self.enabled:
            return

        filtered_data = self.sensitive_filter.filter_dict(settings_data)
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "settings": filtered_data,
        }

        self.logger.info(json.dumps(log_entry, ensure_ascii=False))

    def log_data_anomaly(self, anomaly_type: str, details: dict[str, Any]) -> None:
        """记录数据异常"""
        if not self.enabled:
            return

        filtered_details = self.sensitive_filter.filter_dict(details)
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "anomaly_type": anomaly_type,
            "details": filtered_details,
        }

        self.logger.warning(json.dumps(log_entry, ensure_ascii=False))

    def log_security_scan_result(
        self, scan_type: str, result: str, **kwargs: Any
    ) -> None:
        """记录安全扫描结果"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "scan_type": scan_type,
            "result": result,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_access_attempt(
        self, user_id: str, resource: str, success: bool, **kwargs: Any
    ) -> None:
        """记录访问尝试"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "resource": resource,
            "success": success,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_suspicious_activity(
        self, ip_address: str, reason: str, **kwargs: Any
    ) -> None:
        """记录可疑活动"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "ip_address": ip_address,
            "reason": reason,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.warning(json.dumps(filtered_entry, ensure_ascii=False))

    def log_system_metric(self, name: str, value: float, **kwargs: Any) -> None:
        """记录系统指标"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "metric_name": name,
            "metric_value": value,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_application_event(self, event_name: str, **kwargs: Any) -> None:
        """记录应用事件"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_name": event_name,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_resource_access(
        self, user_id: str, resource_type: str, resource_id: str, **kwargs: Any
    ) -> None:
        """记录资源访问"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_data_change(
        self, user_id: str, table: str, action: str, **kwargs: Any
    ) -> None:
        """记录数据变更"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "table": table,
            "action": action,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_permission_grant(
        self, user_id: str, permission: str, **kwargs: Any
    ) -> None:
        """记录权限授予"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "permission": permission,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_permission_revoke(
        self, user_id: str, permission: str, **kwargs: Any
    ) -> None:
        """记录权限撤销"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "permission": permission,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_error_response(
        self, status_code: int, error_code: str, **kwargs: Any
    ) -> None:
        """记录错误响应"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "status_code": status_code,
            "error_code": error_code,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_rate_limit_hit(self, key: str, **kwargs: Any) -> None:
        """记录限流触发"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "key": key,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.warning(json.dumps(filtered_entry, ensure_ascii=False))

    def log_security_configuration(self, config: dict[str, Any]) -> None:
        """记录安全配置"""
        if not self.enabled:
            return

        filtered_config = self.sensitive_filter.filter_dict(config)
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "config": filtered_config,
        }

        self.logger.info(json.dumps(log_entry, ensure_ascii=False))

    def log_abnormal_request(self, request_info: dict[str, Any]) -> None:
        """记录异常请求"""
        if not self.enabled:
            return

        filtered_info = self.sensitive_filter.filter_dict(request_info)
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "request": filtered_info,
        }

        self.logger.warning(json.dumps(log_entry, ensure_ascii=False))

    def log_user_lockout(self, user_id: str, reason: str, **kwargs: Any) -> None:
        """记录用户锁定"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "reason": reason,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.warning(json.dumps(filtered_entry, ensure_ascii=False))

    def log_suspicious_login(self, username: str, reason: str, **kwargs: Any) -> None:
        """记录可疑登录"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "username": username,
            "reason": reason,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.warning(json.dumps(filtered_entry, ensure_ascii=False))

    def log_token_revocation(self, user_id: str, token_id: str, **kwargs: Any) -> None:
        """记录令牌撤销"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "token_id": token_id,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_sensitive_operation(
        self, user_id: str, operation: str, **kwargs: Any
    ) -> None:
        """记录敏感操作"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "operation": operation,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))

    def log_data_breach(self, incident: str, **kwargs: Any) -> None:
        """记录数据泄露事件"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "incident": incident,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.error(json.dumps(filtered_entry, ensure_ascii=False))

    def log_policy_violation(self, policy: str, **kwargs: Any) -> None:
        """记录策略违规"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "policy": policy,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.warning(json.dumps(filtered_entry, ensure_ascii=False))

    def log_security_metric(self, metric: str, value: float, **kwargs: Any) -> None:
        """记录安全指标"""
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "metric": metric,
            "value": value,
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))
