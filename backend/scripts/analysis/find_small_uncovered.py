#!/usr/bin/env python3
"""Find small untested files (10-40 statements)"""

import json

with open("coverage.json") as f:
    data = json.load(f)

files = [
    (k, v["summary"]["num_statements"], v["summary"]["percent_covered"])
    for k, v in data["files"].items()
]

# Find small files with 0% coverage (10-40 statements)
small_uncovered = sorted(
    [f for f in files if f[2] == 0 and 10 <= f[1] < 40],
    key=lambda x: x[1],
    reverse=True,
)

print("Small zero-coverage files (10-40 statements):")
print("-" * 80)
for path, stmts, _ in small_uncovered[:20]:
    fname = path.split("\\")[-1] if "\\" in path else path.split("/")[-1]
    print(f"{fname:50} {stmts:4} stmts")

total = sum(f[1] for f in small_uncovered)
print(f"\nTotal statements in small uncovered files: {total}")
