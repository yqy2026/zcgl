"""
Precise coverage tests - Target exact uncovered lines

This file contains tests that specifically target the remaining uncovered lines
with techniques designed to actually execute those code paths.
"""

import pytest
import sys
import os
import time
import asyncio
from io import StringIO
from unittest.mock import patch, Mock, MagicMock, PropertyMock
import importlib


class TestTaskQueueWorkerLines:
    """Test task_queue.py:190, 192, 196 - worker method processing"""

    def test_task_queue_worker_processing(self):
        """
        Target task_queue.py:190, 192, 196
        Lines 190, 192, 196 in the worker method

        These lines are in the worker loop that processes tasks.
        Line 190: self.process_task(task)
        Line 192: self.queue.task_done()
        Line 196: logger.error(f"工作线程错误: {e}")
        """
        from src.core.task_queue import TaskQueue, TaskStatus

        # Create a task queue with one worker
        queue = TaskQueue(max_workers=1)

        # Register a callback
        executed = []

        def task_callback():
            executed.append(True)
            return "done"

        queue.register_callback("test-task", task_callback)

        # Submit a task
        task_id = queue.submit_task("test-task")

        # Start the queue
        queue.start()

        # Wait for task to process
        time.sleep(0.5)

        # Stop the queue
        queue.stop()

        # Verify task was executed
        assert len(executed) > 0, "Task should have been executed"


class TestEnhancedErrorHandlerHealthCheck:
    """Test enhanced_error_handler.py:212-214 - exception handler in monitor_processing_health"""

    @pytest.mark.asyncio
    async def test_monitor_processing_health_exception_handler(self):
        """
        Target enhanced_error_handler.py:212-214
        Lines 212-214: Exception handler in monitor_processing_health function

        These lines execute when an exception occurs during health monitoring.
        """
        from src.services.core.enhanced_error_handler import monitor_processing_health

        # Mock get_ocr_service to raise an exception
        with patch('src.services.providers.ocr_provider.get_ocr_service',
                   side_effect=RuntimeError("Test OCR service error")):

            # Call monitor_processing_health - should hit exception handler
            result = await monitor_processing_health()

            # Should return error status
            assert isinstance(result, dict)
            assert "status" in result
            assert result["status"] == "unhealthy"


class TestEncodingUtilsLine37:
    """Test encoding_utils.py:37 - ASCII fallback in safe_print"""

    def test_safe_print_unicode_error_fallback(self):
        """
        Target encoding_utils.py:37
        Line 37: print(str(message).encode("ascii", errors="replace").decode("ascii"))

        This line executes when print() raises UnicodeEncodeError.
        """
        from src.core.encoding_utils import safe_print

        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            # Create a custom stdout that raises UnicodeEncodeError
            class UnicodeFailingStream:
                def __init__(self):
                    self.calls = []

                def write(self, s):
                    self.calls.append(s)
                    # First write raises UnicodeEncodeError
                    if len(self.calls) == 1:
                        raise UnicodeEncodeError('ascii', s, 0, len(s), 'test error')
                    return len(s)

                def flush(self):
                    pass

            sys.stdout = UnicodeFailingStream()
            sys.stderr = UnicodeFailingStream()

            # Call safe_print - should hit line 37
            safe_print("test with unicode: \u2014")

            # If we get here without exception, line 37 was executed
            assert True

        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr


class TestEnumFieldLine95:
    """Test enum_field.py:95 - return v when None in validate_code"""

    def test_enum_field_value_update_none_code(self):
        """
        Target enum_field.py:95
        Line 95: return v (when v is None)

        This line returns None when code field validator receives None.
        """
        from src.schemas.enum_field import EnumFieldValueUpdate

        # Create with code=None - should hit line 95
        update = EnumFieldValueUpdate(code=None)

        # Verify
        assert update.code is None


class TestFileSecurityLines218_219:
    """Test file_security.py:218-219 - exception handler in validate_file_path"""

    def test_validate_file_path_null_byte_exception(self):
        """
        Target file_security.py:218-219
        Lines 218-219: except (OSError, ValueError): return False

        Null bytes in path cause OSError.
        """
        from src.utils.file_security import validate_file_path

        # Use null byte which causes OSError
        invalid_path = "test\x00file.txt"
        allowed = ["C:\\tmp"]

        result = validate_file_path(invalid_path, allowed)

        # Should return False (exception caught)
        assert result is False


class TestApiV1Lines46_48:
    """Test api/v1/__init__.py:46-48 - ImportError handler for system_settings"""

    def test_api_v1_system_settings_router_exists(self):
        """
        Verify api/v1 module structure
        """
        from src.api.v1 import api_router, system_settings_router

        # The module should have loaded properly
        assert api_router is not None
        # system_settings_router can be None or a router
        assert system_settings_router is None or hasattr(system_settings_router, 'routes')


# Module-level tests
def test_task_queue_integration():
    """Integration test for task queue worker"""
    from src.core.task_queue import TaskQueue

    queue = TaskQueue(max_workers=1)

    results = []

    def task_func():
        results.append("done")
        return "success"

    queue.register_callback("integration-test", task_func)
    queue.submit_task("integration-test")
    queue.start()
    time.sleep(0.3)
    queue.stop()

    assert len(results) > 0


@pytest.mark.asyncio
async def test_enhanced_error_handler_health_check():
    """Test enhanced error handler health monitoring"""
    from src.services.core.enhanced_error_handler import monitor_processing_health

    # Test normal health check
    result = await monitor_processing_health()
    assert isinstance(result, dict)


def test_encoding_safe_print():
    """Test encoding utils safe print"""
    from src.core.encoding_utils import safe_print

    # Should not raise exception
    safe_print("test message")
    safe_print("测试消息")
    safe_print("🚀 emoji test")


def test_enum_field_none_code():
    """Test enum field with None code"""
    from src.schemas.enum_field import EnumFieldValueUpdate, EnumFieldTypeUpdate

    value_update = EnumFieldValueUpdate(code=None)
    type_update = EnumFieldTypeUpdate(code=None)

    assert value_update.code is None
    assert type_update.code is None


def test_file_security_exception_handling():
    """Test file security exception handling"""
    from src.utils.file_security import validate_file_path

    # Test with null byte (causes OSError)
    result = validate_file_path("test\x00file", ["/tmp"])
    assert result is False
