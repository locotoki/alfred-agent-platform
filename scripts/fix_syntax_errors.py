#!/usr/bin/env python3
"""Script to fix common syntax errors in Python files"""

import os
import re
from pathlib import Path  # noqa: F401

def fix_syntax_errors(file_path):
    """Fix various syntax errors in Python files"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Store original content for comparison
        original_content = content

        # Fix class definitions with trailing periods
        class_pattern = r"(class\s+\w+(?:\s*\([^)]*\))?):\."
        content = re.sub(class_pattern, r"\1:", content)

        # Fix function definitions with trailing periods
        func_pattern = r"(def\s+\w+\s*\([^)]*\)):\."
        content = re.sub(func_pattern, r"\1:", content)

        # Fix method calls with trailing periods
        method_pattern = r"(\.\w+\s*\([^)]*\))\."
        content = re.sub(method_pattern, r"\1", content)

        # Fix trailing periods before multi-line strings
        string_pattern = r'(\w+\s*=\s*)\.([\s]*""")'
        content = re.sub(string_pattern, r"\1\2", content)

        # Fix other common syntax errors
        content = re.sub(
            r'(\w+\s*)\.(""")', r"\1\2", content
        )  # Remove periods before triple quotes
        content = re.sub(
            r"(\w+\s*=\s*)\.(.*)", r"\1\2", content
        )  # Remove periods after assignments
        content = re.sub(
            r"(await\s+\w+\s*)\.(.*)", r"\1\2", content
        )  # Remove periods after await statements

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Scan the codebase and fix common syntax errors"""
    # Define a list of directories we want to process
    directories_to_check = [
        "agents",
        "alfred",
        "libs",
        "scripts",
        "services",
        "api",
        "backend",
    ]

    fixed_count = 0
    total_files = 0

    for directory in directories_to_check:
        if not os.path.exists(directory):
            continue

        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    total_files += 1
                    if fix_syntax_errors(file_path):
                        fixed_count += 1
                        print(f"Fixed: {file_path}")

    print(f"\nProcessed {total_files} Python files")
    print(f"Fixed syntax errors in {fixed_count} files")

if __name__ == "__main__":
    main()
