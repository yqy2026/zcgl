#!/usr/bin/env python3
"""
持续质量监控脚本
Continuous Quality Monitoring Script

该脚本提供自动化的质量监控功能，包括：
- 测试覆盖率监控
- 代码质量检查
- 性能指标监控
- API健康检查
- 质量趋势分析
"""

import os
import sys
import time
import json
import yaml
import asyncio
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

import requests
import psutil


class QualityLevel(Enum):
    """质量等级枚举"""
    EXCELLENT = "excellent"      # 优秀 (90-100分)
    GOOD = "good"                # 良好 (80-89分)
    SATISFACTORY = "satisfactory" # 合格 (70-79分)
    NEEDS_IMPROVEMENT = "needs_improvement"  # 需要改进 (60-69分)
    POOR = "poor"               # 较差 (0-59分)


@dataclass
class QualityMetric:
    """质量指标数据类"""
    name: str
    value: float
    unit: str
    threshold: float
    status: QualityLevel
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


@dataclass
class QualityReport:
    """质量报告数据类"""
    timestamp: datetime
    overall_score: float
    overall_level: QualityLevel
    metrics: List[QualityMetric]
    recommendations: List[str]
    warnings: List[str]


class QualityMonitor:
    """质量监控器主类"""

    def __init__(self, config_path: str = "quality_monitor_config.yaml"):
        """初始化质量监控器"""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.logger = self._setup_logger()
        self.base_dir = Path(__file__).parent.parent

        # 创建必要的目录
        self._ensure_directories()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.error(f"配置文件不存在: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"配置文件格式错误: {e}")
            raise

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("quality_monitor")
        logger.setLevel(logging.INFO)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # 文件处理器
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / "quality_monitor.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(console_formatter)
        logger.addHandler(file_handler)

        return logger

    def _ensure_directories(self):
        """确保必要的目录存在"""
        dirs = ["logs", "reports", "data"]
        for dir_name in dirs:
            (self.base_dir / dir_name).mkdir(exist_ok=True)

    async def run_quick_health_check(self) -> QualityReport:
        """执行快速健康检查"""
        self.logger.info("开始执行快速健康检查...")

        metrics = []

        # 1. 基本语法检查
        syntax_metric = await self._check_syntax()
        metrics.append(syntax_metric)

        # 2. 导入检查
        import_metric = await self._check_imports()
        metrics.append(import_metric)

        # 3. API健康检查
        api_metric = await self._check_api_health()
        metrics.append(api_metric)

        # 4. 基本测试
        basic_test_metric = await self._run_basic_tests()
        metrics.append(basic_test_metric)

        # 计算总体分数
        overall_score = self._calculate_overall_score(metrics)
        overall_level = self._get_quality_level(overall_score)

        # 生成建议和警告
        recommendations, warnings = self._generate_recommendations(metrics)

        report = QualityReport(
            timestamp=datetime.now(),
            overall_score=overall_score,
            overall_level=overall_level,
            metrics=metrics,
            recommendations=recommendations,
            warnings=warnings
        )

        self.logger.info(f"快速健康检查完成 - 总分: {overall_score:.1f} ({overall_level.value})")
        return report

    async def run_comprehensive_check(self) -> QualityReport:
        """执行全面质量检查"""
        self.logger.info("开始执行全面质量检查...")

        metrics = []

        # 1. 测试覆盖率
        coverage_metric = await self._check_test_coverage()
        metrics.append(coverage_metric)

        # 2. 代码质量
        code_quality_metric = await self._check_code_quality()
        metrics.append(code_quality_metric)

        # 3. 测试性能
        performance_metric = await self._check_test_performance()
        metrics.append(performance_metric)

        # 4. 安全检查
        security_metric = await self._check_security()
        metrics.append(security_metric)

        # 5. 复杂度分析
        complexity_metric = await self._check_complexity()
        metrics.append(complexity_metric)

        # 计算总体分数
        overall_score = self._calculate_overall_score(metrics)
        overall_level = self._get_quality_level(overall_score)

        # 生成建议和警告
        recommendations, warnings = self._generate_recommendations(metrics)

        report = QualityReport(
            timestamp=datetime.now(),
            overall_score=overall_score,
            overall_level=overall_level,
            metrics=metrics,
            recommendations=recommendations,
            warnings=warnings
        )

        self.logger.info(f"全面质量检查完成 - 总分: {overall_score:.1f} ({overall_level.value})")
        return report

    async def _check_syntax(self) -> QualityMetric:
        """检查代码语法"""
        try:
            # 使用ruff进行语法检查
            result = subprocess.run(
                ["ruff", "check", "src/", "--select=E,F", "--output-format=json"],
                capture_output=True,
                text=True,
                cwd=self.base_dir
            )

            if result.stdout:
                errors = json.loads(result.stdout)
                error_count = len(errors)
            else:
                error_count = 0

            # 计算分数 (无错误=100分，每错误扣10分，最低0分)
            score = max(0, 100 - error_count * 10)

            status = self._get_quality_level(score)

            return QualityMetric(
                name="语法检查",
                value=score,
                unit="分",
                threshold=90.0,
                status=status,
                timestamp=datetime.now(),
                details={"error_count": error_count, "errors": errors[:5]}  # 只保留前5个错误
            )

        except Exception as e:
            self.logger.error(f"语法检查失败: {e}")
            return QualityMetric(
                name="语法检查",
                value=0,
                unit="分",
                threshold=90.0,
                status=QualityLevel.POOR,
                timestamp=datetime.now(),
                details={"error": str(e)}
            )

    async def _check_imports(self) -> QualityMetric:
        """检查模块导入"""
        try:
            # 尝试导入主要模块
            import_modules = [
                "src.main",
                "src.models.asset",
                "src.services.pdf_import_service",
                "src.api.v1.assets"
            ]

            failed_imports = []
            for module in import_modules:
                try:
                    __import__(module)
                except ImportError as e:
                    failed_imports.append({"module": module, "error": str(e)})

            success_count = len(import_modules) - len(failed_imports)
            score = (success_count / len(import_modules)) * 100

            status = self._get_quality_level(score)

            return QualityMetric(
                name="模块导入",
                value=score,
                unit="分",
                threshold=95.0,
                status=status,
                timestamp=datetime.now(),
                details={
                    "total_modules": len(import_modules),
                    "successful_imports": success_count,
                    "failed_imports": failed_imports
                }
            )

        except Exception as e:
            self.logger.error(f"导入检查失败: {e}")
            return QualityMetric(
                name="模块导入",
                value=0,
                unit="分",
                threshold=95.0,
                status=QualityLevel.POOR,
                timestamp=datetime.now(),
                details={"error": str(e)}
            )

    async def _check_api_health(self) -> QualityMetric:
        """检查API健康状态"""
        try:
            base_url = "http://localhost:8002"
            endpoints = [
                "/api/v1/health",
                "/api/v1/",
                "/docs"
            ]

            response_times = []
            successful_endpoints = 0

            for endpoint in endpoints:
                try:
                    start_time = time.time()
                    response = requests.get(f"{base_url}{endpoint}", timeout=5)
                    response_time = (time.time() - start_time) * 1000  # 转换为毫秒

                    if response.status_code == 200:
                        successful_endpoints += 1
                        response_times.append(response_time)
                except requests.exceptions.RequestException:
                    pass

            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                score = min(100, max(0, 100 - (avg_response_time - 100) / 10))  # 100ms为满分
            else:
                avg_response_time = 0
                score = 0

            success_rate = (successful_endpoints / len(endpoints)) * 100

            status = self._get_quality_level(score)

            return QualityMetric(
                name="API健康",
                value=score,
                unit="分",
                threshold=80.0,
                status=status,
                timestamp=datetime.now(),
                details={
                    "success_rate": success_rate,
                    "avg_response_time": avg_response_time,
                    "successful_endpoints": successful_endpoints,
                    "total_endpoints": len(endpoints)
                }
            )

        except Exception as e:
            self.logger.error(f"API健康检查失败: {e}")
            return QualityMetric(
                name="API健康",
                value=0,
                unit="分",
                threshold=80.0,
                status=QualityLevel.POOR,
                timestamp=datetime.now(),
                details={"error": str(e)}
            )

    async def _run_basic_tests(self) -> QualityMetric:
        """运行基本测试"""
        try:
            test_files = [
                "tests/test_main.py",
                "tests/test_quick_suite.py"
            ]

            start_time = time.time()

            # 运行测试
            result = subprocess.run(
                ["python", "-m", "pytest"] + test_files + ["-v", "--tb=no"],
                capture_output=True,
                text=True,
                cwd=self.base_dir
            )

            execution_time = time.time() - start_time

            # 解析测试结果
            output = result.stdout + result.stderr
            passed_tests = output.count("PASSED")
            failed_tests = output.count("FAILED")
            error_tests = output.count("ERROR")

            total_tests = passed_tests + failed_tests + error_tests

            if total_tests > 0:
                success_rate = (passed_tests / total_tests) * 100
                score = success_rate
            else:
                success_rate = 0
                score = 0

            # 性能评分 (30秒内完成得满分，每超过1秒扣2分)
            performance_score = max(0, 100 - max(0, execution_time - 30) * 2)

            # 综合评分
            final_score = (score + performance_score) / 2

            status = self._get_quality_level(final_score)

            return QualityMetric(
                name="基本测试",
                value=final_score,
                unit="分",
                threshold=80.0,
                status=status,
                timestamp=datetime.now(),
                details={
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "error_tests": error_tests,
                    "success_rate": success_rate,
                    "execution_time": execution_time,
                    "performance_score": performance_score
                }
            )

        except Exception as e:
            self.logger.error(f"基本测试失败: {e}")
            return QualityMetric(
                name="基本测试",
                value=0,
                unit="分",
                threshold=80.0,
                status=QualityLevel.POOR,
                timestamp=datetime.now(),
                details={"error": str(e)}
            )

    async def _check_test_coverage(self) -> QualityMetric:
        """检查测试覆盖率"""
        try:
            start_time = time.time()

            # 运行覆盖率测试
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "--cov=src", "--cov-report=term-missing"],
                capture_output=True,
                text=True,
                cwd=self.base_dir
            )

            execution_time = time.time() - start_time

            # 解析覆盖率结果
            output = result.stdout
            coverage_line = None

            for line in output.split('\n'):
                if 'TOTAL' in line and '%' in line:
                    coverage_line = line.strip()
                    break

            if coverage_line:
                # 提取覆盖率百分比
                coverage_str = coverage_line.split()[1].replace('%', '')
                coverage = float(coverage_str)
            else:
                coverage = 0

            # 覆盖率评分 (50%为及格，每增加1%加2分，最高100分)
            if coverage >= 50:
                score = min(100, 70 + (coverage - 50) * 2)
            else:
                score = coverage * 1.4  # 50%以下线性映射

            status = self._get_quality_level(score)

            return QualityMetric(
                name="测试覆盖率",
                value=score,
                unit="分",
                threshold=70.0,
                status=status,
                timestamp=datetime.now(),
                details={
                    "coverage_percentage": coverage,
                    "execution_time": execution_time,
                    "target_threshold": 50
                }
            )

        except Exception as e:
            self.logger.error(f"覆盖率检查失败: {e}")
            return QualityMetric(
                name="测试覆盖率",
                value=0,
                unit="分",
                threshold=70.0,
                status=QualityLevel.POOR,
                timestamp=datetime.now(),
                details={"error": str(e)}
            )

    async def _check_code_quality(self) -> QualityMetric:
        """检查代码质量"""
        try:
            # 使用ruff检查代码质量
            result = subprocess.run(
                ["ruff", "check", "src/", "--output-format=json"],
                capture_output=True,
                text=True,
                cwd=self.base_dir
            )

            if result.stdout:
                issues = json.loads(result.stdout)
                issue_count = len(issues)
            else:
                issue_count = 0

            # 计算质量分数 (无问题为100分，每问题扣5分)
            score = max(0, 100 - issue_count * 5)

            status = self._get_quality_level(score)

            return QualityMetric(
                name="代码质量",
                value=score,
                unit="分",
                threshold=85.0,
                status=status,
                timestamp=datetime.now(),
                details={
                    "issue_count": issue_count,
                    "issues": issues[:5]  # 只保留前5个问题
                }
            )

        except Exception as e:
            self.logger.error(f"代码质量检查失败: {e}")
            return QualityMetric(
                name="代码质量",
                value=0,
                unit="分",
                threshold=85.0,
                status=QualityLevel.POOR,
                timestamp=datetime.now(),
                details={"error": str(e)}
            )

    async def _check_test_performance(self) -> QualityMetric:
        """检查测试性能"""
        try:
            # 运行性能测试
            test_files = ["tests/test_main.py", "tests/test_quick_suite.py"]

            start_time = time.time()

            result = subprocess.run(
                ["python", "-m", "pytest"] + test_files + ["--tb=no"],
                capture_output=True,
                text=True,
                cwd=self.base_dir
            )

            execution_time = time.time() - start_time

            # 性能评分 (30秒内完成得满分，每超过1秒扣3分)
            if execution_time <= 30:
                score = 100
            else:
                score = max(0, 100 - (execution_time - 30) * 3)

            status = self._get_quality_level(score)

            return QualityMetric(
                name="测试性能",
                value=score,
                unit="分",
                threshold=80.0,
                status=status,
                timestamp=datetime.now(),
                details={
                    "execution_time": execution_time,
                    "target_time": 30,
                    "files_tested": len(test_files)
                }
            )

        except Exception as e:
            self.logger.error(f"测试性能检查失败: {e}")
            return QualityMetric(
                name="测试性能",
                value=0,
                unit="分",
                threshold=80.0,
                status=QualityLevel.POOR,
                timestamp=datetime.now(),
                details={"error": str(e)}
            )

    async def _check_security(self) -> QualityMetric:
        """检查安全性"""
        try:
            # 使用bandit进行安全检查
            result = subprocess.run(
                ["bandit", "-r", "src/", "-f", "json"],
                capture_output=True,
                text=True,
                cwd=self.base_dir
            )

            if result.stdout:
                security_report = json.loads(result.stdout)
                high_issues = len([i for i in security_report.get('results', [])
                               if i.get('issue_severity') == 'HIGH'])
                medium_issues = len([i for i in security_report.get('results', [])
                                 if i.get('issue_severity') == 'MEDIUM'])
                low_issues = len([i for i in security_report.get('results', [])
                              if i.get('issue_severity') == 'LOW'])
            else:
                high_issues = medium_issues = low_issues = 0

            # 安全评分 (高问题-20分，中问题-10分，低问题-5分)
            score = max(0, 100 - high_issues * 20 - medium_issues * 10 - low_issues * 5)

            status = self._get_quality_level(score)

            return QualityMetric(
                name="安全性检查",
                value=score,
                unit="分",
                threshold=90.0,
                status=status,
                timestamp=datetime.now(),
                details={
                    "high_issues": high_issues,
                    "medium_issues": medium_issues,
                    "low_issues": low_issues,
                    "total_issues": high_issues + medium_issues + low_issues
                }
            )

        except Exception as e:
            self.logger.error(f"安全检查失败: {e}")
            return QualityMetric(
                name="安全性检查",
                value=0,
                unit="分",
                threshold=90.0,
                status=QualityLevel.POOR,
                timestamp=datetime.now(),
                details={"error": str(e)}
            )

    async def _check_complexity(self) -> QualityMetric:
        """检查代码复杂度"""
        try:
            # 使用radon进行复杂度分析
            result = subprocess.run(
                ["radon", "cc", "src/", "--json"],
                capture_output=True,
                text=True,
                cwd=self.base_dir
            )

            if result.stdout and result.returncode == 0:
                complexity_data = json.loads(result.stdout)

                # 计算平均复杂度
                total_complexity = 0
                function_count = 0

                for filename, file_data in complexity_data.items():
                    for item in file_data:
                        if isinstance(item, dict) and 'complexity' in item:
                            total_complexity += item['complexity']
                            function_count += 1

                if function_count > 0:
                    avg_complexity = total_complexity / function_count
                else:
                    avg_complexity = 0

                # 复杂度评分 (平均复杂度10以下得满分，每增加1扣10分)
                if avg_complexity <= 10:
                    score = 100
                else:
                    score = max(0, 100 - (avg_complexity - 10) * 10)
            else:
                avg_complexity = 0
                score = 100

            status = self._get_quality_level(score)

            return QualityMetric(
                name="代码复杂度",
                value=score,
                unit="分",
                threshold=80.0,
                status=status,
                timestamp=datetime.now(),
                details={
                    "avg_complexity": avg_complexity,
                    "function_count": function_count,
                    "total_complexity": total_complexity
                }
            )

        except Exception as e:
            self.logger.error(f"复杂度检查失败: {e}")
            return QualityMetric(
                name="代码复杂度",
                value=50,  # 给默认分数，因为工具可能未安装
                unit="分",
                threshold=80.0,
                status=QualityLevel.SATISFACTORY,
                timestamp=datetime.now(),
                details={"error": str(e), "note": "radon工具未安装，使用默认分数"}
            )

    def _calculate_overall_score(self, metrics: List[QualityMetric]) -> float:
        """计算总体质量分数"""
        if not metrics:
            return 0.0

        # 根据重要性分配权重
        weights = {
            "语法检查": 0.10,
            "模块导入": 0.10,
            "API健康": 0.15,
            "基本测试": 0.15,
            "测试覆盖率": 0.20,
            "代码质量": 0.15,
            "测试性能": 0.10,
            "安全性检查": 0.10,
            "代码复杂度": 0.05
        }

        weighted_score = 0.0
        total_weight = 0.0

        for metric in metrics:
            weight = weights.get(metric.name, 0.1)
            weighted_score += metric.value * weight
            total_weight += weight

        return weighted_score / total_weight if total_weight > 0 else 0.0

    def _get_quality_level(self, score: float) -> QualityLevel:
        """根据分数获取质量等级"""
        if score >= 90:
            return QualityLevel.EXCELLENT
        elif score >= 80:
            return QualityLevel.GOOD
        elif score >= 70:
            return QualityLevel.SATISFACTORY
        elif score >= 60:
            return QualityLevel.NEEDS_IMPROVEMENT
        else:
            return QualityLevel.POOR

    def _generate_recommendations(self, metrics: List[QualityMetric]) -> tuple[List[str], List[str]]:
        """生成改进建议和警告"""
        recommendations = []
        warnings = []

        for metric in metrics:
            if metric.value < metric.threshold:
                warnings.append(f"{metric.name}: 分数 {metric.value:.1f} 低于阈值 {metric.threshold}")

                # 根据指标类型生成具体建议
                if metric.name == "测试覆盖率":
                    recommendations.append("建议增加测试用例，特别是API端点和错误处理的测试")
                elif metric.name == "代码质量":
                    recommendations.append("建议使用ruff修复代码质量问题，提升代码规范")
                elif metric.name == "测试性能":
                    recommendations.append("建议优化测试执行效率，使用mock减少外部依赖")
                elif metric.name == "安全性检查":
                    recommendations.append("建议修复安全漏洞，特别是输入验证和SQL注入防护")
                elif metric.name == "API健康":
                    recommendations.append("建议检查API服务状态，确保所有端点正常响应")
                else:
                    recommendations.append(f"建议改进{metric.name}，提升系统质量")

        return recommendations, warnings

    def save_report(self, report: QualityReport, format: str = "markdown") -> str:
        """保存质量报告"""
        timestamp_str = report.timestamp.strftime("%Y%m%d_%H%M%S")

        if format == "markdown":
            content = self._generate_markdown_report(report)
            filename = f"reports/quality_report_{timestamp_str}.md"
        elif format == "json":
            content = self._generate_json_report(report)
            filename = f"reports/quality_report_{timestamp_str}.json"
        else:
            content = str(report)
            filename = f"reports/quality_report_{timestamp_str}.txt"

        report_path = self.base_dir / filename

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)

        self.logger.info(f"质量报告已保存: {report_path}")
        return str(report_path)

    def _generate_markdown_report(self, report: QualityReport) -> str:
        """生成Markdown格式的报告"""
        content = f"""# 质量监控报告

## 基本信息

- **报告时间**: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- **总体分数**: {report.overall_score:.1f}分
- **质量等级**: {self._get_level_display(report.overall_level)}
- **检查指标数**: {len(report.metrics)}

## 质量等级说明

{self._get_level_description(report.overall_level)}

## 详细指标

| 指标名称 | 分数 | 阈值 | 状态 | 详细信息 |
|---------|------|------|------|----------|
"""

        for metric in report.metrics:
            details_str = self._format_metric_details(metric)
            content += f"| {metric.name} | {metric.value:.1f} | {metric.threshold:.1f} | {self._get_level_display(metric.status)} | {details_str} |\n"

        content += f"""
## 改进建议

"""

        if report.recommendations:
            for i, rec in enumerate(report.recommendations, 1):
                content += f"{i}. {rec}\n"
        else:
            content += "暂无改进建议，系统质量良好。\n"

        content += """
## 警告信息

"""

        if report.warnings:
            for warning in report.warnings:
                content += f"- [警告] {warning}\n"
        else:
            content += "无警告信息。\n"

        content += f"""
## 报告生成时间

报告生成于: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

---
*该报告由持续质量监控系统自动生成*
"""

        return content

    def _generate_json_report(self, report: QualityReport) -> str:
        """生成JSON格式的报告"""
        report_dict = {
            "timestamp": report.timestamp.isoformat(),
            "overall_score": report.overall_score,
            "overall_level": report.overall_level.value,
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "unit": m.unit,
                    "threshold": m.threshold,
                    "status": m.status.value,
                    "timestamp": m.timestamp.isoformat(),
                    "details": m.details
                }
                for m in report.metrics
            ],
            "recommendations": report.recommendations,
            "warnings": report.warnings
        }

        return json.dumps(report_dict, ensure_ascii=False, indent=2)

    def _get_level_display(self, level: QualityLevel) -> str:
        """获取质量等级显示文本"""
        displays = {
            QualityLevel.EXCELLENT: "[优秀] 优秀",
            QualityLevel.GOOD: "[良好] 良好",
            QualityLevel.SATISFACTORY: "[合格] 合格",
            QualityLevel.NEEDS_IMPROVEMENT: "[需改进] 需改进",
            QualityLevel.POOR: "[较差] 较差"
        }
        return displays.get(level, "未知")

    def _get_level_description(self, level: QualityLevel) -> str:
        """获取质量等级描述"""
        descriptions = {
            QualityLevel.EXCELLENT: "系统质量优秀，各项指标均达到最佳标准，可以安全部署到生产环境。",
            QualityLevel.GOOD: "系统质量良好，大部分指标达到标准，适合生产环境部署。",
            QualityLevel.SATISFACTORY: "系统质量合格，基本满足要求，建议修复部分问题后部署。",
            QualityLevel.NEEDS_IMPROVEMENT: "系统质量需要改进，存在一些问题需要修复，不建议生产部署。",
            QualityLevel.POOR: "系统质量较差，存在严重问题，必须修复后才能部署。"
        }
        return descriptions.get(level, "未知质量等级")

    def _format_metric_details(self, metric: QualityMetric) -> str:
        """格式化指标详细信息"""
        if not metric.details:
            return "无详细信息"

        details = []
        for key, value in metric.details.items():
            if isinstance(value, list) and value:
                details.append(f"{key}: {len(value)}项")
            elif isinstance(value, dict):
                details.append(f"{key}: {len(value)}项")
            else:
                details.append(f"{key}: {value}")

        return ", ".join(details[:3])  # 只显示前3个细节


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="持续质量监控系统")
    parser.add_argument(
        "--mode",
        choices=["quick", "comprehensive"],
        default="quick",
        help="检查模式: quick(快速检查) 或 comprehensive(全面检查)"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json", "console"],
        default="markdown",
        help="报告格式"
    )
    parser.add_argument(
        "--config",
        default="quality_monitor_config.yaml",
        help="配置文件路径"
    )

    args = parser.parse_args()

    try:
        monitor = QualityMonitor(args.config)

        if args.mode == "quick":
            report = await monitor.run_quick_health_check()
        else:
            report = await monitor.run_comprehensive_check()

        if args.format == "console":
            # 控制台输出
            print(f"\n{'='*60}")
            print(f"质量监控报告 - {args.mode.upper()} 模式")
            print(f"{'='*60}")
            print(f"总体分数: {report.overall_score:.1f}分 ({monitor._get_level_display(report.overall_level)})")
            print(f"检查时间: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"\n详细指标:")
            for metric in report.metrics:
                print(f"  - {metric.name}: {metric.value:.1f}分 (阈值: {metric.threshold:.1f})")

            if report.recommendations:
                print(f"\n改进建议:")
                for rec in report.recommendations:
                    print(f"  • {rec}")

            if report.warnings:
                print(f"\n警告信息:")
                for warning in report.warnings:
                    print(f"  [警告] {warning}")
        else:
            # 保存报告文件
            report_path = monitor.save_report(report, args.format)
            print(f"质量报告已生成: {report_path}")

            # 同时显示简要信息
            print(f"\n质量检查完成:")
            print(f"- 总体分数: {report.overall_score:.1f}分")
            print(f"- 质量等级: {monitor._get_level_display(report.overall_level)}")
            print(f"- 检查指标: {len(report.metrics)}项")
            print(f"- 改进建议: {len(report.recommendations)}项")
            print(f"- 警告信息: {len(report.warnings)}项")

        # 根据质量等级设置退出代码
        if report.overall_level == QualityLevel.POOR:
            sys.exit(2)  # 严重问题
        elif report.overall_level in [QualityLevel.NEEDS_IMPROVEMENT, QualityLevel.SATISFACTORY]:
            sys.exit(1)  # 需要改进
        else:
            sys.exit(0)  # 质量良好

    except Exception as e:
        print(f"质量监控执行失败: {e}")
        sys.exit(3)


if __name__ == "__main__":
    asyncio.run(main())