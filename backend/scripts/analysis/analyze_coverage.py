#!/usr/bin/env python
"""Analyze uncovered code lines in security modules."""

import json

# Read coverage.json
with open("coverage.json") as f:
    data = json.load(f)

# Find security-related files
security_files = {}
for file_path, file_data in data["files"].items():
    if (
        "security" in file_path.lower()
        or "token_blacklist" in file_path
        or "logging_security" in file_path
    ):
        if "src" in file_path:  # Only source files, not test files
            summary = file_data["summary"]
            missing = file_data.get("missing_lines", [])
            security_files[file_path] = {
                "coverage": f"{summary['percent_covered']:.1f}%",
                "num_statements": summary["num_statements"],
                "missing_lines": len(missing),
                "missing": missing,
            }

# Print summary
print("=== Coverage Summary for Security Modules ===\n")
for file_path, info in sorted(security_files.items()):
    filename = file_path.split("\\")[-1]
    print(f"{filename}:")
    print(
        f'  Coverage: {info["coverage"]} ({info["missing_lines"]} of {info["num_statements"]} lines missing)'
    )
    if info["missing_lines"] > 0:
        # Group missing lines into ranges
        missing = sorted(info["missing"])
        ranges = []
        start = missing[0]
        end = missing[0]
        for line in missing[1:]:
            if line == end + 1:
                end = line
            else:
                ranges.append(f"{start}-{end}" if start != end else str(start))
                start = end = line
        ranges.append(f"{start}-{end}" if start != end else str(start))
        print(
            f'  Missing lines: {", ".join(ranges[:10])}'
            + ("..." if len(ranges) > 10 else "")
        )
    print()

# Now categorize by importance
print("=== Detailed Analysis of Uncovered Code ===\n")

# For security.py
security_file = "src\\core\\security.py"
if (
    security_file in security_files
    and security_files[security_file]["missing_lines"] > 0
):
    missing = sorted(security_files[security_file]["missing"])
    print("security.py uncovered lines by category:")
    print("  Lines 23-26: Config validation (edge cases)")
    print("  Line 177: File type validation error path")
    print("  Lines 293-300: UploadFile integration method")
    print("  Lines 349, 426: Error handling paths")
    print("  Lines 465-509: Rate limiter configuration and edge cases")
    print("  Lines 642+: Sensitive data filtering edge cases")
    print()

# For logging_security.py
logging_file = "src\\core\\logging_security.py"
if logging_file in security_files and security_files[logging_file]["missing_lines"] > 0:
    missing = sorted(security_files[logging_file]["missing"])
    print("logging_security.py uncovered lines by category:")
    print("  Lines 165-169, 202, 206, 210, 215: Formatter exception handling")
    print("  Lines 270-279, 283-285: Configuration edge cases")
    print("  Lines 430-460, 538, 549+: Security event logging error paths")
    print()

# For token_blacklist.py
token_file = "src\\core\\token_blacklist.py"
if token_file in security_files and security_files[token_file]["missing_lines"] > 0:
    missing = sorted(security_files[token_file]["missing"])
    print(f"token_blacklist.py uncovered lines: {missing}")
    print("  (mostly cleanup edge cases and error handling)")
    print()
