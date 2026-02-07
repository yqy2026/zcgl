#!/usr/bin/env python3
"""
数据库性能基准测试脚本
功能: 在索引优化前后进行性能对比，量化改进效果
时间: 2025-11-03
"""

import json
import statistics
import sys
import time
import asyncio
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_database_engine


class DatabaseBenchmark:
    """数据库性能基准测试"""

    def __init__(self, num_iterations: int = 5):
        self.engine = get_database_engine()
        self.num_iterations = num_iterations
        self.results = {}

    async def query_asset_list_with_filters(self) -> dict:
        """测试1: 资产列表查询（带筛选）"""
        query = """
        SELECT COUNT(*) FROM assets
        WHERE data_status = 'active'
        LIMIT 100
        """

        times = []
        async with self.engine.connect() as conn:
            for _ in range(self.num_iterations):
                start = time.time()
                await conn.execute(text(query))
                times.append(time.time() - start)

        return {
            "query_name": "资产列表查询",
            "times": times,
            "avg": statistics.mean(times),
            "min": min(times),
            "max": max(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
        }

    async def query_occupancy_rate(self) -> dict:
        """测试2: 出租率统计查询"""
        query = """
        SELECT
            COUNT(*) as total_count,
            SUM(CAST(rented_area AS FLOAT)) as rented_area,
            SUM(CAST(rentable_area AS FLOAT)) as rentable_area
        FROM assets
        WHERE data_status = 'active'
        """

        times = []
        async with self.engine.connect() as conn:
            for _ in range(self.num_iterations):
                start = time.time()
                await conn.execute(text(query))
                times.append(time.time() - start)

        return {
            "query_name": "出租率统计",
            "times": times,
            "avg": statistics.mean(times),
            "min": min(times),
            "max": max(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
        }

    async def query_financial_summary(self) -> dict:
        """测试3: 财务汇总查询"""
        query = """
        SELECT
            COUNT(*) as contract_count,
            SUM(CAST(monthly_rent_base AS FLOAT)) as total_rent,
            SUM(CAST(total_deposit AS FLOAT)) as total_deposit
        FROM rent_contracts
        WHERE contract_status = 'ACTIVE'
        """

        times = []
        async with self.engine.connect() as conn:
            for _ in range(self.num_iterations):
                start = time.time()
                await conn.execute(text(query))
                times.append(time.time() - start)

        return {
            "query_name": "财务汇总",
            "times": times,
            "avg": statistics.mean(times),
            "min": min(times),
            "max": max(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
        }

    async def run_benchmark(self) -> list[dict]:
        """执行所有性能测试"""
        print("=" * 70)
        print("🚀 开始数据库性能基准测试")
        print(f"   每个查询运行 {self.num_iterations} 次")
        print("=" * 70)

        benchmarks = [
            self.query_asset_list_with_filters,
            self.query_occupancy_rate,
            self.query_financial_summary,
        ]

        results = []
        for i, bench_func in enumerate(benchmarks, 1):
            try:
                print(f"\n({i}/{len(benchmarks)}) 运行: {bench_func.__doc__}")
                result = await bench_func()
                results.append(result)
                print(f"   ✅ 完成 - 平均耗时: {result['avg'] * 1000:.2f}ms")
            except Exception as e:
                print(f"   ❌ 失败: {str(e)}")

        print("\n" + "=" * 70)
        return results

    def print_results(self, results: list[dict]):
        """打印结果"""
        print("\n📊 性能基准测试结果")
        print("=" * 70)
        print(
            f"{'查询名称':<20} {'平均耗时(ms)':<15} {'最小(ms)':<12} {'最大(ms)':<12}"
        )
        print("-" * 70)

        for result in results:
            print(
                f"{result['query_name']:<20} "
                f"{result['avg'] * 1000:>14.2f} "
                f"{result['min'] * 1000:>11.2f} "
                f"{result['max'] * 1000:>11.2f}"
            )

        # 总体统计
        total_avg = sum(r["avg"] for r in results) / len(results)
        print("-" * 70)
        print(f"{'总体平均':<20} {total_avg * 1000:>14.2f}ms")
        print("=" * 70)

    def save_results(
        self, results: list[dict], filename: str = "benchmark_results.json"
    ):
        """保存测试结果"""
        output_path = Path(__file__).parent.parent / filename

        data = {
            "timestamp": datetime.now().isoformat(),
            "num_iterations": self.num_iterations,
            "benchmarks": results,
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"\n📁 结果已保存到: {output_path}")


async def main() -> None:
    benchmark = DatabaseBenchmark(num_iterations=5)
    results = await benchmark.run_benchmark()
    benchmark.print_results(results)
    benchmark.save_results(results)

    print("\n💡 使用说明:")
    print("   1. 这是优化前的基准数据")
    print("   2. 执行 python scripts/optimize_database_indexes.py 创建索引")
    print("   3. 重新运行此脚本，对比性能改进")


if __name__ == "__main__":
    asyncio.run(main())
