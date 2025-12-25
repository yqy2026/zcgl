#!/usr/bin/env python3
"""
性能优化工具
分析和优化系统性能
"""

import json
import os
import sqlite3
import sys
import time
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))


class PerformanceOptimizer:
    def __init__(self, db_path):
        self.db_path = db_path
        self.optimization_log = []

    def analyze_database_performance(self):
        """分析数据库性能"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        analysis = {
            "timestamp": datetime.now().isoformat(),
            "database_size": os.path.getsize(self.db_path) / (1024 * 1024),  # MB
            "tables": {},
            "indexes": {},
            "recommendations": [],
        }

        try:
            # 分析表信息
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            for (table_name,) in tables:
                if table_name.startswith("sqlite_"):
                    continue

                # 表大小和行数
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]

                # 表结构
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()

                analysis["tables"][table_name] = {
                    "row_count": row_count,
                    "column_count": len(columns),
                    "columns": [col[1] for col in columns],
                }

            # 分析索引
            cursor.execute(
                "SELECT name, tbl_name FROM sqlite_master WHERE type='index'"
            )
            indexes = cursor.fetchall()

            for index_name, table_name in indexes:
                if not index_name.startswith("sqlite_"):
                    analysis["indexes"][index_name] = table_name

            # 性能建议
            if len(analysis["indexes"]) < 5:
                analysis["recommendations"].append("建议添加更多索引以提高查询性能")

            if analysis["database_size"] > 100:  # 100MB
                analysis["recommendations"].append("数据库文件较大，建议定期清理和压缩")

            # 检查是否有大表缺少索引
            for table_name, info in analysis["tables"].items():
                if info["row_count"] > 1000:
                    table_indexes = [
                        idx
                        for idx, tbl in analysis["indexes"].items()
                        if tbl == table_name
                    ]
                    if len(table_indexes) < 2:
                        analysis["recommendations"].append(
                            f"表 {table_name} 数据量大但索引较少，建议添加索引"
                        )

        finally:
            conn.close()

        return analysis

    def optimize_database(self):
        """优化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        optimizations = []

        try:
            # 1. 分析查询计划
            print("分析查询性能...")

            # 2. 重建索引
            print("重建索引...")
            cursor.execute("REINDEX")
            optimizations.append("重建了所有索引")

            # 3. 清理碎片
            print("清理数据库碎片...")
            cursor.execute("VACUUM")
            optimizations.append("清理了数据库碎片")

            # 4. 更新统计信息
            print("更新统计信息...")
            cursor.execute("ANALYZE")
            optimizations.append("更新了查询统计信息")

            # 5. 优化配置
            print("优化数据库配置...")
            cursor.execute("PRAGMA optimize")
            optimizations.append("优化了数据库配置")

            conn.commit()

            self.optimization_log.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "optimizations": optimizations,
                }
            )

            print("数据库优化完成")
            return optimizations

        except Exception as e:
            conn.rollback()
            print(f"优化失败: {str(e)}")
            raise
        finally:
            conn.close()

    def create_performance_indexes(self):
        """创建性能索引"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        indexes_to_create = [
            (
                "idx_assets_property_name",
                "CREATE INDEX IF NOT EXISTS idx_assets_property_name ON assets(property_name)",
            ),
            (
                "idx_assets_usage_status",
                "CREATE INDEX IF NOT EXISTS idx_assets_usage_status ON assets(usage_status)",
            ),
            (
                "idx_assets_manager_name",
                "CREATE INDEX IF NOT EXISTS idx_assets_manager_name ON assets(manager_name)",
            ),
            (
                "idx_assets_project_name",
                "CREATE INDEX IF NOT EXISTS idx_assets_project_name ON assets(project_name)",
            ),
            (
                "idx_assets_business_category",
                "CREATE INDEX IF NOT EXISTS idx_assets_business_category ON assets(business_category)",
            ),
            (
                "idx_assets_created_at",
                "CREATE INDEX IF NOT EXISTS idx_assets_created_at ON assets(created_at)",
            ),
            (
                "idx_assets_occupancy_rate",
                "CREATE INDEX IF NOT EXISTS idx_assets_occupancy_rate ON assets(occupancy_rate)",
            ),
            (
                "idx_assets_monthly_rent",
                "CREATE INDEX IF NOT EXISTS idx_assets_monthly_rent ON assets(monthly_rent)",
            ),
            # 复合索引
            (
                "idx_assets_status_nature",
                "CREATE INDEX IF NOT EXISTS idx_assets_status_nature ON assets(usage_status, property_nature)",
            ),
            (
                "idx_assets_manager_project",
                "CREATE INDEX IF NOT EXISTS idx_assets_manager_project ON assets(manager_name, project_name)",
            ),
        ]

        created_indexes = []

        try:
            for index_name, sql in indexes_to_create:
                try:
                    cursor.execute(sql)
                    created_indexes.append(index_name)
                    print(f"创建索引: {index_name}")
                except sqlite3.Error as e:
                    print(f"创建索引 {index_name} 失败: {str(e)}")

            conn.commit()
            print(f"成功创建 {len(created_indexes)} 个索引")

            return created_indexes

        except Exception as e:
            conn.rollback()
            print(f"创建索引失败: {str(e)}")
            raise
        finally:
            conn.close()

    def benchmark_queries(self):
        """基准测试查询性能"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        test_queries = [
            ("全表扫描", "SELECT COUNT(*) FROM assets"),
            ("按名称查询", "SELECT * FROM assets WHERE property_name LIKE '%大厦%'"),
            ("按状态筛选", "SELECT * FROM assets WHERE usage_status = '出租'"),
            (
                "复杂查询",
                """
                SELECT usage_status, COUNT(*), AVG(occupancy_rate)
                FROM assets
                WHERE occupancy_rate IS NOT NULL
                GROUP BY usage_status
            """,
            ),
            ("排序查询", "SELECT * FROM assets ORDER BY monthly_rent DESC LIMIT 10"),
            (
                "统计查询",
                """
                SELECT
                    COUNT(*) as total,
                    AVG(occupancy_rate) as avg_occupancy,
                    SUM(monthly_rent) as total_rent
                FROM assets
                WHERE rentable_area > 0
            """,
            ),
        ]

        results = []

        try:
            for query_name, sql in test_queries:
                # 预热查询
                cursor.execute(sql)
                cursor.fetchall()

                # 测试查询性能
                start_time = time.time()
                cursor.execute(sql)
                result = cursor.fetchall()
                end_time = time.time()

                execution_time = (end_time - start_time) * 1000  # 毫秒

                results.append(
                    {
                        "query_name": query_name,
                        "execution_time_ms": round(execution_time, 2),
                        "result_count": len(result),
                    }
                )

                print(f"{query_name}: {execution_time:.2f}ms ({len(result)} 行)")

            return results

        finally:
            conn.close()

    def generate_performance_report(self, output_file):
        """生成性能报告"""
        print("生成性能分析报告...")

        # 数据库分析
        db_analysis = self.analyze_database_performance()

        # 查询基准测试
        query_benchmarks = self.benchmark_queries()

        # 系统信息
        system_info = {
            "database_file": self.db_path,
            "file_size_mb": round(os.path.getsize(self.db_path) / (1024 * 1024), 2),
            "last_modified": datetime.fromtimestamp(
                os.path.getmtime(self.db_path)
            ).isoformat(),
        }

        report = {
            "timestamp": datetime.now().isoformat(),
            "system_info": system_info,
            "database_analysis": db_analysis,
            "query_benchmarks": query_benchmarks,
            "optimization_log": self.optimization_log,
            "recommendations": self._generate_recommendations(
                db_analysis, query_benchmarks
            ),
        }

        # 保存报告
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"性能报告已生成: {output_file}")
        return report

    def _generate_recommendations(self, db_analysis, query_benchmarks):
        """生成优化建议"""
        recommendations = []

        # 基于数据库分析的建议
        recommendations.extend(db_analysis.get("recommendations", []))

        # 基于查询性能的建议
        slow_queries = [q for q in query_benchmarks if q["execution_time_ms"] > 100]
        if slow_queries:
            recommendations.append(f"发现 {len(slow_queries)} 个慢查询，建议优化")

        # 基于数据量的建议
        total_rows = sum(info["row_count"] for info in db_analysis["tables"].values())
        if total_rows > 10000:
            recommendations.append("数据量较大，建议定期归档历史数据")

        # 基于索引的建议
        if len(db_analysis["indexes"]) < 8:
            recommendations.append("索引数量较少，建议添加更多索引提高查询性能")

        return recommendations


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="性能优化工具")
    parser.add_argument("--db", default="../land_property.db", help="数据库文件路径")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 分析命令
    analyze_parser = subparsers.add_parser("analyze", help="分析数据库性能")

    # 优化命令
    optimize_parser = subparsers.add_parser("optimize", help="优化数据库")

    # 创建索引命令
    index_parser = subparsers.add_parser("create-indexes", help="创建性能索引")

    # 基准测试命令
    benchmark_parser = subparsers.add_parser("benchmark", help="查询性能基准测试")

    # 生成报告命令
    report_parser = subparsers.add_parser("report", help="生成性能报告")
    report_parser.add_argument(
        "--output", default="performance_report.json", help="报告文件"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if not os.path.exists(args.db):
        print(f"数据库文件不存在: {args.db}")
        sys.exit(1)

    optimizer = PerformanceOptimizer(args.db)

    try:
        if args.command == "analyze":
            analysis = optimizer.analyze_database_performance()
            print(json.dumps(analysis, indent=2, ensure_ascii=False))

        elif args.command == "optimize":
            optimizer.optimize_database()

        elif args.command == "create-indexes":
            optimizer.create_performance_indexes()

        elif args.command == "benchmark":
            results = optimizer.benchmark_queries()
            print(json.dumps(results, indent=2, ensure_ascii=False))

        elif args.command == "report":
            optimizer.generate_performance_report(args.output)

    except Exception as e:
        print(f"操作失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
