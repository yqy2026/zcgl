"""
高级Mock服务系统
提供完全模拟的PDF处理服务，避免真实PaddleOCR加载
"""

import asyncio
import time
from typing import Any
from unittest.mock import Mock


class MockPDFProcessingService:
    """模拟PDF处理服务 - 完全避免真实OCR调用"""

    def __init__(self, config: dict | None = None):
        """初始化模拟服务"""
        self.config = config or {}
        self.ocr = self._create_mock_ocr()
        self.supported_methods = ["pdfplumber", "pymupdf", "ocr"]
        self._processing_stats = {
            "total_processed": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
        }

    def _create_mock_ocr(self):
        """创建模拟OCR服务"""
        mock_ocr = Mock()
        mock_ocr.ocr = lambda img_path: {
            "text": f"模拟OCR识别的文本内容 - {img_path}",
            "confidence": 0.95,
            "regions": [
                {
                    "text": "权属方：国资集团",
                    "bbox": [100, 100, 300, 150],
                    "confidence": 0.98,
                },
                {
                    "text": "物业名称：测试物业",
                    "bbox": [100, 200, 350, 250],
                    "confidence": 0.96,
                },
            ],
        }
        return mock_ocr

    async def process_pdf_async(
        self, pdf_path: str, method: str = "auto"
    ) -> dict[str, Any]:
        """异步模拟PDF处理"""
        start_time = time.time()

        # 模拟处理时间（根据方法不同）
        processing_times = {"pdfplumber": 0.1, "pymupdf": 0.05, "ocr": 0.3, "auto": 0.2}

        # 模拟异步处理延迟
        await asyncio.sleep(processing_times.get(method, 0.2))

        processing_time = time.time() - start_time
        self._update_stats(processing_time)

        # 返回模拟的处理结果
        return {
            "status": "success",
            "text_content": self._generate_mock_text_content(),
            "metadata": self._generate_mock_metadata(),
            "pages": 3,
            "extraction_method": method,
            "processing_time": processing_time,
            "confidence": 0.95,
        }

    def _generate_mock_text_content(self) -> str:
        """生成模拟的PDF文本内容"""
        return """权属方：国资集团
管理方：测试管理公司
项目名称：测试地产项目
物业名称：测试商业中心
地址：广州市测试区测试路123号
确权状态：已确权
物业性质：经营性
使用状态：出租
土地面积：1000.0平方米
实际房产面积：800.0平方米
可出租面积：600.0平方米
已出租面积：400.0平方米
年收入：500000.0元
年支出：200000.0元
净收入：300000.0元"""

    def _generate_mock_metadata(self) -> dict[str, Any]:
        """生成模拟的PDF元数据"""
        return {
            "title": "测试PDF文档",
            "author": "测试生成器",
            "created_date": "2025-01-01",
            "page_count": 3,
            "file_size": 1024000,
            "format": "PDF 1.4",
        }

    def _update_stats(self, processing_time: float):
        """更新处理统计信息"""
        self._processing_stats["total_processed"] += 1
        self._processing_stats["total_time"] += processing_time
        self._processing_stats["avg_time"] = (
            self._processing_stats["total_time"]
            / self._processing_stats["total_processed"]
        )

    def get_stats(self) -> dict[str, Any]:
        """获取处理统计信息"""
        return self._processing_stats.copy()


