#!/usr/bin/env python3
"""
全面修复所有缺失的typing导入
"""

import re
from pathlib import Path


def main():
    print("Fixing all missing typing imports...")

    src_dir = Path("src")
    fixed_count = 0

    # Files that commonly need typing imports
    common_typing_files = [
        "src/core/config_manager.py",
        "src/core/performance.py",
        "src/core/cache_manager.py",
        "src/core/error_codes.py",
        "src/core/security.py",
        "src/core/validators.py",
        "src/middleware/auth.py",
        "src/middleware/api_versioning.py",
        "src/middleware/organization_permission.py",
        "src/services/audit_service.py",
        "src/services/auth_service.py",
        "src/services/contract_extractor.py",
        "src/services/contract_semantic_validator.py",
        "src/services/contract_table_analyzer.py",
        "src/services/database_optimizer.py",
        "src/services/enhanced_field_mapper.py",
        "src/services/error_recovery_service.py",
        "src/services/excel_export.py",
        "src/services/excel_import.py",
        "src/services/history_tracker.py",
        "src/services/ml_enhanced_extractor.py",
        "src/services/monitoring.py",
        "src/services/occupancy_calculator.py",
        "src/services/pdf_processing_service.py",
        "src/services/pdf_session_service.py",
        "src/services/rbac_service.py",
        "src/services/statistics.py",
        "src/utils/api_consistency_checker.py",
        "src/utils/api_performance_optimizer.py",
        "src/utils/filename_sanitizer.py",
        "src/utils/model_utils.py",
        "src/api/v1/analytics.py",
        "src/api/v1/error_recovery.py",
        "src/api/v1/fast_response_optimized.py",
        "src/api/v1/optimized_endpoints.py",
        "src/api/v1/statistics.py",
        "src/api/v1/system_monitoring.py",
        "src/crud/base.py",
        "src/crud/enhanced_base.py",
        "src/crud/asset.py",
        "src/crud/auth.py",
        "src/crud/custom_field.py",
        "src/crud/enum_field.py",
        "src/crud/history.py",
        "src/crud/organization.py",
        "src/crud/ownership.py",
        "src/crud/project.py",
        "src/crud/rent_contract.py",
        "src/crud/rbac.py",
        "src/crud/system_dictionary.py",
        "src/crud/task.py",
        "src/schemas/common.py",
        "src/validation/framework.py",
    ]

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            original = content

            file_path_str = str(py_file).replace("\\", "/")

            # Check if file needs typing imports
            needs_typing = any(
                [
                    "Dict[" in content
                    and "Dict" not in content
                    and "from typing import" in content,
                    "List[" in content
                    and "List" not in content
                    and "from typing import" in content,
                    "Optional[" in content
                    and "Optional" not in content
                    and "from typing import" in content,
                    "Union[" in content
                    and "Union" not in content
                    and "from typing import" in content,
                    "Callable[" in content
                    and "Callable" not in content
                    and "from typing import" in content,
                    "Any[" in content
                    and "Any" not in content
                    and "from typing import" in content,
                ]
            )

            # Also check specific files
            if any(file_path_str.endswith(f) for f in common_typing_files):
                needs_typing = True

            if needs_typing:
                # Determine what typing imports are needed
                needed_imports = []

                if "Dict[" in content and "Dict" not in content:
                    needed_imports.append("Dict")
                if "List[" in content and "List" not in content:
                    needed_imports.append("List")
                if "Optional[" in content and "Optional" not in content:
                    needed_imports.append("Optional")
                if "Union[" in content and "Union" not in content:
                    needed_imports.append("Union")
                if "Callable[" in content and "Callable" not in content:
                    needed_imports.append("Callable")
                if "Any[" in content and "Any" not in content:
                    needed_imports.append("Any")

                if needed_imports:
                    if "from typing import" in content:
                        # Add to existing typing import
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
                    else:
                        # Add new typing import
                        lines = content.split("\n")
                        insert_pos = 0
                        for i, line in enumerate(lines):
                            if line.strip().startswith(("import ", "from ")):
                                insert_pos = i + 1
                            elif line.strip() == "" and insert_pos > 0:
                                break
                        lines.insert(
                            insert_pos,
                            f"from typing import {', '.join(needed_imports)}",
                        )
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
