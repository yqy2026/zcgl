"""
Sensitive data filtering and security log formatting helpers.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any


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
        if getattr(record, "args", None):
            # Format once and redact to avoid breaking %-format placeholders.
            try:
                formatted = record.getMessage()
            except Exception:
                formatted = f"{record.msg} {record.args}"
            record.msg = self._filter_sensitive_data(str(formatted))
            record.args = ()
            return record

        if hasattr(record, "msg"):
            record.msg = self._filter_sensitive_data(str(record.msg))

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
