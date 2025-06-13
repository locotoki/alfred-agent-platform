#!/usr/bin/env python3
"""
Fix benchmark tests by replacing xfail markers with benchmark markers.

This script:
1. Searches for all Python files in the tests/benchmark directory
2. Also searches for any files with "benchmark" in their name in the tests directory
3. Removes individual @pytest.mark.xfail markers and replaces with @pytest.mark.benchmark
4. Updates pytestmark global xfail markers
"""

import re
import sys
from pathlib import Path

def process_file(file_path: Path) -> tuple[bool, int]:
    """Process a single file to replace xfail markers.

    Args:
        file_path: Path to the Python file

    Returns:
        tuple: (file_was_changed, number_of_replacements)
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Count original xfail markers
    xfail_count = content.count("@pytest.mark.xfail")

    # Replace individual xfail markers on test functions
    pattern = r"@pytest\.mark\.xfail\(.*?\)\s+"
    benchmark_replacement = "@pytest.mark.benchmark\n"
    new_content = re.sub(pattern, benchmark_replacement, content)

    # Replace global pytestmark = pytest.mark.xfail
    pattern = r"pytestmark\s*=\s*pytest\.mark\.xfail\(.*?\)"
    benchmark_replacement = (
        "# pytestmark has been removed - benchmark tests are skipped by default in conftest.py"
    )
    new_content = re.sub(pattern, benchmark_replacement, new_content)

    # Only write the file if changes were made
    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True, xfail_count

    return False, 0

def main():
    """Replace benchmark xfail markers with benchmark markers."""
    # Get the project root directory
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent

    # Find benchmark test files
    benchmark_files = list(project_root.glob("tests/benchmark/**/*.py"))
    other_benchmark_files = list(project_root.glob("tests/**/test_*benchmark*.py"))

    # Combine and remove duplicates
    all_files = list(set(benchmark_files).union(set(other_benchmark_files)))

    print(f"Found {len(all_files)} benchmark test files to process:")

    total_files_changed = 0
    total_replacements = 0

    for file_path in all_files:
        file_changed, replacements = process_file(file_path)

        if file_changed:
            total_files_changed += 1
            total_replacements += replacements
            print(
                f"✅ Updated {file_path.relative_to(project_root)} - replaced {replacements} xfail markers"
            )
        else:
            print(f"- No changes needed in {file_path.relative_to(project_root)}")

    print(
        f"\nSummary: Updated {total_files_changed} files, replaced {total_replacements} xfail markers."
    )
    return 0

if __name__ == "__main__":
    sys.exit(main())
