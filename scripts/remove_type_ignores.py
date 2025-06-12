#!/usr/bin/env python3
"""Remove unnecessary '# type: ignore' comments from Python files"""

import argparse
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def get_python_files(exclude_venv=True):
    """Get all Python files in the project"""
    root_dir = Path(".")
    python_files = []

    for path in root_dir.rglob("*.py"):
        if exclude_venv and ".venv/" in str(path):
            continue
        python_files.append(path)

    return python_files

def remove_blanket_type_ignore(file_path):
    """Remove '# type: ignore' from the top of the file"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Look for standalone '# type: ignore' at the beginning of the file
    # or after shebang/docstring
    updated_content = re.sub(r"(^|\n)# type: ignore(\s*)(\n|$)", r"\1\3", content)

    if updated_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        return True

    return False

def check_mypy(paths=None):
    """Run mypy on the given paths or the entire project"""
    cmd = ["mypy"]
    if paths:
        cmd.extend(str(p) for p in paths)
    else:
        cmd.append(".")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def process_file(file_path, check=True, verbose=False):
    """Process a single file, remove type: ignore and check if mypy still passes"""
    original_content = None
    if check:
        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read()

    removed = remove_blanket_type_ignore(file_path)
    if not removed:
        if verbose:
            print(f"No blanket ignore found in {file_path}")
        return False

    if check:
        success, output = check_mypy([file_path])
        if not success:
            # Revert changes
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(original_content)
            if verbose:
                print(f"Failed mypy check for {file_path}, reverted changes")
                print(output)
            return False

    if verbose:
        print(f"Successfully removed type ignore from {file_path}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Remove unnecessary '# type: ignore' comments.")
    parser.add_argument(
        "--no-check",
        action="store_true",
        help="Don't check with mypy after removing comments",
    )
    parser.add_argument(
        "--batch", type=int, default=10, help="Number of files to process in parallel"
    )
    parser.add_argument("--verbose", action="store_true", help="Print detailed information")
    args = parser.parse_args()

    python_files = get_python_files()
    total_files = len(python_files)
    modified_count = 0

    print(f"Found {total_files} Python files")

    with ThreadPoolExecutor(max_workers=args.batch) as executor:
        futures = {
            executor.submit(process_file, file_path, not args.no_check, args.verbose): file_path
            for file_path in python_files
        }

        for future in futures:
            if future.result():
                modified_count += 1

    print(f"Removed unnecessary '# type: ignore' from {modified_count} files")

    if not args.no_check:
        success, output = check_mypy()
        if success:
            print("Final mypy check passed successfully!")
        else:
            print("Final mypy check failed. Some files may still have type issues.")
            print(output)

if __name__ == "__main__":
    main()
