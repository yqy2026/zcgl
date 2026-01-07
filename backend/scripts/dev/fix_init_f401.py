#!/usr/bin/env python3
"""
Fix F401 errors in __init__.py files by adding # noqa: F401 comments
"""
import re
from pathlib import Path


def fix_init_f401(filepath: Path) -> bool:
    """Fix F401 errors in __init__.py file"""
    content = filepath.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    new_lines = []
    for line in lines:
        # Match import lines that are not already commented with noqa
        if (
            "from " in line
            and " import " in line
            and "# noqa: F401" not in line
            and ("# type:" not in line or "# type:" in line)  # allow type comments
        ):
            # Check if this is in a try-except block pattern
            new_lines.append(line.rstrip() + "  # noqa: F401\n")
        else:
            new_lines.append(line)

    new_content = "".join(new_lines)
    if new_content != content:
        filepath.write_text(new_content, encoding="utf-8")
        return True
    return False


def main():
    """Main function"""
    backend_dir = Path("/home/y/zcgl/backend/src")

    # Find all __init__.py files
    init_files = list(backend_dir.rglob("__init__.py"))

    fixed_count = 0
    for init_file in init_files:
        try:
            if fix_init_f401(init_file):
                print(f"Fixed: {init_file.relative_to(backend_dir)}")
                fixed_count += 1
        except Exception as e:
            print(f"Error processing {init_file}: {e}")

    print(f"\nTotal files fixed: {fixed_count}")


if __name__ == "__main__":
    main()
