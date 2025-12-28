#!/usr/bin/env python3
"""
API缓存清理脚本
彻底清理API相关的缓存文件和路由信息
"""

import glob
import os
import shutil


def clean_api_cache():
    """清理API相关的缓存"""
    print("开始清理API缓存...")

    # 清理__pycache__目录
    cache_dirs = []
    for root, dirs, _ in os.walk("."):
        if "__pycache__" in dirs:
            cache_dirs.append(os.path.join(root, "__pycache__"))

    for cache_dir in cache_dirs:
        try:
            shutil.rmtree(cache_dir)
            print(f"   [OK] 删除缓存目录: {cache_dir}")
        except Exception as e:
            print(f"   [ERROR] 删除失败 {cache_dir}: {e}")

    # 清理.pyc文件
    pyc_files = glob.glob("**/*.pyc", recursive=True)
    for pyc_file in pyc_files:
        try:
            os.remove(pyc_file)
            print(f"   [OK] 删除pyc文件: {pyc_file}")
        except Exception as e:
            print(f"   [ERROR] 删除失败 {pyc_file}: {e}")

    # 清理特定的PDF导入V2缓存
    v2_cache_files = glob.glob("**/*pdf_import_v2*", recursive=True)
    for cache_file in v2_cache_files:
        try:
            if os.path.isfile(cache_file):
                os.remove(cache_file)
                print(f"   [OK] 删除V2缓存文件: {cache_file}")
            elif os.path.isdir(cache_file):
                shutil.rmtree(cache_file)
                print(f"   [OK] 删除V2缓存目录: {cache_file}")
        except Exception as e:
            print(f"   [ERROR] 删除失败 {cache_file}: {e}")

    print("\n清理统计:")
    print(f"   - 缓存目录: {len(cache_dirs)}")
    print(f"   - pyc文件: {len(pyc_files)}")
    print(f"   - V2缓存文件: {len(v2_cache_files)}")
    print(
        f"   - 总计: {len(cache_dirs) + len(pyc_files) + len(v2_cache_files)} 个文件/目录"
    )


if __name__ == "__main__":
    clean_api_cache()
    print("\nAPI缓存清理完成！")
