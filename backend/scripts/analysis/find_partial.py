#!/usr/bin/env python3
"""Find partially covered files that could improve overall coverage"""

import json
from pathlib import Path

coverage_path = (
    Path(__file__).resolve().parents[3]
    / "test-results"
    / "backend"
    / "coverage"
    / "coverage.json"
)
if not coverage_path.exists():
    coverage_path = Path("coverage.json")

with coverage_path.open() as f:
    data = json.load(f)

files = [
    (
        k,
        v["summary"]["num_statements"],
        v["summary"]["percent_covered"],
        v["summary"]["missing_lines"],
    )
    for k, v in data["files"].items()
]

# Find files with 40+ statements and less than 50% coverage
partial = sorted(
    [f for f in files if f[2] < 50 and f[1] > 40], key=lambda x: x[1], reverse=True
)

print("Partially covered files (<50% coverage, 40+ statements):")
print("-" * 100)
for path, stmts, pct, _ in partial[:20]:
    fname = path.split("\\")[-1] if "\\" in path else path.split("/")[-1]
    uncovered = stmts * (100 - pct) / 100
    print(f"{fname:50} {stmts:4} stmts  {pct:5.1f}%  (~{uncovered:.0f} uncovered)")

# Calculate potential impact
total_uncovered = sum(f[1] * (100 - f[2]) / 100 for f in partial)
print(f"\nTotal uncovered in these files: ~{total_uncovered:.0f} statements")
