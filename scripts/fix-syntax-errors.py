#!/usr/bin/env python3
"""
Script to fix common syntax errors before running Black formatter.
This fixes common patterns that would cause Black to fail:
1. Missing parentheses in method chaining (e.g., obj.method1().method2())
2. Improper datetime formatting (datetime.now().strftime())
3. Multiline string formatting
"""

import argparse
import glob
import os
import re
from pathlib import Path

def fix_method_chaining(content):
    """Fix missing parentheses in method chaining"""
    # Find patterns like .get("key").get("subkey") and fix to .get("key").get("subkey")
    content = re.sub(r"(\.\w+\([^)]*\))(\w+\()", r"\1.\2", content)
    return content

def fix_datetime_formatting(content):
    """Fix datetime function calls without proper parentheses"""
    # Find patterns like datetime.now().strftime and fix to datetime.now().strftime
    content = re.sub(r"(now\(\))(\w+\()", r"\1.\2", content)
    return content

def fix_string_issues(content):
    """Fix string formatting issues"""
    # Fix patterns like foo = """text""" to foo = """text"""
    content = re.sub(r'=\s*\.\s*"""', r'= """', content)
    return content

def fix_file(file_path):
    """Apply all fixes to a file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Apply all fixes
        original_content = content
        content = fix_method_chaining(content)
        content = fix_datetime_formatting(content)
        content = fix_string_issues(content)

        # Only write if changes were made
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Fix common syntax errors in Python files")
    parser.add_argument("--dir", "-d", default=".", help="Directory to process")
    parser.add_argument("--files", "-f", nargs="+", help="Specific files to process")
    args = parser.parse_args()

    if args.files:
        python_files = [f for f in args.files if f.endswith(".py")]
    else:
        python_files = glob.glob(os.path.join(args.dir, "**", "*.py"), recursive=True)

    # Skip directories that should be excluded
    excluded_dirs = [
        ".git",
        ".mypy_cache",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "youtube-test-env",
        "migrations",
    ]

    filtered_files = []
    for file in python_files:
        path = Path(file)
        if not any(excluded in path.parts for excluded in excluded_dirs):
            filtered_files.append(file)

    files_fixed = 0
    for file in filtered_files:
        if fix_file(file):
            files_fixed += 1
            print(f"Fixed: {file}")

    print(f"Processed {len(filtered_files)} files, fixed {files_fixed} files")

if __name__ == "__main__":
    main()
