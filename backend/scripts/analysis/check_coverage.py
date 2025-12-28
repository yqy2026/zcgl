"""Check exact uncovered lines to target"""
import json

with open("coverage.json", "r") as f:
    data = json.load(f)

# Get the exact uncovered lines we need to target
targets = [
    "src/core/encoding_utils.py",
    "src/schemas/enum_field.py",
    "src/utils/file_security.py",
    "src/api/v1/__init__.py"
]

print("=== 当前未覆盖的具体行 ===")
total_uncovered = 0
for file_path in targets:
    if file_path in data["files"]:
        file_data = data["files"][file_path]
        missing = sorted(file_data["missing_lines"])
        if missing:
            print(f"{file_path}: {missing}")
            total_uncovered += len(missing)

print(f"\n这4个文件共有 {total_uncovered} 行未覆盖")

# Also check the unreachable ones
unreachable = [
    "src/services/analytics/__init__.py",
    "src/services/asset/__init__.py"
]

print("\n=== 无法覆盖的行（服务已归档）===")
for file_path in unreachable:
    if file_path in data["files"]:
        file_data = data["files"][file_path]
        missing = sorted(file_data["missing_lines"])
        if missing:
            print(f"{file_path}: {missing} (UNREACHABLE - services archived)")
