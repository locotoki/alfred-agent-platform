#!/usr/bin/env python3
"""
Validate the Spring-Clean inventory.csv file.

This script checks the inventory.csv file for common issues such as:
- Empty file paths
- Incorrect classification values
- Duplicate entries
- Improper CSV formatting
"""

import csv
import os
import sys
from pathlib import Path

def validate_inventory(inventory_file: str) -> bool:
    """
    Validate the inventory.csv file.

    Args:
        inventory_file: Path to the inventory.csv file

    Returns:
        bool: True if valid, False if issues found
    """
    if not os.path.exists(inventory_file):
        print(f"Error: Inventory file {inventory_file} not found.")
        return False

    valid = True
    rows = []
    file_paths = set()
    empty_paths = []
    invalid_classifications = []
    line_number = 0

    try:
        with open(inventory_file, "r", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header
            line_number = 1

            # Validate header
            if header != ["file_path", "classification"]:
                print(f"Warning: Unexpected CSV header: {header}")
                valid = False

            # Validate rows
            for row_num, row in enumerate(reader, 2):
                line_number = row_num
                if len(row) != 2:
                    print(f"Error: Row {row_num} has {len(row)} columns, expected 2.")
                    valid = False
                    continue

                file_path, classification = row

                # Check for empty file paths
                if not file_path.strip():
                    empty_paths.append(row_num)
                    valid = False
                    continue

                # Check for duplicate file paths
                if file_path in file_paths:
                    print(f"Error: Duplicate file path on line {row_num}: {file_path}")
                    valid = False
                else:
                    file_paths.add(file_path)

                # Check classification value
                if classification not in ["USED", "ORPHAN"]:
                    invalid_classifications.append((row_num, classification))
                    valid = False

                rows.append(row)

    except Exception as e:
        print(f"Error reading CSV at line {line_number}: {str(e)}")
        return False

    # Report issues
    if empty_paths:
        print(f"Error: Found {len(empty_paths)} empty file paths on lines: {empty_paths}")

    if invalid_classifications:
        print("Error: Found invalid classifications:")
        for line, value in invalid_classifications:
            print(f"  Line {line}: '{value}' (should be 'USED' or 'ORPHAN')")

    # Check if any files actually exist in the repository
    repo_root = Path(inventory_file).parent.parent.parent
    missing_files = 0
    for file_path in file_paths:
        if not (repo_root / file_path).exists() and not file_path.startswith("."):
            # Skip hidden files like .gitignore
            missing_files += 1
            if missing_files <= 10:  # Only show first 10
                print(f"Warning: File does not exist in repo: {file_path}")

    if missing_files > 10:
        print(f"... and {missing_files - 10} more missing files")

    # Print summary
    total_files = len(rows)
    used_count = sum(1 for row in rows if row[1] == "USED")
    orphan_count = sum(1 for row in rows if row[1] == "ORPHAN")
    other_count = total_files - used_count - orphan_count

    print("\nInventory summary:")
    print(f"  Total entries: {total_files}")
    print(f"  USED:         {used_count} ({used_count/total_files*100:.1f}% if valid)")
    print(f"  ORPHAN:       {orphan_count} ({orphan_count/total_files*100:.1f}% if valid)")
    if other_count > 0:
        print(f"  Invalid:      {other_count}")

    return valid

def main() -> int:
    """Run the validator on the inventory.csv file."""
    # Get the script directory
    script_dir = Path(__file__).parent
    inventory_file = script_dir.parent.parent / "arch" / "spring_clean" / "inventory.csv"

    print(f"Validating inventory file: {inventory_file}")
    if validate_inventory(str(inventory_file)):
        print("\n✅ Inventory validation passed!")
        return 0
    else:
        print("\n❌ Inventory validation failed! Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
