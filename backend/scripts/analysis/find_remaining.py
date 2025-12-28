"""Find remaining uncovered lines after latest tests"""
import json

with open("coverage.json") as f:
    data = json.load(f)

totals = data["totals"]
covered = totals["covered_lines"]
total = totals["num_statements"]
missing = total - covered
coverage_pct = covered / total * 100

print(f"Coverage: {covered}/{total} ({coverage_pct:.8f}%)")
print(f"Missing: {missing} lines")
print(f"Target (75%): {int(total * 0.75)} lines")
print(f"Gap: {int(total * 0.75) - covered} lines ({75 - coverage_pct:.8f}%)")

# Find files with uncovered lines, sorted by missing count
uncovered = []
for file_path, file_data in data["files"].items():
    if "src" in file_path:
        summary = file_data["summary"]
        file_missing = summary["num_statements"] - summary["covered_lines"]
        if file_missing > 0:
            uncovered.append({
                "file": file_path,
                "missing": file_missing,
                "lines": sorted(file_data["missing_lines"])
            })

uncovered.sort(key=lambda x: x["missing"])

print("\n=== Files with uncovered lines (sorted) ===")
cumulative = 0
for u in uncovered[:20]:
    print(f"{u['missing']:3} lines | {u['file']}")
    if u['missing'] <= 5:
        print(f"           Lines: {u['lines']}")
    cumulative += u['missing']
    if cumulative >= 30:
        break

print(f"\nCumulative from shown files: {cumulative}")
