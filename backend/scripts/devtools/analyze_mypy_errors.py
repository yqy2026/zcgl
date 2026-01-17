#!/usr/bin/env python3
"""Analyze mypy errors and group by file"""
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def run_mypy():
    """Run mypy and capture output"""
    cmd = [
        sys.executable, "-m", "mypy",
        "src",
        "--ignore-missing-imports",
        "--show-error-codes",
        "--no-error-summary"
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent
    )

    return result.stdout + result.stderr

def parse_errors(output: str):
    """Parse mypy output and group errors by file"""
    errors_by_file = defaultdict(list)
    total_errors = 0

    for line in output.split('\n'):
        if not line.strip():
            continue

        # Skip non-error lines
        if ':' not in line or 'error:' not in line:
            continue

        try:
            # Parse line format: file:line: error: message [error-code]
            parts = line.split(':', 3)
            if len(parts) >= 4:
                file_path = parts[0].strip()
                line_num = parts[1].strip()
                error_part = parts[3].strip() if len(parts) > 3 else ""

                if 'error:' in error_part:
                    total_errors += 1
                    errors_by_file[file_path].append({
                        'line': line_num,
                        'message': error_part
                    })
        except Exception:
            print(f"Warning: Failed to parse line: {line[:100]}", file=sys.stderr)

    return errors_by_file, total_errors

def main():
    print("Running mypy analysis...")
    output = run_mypy()

    errors_by_file, total_errors = parse_errors(output)

    print(f"\n{'='*60}")
    print(f"Total errors: {total_errors}")
    print(f"{'='*60}\n")

    # Sort files by error count
    sorted_files = sorted(
        errors_by_file.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    print("Top 40 files with most errors:\n")
    for i, (file_path, errors) in enumerate(sorted_files[:40], 1):
        file_name = file_path.replace('\\', '/').split('/')[-1]
        print(f"{i:2d}. {file_name:40s} ({len(errors):3d} errors)")

    print(f"\n{'='*60}")
    print(f"Files with errors: {len(errors_by_file)}")
    print(f"Total errors: {total_errors}")
    print(f"{'='*60}")

    # Save detailed report
    report_path = Path(__file__).parent.parent.parent / "mypy_error_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("MyPy Error Report\n")
        f.write(f"{'='*60}\n")
        f.write(f"Total errors: {total_errors}\n")
        f.write(f"Files with errors: {len(errors_by_file)}\n")
        f.write(f"{'='*60}\n\n")

        for file_path, errors in sorted_files:
            f.write(f"\n{file_path} ({len(errors)} errors)\n")
            f.write(f"{'-'*60}\n")
            for error in errors[:10]:  # Show first 10 errors per file
                f.write(f"  Line {error['line']}: {error['message']}\n")
            if len(errors) > 10:
                f.write(f"  ... and {len(errors) - 10} more errors\n")

    print(f"\nDetailed report saved to: {report_path}")

if __name__ == "__main__":
    main()
