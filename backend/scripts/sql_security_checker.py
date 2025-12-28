#!/usr/bin/env python3
"""
SQL安全检查器
用于检测和修复潜在的SQL注入风险
"""

import os
import re
from pathlib import Path


class SQLSecurityChecker:
    """SQL安全检查器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues: list[dict] = []

        # 危险的SQL模式
        self.dangerous_patterns = [
            r'execute\s*\(\s*f["\'].*\{.*\}["\']',  # execute(f"...{var}...")
            r'text\s*\(\s*f["\'].*\{.*\}["\']',  # text(f"...{var}...")
            r'format\s*\(.*["\'].*SELECT.*["\']',  # format("SELECT...")
            r"%.*\%.*s",  # %s格式化
            r'\+\s*["\'].*SELECT.*["\']',  # 字符串拼接SQL
        ]

        # 安全的SQL字段名（白名单）
        self.safe_field_names = {
            "id",
            "created_at",
            "updated_at",
            "title",
            "description",
            "status",
            "priority",
            "severity",
            "category",
            "module",
            "assigned_to",
            "environment",
            "root_cause",
            "resolution",
            "fix_version",
            "reporter",
            "defect_id",
            "user_id",
            "role",
            "username",
            "email",
            "password_hash",
            "is_active",
            "is_locked",
        }

    def check_file(self, file_path: Path) -> list[dict]:
        """检查单个文件的SQL安全问题"""
        issues = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            # 检查每一行
            for line_num, line in enumerate(lines, 1):
                # 检查危险的SQL模式
                for pattern in self.dangerous_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append(
                            {
                                "file": str(file_path),
                                "line": line_num,
                                "content": line.strip(),
                                "type": "dangerous_sql",
                                "pattern": pattern,
                                "severity": "HIGH",
                            }
                        )

                # 检查字符串拼接
                if "ORDER BY" in line and "{" in line and "}" in line:
                    if not re.search(
                        r"ORDER BY\s+(created_at|updated_at|severity|priority|status)\s+(ASC|DESC)",
                        line,
                    ):
                        issues.append(
                            {
                                "file": str(file_path),
                                "line": line_num,
                                "content": line.strip(),
                                "type": "sql_injection_order_by",
                                "severity": "HIGH",
                            }
                        )

                # 检查表名注入
                if "FROM" in line and "{" in line and "}" in line:
                    if not re.search(
                        r"FROM\s+(users|assets|defect_reports|audit_logs|user_sessions)",
                        line,
                    ):
                        issues.append(
                            {
                                "file": str(file_path),
                                "line": line_num,
                                "content": line.strip(),
                                "type": "sql_injection_table_name",
                                "severity": "MEDIUM",
                            }
                        )

                # 检查UPDATE SET
                if "UPDATE" in line and "SET" in line and "{" in line:
                    issues.append(
                        {
                            "file": str(file_path),
                            "line": line_num,
                            "content": line.strip(),
                            "type": "sql_injection_update",
                            "severity": "HIGH",
                        }
                    )

        except Exception as e:
            print(f"检查文件 {file_path} 时出错: {e}")

        return issues

    def check_directory(self, directory: str) -> list[dict]:
        """检查目录中的所有Python文件"""
        all_issues = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    issues = self.check_file(file_path)
                    all_issues.extend(issues)

        return all_issues

    def generate_fix(self, issue: dict) -> str:
        """为发现的问题生成修复建议"""
        if issue["type"] == "dangerous_sql":
            return """
# 修复建议：
# 1. 使用参数化查询
# 2. 使用ORM方法
# 3. 对字段名使用白名单验证

# 不安全的代码：
query = f"SELECT * FROM users WHERE name = '{user_name}'"

# 安全的代码：
query = "SELECT * FROM users WHERE name = ?"
cursor.execute(query, (user_name,))
"""

        elif issue["type"] == "sql_injection_order_by":
            return """
# 修复建议：使用白名单验证排序字段

# 不安全的代码：
query += f" ORDER BY {sort_field} {sort_direction}"

# 安全的代码：
allowed_fields = ["created_at", "updated_at", "name"]
allowed_directions = ["ASC", "DESC"]

if sort_field in allowed_fields and sort_direction.upper() in allowed_directions:
    query += f" ORDER BY {sort_field} {sort_direction.upper()}"
