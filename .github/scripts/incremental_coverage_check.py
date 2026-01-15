#!/usr/bin/env python3
"""
Incremental Coverage Checker - Smart Path to 85%/75%

增量覆盖率检查器 - 智能路径到85%/75%

This script implements a smart coverage checking mechanism that:
- Maintains high standards (85% backend / 75% frontend)
- Allows gradual improvement when below thresholds
- Prevents CI gridlock while ensuring progress

实现智能覆盖率检查机制:
- 维持高标准 (85% 后端 / 75% 前端)
- 低于阈值时允许逐步改进
- 确保进展同时避免CI停滞

Usage:
    python incremental_coverage_check.py <coverage.xml> [baseline_coverage%] [--target=85] [--soft-threshold=80]

Examples:
    python incremental_coverage_check.py coverage.xml
    python incremental_coverage_check.py coverage.xml 78.5
    python incremental_coverage_check.py coverage.xml 78.5 --target=85 --soft-threshold=80

Exit codes:
    0: Coverage check passed (覆盖率检查通过)
    1: Coverage check failed (覆盖率检查失败)
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple


def extract_coverage(coverage_xml: Path) -> float:
    """
    Extract coverage percentage from XML report.

    Args:
        coverage_xml: Path to coverage.xml file

    Returns:
        Coverage percentage (0-100)
    """
    if not coverage_xml.exists():
        print(f"❌ Coverage file not found: {coverage_xml}")
        sys.exit(1)

    try:
        tree = ET.parse(coverage_xml)
        root = tree.getroot()

        # Coverage XML format: <coverage line-rate="0.XXX">
        line_rate = float(root.attrib.get('line-rate', 0))
        coverage_pct = line_rate * 100

        return coverage_pct
    except Exception as e:
        print(f"❌ Error parsing coverage file: {e}")
        sys.exit(1)


def check_coverage_incremental(
    current_pct: float,
    baseline_pct: Optional[float] = None,
    target: float = 85.0,
    soft_threshold: float = 80.0,
    increment: float = 1.0
) -> Tuple[bool, str]:
    """
    Check coverage with incremental requirements.

    Args:
        current_pct: Current coverage percentage
        baseline_pct: Baseline coverage from previous run (optional)
        target: Target coverage percentage
        soft_threshold: Below this: incremental mode active
        increment: Required improvement when below soft_threshold

    Returns:
        Tuple of (passed: bool, message: str)
    """
    # Round to 1 decimal place for consistent display
    current_pct = round(current_pct, 1)

    # Case 1: Already at or above target
    if current_pct >= target:
        return True, f"✅ Coverage {current_pct:.1f}% meets target {target:.0f}%"

    # Case 2: Between soft threshold and target
    if current_pct >= soft_threshold:
        gap = target - current_pct
        return False, f"⚠️  Coverage {current_pct:.1f}% is {gap:.1f}% below target {target:.0f}% - must reach target"

    # Case 3: Below soft threshold - incremental mode
    if baseline_pct is not None:
        baseline_pct = round(baseline_pct, 1)
        improvement = current_pct - baseline_pct

        if improvement < 0:
            return False, f"❌ Coverage decreased by {abs(improvement):.1f}% (current: {current_pct:.1f}%, baseline: {baseline_pct:.1f}%)"

        if improvement >= increment:
            next_target = min(current_pct + increment, target)
            return True, f"✅ Coverage improved by {improvement:.1f}% (current: {current_pct:.1f}%, baseline: {baseline_pct:.1f}%, next target: {next_target:.1f}%)"
        else:
            needed = increment - improvement
            return False, f"❌ Coverage improvement {improvement:.1f}% below required {increment:.1f}% (current: {current_pct:.1f}%, baseline: {baseline_pct:.1f}%, need {needed:.1f}% more)"

    # No baseline provided - just report current status
    return False, f"⚠️  Current coverage {current_pct:.1f}% - below soft threshold {soft_threshold:.0f}% - next PR must improve by at least {increment:.1f}%"


def main():
    parser = argparse.ArgumentParser(
        description='Incremental coverage checker for smart path to high standards',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'coverage_file',
        type=Path,
        help='Path to coverage.xml file'
    )

    parser.add_argument(
        'baseline',
        type=float,
        nargs='?',
        default=None,
        help='Baseline coverage percentage from previous run (optional)'
    )

    parser.add_argument(
        '--target',
        type=float,
        default=85.0,
        help='Target coverage percentage (default: 85.0)'
    )

    parser.add_argument(
        '--soft-threshold',
        type=float,
        default=80.0,
        help='Soft threshold for incremental mode (default: 80.0)'
    )

    parser.add_argument(
        '--increment',
        type=float,
        default=1.0,
        help='Required improvement percentage when below threshold (default: 1.0)'
    )

    args = parser.parse_args()

    # Extract current coverage
    current_coverage = extract_coverage(args.coverage_file)

    # Check with incremental logic
    passed, message = check_coverage_incremental(
        current_coverage,
        args.baseline,
        args.target,
        args.soft_threshold,
        args.increment
    )

    # Print result
    print(message)

    # Exit with appropriate code
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
