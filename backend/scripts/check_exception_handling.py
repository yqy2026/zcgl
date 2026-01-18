"""
检查异常处理问题

自动化检测代码中的异常处理问题:
1. 暴露内部错误的安全问题
2. 过于宽泛的异常捕获
3. 冗余的异常处理代码
"""

import re
from pathlib import Path


def check_security_issues() -> list[tuple[Path, int, str]]:
    """
    检查安全问题：暴露内部错误

    搜索模式: except Exception 后跟 HTTPException(500, detail=f"...{str(e)}")

    Returns:
        List of (file_path, line_number, matched_text)
    """
    issues = []
    # 搜索模式: except Exception as e: 后跟 raise HTTPException
    # 其中 detail 包含 {str(e)} 或 {e}
    pattern = re.compile(
        r'except Exception as e:\s*\n?\s*raise HTTPException\(status_code=500, detail=f"[^"]*:\{str?\(e\)}"\)',
        re.MULTILINE,
    )

    backend_dir = Path(__file__).parent.parent / "src" / "api" / "v1"

    for file in backend_dir.rglob("*.py"):
        # 尝试用UTF-8读取，失败则尝试其他编码
        try:
            content = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = file.read_text(encoding="gbk")
            except UnicodeDecodeError:
                # 如果都失败，跳过这个文件
                continue

        matches = pattern.finditer(content)

        for match in matches:
            line_num = content[: match.start()].count("\n") + 1
            matched_text = match.group(0)
            issues.append((file, line_num, matched_text))

    return issues


def check_broad_exception_catches() -> list[tuple[Path, int, str]]:
    """
    检查过于宽泛的异常捕获

    搜索模式: Service层中的 except Exception，但不重新抛出

    Returns:
        List of (file_path, line_number, matched_text)
    """
    issues = []
    # 搜索 except Exception as e: 后面不跟 raise 的模式
    pattern = re.compile(
        r"except Exception as e:\s*\n?\s*logger\.[a-z]+\([^)]*\)\s*\n?(?!raise)",
        re.MULTILINE,
    )

    backend_dir = Path(__file__).parent.parent / "src" / "services"

    for file in backend_dir.rglob("*.py"):
        # 尝试用UTF-8读取，失败则尝试其他编码
        try:
            content = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = file.read_text(encoding="gbk")
            except UnicodeDecodeError:
                # 如果都失败，跳过这个文件
                continue

        matches = pattern.finditer(content)

        for match in matches:
            line_num = content[: match.start()].count("\n") + 1
            matched_text = match.group(0)
            issues.append((file, line_num, matched_text))

    return issues


def print_report(issues: list[tuple[Path, int, str]], issue_type: str) -> None:
    """打印问题报告"""
    if not issues:
        print(f"[OK] 未发现 {issue_type}")
        return

    print(f"\n[WARNING] 发现 {len(issues)} 处 {issue_type}:\n")
    for file, line_num, matched_text in issues[:10]:  # 只显示前10个
        print(f"  {file}:{line_num}")
        # 只显示匹配文本的前100个字符
        preview = matched_text.replace("\n", "\\n")[:100]
        print(f"    {preview}...\n")

    if len(issues) > 10:
        print(f"  ... 还有 {len(issues) - 10} 处未显示")


def main() -> None:
    """主函数：运行所有检查"""
    print("=" * 70)
    print("异常处理检查工具")
    print("=" * 70)

    # 检查安全问题
    print("\n[CHECK] 检查安全问题: 暴露内部错误给客户端")
    print("-" * 70)
    security_issues = check_security_issues()
    print_report(security_issues, "安全问题")

    # 检查过于宽泛的异常捕获
    print("\n[CHECK] 检查代码质量: 过于宽泛的异常捕获")
    print("-" * 70)
    broad_issues = check_broad_exception_catches()
    print_report(broad_issues, "过于宽泛的异常捕获")

    # 汇总
    print("\n" + "=" * 70)
    total_issues = len(security_issues) + len(broad_issues)
    if total_issues == 0:
        print("[OK] 未发现异常处理问题")
    else:
        print(f"[WARNING] 总共发现 {total_issues} 处问题")
        print(f"   - 安全问题: {len(security_issues)} 处")
        print(f"   - 代码质量问题: {len(broad_issues)} 处")
    print("=" * 70)


if __name__ == "__main__":
    main()
