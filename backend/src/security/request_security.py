"""
Request security utilities.
"""

from __future__ import annotations

import re


class RequestSecurity:
    """请求安全工具类"""

    @staticmethod
    def sanitize_input(input_data: str) -> str:
        """
        清理输入数据

        Args:
            input_data: 输入字符串

        Returns:
            str: 清理后的字符串
        """
        if not isinstance(input_data, str):
            return input_data

        sanitized = input_data.replace("\x00", "")
        # Strip all ASCII control chars, including CR/LF to prevent header injection.
        sanitized = re.sub(r"[\x00-\x1F\x7F]", "", sanitized)
        return sanitized.strip()

    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        if not isinstance(email, str):
            return False

        email = email.strip()
        if "@" not in email:
            return False

        local, domain = email.rsplit("@", 1)
        if not local or not domain:
            return False

        # Reject spaces/quotes and obvious injection characters.
        if re.search(r"[\s\"'\\]", email):
            return False

        # Local part must be ASCII only.
        if any(ord(ch) > 127 for ch in local):
            return False

        # No consecutive dots or dot at ends.
        if ".." in local or ".." in domain:
            return False
        if local.startswith(".") or local.endswith("."):
            return False
        if domain.startswith(".") or domain.endswith("."):
            return False

        # Validate local part characters.
        if not re.match(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$", local):
            return False

        # Validate domain via IDNA; allow unicode domain.
        try:
            ascii_domain = domain.encode("idna").decode("ascii")
        except Exception:
            return False

        if not re.match(r"^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$", ascii_domain):
            return False

        # Labels must not start or end with hyphen.
        if any(
            label.startswith("-") or label.endswith("-")
            for label in ascii_domain.split(".")
        ):
            return False

        return True

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """验证手机号格式"""
        pattern = r"^1[3-9]\d{9}$"
        return re.match(pattern, phone) is not None

    @staticmethod
    def is_safe_url(url: str) -> bool:
        """
        检查URL是否安全

        Args:
            url: 要检查的URL

        Returns:
            bool: URL是否安全
        """
        try:
            if not isinstance(url, str):
                return False

            url = url.strip()
            lowered = url.lower()

            # 检查URL协议
            if not lowered.startswith(("http://", "https://")):
                return False

            # Block javascript/data URLs even if embedded.
            if "javascript:" in lowered or "data:" in lowered:
                return False

            # Block common XSS/event-handler patterns.
            if re.search(r"on\w+\s*=", lowered) or "<script" in lowered:
                return False

            # 检查是否包含危险字符
            dangerous_chars = [
                "<",
                ">",
                '"',
                "'",
                "{",
                "}",
                "|",
                "\\",
                "^",
                "`",
            ]
            if any(char in url for char in dangerous_chars):
                return False

            # Disallow CR/LF to prevent header injection.
            if "\r" in url or "\n" in url:
                return False

            return True

        except Exception:
            return False