class MockPDFImportService:
    """模拟PDF导入服务"""

    def __init__(self):
        """初始化模拟导入服务"""
        self.processing_service = MockPDFProcessingService()
        self.session_service = MockPDFSessionService()
        self.import_stats = {
            "total_imports": 0,
            "successful_imports": 0,
            "failed_imports": 0,
        }

    async def process_pdf_file(
        self,
        db,
        session_id: str,
        user_id: int,
        organization_id: int | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """模拟PDF文件导入处理"""
        start_time = time.time()

        try:
            # 模拟处理步骤
            processing_result = await self.processing_service.process_pdf_async(
                session_id, method="auto"
            )

            # 模拟数据验证和转换
            extracted_data = self._convert_to_asset_data(processing_result)

            # 模拟数据库保存延迟
            await asyncio.sleep(0.1)

            processing_time = time.time() - start_time
            self._update_import_stats(success=True)

            return {
                "status": "success",
                "extracted_data": extracted_data,
                "processing_info": processing_result,
                "session_id": session_id,
                "processing_time": processing_time,
                "validation_errors": [],
                "warnings": [],
            }

        except Exception as e:
            processing_time = time.time() - start_time
            self._update_import_stats(success=False)

            return {
                "status": "error",
                "error": str(e),
                "session_id": session_id,
                "processing_time": processing_time,
                "validation_errors": [str(e)],
                "warnings": ["模拟处理错误"],
            }

    def _convert_to_asset_data(
        self, processing_result: dict[str, Any]
    ) -> dict[str, Any]:
        """将处理结果转换为资产数据"""
        return {
            "ownership_entity": "国资集团",
            "management_entity": "测试管理公司",
            "project_name": "测试地产项目",
            "property_name": "测试商业中心",
            "address": "广州市测试区测试路123号",
            "ownership_status": "已确权",
            "property_nature": "经营性",
            "actual_usage": "商业",
            "usage_status": "出租",
            "land_area": 1000.0,
            "actual_property_area": 800.0,
            "rentable_area": 600.0,
            "rented_area": 400.0,
            "unrented_area": 200.0,
            "annual_income": 500000.0,
            "annual_expense": 200000.0,
            "net_income": 300000.0,
            "confidence": processing_result.get("confidence", 0.95),
            "extraction_method": processing_result.get("extraction_method", "auto"),
        }

    def _update_import_stats(self, success: bool):
        """更新导入统计信息"""
        self.import_stats["total_imports"] += 1
        if success:
            self.import_stats["successful_imports"] += 1
        else:
            self.import_stats["failed_imports"] += 1

    def get_import_stats(self) -> dict[str, Any]:
        """获取导入统计信息"""
        return self.import_stats.copy()


class MockPDFSessionService:
    """模拟PDF会话服务"""

    def __init__(self):
        """初始化会话服务"""
        self.sessions = {}
        self.session_counter = 1000

    def create_session(
        self,
        db,
        filename: str = "test.pdf",
        file_size: int = 1024000,
        file_path: str = "/tmp/test.pdf",
    ) -> str:
        """创建新的模拟会话"""
        session_id = f"mock_session_{self.session_counter}"
        self.session_counter += 1

        self.sessions[session_id] = {
            "session_id": session_id,
            "filename": filename,
            "file_size": file_size,
            "file_path": file_path,
            "status": "created",
            "progress": 0,
            "created_at": time.time(),
            "updated_at": time.time(),
        }

        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """获取会话信息"""
        return self.sessions.get(session_id)

    def update_session(self, session_id: str, **kwargs) -> bool:
        """更新会话信息"""
        if session_id in self.sessions:
            self.sessions[session_id].update(kwargs)
            self.sessions[session_id]["updated_at"] = time.time()
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self.services:
            del self.sessions[session_id]
            return True
        return False

    def get_all_sessions(self) -> list[dict[str, Any]]:
        """获取所有会话"""
        return list(self.sessions.values())


class MockDatabaseService:
    """模拟数据库服务"""

    def __init__(self):
        """初始化模拟数据库服务"""
        self.assets = {}
        self.operations_count = 0

    def add(self, obj) -> None:
        """模拟数据库添加操作"""
        if hasattr(obj, "id"):
            self.assets[obj.id] = obj
        self.operations_count += 1

    def commit(self) -> None:
        """模拟数据库提交操作"""
        pass

    def query(self, model):
        """模拟数据库查询操作"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_query.all.return_value = []
        return mock_query

    def refresh(self, obj) -> None:
        """模拟数据库刷新操作"""
        pass


def create_mock_services():
    """创建完整的模拟服务套件"""
    return {
        "pdf_processing_service": MockPDFProcessingService(),
        "pdf_import_service": MockPDFImportService(),
        "session_service": MockPDFSessionService(),
        "database_service": MockDatabaseService(),
    }


def create_optimized_test_environment():
    """创建优化的测试环境"""
    env_config = {
        # PaddleOCR性能优化
        "PADDLEOCR_USE_CPU": "1",
        "PADDLEOCR_USE_GPU": "0",
        "PADDLEOCR_PP_DEBUG": "0",
        "PADDLEOCR_SHOW_LOG": "False",
        "PADDLEOCR_USE_MP": "False",
        # 其他性能优化
        "PYTHONPATH": "./src",
        "CUDA_VISIBLE_DEVICES": "",
    }

    for key, value in env_config.items():
        import os

        os.environ[key] = value

    return env_config


# 快速测试预设数据
MOCK_PDF_DATA = {
    "valid_pdf": {
        "content": b"%PDF-1.4\nTest PDF Content",
        "size": 1024,
        "filename": "test_valid.pdf",
    },
    "large_pdf": {
        "content": b"%PDF-1.4\n" + b"X" * (10 * 1024 * 1024),  # 10MB
        "size": 10 * 1024 * 1024,
        "filename": "test_large.pdf",
    },
    "malicious_pdf": {
        "content": b"%PDF-1.4\nmalicious script content alert()",
        "size": 2048,
        "filename": "test_malicious.pdf",
    },
}

MOCK_EXTRACTION_RESULTS = {
    "success_result": {
        "status": "success",
        "extracted_data": {
            "ownership_entity": "国资集团",
            "property_name": "测试物业",
            "address": "广州市测试地址",
            "land_area": 1000.0,
            "actual_property_area": 800.0,
            "rentable_area": 600.0,
            "rented_area": 400.0,
            "ownership_status": "已确权",
            "property_nature": "经营性",
            "usage_status": "出租",
        },
        "processing_time": 0.5,
        "validation_errors": [],
        "warnings": [],
    },
    "error_result": {
        "status": "error",
        "error": "PDF解析失败",
        "validation_errors": ["文件格式不正确"],
        "warnings": ["检测到潜在问题"],
    },
}
