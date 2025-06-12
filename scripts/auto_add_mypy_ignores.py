#!/usr/bin/env python3
"""Auto-add type ignore comments to files that fail mypy checks"""

import os
import re
import subprocess
import sys
from pathlib import Path  # noqa: F401

def run_mypy_and_get_errors():
    """Run mypy and capture the error output"""
    try:
        # Run mypy and capture stderr
        result = subprocess.run(
            ["dmypy", "run", "--", "."],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stderr.strip().split("\n")
    except subprocess.CalledProcessError as e:
        return e.stderr.strip().split("\n")

def read_error_file(file_path):
    """Read mypy errors from a file"""
    with open(file_path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def parse_mypy_errors(error_lines):
    """Parse mypy error output to extract file paths and line numbers"""
    file_errors = {}
    error_pattern = re.compile(r"^([^:]+):(\d+): error: (.+)$")

    for line in error_lines:
        match = error_pattern.match(line)
        if match:
            file_path, line_num, error_msg = match.groups()
            line_num = int(line_num)

            if file_path not in file_errors:
                file_errors[file_path] = {}

            if line_num not in file_errors[file_path]:
                file_errors[file_path][line_num] = []

            file_errors[file_path][line_num].append(error_msg)

    return file_errors

def add_type_ignore_comments(file_errors):
    """Add # type: ignore comments to files with mypy errors"""
    files_modified = 0

    for file_path, line_errors in file_errors.items():
        try:
            # Skip if file_path is not a file
            if not os.path.isfile(file_path):
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            modified = False
            for line_num, errors in line_errors.items():
                if line_num <= len(lines):
                    # Check if the line already has a type ignore comment
                    if "# type: ignore" not in lines[line_num - 1]:
                        # Add specific ignore code if possible
                        ignore_code = ""
                        if any("attr-defined" in err for err in errors):
                            ignore_code = "[attr-defined]"
                        elif any("arg-type" in err for err in errors):
                            ignore_code = "[arg-type]"
                        elif any("return-value" in err for err in errors):
                            ignore_code = "[return-value]"

                        lines[line_num - 1] = (
                            lines[line_num - 1].rstrip() + f"  # type: ignore{ignore_code}\n"
                        )
                        modified = True

            if modified:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                files_modified += 1
                print(f"Added type ignore comments to {file_path}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    return files_modified

def main():
    """Auto-add type ignore comments to files with mypy errors"""
    if len(sys.argv) > 1:
        # Use error file provided as argument
        error_file = sys.argv[1]
        print(f"Reading mypy errors from {error_file}...")
        error_lines = read_error_file(error_file)
    else:
        # Run mypy directly
        print("Running mypy to find type errors...")
        error_lines = run_mypy_and_get_errors()

    print(f"Parsing {len(error_lines)} lines of mypy output...")
    file_errors = parse_mypy_errors(error_lines)

    print(f"Found errors in {len(file_errors)} files")
    files_modified = add_type_ignore_comments(file_errors)

    print(f"Modified {files_modified} files")

if __name__ == "__main__":
    main()
