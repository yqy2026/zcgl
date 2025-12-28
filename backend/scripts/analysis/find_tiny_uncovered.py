#!/usr/bin/env python3
"""Find very small untested files (<30 statements)"""

import json

with open("coverage.json") as f:
    data = json.load(f)

files = [
    (k, v["summary"]["num_statements"], v["summary"]["percent_covered"])
    for k, v in data["files"].items()
]

# Find very small files with 0% coverage (1-30 statements)
tiny_uncovered = sorted(
    [f for f in files if f[2] == 0 and 1 <= f[1] <= 30],
    key=lambda x: x[1],
    reverse=True,
)

print("Very small zero-coverage files (1-30 statements):")
print("-" * 80)
for path, stmts, _ in tiny_uncovered[:20]:
    fname = path.split("\\")[-1] if "\\" in path else path.split("/")[-1]
    print(f"{fname:50} {stmts:4} stmts")

total = sum(f[1] for f in tiny_uncovered)
print(f"\nTotal statements in tiny uncovered files: {total}")

# Also find files with <50% coverage and small size
print("\n\nSmall files with partial coverage (<50%, 20-50 statements):")
print("-" * 80)
partial_small = sorted(
    [f for f in files if f[2] < 50 and 20 <= f[1] <= 50],
    key=lambda x: x[1],
    reverse=True,
)
for path, stmts, pct in partial_small[:10]:
    fname = path.split("\\")[-1] if "\\" in path else path.split("/")[-1]
    print(f"{fname:50} {stmts:4} stmts  {pct:5.1f}%")
