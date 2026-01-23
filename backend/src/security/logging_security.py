from typing import Any

"""
安全日志记录器
提供敏感信息脱敏、结构化日志和安全审计功能
"""

import json
import logging
import re
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from ..core.config import get_config


class SensitiveDataFilter(logging.Filter):
    """敏感数据过滤器"""

    def __init__(self) -> None:
        super().__init__()
        self.sensitive_patterns = [
            # 密码相关
            (r"(?i)(password|pwd|pass)\s*[:=]\s*[^\s,}]+", "password=***"),
            (r"(?i)(token|jwt)\s*[:=]\s*[^\s,}]+", "token=***"),
            (r"(?i)(secret|key)\s*[:=]\s*[^\s,}]+", "secret=***"),
            # 个人信息
            (r"(?i)(email|mail)\s*[:=]\s*[^\s,}]+@", "email=***@"),
            (r"(?i)(phone|mobile|tel)\s*[:=]\s*[0-9\-\s\(\)]{10,}", "phone=***"),
            (r"(?i)(idcard|身份证)\s*[:=]\s*[0-9]{15,}", "idcard=***"),
            # 身份证号码（15位或18位）
            (
                r"\b[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b",
                "idcard=***",
            ),
            (r"\b[1-9]\d{7}(0[1-9]|1[0-2])\d{4}\b", "idcard=***"),
            # 手机号码
            (r"\b1[3-9]\d{9}\b", "phone=***"),
            # 银行卡号
            (r"\b[1-9]\d{12,19}\b", "card=***"),
            # IP地址
            (r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", "ip=***"),
            # URL中的敏感参数
            (r"(?i)(token|key|secret)=[^&\s]+", r"\1=***"),
            # 地址信息
            (r"(?i)(address|addr)\s*[:=]\s*[^,}]+", "address=***"),
            # 银行账户信息
            (r"(?i)(account|acct)\s*[:=]\s*[^\s,}]+", "account=***"),
            # 生日信息
            (r"(?i)(birthday|dob)\s*[:=]\s*[^\s,}]+", "birthday=***"),
            # 更多敏感信息模式
            (r"(?i)(username|user)\s*[:=]\s*[^\s,}]+", "username=***"),
            (r"(?i)(name)\s*[:=]\s*[^\s,}]+", "name=***"),
            (r"(?i)(realname|real_name)\s*[:=]\s*[^\s,}]+", "realname=***"),
            (r"(?i)(nickname|nick_name)\s*[:=]\s*[^\s,}]+", "nickname=***"),
        ]

        # 敏感字段名称列表
        self.sensitive_fields = {
            "password",
            "pwd",
            "passwd",
            "pass",
            "token",
            "jwt",
            "access_token",
            "refresh_token",
            "secret",
            "secret_key",
            "private_key",
            "api_key",
            "credit_card",
            "card_number",
            "cc_number",
            "ssn",
            "social_security_number",
            "bank_account",
            "account_number",
            "email_address",
            "email",
            "phone_number",
            "mobile",
            "telephone",
            "id_card",
            "idcard",
            "identity_card",
            "user_id",
            "user_id_hash",
            "session_id",
            "session_token",
            "address",
            "addr",
            "birthday",
            "dob",
            "account",
            "acct",
            "ip",
            "ip_address",
            "username",
            "user",
            "name",
            "realname",
            "real_name",
            "nickname",
            "nick_name",
            "full_name",
            "fullname",
        }

    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        """过滤敏感信息"""
        if hasattr(record, "msg"):
            record.msg = self._filter_sensitive_data(str(record.msg))

        if hasattr(record, "args") and record.args is not None:
            record.args = tuple(
                self._filter_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )

        return record

    def _filter_sensitive_data(self, text: str) -> str:
        """过滤文本中的敏感信息"""
        if not text:
            return text

        filtered_text = text

        # 应用正则模式过滤
        for pattern, replacement in self.sensitive_patterns:
            filtered_text = re.sub(
                pattern, replacement, filtered_text, flags=re.IGNORECASE
            )

        return filtered_text

    def _is_sensitive_key(self, key: str) -> bool:
        return key.lower() in self.sensitive_fields

    def filter_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """过滤字典中的敏感数据"""
        if not isinstance(data, dict):
            return data

        filtered_data: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(key, str) and key.lower() in self.sensitive_fields:
                filtered_data[key] = "***"
            elif isinstance(value, dict):
                filtered_data[key] = self.filter_dict(value)
            elif isinstance(value, list):
                filtered_data[key] = self.filter_list(value)
            elif isinstance(value, str):
                filtered_data[key] = self._filter_sensitive_data(value)
            else:
                filtered_data[key] = value

        return filtered_data

    def filter_list(self, data: list[Any]) -> list[Any]:
        """过滤列表中的敏感数据"""
        if not isinstance(data, list):
            return data

        filtered_list: list[Any] = []
        for item in data:
            if isinstance(item, dict):
                filtered_list.append(self.filter_dict(item))
            elif isinstance(item, list):
                filtered_list.append(self.filter_list(item))
            elif isinstance(item, str):
                filtered_list.append(self._filter_sensitive_data(item))
            else:
                filtered_list.append(item)

        return filtered_list


class SecurityAuditor:
    """安全审计器"""

    def __init__(self) -> None:
        self.security_log_file = get_config("security_log_file", "logs/security.log")
        self.enabled = get_config("security_logging_enabled", True)
        self._setup_security_logger()
        self.sensitive_filter = SensitiveDataFilter()

    def _setup_security_logger(self) -> None:
        """设置安全日志记录器"""
        self.logger = logging.getLogger("security_audit")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            log_dir = Path(self.security_log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(self.security_log_file)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)
            file_handler.addFilter(SensitiveDataFilter())

            self.logger.addHandler(file_handler)

    def log_security_event(
        self,
        event_type: str,
        message: str,
        **kwargs: Any,
    ) -> None:
        """记录安全事件"""
        if not self.enabled:
            return

        log_entry = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))


