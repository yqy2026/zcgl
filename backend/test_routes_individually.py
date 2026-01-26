"""逐个测试路由导入以定位问题"""
import sys
import os

# 设置环境变量
os.environ["ENVIRONMENT"] = "testing"
os.environ["TESTING_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "E0ocpsl2ek0uCNqh65GUSKwMUy9m20BAMXiTGXvkxm4"

# 要测试的路由模块列表（按 v1/__init__.py 中的顺序）
route_modules = [
    ("auth.admin", "admin_router"),
    ("analytics.analytics", "analytics_router"),
    ("assets.assets", "assets_router"),
    ("auth.auth", "auth_router"),
    ("system.backup", "backup_router"),
    ("system.collection", "collection_router"),
    ("system.contact", "contact_router"),
    ("assets.custom_fields", "custom_fields_router"),
    ("system.dictionaries", "dictionaries_router"),
    ("system.enum_field", "enum_field_router"),
    ("system.error_recovery", "error_recovery_router"),
]

print("开始逐个测试路由导入...\n")

for module_path, router_name in route_modules:
    try:
        full_path = f"src.api.v1.{module_path}"
        print(f"测试: {full_path}...", end=" ")
        
        # 动态导入
        parts = full_path.split(".")
        module = __import__(full_path, fromlist=[router_name])
        router = getattr(module, "router")
        
        print(f"✓ 成功 (路由数: {len(router.routes)})")
        
    except Exception as e:
        print(f"✗ 失败")
        print(f"  错误: {str(e)[:200]}")
        print(f"  类型: {type(e).__name__}")
        break  # 在第一个失败处停止

print("\n测试完成")
