#!/usr/bin/env python3
"""
自动修复泛型参数缺失问题

将代码中的裸泛型类型自动添加类型参数：
  list → list[Any]
  dict → dict[str, Any]
  tuple → tuple[Any, ...]

Usage:
    python fix_type_args.py                  # 预览变更（dry-run）
    python fix_type_args.py --apply         # 应用修复
    python fix_type_args.py --file <path>   # 修复单个文件
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any

# 需要在文件顶部导入的语句
REQUIRED_IMPORTS = {
    "Any": "from typing import Any",
}


def add_import_if_needed(file_path: Path, content: str, import_type: str) -> str:
    """检查并添加必要的导入"""
    import_statement = REQUIRED_IMPORTS.get(import_type)

    if not import_statement:
        return content

    # 检查是否已导入
    if import_type in content:
        return content

    # 查找导入区域
    lines = content.split("\n")
    import_end = 0

    # 找到最后一个 import 语句
    for i, line in enumerate(lines):
        if line.strip().startswith("import ") or line.strip().startswith("from "):
            import_end = i

    if import_end > 0:
        # 在最后一个 import 后插入
        lines.insert(import_end + 1, import_statement)
    else:
        # 在文件开头插入（在 shebang 和 docstring 之后）
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(("'''", '"""')):
                # 找到 docstring 结束
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith(("'''", '"""')):
                        insert_pos = j + 1
                        break
                break

        lines.insert(insert_pos, "")
        lines.insert(insert_pos + 1, import_statement)

    return "\n".join(lines)


def fix_generic_types(content: str) -> tuple[str, dict[str, int]]:
    """自动修复泛型参数

    Returns:
        (修复后的内容, 统计信息)
    """
    original = content
    stats = {"list": 0, "dict": 0, "tuple": 0, "total": 0}

    # Pattern 1: list → list[Any]
    # 避免匹配: list[str] (已有泛型), : list (类型注解中的 list), list: (变量声明)
    content = re.sub(
        r"""
        (?<![:\[\s])     # 不紧跟在 : [ 或空格后
        \blist\b
        (?!
            [:\[)]       # 不紧跟 : [ 或 )
            |\s*\[       # 或紧跟 [
        )
        """,
        r"list[Any]",
        content,
        flags=re.VERBOSE,
    )
    count_list = content.count("list[Any]") - original.count("list[Any]")
    stats["list"] = count_list

    # Pattern 2: dict → dict[str, Any]
    # 同样的避免规则
    content = re.sub(
        r"""
        (?<![:\[\s])
        \bdict\b
        (?!
            [:\[)]
            |\s*\[
        )
        """,
        r"dict[str, Any]",
        content,
        flags=re.VERBOSE,
    )
    count_dict = content.count("dict[str, Any]") - original.count("dict[str, Any]")
    stats["dict"] = count_dict

    # Pattern 3: tuple → tuple[Any, ...]
    content = re.sub(
        r"""
        (?<![:\[\s])
        \btuple\b
        (?!
            [:\[)]
            |\s*\[
        )
        """,
        r"tuple[Any, ...]",
        content,
        flags=re.VERBOSE,
    )
    count_tuple = content.count("tuple[Any, ...]") - original.count("tuple[Any, ...]")
    stats["tuple"] = count_tuple

    stats["total"] = sum(stats.values())

    return content, stats


def fix_file(file_path: Path, dry_run: bool = True) -> dict[str, Any]:
    """修复单个文件"""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "file": str(file_path),
            "status": "error",
            "error": str(e),
        }

    original_content = content

    # 修复泛型类型
    content, stats = fix_generic_types(content)

    # 检查是否需要添加 Any 导入
    if stats["total"] > 0 and "Any" not in original_content:
        content = add_import_if_needed(file_path, content, "Any")

    # 计算变更
    changes = stats["total"] > 0

    result = {
        "file": str(file_path),
        "status": "changed" if changes else "unchanged",
        "changes": stats,
    }

    if changes and not dry_run:
        try:
            file_path.write_text(content, encoding="utf-8")
            result["written"] = True
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

    return result


