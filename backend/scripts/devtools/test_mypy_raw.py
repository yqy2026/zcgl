#!/usr/bin/env python3
"""Test mypy raw output"""
import subprocess
import sys
from pathlib import Path

def main():
    cmd = [
        sys.executable, "-m", "mypy",
        "src",
        "--ignore-missing-imports",
        "--show-error-codes"
    ]

    print(f"Running: {' '.join(cmd)}")
    print("="*60)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
        timeout=60
    )

    print(f"Exit code: {result.returncode}")
    print(f"\nStdout ({len(result.stdout)} chars):")
    print(result.stdout[:1000])

    print(f"\nStderr ({len(result.stderr)} chars):")
    print(result.stderr[:1000])

    # Save full output
    output_path = Path(__file__).parent.parent.parent / "mypy_raw_output.txt"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=== STDOUT ===\n")
        f.write(result.stdout)
        f.write("\n=== STDERR ===\n")
        f.write(result.stderr)

    print(f"\nFull output saved to: {output_path}")

if __name__ == "__main__":
    main()
