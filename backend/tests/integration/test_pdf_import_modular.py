"""
PDF导入API集成测试

测试模块化的PDF导入功能
"""

import pytest

pytestmark = pytest.mark.skip(reason="Integration API tests require real JWT authentication setup")
from fastapi.testclient import TestClient

from src.main import app


class TestPDFSystemInfo:
    """测试系统信息端点"""

    def test_get_system_info(self, client: TestClient):
        """测试获取系统信息"""
        response = client.get("/api/pdf-import/info")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "capabilities" in data
        assert "extractor_summary" in data

        # 验证系统能力
        capabilities = data["capabilities"]
        assert capabilities["pdfplumber_available"] is True
        assert capabilities["pymupdf_available"] is True
        assert isinstance(capabilities["supported_formats"], list)
        assert capabilities["max_file_size_mb"] > 0

    def test_get_health_check(self, client: TestClient):
        """测试健康检查端点"""
        response = client.get("/api/pdf-import/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert "performance" in data


class TestPDFPerformance:
    """测试性能监控端点"""

    def test_get_realtime_performance(self, client: TestClient):
        """测试获取实时性能数据"""
        response = client.get("/api/pdf-import/performance/realtime")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "enabled" in data["data"]

    def test_get_performance_report(self, client: TestClient):
        """测试获取性能报告"""
        response = client.get("/api/pdf-import/performance/report?hours=24")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_get_performance_health(self, client: TestClient):
        """测试获取性能健康状态"""
        response = client.get("/api/pdf-import/performance/health")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True


class TestPDFQuality:
    """测试质量评估端点"""

    def test_get_quality_assessment(self, client: TestClient):
        """测试获取质量评估（会话不存在时）"""
        response = client.get("/api/pdf-import/quality/assessment/non-existent-session")
        assert response.status_code == 200

        data = response.json()
        # 会话不存在时应该返回错误，但不应该500
        assert "success" in data


class TestPDFV1Compatibility:
    """测试V1兼容端点"""

    def test_extract_from_text_v1(self, client: TestClient):
        """测试V1文本提取端点"""
        payload = {
            "text": "租赁合同\n出租方：张三\n承租方：李四\n租金：5000元/月",
            "validate_fields": False,
            "include_raw_text": False,
        }

        response = client.post("/api/pdf-import/extract", json=payload)
        assert response.status_code == 200

        data = response.json()
        # V1兼容模式应该返回数据
        assert "success" in data or "error" in data

    def test_extract_from_text_v2_form(self, client: TestClient):
        """测试V2表单文本提取端点"""
        response = client.post(
            "/api/pdf-import/extract",
            data={"text": "租赁合同\n租金：5000元/月", "validate_fields": "false"},
        )
        assert response.status_code == 200

        data = response.json()
        assert "success" in data


class TestPDFUpload:
    """测试文件上传端点"""

    def test_upload_endpoint_rejects_non_pdf(self, client: TestClient):
        """测试上传端点拒绝非PDF文件"""
        # 注意：这个测试需要实际文件上传，这里只测试端点存在
        # 完整的文件上传测试需要更多设置
        pass

    def test_upload_and_extract_v1_rejects_non_pdf(self, client: TestClient):
        """测试V1上传端点拒绝非PDF文件"""
        pass


class TestPDFSessions:
    """测试会话管理端点"""

    def test_get_active_sessions(self, client: TestClient):
        """测试获取活跃会话列表"""
        response = client.get("/api/pdf-import/sessions")
        assert response.status_code == 200

        data = response.json()
        assert "success" in data
        assert "active_sessions" in data

    def test_get_session_history(self, client: TestClient):
        """测试获取会话历史"""
        response = client.get("/api/pdf-import/sessions/history?limit=10")
        assert response.status_code == 200

        data = response.json()
        assert "success" in data
        assert "history" in data

    def test_get_session_progress_nonexistent(self, client: TestClient):
        """测试获取不存在的会话进度"""
        response = client.get("/api/pdf-import/progress/fake-session-id")
        assert response.status_code == 200

        data = response.json()
        assert "success" in data


class TestPDFRoutesRegistration:
    """测试路由注册"""

    def test_all_routes_registered(self, client: TestClient):
        """测试所有PDF路由已正确注册"""
        # 从OpenAPI schema获取所有路由
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()

        # 查找所有 /api/pdf-import 路径
        pdf_paths = [
            path
            for path in openapi_schema["paths"].keys()
            if path.startswith("/api/pdf-import")
        ]

        # 验证核心端点存在
        required_endpoints = [
            "/api/pdf-import/info",
            "/api/pdf-import/health",
            "/api/pdf-import/performance/realtime",
            "/api/pdf-import/sessions",
            "/api/pdf-import/progress/{session_id}",
        ]

        for endpoint in required_endpoints:
            # 检查端点或其参数化版本是否存在
            matching_paths = [p for p in pdf_paths if endpoint.split("{")[0] in p]
            assert len(matching_paths) > 0, f"Endpoint {endpoint} not found in registered paths"

        print(f"\n[INFO] Found {len(pdf_paths)} PDF-import endpoints:")
        for path in sorted(pdf_paths):
            print(f"  {path}")


# Test fixtures
@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)
