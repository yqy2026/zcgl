#!/usr/bin/env python3
"""
简单测试CacheManager
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test():
    try:
        from src.api.v1.analytics import analytics_cache
        print("Analytics模块导入成功")

        # 直接调用comprehensive端点的相关代码
        print(f"analytics_cache有get_stats: {hasattr(analytics_cache, 'get_stats')}")

        if hasattr(analytics_cache, 'get_stats'):
            try:
                result = analytics_cache.get_stats()
                print(f"get_stats调用成功: {type(result)}")
                print(f"返回结果前5个键: {list(result.keys())[:5]}")
            except Exception as e:
                print(f"get_stats调用失败: {e}")
                print(f"错误类型: {type(e)}")

        # 测试性能统计
        from src.core.performance import get_performance_stats
        try:
            perf = get_performance_stats()
            print(f"性能统计成功: {type(perf)}")
        except Exception as e:
            print(f"性能统计失败: {e}")

    except Exception as e:
        print(f"整体测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()