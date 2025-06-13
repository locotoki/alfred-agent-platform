#!/usr/bin/env python3
"""Add type: ignore comments to baseline mypy errors."""

import re
import sys
from pathlib import Path

def parse_mypy_output(baseline_file):
    """Parse mypy output and extract file, line, and error info."""
    errors = []
    with open(baseline_file, "r") as f:
        for line in f:
            # Match pattern: filename:line: error: message [error-code]
            match = re.match(r"^(.+?):(\d+):\s+error:\s+(.+?)\s+\[(.+?)\]", line)
            if match:
                errors.append(
                    {
                        "file": match.group(1),
                        "line": int(match.group(2)),
                        "message": match.group(3),
                        "code": match.group(4),
                    }
                )
    return errors

def add_type_ignore(file_path, line_num, error_code):
    """Add type: ignore comment to a specific line."""
    lines = []
    with open(file_path, "r") as f:
        lines = f.readlines()

    if line_num > len(lines):
        print(f"Warning: Line {line_num} exceeds file length for {file_path}")
        return False

    # Check if type: ignore already exists
    line_idx = line_num - 1
    if "type: ignore" in lines[line_idx]:
        print(f"Skipping {file_path}:{line_num} - already has type: ignore")
        return False

    # Add type: ignore comment
    line = lines[line_idx].rstrip()
    if not line.endswith("  # type: ignore"):
        lines[line_idx] = f"{line}  # type: ignore[{error_code}]\n"

    with open(file_path, "w") as f:
        f.writelines(lines)

    return True

def main():
    """Execute the main logic to add type ignores."""
    baseline_file = ".mypy-baseline.txt"
    if not Path(baseline_file).exists():
        print(f"Error: {baseline_file} not found")
        sys.exit(1)

    errors = parse_mypy_output(baseline_file)

    # Group errors by file
    errors_by_file = {}
    for error in errors:
        if error["file"] not in errors_by_file:
            errors_by_file[error["file"]] = []
        errors_by_file[error["file"]].append(error)

    # Sort errors by line number in reverse order (to avoid line number shifts)
    for file_path, file_errors in errors_by_file.items():
        file_errors.sort(key=lambda x: x["line"], reverse=True)

    # Apply fixes
    fixed_count = 0
    for file_path, file_errors in errors_by_file.items():
        if not Path(file_path).exists():
            print(f"Warning: File {file_path} not found")
            continue

        print(f"\nProcessing {file_path}...")
        for error in file_errors:
            if add_type_ignore(file_path, error["line"], error["code"]):
                print(f"  Added type: ignore[{error['code']}] at line {error['line']}")
                fixed_count += 1

    print(f"\nTotal fixes applied: {fixed_count}")

if __name__ == "__main__":
    main()