else:
    query += " ORDER BY created_at DESC"  # 默认排序
"""

        elif issue["type"] == "sql_injection_table_name":
            return """
# 修复建议：使用白名单验证表名

# 不安全的代码：
query = f"SELECT COUNT(*) FROM {table_name}"

# 安全的代码：
allowed_tables = ["users", "assets", "defect_reports"]
if table_name in allowed_tables:
    query = f"SELECT COUNT(*) FROM {table_name}"
else:
    raise ValueError(f"不允许的表名: {table_name}")
"""

        else:
            return "# 需要手动检查和修复"

    def create_security_report(self) -> str:
        """创建安全检查报告"""
        # 检查src目录
        issues = self.check_directory(str(self.project_root / "src"))

        if not issues:
            return "✅ 未发现SQL安全问题"

        # 按严重程度分类
        high_issues = [i for i in issues if i["severity"] == "HIGH"]
        medium_issues = [i for i in issues if i["severity"] == "MEDIUM"]

        report = []
        report.append("# SQL安全检查报告\n")
        report.append(f"📊 发现 {len(issues)} 个潜在问题")
        report.append(f"🔴 高风险: {len(high_issues)} 个")
        report.append(f"🟡 中风险: {len(medium_issues)} 个\n")

        # 详细问题列表
        for i, issue in enumerate(issues, 1):
            severity_icon = "🔴" if issue["severity"] == "HIGH" else "🟡"
            report.append(f"{severity_icon} **问题 {i}**")
            report.append(f"   文件: {issue['file']}")
            report.append(f"   行号: {issue['line']}")
            report.append(f"   类型: {issue['type']}")
            report.append(f"   代码: `{issue['content']}`")
            report.append(f"   修复建议:\n{self.generate_fix(issue)}")
            report.append("---\n")

        # 总结和建议
        report.append("## 🔧 修复建议总结")
        report.append("1. 立即修复所有高风险问题")
        report.append("2. 使用参数化查询替代字符串拼接")
        report.append("3. 实施字段名和表名白名单验证")
        report.append("4. 使用ORM方法而非原生SQL")
        report.append("5. 实施代码审查流程")

        return "\n".join(report)

    def fix_common_issues(self, file_path: str, dry_run: bool = True) -> bool:
        """自动修复常见问题"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # 修复ORDER BY注入
            content = re.sub(
                r'query\s*\+=\s*f" ORDER BY \{([^}]+)\} \{([^}]+)\.upper\(\)"',
                r'# 安全的排序实现\nif \1 in ["created_at", "updated_at", "severity", "priority"] and \2.upper() in ["ASC", "DESC"]:\n    query += f" ORDER BY {\1} {\2.upper()}"\nelse:\n    query += " ORDER BY created_at DESC"',
                content,
            )

            # 修复表名注入
            content = re.sub(
                r'text\(f"SELECT COUNT\(\*\) FROM \{([^}]+)\}"\)',
                r'# 安全的表名查询\nallowed_tables = ["users", "assets", "defect_reports"]\nif \1 in allowed_tables:\n    count_query = text(f"SELECT COUNT(*) FROM {\1}")\nelse:\n    raise ValueError(f"不允许的表名: {\1}")',
                content,
            )

            if content != original_content:
                if not dry_run:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"✅ 已修复文件: {file_path}")
                else:
                    print(f"🔍 发现可修复的问题: {file_path}")
                return True

        except Exception as e:
            print(f"修复文件 {file_path} 时出错: {e}")

        return False


def main():
    """主函数"""
    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    print("🔍 开始SQL安全检查...")

    # 创建检查器
    checker = SQLSecurityChecker(str(project_root))

    # 生成报告
    report = checker.create_security_report()

    # 输出报告
    print(report)

    # 保存报告到文件
    report_file = project_root / "sql_security_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n📄 报告已保存到: {report_file}")

    # 询问是否自动修复
    try:
        response = input("\n是否尝试自动修复常见问题? (y/n): ").lower()
        if response == "y":
            print("\n🔧 尝试自动修复...")
            checker.fix_common_issues(
                str(project_root / "src" / "api" / "v1" / "defect_tracking.py"),
                dry_run=False,
            )
    except KeyboardInterrupt:
        print("\n操作已取消")


if __name__ == "__main__":
    main()
