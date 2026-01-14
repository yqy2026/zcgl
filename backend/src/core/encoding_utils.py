"""
编码安全工具模块
强制UTF-8编码处理，避免中文显示问题
"""

import codecs
import logging
import sys
from typing import Any


# 强制设置UTF-8编码输出
def setup_utf8_encoding() -> bool:
    """设置UTF-8编码环境"""
    try:
        # 强制设置stdout和stderr为UTF-8编码
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)
        if hasattr(sys.stderr, "buffer"):
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer)

        # 设置默认编码
        if hasattr(sys, "setdefaultencoding"):
            sys.setdefaultencoding("utf-8")

        return True
    except Exception:
        return False


def safe_print(message: Any) -> None:
    """安全打印，避免编码错误"""
    try:
        sys.stdout.write(str(message) + "\n")
        sys.stdout.flush()
    except UnicodeEncodeError:
        # 降级到ASCII编码，替换无法编码的字符
        sys.stdout.write(
            str(message).encode("ascii", errors="replace").decode("ascii") + "\n"
        )
        sys.stdout.flush()
    except Exception:
        sys.stdout.write("[Encoding Error: Unable to display message]\n")
        sys.stdout.flush()


def safe_log_format(message: str) -> str:
    """安全的日志格式化，移除可能导致编码问题的字符"""
    # 移除emoji字符和其他可能导致编码问题的Unicode字符
    import re

    # 保留中文字符、英文字符、数字和基本标点
    cleaned = re.sub(r'[^\u4e00-\u9fff\u3400-\u4dbf\w\s.,!?;:()[\]{}"\'-]', "", message)
    return cleaned.strip()


def safe_error_message(error: Exception) -> str:
    """安全错误消息格式化"""
    try:
        error_str = str(error)
        # 移除可能导致编码问题的字符
        return safe_log_format(f"Error: {error_str}")
    except Exception:
        return "Error: Unable to display error details due to encoding issues"


# 在模块导入时自动设置编码
setup_utf8_encoding()


# 创建编码安全的日志处理器
class EncodingSafeHandler(logging.Handler):
    """编码安全的日志处理器"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # 格式化日志消息
            msg = self.format(record)
            # 安全处理编码问题
            safe_msg = safe_log_format(msg)

            # 输出到控制台
            sys.stderr.write(safe_msg + "\n")
            sys.stderr.flush()
        except Exception:
            sys.stderr.write(f"[Logging Error] Unable to format log record: {record}\n")
            sys.stderr.flush()
