"""
PDF处理性能基准测试
"""

import asyncio
import json
import logging
import os
import statistics
import tempfile
import time
from typing import Any

from src.services.enhanced_field_mapper import enhanced_field_mapper
from src.services.enhanced_pdf_processor import enhanced_pdf_processor
from src.services.ml_enhanced_extractor import ml_enhanced_extractor
from src.services.parallel_pdf_processor import ParallelPDFProcessor, TaskPriority

logger = logging.getLogger(__name__)


class PDFProcessingBenchmark:
    """PDF处理性能基准测试类"""

    def __init__(self):
        self.results = {}
        self.test_files = []

    def create_test_files(self, count: int = 10) -> list[str]:
        """创建测试文件"""
        files = []

        for i in range(count):
            # 创建不同大小的测试PDF文件
            content_sizes = [
                1024,  # 1KB - 小文件
                10240,  # 10KB - 中等文件
                102400,  # 100KB - 大文件
                512000,  # 500KB - 超大文件
            ]

            size = content_sizes[i % len(content_sizes)]

            temp_file = tempfile.NamedTemporaryFile(
                suffix=f"_benchmark_{i}_{size}B.pdf", delete=False
            )

            # 生成模拟PDF内容
            content = self._generate_pdf_content(size)
            temp_file.write(content.encode("utf-8"))
            temp_file.close()

            files.append(temp_file.name)

        self.test_files = files
        return files

    def _generate_pdf_content(self, size: int) -> str:
        """生成指定大小的PDF内容"""
        base_content = """
%PDF-1.4
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
/Length {content_length}
>>
stream
BT
/F1 12 Tf
72 720 Td
(content) Tj
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
{cross_ref}
%%EOF
        """

        # 重复内容以达到目标大小
        target_length = (
            size - len(base_content) + len("{content_length}") + len("{cross_ref}")
        )
        repeat_count = max(1, target_length // 100)

        content = "租赁合同\n" * repeat_count
        content += f"出租方：测试公司{i}\n" * (repeat_count // 2)
        content += f"承租方：测试用户{i}\n" * (repeat_count // 2)
        content += f"租金：{5000 + i * 100}元/月\n" * (repeat_count // 3)
        content += f"地址：测试地址{i}号\n" * (repeat_count // 3)

        # 填充到目标大小
        while len(content.encode("utf-8")) < size:
            content += "测试内容\n"

        return base_content.format(
            content_length=len(content),
            content=content[: size - 200],  # 保留PDF结构的空间
            cross_ref=len(content) + 200,
        )

    async def benchmark_enhanced_processor(
        self, file_paths: list[str]
    ) -> dict[str, Any]:
        """基准测试增强处理器"""
        times = []
        success_count = 0
        error_count = 0

        for file_path in file_paths:
            try:
                start_time = time.time()

                result = await enhanced_pdf_processor.process_with_enhanced_config(
                    file_path
                )

                end_time = time.time()
                processing_time = end_time - start_time

                times.append(processing_time)

                if result.get("success"):
                    success_count += 1
                else:
                    error_count += 1

                logger.info(
                    f"文件 {os.path.basename(file_path)} 处理时间: {processing_time:.2f}秒"
                )

            except Exception as e:
                error_count += 1
                logger.error(f"处理文件失败 {file_path}: {str(e)}")

        return {
            "processor": "enhanced_pdf_processor",
            "total_files": len(file_paths),
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": success_count / len(file_paths) if file_paths else 0,
            "times": times,
            "avg_time": statistics.mean(times) if times else 0,
            "min_time": min(times) if times else 0,
            "max_time": max(times) if times else 0,
            "median_time": statistics.median(times) if times else 0,
            "total_time": sum(times),
            "throughput": len(file_paths) / sum(times) if times else 0,
        }

    async def benchmark_parallel_processor(
        self, file_paths: list[str]
    ) -> dict[str, Any]:
        """基准测试并行处理器"""
        processor = ParallelPDFProcessor(max_workers=4)

        try:
            start_time = time.time()

            # 提交所有任务
            task_ids = []
            for file_path in file_paths:
                task_id = await processor.submit_task(
                    file_path, {"prefer_ocr": False}, TaskPriority.NORMAL
                )
                task_ids.append(task_id)

            # 等待所有任务完成
            completed_tasks = []
            max_wait_time = 300  # 最大等待5分钟
            wait_start = time.time()

            while (
                len(completed_tasks) < len(task_ids)
                and (time.time() - wait_start) < max_wait_time
            ):
                await asyncio.sleep(1)

                for task_id in task_ids:
                    if task_id not in [t.task_id for t in completed_tasks]:
                        task = processor.get_task_status(task_id)
                        if task and task.status in ["completed", "failed"]:
                            completed_tasks.append(task)

            end_time = time.time()
            total_time = end_time - start_time

            # 统计结果
            success_count = len([t for t in completed_tasks if t.status == "completed"])
            error_count = len([t for t in completed_tasks if t.status == "failed"])

            # 计算处理时间（简化版本）
            avg_task_time = total_time / len(task_ids) if task_ids else 0

            # 获取性能统计
            perf_stats = processor.get_performance_stats()

            return {
                "processor": "parallel_pdf_processor",
                "total_files": len(file_paths),
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": success_count / len(file_paths) if file_paths else 0,
                "total_time": total_time,
                "avg_task_time": avg_task_time,
                "throughput": len(file_paths) / total_time if total_time > 0 else 0,
                "performance_stats": perf_stats,
            }

        finally:
            processor.shutdown()

    async def benchmark_ml_extractor(
        self, test_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """基准测试机器学习提取器"""
        times = []
        success_count = 0
        error_count = 0

        for data in test_data:
            try:
                start_time = time.time()

                result = await ml_enhanced_extractor.extract_contract_info_hybrid(data)

                end_time = time.time()
                processing_time = end_time - start_time

                times.append(processing_time)

                if result and result.get("confidence", 0) > 0.5:
                    success_count += 1
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
                logger.error(f"ML提取失败: {str(e)}")

        return {
            "processor": "ml_enhanced_extractor",
            "total_tests": len(test_data),
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": success_count / len(test_data) if test_data else 0,
            "times": times,
            "avg_time": statistics.mean(times) if times else 0,
            "min_time": min(times) if times else 0,
            "max_time": max(times) if times else 0,
            "median_time": statistics.median(times) if times else 0,
        }

    async def benchmark_field_mapper(
        self, test_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """基准测试字段映射器"""
        times = []
        success_count = 0
        error_count = 0

        for data in test_data:
            try:
                start_time = time.time()

                result = await enhanced_field_mapper.map_to_asset_model(data)

                end_time = time.time()
                processing_time = end_time - start_time

                times.append(processing_time)

                if result and result.get("mapping_confidence", 0) > 0.5:
                    success_count += 1
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
                logger.error(f"字段映射失败: {str(e)}")

        return {
            "processor": "enhanced_field_mapper",
            "total_tests": len(test_data),
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": success_count / len(test_data) if test_data else 0,
            "times": times,
            "avg_time": statistics.mean(times) if times else 0,
            "min_time": min(times) if times else 0,
            "max_time": max(times) if times else 0,
            "median_time": statistics.median(times) if times else 0,
        }

    def create_test_data(self, count: int = 20) -> list[dict[str, Any]]:
        """创建测试数据"""
        test_data = []

        for i in range(count):
            data = {
                "raw_text": f"""
                租赁合同第{i+1}号

                出租方：测试出租方{i+1}
                承租方：测试承租方{i+1}

                租赁房屋地址：测试地址{i+1}号
                建筑面积：{100 + i * 10}平方米
                租金：{5000 + i * 100}元/月

                租赁期限：自2024年1月1日至2024年12月31日

                其他条款：标准租赁条款
                """,
                "structured_data": {
                    "landlord": f"测试出租方{i+1}",
                    "tenant": f"测试承租方{i+1}",
                    "address": f"测试地址{i+1}号",
                    "area": 100 + i * 10,
                    "rent": 5000 + i * 100,
                    "lease_start": "2024-01-01",
                    "lease_end": "2024-12-31",
                },
                "confidence_scores": {
                    "text_extraction": 0.9 + (i % 10) * 0.01,
                    "field_detection": 0.8 + (i % 10) * 0.02,
                },
            }
            test_data.append(data)

        return test_data

    async def run_full_benchmark(self) -> dict[str, Any]:
        """运行完整基准测试"""
        logger.info("开始PDF处理性能基准测试")

        # 创建测试文件和数据
        test_files = self.create_test_files(15)
        test_data = self.create_test_data(20)

        try:
            results = {
                "benchmark_info": {
                    "timestamp": time.time(),
                    "test_files_count": len(test_files),
                    "test_data_count": len(test_data),
                    "system_info": self._get_system_info(),
                },
                "results": {},
            }

            # 测试增强处理器
            logger.info("测试增强PDF处理器...")
            enhanced_result = await self.benchmark_enhanced_processor(
                test_files[:5]
            )  # 限制文件数量
            results["results"]["enhanced_processor"] = enhanced_result

            # 测试并行处理器
            logger.info("测试并行PDF处理器...")
            parallel_result = await self.benchmark_parallel_processor(test_files[:10])
            results["results"]["parallel_processor"] = parallel_result

            # 测试机器学习提取器
            logger.info("测试机器学习提取器...")
            ml_result = await self.benchmark_ml_extractor(test_data)
            results["results"]["ml_extractor"] = ml_result

            # 测试字段映射器
            logger.info("测试字段映射器...")
            mapper_result = await self.benchmark_field_mapper(test_data)
            results["results"]["field_mapper"] = mapper_result

            # 性能对比分析
            results["analysis"] = self._analyze_results(results["results"])

            return results

        finally:
            # 清理测试文件
            for file_path in test_files:
                try:
                    os.unlink(file_path)
                except:
                    pass

    def _get_system_info(self) -> dict[str, Any]:
        """获取系统信息"""
        import platform

        import psutil

        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage(".").free,
        }

    def _analyze_results(self, results: dict[str, Any]) -> dict[str, Any]:
        """分析基准测试结果"""
        analysis = {"performance_ranking": [], "recommendations": [], "bottlenecks": []}

        # 性能排序（按吞吐量）
        processors = []
        for name, result in results.items():
            if "throughput" in result:
                processors.append(
                    {
                        "name": name,
                        "throughput": result["throughput"],
                        "success_rate": result["success_rate"],
                        "avg_time": result.get("avg_time", 0),
                    }
                )

        processors.sort(key=lambda x: x["throughput"], reverse=True)
        analysis["performance_ranking"] = processors

        # 性能瓶颈分析
        for processor in processors:
            if processor["success_rate"] < 0.8:
                analysis["bottlenecks"].append(
                    {
                        "processor": processor["name"],
                        "issue": "成功率过低",
                        "success_rate": processor["success_rate"],
                    }
                )

            if processor["avg_time"] > 10:  # 超过10秒
                analysis["bottlenecks"].append(
                    {
                        "processor": processor["name"],
                        "issue": "处理时间过长",
                        "avg_time": processor["avg_time"],
                    }
                )

        # 优化建议
        if analysis["bottlenecks"]:
            analysis["recommendations"].append(
                "存在性能瓶颈，建议优化算法或增加硬件资源"
            )

        if any(p["throughput"] < 0.1 for p in processors):
            analysis["recommendations"].append("吞吐量偏低，建议启用并行处理")

        return analysis

    def save_results(self, results: dict[str, Any], filename: str = None):
        """保存基准测试结果"""
        if filename is None:
            timestamp = int(time.time())
            filename = f"pdf_processing_benchmark_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"基准测试结果已保存到: {filename}")
        return filename

    def print_summary(self, results: dict[str, Any]):
        """打印基准测试摘要"""
        print("\n" + "=" * 60)
        print("PDF处理性能基准测试摘要")
        print("=" * 60)

        for processor_name, result in results["results"].items():
            print(f"\n{processor_name}:")
            print(f"  成功率: {result['success_rate']:.1%}")

            if "throughput" in result:
                print(f"  吞吐量: {result['throughput']:.2f} 文件/秒")
                print(f"  平均处理时间: {result.get('avg_time', 0):.2f} 秒")

            if "total_time" in result:
                print(f"  总处理时间: {result['total_time']:.2f} 秒")

        print("\n性能排名:")
        for i, processor in enumerate(results["analysis"]["performance_ranking"], 1):
            print(
                f"  {i}. {processor['name']} - 吞吐量: {processor['throughput']:.2f} 文件/秒"
            )

        if results["analysis"]["recommendations"]:
            print("\n优化建议:")
            for rec in results["analysis"]["recommendations"]:
                print(f"  - {rec}")

        print("=" * 60)


async def main():
    """主函数"""
    benchmark = PDFProcessingBenchmark()

    try:
        # 运行基准测试
        results = await benchmark.run_full_benchmark()

        # 保存结果
        filename = benchmark.save_results(results)

        # 打印摘要
        benchmark.print_summary(results)

        return results

    except Exception as e:
        logger.error(f"基准测试失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 运行基准测试
    asyncio.run(main())
