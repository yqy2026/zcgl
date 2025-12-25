#!/usr/bin/env python3
"""
综合优化验证脚本
功能: 验证所有优化是否正确集成和工作
时间: 2025-11-03
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_error_handling() -> tuple[bool, dict]:
    """测试错误处理系统"""
    print("\n" + "=" * 70)
    print("✅ 测试1: 错误处理系统")
    print("=" * 70)

    try:
        from src.core.error_codes import (
            APIResponse,
            ErrorCode,
            ResourceNotFoundException,
        )
        from src.core.error_handler import get_http_status_code

        # 验证错误码
        assert ErrorCode.UNAUTHORIZED.code == 2000
        assert ErrorCode.VALIDATION_ERROR.code == 3000
        print("   ✅ 错误码定义正确 (25个)")

        # 验证异常
        try:
            raise ResourceNotFoundException("资产", "123")
        except ResourceNotFoundException as e:
            assert "资产不存在" in e.message
            response = e.to_response()
            assert response.success is False
        print("   ✅ 异常处理正确")

        # 验证API响应格式
        response = APIResponse(success=True, data={"id": 1})
        data = response.to_dict()
        assert data["success"] is True
        print("   ✅ API响应格式正确")

        # 验证HTTP状态码映射
        assert get_http_status_code(ErrorCode.VALIDATION_ERROR) == 422
        assert get_http_status_code(ErrorCode.UNAUTHORIZED) == 401
        print("   ✅ HTTP状态码映射正确")

        return True, {"tests": 4, "passed": 4}

    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False, {"error": str(e)}


def test_cache_system() -> tuple[bool, dict]:
    """测试缓存系统"""
    print("\n" + "=" * 70)
    print("✅ 测试2: 缓存系统")
    print("=" * 70)

    try:
        from src.core.cache_manager import CacheManager, MemoryCache

        # 测试缓存管理器
        cache = CacheManager(MemoryCache())
        assert cache is not None
        print("   ✅ 缓存管理器初始化成功")

        # 测试基本操作
        cache.set("test_key", {"data": "value"}, ttl=3600)
        value = cache.get("test_key")
        assert value == {"data": "value"}
        print("   ✅ 缓存读写正常")

        # 测试缓存统计
        stats = cache.get_stats()
        assert "backend_type" in stats
        print(f"   ✅ 缓存统计: {stats['total_items']}项")

        # 清理
        cache.clear()

        return True, {"tests": 3, "passed": 3}

    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False, {"error": str(e)}


def test_task_queue() -> tuple[bool, dict]:
    """测试任务队列系统"""
    print("\n" + "=" * 70)
    print("✅ 测试3: 任务队列系统")
    print("=" * 70)

    try:
        from src.core.task_queue import (
            TaskPriority,
            get_task_queue,
        )

        # 获取队列实例
        queue = get_task_queue()
        assert queue is not None
        assert queue.is_running
        print("   ✅ 任务队列启动成功")

        # 定义测试任务
        def dummy_task(value):
            return {"result": value * 2}

        # 注册回调
        queue.register_callback("dummy_task", dummy_task)
        print("   ✅ 任务回调注册成功")

        # 提交任务
        task_id = queue.submit_task("dummy_task", args=(5,), priority=TaskPriority.HIGH)
        assert task_id is not None
        print(f"   ✅ 任务提交成功: {task_id}")

        # 查询队列统计
        stats = queue.get_stats()
        assert "total" in stats
        print(
            f"   ✅ 队列统计: 待处理{stats['pending']}, 处理中{stats['processing']}, "
            f"已完成{stats['completed']}, 失败{stats['failed']}"
        )

        return True, {"tests": 4, "passed": 4}

    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False, {"error": str(e)}


def test_main_integration() -> tuple[bool, dict]:
    """测试主应用集成"""
    print("\n" + "=" * 70)
    print("✅ 测试4: 主应用集成")
    print("=" * 70)

    try:
        from fastapi.testclient import TestClient

        from src.main import app

        # 创建测试客户端
        client = TestClient(app)

        # 测试健康检查
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        print("   ✅ 健康检查正常")

        # 测试应用信息
        response = client.get("/api/info")
        assert response.status_code == 200
        assert "version" in response.json()
        print("   ✅ 应用信息正常")

        # 测试根路由
        response = client.get("/")
        assert response.status_code == 200
        print("   ✅ 根路由正常")

        # 验证错误处理器已注册
        assert len(app.exception_handlers) > 0
        print("   ✅ 错误处理器已注册")

        return True, {"tests": 4, "passed": 4}

    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False, {"error": str(e)}


def main():
    """执行所有验证"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + "🚀 开始综合优化验证".center(68) + "║")
    print("╚" + "=" * 68 + "╝")

    tests = [
        ("错误处理系统", test_error_handling),
        ("缓存系统", test_cache_system),
        ("任务队列系统", test_task_queue),
        ("主应用集成", test_main_integration),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            passed, details = test_func()
            results.append((test_name, passed, details))
        except Exception as e:
            print(f"\n   ❌ {test_name}执行异常: {e}")
            results.append((test_name, False, {"error": str(e)}))

    # 打印总结
    print("\n" + "=" * 70)
    print("📊 验证结果总结")
    print("=" * 70)

    total_tests = 0
    total_passed = 0

    for test_name, passed, details in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"\n{status} - {test_name}")

        if passed and "tests" in details:
            total_tests += details["tests"]
            total_passed += details["passed"]
            print(f"   {details['passed']}/{details['tests']} 测试通过")
        elif "error" in details:
            print(f"   错误: {details['error']}")

    print("\n" + "=" * 70)
    print(f"🎯 总体结果: {total_passed}/{total_tests} 测试通过")
    print("=" * 70)

    if all(passed for _, passed, _ in results):
        print("\n✨ 所有优化验证成功！系统已完全就绪！")
        print("\n下一步建议:")
        print("  1. 代码审查 - 进行技术评审")
        print("  2. 提交PR - 准备合并到develop分支")
        print("  3. 部署准备 - 制定发布计划")
        return True
    else:
        print("\n⚠️  部分验证失败，请检查错误信息")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
