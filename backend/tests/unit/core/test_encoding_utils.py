"""
Unit tests for encoding_utils
"""

import logging

from src.core import encoding_utils


class DummyStream:
    def __init__(self, *, fail_on_unicode: bool = False, fail_once: bool = False):
        self.output = ""
        self.fail_on_unicode = fail_on_unicode
        self.fail_once = fail_once
        self.write_calls = 0
        self.buffer = None

    def write(self, text: str):
        self.write_calls += 1
        if self.fail_once and self.write_calls == 1:
            raise Exception("write failed")
        if self.fail_on_unicode and any(ord(c) > 127 for c in text):
            raise UnicodeEncodeError("ascii", text, 0, 1, "encoding error")
        self.output += text

    def flush(self):
        return None


class TestEncodingUtils:
    def test_safe_log_format_removes_emoji_and_symbols(self):
        message = "Hello ✅ world #1 测试"
        cleaned = encoding_utils.safe_log_format(message)
        assert "✅" not in cleaned
        assert "#" not in cleaned
        assert "测试" in cleaned
        assert "Hello" in cleaned

    def test_safe_error_message_sanitizes_exception(self):
        error = ValueError("Bad ✅ input")
        safe_message = encoding_utils.safe_error_message(error)
        assert "✅" not in safe_message
        assert safe_message.startswith("Error:")

    def test_safe_print_falls_back_on_unicode_error(self, monkeypatch):
        stream = DummyStream(fail_on_unicode=True)
        monkeypatch.setattr(encoding_utils.sys, "stdout", stream)

        encoding_utils.safe_print("emoji ✅")

        assert "emoji ?" in stream.output

    def test_safe_print_falls_back_on_generic_error(self, monkeypatch):
        stream = DummyStream(fail_once=True)
        monkeypatch.setattr(encoding_utils.sys, "stdout", stream)

        encoding_utils.safe_print("plain text")

        assert "Encoding Error" in stream.output

    def test_setup_utf8_encoding_returns_false_on_error(self, monkeypatch):
        def raise_writer(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(encoding_utils.codecs, "getwriter", raise_writer)
        monkeypatch.setattr(encoding_utils.sys, "stdout", DummyStream())
        monkeypatch.setattr(encoding_utils.sys, "stderr", DummyStream())

        assert encoding_utils.setup_utf8_encoding() is False

    def test_encoding_safe_handler_emits_sanitized_message(self, monkeypatch):
        stream = DummyStream()
        monkeypatch.setattr(encoding_utils.sys, "stderr", stream)

        handler = encoding_utils.EncodingSafeHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Hi ✅",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        assert "✅" not in stream.output
        assert "Hi" in stream.output
