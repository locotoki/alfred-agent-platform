#!/usr/bin/env python3
"""Script to fix method chaining syntax errors in Python files"""

import os
import re
from pathlib import Path  # noqa: F401

def fix_method_chaining(file_path):
    """Fix method chaining syntax errors in Python files"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Store original content for comparison
        original_content = content

        # Fix method chaining issues
        content = re.sub(r"(\.\w+\([^)]*\))(\w+\()", r"\1.\2", content)
        content = re.sub(r"(\(.*?\))(\w+\()", r"\1.\2", content)
        content = re.sub(r"(\.\w+\([^)]*\))(\w+)", r"\1.\2", content)
        content = re.sub(r"(\.\w+\(\))(\w+\()", r"\1.\2", content)
        content = re.sub(r"(\.\w+\(\))(\w+)", r"\1.\2", content)

        # Fix specific patterns like datetime.now().strftime
        content = re.sub(r"(now\(\))(\w+)", r"\1.\2", content)
        content = re.sub(r"(utcnow\(\))(\w+)", r"\1.\2", content)
        content = re.sub(r"(today\(\))(\w+)", r"\1.\2", content)
        content = re.sub(r"(date\(\))(\w+)", r"\1.\2", content)

        # Fix lowercase() and strip() chaining
        content = re.sub(r"(\w+\(\))lower\(\)", r"\1.lower()", content)
        content = re.sub(r"(\w+\(\))strip\(\)", r"\1.strip()", content)
        content = re.sub(r"(\w+\(\))replace\(", r"\1.replace(", content)

        # Fix numpy and pandas method chaining
        content = re.sub(r"(\w+\(\))reshape\(", r"\1.reshape(", content)
        content = re.sub(r"(\w+\(\))toarray\(", r"\1.toarray(", content)

        # Fix dictionary and collection operations
        content = re.sub(r"(\w+\(\))items\(\)", r"\1.items()", content)
        content = re.sub(r"(\w+\(\))values\(\)", r"\1.values()", content)
        content = re.sub(r"(\w+\(\))keys\(\)", r"\1.keys()", content)
        content = re.sub(r"(\w+\(\))get\(", r"\1.get(", content)

        # Fix prometheus metrics chaining
        content = re.sub(r"(\w+\([^)]*\))inc\(\)", r"\1.inc()", content)
        content = re.sub(r"(\w+\([^)]*\))observe\(", r"\1.observe(", content)
        content = re.sub(r"(\w+\([^)]*\))get_value\(\)", r"\1.get_value()", content)

        # Fix bytes/string operations
        content = re.sub(r"(\w+\(\))decode\(", r"\1.decode(", content)
        content = re.sub(r"(\w+\(\))encode\(", r"\1.encode(", content)
        content = re.sub(r"(\w+\(\))hexdigest\(\)", r"\1.hexdigest()", content)

        # Fix API response chains
        content = re.sub(r"(\w+\(\))result\(\)", r"\1.result()", content)
        content = re.sub(r"(\w+\(\))scalars\(\)", r"\1.scalars()", content)
        content = re.sub(r"(\w+\(\))all\(\)", r"\1.all()", content)
        content = re.sub(r"(\w+\(\))first\(\)", r"\1.first()", content)

        # Fix split operations
        content = re.sub(r"(\w+\(\))split\(", r"\1.split(", content)

        # Fix label operations for collections
        content = re.sub(r"(\w+\(\))labels", r"\1.labels", content)
        content = re.sub(r"(\w+\(\))collections", r"\1.collections", content)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Scan the codebase and fix method chaining syntax errors"""
    # Define a list of directories we want to process
    directories_to_check = [
        "agents",
        "alfred",
        "libs",
        "scripts",
        "services",
        "api",
        "backend",
        "tests",
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
                    if fix_method_chaining(file_path):
                        fixed_count += 1
                        print(f"Fixed: {file_path}")

    print(f"\nProcessed {total_files} Python files")
    print(f"Fixed method chaining in {fixed_count} files")

if __name__ == "__main__":
    main()
