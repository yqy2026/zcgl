#!/usr/bin/env python3
import re
from pathlib import Path

def main():
    print("Fixing List[Any][...] typing errors...")

    src_dir = Path("src")
    fixed_count = 0

    # Pattern to fix: List[Any][SomeType] -> List[SomeType]
    wrong_pattern = r'List\[Any\]\[([^]]+)\]'

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text(encoding='utf-8')
            original = content

            # Fix the wrong typing annotations
            content = re.sub(wrong_pattern, r'List[\1]', content)

            if content != original:
                py_file.write_text(content, encoding='utf-8')
                fixed_count += 1
                print(f"Fixed: {py_file}")

        except Exception as e:
            print(f"Error processing {py_file}: {e}")

    print(f"Total fixed: {fixed_count} files")

if __name__ == "__main__":
    main()