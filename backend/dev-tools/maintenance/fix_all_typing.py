#!/usr/bin/env python3
import re
from pathlib import Path


def main():
    print("Fixing all typing errors...")

    src_dir = Path("src")
    fixed_count = 0

    # All patterns to fix
    patterns = [
        # List errors
        (r"List\[Any\]\[([^]]+)\]", r"List[\1]"),
        # Dict errors
        (r"Dict\[str, Any\]\[str, Any\]", r"Dict[str, Any]"),
        (r"Dict\[str, Any\]\[str, list\[str\]\]", r"Dict[str, List[str]]"),
        (r"dict\[str, Any\]\[str\]", r"dict[str, str]"),
        (r"Dict\[str, Any\]\[str\]", r"Dict[str, str]"),
        # Complex nested patterns
        (r"dict\[str, Any\]\[str, list\[str\]\]", r"dict[str, List[str]]"),
    ]

    # Files that need Dict import
    dict_import_files = [
        "src/services/contract_extractor.py",
        "src/validation/framework.py",
        "src/services/contract_semantic_validator.py",
        "src/services/contract_table_analyzer.py",
        "src/services/rbac_service.py",
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

            # Add missing Dict import if needed
            file_path_str = str(py_file).replace("\\", "/")
            if any(file_path_str.endswith(f) for f in dict_import_files):
                if "from typing import" in content and "Dict" not in content:
                    # Add Dict to existing typing import
                    content = re.sub(
                        r"from typing import ([^\n]+)",
                        lambda m: f"from typing import Dict, {m.group(1)}"
                        if m.group(1).strip()
                        else "from typing import Dict",
                        content,
                    )
                elif "from typing import" not in content and "Dict" in content:
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
