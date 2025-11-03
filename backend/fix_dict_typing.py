#!/usr/bin/env python3
import re
from pathlib import Path

def main():
    print("Fixing Dict typing errors...")

    src_dir = Path("src")
    fixed_count = 0

    # Pattern to fix: Dict[str, Any][str, Any] -> Dict[str, Any]
    patterns = [
        (r'Dict\[str, Any\]\[str, Any\]', r'Dict[str, Any]'),
        (r'dict\[str, Any\]\[str\]', r'dict[str, str]'),
        (r'Dict\[str, Any\]\[str\]', r'Dict[str, str]'),
    ]

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text(encoding='utf-8')
            original = content

            # Apply all pattern fixes
            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content)

            if content != original:
                py_file.write_text(content, encoding='utf-8')
                fixed_count += 1
                print(f"Fixed: {py_file}")

        except Exception as e:
            print(f"Error processing {py_file}: {e}")

    print(f"Total fixed: {fixed_count} files")

if __name__ == "__main__":
    main()