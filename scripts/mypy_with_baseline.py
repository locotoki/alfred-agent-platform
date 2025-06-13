#!/usr/bin/env python3
"""Run mypy and filter out baseline errors."""

import subprocess
import sys
from pathlib import Path

def load_baseline():
    """Load baseline errors from file."""
    baseline_file = Path(".mypy-baseline.txt")
    if not baseline_file.exists():
        return set()

    baseline_errors = set()
    with open(baseline_file, "r") as f:
        for line in f:
            # Store each error line as is
            baseline_errors.add(line.strip())

    return baseline_errors

def run_mypy(args):
    """Run mypy and capture output."""
    cmd = ["mypy"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def filter_errors(output, baseline):
    """Filter out baseline errors from mypy output."""
    new_errors = []
    error_count = 0

    for line in output.strip().split("\n"):
        if line.strip() in baseline:
            continue

        # Count errors
        if " error: " in line:
            error_count += 1

        new_errors.append(line)

    return "\n".join(new_errors), error_count

def main():
    """Execute the main logic to run mypy with baseline filtering."""
    # Load baseline
    baseline = load_baseline()

    # Run mypy
    mypy_args = sys.argv[1:] if len(sys.argv) > 1 else ["."]
    stdout, stderr, returncode = run_mypy(mypy_args)

    # Filter errors
    filtered_output, new_error_count = filter_errors(stdout, baseline)

    # Print output
    if filtered_output:
        print(filtered_output)

    if stderr:
        print(stderr, file=sys.stderr)

    # Exit with appropriate code
    if new_error_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
