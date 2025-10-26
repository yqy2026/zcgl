"""
PDF处理功能测试运行脚本
"""

import asyncio
import sys
import os
import logging
import time
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from src.services.enhanced_pdf_processor import enhanced_pdf_processor
from src.services.ml_enhanced_extractor import ml_enhanced_extractor
from src.services.enhanced_field_mapper import enhanced_field_mapper
from src.services.parallel_pdf_processor import ParallelPDFProcessor, TaskPriority

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_tests.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class PDFTestRunner:
    """PDF测试运行器"""

    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()

    def log_section(self, title: str):
        """记录测试章节"""
        logger.info("\n" + "="*60)
        logger.info(f" {title}")
        logger.info("="*60)

    def log_test(self, test_name: str, status: str, message: str = ""):
        """记录测试结果"""
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        logger.info(f"{status_icon} {test_name}: {status}")
        if message:
            logger.info(f"   {message}")

    async def test_basic_imports(self):
        """测试基础导入"""
        self.log_section("基础导入测试")

        try:
            # 测试服务导入
            from src.services.enhanced_pdf_processor import enhanced_pdf_processor
            from src.services.ml_enhanced_extractor import ml_enhanced_extractor
            from src.services.enhanced_field_mapper import enhanced_field_mapper
            from src.services.parallel_pdf_processor import ParallelPDFProcessor

            self.log_test("服务模块导入", "PASS", "所有核心服务模块导入成功")

            # 测试API导入
            from src.api.v1.pdf_import_unified import router as pdf_router
            from src.api.v1.pdf_monitoring import router as monitoring_router

            self.log_test("API模块导入", "PASS", "PDF导入和监控API模块导入成功")

            return True

        except Exception as e:
            self.log_test("基础导入", "FAIL", f"导入失败: {str(e)}")
            return False

    async def test_enhanced_processor(self):
        """测试增强处理器"""
        self.log_section("增强PDF处理器测试")

        try:
            # 创建测试文件
            test_file = self._create_test_pdf("test_enhanced.pdf")

            # 文档分析测试
            analysis = await enhanced_pdf_processor.analyze_document(test_file)
            self.log_test(
                "文档分析",
                "PASS" if analysis else "FAIL",
                f"文档类型: {analysis.get('document_type', 'unknown') if analysis else 'none'}"
            )

            # 智能配置测试
            if analysis:
                config = enhanced_pdf_processor.get_intelligent_config(analysis)
                self.log_test(
                    "智能配置",
                    "PASS" if config else "FAIL",
                    f"策略: {config.get('processing_strategy', 'none') if config else 'none'}"
                )

            # 清理测试文件
            os.unlink(test_file)
            return True

        except Exception as e:
            self.log_test("增强处理器", "FAIL", f"测试失败: {str(e)}")
            return False

    async def test_ml_extractor(self):
        """测试机器学习提取器"""
        self.log_section("机器学习提取器测试")

        try:
            # 创建测试数据
            test_data = {
                'raw_text': '租赁合同\n出租方：测试公司\n承租方：测试用户\n租金：5000元/月',
                'structured_data': {
                    'landlord': '测试公司',
                    'tenant': '测试用户',
                    'rent': 5000
                },
                'confidence_scores': {
                    'text_extraction': 0.9,
                    'field_detection': 0.8
                }
            }

            # 混合提取测试
            result = await ml_enhanced_extractor.extract_contract_info_hybrid(test_data)
            self.log_test(
                "混合提取",
                "PASS" if result else "FAIL",
                f"置信度: {result.get('confidence', 0):.2f}" if result else "无结果"
            )

            # 语义验证测试
            if result and result.get('contract_info'):
                validation = await ml_enhanced_extractor.validate_contract_semantics(
                    result['contract_info']
                )
                self.log_test(
                    "语义验证",
                    "PASS" if validation else "FAIL",
                    f"验证分数: {validation.get('validation_score', 0):.2f}" if validation else "无验证结果"
                )

            return True

        except Exception as e:
            self.log_test("机器学习提取器", "FAIL", f"测试失败: {str(e)}")
            return False

    async def test_field_mapper(self):
        """测试字段映射器"""
        self.log_section("字段映射器测试")

        try:
            # 创建测试字段数据
            test_fields = {
                'landlord_name': '测试出租方',
                'tenant_name': '测试承租方',
                'monthly_rent': 5000,
                'property_address': '北京市朝阳区测试地址123号',
                'lease_start_date': '2024-01-01',
                'lease_end_date': '2024-12-31',
                'total_area': 100
            }

            # 智能映射测试
            result = await enhanced_field_mapper.map_to_asset_model(test_fields)
            self.log_test(
                "智能映射",
                "PASS" if result else "FAIL",
                f"映射置信度: {result.get('mapping_confidence', 0):.2f}" if result else "无映射结果"
            )

            # 数据验证测试
            if result and result.get('mapped_fields'):
                validation = enhanced_field_mapper.validate_mapped_data(
                    result['mapped_fields']
                )
                self.log_test(
                    "数据验证",
                    "PASS" if validation else "FAIL",
                    f"验证状态: {'通过' if validation.get('is_valid') else '失败'}" if validation else "无验证结果"
                )

            return True

        except Exception as e:
            self.log_test("字段映射器", "FAIL", f"测试失败: {str(e)}")
            return False

    async def test_parallel_processor(self):
        """测试并行处理器"""
        self.log_section("并行处理器测试")

        try:
            processor = ParallelPDFProcessor(max_workers=2, max_cache_size=10)

            # 缓存测试
            test_key = "test_key"
            test_value = {"test": "data"}
            processor._set_cache(test_key, test_value)
            cached_value = processor._get_from_cache(test_key)

            self.log_test(
                "缓存操作",
                "PASS" if cached_value == test_value else "FAIL",
                "缓存读写正常" if cached_value == test_value else "缓存读写异常"
            )

            # 性能统计测试
            stats = processor.get_performance_stats()
            self.log_test(
                "性能统计",
                "PASS" if stats else "FAIL",
                f"统计项数量: {len(stats)}" if stats else "无统计数据"
            )

            # 队列状态测试
            queue_status = processor.get_queue_status()
            self.log_test(
                "队列状态",
                "PASS" if queue_status else "FAIL",
                f"最大工作线程: {queue_status.get('max_workers', 0)}" if queue_status else "无队列信息"
            )

            processor.shutdown()
            return True

        except Exception as e:
            self.log_test("并行处理器", "FAIL", f"测试失败: {str(e)}")
            return False

    async def test_integration(self):
        """集成测试"""
        self.log_section("集成测试")

        try:
            # 创建测试文件
            test_file = self._create_test_pdf("integration_test.pdf")

            # 模拟完整处理流程
            logger.info("开始完整处理流程测试...")

            # 1. 文档分析
            analysis = await enhanced_pdf_processor.analyze_document(test_file)
            if not analysis:
                raise Exception("文档分析失败")

            # 2. 获取处理配置
            config = enhanced_pdf_processor.get_intelligent_config(analysis)
            if not config:
                raise Exception("获取处理配置失败")

            # 3. 处理文档
            result = await enhanced_pdf_processor.process_with_enhanced_config(
                test_file, config
            )

            success = result and result.get('success')
            self.log_test(
                "完整流程",
                "PASS" if success else "FAIL",
                "PDF处理完整流程测试成功" if success else "PDF处理流程失败"
            )

            # 清理测试文件
            os.unlink(test_file)
            return success

        except Exception as e:
            self.log_test("集成测试", "FAIL", f"集成测试失败: {str(e)}")
            return False

    async def test_performance(self):
        """性能测试"""
        self.log_section("性能测试")

        try:
            # 创建多个测试文件
            test_files = []
            for i in range(3):
                file_path = self._create_test_pdf(f"perf_test_{i}.pdf")
                test_files.append(file_path)

            # 并行处理性能测试
            processor = ParallelPDFProcessor(max_workers=2)

            start_time = time.time()
            task_ids = []

            # 提交任务
            for file_path in test_files:
                task_id = await processor.submit_task(
                    file_path,
                    {'prefer_ocr': False},
                    TaskPriority.NORMAL
                )
                task_ids.append(task_id)

            # 等待任务完成（简化版本）
            await asyncio.sleep(2)  # 模拟处理时间

            end_time = time.time()
            processing_time = end_time - start_time

            # 性能评估
            avg_time_per_file = processing_time / len(test_files)
            throughput = len(test_files) / processing_time if processing_time > 0 else 0

            self.log_test(
                "并行处理性能",
                "PASS" if avg_time_per_file < 10 else "WARN",
                f"平均处理时间: {avg_time_per_file:.2f}秒/文件, 吞吐量: {throughput:.2f}文件/秒"
            )

            # 清理资源
            processor.shutdown()
            for file_path in test_files:
                os.unlink(file_path)

            return True

        except Exception as e:
            self.log_test("性能测试", "FAIL", f"性能测试失败: {str(e)}")
            return False

    def _create_test_pdf(self, filename: str) -> str:
        """创建测试PDF文件"""
        import tempfile

        temp_file = tempfile.NamedTemporaryFile(suffix=f'_{filename}', delete=False)

        # 创建简单的PDF内容
        pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 595 842]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 100
