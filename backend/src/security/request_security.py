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
        sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", sanitized)
        return sanitized.strip()

    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

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
            # 检查URL协议
            if not url.startswith(("http://", "https://")):
                return False

            # 检查是否包含危险字符
            dangerous_chars = [
                "<",
                ">",
                '"',
                "'",
                "#",
                "%",
                "{",
                "}",
                "|",
                "\\",
                "^",
                "`",
            ]
            if any(char in url for char in dangerous_chars):
                return False

            # 检查JavaScript协议
            return "javascript:" not in url.lower()

        except Exception:
            return False
