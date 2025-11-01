#!/usr/bin/env python3
"""
测试恢复脚本
恢复之前禁用的测试文件
"""

import os
import shutil
from pathlib import Path

# 之前禁用的测试文件列表
PROBLEMATIC_TESTS = [
    "tests/test_asset_performance.py",
    "tests/test_asset_rbac_integration.py",
    "tests/test_backup.py",
    "tests/test_enhanced_pdf_processor.py",
    "tests/test_error_recovery.py",
    "tests/test_excel_export.py",
    "tests/test_occupancy_calculator.py",
    "tests/test_rbac_complete.py",
    "tests/test_schemas.py",
    "tests/test_statistics.py",
    "tests/test_ultra_fast.py"
]

def restore_backend_tests():
    """恢复后端测试"""
    backend_dir = Path(__file__).parent.parent
    disabled_dir = backend_dir / "tests_disabled"

    restored_count = 0
    for test_file in PROBLEMATIC_TESTS:
        src_path = disabled_dir / Path(test_file).name
        dst_path = backend_dir / test_file

        if src_path.exists():
            # 确保目标目录存在
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            print(f"✅ 已恢复: {test_file}")
            restored_count += 1
        else:
            print(f"⚠️  文件不存在: {test_file}")

    # 清理空的禁用目录
    if disabled_dir.exists() and not any(disabled_dir.iterdir()):
        disabled_dir.rmdir()
        print(f"🧹 清理禁用目录: {disabled_dir}")

    print(f"\n📊 恢复结果:")
    print(f"   - 恢复测试文件: {restored_count}")

    return restored_count

def main():
    """主函数"""
    print("🔄 开始恢复测试...")

    # 恢复后端测试
    restored_count = restore_backend_tests()

    print(f"\n✅ 测试恢复完成!")
    print(f"   - 恢复测试文件: {restored_count}个")
    print(f"   - 现在可以运行完整测试套件")

if __name__ == "__main__":
    main()