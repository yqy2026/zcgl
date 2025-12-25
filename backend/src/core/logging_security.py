from typing import Any

"""
安全日志记录器
提供敏感信息脱敏、结构化日志和安全审计功能
"""

import hashlib
import json
import logging
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .config import get_config


class SensitiveDataFilter(logging.Filter):
    """敏感数据过滤器"""

    def __init__(self):
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
        """过滤文本中的敏感数据"""
        if not isinstance(text, str):
            return text

        filtered_text = text

        # 应用正则模式过滤
        for pattern, replacement in self.sensitive_patterns:
            filtered_text = re.sub(
                pattern, replacement, filtered_text, flags=re.IGNORECASE
            )

        # 过滤JSON中的敏感字段
        try:
            if text.strip().startswith("{") or text.strip().startswith("["):
                data = json.loads(text)
                filtered_data = self._filter_dict(data)
                return json.dumps(filtered_data, ensure_ascii=False)
        except (json.JSONDecodeError, ValueError):
            pass

        return filtered_text

    def _filter_dict(self, data: Any) -> Any:
        """递归过滤字典中的敏感数据"""
        if isinstance(data, dict):
            return {
                key: self._filter_value(key, self._is_sensitive_key(key))
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._filter_dict(item) for item in data]
        else:
            return data

    def _filter_value(self, value: Any, is_sensitive: bool) -> Any:
        """过滤单个值"""
        if is_sensitive:
            return "***"
        elif isinstance(value, (dict, list)):
            return self._filter_dict(value)
        elif isinstance(value, str):
            return self._filter_sensitive_data(value)
        return value

    def _is_sensitive_key(self, key: str) -> bool:
        """检查键名是否敏感"""
        key_lower = str(key).lower()
        return any(sensitive in key_lower for sensitive in self.sensitive_fields)


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为结构化JSON"""
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": self._sanitize_message(record.getMessage()),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加请求ID（如果存在）
        if hasattr(record, "request_id"):
            log_entry["request_id"] = str(getattr(record, "request_id", ""))

        # 添加用户ID（如果存在）
        if hasattr(record, "user_id"):
            log_entry["user_id"] = str(getattr(record, "user_id", ""))

        # 添加会话ID（如果存在）
        if hasattr(record, "session_id"):
            log_entry["session_id"] = str(getattr(record, "session_id", ""))

        # 添加IP地址（如果存在）
        if hasattr(record, "client_ip"):
            log_entry["client_ip"] = str(getattr(record, "client_ip", ""))

        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self._format_exception(record.exc_info)

        # 添加额外字段
        extra_fields = getattr(record, "extra_fields", None)
        if extra_fields:
            log_entry.update(extra_fields)

        # 确保所有字段都可以被JSON序列化
        log_entry = self._ensure_json_serializable(log_entry)

        return json.dumps(log_entry, ensure_ascii=False)

    def _sanitize_message(self, message: str) -> str:
        """清理消息中的不可序列化内容"""
        if not isinstance(message, str):
            try:
                # 尝试转换为字符串
                message = str(message)
            except Exception:
                message = "<无法序列化的消息对象>"

        # 限制消息长度
        if len(message) > 1000:
            message = message[:1000] + "...(截断)"

        return message

    def _ensure_json_serializable(self, obj: Any) -> Any:
        """确保对象可以被JSON序列化"""
        if obj is None:
            return None
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {
                key: self._ensure_json_serializable(value) for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [self._ensure_json_serializable(item) for item in obj]
        elif hasattr(obj, "__dict__"):
            # 处理SQLAlchemy模型对象和其他自定义对象
            try:
                # 尝试获取对象的字典表示
                obj_dict = obj.__dict__.copy()
                # 移除SQLAlchemy的内部属性
                obj_dict.pop("_sa_instance_state", None)
                return {
                    key: self._ensure_json_serializable(value)
                    for key, value in obj_dict.items()
                    if not key.startswith("_")
                }
            except Exception:
                # 如果无法序列化，返回字符串表示
                return str(obj)[:500]  # 限制长度
        else:
            # 对于其他类型，尝试转换为字符串
            try:
                json.dumps(obj)  # 测试是否可序列化
                return obj
            except (TypeError, ValueError):
                return str(obj)[:500]  # 限制长度

    def _format_exception(self, exc_info) -> str:
        """格式化异常信息"""
        import traceback

        return "".join(traceback.format_exception(*exc_info))


class SecurityAuditor:
    """安全审计器"""

    def __init__(self):
        self.security_log_file = get_config("security_log_file", "logs/security.log")
        self.enabled = get_config("security_logging_enabled", True)
        self._setup_security_logger()
        self.sensitive_filter = SensitiveDataFilter()

    def _setup_security_logger(self):
        """设置安全日志记录器"""
        if not self.enabled:
            return

        # 创建安全日志目录
        log_dir = Path(self.security_log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # 创建安全日志记录器
        self.security_logger = logging.getLogger("security")
        self.security_logger.setLevel(logging.INFO)

        # 创建文件处理器
        handler = logging.FileHandler(self.security_log_file)
        handler.setFormatter(StructuredFormatter())
        handler.addFilter(SensitiveDataFilter())

        self.security_logger.addHandler(handler)
        self.security_logger.propagate = False

    def log_security_event(
        self,
        event_type: str,
        message: str,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        **kwargs,
    ):
        """记录安全事件"""
        if not self.enabled:
            return

        security_event = {
            "event_type": event_type,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
            "severity": self._get_event_severity(event_type),
        }

        # 添加可选字段并进行脱敏处理
        if user_id:
            security_event["user_id"] = self._hash_sensitive_data(user_id)
        if ip_address:
            security_event["ip_address"] = self._hash_sensitive_data(ip_address)
        if user_agent:
            # 对用户代理进行脱敏处理
            filtered_user_agent = self.sensitive_filter._filter_sensitive_data(
                user_agent
            )
            security_event["user_agent"] = filtered_user_agent[:500]  # 限制长度
        if request_id:
            security_event["request_id"] = request_id

        # 对额外字段进行脱敏处理
        filtered_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                # 检查键是否敏感
                if self.sensitive_filter._is_sensitive_key(key):
                    filtered_kwargs[key] = "***"
                else:
                    # 对值进行脱敏处理
                    filtered_kwargs[key] = self.sensitive_filter._filter_sensitive_data(
                        value
                    )
            else:
                filtered_kwargs[key] = value

        # 添加额外字段
        security_event.update(filtered_kwargs)

        # 确保所有数据都可以被JSON序列化
        serializable_event = self._ensure_json_serializable(security_event)

        self.security_logger.info(serializable_event)

    def _get_event_severity(self, event_type: str) -> str:
        """获取事件严重程度"""
        high_severity_events = {
            "AUTHENTICATION_FAILURE",
            "AUTHORIZATION_FAILURE",
            "PRIVILEGE_ESCALATION",
            "SUSPICIOUS_ACTIVITY",
            "DATA_BREACH_ATTEMPT",
            "MALICIOUS_REQUEST",
            "BRUTE_FORCE_ATTACK",
            "FILE_UPLOAD_MALICIOUS",
            "SQL_INJECTION_ATTEMPT",
            "XSS_ATTACK",
            "CSRF_ATTEMPT",
        }

        medium_severity_events = {
            "INVALID_TOKEN",
            "SESSION_EXPIRED",
            "ACCESS_DENIED",
            "RATE_LIMIT_EXCEEDED",
            "FILE_UPLOAD_REJECTED",
            "PASSWORD_RESET_REQUEST",
            "ACCOUNT_LOCKED",
        }

        low_severity_events = {
            "AUTHENTICATION_SUCCESS",
            "PASSWORD_CHANGED",
            "PROFILE_UPDATED",
            "FILE_UPLOAD_SUCCESS",
        }

        if event_type in high_severity_events:
            return "HIGH"
        elif event_type in medium_severity_events:
            return "MEDIUM"
        elif event_type in low_severity_events:
            return "LOW"
        else:
            return "INFO"

    def _ensure_json_serializable(self, obj: Any) -> Any:
        """确保对象可以被JSON序列化"""
        if obj is None:
            return None
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {
                key: self._ensure_json_serializable(value) for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [self._ensure_json_serializable(item) for item in obj]
        elif hasattr(obj, "__dict__"):
            # 处理SQLAlchemy模型对象和其他自定义对象
            try:
                # 尝试获取对象的字典表示
                obj_dict = obj.__dict__.copy()
                # 移除SQLAlchemy的内部属性
                obj_dict.pop("_sa_instance_state", None)
                return {
                    key: self._ensure_json_serializable(value)
                    for key, value in obj_dict.items()
                    if not key.startswith("_")
                }
            except Exception:
                # 如果无法序列化，返回字符串表示
                return str(obj)[:500]  # 限制长度
        else:
            # 对于其他类型，尝试转换为字符串
            try:
                json.dumps(obj)  # 测试是否可序列化
                return obj
            except (TypeError, ValueError):
                return str(obj)[:500]  # 限制长度

    def _hash_sensitive_data(self, data: str) -> str:
        """对敏感数据进行哈希处理"""
        if not data:
            return data

        # 使用SHA-256哈希
        hash_object = hashlib.sha256(data.encode())
        return hash_object.hexdigest()[:16]  # 取前16位


class RequestLogger:
    """请求日志记录器"""

    def __init__(self):
        self.request_log_file = get_config("request_log_file", "logs/requests.log")
        self.enabled = get_config("request_logging_enabled", True)
        self._setup_request_logger()
        self.sensitive_filter = SensitiveDataFilter()

    def _setup_request_logger(self):
        """设置请求日志记录器"""
        if not self.enabled:
            return

        # 创建请求日志目录
        log_dir = Path(self.request_log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # 创建请求日志记录器
        self.request_logger = logging.getLogger("requests")
        self.request_logger.setLevel(logging.INFO)

        # 创建文件处理器
        handler = logging.FileHandler(self.request_log_file)
        handler.setFormatter(StructuredFormatter())
        handler.addFilter(SensitiveDataFilter())

        self.request_logger.addHandler(handler)
        self.request_logger.propagate = False

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        **kwargs,
    ):
        """记录请求信息"""
        if not self.enabled:
            return

        request_info = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # 添加可选字段并进行脱敏处理
        if user_id:
            request_info["user_id"] = self._hash_sensitive_data(user_id)
        if ip_address:
            request_info["ip_address"] = self._hash_sensitive_data(ip_address)
        if user_agent:
            # 对用户代理进行脱敏处理
            filtered_user_agent = self.sensitive_filter._filter_sensitive_data(
                user_agent
            )
            request_info["user_agent"] = filtered_user_agent[:500]
        if request_id:
            request_info["request_id"] = request_id

        # 对额外字段进行脱敏处理
        filtered_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                # 检查键是否敏感
                if self.sensitive_filter._is_sensitive_key(key):
                    filtered_kwargs[key] = "***"
                else:
                    # 对值进行脱敏处理
                    filtered_kwargs[key] = self.sensitive_filter._filter_sensitive_data(
                        value
                    )
            else:
                filtered_kwargs[key] = value

        # 添加额外字段
        request_info.update(filtered_kwargs)

        # 确保所有数据都可以被JSON序列化
        serializable_request = self._ensure_json_serializable(request_info)

        # 根据状态码决定日志级别
        if status_code >= 500:
            self.request_logger.error(serializable_request)
        elif status_code >= 400:
            self.request_logger.warning(serializable_request)
        else:
            self.request_logger.info(serializable_request)

    def _ensure_json_serializable(self, obj: Any) -> Any:
        """确保对象可以被JSON序列化"""
        if obj is None:
            return None
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {
                key: self._ensure_json_serializable(value) for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [self._ensure_json_serializable(item) for item in obj]
        elif hasattr(obj, "__dict__"):
            # 处理SQLAlchemy模型对象和其他自定义对象
            try:
                # 尝试获取对象的字典表示
                obj_dict = obj.__dict__.copy()
                # 移除SQLAlchemy的内部属性
                obj_dict.pop("_sa_instance_state", None)
                return {
                    key: self._ensure_json_serializable(value)
                    for key, value in obj_dict.items()
                    if not key.startswith("_")
                }
            except Exception:
                # 如果无法序列化，返回字符串表示
                return str(obj)[:500]  # 限制长度
        else:
            # 对于其他类型，尝试转换为字符串
            try:
                json.dumps(obj)  # 测试是否可序列化
                return obj
            except (TypeError, ValueError):
                return str(obj)[:500]  # 限制长度

    def _hash_sensitive_data(self, data: str) -> str:
        """对敏感数据进行哈希处理"""
        if not data:
            return data

        hash_object = hashlib.sha256(data.encode())
        return hash_object.hexdigest()[:16]


# 全局实例
security_auditor = SecurityAuditor()
request_logger = RequestLogger()


def setup_logging_security():
    """设置日志安全"""
    # 获取日志配置
    log_level = get_config("log_level", "INFO")
    log_file = get_config("log_file", "logs/app.log")

    # 创建日志目录
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # 配置根日志记录器
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    # 添加敏感数据过滤器到所有处理器
    for handler in logging.getLogger().handlers:
        handler.addFilter(SensitiveDataFilter())

    logger = logging.getLogger(__name__)
    logger.info("日志安全设置完成")

    return logger


# 便捷函数
def log_security_event(event_type: str, message: str, **kwargs):
    """记录安全事件的便捷函数"""
    security_auditor.log_security_event(event_type, message, **kwargs)


def log_request_info(**kwargs):
    """记录请求信息的便捷函数"""
    request_logger.log_request(**kwargs)


def get_request_context() -> dict[str, str]:
    """获取请求上下文"""
    return {"request_id": str(uuid.uuid4()), "timestamp": datetime.now(UTC).isoformat()}


if __name__ == "__main__":
    # 测试日志安全
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
        duration_ms=150.5,
        user_id="user123",
    )
