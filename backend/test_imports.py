#!/usr/bin/env python
"""测试新模块的导入"""

import sys

sys.path.insert(0, ".")

print("测试 environment.py...")
from src.core.environment import (
    get_environment,
    is_testing,
    is_production,
    get_dependency_policy,
    DependencyPolicy,
)

print("✓ environment.py 导入成功")

print("\n测试 import_utils.py...")
from src.core.import_utils import (
    safe_import,
    safe_import_from,
    create_mock_registry,
    create_lambda_none,
)

print("✓ import_utils.py 导入成功")

print("\n测试 dependency_checker.py...")
from src.core.dependency_checker import dependency_checker

print("✓ dependency_checker.py 导入成功")

print("\n测试环境检测...")
env = get_environment()
print(f"当前环境: {env.value}")
print(f"是否测试环境: {is_testing()}")
print(f"是否生产环境: {is_production()}")
policy = get_dependency_policy()
print(f"依赖策略: {policy.value}")

print("\n✅ 所有测试通过!")