def fix_directory(
    source_dir: Path, dry_run: bool = True, pattern: str = "*.py"
) -> dict[str, Any]:
    """修复目录中的所有 Python 文件"""
    results = []
    total_stats = {"list": 0, "dict": 0, "tuple": 0, "total": 0, "files_changed": 0}

    for py_file in source_dir.rglob(pattern):
        # 跳过虚拟环境和缓存目录
        if any(
            part in py_file.parts
            for part in ["venv", ".venv", "__pycache__", ".tox", "node_modules"]
        ):
            continue

        result = fix_file(py_file, dry_run)
        results.append(result)

        if result["status"] == "changed":
            total_stats["files_changed"] += 1
            for key in ["list", "dict", "tuple", "total"]:
                total_stats[key] += result["changes"][key]

    return {"results": results, "summary": total_stats}


def print_report(results: dict[str, Any], dry_run: bool):
    """打印修复报告"""
    print("=" * 80)
    print(" 泛型参数自动修复报告")
    print("=" * 80)

    summary = results["summary"]
    mode = "预览模式 (DRY-RUN)" if dry_run else "应用模式 (APPLY)"
    print(f"\n模式: {mode}")
    print(f"扫描文件数: {len(results['results'])}")
    print(f"修改文件数: {summary['files_changed']}")
    print("\n修复统计:")
    print(f"  list[Any]:          {summary['list']:5d} 处")
    print(f"  dict[str, Any]:     {summary['dict']:5d} 处")
    print(f"  tuple[Any, ...]:    {summary['tuple']:5d} 处")
    print(f"  总计:               {summary['total']:5d} 处")

    # 显示修改的文件
    if summary["files_changed"] > 0:
        print(f"\n修改的文件 (共 {summary['files_changed']} 个):")
        for result in results["results"]:
            if result["status"] == "changed":
                changes = result["changes"]
                print(
                    f"  - {result['file']}: "
                    f"list={changes['list']}, dict={changes['dict']}, tuple={changes['tuple']}"
                )

    print("\n" + "=" * 80)

    if dry_run and summary["files_changed"] > 0:
        print("\n提示: 这是预览模式，使用 --apply 参数应用修复")
        print("   示例: python fix_type_args.py --apply")


def main():
    parser = argparse.ArgumentParser(
        description="自动修复泛型参数缺失问题",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python fix_type_args.py                  # 预览变更
  python fix_type_args.py --apply         # 应用修复
  python fix_type_args.py --file src/utils/model_utils.py
  python fix_type_args.py --apply --source-dir src/services
        """,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="应用修复（默认为预览模式）",
    )
    parser.add_argument("--file", type=Path, help="修复单个文件")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("src"),
        help="源代码目录（默认: src）",
    )
    parser.add_argument("--pattern", default="*.py", help="文件匹配模式（默认: *.py）")

    args = parser.parse_args()

    if args.file:
        # 修复单个文件
        if not args.file.exists():
            print(f"错误: 文件不存在: {args.file}")
            sys.exit(1)

        result = fix_file(args.file, dry_run=not args.apply)
        print(f"\n文件: {result['file']}")
        print(f"状态: {result['status']}")

        if result["status"] == "changed":
            changes = result["changes"]
            print(
                f"修复: list={changes['list']}, dict={changes['dict']}, tuple={changes['tuple']}"
            )
    else:
        # 修复目录
        if not args.source_dir.exists():
            print(f"错误: 目录不存在: {args.source_dir}")
            sys.exit(1)

        print(f"扫描目录: {args.source_dir}")
        print("请稍候...\n")

        results = fix_directory(
            args.source_dir, dry_run=not args.apply, pattern=args.pattern
        )
        print_report(results, dry_run=not args.apply)


if __name__ == "__main__":
    main()
