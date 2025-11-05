#!/usr/bin/env python3
import re
from pathlib import Path


def main():
    print("Fixing final typing errors...")

    src_dir = Path("src")
    fixed_count = 0

    # All remaining patterns to fix
    patterns = [
        # Complex nested patterns
        (r"Dict\[str, Any\]\[str, dict\[str, Any\]\]", r"Dict[str, Dict[str, Any]]"),
        (r"dict\[str, Any\]\[str, dict\[str, Any\]\]", r"dict[str, Dict[str, Any]]"),
    ]

    # Files that need typing imports
    typing_import_files = [
        "src/services/enhanced_field_mapper.py",
        "src/services/contract_semantic_validator.py",
        "src/api/v1/statistics.py",
        "src/api/v1/system_monitoring.py",
        "src/services/occupancy_calculator.py",
        "src/services/history_tracker.py",
        "src/services/error_recovery_service.py",
    ]

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            original = content

            # Apply all pattern fixes
            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content)

            # Add missing typing imports if needed
            file_path_str = str(py_file).replace("\\", "/")
            if any(file_path_str.endswith(f) for f in typing_import_files):
                if "from typing import" in content:
                    # Check what typing imports are missing
                    needed_imports = []
                    if "Dict" in content and "Dict" not in content:
                        needed_imports.append("Dict")

                    if needed_imports:
                        # Add missing imports to existing typing import
                        current_imports = re.search(
                            r"from typing import ([^\n]+)", content
                        )
                        if current_imports:
                            existing_imports = [
                                imp.strip()
                                for imp in current_imports.group(1).split(",")
                            ]
                            for needed in needed_imports:
                                if needed not in existing_imports:
                                    existing_imports.append(needed)
                            new_import_line = (
                                f"from typing import {', '.join(existing_imports)}"
                            )
                            content = content.replace(
                                current_imports.group(0), new_import_line
                            )
                elif "Dict" in content:
                    # Add typing import at the top
                    lines = content.split("\n")
                    insert_pos = 0
                    for i, line in enumerate(lines):
                        if line.strip().startswith(("import ", "from ")):
                            insert_pos = i + 1
                        elif line.strip() == "" and insert_pos > 0:
                            break
                    lines.insert(insert_pos, "from typing import Dict")
                    content = "\n".join(lines)

            if content != original:
                py_file.write_text(content, encoding="utf-8")
                fixed_count += 1
                print(f"Fixed: {py_file}")

        except Exception as e:
            print(f"Error processing {py_file}: {e}")

    print(f"Total fixed: {fixed_count} files")


if __name__ == "__main__":
    main()
