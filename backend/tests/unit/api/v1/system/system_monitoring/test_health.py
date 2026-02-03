"""
健康检查模块测试

测试 system_monitoring/health.py 中的健康检查功能
"""

from datetime import datetime
from unittest.mock import MagicMock, patch


class TestCheckComponentHealth:
    """check_component_health 函数测试"""

    @patch("src.api.v1.system.system_monitoring.health.get_database_manager")
    @patch("src.api.v1.system.system_monitoring.health.psutil")
    def test_returns_dict(self, mock_psutil, mock_get_db):
        """测试返回字典类型"""
        from src.api.v1.system.system_monitoring.health import check_component_health

        # Mock database manager
        mock_db = MagicMock()
        mock_db.run_health_check.return_value = {
            "healthy": True,
            "timestamp": datetime.now().isoformat(),
            "checks": {"basic_connection": {"response_time_ms": 5}},
            "overall_score": 95,
        }
        mock_db.get_connection_pool_status.return_value = {
            "utilization": 50,
            "active_connections": 5,
        }
        mock_get_db.return_value = mock_db

        # Mock psutil
        mock_disk = MagicMock()
        mock_disk.percent = 50
        mock_disk.free = 100 * 1024**3
        mock_psutil.disk_usage.return_value = mock_disk

        mock_memory = MagicMock()
        mock_memory.percent = 60
        mock_memory.available = 8 * 1024**3
        mock_psutil.virtual_memory.return_value = mock_memory

        result = check_component_health()

        assert isinstance(result, dict)

    @patch("src.api.v1.system.system_monitoring.health.get_database_manager")
    @patch("src.api.v1.system.system_monitoring.health.psutil")
    def test_contains_database_component(self, mock_psutil, mock_get_db):
        """测试包含数据库组件"""
        from src.api.v1.system.system_monitoring.health import check_component_health

        mock_db = MagicMock()
        mock_db.run_health_check.return_value = {
            "healthy": True,
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "overall_score": 90,
        }
        mock_db.get_connection_pool_status.return_value = {"utilization": 40}
        mock_get_db.return_value = mock_db

        mock_disk = MagicMock(percent=50, free=100 * 1024**3)
        mock_psutil.disk_usage.return_value = mock_disk
        mock_memory = MagicMock(percent=60, available=8 * 1024**3)
        mock_psutil.virtual_memory.return_value = mock_memory

        result = check_component_health()

        assert "database" in result
        assert "status" in result["database"]

    @patch("src.api.v1.system.system_monitoring.health.get_database_manager")
    @patch("src.api.v1.system.system_monitoring.health.psutil")
    def test_contains_cache_component(self, mock_psutil, mock_get_db):
        """测试包含缓存组件"""
        from src.api.v1.system.system_monitoring.health import check_component_health

        mock_get_db.return_value = None

        mock_disk = MagicMock(percent=50, free=100 * 1024**3)
        mock_psutil.disk_usage.return_value = mock_disk
        mock_memory = MagicMock(percent=60, available=8 * 1024**3)
        mock_psutil.virtual_memory.return_value = mock_memory

        result = check_component_health()

        assert "cache" in result
        assert result["cache"]["status"] == "healthy"

    @patch("src.api.v1.system.system_monitoring.health.get_database_manager")
    @patch("src.api.v1.system.system_monitoring.health.psutil")
    def test_contains_filesystem_component(self, mock_psutil, mock_get_db):
        """测试包含文件系统组件"""
        from src.api.v1.system.system_monitoring.health import check_component_health

        mock_get_db.return_value = None

        mock_disk = MagicMock(percent=50, free=100 * 1024**3)
        mock_psutil.disk_usage.return_value = mock_disk
        mock_memory = MagicMock(percent=60, available=8 * 1024**3)
        mock_psutil.virtual_memory.return_value = mock_memory

        result = check_component_health()

        assert "filesystem" in result
        assert "usage_percent" in result["filesystem"]

    @patch("src.api.v1.system.system_monitoring.health.get_database_manager")
    @patch("src.api.v1.system.system_monitoring.health.psutil")
    def test_contains_memory_component(self, mock_psutil, mock_get_db):
        """测试包含内存组件"""
        from src.api.v1.system.system_monitoring.health import check_component_health

        mock_get_db.return_value = None

        mock_disk = MagicMock(percent=50, free=100 * 1024**3)
        mock_psutil.disk_usage.return_value = mock_disk
        mock_memory = MagicMock(percent=60, available=8 * 1024**3)
        mock_psutil.virtual_memory.return_value = mock_memory

        result = check_component_health()

        assert "memory" in result
        assert "usage_percent" in result["memory"]

    @patch("src.api.v1.system.system_monitoring.health.get_database_manager")
    @patch("src.api.v1.system.system_monitoring.health.psutil")
    def test_filesystem_warning_on_high_usage(self, mock_psutil, mock_get_db):
        """测试文件系统使用率高时显示警告"""
        from src.api.v1.system.system_monitoring.health import check_component_health

        mock_get_db.return_value = None

        mock_disk = MagicMock(percent=92, free=10 * 1024**3)
        mock_psutil.disk_usage.return_value = mock_disk
        mock_memory = MagicMock(percent=60, available=8 * 1024**3)
        mock_psutil.virtual_memory.return_value = mock_memory

        result = check_component_health()

        assert result["filesystem"]["status"] == "warning"

    @patch("src.api.v1.system.system_monitoring.health.get_database_manager")
    @patch("src.api.v1.system.system_monitoring.health.psutil")
    def test_memory_warning_on_high_usage(self, mock_psutil, mock_get_db):
        """测试内存使用率高时显示警告"""
        from src.api.v1.system.system_monitoring.health import check_component_health

        mock_get_db.return_value = None

        mock_disk = MagicMock(percent=50, free=100 * 1024**3)
        mock_psutil.disk_usage.return_value = mock_disk
        mock_memory = MagicMock(percent=90, available=2 * 1024**3)
        mock_psutil.virtual_memory.return_value = mock_memory

        result = check_component_health()

        assert result["memory"]["status"] == "warning"

    @patch("src.api.v1.system.system_monitoring.health.get_database_manager")
    @patch("src.api.v1.system.system_monitoring.health.psutil")
    def test_database_unhealthy_when_manager_none(self, mock_psutil, mock_get_db):
        """测试数据库管理器为空时状态为 unhealthy"""
        from src.api.v1.system.system_monitoring.health import check_component_health

        mock_get_db.return_value = None

        mock_disk = MagicMock(percent=50, free=100 * 1024**3)
        mock_psutil.disk_usage.return_value = mock_disk
        mock_memory = MagicMock(percent=60, available=8 * 1024**3)
        mock_psutil.virtual_memory.return_value = mock_memory

        result = check_component_health()

        assert result["database"]["status"] == "unhealthy"


