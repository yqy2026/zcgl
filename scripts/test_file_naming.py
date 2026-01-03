#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件命名检查脚本 - 测试用例
验证脚本能够正确检测各种文件命名
"""

import subprocess
import sys
from pathlib import Path

# 设置控制台编码为 UTF-8
if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass


def run_test(test_name, files, should_pass=True):
    """运行单个测试"""
    print(f"\n{'='*60}")
    print(f"📝 {test_name}")
    print(f"{'='*60}")

    # 过滤掉不存在的文件
    existing_files = [f for f in files if Path(f).exists()]

    if not existing_files:
        print(f"⚠️  跳过测试（文件不存在）")
        return

    print(f"检查 {len(existing_files)} 个文件:")
    for f in existing_files:
        print(f"  - {f}")
    print()

    result = subprocess.run(
        [sys.executable, "scripts/check_file_naming.py"] + existing_files,
        capture_output=True,
        text=True
    )

    print(result.stdout)

    if result.returncode == 0:
        print("✅ 测试通过（符合规范）")
    else:
        print("❌ 测试失败（不符合规范）")

    return result.returncode == 0


def main():
    """主测试函数"""
    print("=" * 60)
    print("文件命名检查脚本 - 测试套件")
    print("=" * 60)

    tests = [
        # 测试1: Frontend Hook 文件
        (
            "测试1: Frontend Hook 文件",
            [
                "frontend/src/hooks/useAuth.ts",
                "frontend/src/hooks/useAssets.ts",
                "frontend/src/hooks/useProject.ts",
                "frontend/src/hooks/useDictionary.ts",
                "frontend/src/hooks/useErrorHandler.ts",
                "frontend/src/hooks/useAnalytics.ts",
                "frontend/src/hooks/useSearchHistory.ts",
                "frontend/src/hooks/useUserExperience.ts",
                "frontend/src/hooks/useRealTimeUpdates.ts",
            ],
            True
        ),

        # 测试2: Frontend 组件文件
        (
            "测试2: Frontend 组件文件",
            [
                "frontend/src/components/Asset/AssetForm.tsx",
                "frontend/src/components/Asset/AssetCard.tsx",
                "frontend/src/components/Analytics/AnalyticsDashboard.tsx",
                "frontend/src/components/Charts/OccupancyRateChart.tsx",
                "frontend/src/components/Forms/OwnershipForm.tsx",
                "frontend/src/components/Layout/AppLayout.tsx",
                "frontend/src/components/Auth/AuthGuard.tsx",
            ],
            True
        ),

        # 测试3: Frontend 测试文件
        (
            "测试3: Frontend 测试文件",
            [
                "frontend/src/components/Asset/__tests__/AssetCard.test.tsx",
                "frontend/src/hooks/__tests__/useAuth.test.ts",
                "frontend/src/components/Analytics/__tests__/AnalyticsDashboard.test.tsx",
            ],
            True
        ),

        # 测试4: Frontend Service/Util 文件
        (
            "测试4: Frontend Service/Util 文件",
            [
                "frontend/src/utils/format.ts",
                "frontend/src/utils/validationRules.ts",
                "frontend/src/utils/assetCalculations.ts",
                "frontend/src/services/analyticsService.ts",
                "frontend/src/services/ownershipService.ts",
                "frontend/src/types/api.ts",
                "frontend/src/types/auth.ts",
            ],
            True
        ),

        # 测试5: Backend API 文件
        (
            "测试5: Backend API 文件",
            [
                "backend/src/api/v1/assets.py",
                "backend/src/api/v1/auth.py",
                "backend/src/api/v1/rent_contract.py",
                "backend/src/api/v1/organization.py",
                "backend/src/api/v1/ownership.py",
                "backend/src/api/v1/project.py",
                "backend/src/api/v1/excel.py",
                "backend/src/api/v1/monitoring.py",
            ],
            True
        ),

        # 测试6: Backend CRUD/Model/Schema 文件
        (
            "测试6: Backend CRUD/Model/Schema 文件",
            [
                "backend/src/crud/asset.py",
                "backend/src/crud/auth.py",
                "backend/src/models/asset.py",
                "backend/src/models/operation_log.py",
                "backend/src/schemas/asset.py",
                "backend/src/schemas/auth.py",
                "backend/src/schemas/common.py",
            ],
            True
        ),

        # 测试7: Backend Service 文件
        (
            "测试7: Backend Service 文件",
            [
                "backend/src/services/core/audit_service.py",
                "backend/src/services/asset/asset_calculator.py",
                "backend/src/services/permission/permission_cache_service.py",
            ],
            True
        ),

        # 测试8: Store 文件
        (
            "测试8: Store 文件",
            [
                "frontend/src/store/useAppStore.ts",
                "frontend/src/store/useAssetStore.ts",
                "frontend/src/store/useAuthStore.ts",
            ],
            True
        ),

        # 测试9: 类型定义文件
        (
            "测试9: 类型定义文件",
            [
                "frontend/src/vite-env.d.ts",
                "frontend/src/global.d.ts",
            ],
            True
        ),

        # 测试10: 混合文件
        (
            "测试10: 混合 Frontend 和 Backend 文件",
            [
                "frontend/src/hooks/useAuth.ts",
                "backend/src/api/v1/auth.py",
                "frontend/src/components/Auth/AuthGuard.tsx",
                "backend/src/crud/auth.py",
                "frontend/src/utils/format.ts",
                "backend/src/models/asset.py",
            ],
            True
        ),
    ]

    passed = 0
    failed = 0
    skipped = 0

    for test_name, files, should_pass in tests:
        try:
            result = run_test(test_name, files, should_pass)
            if result is None:
                skipped += 1
            elif result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ 测试执行错误: {e}")
            failed += 1

    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"⚠️  跳过: {skipped}")
    print(f"📝 总计: {passed + failed + skipped}")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 所有测试通过！文件命名检查脚本工作正常。")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查脚本逻辑。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
