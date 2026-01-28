"""测试导入以定位问题"""

import sys
import os

# 设置环境变量（必须在导入之前）
os.environ["ENVIRONMENT"] = "testing"
os.environ["TESTING_MODE"] = "true"
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "postgresql://user:pass@localhost:5432/zcgl_test")
os.environ["SECRET_KEY"] = "E0ocpsl2ek0uCNqh65GUSKwMUy9m20BAMXiTGXvkxm4"

try:
    print("尝试导入 dictionaries router...")
    from src.api.v1.system.dictionaries import router as dict_router

    print(f"✅ dictionaries router 导入成功，路由数: {len(dict_router.routes)}")
    for route in dict_router.routes:
        if hasattr(route, "path"):
            print(f"  {route.methods} {route.path}")
except Exception as e:
    print(f"❌ 导入失败: {e}")
    import traceback

    traceback.print_exc()

try:
    print("\n尝试导入 api_router...")
    from src.api.v1 import api_router

    print(f"✅ api_router 导入成功")
except Exception as e:
    print(f"❌ 导入失败: {e}")
    import traceback

    traceback.print_exc()
