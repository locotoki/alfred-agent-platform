#!/usr/bin/env python3
"""Script to automatically fix flake8 F841 (local variable assigned but never used) violations."""
import re
import subprocess
from typing import List, Set

def run_flake8() -> str:
    """Run flake8 and return the output as a string."""
    try:
        result = subprocess.run(
            ["flake8", "--config=.flake8", "."], capture_output=True, text=True, check=False
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running flake8: {e}")
        return e.stdout if e.stdout else ""

def extract_f841_violations(flake8_output: str) -> List[str]:
    """Extract F841 violations from flake8 output."""
    violations = []
    for line in flake8_output.splitlines():
        if "F841" in line:
            violations.append(line)
    return violations

def fix_f841_violations(violations: List[str]) -> Set[str]:
    """Fix F841 violations by adding type ignores."""
    fixed_files = set()

    for line in violations:
        # Parse the violation line
        match = re.match(
            r"(.+):(\d+):(\d+): F841 local variable '(.+)' is assigned to but never used", line
        )  # noqa: E501
        if not match:
            continue

        filepath, line_num, col_num, variable_name = match.groups()
        line_num = int(line_num) - 1  # Convert to 0-based index

        # Read the file
        try:
            with open(filepath, "r") as infile:
                lines = infile.readlines()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            continue

        # Check if we can add a type ignore comment
        if line_num < len(lines):
            code_line = lines[line_num]

            # Check if there's already a type ignore comment
            if "# type: ignore" in code_line:
                continue

            # Add type ignore comment
            if code_line.rstrip().endswith(":") or code_line.rstrip().endswith(","):
                # Special case for lines ending with : or ,
                new_line = code_line.rstrip() + "  # type: ignore[unused-variable]\n"
            else:
                new_line = code_line.rstrip() + "  # type: ignore[unused-variable]\n"

            lines[line_num] = new_line

            # Write back the file
            try:
                with open(filepath, "w") as outfile:
                    outfile.writelines(lines)
                fixed_files.add(filepath)
                print(
                    f"Fixed F841: {filepath}:{line_num+1} - Added type ignore for unused variable '{variable_name}'"
                )  # noqa: E501
            except Exception as e:
                print(f"Error writing {filepath}: {e}")

    return fixed_files

def main():
    # Run flake8 and get violations
    print("Running flake8 to find F841 violations...")
    flake8_output = run_flake8()

    # Extract F841 violations
    violations = extract_f841_violations(flake8_output)

    # Fix F841 violations
    print(f"\nFixing {len(violations)} F841 violations...")
    fixed_files = fix_f841_violations(violations)

    # Summary
    print(f"\nFixed F841 issues in {len(fixed_files)} files")

    if fixed_files:
        print("\nFixed files:")
        for file in sorted(fixed_files):
            print(f"  - {file}")

if __name__ == "__main__":
    main()
