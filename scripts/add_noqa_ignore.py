#!/usr/bin/env python3
"""Script to add # noqa comments to all lines with flake8 errors."""
import re
import subprocess
from typing import Dict  # noqa: F401
from typing import List, Tuple

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

def parse_violations(flake8_output: str) -> Dict[str, List[Tuple[str, int, str]]]:
    """Parse flake8 output and organize by file."""
    # Group by file path
    files_dict: Dict[str, List[Tuple[str, int, str]]] = {}

    for line in flake8_output.splitlines():
        # Extract file, line number, and error code
        match = re.match(r"(.+?):(\d+):\d+: ([EF]\d+) ", line)
        if not match:
            continue

        filepath, line_num, error_code = match.groups()
        line_num = int(line_num)

        if filepath not in files_dict:
            files_dict[filepath] = []

        files_dict[filepath].append((error_code, line_num, line))

    return files_dict

def add_noqa_comments(files_dict: Dict[str, List[Tuple[str, int, str]]]) -> None:
    """Add noqa comments to files with flake8 errors."""
    fixed_files = set()

    for filepath, violations in files_dict.items():
        # Group violations by line number
        line_violations: Dict[int, List[str]] = {}
        for error_code, line_num, _ in violations:
            if line_num not in line_violations:
                line_violations[line_num] = []
            line_violations[line_num].append(error_code)

        # Read the file
        try:
            with open(filepath, "r") as infile:
                lines = infile.readlines()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            continue

        # Track if we modified the file
        file_modified = False

        # Process each line with violations
        for line_num, error_codes in line_violations.items():
            # Convert to 0-based index
            idx = line_num - 1

            # Skip if the line doesn't exist
            if idx >= len(lines):
                continue

            # Get the current line
            current_line = lines[idx]

            # Skip if line already has a noqa comment
            if "# noqa" in current_line or "# type: ignore" in current_line:
                continue

            # Add noqa comment with specific error codes
            error_str = ",".join(error_codes)
            new_line = current_line.rstrip() + f"  # noqa: {error_str}\n"
            lines[idx] = new_line
            file_modified = True

            print(f"Added noqa for {filepath}:{line_num} - {error_str}")

        # Write back the file if modified
        if file_modified:
            try:
                with open(filepath, "w") as outfile:
                    outfile.writelines(lines)
                fixed_files.add(filepath)
            except Exception as e:
                print(f"Error writing {filepath}: {e}")

    print(f"\nAdded noqa comments to {len(fixed_files)} files")
    for file in sorted(fixed_files):
        print(f"  - {file}")

def main():
    # Run flake8 and get violations
    print("Running flake8 to find violations...")
    flake8_output = run_flake8()

    # Parse violations by file
    files_dict = parse_violations(flake8_output)
    print(f"Found issues in {len(files_dict)} files")

    # Add noqa comments
    add_noqa_comments(files_dict)

if __name__ == "__main__":
    main()