class TestCalculateOverallHealthScore:
    """calculate_overall_health_score 函数测试"""

    def test_empty_components(self):
        """测试空组件列表"""
        from src.api.v1.system.system_monitoring.health import (
            calculate_overall_health_score,
        )

        result = calculate_overall_health_score({})
        assert result == 0.0

    def test_all_healthy(self):
        """测试所有组件健康"""
        from src.api.v1.system.system_monitoring.health import (
            calculate_overall_health_score,
        )

        components = {
            "database": {"status": "healthy"},
            "cache": {"status": "healthy"},
            "filesystem": {"status": "healthy"},
        }

        result = calculate_overall_health_score(components)
        assert result == 100.0

    def test_all_unhealthy(self):
        """测试所有组件不健康"""
        from src.api.v1.system.system_monitoring.health import (
            calculate_overall_health_score,
        )

        components = {
            "database": {"status": "unhealthy"},
            "cache": {"status": "unhealthy"},
            "filesystem": {"status": "unhealthy"},
        }

        result = calculate_overall_health_score(components)
        assert result == 0.0

    def test_mixed_status(self):
        """测试混合状态"""
        from src.api.v1.system.system_monitoring.health import (
            calculate_overall_health_score,
        )

        components = {
            "database": {"status": "healthy"},  # 100
            "cache": {"status": "warning"},  # 70
            "filesystem": {"status": "degraded"},  # 50
            "memory": {"status": "unhealthy"},  # 0
        }

        result = calculate_overall_health_score(components)
        expected = (100 + 70 + 50 + 0) / 4
        assert result == expected

    def test_warning_status(self):
        """测试警告状态"""
        from src.api.v1.system.system_monitoring.health import (
            calculate_overall_health_score,
        )

        components = {
            "database": {"status": "warning"},
            "cache": {"status": "warning"},
        }

        result = calculate_overall_health_score(components)
        assert result == 70.0

    def test_unknown_status(self):
        """测试未知状态"""
        from src.api.v1.system.system_monitoring.health import (
            calculate_overall_health_score,
        )

        components = {
            "database": {"status": "unknown_status"},
        }

        result = calculate_overall_health_score(components)
        assert result == 0.0
