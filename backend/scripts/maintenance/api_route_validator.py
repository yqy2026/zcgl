#!/usr/bin/env python3
"""
API路由验证脚本
用于检测和防止API版本混乱问题
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app


def validate_api_routes():
    """验证API路由，检测版本混乱"""
    print("🔍 API路由验证报告")
    print("=" * 50)

    # 收集所有PDF相关的路由
    pdf_routes = []

    for route in app.routes:
        if hasattr(route, 'path'):
            path = route.path
            if 'pdf' in path.lower():
                pdf_routes.append({
                    'path': path,
                    'methods': getattr(route, 'methods', ['GET']),
                    'name': getattr(route, 'name', 'Unknown')
                })

    # 分析路由版本
    v1_routes = [r for r in pdf_routes if '/pdf_import/' in r['path'] and 'pdf_import_v2' not in r['path']]
    v2_routes = [r for r in pdf_routes if 'pdf_import_v2' in r['path']]
    other_routes = [r for r in pdf_routes if r not in v1_routes and r not in v2_routes]

    print("📊 路由统计:")
    print(f"   - PDF相关路由总数: {len(pdf_routes)}")
    print(f"   - V1路由 (/api/v1/pdf_import/*): {len(v1_routes)}")
    print(f"   - V2路由 (/api/v1/pdf_import_v2/*): {len(v2_routes)}")
    print(f"   - 其他PDF路由: {len(other_routes)}")

    print("\n🚨 问题检测:")
    if v2_routes:
        print(f"   ❌ 发现 {len(v2_routes)} 个V2路由，存在版本混乱")
        for route in v2_routes:
            print(f"      - {route['path']} ({', '.join(route['methods'])})")
        print("\n💡 建议操作:")
        print("   1. 检查并移除V2路由注册代码")
        print("   2. 清理Python缓存和重启服务")
        print("   3. 验证OpenAPI规范更新")
        return False
    else:
        print("   ✅ 未发现V2路由，API版本统一")
        return True

if __name__ == "__main__":
    is_valid = validate_api_routes()
    sys.exit(0 if is_valid else 1)