class RequestLogger:
    """请求日志记录器"""

    def __init__(self) -> None:
        self.log_file = get_config("request_log_file", "logs/request.log")
        self.enabled = get_config("request_logging_enabled", True)
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


def _safe_json_serialize(obj: Any) -> Any:
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_safe_json_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _safe_json_serialize(v) for k, v in obj.items()}
    if hasattr(obj, "dict"):
        return _safe_json_serialize(obj.dict())
    if hasattr(obj, "__dict__"):
        return _safe_json_serialize(obj.__dict__)
    return str(obj)[:500]


class SecurityLogFormatter(logging.Formatter):
    """安全日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.args:
            log_data["args"] = _safe_json_serialize(record.args)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class StructuredSecurityLogger:
    """结构化安全日志记录器"""

    def __init__(self, name: str = "structured_security") -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            log_file = get_config(
                "security_structured_log_file", "logs/security_structured.log"
            )
            log_dir = Path(log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            handler = logging.FileHandler(log_file)
            handler.setFormatter(SecurityLogFormatter())
            handler.addFilter(SensitiveDataFilter())
            self.logger.addHandler(handler)

    def log_event(self, event_type: str, **kwargs: Any) -> None:
        if not self.logger.isEnabledFor(logging.INFO):
            return

        log_data = {
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            **kwargs,
        }

        filtered_data = SensitiveDataFilter().filter_dict(log_data)
        self.logger.info(json.dumps(filtered_data, ensure_ascii=False))


class AuditTrailLogger:
    """审计日志记录器"""

    def __init__(self) -> None:
        self.logger = logging.getLogger("audit_trail")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            log_file = get_config("audit_log_file", "logs/audit.log")
            log_dir = Path(log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            handler = logging.FileHandler(log_file)
            handler.setFormatter(SecurityLogFormatter())
            handler.addFilter(SensitiveDataFilter())
            self.logger.addHandler(handler)

    def log_audit(self, action: str, **kwargs: Any) -> None:
        if not self.logger.isEnabledFor(logging.INFO):
            return

        log_data = {
            "action": action,
            "timestamp": datetime.now(UTC).isoformat(),
            **kwargs,
        }

        filtered_data = SensitiveDataFilter().filter_dict(log_data)
        self.logger.info(json.dumps(filtered_data, ensure_ascii=False))


class SecurityMetrics:
    """安全指标记录器"""

    def __init__(self) -> None:
        self.metrics: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()

    def record_metric(self, name: str, value: float) -> None:
        with self.lock:
            self.metrics[name].append(value)

    def get_metrics(self) -> dict[str, dict[str, float]]:
        with self.lock:
            result: dict[str, dict[str, float]] = {}
            for name, values in self.metrics.items():
                if not values:
                    continue
                result[name] = {
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "count": len(values),
                }
            return result


class SecurityMonitor:
    """安全监控器"""

    def __init__(self) -> None:
        self.structured_logger = StructuredSecurityLogger()
        self.audit_logger = AuditTrailLogger()
        self.metrics = SecurityMetrics()

    def record_event(self, event_type: str, **kwargs: Any) -> None:
        self.structured_logger.log_event(event_type, **kwargs)

    def record_audit(self, action: str, **kwargs: Any) -> None:
        self.audit_logger.log_audit(action, **kwargs)

    def record_metric(self, name: str, value: float) -> None:
        self.metrics.record_metric(name, value)

    def get_metrics(self) -> dict[str, dict[str, float]]:
        return self.metrics.get_metrics()


security_monitor = SecurityMonitor()
security_auditor: SecurityAuditor = SecurityAuditor()
request_logger: RequestLogger = RequestLogger()


def setup_logging_security() -> logging.Logger:
    """设置日志安全"""
    log_level = get_config("log_level", "INFO")
    log_file = get_config("log_file", "logs/app.log")

    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    for handler in logging.getLogger().handlers:
        handler.addFilter(SensitiveDataFilter())

    logger = logging.getLogger(__name__)
    logger.info("日志安全设置完成")

    return logger


def log_security_event(event_type: str, message: str, **kwargs: Any) -> None:
    """记录安全事件的便捷函数"""
    security_auditor.log_security_event(event_type, message, **kwargs)


def log_request_info(**kwargs: Any) -> None:
    """记录请求信息的便捷函数"""
    request_logger.log_request(**kwargs)


def get_request_context() -> dict[str, str]:
    """获取请求上下文"""
    return {"request_id": str(uuid.uuid4()), "timestamp": datetime.now(UTC).isoformat()}


if __name__ == "__main__":
    setup_logging_security()

    logger = logging.getLogger(__name__)
    logger.info("测试敏感数据过滤: password=secret123, email=user@example.com")

    log_security_event(
        "TEST_EVENT", "测试安全事件", user_id="user123", ip_address="192.168.1.1"
    )

    log_request_info(
        method="POST",
        path="/api/v1/login",
        status_code=200,
        response_time=0.1,
        user_id="user123",
        ip_address="192.168.1.1",
    )