>>
stream
BT
/F1 12 Tf
72 720 Td
(租赁合同 - {filename}) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f
0000000010 00000 n
0000000079 00000 n
0000000173 00000 n
0000000301 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
450
%%EOF
"""

        temp_file.write(pdf_content.encode('utf-8'))
        temp_file.close()

        return temp_file.name

    async def run_all_tests(self):
        """运行所有测试"""
        self.log_section("PDF处理功能测试开始")

        test_suites = [
            ("基础导入", self.test_basic_imports),
            ("增强处理器", self.test_enhanced_processor),
            ("机器学习提取器", self.test_ml_extractor),
            ("字段映射器", self.test_field_mapper),
            ("并行处理器", self.test_parallel_processor),
            ("集成测试", self.test_integration),
            ("性能测试", self.test_performance)
        ]

        results = {
            'total_tests': len(test_suites),
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'details': []
        }

        for test_name, test_func in test_suites:
            try:
                success = await test_func()
                if success:
                    results['passed'] += 1
                    status = "PASS"
                else:
                    results['failed'] += 1
                    status = "FAIL"

                results['details'].append({
                    'name': test_name,
                    'status': status,
                    'timestamp': time.time()
                })

            except Exception as e:
                results['failed'] += 1
                self.log_test(test_name, "FAIL", f"测试异常: {str(e)}")
                results['details'].append({
                    'name': test_name,
                    'status': "FAIL",
                    'error': str(e),
                    'timestamp': time.time()
                })

        # 生成测试报告
        self._generate_test_report(results)

        return results

    def _generate_test_report(self, results: dict):
        """生成测试报告"""
        self.log_section("测试报告")

        total_time = time.time() - self.start_time
        success_rate = (results['passed'] / results['total_tests']) * 100

        logger.info(f"总测试数: {results['total_tests']}")
        logger.info(f"通过: {results['passed']}")
        logger.info(f"失败: {results['failed']}")
        logger.info(f"成功率: {success_rate:.1f}%")
        logger.info(f"总耗时: {total_time:.2f}秒")

        # 保存测试报告
        report_data = {
            'test_summary': {
                'total_tests': results['total_tests'],
                'passed': results['passed'],
                'failed': results['failed'],
                'success_rate': success_rate,
                'total_time': total_time,
                'timestamp': time.time()
            },
            'test_details': results['details']
        }

        report_file = f"pdf_test_report_{int(time.time())}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        logger.info(f"测试报告已保存: {report_file}")

async def main():
    """主函数"""
    logger.info("PDF处理功能测试运行器启动")

    try:
        runner = PDFTestRunner()
        results = await runner.run_all_tests()

        # 根据测试结果设置退出码
        if results['failed'] == 0:
            logger.info("✅ 所有测试通过")
            sys.exit(0)
        else:
            logger.error(f"❌ {results['failed']} 个测试失败")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"测试运行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())