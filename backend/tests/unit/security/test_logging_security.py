"""setup_logging_security 文件编码回归测试（2026-08-17 缺陷 2.5 复核补修）。

复核发现：缺陷 2.5 的 PYTHONIOENCODING 修复只覆盖 std 流，
`logging.FileHandler` 仍以 locale 编码（Windows cp936/GBK, strict）打开日志文件，
写 emoji（🔐）日志行即抛 UnicodeEncodeError 丢行（启动期「Logging error」）。
本文件钉住：传入 basicConfig 的 FileHandler 必须显式 utf-8，且该 handler 能落盘 emoji 行。

实现说明：pytest 的 logging 插件在测试执行期占用 root logger 的 handler，
`logging.basicConfig` 幂等（root 已有 handler 时跳过），因此不直接调用
setup_logging_security 的真实 basicConfig，而是捕获其入参断言契约，
并用捕获的 FileHandler 直接 emit 做端到端 emoji 落盘验证。
"""

import logging
from pathlib import Path
from typing import Any

import pytest

from src.security.logging_security import setup_logging_security

pytestmark = pytest.mark.unit


@pytest.fixture
def captured_basic_config(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """捕获 setup_logging_security 传给 logging.basicConfig 的关键参数。"""
    captured: dict[str, Any] = {}

    def fake_basic_config(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)
    return captured


def test_file_handler_must_use_utf8_encoding(
    captured_basic_config: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FileHandler 必须显式 utf-8（修复前 encoding=None → locale cp936 → emoji 丢行）。"""
    monkeypatch.setattr(
        "src.security.logging_security.settings.LOG_FILE", str(tmp_path / "app.log")
    )
    monkeypatch.setattr("src.security.logging_security.settings.LOG_LEVEL", "INFO")

    setup_logging_security()

    handlers = captured_basic_config.get("handlers", [])
    file_handlers = [h for h in handlers if isinstance(h, logging.FileHandler)]
    assert file_handlers, "setup_logging_security 应配置 FileHandler"
    for handler in file_handlers:
        assert handler.encoding == "utf-8", (
            f"FileHandler 必须显式 utf-8，当前 encoding={handler.encoding!r}"
        )


def test_emoji_log_line_is_written_by_file_handler(
    captured_basic_config: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """端到端：setup 构造的 FileHandler 必须能落盘 emoji 行（修复前 cp936 strict 抛错、文件无此行）。"""
    log_file = tmp_path / "app.log"
    monkeypatch.setattr(
        "src.security.logging_security.settings.LOG_FILE", str(log_file)
    )
    monkeypatch.setattr("src.security.logging_security.settings.LOG_LEVEL", "INFO")

    setup_logging_security()

    handlers = captured_basic_config.get("handlers", [])
    file_handlers = [h for h in handlers if isinstance(h, logging.FileHandler)]
    assert file_handlers

    logger = logging.getLogger("test_logging_security")
    logger.setLevel(logging.INFO)
    logger.handlers = list(file_handlers)
    logger.propagate = False
    logger.info("🔐 emoji 日志行")
    for handler in file_handlers:
        handler.flush()

    content = log_file.read_text(encoding="utf-8")
    assert "🔐 emoji 日志行" in content
