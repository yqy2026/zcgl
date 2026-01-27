"""直接测试 dictionaries 路由"""

import sys
import os

# 设置环境变量
os.environ["ENVIRONMENT"] = "testing"
os.environ["TESTING_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "E0ocpsl2ek0uCNqh65GUSKwMUy9m20BAMXiTGXvkxm4"

sys.path.insert(0, ".")

from fastapi import FastAPI
from fastapi.testclient import TestClient

# 直接导入 dictionaries router
from src.api.v1.system.dictionaries import router as dict_router

# 创建一个简单的测试应用
app = FastAPI()
app.include_router(dict_router)

# 创建测试客户端
client = TestClient(app)

# 测试路由
print("测试 dictionaries 路由...")
print(f"注册的路由数: {len(app.routes)}")

for route in app.routes:
    if hasattr(route, "path"):
        print(f"  {route.methods} {route.path}")

# 测试一个端点
print("\n测试 GET /types 端点...")
response = client.get("/types")
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    print(f"响应: {response.json()}")
else:
    print(f"错误: {response.text}")
