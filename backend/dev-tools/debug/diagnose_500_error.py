#!/usr/bin/env python3
"""
深度诊断500错误 - 捕获完整的错误堆栈和请求信息
"""

import asyncio
import os
import sys
import traceback
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


async def diagnose_http_500():
    """深度诊断HTTP 500错误"""
    print("深度HTTP 500错误诊断")
    print("=" * 60)
    print(f"时间: {datetime.now()}")
    print("=" * 60)

    try:
        # 1. 测试CRUD层
        print("\n1. 测试CRUD层...")
        from src.crud.enum_field import get_enum_field_type_crud
        from src.database import get_db

        db = next(get_db())
        try:
            crud = get_enum_field_type_crud(db)
            result = crud.get_multi(skip=0, limit=5)
            print(f"   CRUD层成功: 返回 {len(result)} 个记录")
            if result:
                print(f"   第一个记录: {result[0].name} ({result[0].code})")
        finally:
            db.close()

        # 2. 测试API函数直接调用
        print("\n2. 测试API函数直接调用...")
        from src.api.v1.enum_field import get_enum_field_types

        db = next(get_db())
        try:
            result = await get_enum_field_types(
                skip=0,
                limit=5,
                category=None,
                status=None,
                is_system=None,
                keyword=None,
                db=db,
            )
            print(f"   API函数成功: 返回 {len(result)} 个记录")
            if result:
                print(f"   第一个记录: {result[0].name} ({result[0].code})")
        finally:
            db.close()

        # 3. 测试FastAPI路由注册
        print("\n3. 测试FastAPI路由注册...")

        from src.main import app

        enum_routes = []
        for route in app.routes:
            if hasattr(route, "path") and "enum" in route.path:
                enum_routes.append(route)

        print(f"   发现 {len(enum_routes)} 个enum路由:")
        for route in enum_routes:
            if hasattr(route, "methods"):
                print(f"     - {route.path}: {list(route.methods)}")
            else:
                print(f"     - {route.path}: {type(route).__name__}")

        # 4. 测试HTTP请求 - 使用TestClient
        print("\n4. 测试HTTP请求 (TestClient)...")
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/api/v1/enum-fields/types?limit=5")

        print(f"   TestClient状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   TestClient成功: 返回 {len(data)} 个记录")
            if data:
                print(
                    f"   第一个记录: {data[0].get('name', 'N/A')} ({data[0].get('code', 'N/A')})"
                )
        else:
            print(f"   TestClient失败: {response.text}")

        # 5. 检查enum_field模块导入
        print("\n5. 检查enum_field模块导入...")
        try:
            from src.api.v1 import enum_field

            print("   enum_field模块导入成功")
            print(f"   模块文件: {enum_field.__file__}")
            print(f"   router对象: {enum_field.router}")

            # 检查路由定义
            if hasattr(enum_field, "router"):
                router = enum_field.router
                print(f"   router路由数: {len(router.routes)}")
                for route in router.routes:
                    if hasattr(route, "path"):
                        print(
                            f"     - {route.path}: {getattr(route, 'methods', 'N/A')}"
                        )
        except Exception as e:
            print(f"   enum_field模块导入失败: {e}")
            traceback.print_exc()

        # 6. 检查API模块注册
        print("\n6. 检查API模块注册...")
        try:
            from src.api.v1 import api_router

            print(f"   api_router对象: {api_router}")
            print(f"   注册的路由数: {len(api_router.routes)}")

            # 查找enum相关路由
            enum_routes = [
                r for r in api_router.routes if hasattr(r, "path") and "enum" in r.path
            ]
            print(f"   enum路由数: {len(enum_routes)}")
            for route in enum_routes:
                print(
                    f"     - {route.path}: {list(route.methods) if hasattr(route, 'methods') else 'N/A'}"
                )

        except Exception as e:
            print(f"   API模块检查失败: {e}")
            traceback.print_exc()

        # 7. 尝试直接HTTP请求并捕获详细错误
        print("\n7. 尝试真实HTTP请求...")
        try:
            import time

            import requests

            # 添加更详细的请求信息
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Enum-Field-Diagnostic/1.0",
            }

            start_time = time.time()
            response = requests.get(
                "http://localhost:8002/api/v1/enum-fields/types?limit=5",
                headers=headers,
                timeout=10,
            )
            elapsed = time.time() - start_time

            print(f"   HTTP状态码: {response.status_code}")
            print(f"   响应时间: {elapsed:.2f}秒")
            print(f"   响应头: {dict(response.headers)}")

            if response.status_code == 200:
                data = response.json()
                print(f"   HTTP请求成功: 返回 {len(data)} 个记录")
            else:
                print(f"   HTTP请求失败: {response.text}")

        except Exception as e:
            print(f"   HTTP请求异常: {e}")
            traceback.print_exc()

        print("\n" + "=" * 60)
        print("诊断完成")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ 诊断过程失败: {e}")
        print("\n完整错误堆栈:")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(diagnose_http_500())
    if result:
        print("\n✅ 诊断成功完成")
    else:
        print("\n❌ 诊断失败")
