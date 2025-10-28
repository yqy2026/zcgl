#!/usr/bin/env python3
"""
修复AuditLogCRUD.create方法，添加details参数支持
"""

import re

def fix_audit_log_crud():
    """修复AuditLogCRUD.create方法"""
    file_path = "src/crud/auth.py"

    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 找到AuditLogCRUD.create方法并添加details参数
        pattern = r'(session_id: str \| None = None,\s+)(\) -> AuditLog:)'
        replacement = r'\1details: str | None = None,\n    \2'

        new_content = re.sub(pattern, replacement, content)

        if new_content != content:
            # 写入修复后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("Success: AuditLogCRUD.create method fixed, details parameter added")
            return True
        else:
            print("⚠️ 未找到需要修复的模式")
            return False

    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False

if __name__ == "__main__":
    fix_audit_log_crud()